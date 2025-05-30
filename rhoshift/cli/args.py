import argparse
import sys
from typing import Dict, Any


def parse_args() -> argparse.Namespace:
    """Parse and return command line arguments"""
    parser = argparse.ArgumentParser(description="OpenShift Operator Installation Tool")

    # Operator selection
    operators = parser.add_argument_group("Operator Selection")
    operators.add_argument("--serverless", action="store_true",
                           help="Install Serverless Operator")
    operators.add_argument("--servicemesh", action="store_true",
                           help="Install Service Mesh Operator")
    operators.add_argument("--authorino", action="store_true",
                           help="Install Authorino Operator")
    operators.add_argument("--rhoai", action="store_true",
                           help="Install RHOArawI Operator")
    operators.add_argument("--all", action="store_true",
                           help="Install all operators")
    operators.add_argument("--cleanup", action="store_true",
                           help="clean up all RHOAI, serverless , servishmesh , Authorino Operator ")
    operators.add_argument("--deploy-rhoai-resources",
                           action="store_true", help="creates dsc and dsci")

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
    config.add_argument("--raw", default=False, type=str,
                        help="True if install raw else False")
    config.add_argument("--rhoai-image", required='--rhoai' in sys.argv, type=str,
                        default="quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.20-nightly",
                        help="rhoai image eg: quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.20-nightly")

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
            'rhoai': True
        }

    return {
        'serverless': args.serverless,
        'servicemesh': args.servicemesh,
        'authorino': args.authorino,
        'rhoai': args.rhoai
    }
