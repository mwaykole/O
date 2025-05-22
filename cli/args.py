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

    # Upgrade Matrix options
    upgrade = parser.add_argument_group("Upgrade Matrix")
    upgrade.add_argument("--run-matrix", nargs=4, metavar=('FROM_VERSION', 'FROM_CHANNEL', 'TO_VERSION', 'TO_CHANNEL'),
                        help="Run upgrade matrix test. Example: --run-matrix 2.20 stable 2.19 fast")
    upgrade.add_argument("--scenario", action="append", choices=['serverless', 'rawdeployment', 'serverless,rawdeployment'],
                        help="Specific scenario(s) to run in upgrade matrix")
    upgrade.add_argument("--skip-cleanup", action="store_true",
                        help="Skip cleanup before each scenario in upgrade matrix")
    upgrade.add_argument("--from-image", type=str,
                        help="Custom source image path for upgrade matrix")
    upgrade.add_argument("--to-image", type=str,
                        help="Custom target image path for upgrade matrix")

    # Output control
    output = parser.add_argument_group("Output Control")
    output.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging")

    return parser.parse_args()


def build_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Convert parsed args to operator config dictionary"""
    config = {
        'oc_binary': args.oc_binary,
        'max_retries': args.retries,
        'retry_delay': args.retry_delay,
        'timeout': args.timeout,
        'rhoai_image': args.rhoai_image,
        'rhoai_channel': args.rhoai_channel,
        'raw': args.raw,
    }

    # Add upgrade matrix configuration if --run-matrix is used
    if args.run_matrix:
        from_version, from_channel, to_version, to_channel = args.run_matrix
        config.update({
            'from_version': from_version,
            'from_channel': from_channel,
            'to_version': to_version,
            'to_channel': to_channel,
            'scenarios': args.scenario,
            'skip_cleanup': args.skip_cleanup,
            'from_image': args.from_image,
            'to_image': args.to_image
        })

    return config


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
