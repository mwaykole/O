"""
OpenShift Operator Management Module

This module provides functionality for installing, monitoring, and managing various OpenShift operators
including Serverless, Service Mesh, Authorino, and RHOAI operators. It handles operator lifecycle
management, status monitoring, and cleanup operations.
"""

# operator.py
import concurrent.futures
import json
import logging
import os
import tempfile
import time
from typing import Dict, List, Tuple, Optional
from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
from rhoshift.utils.constants import WaitTime

import rhoshift.utils.constants as constants
from rhoshift.utils.utils import run_command, apply_manifest, wait_for_resource_for_specific_status

logger = logging.getLogger(__name__)


class OpenShiftOperatorInstaller:
    """
    Manages the installation and lifecycle of OpenShift operators.
    
    This class provides methods for installing, monitoring, and uninstalling various OpenShift
    operators with proper error handling and status verification.
    """

    @classmethod
    def get_operator_configs(cls, oc_binary: str = "oc"):
        """Get operator configurations from optimized constants."""
        configs = {}
        manifest_generator = OpenShiftOperatorInstallManifest()
        
        for op_key in OpenShiftOperatorInstallManifest.list_operators():
            op_config = OpenShiftOperatorInstallManifest.get_operator_config(op_key)
            configs[op_key] = {
                'manifest': manifest_generator.generate_operator_manifest(op_key, oc_binary),
                'namespace': op_config.namespace,
                'display_name': op_config.display_name,
                'config': op_config  # Store the full config for advanced features
            }
        return configs

    @property
    def OPERATOR_CONFIGS(self):
        """Backward compatibility property."""
        return self.get_operator_configs()

    @classmethod
    def install_operator(cls, operator_name: str, **kwargs) -> Tuple[int, str, str]:
        """Install an OpenShift operator by name with validation."""
        oc_binary = kwargs.get('oc_binary', 'oc')
        
        configs = cls.get_operator_configs(oc_binary)
        
        if operator_name not in configs:
            available = ', '.join(OpenShiftOperatorInstallManifest.list_operators())
            raise ValueError(f"Unknown operator: {operator_name}. Available: {available}")
        
        warnings = OpenShiftOperatorInstallManifest.validate_operator_compatibility([operator_name])
        for warning in warnings:
            logger.warning(f"⚠️  {warning}")
            
        config = configs[operator_name]
        logger.info(f"Installing {config['display_name']}...")
        
        if operator_name == 'openshift-cert-manager-operator':
            kwargs.setdefault('timeout', WaitTime.WAIT_TIME_10_MIN)  # 10 minutes for cert-manager
            logger.info(f"Using extended timeout for cert-manager operator: {kwargs['timeout']} seconds")
        
        return cls._install_operator(operator_name, config['manifest'], **kwargs)

    @classmethod
    def install_serverless_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the OpenShift Serverless Operator."""
        return cls.install_operator('serverless-operator', **kwargs)

    @classmethod
    def install_service_mesh_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the Service Mesh Operator."""
        return cls.install_operator('servicemeshoperator', **kwargs)

    @classmethod
    def install_authorino_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the Authorino Operator."""
        return cls.install_operator('authorino-operator', **kwargs)

    @classmethod
    def install_cert_manager_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the cert-manager Operator."""
        return cls.install_operator('openshift-cert-manager-operator', **kwargs)

    @classmethod
    def install_kueue_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the Kueue Operator."""
        return cls.install_operator('kueue-operator', **kwargs)

    @classmethod
    def install_keda_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the KEDA (Custom Metrics Autoscaler) Operator."""
        logger.info("Installing KEDA (Custom Metrics Autoscaler) Operator...")
        result = cls.install_operator('openshift-custom-metrics-autoscaler-operator', **kwargs)
        
        if result[0] == 0:
            logger.info("Operator installed successfully. Creating KedaController resource...")
            
            keda_controller_manifest = """apiVersion: keda.sh/v1alpha1
kind: KedaController
metadata:
  name: keda
  namespace: openshift-keda
spec:
  admissionWebhooks:
    logEncoder: console
    logLevel: info
  metricsServer:
    logLevel: "0"
  operator:
    logEncoder: console
    logLevel: info
  serviceAccount: {}
  watchNamespace: ""
"""
            oc_binary = kwargs.get('oc_binary', 'oc')
            cmd = f"{oc_binary} apply -f - <<EOF\n{keda_controller_manifest}\nEOF"
            
            try:
                rc, stdout, stderr = run_command(
                    cmd,
                    max_retries=kwargs.get('max_retries', 3),
                    retry_delay=kwargs.get('retry_delay', 10),
                    timeout=kwargs.get('timeout', WaitTime.WAIT_TIME_5_MIN),
                    log_output=True
                )
                if rc == 0:
                    logger.info("✅ KedaController resource created successfully")
                    
                    logger.info("Waiting for KEDA to become ready...")
                    keda_ready_cmd = f"{oc_binary} get kedacontroller keda -n openshift-keda -o jsonpath='{{.status.phase}}'"
                    
                    import time
                    end_time = time.time() + 120
                    while time.time() < end_time:
                        try:
                            rc, phase, stderr = run_command(keda_ready_cmd, log_output=False)
                            if rc == 0 and "Installation Succeeded" in phase:
                                logger.info("✅ KEDA is ready and operational!")
                                break
                            elif rc == 0 and phase:
                                logger.debug(f"KEDA status: {phase}")
                            time.sleep(5)
                        except Exception:
                            time.sleep(5)
                    else:
                        logger.warning("⚠️  KEDA may still be starting up. Check status with: oc get kedacontroller keda -n openshift-keda")
                        
                else:
                    logger.error(f"❌ Failed to create KedaController resource: {stderr}")
                    logger.warning("You can manually create the KedaController later if needed")
                    
            except Exception as e:
                logger.error(f"❌ Failed to create KedaController resource: {str(e)}")
                logger.warning("You can manually create the KedaController later if needed")
        else:
            logger.error("❌ KEDA Operator installation failed")
        
        return result

    @classmethod
    def install_rhoai_operator(
            cls,
            oc_binary: str = "oc",
            timeout: int = 1200,
            **kwargs
    ) -> Dict[str, Dict[str, str]]:
        """
        Installs the Red Hat OpenShift AI (RHOAI) Operator using the olminstall script.

        Args:
            oc_binary: Path to OpenShift CLI binary
            timeout: Installation timeout in seconds
            **kwargs: Additional parameters:
                - rhoai_channel: Installation channel (stable/nightly)
                - rhoai_image: RHOAI container image
                - raw: Enable raw serving
                - create_dsc_dsci: Create Data Science Cluster/Instance

        Returns:
            Dict containing installation results and status

        Raises:
            RuntimeError: If required parameters are missing or installation fails
        """
        required_params = ['rhoai_channel', 'rhoai_image', 'raw', 'create_dsc_dsci']
        for param in required_params:
            if param not in kwargs:
                raise RuntimeError(f"Missing required parameter: {param}")

        channel = kwargs.pop("rhoai_channel")
        rhoai_image = kwargs.pop("rhoai_image")
        is_Raw = bool(kwargs.pop('raw'))  
        create_dsc_dsci = bool(kwargs.pop('create_dsc_dsci'))  

        if not channel or not rhoai_image:
            raise RuntimeError("Both channel and rhoai_image are required")

        temp_dir = tempfile.mkdtemp()
        results = {}

        try:
            clone_cmd = (
                f"git clone https://gitlab.cee.redhat.com/data-hub/olminstall.git {temp_dir} && "
                f"cd {temp_dir}"
            )

            rc, stdout, stderr = run_command(
                clone_cmd,
                timeout=WaitTime.WAIT_TIME_5_MIN,
                log_output=True,
                **kwargs
            )
            if rc != 0:
                raise RuntimeError(f"Failed to clone olminstall repo: {stderr}")

            extra_params = " -n rhods-operator -p opendatahub-operators" if channel == "odh-nightlies" else ""
            install_cmd = (
                f"cd {temp_dir} && "
                f"./setup.sh -t operator -u {channel} -i {rhoai_image}{extra_params}"
            )

            rc, stdout, stderr = run_command(
                install_cmd,
                timeout=timeout,
                log_output=True,
                **kwargs
            )

            if rc != 0:
                raise RuntimeError(f"RHOAI installation failed: {stderr}")

            namespace = "opendatahub-operators" if channel == "odh-nightlies" else "redhat-ods-operator"
            operator_name = "opendatahub-operator.1.18.0" if channel == "odh-nightlies" else "rhods-operator"
            # namespace = "redhat-ods-operator"
            results = cls.wait_for_operator(
                operator_name=operator_name,
                namespace=namespace,
                oc_binary=oc_binary,
                timeout=timeout
            )

            if results.get(operator_name, {}).get("status") != "installed":
                raise RuntimeError("RHOAI Operator installation timed out")

            logger.info("✅ RHOAI Operator installed successfully")
            
            if create_dsc_dsci:
                logger.info("⏳ Waiting for RHOAI webhook certificates to become valid...")
                webhook_wait_time = 60  # Wait 60 seconds for certificates to become valid
                logger.info(f"⏱️  Waiting {webhook_wait_time} seconds for webhook certificates...")
                time.sleep(webhook_wait_time)
                
                cls.deploy_dsc_dsci(
                    kserve_raw=is_Raw, 
                    channel=channel,
                    create_dsc_dsci=create_dsc_dsci,
                    kueue_management_state=kwargs.get('kueue_management_state')
                )

            return results

        except Exception as e:
            logger.error(f"❌ Failed to install RHOAI Operator: {str(e)}")
            results["rhods-operator"] = {
                'status': 'failed',
                'message': str(e)
            }
            return results

        finally:
            try:
                if os.path.exists(temp_dir):
                    run_command(f"rm -rf {temp_dir}", log_output=False)
            except Exception:
                pass

    @classmethod
    def _install_operator(cls, operator_name: str, manifest: str, **kwargs) -> Tuple[int, str, str]:
        """Internal method to handle operator installation."""
        try:
            logger.info(f"Applying manifest for {operator_name}...")
            cmd = f"{kwargs.get('oc_binary', 'oc')} apply -f - <<EOF\n{manifest}\nEOF"

            rc, stdout, stderr = run_command(
                cmd,
                max_retries=kwargs.get('max_retries', 3),
                retry_delay=kwargs.get('retry_delay', 10),
                timeout=kwargs.get('timeout', WaitTime.WAIT_TIME_5_MIN),
                log_output=True
            )

            if rc == 0:
                logger.debug(f"Manifest applied for {operator_name}")
                return rc, stdout, stderr

            raise RuntimeError(f"Installation failed with exit code {rc}. Error: {stderr}")

        except Exception as e:
            logger.error(f"Failed to install {operator_name}: {str(e)}")
            raise

    @classmethod
    def _check_operator_status(
            cls,
            operator_name: str,
            namespace: str,
            oc_binary: str,
            end_time: float,
            interval: int
    ) -> Tuple[bool, Optional[str]]:
        """Check both CSV and Deployment status for an operator."""
        try:
            if namespace not in ['openshift-operators']:  # Skip conflict check for shared namespaces
                og_cmd = f"{oc_binary} get operatorgroup -n {namespace}"
                rc, stdout, stderr = run_command(og_cmd, log_output=False)
                if rc == 0:
                    lines = stdout.strip().split('\n')
                    if len(lines) > 2:  # More than header + 1 operator group
                        return False, f"Multiple OperatorGroups detected in namespace {namespace}. This prevents CSV creation."
            
            sub_cmd = f"{oc_binary} get subscription -n {namespace} -o json"
            rc, stdout, stderr = run_command(sub_cmd, log_output=False)
            if rc == 0:
                import json
                subs = json.loads(stdout)
                for sub in subs.get('items', []):
                    conditions = sub.get('status', {}).get('conditions', [])
                    for condition in conditions:
                        if condition.get('status') == 'True' and 'Error' in condition.get('type', ''):
                            return False, f"Subscription error: {condition.get('message', 'Unknown error')}"
            
            from ..constants import OpenShiftOperatorInstallManifest
            operator_config = None
            try:
                operator_config = OpenShiftOperatorInstallManifest.get_operator_config(operator_name)
            except ValueError:
                pass
                
            if operator_config and operator_config.csv_name_prefix:
                csv_search_pattern = operator_config.csv_name_prefix
            else:
                csv_search_pattern = operator_name
            
            csv_cmd = f"{oc_binary} get csv -n {namespace} -o json"
            rc, stdout, stderr = run_command(csv_cmd, log_output=False)
            
            if rc != 0:
                return False, f"Error getting CSVs in {namespace}: {stderr}"
            
            import json
            try:
                csvs = json.loads(stdout)
                matching_csvs = []
                
                for csv in csvs.get('items', []):
                    csv_name = csv.get('metadata', {}).get('name', '')
                    if csv_name.startswith(csv_search_pattern):
                        phase = csv.get('status', {}).get('phase', '')
                        matching_csvs.append((csv_name, phase))
                
                if not matching_csvs:
                    return False, f"No CSV found matching pattern '{csv_search_pattern}' in namespace {namespace}"
                
                succeeded_csvs = [csv for csv, phase in matching_csvs if phase == "Succeeded"]
                if succeeded_csvs:
                    logger.debug(f"Found succeeded CSV: {succeeded_csvs[0]}")
                    return True, f"Operator fully installed and ready (CSV: {succeeded_csvs[0]})"
                
                # Report status of non-succeeded CSVs
                failed_csvs = [(csv, phase) for csv, phase in matching_csvs if phase in ["Failed", "InstallReady"]]
                if failed_csvs:
                    return False, f"CSV in failed state: {failed_csvs[0][0]} - {failed_csvs[0][1]}"
                
                # Report other states
                pending_csvs = [(csv, phase) for csv, phase in matching_csvs if phase not in ["Succeeded", "Failed"]]
                if pending_csvs:
                    return False, f"CSV pending: {pending_csvs[0][0]} - {pending_csvs[0][1]}"
                    
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON from CSV command: {e}"

            return False, "CSV not in succeeded phase"

        except Exception as e:
            return False, f"Unexpected error checking operator status: {str(e)}"

    @classmethod
    def wait_for_operator(
            cls,
            operator_name: str,
            namespace: str,
            oc_binary: str = "oc",
            timeout: int = 600,
            interval: int = 2
    ) -> Dict[str, Dict[str, str]]:
        return cls.wait_for_operators(
            operators=[{'name': operator_name, 'namespace': namespace}],
            oc_binary=oc_binary,
            timeout=timeout,
            interval=interval,
            max_workers=1
        )

    @classmethod
    def wait_for_operators(
            cls,
            operators: List[Dict[str, str]],
            oc_binary: str = "oc",
            timeout: int = WaitTime.WAIT_TIME_10_MIN,
            interval: int = 2,
            max_workers: int = 5
    ) -> Dict[str, Dict[str, str]]:
        results = {}
        end_time = time.time() + timeout
        def _check_operator(op: Dict[str, str]) -> Tuple[str, bool, str]:
            last_message = ""
            while time.time() < end_time:
                is_ready, message = cls._check_operator_status(
                    op['name'],
                    op['namespace'],
                    oc_binary,
                    end_time,
                    interval
                )

                if is_ready:
                    return op['name'], True, message

                if message != last_message:
                    logger.debug(f"{op['name']}: {message}")
                    last_message = message

                time.sleep(interval)

            return op['name'], False, f"Timeout after {timeout} seconds waiting for {op['name']}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_op = {
                executor.submit(_check_operator, op): op['name']
                for op in operators
            }

            for future in concurrent.futures.as_completed(future_to_op):
                op_name = future_to_op[future]
                try:
                    name, success, message = future.result()
                    if success:
                        results[name] = {'status': 'installed', 'message': message}
                        logger.info(f"✅ {name} is ready")
                    else:
                        results[name] = {'status': 'failed', 'message': message}
                        logger.error(f"❌ {name} failed: {message}")
                except Exception as e:
                    results[op_name] = {'status': 'failed', 'message': str(e)}
                    logger.error(f"❌ Error checking {op_name}: {str(e)}")

        return results

    @classmethod
    def force_delete_rhoai_dsc_dsci(cls,
                                    oc_binary: str = "oc",
                                    timeout: int = WaitTime.WAIT_TIME_5_MIN,
                                    channel: str = None,
                                    **kwargs
                                    ) -> Dict[str, Dict[str, str]]:
        """
        Removes RHOAI Data Science Cluster and Instance resources with finalizer cleanup.

        Args:
            oc_binary: Path to OpenShift CLI binary
            timeout: Command execution timeout in seconds
            **kwargs: Additional arguments for command execution

        Returns:
            Dict containing command execution results and status
        """
        results = {}
        ods_namespace = "opendatahub" if channel == "odh-nightlies" else "redhat-ods-operator"
        application_namespace = "opendatahub" if channel == "odh-nightlies" else "redhat-ods-applications"
        # Define the exact commands to run in order
        commands = [
            {
                "name": "delete_dsc",
                "cmd": f"{oc_binary} delete dsc --all -n {application_namespace} --wait=true --timeout={timeout}s",
                "description": "Delete all DSC resources"
            },
            {
                "name": "clean_dsci_finalizers",
                "cmd": f"{oc_binary} get dsci -n {ods_namespace} -o name | xargs -I {{}} {oc_binary} patch {{}} -n {ods_namespace} --type=merge -p '{{\"metadata\":{{\"finalizers\":[]}}}}'",
                "description": "Remove DSCI finalizers"
            },
            {
                "name": "delete_dsci",
                "cmd": f"{oc_binary} delete dsci --all -n {ods_namespace} --wait=true --timeout={timeout}s",
                "description": "Delete all DSCI resources"
            },
            {
                "name": "clean_dsc_finalizers",
                "cmd": f"{oc_binary} get dsc -n {application_namespace} -o name | xargs -I {{}} {oc_binary} patch {{}} -n {application_namespace} --type=merge -p '{{\"metadata\":{{\"finalizers\":[]}}}}'",
                "description": "Remove DSC finalizers"
            }
        ]

        for cmd_info in commands:
            try:
                rc, stdout, stderr = run_command(
                    cmd_info["cmd"],
                    timeout=timeout,
                    **kwargs
                )

                results[cmd_info["name"]] = {
                    "status": "success" if rc == 0 else "failed",
                    "return_code": rc,
                    "stdout": stdout,
                    "stderr": stderr,
                    "description": cmd_info["description"]
                }

                if rc != 0:
                    logger.warning(f"Command failed: {cmd_info['name']}. Error: {stderr}")
                    
                    # Special handling for webhook certificate issues in DSCI deletion
                    if cmd_info["name"] == "delete_dsci" and ("webhook" in stderr.lower() or "certificate" in stderr.lower() or "x509" in stderr.lower()):
                        logger.warning("⚠️  DSCI deletion failed due to webhook certificate issues, trying alternative approach...")
                        try:
                            # Try direct resource deletion bypassing webhook validation
                            direct_delete_cmd = f"{oc_binary} delete dsci default-dsci --ignore-not-found=true --force --grace-period=0"
                            alt_rc, alt_stdout, alt_stderr = run_command(direct_delete_cmd, timeout=60)
                            if alt_rc == 0:
                                logger.info("✅ DSCI deleted using direct approach")
                                results[cmd_info["name"]]["status"] = "success"
                                results[cmd_info["name"]]["alternative_method"] = "force delete"
                            else:
                                logger.warning(f"⚠️  Direct DSCI deletion also failed: {alt_stderr}")
                                # Try one more approach - patch finalizers first
                                try:
                                    patch_cmd = f"{oc_binary} patch dsci default-dsci --type=merge -p '{{\"metadata\":{{\"finalizers\":[]}}}}'"
                                    patch_rc, _, _ = run_command(patch_cmd, timeout=30)
                                    if patch_rc == 0:
                                        time.sleep(5)  # Give it time to process
                                        final_rc, _, _ = run_command(direct_delete_cmd, timeout=60)
                                        if final_rc == 0:
                                            logger.info("✅ DSCI deleted after finalizer removal")
                                            results[cmd_info["name"]]["status"] = "success"
                                            results[cmd_info["name"]]["alternative_method"] = "finalizer patch + force delete"
                                except Exception as patch_error:
                                    logger.warning(f"⚠️  Finalizer patch approach also failed: {patch_error}")
                        except Exception as e:
                            logger.warning(f"⚠️  Alternative DSCI deletion failed: {e}")
                else:
                    logger.info(f"Command succeeded: {cmd_info['name']}")

            except Exception as e:
                results[cmd_info["name"]] = {
                    "status": "error",
                    "error": str(e),
                    "description": cmd_info["description"]
                }
                logger.error(f"Exception executing {cmd_info['name']}: {str(e)}")

        return results

    @classmethod
    def install_rhoai_operator_enhanced(cls, **kwargs) -> Tuple[int, str, str]:
        """
        Enhanced RHOAI operator installation with comprehensive error handling.
        
        This method provides improved error handling for DSCI conflicts and
        webhook certificate timing issues.
        """
        try:
            # Use the standard installer but with enhanced error handling
            result = cls.install_rhoai_operator(**kwargs)
            return (0, "RHOAI operator with DSC/DSCI installed successfully", "")
        except Exception as e:
            error_msg = str(e)
            if "MonitoringNamespace is immutable" in error_msg:
                return (1, "", f"RHOAI installation failed due to DSCI conflict: {error_msg}. Use --deploy-rhoai-resources to force recreate DSCI.")
            else:
                return (1, "", f"RHOAI installation failed: {error_msg}")

    @classmethod
    def deploy_dsc_dsci(cls, channel, kserve_raw=False, create_dsc_dsci=False, kueue_management_state=None):
        """
        Deploys Data Science Cluster and Instance resources for RHOAI.

        Args:
            channel: Installation channel
            kserve_raw: Enable raw serving
            create_dsc_dsci: Create new DSC/DSCI resources
            kueue_management_state: Kueue managementState in DSC ('Managed', 'Unmanaged', or None)
        """
        logging.debug("Deploying Data Science Cluster and Instance resources...")
        if create_dsc_dsci:

            # Delete old dsc and dsci
            result = cls.force_delete_rhoai_dsc_dsci()
            # Check results
            dsci_deletion_successful = False
            for cmd_name, cmd_result in result.items():
                logger.info(f"{cmd_name}: {cmd_result['status']}")
                if cmd_result['status'] != 'success':
                    logger.error(f" {cmd_result.get('stderr', cmd_result.get('error', ''))}")
                    # If DSCI deletion fails due to webhook issues, try alternative deletion
                    if cmd_name == "delete_dsci" and "webhook" in cmd_result.get('stderr', '').lower():
                        logger.warning("⚠️  DSCI deletion failed due to webhook issues, trying alternative approach...")
                        try:
                            # Try direct resource deletion bypassing webhook validation
                            direct_delete_cmd = f"oc delete dsci default-dsci --ignore-not-found=true --force --grace-period=0"
                            rc, stdout, stderr = run_command(direct_delete_cmd, timeout=60)
                            if rc == 0:
                                logger.info("✅ DSCI deleted using direct approach")
                                dsci_deletion_successful = True
                            else:
                                logger.warning(f"⚠️  Direct DSCI deletion also failed: {stderr}")
                        except Exception as e:
                            logger.warning(f"⚠️  Alternative DSCI deletion failed: {e}")
                elif cmd_name == "delete_dsci" and cmd_result['status'] == 'success':
                    dsci_deletion_successful = True
            
            # Wait for DSCI to be completely deleted before proceeding
            if dsci_deletion_successful or create_dsc_dsci:
                logger.info("⏳ Waiting for DSCI deletion to complete...")
                max_wait_time = 120  # 2 minutes
                wait_interval = 5
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    check_cmd = "oc get dsci default-dsci 2>/dev/null || echo 'NOT_FOUND'"
                    rc, output, _ = run_command(check_cmd, log_output=False)
                    
                    if rc != 0 or 'NOT_FOUND' in output:
                        logger.info("✅ DSCI deletion confirmed - resource no longer exists")
                        break
                    else:
                        logger.debug(f"DSCI still exists, waiting... ({int(time.time() - start_time)}s elapsed)")
                        time.sleep(wait_interval)
                
                # Final check
                final_check_cmd = "oc get dsci default-dsci 2>/dev/null || echo 'NOT_FOUND'"
                rc, output, _ = run_command(final_check_cmd, log_output=False)
                if rc == 0 and 'NOT_FOUND' not in output:
                    logger.warning("⚠️  DSCI still exists after deletion attempts - proceeding anyway")
                    logger.info("💡 This may cause immutable field conflicts")
                else:
                    logger.info("✅ DSCI deletion wait completed successfully")
        
        # Check if DSCI already exists and handle conflicts
        existing_dsci_cmd = "oc get dsci default-dsci -o jsonpath='{.spec.monitoring.namespace}' 2>/dev/null || echo 'NOT_FOUND'"
        rc, existing_monitoring_ns, _ = run_command(existing_dsci_cmd, log_output=False)
        
        dsci_params = {}
        desired_monitoring_ns = "redhat-ods-monitoring"  # Default value
        if channel == "odh-nightlies":
            dsci_params["applications_namespace"] = "opendatahub"
            dsci_params["monitoring_namespace"] = "opendatahub"
            desired_monitoring_ns = "opendatahub"
        
        # Handle existing DSCI conflicts
        should_apply_dsci = True
        if rc == 0 and existing_monitoring_ns.strip() != "NOT_FOUND":
            existing_monitoring_ns = existing_monitoring_ns.strip()
            if existing_monitoring_ns != desired_monitoring_ns:
                logger.warning(f"⚠️  DSCI conflict detected: existing monitoring namespace is '{existing_monitoring_ns}', but '{desired_monitoring_ns}' is required for channel '{channel}'")
                
                if create_dsc_dsci:
                    logger.info("🔄 Attempting to recreate DSCI with correct configuration...")
                    # Force delete was attempted above during create_dsc_dsci block
                    logger.info("🛠️  Will attempt to apply new DSCI - if deletion failed, this may result in immutable field error")
                else:
                    logger.info(f"ℹ️  Using existing DSCI with monitoring namespace '{existing_monitoring_ns}' (channel '{channel}' requested '{desired_monitoring_ns}')")
                    # Use the existing configuration to avoid conflicts
                    if existing_monitoring_ns == "opendatahub":
                        dsci_params["applications_namespace"] = "opendatahub"
                        dsci_params["monitoring_namespace"] = "opendatahub"
                    else:
                        # Use defaults for redhat-ods-monitoring
                        dsci_params = {}
                    should_apply_dsci = False  # Don't apply DSCI to avoid conflict
        
        # Only apply DSCI if it doesn't exist or if we're creating new resources
        if should_apply_dsci:
            dsci = constants.get_dsci_manifest(
                kserve_raw=kserve_raw,
                **dsci_params
            )

            # Apply DSCI with enhanced error handling for immutable fields
            try:
                apply_manifest(dsci)
                logger.info("✅ DSCI manifest applied successfully")
            except Exception as e:
                error_msg = str(e)
                if "MonitoringNamespace is immutable" in error_msg or "immutable" in error_msg:
                    logger.error(f"❌ DSCI immutable field conflict: {error_msg}")
                    logger.info("💡 Suggestion: Use --deploy-rhoai-resources to force recreate DSCI with correct configuration")
                    raise
                else:
                    logger.error(f"❌ DSCI creation failed with unexpected error: {error_msg}")
                    raise
        else:
            logger.info(f"ℹ️  Using existing DSCI (monitoring namespace: {existing_monitoring_ns})")
        success, out, err = wait_for_resource_for_specific_status(
            status="Ready",
            cmd="oc get dsci/default-dsci -o jsonpath='{.status.phase}'",
            timeout=WaitTime.WAIT_TIME_10_MIN,
            interval=5,
            case_sensitive=True,
        )
        if success:
            logger.info("DSCI is Ready!")
        else:
            logger.error(f"DSCI did not become Ready. Last status: {out.strip()}")

        dsc_params = {}
        if channel == "odh-nightlies":
            dsc_params["operator_namespace"] = "opendatahub-operator"

        # Deploy DataScienceCluster with Kueue management state
        apply_manifest(constants.get_dsc_manifest(
            enable_raw_serving=kserve_raw, 
            kueue_management_state=kueue_management_state,
            **dsc_params
        ))
        namespace = "opendatahub" if channel == "odh-nightlies" else "redhat-ods-applications"

        success, out, err = wait_for_resource_for_specific_status(
            status="Ready",
            cmd=f"oc get dsc/default-dsc -n {namespace} -o jsonpath='{{.status.phase}}'",
            timeout=WaitTime.WAIT_TIME_10_MIN,
            interval=5,
            case_sensitive=True,
        )
        logging.warning(out)
        if success:
            logger.info("DSC is Ready!")
        else:
            logger.error(f"DSC did not become Ready. Last status: {out.strip()}")

    @classmethod
    def uninstall_operator(
            cls,
            operator_name: str,
            namespace: str,
            oc_binary: str = "oc",
            **kwargs
    ) -> Tuple[int, str, str]:
        try:
            logger.info(f"Uninstalling {operator_name} from {namespace}...")
            cmd = (
                f"{oc_binary} delete subscription {operator_name} -n {namespace} && "
                f"{oc_binary} delete csv -n {namespace} --selector operators.coreos.com/{operator_name}.{namespace}="
            )
            return run_command(
                cmd,
                max_retries=kwargs.get('max_retries', 3),
                retry_delay=kwargs.get('retry_delay', 10),
                timeout=kwargs.get('timeout', WaitTime.WAIT_TIME_5_MIN),
                log_output=True
            )
        except Exception as e:
            logger.error(f"Failed to uninstall {operator_name}: {str(e)}")
            raise

    @classmethod
    def install_all_and_wait(cls, oc_binary="oc", **kwargs) -> Dict[str, Dict[str, str]]:
        """
        Installs and monitors all supported operators in parallel with validation.

        Args:
            oc_binary: Path to OpenShift CLI binary
            **kwargs: Additional installation parameters

        Returns:
            Dict containing installation results for each operator
        """
        # Get all available operators from optimized config
        available_operators = OpenShiftOperatorInstallManifest.list_operators()
        
        # Add RHOAI operator separately as it uses different installation method
        install_methods = []
        
        # Add standard operators
        for op_key in available_operators:
            op_config = OpenShiftOperatorInstallManifest.get_operator_config(op_key)
            method_name = f"install_{op_key.replace('-', '_')}"
            if hasattr(cls, method_name):
                install_methods.append((op_key, op_config.namespace, getattr(cls, method_name)))
        
        # Add RHOAI operator (special case)
        install_methods.append(("rhods-operator", "redhat-ods-operator", cls.install_rhoai_operator))

        # Validate compatibility for all operators
        operator_names = [name for name, _, _ in install_methods]
        warnings = OpenShiftOperatorInstallManifest.validate_operator_compatibility(operator_names)
        
        if warnings:
            logger.warning("⚠️  Compatibility warnings for batch installation:")
            for warning in warnings:
                logger.warning(f"   - {warning}")

        logger.info("🚀 Applying manifests for all operators in parallel...")

        def _apply_install(name, namespace, method):
            try:
                rc, out, err = method(oc_binary=oc_binary, **kwargs)
                if rc == 0:
                    logger.debug(f"Manifest applied for {name}")
                    return name, namespace, True
                logger.error(f"❌ Failed to apply manifest for {name}: {err}")
                return name, namespace, False
            except Exception as e:
                logger.error(f"❌ Exception applying {name}: {e}")
                return name, namespace, False

        applied_successfully = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(install_methods)) as executor:
            futures = [
                executor.submit(_apply_install, name, namespace, method)
                for name, namespace, method in install_methods
            ]

            for future in concurrent.futures.as_completed(futures):
                name, namespace, success = future.result()
                if success:
                    applied_successfully.append({'name': name, 'namespace': namespace})

        if not applied_successfully:
            logger.error("❌ No operator manifests were applied successfully.")
            return {}

        logger.info("⏳ Waiting for all successfully applied operators to be ready...")
        results = cls.wait_for_operators(
            operators=applied_successfully,
            oc_binary=oc_binary,
            timeout=kwargs.get("timeout", WaitTime.WAIT_TIME_10_MIN),
            interval=kwargs.get("interval", 5),
            max_workers=len(applied_successfully)
        )

        logger.info("📦 Operator installation summary:")
        for name, result in results.items():
            status_icon = "✅" if result["status"] == "installed" else "❌"
            logger.info(f"{status_icon} {name}: {result['message']}")

        return results
