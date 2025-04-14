#!/usr/bin/env python3
import sys

sys.dont_write_bytecode = True
import sys
from cli.args import parse_args
from cli.commands import install_operator, install_operators
from logger.logger import Logger

logger = Logger.get_logger(__name__)


def main() -> int:
    """Main entry point for the operator installation tool."""
    try:
        args = parse_args()

        config = {
            'oc_binary': args.oc_binary,
            'max_retries': args.retries,
            'retry_delay': args.retry_delay,
            'timeout': args.timeout,
            'rhoai_image': args.rhoai_image,
            'rhoai_channel': args.rhoai_channel,
            'raw':args.raw,
        }
        logger.info(config)
        # Determine which operators to install
        selected_ops = {
            'serverless': args.serverless or args.all,
            'servicemesh': args.servicemesh or args.all,
            'authorino': args.authorino or args.all,
            'rhoai': args.rhoai,
        }

        if not any(selected_ops.values()):
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

        if success:
            logger.info("Operator installation completed successfully")
            return 0

        logger.error("Operator installation failed")
        return 1

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
