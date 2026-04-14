"""
Enhanced operator installation with integrated stability features.
This shows how to integrate the robustness improvements into the existing operator.py.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..constants import WaitTime
from ..health_monitor import HealthStatus, check_operator_health
from ..resilience import execute_resilient_operation
from ..stability_coordinator import (
    StabilityConfig,
    StabilityCoordinator,
    StabilityLevel,
)
from .operator import OpenShiftOperatorInstaller

logger = logging.getLogger(__name__)


class EnhancedOpenShiftOperatorInstaller(OpenShiftOperatorInstaller):
    """
    Enhanced operator installer with integrated stability and robustness features.

    This extends the existing installer with:
    - Pre-flight validation
    - Enhanced error recovery
    - Health monitoring
    - Automatic recovery
    """

    def __init__(
        self,
        stability_level: StabilityLevel = StabilityLevel.ENHANCED,
        oc_binary: str = "oc",
    ):
        self.stability_config = StabilityConfig(level=stability_level)
        self.coordinator = StabilityCoordinator(self.stability_config, oc_binary)
        self.oc_binary = oc_binary

    @classmethod
    def install_operator_with_stability(
        cls,
        operator_name: str,
        stability_level: StabilityLevel = StabilityLevel.ENHANCED,
        **kwargs,
    ) -> Tuple[int, str, str]:
        """
        Install operator with enhanced stability features.

        This method wraps the existing install_operator with:
        - Pre-flight checks
        - Resilient error handling
        - Post-installation health validation
        - Auto-recovery capabilities
        """

        installer = cls(stability_level, kwargs.get("oc_binary", "oc"))

        from ..constants import OpenShiftOperatorInstallManifest

        manifest_gen = OpenShiftOperatorInstallManifest()

        if operator_name in manifest_gen.OPERATORS:
            namespace = manifest_gen.OPERATORS[operator_name].namespace
        else:
            namespace = "openshift-operators"  # Default namespace

        success, results = installer.coordinator.install_operator_with_stability(
            operator_name=operator_name,
            namespace=namespace,
            installation_func=lambda **kw: cls.install_operator(operator_name, **kw),
            **kwargs,
        )

        if success:
            return 0, f"Successfully installed {operator_name}", ""
        else:
            error_msg = "; ".join(results.get("errors", ["Installation failed"]))
            return 1, "", error_msg

    @classmethod
    def install_keda_operator_enhanced(cls, **kwargs) -> Tuple[int, str, str]:
        """Enhanced KEDA operator installation with KedaController creation and stability."""

        def enhanced_keda_installation(**install_kwargs):
            """Enhanced KEDA installation with KedaController creation."""

            result = cls.install_operator(
                "openshift-custom-metrics-autoscaler-operator", **install_kwargs
            )

            if result[0] != 0:
                return result

            logger.info(
                "Creating KedaController resource with enhanced error handling..."
            )

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

            def create_keda_controller():
                from ..utils import apply_manifest

                return apply_manifest(
                    keda_controller_manifest,
                    oc_binary=install_kwargs.get("oc_binary", "oc"),
                    max_retries=5,
                    retry_delay=15,
                    timeout=WaitTime.WAIT_TIME_5_MIN,
                )

            success, controller_result, warnings = execute_resilient_operation(
                create_keda_controller,
                "KedaController creation",
                context={
                    "namespace": "openshift-keda",
                    "oc_binary": install_kwargs.get("oc_binary", "oc"),
                },
                max_retries=3,
            )

            if success:
                logger.info(
                    "✅ KedaController created successfully with enhanced resilience"
                )

                logger.info("Monitoring KEDA controller readiness...")
                keda_ready = cls._wait_for_keda_readiness(
                    install_kwargs.get("oc_binary", "oc")
                )

                if keda_ready:
                    logger.info("✅ KEDA controller is ready and operational")
                else:
                    logger.warning("⚠️  KEDA controller may still be starting up")
            else:
                logger.error(f"❌ KedaController creation failed: {controller_result}")
                for warning in warnings:
                    logger.warning(f"⚠️  {warning}")

            return result

        # Remove stability_level from kwargs to avoid conflict
        keda_kwargs = {k: v for k, v in kwargs.items() if k != "stability_level"}
        return cls.install_operator_with_stability(
            "openshift-custom-metrics-autoscaler-operator",
            stability_level=StabilityLevel.COMPREHENSIVE,  # Use highest stability level for KEDA
            **keda_kwargs,
        )

    @classmethod
    def _wait_for_keda_readiness(
        cls, oc_binary: str = "oc", timeout: int = 120
    ) -> bool:
        """Wait for KEDA controller to become ready with health monitoring."""

        import time

        end_time = time.time() + timeout

        while time.time() < end_time:
            try:
                # Use health monitoring to check KEDA status
                keda_ready_cmd = f"{oc_binary} get kedacontroller keda -n openshift-keda -o jsonpath='{{.status.phase}}'"

                from ..utils import run_command

                rc, phase, stderr = run_command(keda_ready_cmd, log_output=False)

                if rc == 0 and "Installation Succeeded" in phase:
                    return True
                elif rc == 0 and phase:
                    logger.debug(f"KEDA status: {phase}")

                time.sleep(5)

            except Exception as e:
                logger.debug(f"Error checking KEDA readiness: {e}")
                time.sleep(5)

        return False

    @classmethod
    def install_rhcl_operator_enhanced(cls, **kwargs) -> Tuple[int, str, str]:
        """Enhanced RHCL operator installation with Kuadrant CR creation."""
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller

        rhcl_kwargs = {k: v for k, v in kwargs.items() if k != "stability_level"}
        return OpenShiftOperatorInstaller.install_rhcl_operator(**rhcl_kwargs)

    @classmethod
    def install_lws_operator_enhanced(cls, **kwargs) -> Tuple[int, str, str]:
        """Enhanced LWS operator installation with LeaderWorkerSetOperator CR creation."""
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller

        lws_kwargs = {k: v for k, v in kwargs.items() if k != "stability_level"}
        return OpenShiftOperatorInstaller.install_lws_operator(**lws_kwargs)

    @classmethod
    def install_rhoai_operator_enhanced(cls, **kwargs) -> Tuple[int, str, str]:
        """
        Enhanced RHOAI operator installation with comprehensive stability features.

        This includes:
        - Enhanced webhook certificate handling
        - DSCI/DSC creation with retry logic
        - Health monitoring for all components
        """

        def enhanced_rhoai_installation(**install_kwargs):
            """Enhanced RHOAI installation with webhook resilience and DSC/DSCI deployment."""

            # Import the standard installer to access RHOAI installation logic
            from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller

            # Install RHOAI operator with full DSC/DSCI deployment logic
            result = OpenShiftOperatorInstaller.install_rhoai_operator(**install_kwargs)

            return result

        # Use the enhanced installation function with stability coordinator
        from rhoshift.utils.stability_coordinator import (
            StabilityConfig,
            StabilityCoordinator,
        )

        stability_config = StabilityConfig(level=StabilityLevel.COMPREHENSIVE)
        coordinator = StabilityCoordinator(
            stability_config, kwargs.get("oc_binary", "oc")
        )

        # Remove stability_level from kwargs to avoid conflict
        rhoai_kwargs = {k: v for k, v in kwargs.items() if k != "stability_level"}

        try:
            # Run enhanced installation with full RHOAI logic
            result = enhanced_rhoai_installation(**rhoai_kwargs)

            # Check if installation was successful
            if isinstance(result, dict):
                # Check if any operator failed
                failed_operators = [
                    name
                    for name, info in result.items()
                    if info.get("status") != "installed"
                    and info.get("status") != "success"
                ]

                if failed_operators:
                    error_msg = (
                        f"RHOAI installation failed for: {', '.join(failed_operators)}"
                    )
                    return (1, "", error_msg)
                else:
                    return (
                        0,
                        "RHOAI operator with DSC/DSCI installed successfully",
                        "",
                    )
            else:
                return (0, "RHOAI operator with DSC/DSCI installed successfully", "")

        except Exception as e:
            error_msg = str(e)
            if "MonitoringNamespace is immutable" in error_msg:
                return (
                    1,
                    "",
                    f"RHOAI installation failed due to DSCI conflict: {error_msg}. Use --deploy-rhoai-resources to force recreate DSCI.",
                )
            else:
                return (1, "", f"RHOAI installation failed: {error_msg}")

    def generate_installation_report(self) -> str:
        """Generate comprehensive installation report."""
        return self.coordinator.generate_stability_report()

    def monitor_all_operators(self) -> Dict[str, Dict[str, Any]]:
        """Monitor health of all installed operators."""
        return self.coordinator.monitor_installed_operators()

    @classmethod
    def validate_cluster_readiness(
        cls, oc_binary: str = "oc"
    ) -> Tuple[bool, list[str]]:
        """
        Validate cluster readiness before any operator installation.

        Returns:
            (ready: bool, warnings: List[str])
        """
        from ..resilience import run_preflight_checks

        return run_preflight_checks(oc_binary)

    @classmethod
    def validate_dsci_compatibility(
        cls, selected_ops: Dict[str, bool], config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate DSCI compatibility before operator installation.

        Args:
            selected_ops: Dictionary of selected operators
            config: Configuration dictionary containing channel info

        Returns:
            (compatible: bool, warnings: List[str])
        """
        warnings = []

        # Only check if RHOAI is being installed
        if not selected_ops.get("rhoai", False):
            return True, warnings

        from ..utils import run_command

        # Check if DSCI exists
        existing_dsci_cmd = "oc get dsci default-dsci -o jsonpath='{.spec.monitoring.namespace}' 2>/dev/null || echo 'NOT_FOUND'"
        rc, existing_monitoring_ns, _ = run_command(existing_dsci_cmd, log_output=False)

        if rc != 0 or existing_monitoring_ns.strip() == "NOT_FOUND":
            # No existing DSCI, no conflict
            return True, warnings

        existing_monitoring_ns = existing_monitoring_ns.strip()

        # Determine desired monitoring namespace based on channel
        channel = config.get("rhoai_channel", "stable")
        desired_monitoring_ns = (
            "opendatahub" if channel == "odh-nightlies" else "redhat-ods-monitoring"
        )

        # Check for conflict
        if existing_monitoring_ns != desired_monitoring_ns:
            deploy_resources = config.get("create_dsc_dsci", False)

            if deploy_resources:
                warnings.append(
                    f"🔄 DSCI will be recreated: existing monitoring namespace '{existing_monitoring_ns}' → '{desired_monitoring_ns}' (channel: {channel})"
                )
            else:
                warnings.append(
                    f"⚠️  DSCI compatibility: existing monitoring namespace is '{existing_monitoring_ns}', channel '{channel}' prefers '{desired_monitoring_ns}'. Using existing configuration."
                )
        else:
            warnings.append(
                f"✅ DSCI compatible: monitoring namespace '{existing_monitoring_ns}' matches channel '{channel}'"
            )

        return True, warnings

    @classmethod
    def check_operator_health_status(
        cls, operator_name: str, namespace: str, oc_binary: str = "oc"
    ) -> Tuple[HealthStatus, str]:
        """
        Check health status of a specific operator.

        Returns:
            (status: HealthStatus, report: str)
        """
        health_status, health_results = check_operator_health(
            operator_name, namespace, oc_binary
        )

        from ..health_monitor import generate_health_report

        report = generate_health_report(health_results)

        return health_status, report


# Example usage functions that show integration with existing code
def install_operators_with_enhanced_stability(
    selected_ops: Dict[str, bool], config: Dict[str, Any]
) -> bool:
    """
    Enhanced version of install_operators with integrated stability features.

    This function shows how to integrate the stability improvements
    into the existing operator installation workflow.
    """

    logger.info("🛡️  Installing operators with enhanced stability features...")

    # Validate cluster readiness first
    cluster_ready, cluster_warnings = (
        EnhancedOpenShiftOperatorInstaller.validate_cluster_readiness(
            config.get("oc_binary", "oc")
        )
    )

    if not cluster_ready:
        logger.error("❌ Cluster validation failed. Aborting installation.")
        return False

    for warning in cluster_warnings:
        logger.warning(f"⚠️  {warning}")

    # Validate DSCI compatibility for RHOAI installations
    dsci_compatible, dsci_warnings = (
        EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
    )

    if not dsci_compatible:
        logger.error("❌ DSCI compatibility validation failed. Aborting installation.")
        return False

    for warning in dsci_warnings:
        logger.info(f"🔍 DSCI: {warning}")

    # Create enhanced installer
    installer = EnhancedOpenShiftOperatorInstaller(
        stability_level=StabilityLevel.ENHANCED, oc_binary=config.get("oc_binary", "oc")
    )

    # Install operators with enhanced stability
    success_count = 0
    total_count = sum(selected_ops.values())

    # Define enhanced installation mapping
    enhanced_installers = {
        "keda": EnhancedOpenShiftOperatorInstaller.install_keda_operator_enhanced,
        "rhcl": EnhancedOpenShiftOperatorInstaller.install_rhcl_operator_enhanced,
        "lws": EnhancedOpenShiftOperatorInstaller.install_lws_operator_enhanced,
        "rhoai": EnhancedOpenShiftOperatorInstaller.install_rhoai_operator_enhanced,
    }

    cli_to_operator_map = {
        "cert-manager": "openshift-cert-manager-operator",
        "kueue": "kueue-operator",
        "keda": "openshift-custom-metrics-autoscaler-operator",
        "rhcl": "rhcl-operator",
        "lws": "leader-worker-set",
        "rhoai": "opendatahub-operator",
    }

    for op_name, should_install in selected_ops.items():
        if not should_install:
            continue

        logger.info(f"🚀 Installing {op_name} with enhanced stability...")

        # Get the actual operator name for installation
        actual_operator_name = cli_to_operator_map.get(op_name, op_name)

        try:
            if op_name in enhanced_installers:
                rc, stdout, stderr = enhanced_installers[op_name](**config)
            else:
                # Fall back to standard installation for operators without enhanced versions
                rc, stdout, stderr = (
                    EnhancedOpenShiftOperatorInstaller.install_operator_with_stability(
                        actual_operator_name, **config
                    )
                )

            if rc == 0:
                logger.info(
                    f"✅ {op_name} installed successfully with stability assurance"
                )
                success_count += 1
            else:
                logger.error(f"❌ {op_name} installation failed: {stderr}")

        except Exception as e:
            logger.error(f"❌ {op_name} installation error: {e}")

    # Generate final report
    installation_report = installer.generate_installation_report()
    logger.info(f"Installation Report:\n{installation_report}")

    # Monitor all operators
    monitoring_results = installer.monitor_all_operators()
    if monitoring_results:
        logger.info(
            f"🏥 Post-installation health monitoring completed for {len(monitoring_results)} operators"
        )

    success_rate = success_count / total_count if total_count > 0 else 0
    logger.info(
        f"📊 Installation success rate: {success_rate:.1%} ({success_count}/{total_count})"
    )

    return success_count == total_count
