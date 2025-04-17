# operator.py
import concurrent.futures
import json
import logging
import os
import tempfile
import time
from typing import Dict, List, Tuple, Optional
from utils.constants import OpenShiftOperatorInstallManifest
from utils.constants import WaitTime

import utils.constants as constants
from utils.utils import run_command, apply_manifest, wait_for_resource_for_specific_status

logger = logging.getLogger(__name__)


class OpenShiftOperatorInstaller:
    """Handles installation and monitoring of OpenShift operators."""

    @classmethod
    def install_serverless_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the OpenShift Serverless Operator."""
        manifest = OpenShiftOperatorInstallManifest.SERVERLESS_MANIFEST
        return cls._install_operator("serverless-operator", manifest, **kwargs)

    @classmethod
    def install_service_mesh_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the Service Mesh Operator."""
        manifest = OpenShiftOperatorInstallManifest.SERVICEMESH_MANIFEST
        return cls._install_operator("servicemeshoperator", manifest, **kwargs)

    @classmethod
    def install_authorino_operator(cls, **kwargs) -> Tuple[int, str, str]:
        """Install the Authorino Operator."""
        manifest = OpenShiftOperatorInstallManifest.AUTHORINO_MANIFEST
        return cls._install_operator("authorino-operator", manifest, **kwargs)

    @classmethod
    def install_rhoai_operator(
            cls,
            oc_binary: str = "oc",
            timeout: int = 1200,
            **kwargs
    ) -> Dict[str, Dict[str, str]]:
        """
        Install RHOAI (Red Hat OpenShift AI) Operator using the olminstall script.

        Args:
            channel: The channel to install from (e.g., 'stable' or 'nightly')
            rhoai_image: The RHOAI image to install
            oc_binary: Path to oc binary (default: 'oc')
            timeout: Timeout in seconds for installation (default: 1200)
            **kwargs: Additional arguments to pass to run_command

        Returns:
            Dictionary with installation results
        """
        channel = kwargs.pop("rhoai_channel")
        rhoai_image = kwargs.pop("rhoai_image")
        is_Raw = kwargs.pop('raw')
        create_dsc_dsci = kwargs.pop('create_dsc_dsci')
        temp_dir = tempfile.mkdtemp()
        results = {}
        if not channel or not rhoai_image:
            raise RuntimeError("Both channel and rhoai_image are required")
        try:
            # Clone the olminstall repository
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

            # Run the setup script
            install_cmd = (
                f"cd {temp_dir} && "
                f"./setup.sh -t operator -u {channel} -i {rhoai_image}"
            )

            rc, stdout, stderr = run_command(
                install_cmd,
                timeout=timeout,
                log_output=True,
                **kwargs
            )

            if rc != 0:
                raise RuntimeError(f"RHOAI installation failed: {stderr}")

            # Wait for the operator to be ready
            results = cls.wait_for_operator(
                operator_name="rhods-operator",
                namespace="redhat-ods-operator",
                oc_binary=oc_binary,
                timeout=timeout
            )

            if results.get("rhods-operator", {}).get("status") != "installed":
                raise RuntimeError("RHOAI Operator installation timed out")

            logger.info("✅ RHOAI Operator installed successfully")
            if create_dsc_dsci:
                # craete new dsc and dsci
                cls.deploy_dsc_dsci(kserve_raw=is_Raw, channel=channel,
                                    create_dsc_dsci=create_dsc_dsci)

            return results

        except Exception as e:
            logger.error(f"❌ Failed to install RHOAI Operator: {str(e)}")
            results["rhods-operator"] = {
                'status': 'failed',
                'message': str(e)
            }
            return results

        finally:
            # Clean up temporary directory
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
            # Check CSV status
            csv_cmd = f"{oc_binary} get csv -n default | grep '{operator_name}' | awk '{{print $NF}}'"
            rc, stdout, stderr = run_command(csv_cmd, log_output=True)

            if rc != 0:
                return False, f"Error running oc get csv: {stderr}"
            if stdout.strip() != "Succeeded":
                return False, "CSV not in succeeded phase"

            return True, "Operator fully installed and ready"

        except json.JSONDecodeError:
            return False, "Invalid JSON from oc command"
        except Exception as e:
            return False, str(e)

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
                                    **kwargs
                                    ) -> Dict[str, Dict[str, str]]:
        """
        Execute specific commands to delete RHOAI resources with finalizer cleanup.

        Args:
            oc_binary: Path to oc CLI (default: 'oc')
            timeout: Timeout in seconds for commands (default: 300)
            **kwargs: Additional arguments for run_command

        Returns:
            Dictionary with command execution results
        """
        results = {}

        # Define the exact commands to run in order
        commands = [
            {
                "name": "delete_dsc",
                "cmd": f"{oc_binary} delete dsc --all -n redhat-ods-applications --wait=true --timeout={timeout}s",
                "description": "Delete all DSC resources"
            },
            {
                "name": "clean_dsci_finalizers",
                "cmd": f"{oc_binary} get dsci -n redhat-ods-operator -o name | xargs -I {{}} {oc_binary} patch {{}} -n redhat-ods-operator --type=merge -p '{{\"metadata\":{{\"finalizers\":[]}}}}'",
                "description": "Remove DSCI finalizers"
            },
            {
                "name": "delete_dsci",
                "cmd": f"{oc_binary} delete dsci --all -n redhat-ods-operator --wait=true --timeout={timeout}s",
                "description": "Delete all DSCI resources"
            },
            {
                "name": "clean_dsc_finalizers",
                "cmd": f"{oc_binary} get dsc -n redhat-ods-applications -o name | xargs -I {{}} {oc_binary} patch {{}} -n redhat-ods-applications --type=merge -p '{{\"metadata\":{{\"finalizers\":[]}}}}'",
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
    def deploy_dsc_dsci(cls, channel, kserve_raw=False, create_dsc_dsci=False):
        kserve_raw = kserve_raw == "True"
        # create_dsc_dsci = create_dsc_dsci == "True"
        logging.debug(f" Creating DSC and DSCI resource.....")
        if create_dsc_dsci:
            # Delete old dsc and dsci
            result = cls.force_delete_rhoai_dsc_dsci()
            # Check results
            for cmd_name, cmd_result in result.items():
                logger.info(f"{cmd_name}: {cmd_result['status']}")
                if cmd_result['status'] != 'success':
                    logger.error(f" {cmd_result.get('stderr', cmd_result.get('error', ''))}")
        dsci_params = {}
        if channel == "odh-nightlies":
            dsci_params["applications_namespace"] = "opendatahub"
            dsci_params["monitoring_namespace"] = "opendatahub"

        dsci = constants.get_dsci_manifest(
            kserve_raw=kserve_raw,
            **dsci_params
        )

        apply_manifest(dsci)
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

        # Deploy DataScienceCluster
        apply_manifest(constants.get_dsc_manifest(enable_raw_serving=kserve_raw, **dsc_params))

        success, out, err = wait_for_resource_for_specific_status(
            status="Ready",
            cmd="oc get dsc/default-dsc -n redhat-ods-applications -o jsonpath='{.status.phase}'",
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
        """Install all known operators in parallel and wait for them in parallel."""
        install_methods = [
            ("serverless-operator", "openshift-serverless", cls.install_serverless_operator),
            ("servicemeshoperator", "openshift-operators", cls.install_service_mesh_operator),
            ("authorino-operator", "openshift-operators", cls.install_authorino_operator),
            ("rhods-operator", "redhat-ods-operator", cls.install_rhoai_operator),
        ]

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
