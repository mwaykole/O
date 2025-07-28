#!/usr/bin/env python3
import sys
import os
import logging
try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files
from rhoshift.utils.utils import run_command

# Configure logging
logger = logging.getLogger(__name__)


def find_script():
    """Locate the run_upgrade_matrix.sh script using multiple methods."""
    try:
        # 1. First try using importlib.resources (modern approach)
        try:
            import rhoshift
            script_files = files(rhoshift) / "scripts" / "run_upgrade_matrix.sh"
            if script_files.is_file():
                # For importlib.resources, we need to extract to a temporary location
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
                    temp_file.write(script_files.read_text())
                    os.chmod(temp_file.name, 0o755)
                    return temp_file.name
        except Exception as e:
            logger.debug(f"importlib.resources approach failed: {str(e)}")

        # 2. Fallback for development environment
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        script_path = os.path.join(base_path, 'scripts', 'run_upgrade_matrix.sh')
        if os.path.exists(script_path):
            return script_path

        # 3. Check in rhoshift package directory (for editable installs)
        rhoshift_script_path = os.path.join(base_path, 'rhoshift', 'scripts', 'run_upgrade_matrix.sh')
        if os.path.exists(rhoshift_script_path):
            return rhoshift_script_path

    except Exception as e:
        logger.debug(f"Error while locating script: {str(e)}")

    return None


def run_upgrade_matrix():
    """Execute the upgrade matrix shell script."""
    script_path = find_script()

    if not script_path or not os.path.exists(script_path):
        logger.error("Could not locate run_upgrade_matrix.sh script")
        logger.error("Searched in:")
        logger.error("1. Package resources (rhoshift/scripts/)")
        logger.error("2. Project root (scripts/)")
        return 1

    try:
        # Make script executable
        os.chmod(script_path, 0o755)

        # Prepare command
        args = " ".join(sys.argv[1:])
        logger.info(f"Executing upgrade matrix with arguments: {args}")
        cmd = f"bash {script_path} {args}"

        # Execute command
        return_code, stdout, stderr = run_command(
            cmd,
            live_output=True,
            max_retries=0
        )

        if return_code != 0:
            logger.error(f"Script failed with exit code {return_code}")
            if stderr:
                logger.error(stderr)
        else:
            logger.info("Upgrade matrix completed successfully")
            if stdout:
                logger.info(stdout)

        return return_code

    except Exception as e:
        logger.error(f"Failed to execute upgrade matrix: {str(e)}")
        return 1


def main():
    """Entry point for the run-upgrade-matrix command."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return run_upgrade_matrix()


if __name__ == "__main__":
    sys.exit(main())
