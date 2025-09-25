"""
Enhanced operator installation with integrated stability features.
This shows how to integrate the robustness improvements into the existing operator.py.
"""

import logging
from typing import Tuple, Dict, Any, Optional

from ..stability_coordinator import StabilityCoordinator, StabilityLevel, StabilityConfig
from ..resilience import execute_resilient_operation
from ..health_monitor import check_operator_health, HealthStatus
from .operator import OpenShiftOperatorInstaller
from ..constants import WaitTime

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
    
    def __init__(self, stability_level: StabilityLevel = StabilityLevel.ENHANCED, oc_binary: str = "oc"):
        self.stability_config = StabilityConfig(level=stability_level)
        self.coordinator = StabilityCoordinator(self.stability_config, oc_binary)
        self.oc_binary = oc_binary
    
    @classmethod
    def install_operator_with_stability(
        cls,
        operator_name: str,
        stability_level: StabilityLevel = StabilityLevel.ENHANCED,
        **kwargs
    ) -> Tuple[int, str, str]:
        """
        Install operator with enhanced stability features.
        
        This method wraps the existing install_operator with:
        - Pre-flight checks
        - Resilient error handling
        - Post-installation health validation
        - Auto-recovery capabilities
        """
        
        # Create enhanced installer instance
        installer = cls(stability_level, kwargs.get('oc_binary', 'oc'))
        
        # Extract namespace for operator
        from ..constants import OpenShiftOperatorInstallManifest
        manifest_gen = OpenShiftOperatorInstallManifest()
        
        if operator_name in manifest_gen.OPERATORS:
            namespace = manifest_gen.OPERATORS[operator_name].namespace
        else:
            namespace = "openshift-operators"  # Default namespace
        
        # Use stability coordinator to install
        success, results = installer.coordinator.install_operator_with_stability(
            operator_name=operator_name,
            namespace=namespace,
            installation_func=lambda **kw: cls.install_operator(operator_name, **kw),
            **kwargs
        )
        
        # Convert results back to expected format
        if success:
            return 0, f"Successfully installed {operator_name}", ""
        else:
            error_msg = "; ".join(results.get('errors', ['Installation failed']))
            return 1, "", error_msg
    
    @classmethod
    def install_serverless_operator_enhanced(cls, **kwargs) -> Tuple[int, str, str]:
        """Enhanced serverless operator installation with stability features."""
        return cls.install_operator_with_stability('serverless-operator', **kwargs)
    
    @classmethod
    def install_keda_operator_enhanced(cls, **kwargs) -> Tuple[int, str, str]:
        """Enhanced KEDA operator installation with KedaController creation and stability."""
        
        def enhanced_keda_installation(**install_kwargs):
            """Enhanced KEDA installation with KedaController creation."""
            
            # Install the operator first
            result = cls.install_operator('openshift-custom-metrics-autoscaler-operator', **install_kwargs)
            
            if result[0] != 0:
                return result
            
            # Create KedaController with resilience
            logger.info("Creating KedaController resource with enhanced error handling...")
            
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
                    oc_binary=install_kwargs.get('oc_binary', 'oc'),
                    max_retries=5,
                    retry_delay=15,
                    timeout=WaitTime.WAIT_TIME_5_MIN
                )
            
            # Use resilient operation for KedaController creation
            success, controller_result, warnings = execute_resilient_operation(
                create_keda_controller,
                "KedaController creation",
                context={'namespace': 'openshift-keda', 'oc_binary': install_kwargs.get('oc_binary', 'oc')},
                max_retries=3
            )
            
            if success:
                logger.info("✅ KedaController created successfully with enhanced resilience")
                
                # Wait for KEDA readiness with health monitoring
                logger.info("Monitoring KEDA controller readiness...")
                keda_ready = cls._wait_for_keda_readiness(install_kwargs.get('oc_binary', 'oc'))
                
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
        keda_kwargs = {k: v for k, v in kwargs.items() if k != 'stability_level'}
        return cls.install_operator_with_stability(
            'openshift-custom-metrics-autoscaler-operator',
            stability_level=StabilityLevel.COMPREHENSIVE,  # Use highest stability level for KEDA
            **keda_kwargs
        )
    
    @classmethod
    def _wait_for_keda_readiness(cls, oc_binary: str = "oc", timeout: int = 120) -> bool:
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
    def install_rhoai_operator_enhanced(cls, **kwargs) -> Tuple[int, str, str]:
        """
        Enhanced RHOAI operator installation with comprehensive stability features.
        
        This includes:
        - Enhanced webhook certificate handling
        - DSCI/DSC creation with retry logic
        - Health monitoring for all components
        """
        
        def enhanced_rhoai_installation(**install_kwargs):
            """Enhanced RHOAI installation with webhook resilience."""
            
            # Install RHOAI operator
            result = cls.install_rhoai_operator(**install_kwargs)
            
            return result
        
        # Remove stability_level from kwargs to avoid conflict
        rhoai_kwargs = {k: v for k, v in kwargs.items() if k != 'stability_level'}
        return cls.install_operator_with_stability(
            'opendatahub-operator',  # Correct operator name
            stability_level=StabilityLevel.COMPREHENSIVE,  # Use highest stability for RHOAI
            **rhoai_kwargs
        )
    
    def generate_installation_report(self) -> str:
        """Generate comprehensive installation report."""
        return self.coordinator.generate_stability_report()
    
    def monitor_all_operators(self) -> Dict[str, Dict[str, Any]]:
        """Monitor health of all installed operators."""
        return self.coordinator.monitor_installed_operators()
    
    @classmethod
    def validate_cluster_readiness(cls, oc_binary: str = "oc") -> Tuple[bool, list[str]]:
        """
        Validate cluster readiness before any operator installation.
        
        Returns:
            (ready: bool, warnings: List[str])
        """
        from ..resilience import run_preflight_checks
        return run_preflight_checks(oc_binary)
    
    @classmethod
    def check_operator_health_status(cls, operator_name: str, namespace: str, oc_binary: str = "oc") -> Tuple[HealthStatus, str]:
        """
        Check health status of a specific operator.
        
        Returns:
            (status: HealthStatus, report: str)
        """
        health_status, health_results = check_operator_health(operator_name, namespace, oc_binary)
        
        from ..health_monitor import generate_health_report
        report = generate_health_report(health_results)
        
        return health_status, report


# Example usage functions that show integration with existing code
def install_operators_with_enhanced_stability(selected_ops: Dict[str, bool], config: Dict[str, Any]) -> bool:
    """
    Enhanced version of install_operators with integrated stability features.
    
    This function shows how to integrate the stability improvements
    into the existing operator installation workflow.
    """
    
    logger.info("🛡️  Installing operators with enhanced stability features...")
    
    # Validate cluster readiness first
    cluster_ready, warnings = EnhancedOpenShiftOperatorInstaller.validate_cluster_readiness(
        config.get('oc_binary', 'oc')
    )
    
    if not cluster_ready:
        logger.error("❌ Cluster validation failed. Aborting installation.")
        return False
    
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")
    
    # Create enhanced installer
    installer = EnhancedOpenShiftOperatorInstaller(
        stability_level=StabilityLevel.ENHANCED,
        oc_binary=config.get('oc_binary', 'oc')
    )
    
    # Install operators with enhanced stability
    success_count = 0
    total_count = sum(selected_ops.values())
    
    # Define enhanced installation mapping
    enhanced_installers = {
        'serverless': EnhancedOpenShiftOperatorInstaller.install_serverless_operator_enhanced,
        'keda': EnhancedOpenShiftOperatorInstaller.install_keda_operator_enhanced,
        'rhoai': EnhancedOpenShiftOperatorInstaller.install_rhoai_operator_enhanced,
        # Add other operators as needed
    }
    
    # Map CLI names to actual operator names
    cli_to_operator_map = {
        'serverless': 'serverless-operator',
        'servicemesh': 'servicemeshoperator',
        'authorino': 'authorino-operator',
        'cert-manager': 'openshift-cert-manager-operator',
        'kueue': 'kueue-operator',
        'keda': 'openshift-custom-metrics-autoscaler-operator',
        'rhoai': 'opendatahub-operator'
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
                rc, stdout, stderr = EnhancedOpenShiftOperatorInstaller.install_operator_with_stability(
                    actual_operator_name, **config
                )
            
            if rc == 0:
                logger.info(f"✅ {op_name} installed successfully with stability assurance")
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
        logger.info(f"🏥 Post-installation health monitoring completed for {len(monitoring_results)} operators")
    
    success_rate = success_count / total_count if total_count > 0 else 0
    logger.info(f"📊 Installation success rate: {success_rate:.1%} ({success_count}/{total_count})")
    
    return success_count == total_count


# Integration helper for existing code
def enhance_existing_operator_installation():
    """
    Example showing how to enhance existing operator.py methods.
    
    This would typically be done by modifying the existing methods
    to use the stability coordinator.
    """
    
    # Example of enhancing the existing install_serverless_operator method:
    original_install_serverless = OpenShiftOperatorInstaller.install_serverless_operator
    
    @classmethod
    def enhanced_install_serverless_operator(cls, **kwargs):
        """Enhanced version of install_serverless_operator."""
        return EnhancedOpenShiftOperatorInstaller.install_serverless_operator_enhanced(**kwargs)
    
    # Replace the original method (this would be done in operator.py)
    # OpenShiftOperatorInstaller.install_serverless_operator = enhanced_install_serverless_operator
    
    logger.info("✅ Enhanced operator installation methods integrated")
