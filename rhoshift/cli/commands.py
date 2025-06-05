# commands.py
import sys

sys.dont_write_bytecode = True

import logging
from typing import Dict, Any

from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller

logger = logging.getLogger(__name__)


def install_operator(op_name: str, config: Dict[str, Any]) -> bool:
    """Install a single operator with waiting."""

    operator_map = {
        'serverless': {
            'installer': OpenShiftOperatorInstaller.install_serverless_operator,
            'csv_name': 'serverless-operator',
            'namespace': 'openshift-serverless',
            'display': '🚀 Serverless Operator'
        },
        'servicemesh': {
            'installer': OpenShiftOperatorInstaller.install_service_mesh_operator,
            'csv_name': 'servicemeshoperator',
            'namespace': 'openshift-operators',
            'display': '🛡️ Service Mesh Operator'
        },
        'authorino': {
            'installer': OpenShiftOperatorInstaller.install_authorino_operator,
            'csv_name': 'authorino-operator',
            'namespace': 'openshift-operators',
            'display': '🔐 Authorino Operator'
        },
        'rhoai': {
            'installer': OpenShiftOperatorInstaller.install_rhoai_operator,
            'channel': config.get("rhoai_channel"),
            'rhoai_image': config.get("rhoai_image"),
            'raw': config.get("raw", False),
            'create_dsc_dsci': config.get("create_dsc_dsci", False),
            'csv_name': "opendatahub-operator" if config.get("rhoai_channel") == "odh-nightlies" else "rhods-operator",
            'namespace': 'opendatahub-operator' if config.get("rhoai_channel") == "odh-nightlies" else "rhods-operator",
            'display': 'ODH Operator' if config.get("rhoai_channel") == "odh-nightlies" else 'RHOAI Operator'
        },
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

        logger.warning(results[info['csv_name']]['status'])
        logger.warning(info['csv_name'])

        if results[info['csv_name']]['status'] == 'installed':
            logger.info(f"{info['display']} installed successfully")
            return True

        logger.error(f"{info['display']} failed: {results[info['csv_name']]['message']}")
        return False

    except Exception as e:
        logger.error(f"Failed to install {info['display']}: {str(e)}")
        return False


def install_operators(selected_ops: Dict[str, bool], config: Dict[str, Any]) -> bool:
    """Install multiple operators"""
    success = True
    for op_name, selected in selected_ops.items():
        if selected:
            if not install_operator(op_name, config):
                success = False
    return success

