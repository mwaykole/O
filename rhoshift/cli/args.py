import argparse
import sys
from typing import Dict, Any


def str_to_bool(v):
    """Convert string to boolean value."""
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def parse_args() -> argparse.Namespace:
    """Parse and return command line arguments"""
    parser = argparse.ArgumentParser(description="OpenShift Operator Installation Tool")

    # Operator Selection
    operator_group = parser.add_argument_group('Operator Selection')
    operator_group.add_argument('--serverless', action='store_true', help='Install Serverless Operator')
    operator_group.add_argument('--servicemesh', action='store_true', help='Install Service Mesh Operator')
    operator_group.add_argument('--authorino', action='store_true', help='Install Authorino Operator')
    operator_group.add_argument('--cert-manager', action='store_true', help='Install cert-manager Operator (latest v1.16.1)')
    operator_group.add_argument('--rhoai', action='store_true', help='Install RHOArawI Operator')
    operator_group.add_argument('--kueue', nargs='?', const='Unmanaged', choices=['Managed', 'Unmanaged'], 
                                help='Install Kueue Operator with specified managementState in DSC (default: Unmanaged if no value provided)')
    operator_group.add_argument('--keda', action='store_true', help='Install KEDA (Custom Metrics Autoscaler) Operator')
    operator_group.add_argument('--all', action='store_true', help='Install all operators')
    operator_group.add_argument('--cleanup', action='store_true', help='clean up all RHOAI, serverless , servishmesh , Authorino Operator')
    operator_group.add_argument('--deploy-rhoai-resources', action='store_true', help='creates dsc and dsci')
    operator_group.add_argument('--summary', action='store_true', help='Show detailed summary of all supported operators and their versions')

    # Configuration options
    config = parser.add_argument_group("Configuration")
    config.add_argument("--oc-binary", default="oc",
                        help="Path to oc CLI (default: oc)")
    config.add_argument("--retries", type=int, default=3,
                        help="Max retry attempts (default: 3)")
    config.add_argument("--retry-delay", type=int, default=10,
                        help="Delay between retries in seconds (default: 10)")
    config.add_argument("--timeout", type=int, default=300,
                        help="Command timeout in seconds (default: 300)")
    config.add_argument("--rhoai-channel", default='stable', type=str,
                        help="rhoai channel fast OR stable")
    config.add_argument("--raw", default=False, type=str_to_bool,
                        help="True if install raw else False")
    config.add_argument("--rhoai-image", required='--rhoai' in sys.argv, type=str,
                        default="quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.25-nightly",
                        help="rhoai image eg: quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.25-nightly")

    # Output control
    output = parser.add_argument_group("Output Control")
    output.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging")

    return parser.parse_args()


def build_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Convert parsed args to operator config dictionary"""
    return {
        'oc_binary': args.oc_binary,
        'max_retries': args.retries,
        'retry_delay': args.retry_delay,
        'timeout': args.timeout,
        'rhoai_image': args.rhoai_image,
        'rhoai_channel': args.rhoai_channel,
        'raw': args.raw,
    }


def select_operators(args: argparse.Namespace) -> Dict[str, bool]:
    """Determine which operators to install based on args"""
    if args.all:
        return {
            'serverless': True,
            'servicemesh': True,
            'authorino': True,
            'cert-manager': True,
            'rhoai': True,
            'kueue': True,
            'keda': True
        }

    return {
        'serverless': args.serverless,
        'servicemesh': args.servicemesh,
        'authorino': args.authorino,
        'cert-manager': getattr(args, 'cert_manager', False),  # Handle hyphen to underscore conversion
        'rhoai': args.rhoai,
        'kueue': args.kueue,
        'keda': args.keda
    }
