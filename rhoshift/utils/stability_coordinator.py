"""
Stability coordinator that integrates all robustness improvements.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .resilience import ResilientOperatorManager, PreflightChecker, execute_resilient_operation
from .health_monitor import OperatorHealthMonitor, HealthStatus, ResourceHealth, ResourceType
from .constants import OpenShiftOperatorInstallManifest, WaitTime
from .utils import run_command

logger = logging.getLogger(__name__)


class StabilityLevel(Enum):
    """Stability assurance levels."""
    BASIC = 1               # Basic error handling
    ENHANCED = 2            # Enhanced with health checks
    COMPREHENSIVE = 3       # Full resilience + monitoring


@dataclass
class StabilityConfig:
    """Configuration for stability features."""
    level: StabilityLevel = StabilityLevel.ENHANCED
    enable_preflight_checks: bool = True
    enable_health_monitoring: bool = True
    enable_auto_recovery: bool = True
    health_check_timeout: int = 300
    max_recovery_attempts: int = 3
    monitoring_interval: int = 30


class StabilityCoordinator:
    """Coordinates all stability and robustness features."""
    
    def __init__(self, config: StabilityConfig, oc_binary: str = "oc"):
        self.config = config
        self.oc_binary = oc_binary
        self.resilient_manager = ResilientOperatorManager()
        self.health_monitor = OperatorHealthMonitor(oc_binary)
        self.preflight_checker = PreflightChecker()
        self.installed_operators: Dict[str, Dict[str, Any]] = {}
    
    def install_operator_with_stability(
        self,
        operator_name: str,
        namespace: str,
        installation_func: Callable,
        **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Install an operator with full stability assurance.
        
        Returns:
            (success: bool, results: Dict[str, Any])
        """
        
        results = {
            'operator_name': operator_name,
            'namespace': namespace,
            'preflight_passed': False,
            'installation_success': False,
            'health_check_passed': False,
            'warnings': [],
            'errors': [],
            'installation_time': 0,
            'health_status': HealthStatus.UNKNOWN
        }
        
        start_time = time.time()
        
        try:
            # Phase 1: Pre-flight checks
            if self.config.enable_preflight_checks:
                logger.info(f"🔍 Running pre-flight checks for {operator_name}...")
                preflight_success, preflight_warnings = self._run_preflight_checks(namespace)
                results['preflight_passed'] = preflight_success
                results['warnings'].extend(preflight_warnings)
                
                if not preflight_success:
                    results['errors'].append("Pre-flight checks failed")
                    return False, results
            
            # Phase 2: Enhanced installation with resilience
            logger.info(f"🚀 Installing {operator_name} with enhanced resilience...")
            
            if self.config.level.value >= StabilityLevel.ENHANCED.value:
                install_success, install_result, install_warnings = execute_resilient_operation(
                    installation_func,
                    f"{operator_name} installation",
                    context={'namespace': namespace, 'oc_binary': self.oc_binary},
                    **kwargs
                )
            else:
                try:
                    install_result = installation_func(**kwargs)
                    install_success = True
                    install_warnings = []
                except Exception as e:
                    install_success = False
                    install_result = e
                    install_warnings = [str(e)]
            
            results['installation_success'] = install_success
            results['warnings'].extend(install_warnings)
            results['installation_time'] = time.time() - start_time
            
            if not install_success:
                results['errors'].append(f"Installation failed: {install_result}")
                return False, results
            
            # Phase 3: Post-installation health checks
            if self.config.enable_health_monitoring:
                logger.info(f"🏥 Running health checks for {operator_name}...")
                health_success, health_details = self._run_health_checks(operator_name, namespace)
                results['health_check_passed'] = health_success
                results['health_status'] = health_details.get('overall_status', HealthStatus.UNKNOWN)
                results['health_details'] = health_details
                
                if not health_success and self.config.enable_auto_recovery:
                    logger.info(f"🔧 Attempting auto-recovery for {operator_name}...")
                    recovery_success = self._attempt_auto_recovery(operator_name, namespace, health_details)
                    results['auto_recovery_attempted'] = True
                    results['auto_recovery_success'] = recovery_success
                    
                    if recovery_success:
                        # Re-run health checks after recovery
                        health_success, health_details = self._run_health_checks(operator_name, namespace)
                        results['health_check_passed'] = health_success
                        results['health_status'] = health_details.get('overall_status', HealthStatus.UNKNOWN)
            
            # Track successful installation
            if install_success:
                self.installed_operators[operator_name] = {
                    'namespace': namespace,
                    'install_time': time.time(),
                    'health_status': results.get('health_status', HealthStatus.UNKNOWN)
                }
            
            return install_success, results
            
        except Exception as e:
            results['errors'].append(f"Unexpected error: {str(e)}")
            results['installation_time'] = time.time() - start_time
            logger.error(f"❌ Stability coordinator failed for {operator_name}: {e}")
            return False, results
    
    def _run_preflight_checks(self, namespace: str) -> Tuple[bool, List[str]]:
        """Run comprehensive pre-flight checks."""
        all_warnings = []
        
        # Basic cluster connectivity
        success, warnings = self.preflight_checker.validate_cluster_connectivity(self.oc_binary)
        all_warnings.extend(warnings)
        if not success:
            return False, all_warnings
        
        # Permission validation
        success, warnings = self.preflight_checker.validate_permissions(self.oc_binary, namespace)
        all_warnings.extend(warnings)
        if not success:
            return False, all_warnings
        
        # Resource quota checks
        success, warnings = self.preflight_checker.check_resource_quotas(self.oc_binary, namespace)
        all_warnings.extend(warnings)
        
        # Namespace-specific checks
        ns_warnings = self._check_namespace_readiness(namespace)
        all_warnings.extend(ns_warnings)
        
        return True, all_warnings
    
    def _check_namespace_readiness(self, namespace: str) -> List[str]:
        """Check if namespace is ready for operator installation."""
        warnings = []
        
        # Check if namespace exists
        cmd = f"{self.oc_binary} get namespace {namespace}"
        rc, stdout, stderr = run_command(cmd, max_retries=1, log_output=False)
        
        if rc != 0:
            if "not found" in stderr.lower():
                logger.info(f"📁 Namespace {namespace} will be created during installation")
            else:
                warnings.append(f"Cannot verify namespace {namespace}: {stderr}")
        else:
            logger.debug(f"✅ Namespace {namespace} exists")
        
        return warnings
    
    def _run_health_checks(self, operator_name: str, namespace: str) -> Tuple[bool, Dict[str, Any]]:
        """Run comprehensive health checks."""
        
        overall_status, health_results = self.health_monitor.check_operator_health(
            operator_name, namespace, include_dependencies=True
        )
        
        health_details = {
            'overall_status': overall_status,
            'health_results': health_results,
            'healthy_count': len([h for h in health_results if h.status == HealthStatus.HEALTHY]),
            'degraded_count': len([h for h in health_results if h.status == HealthStatus.DEGRADED]),
            'unhealthy_count': len([h for h in health_results if h.status == HealthStatus.UNHEALTHY]),
            'unknown_count': len([h for h in health_results if h.status == HealthStatus.UNKNOWN])
        }
        
        # Generate health report
        health_report = self.health_monitor.generate_health_report(health_results)
        health_details['report'] = health_report
        
        # Consider it successful if overall status is healthy or degraded (not critical issues)
        success = overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        
        if success:
            logger.info(f"✅ Health checks passed for {operator_name} (status: {overall_status.value})")
        else:
            logger.warning(f"⚠️  Health checks failed for {operator_name} (status: {overall_status.value})")
        
        logger.debug(f"Health report for {operator_name}:\n{health_report}")
        
        return success, health_details
    
    def _attempt_auto_recovery(self, operator_name: str, namespace: str, health_details: Dict[str, Any]) -> bool:
        """Attempt automatic recovery based on health check results."""
        
        if not self.config.enable_auto_recovery:
            return False
        
        health_results = health_details.get('health_results', [])
        recovery_actions = []
        
        # Analyze health issues and determine recovery actions
        for health_result in health_results:
            if health_result.status == HealthStatus.UNHEALTHY:
                if health_result.resource_type == ResourceType.SUBSCRIPTION:
                    recovery_actions.append(('restart_subscription', health_result))
                elif health_result.resource_type == ResourceType.OPERATOR_GROUP:
                    recovery_actions.append(('fix_operator_group', health_result))
                elif health_result.resource_type == ResourceType.DEPLOYMENT:
                    recovery_actions.append(('restart_deployment', health_result))
        
        if not recovery_actions:
            logger.info("🤷 No automatic recovery actions available")
            return False
        
        success_count = 0
        for action_type, health_result in recovery_actions[:self.config.max_recovery_attempts]:
            logger.info(f"🔧 Attempting recovery action: {action_type} for {health_result.name}")
            
            try:
                if self._execute_recovery_action(action_type, health_result, namespace):
                    success_count += 1
                    logger.info(f"✅ Recovery action {action_type} succeeded")
                else:
                    logger.warning(f"⚠️  Recovery action {action_type} failed")
            except Exception as e:
                logger.error(f"❌ Recovery action {action_type} error: {e}")
        
        # Consider recovery successful if at least one action succeeded
        return success_count > 0
    
    def _execute_recovery_action(self, action_type: str, health_result: ResourceHealth, namespace: str) -> bool:
        """Execute a specific recovery action."""
        
        if action_type == 'restart_subscription':
            return self._restart_subscription(health_result, namespace)
        elif action_type == 'fix_operator_group':
            return self._fix_operator_group(health_result, namespace)
        elif action_type == 'restart_deployment':
            return self._restart_deployment(health_result, namespace)
        else:
            logger.warning(f"Unknown recovery action: {action_type}")
            return False
    
    def _restart_subscription(self, health_result: ResourceHealth, namespace: str) -> bool:
        """Restart a problematic subscription."""
        try:
            # Delete and recreate subscription (this is a simplified approach)
            logger.info(f"🔄 Restarting subscription in {namespace}...")
            
            # For now, just log the action - implementing full subscription restart
            # would require storing original subscription manifests
            logger.warning("Subscription restart not fully implemented - requires manifest recreation")
            return False
            
        except Exception as e:
            logger.error(f"Failed to restart subscription: {e}")
            return False
    
    def _fix_operator_group(self, health_result: ResourceHealth, namespace: str) -> bool:
        """Fix OperatorGroup conflicts."""
        try:
            logger.info(f"🔧 Attempting to fix OperatorGroup in {namespace}...")
            
            # Get all operator groups in namespace
            cmd = f"{self.oc_binary} get operatorgroup -n {namespace} -o name"
            rc, stdout, stderr = run_command(cmd, log_output=False)
            
            if rc == 0:
                og_names = [line.strip() for line in stdout.split('\n') if line.strip()]
                
                if len(og_names) > 1:
                    # Delete extra operator groups (keep the first one)
                    for og_name in og_names[1:]:
                        logger.info(f"Deleting extra OperatorGroup: {og_name}")
                        delete_cmd = f"{self.oc_binary} delete {og_name} -n {namespace}"
                        rc, stdout, stderr = run_command(delete_cmd, log_output=False)
                        
                        if rc != 0:
                            logger.error(f"Failed to delete {og_name}: {stderr}")
                            return False
                    
                    logger.info("✅ Fixed OperatorGroup conflicts")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to fix OperatorGroup: {e}")
            return False
    
    def _restart_deployment(self, health_result: ResourceHealth, namespace: str) -> bool:
        """Restart a problematic deployment."""
        try:
            deployment_name = health_result.details.get('deployment_name')
            if not deployment_name:
                # Extract deployment name from health result
                if health_result.resource_type == ResourceType.DEPLOYMENT:
                    deployment_name = health_result.name.replace('-deployment', '').split('-')[-1]
            
            if deployment_name:
                logger.info(f"🔄 Restarting deployment {deployment_name} in {namespace}...")
                cmd = f"{self.oc_binary} rollout restart deployment/{deployment_name} -n {namespace}"
                rc, stdout, stderr = run_command(cmd, log_output=False)
                
                if rc == 0:
                    logger.info(f"✅ Deployment {deployment_name} restart initiated")
                    return True
                else:
                    logger.error(f"Failed to restart deployment {deployment_name}: {stderr}")
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to restart deployment: {e}")
            return False
    
    def monitor_installed_operators(self) -> Dict[str, Dict[str, Any]]:
        """Monitor health of all installed operators."""
        
        if not self.config.enable_health_monitoring:
            return {}
        
        monitoring_results = {}
        
        for operator_name, operator_info in self.installed_operators.items():
            namespace = operator_info['namespace']
            
            logger.debug(f"🏥 Monitoring {operator_name} in {namespace}...")
            
            try:
                health_success, health_details = self._run_health_checks(operator_name, namespace)
                
                monitoring_results[operator_name] = {
                    'namespace': namespace,
                    'health_success': health_success,
                    'health_details': health_details,
                    'last_monitored': time.time()
                }
                
                # Update stored health status
                self.installed_operators[operator_name]['health_status'] = health_details.get('overall_status', HealthStatus.UNKNOWN)
                
            except Exception as e:
                logger.error(f"Failed to monitor {operator_name}: {e}")
                monitoring_results[operator_name] = {
                    'namespace': namespace,
                    'health_success': False,
                    'error': str(e),
                    'last_monitored': time.time()
                }
        
        return monitoring_results
    
    def generate_stability_report(self) -> str:
        """Generate comprehensive stability report."""
        
        report = []
        report.append("=== STABILITY COORDINATOR REPORT ===")
        report.append("")
        report.append(f"Stability Level: {self.config.level.name.lower()}")
        report.append(f"Installed Operators: {len(self.installed_operators)}")
        report.append("")
        
        if self.installed_operators:
            report.append("OPERATOR STATUS:")
            for op_name, op_info in self.installed_operators.items():
                status_emoji = {
                    HealthStatus.HEALTHY: "✅",
                    HealthStatus.DEGRADED: "⚠️",
                    HealthStatus.UNHEALTHY: "❌",
                    HealthStatus.UNKNOWN: "❓"
                }.get(op_info.get('health_status', HealthStatus.UNKNOWN), "❓")
                
                install_time = op_info.get('install_time', 0)
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(install_time)) if install_time else "Unknown"
                
                report.append(f"  {status_emoji} {op_name} ({op_info['namespace']}) - Installed: {time_str}")
        
        report.append("")
        report.append("CONFIGURATION:")
        report.append(f"  • Pre-flight checks: {'Enabled' if self.config.enable_preflight_checks else 'Disabled'}")
        report.append(f"  • Health monitoring: {'Enabled' if self.config.enable_health_monitoring else 'Disabled'}")
        report.append(f"  • Auto recovery: {'Enabled' if self.config.enable_auto_recovery else 'Disabled'}")
        report.append(f"  • Max recovery attempts: {self.config.max_recovery_attempts}")
        
        return "\n".join(report)


# Convenience functions for easy integration
def create_stability_coordinator(
    level: StabilityLevel = StabilityLevel.ENHANCED,
    oc_binary: str = "oc"
) -> StabilityCoordinator:
    """Create a stability coordinator with default configuration."""
    config = StabilityConfig(level=level)
    return StabilityCoordinator(config, oc_binary)


def install_with_stability(
    operator_name: str,
    namespace: str,
    installation_func: Callable,
    stability_level: StabilityLevel = StabilityLevel.ENHANCED,
    oc_binary: str = "oc",
    **kwargs
) -> Tuple[bool, Dict[str, Any]]:
    """Convenience function to install operator with stability assurance."""
    
    coordinator = create_stability_coordinator(stability_level, oc_binary)
    return coordinator.install_operator_with_stability(
        operator_name, namespace, installation_func, **kwargs
    )
