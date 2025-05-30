import logging
import subprocess
import time
import asyncio
from typing import Tuple, Optional, Dict, Any
import sys
import threading
from dataclasses import dataclass
from enum import Enum


class CommandError(Exception):
    """Base exception for command execution errors."""
    pass


class CommandTimeoutError(CommandError):
    """Raised when a command execution times out."""
    pass


class CommandExecutionError(CommandError):
    """Raised when a command fails to execute."""
    def __init__(self, return_code: int, command: str, stdout: str, stderr: str):
        self.return_code = return_code
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"Command failed with return code {return_code}: {stderr}")


@dataclass
class CommandResult:
    """Result of a command execution."""
    return_code: int
    stdout: str
    stderr: str
    execution_time: float


class OutputMode(Enum):
    """Mode for handling command output."""
    BUFFER = "buffer"  # Collect all output in memory
    STREAM = "stream"  # Stream output in real-time
    DISCARD = "discard"  # Discard output


async def run_command_async(
        cmd: str,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        shell: bool = True,
        output_mode: OutputMode = OutputMode.BUFFER,
        log_output: bool = True,
) -> CommandResult:
    """Execute a shell command asynchronously with retries and proper error handling."""
    attempt = 0
    start_time = time.time()

    while attempt <= max_retries:
        attempt += 1
        try:
            logging.info(f"Executing command (attempt {attempt}/{max_retries}): {cmd}")

            if output_mode == OutputMode.STREAM:
                return await _run_command_streaming(cmd, timeout, cwd, env, shell, log_output, start_time)
            else:
                return await _run_command_buffered(cmd, timeout, cwd, env, shell, log_output, output_mode, start_time)

        except asyncio.TimeoutError:
            if attempt <= max_retries:
                logging.warning(f"Command timed out, retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                raise CommandTimeoutError(f"Command timed out after {timeout} seconds: {cmd}")

        except Exception as e:
            if attempt <= max_retries:
                logging.warning(f"Command failed, retrying in {retry_delay} seconds: {str(e)}")
                await asyncio.sleep(retry_delay)
            else:
                raise CommandExecutionError(-1, cmd, "", str(e))

    raise CommandExecutionError(-1, cmd, "", "Max retries exceeded")


async def _run_command_streaming(
        cmd: str,
        timeout: Optional[int],
        cwd: Optional[str],
        env: Optional[dict],
        shell: bool,
        log_output: bool,
        start_time: float,
) -> CommandResult:
    """Run command with streaming output."""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
        shell=shell
    )

    stdout_lines = []
    stderr_lines = []

    async def read_stream(stream, lines, is_stderr=False):
        while True:
            line = await stream.readline()
            if not line:
                break
            line_str = line.decode().rstrip()
            if log_output:
                logging.debug(f"{'STDERR' if is_stderr else 'STDOUT'}: {line_str}")
            lines.append(line_str)

    await asyncio.gather(
        read_stream(process.stdout, stdout_lines),
        read_stream(process.stderr, stderr_lines, True)
    )

    try:
        return_code = await asyncio.wait_for(process.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        raise CommandTimeoutError(f"Command timed out after {timeout} seconds: {cmd}")

    return CommandResult(
        return_code=return_code,
        stdout='\n'.join(stdout_lines),
        stderr='\n'.join(stderr_lines),
        execution_time=time.time() - start_time
    )


async def _run_command_buffered(
        cmd: str,
        timeout: Optional[int],
        cwd: Optional[str],
        env: Optional[dict],
        shell: bool,
        log_output: bool,
        output_mode: OutputMode,
        start_time: float,
) -> CommandResult:
    """Run command with buffered output."""
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE if output_mode != OutputMode.DISCARD else None,
            stderr=asyncio.subprocess.PIPE if output_mode != OutputMode.DISCARD else None,
            cwd=cwd,
            env=env,
            shell=shell
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        if output_mode != OutputMode.DISCARD:
            stdout_str = stdout.decode() if stdout else ""
            stderr_str = stderr.decode() if stderr else ""
            
            if log_output:
                if stdout_str:
                    logging.debug(f"STDOUT: {stdout_str.strip()}")
                if stderr_str:
                    logging.debug(f"STDERR: {stderr_str.strip()}")
        else:
            stdout_str = stderr_str = ""

        return CommandResult(
            return_code=process.returncode,
            stdout=stdout_str,
            stderr=stderr_str,
            execution_time=time.time() - start_time
        )

    except asyncio.TimeoutError:
        raise CommandTimeoutError(f"Command timed out after {timeout} seconds: {cmd}")


def run_command(
        cmd: str,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        shell: bool = True,
        log_output: bool = True,
        live_output: bool = False,
) -> Tuple[int, str, str]:
    """Synchronous wrapper for run_command_async."""
    output_mode = OutputMode.STREAM if live_output else OutputMode.BUFFER
    try:
        result = asyncio.run(run_command_async(
            cmd=cmd,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            cwd=cwd,
            env=env,
            shell=shell,
            output_mode=output_mode,
            log_output=log_output
        ))
        return result.return_code, result.stdout, result.stderr
    except CommandError as e:
        if isinstance(e, CommandExecutionError):
            return e.return_code, e.stdout, e.stderr
        raise


def apply_manifest(
        manifest_content: str,
        oc_binary: str = "oc",
        namespace: Optional[str] = None,
        context: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 10.0,
        timeout: Optional[int] = 300,
        log_output: bool = True,
        **kwargs
) -> Tuple[int, str, str]:
    """Apply a Kubernetes/OpenShift manifest with robust error handling.

    Args:
        manifest_content: String content of the manifest to apply
        oc_binary: Path to oc/kubectl binary (default: 'oc')
        namespace: Namespace to apply the manifest to
        context: Kubernetes context to use
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        timeout: Timeout in seconds for the command
        log_output: Whether to log command output
        **kwargs: Additional arguments to pass to run_command

    Returns:
        Tuple of (return_code, stdout, stderr)

    Raises:
        RuntimeError: If manifest application fails after retries
    """
    try:
        # Build base command
        cmd_parts = [oc_binary, "apply", "-f", "-"]

        if namespace:
            cmd_parts.extend(["-n", namespace])
        if context:
            cmd_parts.extend(["--context", context])

        base_cmd = " ".join(cmd_parts)
        full_cmd = f"{base_cmd} <<EOF\n{manifest_content}\nEOF"

        logging.info(f"Applying manifest (size: {len(manifest_content)} bytes)")
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"Manifest content:\n{manifest_content}")

        rc, stdout, stderr = run_command(
            full_cmd,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            log_output=log_output,
            **kwargs
        )

        if rc != 0:
            error_msg = f"Manifest application failed (rc={rc}): {stderr.strip()}"
            if "already exists" in stderr:
                logging.warning(error_msg)
            else:
                raise RuntimeError(error_msg)

        logging.info("Manifest applied successfully")
        return rc, stdout, stderr

    except Exception as e:
        logging.error(f"Failed to apply manifest: {str(e)}")
        raise RuntimeError(f"Manifest application failed: {str(e)}") from e


def wait_for_resource_for_specific_status(
        status: str,
        cmd: str,
        timeout: int = 300,
        interval: int = 5,
        case_sensitive: bool = False,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        log_output: bool = True,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        shell: bool = True
) -> Tuple[bool, str, str]:
    """
    Wait for a specific status to appear in command output.

    Args:
        status: Expected status string to wait for
        cmd: Command to execute repeatedly
        timeout: Maximum time to wait in seconds (default: 300)
        interval: Time between command executions in seconds (default: 5)
        case_sensitive: Whether status check should be case sensitive (default: False)
        max_retries: Maximum retry attempts for each command execution (passed to run_command)
        retry_delay: Delay between retries in seconds (passed to run_command)
        log_output: Whether to log command output (passed to run_command)
        cwd: Working directory for command (passed to run_command)
        env: Environment variables dictionary (passed to run_command)
        shell: Whether to run through shell (passed to run_command)

    Returns:
        Tuple of (success: bool, last_stdout: str, last_stderr: str)
    """
    start_time = time.time()
    end_time = start_time + timeout
    last_stdout = ""
    last_stderr = ""

    if not case_sensitive:
        status = status.lower()

    while time.time() < end_time:
        # Run the check command with explicit parameters
        rc, last_stdout, last_stderr = run_command(
            cmd,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=interval,  # Don't let individual commands exceed our interval
            cwd=cwd,
            env=env,
            shell=shell,
            log_output=log_output
        )

        # Check if command succeeded and contains desired status
        current_status = last_stdout if case_sensitive else last_stdout.lower()
        if rc == 0 and status == current_status.strip():
            return True, last_stdout, last_stderr

        # Log progress if we have stderr output
        if last_stderr:
            logging.info(f"Waiting for status '{status}': {last_stderr.strip()}")

        # Sleep until next check
        time.sleep(interval)

    # Timeout reached
    elapsed = time.time() - start_time
    logging.error(
        f"Timeout after {elapsed:.1f}s waiting for status '{status}'. "
        f"Last output: {last_stdout.strip()}"
    )
    return False, last_stdout, last_stderr
