#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from utils.operator.cleanup import cleanup
from cli.args import parse_args
from cli.commands import install_operator, install_operators
from logger.logger import Logger
from typing import Optional

logger = Logger.get_logger(__name__)


def main() -> Optional[int]:

    """Main entry point for the operator installation tool."""
    def display_large_banner():
        banner = r"""
           OOOOOOOOO     
         OO:::::::::OO   
       OO:::::::::::::OO 
      O:::::::OOO:::::::O
      O::::::O   O::::::O
      O:::::O     O:::::O
      O:::::O     O:::::O
      O::::::O   O::::::O
      O:::::::OOO:::::::O
       OO:::::::::::::OO 
         OO:::::::::OO   
           OOOOOOOOO     
        """
        print(banner.center(50))

    display_large_banner()
    try:
        args = parse_args()
        if args.cleanup:
            cleanup()

        config = {
            'oc_binary': args.oc_binary,
            'max_retries': args.retries,
            'retry_delay': args.retry_delay,
            'timeout': args.timeout,
            'rhoai_image': args.rhoai_image,
            'rhoai_channel': args.rhoai_channel,
            'raw': args.raw,
            'create_dsc_dsci': args.deploy_rhoai_resources,
        }
        logger.info(config)
        # Determine which operators to install
        selected_ops = {
            'serverless': args.serverless or args.all,
            'servicemesh': args.servicemesh or args.all,
            'authorino': args.authorino or args.all,
            'rhoai': args.rhoai,
        }

        if not any(selected_ops.values()) and not args.cleanup:
            logger.error("No operators selected. Use --help for usage information.")
            return 1

        # Count how many operators were selected
        selected_count = sum(selected_ops.values())

        if selected_count == 1:
            # Single operator installation
            op_name = next(name for name, selected in selected_ops.items() if selected)
            success = install_operator(op_name, config)
        else:
            # Multiple operators installation
            logger.info(config)
            logger.info(f"Installing {selected_count} operators...")
            success = install_operators(selected_ops, config)

        if success and not args.cleanup:
            logger.info("Operator installation completed successfully")
            return 0
        if not args.cleanup:
            logger.error("Operator installation failed")
            return 1
        return None

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
