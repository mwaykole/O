"""
Health monitoring and state validation for OpenShift operators and resources.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from .utils import run_command

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ResourceType(Enum):
    """Types of resources to monitor."""
    OPERATOR_CSV = "csv"
    SUBSCRIPTION = "subscription"
    DEPLOYMENT = "deployment"
    POD = "pod"
    SERVICE = "service"
    DSCI = "dsci"
    DSC = "dsc"
    OPERATOR_GROUP = "operatorgroup"


@dataclass
class HealthCheck:
    """Definition of a health check."""
    name: str
    resource_type: ResourceType
    namespace: str
    resource_name: Optional[str] = None
    expected_conditions: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300
    critical: bool = True  # If False, failures are warnings


@dataclass
class ResourceHealth:
    """Health information for a resource."""
    resource_type: ResourceType
    name: str
    namespace: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    last_checked: Optional[float] = None


class OperatorHealthMonitor:
    """Monitor operator health and validate resource states."""
    
    def __init__(self, oc_binary: str = "oc"):
        self.oc_binary = oc_binary
        self.health_cache: Dict[str, ResourceHealth] = {}
    
    def check_operator_health(
        self,
        operator_name: str,
        namespace: str,
        include_dependencies: bool = True
    ) -> Tuple[HealthStatus, List[ResourceHealth]]:
        """Comprehensive health check for an operator."""
        
        health_results = []
        overall_status = HealthStatus.HEALTHY
        
        # Define health checks for the operator
        health_checks = [
            HealthCheck(
                name=f"{operator_name}-subscription",
                resource_type=ResourceType.SUBSCRIPTION,
                namespace=namespace,
                resource_name=operator_name,
                expected_conditions={"type": "CatalogSourcesUnhealthy", "status": "False"}
            ),
            HealthCheck(
                name=f"{operator_name}-csv",
                resource_type=ResourceType.OPERATOR_CSV,
                namespace=namespace,
                expected_conditions={"phase": "Succeeded"}
            ),
            HealthCheck(
                name=f"{operator_name}-operatorgroup",
                resource_type=ResourceType.OPERATOR_GROUP,
                namespace=namespace,
                critical=False  # OperatorGroup issues are often warnings
            )
        ]
        
        # Execute health checks
        for check in health_checks:
            try:
                health_result = self._execute_health_check(check)
                health_results.append(health_result)
                
                # Update overall status
                if check.critical and health_result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif health_result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                logger.warning(f"Health check failed for {check.name}: {e}")
                health_results.append(ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {str(e)}",
                    last_checked=time.time()
                ))
        
        # Check dependent resources if requested
        if include_dependencies:
            dep_status, dep_results = self._check_operator_dependencies(operator_name, namespace)
            health_results.extend(dep_results)
            if dep_status == HealthStatus.UNHEALTHY and overall_status != HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return overall_status, health_results
    
    def _execute_health_check(self, check: HealthCheck) -> ResourceHealth:
        """Execute a specific health check."""
        
        if check.resource_type == ResourceType.SUBSCRIPTION:
            return self._check_subscription_health(check)
        elif check.resource_type == ResourceType.OPERATOR_CSV:
            return self._check_csv_health(check)
        elif check.resource_type == ResourceType.OPERATOR_GROUP:
            return self._check_operatorgroup_health(check)
        elif check.resource_type == ResourceType.DEPLOYMENT:
            return self._check_deployment_health(check)
        elif check.resource_type == ResourceType.POD:
            return self._check_pod_health(check)
        elif check.resource_type == ResourceType.DSCI:
            return self._check_dsci_health(check)
        elif check.resource_type == ResourceType.DSC:
            return self._check_dsc_health(check)
        else:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Unsupported resource type: {check.resource_type}",
                last_checked=time.time()
            )
    
    def _check_subscription_health(self, check: HealthCheck) -> ResourceHealth:
        """Check subscription health."""
        cmd = f"{self.oc_binary} get subscription -n {check.namespace} -o json"
        rc, stdout, stderr = run_command(cmd, log_output=False)
        
        if rc != 0:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot retrieve subscriptions: {stderr}",
                last_checked=time.time()
            )
        
        try:
            subs_data = json.loads(stdout)
            subscriptions = subs_data.get('items', [])
            
            if not subscriptions:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.UNHEALTHY,
                    message="No subscriptions found",
                    last_checked=time.time()
                )
            
            unhealthy_subs = []
            degraded_subs = []
            
            for sub in subscriptions:
                sub_name = sub.get('metadata', {}).get('name', 'unknown')
                conditions = sub.get('status', {}).get('conditions', [])
                
                for condition in conditions:
                    if condition.get('type') == 'CatalogSourcesUnhealthy':
                        if condition.get('status') == 'True':
                            unhealthy_subs.append(f"{sub_name}: {condition.get('message', 'Catalog source unhealthy')}")
                    
                    if 'Error' in condition.get('type', '') and condition.get('status') == 'True':
                        degraded_subs.append(f"{sub_name}: {condition.get('message', 'Error condition')}")
            
            if unhealthy_subs:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Unhealthy subscriptions: {', '.join(unhealthy_subs)}",
                    details={'unhealthy_subscriptions': unhealthy_subs},
                    last_checked=time.time()
                )
            
            if degraded_subs:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.DEGRADED,
                    message=f"Degraded subscriptions: {', '.join(degraded_subs)}",
                    details={'degraded_subscriptions': degraded_subs},
                    last_checked=time.time()
                )
            
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.HEALTHY,
                message=f"All {len(subscriptions)} subscription(s) are healthy",
                details={'subscription_count': len(subscriptions)},
                last_checked=time.time()
            )
            
        except json.JSONDecodeError as e:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Cannot parse subscription data: {e}",
                last_checked=time.time()
            )
    
    def _check_csv_health(self, check: HealthCheck) -> ResourceHealth:
        """Check ClusterServiceVersion health."""
        cmd = f"{self.oc_binary} get csv -n {check.namespace} -o json"
        rc, stdout, stderr = run_command(cmd, log_output=False)
        
        if rc != 0:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot retrieve CSVs: {stderr}",
                last_checked=time.time()
            )
        
        try:
            csvs_data = json.loads(stdout)
            csvs = csvs_data.get('items', [])
            
            if not csvs:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.UNHEALTHY,
                    message="No CSVs found",
                    last_checked=time.time()
                )
            
            failed_csvs = []
            pending_csvs = []
            succeeded_csvs = []
            
            for csv in csvs:
                csv_name = csv.get('metadata', {}).get('name', 'unknown')
                phase = csv.get('status', {}).get('phase', 'Unknown')
                
                if phase == 'Failed':
                    reason = csv.get('status', {}).get('reason', 'Unknown reason')
                    failed_csvs.append(f"{csv_name}: {reason}")
                elif phase in ['Pending', 'Installing']:
                    pending_csvs.append(f"{csv_name}: {phase}")
                elif phase == 'Succeeded':
                    succeeded_csvs.append(csv_name)
            
            if failed_csvs:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Failed CSVs: {', '.join(failed_csvs)}",
                    details={'failed_csvs': failed_csvs},
                    last_checked=time.time()
                )
            
            if pending_csvs:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.DEGRADED,
                    message=f"Pending CSVs: {', '.join(pending_csvs)}",
                    details={'pending_csvs': pending_csvs},
                    last_checked=time.time()
                )
            
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.HEALTHY,
                message=f"All {len(succeeded_csvs)} CSV(s) are succeeded",
                details={'succeeded_csvs': succeeded_csvs},
                last_checked=time.time()
            )
            
        except json.JSONDecodeError as e:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Cannot parse CSV data: {e}",
                last_checked=time.time()
            )
    
    def _check_operatorgroup_health(self, check: HealthCheck) -> ResourceHealth:
        """Check OperatorGroup health."""
        cmd = f"{self.oc_binary} get operatorgroup -n {check.namespace} -o json"
        rc, stdout, stderr = run_command(cmd, log_output=False)
        
        if rc != 0:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.DEGRADED,
                message=f"Cannot retrieve OperatorGroups: {stderr}",
                last_checked=time.time()
            )
        
        try:
            og_data = json.loads(stdout)
            operator_groups = og_data.get('items', [])
            
            if len(operator_groups) == 0:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.DEGRADED,
                    message="No OperatorGroup found",
                    last_checked=time.time()
                )
            
            if len(operator_groups) > 1:
                og_names = [og.get('metadata', {}).get('name', 'unknown') for og in operator_groups]
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.DEGRADED,
                    message=f"Multiple OperatorGroups found: {', '.join(og_names)}",
                    details={'operator_groups': og_names},
                    last_checked=time.time()
                )
            
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.HEALTHY,
                message="OperatorGroup is properly configured",
                last_checked=time.time()
            )
            
        except json.JSONDecodeError as e:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Cannot parse OperatorGroup data: {e}",
                last_checked=time.time()
            )
    
    def _check_deployment_health(self, check: HealthCheck) -> ResourceHealth:
        """Check deployment health."""
        if not check.resource_name:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message="Deployment name not specified",
                last_checked=time.time()
            )
        
        cmd = f"{self.oc_binary} get deployment {check.resource_name} -n {check.namespace} -o json"
        rc, stdout, stderr = run_command(cmd, log_output=False)
        
        if rc != 0:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot retrieve deployment {check.resource_name}: {stderr}",
                last_checked=time.time()
            )
        
        try:
            deployment_data = json.loads(stdout)
            spec_replicas = deployment_data.get('spec', {}).get('replicas', 1)
            status = deployment_data.get('status', {})
            ready_replicas = status.get('readyReplicas', 0)
            available_replicas = status.get('availableReplicas', 0)
            
            conditions = status.get('conditions', [])
            progressing = any(c.get('type') == 'Progressing' and c.get('status') == 'True' for c in conditions)
            available = any(c.get('type') == 'Available' and c.get('status') == 'True' for c in conditions)
            
            if ready_replicas == spec_replicas and available_replicas == spec_replicas and available:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.HEALTHY,
                    message=f"Deployment {check.resource_name} is fully available ({ready_replicas}/{spec_replicas})",
                    details={'ready_replicas': ready_replicas, 'spec_replicas': spec_replicas},
                    last_checked=time.time()
                )
            
            if progressing:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.DEGRADED,
                    message=f"Deployment {check.resource_name} is progressing ({ready_replicas}/{spec_replicas})",
                    details={'ready_replicas': ready_replicas, 'spec_replicas': spec_replicas},
                    last_checked=time.time()
                )
            
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNHEALTHY,
                message=f"Deployment {check.resource_name} is not available ({ready_replicas}/{spec_replicas})",
                details={'ready_replicas': ready_replicas, 'spec_replicas': spec_replicas},
                last_checked=time.time()
            )
            
        except json.JSONDecodeError as e:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Cannot parse deployment data: {e}",
                last_checked=time.time()
            )
    
    def _check_dsci_health(self, check: HealthCheck) -> ResourceHealth:
        """Check DSCInitialization health."""
        cmd = f"{self.oc_binary} get dsci -A -o json"
        rc, stdout, stderr = run_command(cmd, log_output=False)
        
        if rc != 0:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Cannot retrieve DSCI: {stderr}",
                last_checked=time.time()
            )
        
        try:
            dsci_data = json.loads(stdout)
            dscis = dsci_data.get('items', [])
            
            if not dscis:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.UNHEALTHY,
                    message="No DSCI found",
                    last_checked=time.time()
                )
            
            for dsci in dscis:
                dsci_name = dsci.get('metadata', {}).get('name', 'unknown')
                phase = dsci.get('status', {}).get('phase', 'Unknown')
                
                if phase == 'Ready':
                    return ResourceHealth(
                        resource_type=check.resource_type,
                        name=check.name,
                        namespace=check.namespace,
                        status=HealthStatus.HEALTHY,
                        message=f"DSCI {dsci_name} is Ready",
                        details={'dsci_name': dsci_name, 'phase': phase},
                        last_checked=time.time()
                    )
                else:
                    conditions = dsci.get('status', {}).get('conditions', [])
                    error_conditions = [c for c in conditions if c.get('status') == 'False']
                    
                    if error_conditions:
                        error_msg = error_conditions[0].get('message', f'Phase: {phase}')
                        return ResourceHealth(
                            resource_type=check.resource_type,
                            name=check.name,
                            namespace=check.namespace,
                            status=HealthStatus.DEGRADED,
                            message=f"DSCI {dsci_name} is not Ready: {error_msg}",
                            details={'dsci_name': dsci_name, 'phase': phase, 'conditions': conditions},
                            last_checked=time.time()
                        )
                    
                    return ResourceHealth(
                        resource_type=check.resource_type,
                        name=check.name,
                        namespace=check.namespace,
                        status=HealthStatus.DEGRADED,
                        message=f"DSCI {dsci_name} phase: {phase}",
                        details={'dsci_name': dsci_name, 'phase': phase},
                        last_checked=time.time()
                    )
            
        except json.JSONDecodeError as e:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Cannot parse DSCI data: {e}",
                last_checked=time.time()
            )
    
    def _check_dsc_health(self, check: HealthCheck) -> ResourceHealth:
        """Check DataScienceCluster health."""
        cmd = f"{self.oc_binary} get dsc -A -o json"
        rc, stdout, stderr = run_command(cmd, log_output=False)
        
        if rc != 0:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Cannot retrieve DSC: {stderr}",
                last_checked=time.time()
            )
        
        try:
            dsc_data = json.loads(stdout)
            dscs = dsc_data.get('items', [])
            
            if not dscs:
                return ResourceHealth(
                    resource_type=check.resource_type,
                    name=check.name,
                    namespace=check.namespace,
                    status=HealthStatus.UNHEALTHY,
                    message="No DSC found",
                    last_checked=time.time()
                )
            
            for dsc in dscs:
                dsc_name = dsc.get('metadata', {}).get('name', 'unknown')
                phase = dsc.get('status', {}).get('phase', 'Unknown')
                
                conditions = dsc.get('status', {}).get('conditions', [])
                ready_condition = next((c for c in conditions if c.get('type') == 'Ready'), None)
                
                if ready_condition and ready_condition.get('status') == 'True':
                    return ResourceHealth(
                        resource_type=check.resource_type,
                        name=check.name,
                        namespace=check.namespace,
                        status=HealthStatus.HEALTHY,
                        message=f"DSC {dsc_name} is Ready",
                        details={'dsc_name': dsc_name, 'phase': phase},
                        last_checked=time.time()
                    )
                else:
                    error_msg = phase
                    if ready_condition:
                        error_msg = ready_condition.get('message', phase)
                    
                    return ResourceHealth(
                        resource_type=check.resource_type,
                        name=check.name,
                        namespace=check.namespace,
                        status=HealthStatus.DEGRADED,
                        message=f"DSC {dsc_name}: {error_msg}",
                        details={'dsc_name': dsc_name, 'phase': phase, 'conditions': conditions},
                        last_checked=time.time()
                    )
            
        except json.JSONDecodeError as e:
            return ResourceHealth(
                resource_type=check.resource_type,
                name=check.name,
                namespace=check.namespace,
                status=HealthStatus.UNKNOWN,
                message=f"Cannot parse DSC data: {e}",
                last_checked=time.time()
            )
    
    def _check_pod_health(self, check: HealthCheck) -> ResourceHealth:
        """Check pod health for operator deployments."""
        # Implementation for pod health checks would go here
        return ResourceHealth(
            resource_type=check.resource_type,
            name=check.name,
            namespace=check.namespace,
            status=HealthStatus.UNKNOWN,
            message="Pod health checking not yet implemented",
            last_checked=time.time()
        )
    
    def _check_operator_dependencies(self, operator_name: str, namespace: str) -> Tuple[HealthStatus, List[ResourceHealth]]:
        """Check health of operator dependencies."""
        # This would check things like:
        # - Required services are running
        # - Network policies allow communication
        # - Required ConfigMaps/Secrets exist
        # For now, return empty dependencies
        return HealthStatus.HEALTHY, []
    
    def generate_health_report(self, health_results: List[ResourceHealth]) -> str:
        """Generate a human-readable health report."""
        report = []
        
        # Group by status
        healthy = [h for h in health_results if h.status == HealthStatus.HEALTHY]
        degraded = [h for h in health_results if h.status == HealthStatus.DEGRADED]
        unhealthy = [h for h in health_results if h.status == HealthStatus.UNHEALTHY]
        unknown = [h for h in health_results if h.status == HealthStatus.UNKNOWN]
        
        report.append("=== OPERATOR HEALTH REPORT ===")
        report.append("")
        
        if healthy:
            report.append(f"✅ HEALTHY ({len(healthy)}):")
            for h in healthy:
                report.append(f"   • {h.name}: {h.message}")
            report.append("")
        
        if degraded:
            report.append(f"⚠️  DEGRADED ({len(degraded)}):")
            for h in degraded:
                report.append(f"   • {h.name}: {h.message}")
            report.append("")
        
        if unhealthy:
            report.append(f"❌ UNHEALTHY ({len(unhealthy)}):")
            for h in unhealthy:
                report.append(f"   • {h.name}: {h.message}")
            report.append("")
        
        if unknown:
            report.append(f"❓ UNKNOWN ({len(unknown)}):")
            for h in unknown:
                report.append(f"   • {h.name}: {h.message}")
            report.append("")
        
        return "\n".join(report)


# Convenience functions
def check_operator_health(operator_name: str, namespace: str, oc_binary: str = "oc") -> Tuple[HealthStatus, List[ResourceHealth]]:
    """Convenience function to check operator health."""
    monitor = OperatorHealthMonitor(oc_binary)
    return monitor.check_operator_health(operator_name, namespace)


def generate_health_report(health_results: List[ResourceHealth]) -> str:
    """Convenience function to generate health report."""
    monitor = OperatorHealthMonitor()
    return monitor.generate_health_report(health_results)
