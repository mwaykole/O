# commands.py
import sys

sys.dont_write_bytecode = True

import logging
from typing import Dict, Any

from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller
# Enhanced stability imports
from rhoshift.utils.operator.enhanced_operator import EnhancedOpenShiftOperatorInstaller
from rhoshift.utils.stability_coordinator import StabilityLevel

logger = logging.getLogger(__name__)


def install_operator(op_name: str, config: Dict[str, Any]) -> bool:
    """Install a single operator with enhanced stability features."""
    
    # 🛡️ Critical operators that benefit from enhanced stability
    enhanced_operators = {
        'keda': EnhancedOpenShiftOperatorInstaller.install_keda_operator_enhanced,
        'rhoai': EnhancedOpenShiftOperatorInstaller.install_rhoai_operator_enhanced,
        'serverless': EnhancedOpenShiftOperatorInstaller.install_serverless_operator_enhanced,
    }
    
    # Use enhanced installer for critical operators  
    stability_level = config.get('stability_level', StabilityLevel.ENHANCED)
    if op_name in enhanced_operators and stability_level.value >= StabilityLevel.ENHANCED.value:
        logger.info(f"🛡️  Using enhanced stability installer for {op_name}")
        try:
            rc, stdout, stderr = enhanced_operators[op_name](**config)
            if rc == 0:
                logger.info(f"✅ Enhanced installation of {op_name} completed successfully")
                return True
            else:
                logger.error(f"❌ Enhanced installation of {op_name} failed: {stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ Enhanced installation of {op_name} failed with error: {e}")
            return False
    
    # Get dynamic operator mapping from optimized constants
    def get_operator_map():
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        
        operator_map = {}
        
        # Map from CLI names to operator keys and method names
        cli_to_operator_config = {
            'serverless': ('serverless-operator', 'install_serverless_operator'),
            'servicemesh': ('servicemeshoperator', 'install_service_mesh_operator'), 
            'authorino': ('authorino-operator', 'install_authorino_operator'),
            'cert-manager': ('openshift-cert-manager-operator', 'install_cert_manager_operator'),
            'kueue': ('kueue-operator', 'install_kueue_operator'),
            'keda': ('openshift-custom-metrics-autoscaler-operator', 'install_keda_operator')
        }
        
        # Build dynamic operator map
        for cli_name, (op_key, method_name) in cli_to_operator_config.items():
            try:
                op_config = OpenShiftOperatorInstallManifest.get_operator_config(op_key)
                
                # Define display icons
                icons = {
                    'serverless': '🚀',
                    'servicemesh': '🛡️',
                    'authorino': '🔐',
                    'cert-manager': '🔐',
                    'kueue': '📋',
                    'keda': '📊'
                }
                
                operator_map[cli_name] = {
                    'installer': getattr(OpenShiftOperatorInstaller, method_name),
                    'csv_name': op_config.name,
                    'namespace': op_config.namespace,
                    'display': f"{icons.get(cli_name, '⚙️')} {op_config.display_name}",
                    'op_key': op_key,
                    'config': op_config
                }
            except (AttributeError, ValueError) as e:
                logger.warning(f"Skipping {cli_name}: {e}")
        
        return operator_map
    
    operator_map = get_operator_map()
    
    # Add validation for single operator
    if op_name in operator_map:
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        warnings = OpenShiftOperatorInstallManifest.validate_operator_compatibility([operator_map[op_name]['op_key']])
        for warning in warnings:
            logger.warning(f"⚠️  {warning}")
    
    # Special handling for RHOAI (different pattern)
    operator_map['rhoai'] = {
        'installer': OpenShiftOperatorInstaller.install_rhoai_operator,
        'channel': config.get("rhoai_channel"),
        'rhoai_image': config.get("rhoai_image"),
        'raw': config.get("raw", False),
        'create_dsc_dsci': config.get("create_dsc_dsci", False),
        'csv_name': "opendatahub-operator" if config.get("rhoai_channel") == "odh-nightlies" else "rhods-operator",
        'namespace': 'opendatahub-operators' if config.get("rhoai_channel") == "odh-nightlies" else "redhat-ods-operator",
        'display': '🤖 ODH Operator' if config.get("rhoai_channel") == "odh-nightlies" else '🤖 RHOAI Operator'
    }
    if op_name not in operator_map:
        raise ValueError(f"Unknown operator: {op_name}")

    info = operator_map[op_name]
    logger.info(f"{info['display']} installation started...")

    try:
        # Install the operator
        info['installer'](**config)
        # Wait for installation
        results = OpenShiftOperatorInstaller.wait_for_operator(
            operator_name=info['csv_name'],
            namespace=info['namespace'],
            oc_binary=config.get('oc_binary', 'oc'),
            timeout=config.get('timeout', 600),
            interval=2
        )

        if results.get(info['csv_name'], {}).get('status') == 'installed':
            logger.info(f"{info['display']} installed successfully")
            success = True
        else:
            logger.error(f"Installation of {info['display']} failed")
            success = False

    except Exception as e:
        logger.error(f"Failed to install {info['display']}: {e}")
        success = False

    logger.warning("installed" if success else "failed")
    logger.warning(info['csv_name'])

    return success


def install_operators(selected_ops: Dict[str, bool], config: Dict[str, Any]) -> bool:
    """Install multiple operators with enhanced batch stability and dependency resolution"""
    # Get selected operator names
    selected_operator_names = [op_name for op_name, selected in selected_ops.items() if selected]
    
    if not selected_operator_names:
        logger.warning("No operators selected for installation")
        return True
    
    # 🛡️ Enhanced batch installation with stability features
    stability_level = config.get('stability_level', StabilityLevel.ENHANCED)
    if stability_level.value >= StabilityLevel.ENHANCED.value and len(selected_operator_names) > 1:
        logger.info(f"🛡️  Using enhanced batch installation with {stability_level.name.lower()} stability")
        try:
            from rhoshift.utils.operator.enhanced_operator import install_operators_with_enhanced_stability
            return install_operators_with_enhanced_stability(selected_ops, config)
        except Exception as e:
            logger.warning(f"⚠️  Enhanced batch installation failed, falling back to standard: {e}")
            # Fall through to standard installation
    
    # Map CLI names to operator keys for validation
    from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
    
    cli_to_operator_key = {
        'serverless': 'serverless-operator',
        'servicemesh': 'servicemeshoperator', 
        'authorino': 'authorino-operator',
        'cert-manager': 'openshift-cert-manager-operator',
        'kueue': 'kueue-operator',
        'keda': 'openshift-custom-metrics-autoscaler-operator'
    }
    
    # Get operator keys for validation (exclude RHOAI as it has different pattern)
    operator_keys = []
    for op_name in selected_operator_names:
        if op_name in cli_to_operator_key:
            operator_keys.append(cli_to_operator_key[op_name])
    
    # Validate batch compatibility and resolve dependencies
    if operator_keys:
        warnings = OpenShiftOperatorInstallManifest.validate_operator_compatibility(operator_keys)
        if warnings:
            logger.warning("⚠️  Batch installation compatibility warnings:")
            for warning in warnings:
                logger.warning(f"   - {warning}")
        
        # Resolve dependencies and get installation order
        resolved_order = OpenShiftOperatorInstallManifest.resolve_dependencies(operator_keys)
        
        # Add any missing dependencies to selected_ops
        reverse_cli_map = {v: k for k, v in cli_to_operator_key.items()}
        for op_key in resolved_order:
            if op_key in reverse_cli_map:
                cli_name = reverse_cli_map[op_key]
                if cli_name not in selected_operator_names:
                    logger.info(f"📦 Auto-adding dependency: {cli_name}")
                    selected_ops[cli_name] = True
                    selected_operator_names.append(cli_name)
        
        # Create ordered installation list
        ordered_cli_names = []
        for op_key in resolved_order:
            if op_key in reverse_cli_map:
                ordered_cli_names.append(reverse_cli_map[op_key])
        
        # Add RHOAI at the end if selected (special case)
        if selected_ops.get('rhoai', False):
            ordered_cli_names.append('rhoai')
    else:
        ordered_cli_names = selected_operator_names
    
    logger.info(f"Installing {len(ordered_cli_names)} operators in order: {' → '.join(ordered_cli_names)}")
    
    # Install operators in dependency order
    success = True
    for op_name in ordered_cli_names:
        if selected_ops.get(op_name, False):
            logger.info(f"🚀 Installing operator: {op_name}")
            if not install_operator(op_name, config):
                success = False
                logger.error(f"❌ Failed to install {op_name}")
                break  # Stop on first failure
            else:
                logger.info(f"✅ Successfully installed {op_name}")
    
    return success

