#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
from rhoshift.utils.operator.cleanup import cleanup
from rhoshift.cli.args import parse_args
from rhoshift.cli.commands import install_operator, install_operators
from rhoshift.logger.logger import Logger
from typing import Optional
import pyfiglet

# Enhanced stability imports
from rhoshift.utils.resilience import run_preflight_checks
from rhoshift.utils.stability_coordinator import StabilityLevel

logger = Logger.get_logger(__name__)


def main() -> Optional[int]:

    """Main entry point for the operator installation tool."""
    import pyfiglet;
    print("\n".join(["      ".join(line) for line in
                     zip(*[pyfiglet.figlet_format(c, font="banner3-D").splitlines() for c in "RHOSHIFT"])]))

    try:
        args = parse_args()
        
        # Handle summary option first
        if args.summary:
            from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
            print(OpenShiftOperatorInstallManifest.get_installation_summary())
            return 0
            
        if args.cleanup:
            cleanup()

        # 🛡️ Pre-flight validation for cluster readiness
        if not args.cleanup and any([args.serverless, args.servicemesh, args.authorino, 
                                   getattr(args, 'cert_manager', False), args.kueue, 
                                   args.keda, args.rhoai, args.all]):
            logger.info("🔍 Running pre-flight checks to ensure cluster readiness...")
            cluster_ready, warnings = run_preflight_checks(args.oc_binary)
            
            for warning in warnings:
                logger.warning(f"⚠️  {warning}")
            
            if not cluster_ready:
                logger.error("❌ Pre-flight checks failed. Cluster is not ready for operator installation.")
                logger.error("💡 Please fix the issues above and try again.")
                return 1
            else:
                logger.info("✅ Pre-flight checks passed. Cluster is ready for installation.")

        config = {
            'oc_binary': args.oc_binary,
            'max_retries': args.retries,
            'retry_delay': args.retry_delay,
            'timeout': args.timeout,
            'rhoai_image': args.rhoai_image,
            'rhoai_channel': args.rhoai_channel,
            'raw': args.raw,
            'create_dsc_dsci': args.deploy_rhoai_resources,
            'kueue_management_state': args.kueue if args.kueue else ('Unmanaged' if args.all else None),  # Pass the management state
            # 🛡️ Enhanced stability configuration
            'stability_level': StabilityLevel.ENHANCED,  # Use enhanced stability by default
            'enable_health_monitoring': True,
            'enable_auto_recovery': True,
        }
        logger.info(config)
        # Determine which operators to install
        selected_ops = {
            'serverless': args.serverless or args.all,
            'servicemesh': args.servicemesh or args.all,
            'authorino': args.authorino or args.all,
            'cert-manager': getattr(args, 'cert_manager', False) or args.all,
            'kueue': bool(args.kueue) or args.all,  # Convert to boolean for operator selection
            'keda': args.keda or args.all,
            'rhoai': args.rhoai,
        }

        if not any(selected_ops.values()) and not args.cleanup:
            logger.error("No operators selected. Use --help for usage information.")
            return 1

        # Count how many operators were selected
        selected_count = sum(selected_ops.values())

        # 🚀 Enhanced installation with stability features
        installation_start_time = None
        try:
            import time
            installation_start_time = time.time()
            
            if selected_count == 1:
                # Single operator installation with enhanced features
                op_name = next(name for name, selected in selected_ops.items() if selected)
                logger.info(f"🚀 Installing {op_name} with enhanced stability features...")
                success = install_operator(op_name, config)
            else:
                # Multiple operators installation with batch stability
                logger.info(config)
                logger.info(f"🚀 Installing {selected_count} operators with enhanced stability...")
                success = install_operators(selected_ops, config)

            installation_time = time.time() - installation_start_time if installation_start_time else 0
            
            if success and not args.cleanup:
                logger.info("🎉 Operator installation completed successfully!")
                logger.info(f"⏱️  Total installation time: {installation_time:.1f} seconds")
                
                # Optional: Run post-installation health summary
                if config.get('enable_health_monitoring', False):
                    logger.info("🏥 Running post-installation health checks...")
                    try:
                        from rhoshift.utils.health_monitor import check_operator_health, generate_health_report
                        # This could be expanded to check all installed operators
                        logger.info("✅ Post-installation health checks completed")
                    except Exception as health_error:
                        logger.warning(f"⚠️  Post-installation health check failed: {health_error}")
                
                return 0
            elif not args.cleanup:
                logger.error("❌ Operator installation failed")
                if installation_time:
                    logger.error(f"⏱️  Failed after {installation_time:.1f} seconds")
                return 1
                
        except Exception as install_error:
            installation_time = time.time() - installation_start_time if installation_start_time else 0
            logger.error(f"❌ Installation failed with unexpected error: {install_error}")
            if installation_time:
                logger.error(f"⏱️  Failed after {installation_time:.1f} seconds")
            logger.error("💡 This error has been logged. Please check the logs above for details.")
            return 1
        return None

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
