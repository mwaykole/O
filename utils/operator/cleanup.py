import os
from utils.utils import run_command


def cleanup():
    script_path = os.path.join(os.path.dirname(__file__), "cleanup_all.sh")
    cmd = f"sh {script_path}"
    run_command(cmd, live_output=True , max_retries=0)