"""Upgrade matrix functionality."""
import os
import logging
from typing import Dict, Any

from utils.utils import run_command

logger = logging.getLogger(__name__)

def validate_config(config: Dict[str, Any]) -> None:
    """Validate the upgrade matrix configuration.
    
    Args:
        config: Dictionary containing upgrade matrix configuration
    
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    required_keys = ['from_version', 'from_channel', 'to_version', 'to_channel']
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")

def run_upgrade_matrix(config: Dict[str, Any]) -> bool:
    """Run the upgrade matrix test.
    
    Args:
        config: Dictionary containing upgrade matrix configuration
            Required keys:
            - from_version: Source version
            - from_channel: Source channel
            - to_version: Target version
            - to_channel: Target channel
            Optional keys:
            - scenarios: List of scenarios to run
            - skip_cleanup: Whether to skip cleanup
            - from_image: Custom source image
            - to_image: Custom target image
    
    Returns:
        bool: True if upgrade matrix completed successfully, False otherwise
    """
    try:
        # Validate configuration
        validate_config(config)
        
        # Get the directory of the current script
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        matrix_script = os.path.join(current_dir, "utils", "upgrade", "run_upgrade_matrix.sh")
        
        # Verify script exists
        if not os.path.exists(matrix_script):
            raise FileNotFoundError(f"Upgrade matrix script not found at: {matrix_script}")
        
        # Verify script is executable
        if not os.access(matrix_script, os.X_OK):
            raise PermissionError(f"Upgrade matrix script is not executable: {matrix_script}")
        
        # Build the command
        cmd_parts = [matrix_script]
        
        # Add scenario if specified
        if config.get('scenarios'):
            for scenario in config['scenarios']:
                cmd_parts.extend(['-s', scenario])
        
        # Add skip cleanup if specified
        if config.get('skip_cleanup'):
            cmd_parts.append('--skip-cleanup')
        
        # Add custom images if specified
        if config.get('from_image'):
            cmd_parts.extend(['--from-image', config['from_image']])
        if config.get('to_image'):
            cmd_parts.extend(['--to-image', config['to_image']])
        
        # Add version and channel arguments
        cmd_parts.extend([
            config['from_version'],
            config['from_channel'],
            config['to_version'],
            config['to_channel']
        ])
        
        # Join command parts into a single string
        cmd = ' '.join(cmd_parts)
        
        # Run the script using run_command
        logger.info(f"Running upgrade matrix with command: {cmd}")
        return_code, stdout, stderr = run_command(
            cmd,
            max_retries=config.get('max_retries', 3),
            retry_delay=config.get('retry_delay', 10.0),
            timeout=config.get('timeout', 300),
            log_output=True,
            live_output=True  # Show live output for better visibility
        )
        
        if return_code != 0:
            logger.error(f"Upgrade matrix failed with exit code {return_code}")
            if stderr:
                logger.error(f"Error output: {stderr}")
            return False
            
        logger.info("Upgrade matrix completed successfully")
        return True
        
    except ValueError as e:
        logger.error(f"Invalid configuration: {str(e)}")
        return False
    except FileNotFoundError as e:
        logger.error(str(e))
        return False
    except PermissionError as e:
        logger.error(str(e))
        return False
    except Exception as e:
        logger.error(f"Failed to run upgrade matrix: {str(e)}")
        return False 