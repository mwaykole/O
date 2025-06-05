import os
import sys
import pkg_resources
from rhoshift.utils.utils import run_command


def cleanup():
    """Execute the cleanup script."""
    try:
        # Try to get the script from package data
        script_path = pkg_resources.resource_filename('rhoshift', 'scripts/cleanup/cleanup_all.sh')
        
        # If not found in package data, try the project root
        if not os.path.exists(script_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            script_path = os.path.join(project_root, "scripts", "cleanup", "cleanup_all.sh")
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Cleanup script not found at {script_path}")
        
        # Make the script executable
        os.chmod(script_path, 0o755)
        
        # Execute the script
        cmd = f"sh {script_path} "
        run_command(cmd, live_output=True, max_retries=0)
        
    except Exception as e:
        raise RuntimeError(f"Failed to execute cleanup script: {str(e)}")