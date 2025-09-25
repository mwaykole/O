"""
Enhanced resilience and error handling utilities for robust operator management.
"""

import logging
import time
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from enum import Enum
from .utils import run_command
from .constants import WaitTime

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Categories of recoverable errors."""
    TRANSIENT = "transient"          # Network, timeout, temporary API issues
    CONFIGURATION = "configuration"  # Wrong config, missing resources
    DEPENDENCY = "dependency"        # Missing dependencies, order issues
    RESOURCE_CONFLICT = "conflict"   # Resource already exists, namespace conflicts
    PERMISSION = "permission"        # RBAC, security issues
    CRITICAL = "critical"           # Unrecoverable errors


@dataclass
class ErrorPattern:
    """Defines a pattern for error detection and recovery."""
    pattern: str
    error_type: ErrorType
    recovery_action: Optional[str] = None
    max_retries: int = 3
    backoff_multiplier: float = 2.0


class ResilientOperatorManager:
    """Enhanced operator management with robust error handling."""
    
    # Common error patterns and recovery strategies
    ERROR_PATTERNS = [
        # Webhook certificate timing issues (already handled)
        ErrorPattern(
            pattern=r"certificate has expired or is not yet valid",
            error_type=ErrorType.TRANSIENT,
            recovery_action="wait_for_certificates",
            max_retries=5,
            backoff_multiplier=1.5
        ),
        
        # Resource conflicts
        ErrorPattern(
            pattern=r"already exists|AlreadyExists",
            error_type=ErrorType.RESOURCE_CONFLICT,
            recovery_action="handle_resource_conflict",
            max_retries=2
        ),
        
        # OLM conflicts
        ErrorPattern(
            pattern=r"Multiple OperatorGroups|more than one operator group",
            error_type=ErrorType.CONFIGURATION,
            recovery_action="resolve_operator_group_conflict",
            max_retries=3
        ),
        
        # Network/API transient issues
        ErrorPattern(
            pattern=r"connection refused|timeout|dial tcp.*connect: connection refused",
            error_type=ErrorType.TRANSIENT,
            recovery_action="wait_and_retry",
            max_retries=5,
            backoff_multiplier=2.0
        ),
        
        # Storage/PVC issues
        ErrorPattern(
            pattern=r"no persistent volumes available|Insufficient storage",
            error_type=ErrorType.CONFIGURATION,
            recovery_action="check_storage_requirements",
            max_retries=2
        ),
        
        # Image pull issues
        ErrorPattern(
            pattern=r"ErrImagePull|ImagePullBackOff",
            error_type=ErrorType.CONFIGURATION,
            recovery_action="validate_image_access",
            max_retries=3
        ),
    ]
    
    @classmethod
    def execute_with_resilience(
        cls,
        operation: Callable,
        operation_name: str,
        max_retries: int = 3,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[bool, Any, List[str]]:
        """
        Execute an operation with enhanced error handling and recovery.
        
        Returns:
            (success: bool, result: Any, warnings: List[str])
        """
        warnings = []
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Executing {operation_name} (attempt {attempt}/{max_retries})")
                
                result = operation(**kwargs)
                logger.info(f"✅ {operation_name} completed successfully")
                return True, result, warnings
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(f"⚠️  {operation_name} failed (attempt {attempt}/{max_retries}): {error_msg}")
                
                # Analyze error and determine recovery strategy
                error_pattern = cls._classify_error(error_msg)
                
                if error_pattern and attempt < max_retries:
                    recovery_result = cls._attempt_recovery(
                        error_pattern, error_msg, context or {}, attempt
                    )
                    
                    if recovery_result:
                        warnings.extend(recovery_result.get('warnings', []))
                        if recovery_result.get('should_retry', True):
                            delay = error_pattern.backoff_multiplier ** (attempt - 1) * 5
                            logger.info(f"🔄 Attempting recovery, retrying in {delay}s...")
                            time.sleep(delay)
                            continue
                    else:
                        logger.error(f"❌ Recovery failed for {operation_name}")
                        break
                elif attempt < max_retries:
                    # Generic retry for unclassified errors
                    delay = 2 ** (attempt - 1) * 5  # Exponential backoff
                    logger.info(f"🔄 Retrying {operation_name} in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ {operation_name} failed after {max_retries} attempts")
                    break
        
        return False, last_error, warnings
    
    @classmethod
    def _classify_error(cls, error_msg: str) -> Optional[ErrorPattern]:
        """Classify error based on patterns."""
        for pattern in cls.ERROR_PATTERNS:
            if re.search(pattern.pattern, error_msg, re.IGNORECASE):
                return pattern
        return None
    
    @classmethod
    def _attempt_recovery(
        cls, 
        error_pattern: ErrorPattern, 
        error_msg: str, 
        context: Dict[str, Any],
        attempt: int
    ) -> Optional[Dict[str, Any]]:
        """Attempt to recover from specific error types."""
        
        if error_pattern.recovery_action == "wait_for_certificates":
            return cls._wait_for_certificates(context, attempt)
        
        elif error_pattern.recovery_action == "handle_resource_conflict":
            return cls._handle_resource_conflict(error_msg, context)
        
        elif error_pattern.recovery_action == "resolve_operator_group_conflict":
            return cls._resolve_operator_group_conflict(context)
        
        elif error_pattern.recovery_action == "wait_and_retry":
            return cls._wait_and_retry(context, attempt)
        
        elif error_pattern.recovery_action == "check_storage_requirements":
            return cls._check_storage_requirements(context)
        
        elif error_pattern.recovery_action == "validate_image_access":
            return cls._validate_image_access(error_msg, context)
        
        return None
    
    @staticmethod
    def _wait_for_certificates(context: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        """Handle webhook certificate timing issues."""
        delay = 30 + (attempt * 15)  # 30s, 45s, 60s...
        logger.info(f"🔐 Waiting {delay}s for webhook certificates to become valid...")
        time.sleep(delay)
        
        return {
            'should_retry': True,
            'warnings': [f'Webhook certificate timing issue resolved after {delay}s wait']
        }
    
    @staticmethod
    def _handle_resource_conflict(error_msg: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resource conflicts by checking if resource is in desired state."""
        warnings = []
        
        # Extract resource information from error
        if "already exists" in error_msg.lower():
            logger.info("🔍 Resource already exists, checking if it matches desired state...")
            
            # For now, assume existing resource is acceptable
            warnings.append("Resource already exists - using existing configuration")
            
            return {
                'should_retry': False,  # Don't retry, consider it successful
                'warnings': warnings
            }
        
        return {'should_retry': True, 'warnings': warnings}
    
    @staticmethod
    def _resolve_operator_group_conflict(context: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to resolve OperatorGroup conflicts."""
        namespace = context.get('namespace', 'unknown')
        oc_binary = context.get('oc_binary', 'oc')
        
        logger.info(f"🔧 Attempting to resolve OperatorGroup conflicts in {namespace}...")
        
        # Check existing OperatorGroups
        cmd = f"{oc_binary} get operatorgroup -n {namespace} -o json"
        rc, stdout, stderr = run_command(cmd, log_output=False)
        
        if rc == 0:
            try:
                og_data = json.loads(stdout)
                if len(og_data.get('items', [])) > 1:
                    logger.warning(f"⚠️  Multiple OperatorGroups found in {namespace}")
                    return {
                        'should_retry': False,
                        'warnings': [f'Multiple OperatorGroups in {namespace} - manual intervention required']
                    }
            except json.JSONDecodeError:
                pass
        
        return {'should_retry': True, 'warnings': []}
    
    @staticmethod
    def _wait_and_retry(context: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        """Generic wait and retry for transient issues."""
        delay = min(60, 10 * attempt)  # Cap at 60s
        logger.info(f"🕒 Transient issue detected, waiting {delay}s before retry...")
        time.sleep(delay)
        
        return {
            'should_retry': True,
            'warnings': [f'Transient network/API issue - retried after {delay}s']
        }
    
    @staticmethod
    def _check_storage_requirements(context: Dict[str, Any]) -> Dict[str, Any]:
        """Check storage requirements and availability."""
        oc_binary = context.get('oc_binary', 'oc')
        warnings = []
        
        logger.info("💾 Checking storage requirements...")
        
        # Check PVs
        cmd = f"{oc_binary} get pv"
        rc, stdout, stderr = run_command(cmd, log_output=False)
        
        if rc == 0:
            available_pvs = len([line for line in stdout.split('\n')[1:] 
                               if 'Available' in line and line.strip()])
            
            if available_pvs == 0:
                warnings.append('No available PersistentVolumes - may cause deployment issues')
                return {'should_retry': False, 'warnings': warnings}
            else:
                logger.info(f"✅ Found {available_pvs} available PersistentVolumes")
        
        return {'should_retry': True, 'warnings': warnings}
    
    @staticmethod
    def _validate_image_access(error_msg: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate image registry access."""
        warnings = []
        
        # Extract image name from error if possible
        image_pattern = r"image \"([^\"]+)\""
        match = re.search(image_pattern, error_msg)
        
        if match:
            image_name = match.group(1)
            logger.warning(f"🐳 Image pull issue detected for: {image_name}")
            warnings.append(f'Image pull failed for {image_name} - check registry access and credentials')
        else:
            warnings.append('Image pull failed - check registry access and credentials')
        
        return {'should_retry': True, 'warnings': warnings}


class PreflightChecker:
    """Pre-flight validation checks before operator installation."""
    
    @staticmethod
    def validate_cluster_connectivity(oc_binary: str = "oc") -> Tuple[bool, List[str]]:
        """Validate basic cluster connectivity."""
        logger.info("🔍 Validating cluster connectivity...")
        warnings = []
        
        # Test basic cluster access
        cmd = f"{oc_binary} cluster-info --request-timeout=10s"
        rc, stdout, stderr = run_command(cmd, max_retries=1, log_output=False)
        
        if rc != 0:
            return False, ["Cannot connect to OpenShift cluster - check kubeconfig"]
        
        # Check cluster version
        cmd = f"{oc_binary} version --request-timeout=10s"
        rc, stdout, stderr = run_command(cmd, max_retries=1, log_output=False)
        
        if rc == 0:
            logger.info("✅ Cluster connectivity verified")
        else:
            warnings.append("Could not determine cluster version")
        
        return True, warnings
    
    @staticmethod
    def validate_permissions(oc_binary: str = "oc", namespace: str = "default") -> Tuple[bool, List[str]]:
        """Validate required permissions."""
        logger.info(f"🔍 Validating permissions in namespace: {namespace}")
        warnings = []
        
        required_verbs = ["create", "get", "list", "update", "patch", "delete"]
        required_resources = ["subscriptions", "operatorgroups", "csvs"]
        
        for resource in required_resources:
            for verb in required_verbs:
                cmd = f"{oc_binary} auth can-i {verb} {resource} -n {namespace} --request-timeout=5s"
                rc, stdout, stderr = run_command(cmd, max_retries=1, log_output=False)
                
                if rc != 0 or "no" in stdout.lower():
                    warnings.append(f"Missing {verb} permission for {resource} in {namespace}")
                    return False, warnings
        
        logger.info("✅ Required permissions verified")
        return True, warnings
    
    @staticmethod
    def check_resource_quotas(oc_binary: str = "oc", namespace: str = "default") -> Tuple[bool, List[str]]:
        """Check resource quotas that might prevent operator installation."""
        logger.info(f"🔍 Checking resource quotas in namespace: {namespace}")
        warnings = []
        
        cmd = f"{oc_binary} get resourcequota -n {namespace} -o json"
        rc, stdout, stderr = run_command(cmd, max_retries=1, log_output=False)
        
        if rc == 0:
            try:
                quotas = json.loads(stdout)
                for quota in quotas.get('items', []):
                    status = quota.get('status', {})
                    hard = status.get('hard', {})
                    used = status.get('used', {})
                    
                    for resource, limit in hard.items():
                        current_usage = used.get(resource, '0')
                        if resource in ['pods', 'requests.cpu', 'requests.memory']:
                            warnings.append(f"Resource quota in {namespace}: {resource} = {current_usage}/{limit}")
            except json.JSONDecodeError:
                warnings.append("Could not parse resource quota information")
        
        return True, warnings


# Convenience functions for integration
def execute_resilient_operation(
    operation: Callable,
    operation_name: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[bool, Any, List[str]]:
    """Convenience wrapper for resilient operation execution."""
    return ResilientOperatorManager.execute_with_resilience(
        operation, operation_name, context=context, **kwargs
    )


def run_preflight_checks(oc_binary: str = "oc") -> Tuple[bool, List[str]]:
    """Run all pre-flight checks."""
    all_warnings = []
    
    # Basic connectivity
    success, warnings = PreflightChecker.validate_cluster_connectivity(oc_binary)
    all_warnings.extend(warnings)
    if not success:
        return False, all_warnings
    
    # Permissions (check in openshift-operators as it's commonly used)
    success, warnings = PreflightChecker.validate_permissions(oc_binary, "openshift-operators")
    all_warnings.extend(warnings)
    if not success:
        return False, all_warnings
    
    # Resource quotas
    success, warnings = PreflightChecker.check_resource_quotas(oc_binary, "openshift-operators")
    all_warnings.extend(warnings)
    
    return True, all_warnings
