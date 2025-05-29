import logging
import sys
import os
from functools import wraps
from typing import Optional, Callable, Any
from pathlib import Path


class Logger:
    """
    A comprehensive logging utility with these features:
    - Default logs to /tmp/rhoshift.log with DEBUG level
    - Console logs with INFO level
    - Automatic log rotation
    - Function call logging decorator
    - Environment variable configuration
    - Thread-safe operations
    """

    _logger: Optional[logging.Logger] = None
    _max_log_size = 10 * 1024 * 1024  # 10MB
    _backup_count = 5
    _log_dir = Path("/tmp")
    _log_file = _log_dir / "rhoshift.log"

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger instance."""
        if cls._logger is None:
            cls._setup_logger()
        return logging.getLogger(name)

    @classmethod
    def _setup_logger(cls) -> None:
        """Set up the root logger with file and console handlers."""
        # Create formatter
        formatter = cls._create_formatter()

        # Create handlers
        try:
            file_handler = cls._create_file_handler(cls._log_file, formatter)
            console_handler = cls._create_console_handler(formatter)
        except Exception as e:
            print(f"Warning: Could not set up log handlers: {e}", file=sys.stderr)
            return

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        cls._logger = root_logger

    @classmethod
    def _create_formatter(cls) -> logging.Formatter:
        """Create log formatter with optional color support."""
        try:
            from colorlog import ColoredFormatter
            return ColoredFormatter(
                '%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                reset=True,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        except ImportError:
            return logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

    @classmethod
    def _create_file_handler(cls, log_path: Path, formatter: logging.Formatter) -> logging.Handler:
        """Create configured file handler with rotation."""
        try:
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                filename=str(log_path),  # Convert Path to string
                maxBytes=cls._max_log_size,
                backupCount=cls._backup_count,
                encoding='utf-8'
            )
        except ImportError:
            handler = logging.FileHandler(
                filename=str(log_path),  # Convert Path to string
                encoding='utf-8'
            )

        handler.setLevel(os.getenv('LOG_FILE_LEVEL', 'DEBUG'))
        handler.setFormatter(formatter)
        return handler

    @classmethod
    def _create_console_handler(cls, formatter: logging.Formatter) -> logging.Handler:
        """Create configured console handler."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(os.getenv('LOG_CONSOLE_LEVEL', 'INFO'))
        handler.setFormatter(formatter)
        return handler

    @classmethod
    def configure(
            cls,
            default_log_file: Optional[str] = None,
            max_log_size: Optional[int] = None,
            backup_count: Optional[int] = None,
            console_level: Optional[str] = None,
            file_level: Optional[str] = None
    ) -> None:
        """Configure logger settings before first use.

        Args:
            default_log_file: Path to log file
            max_log_size: Max log size in bytes before rotation
            backup_count: Number of backup logs to keep
            console_level: Console log level (DEBUG, INFO, etc.)
            file_level: File log level
        """
        if cls._logger:
            cls.get_logger(__name__).warning("Logger already configured, settings not applied")
            return

        if default_log_file:
            cls._log_file = Path(default_log_file)
        if max_log_size:
            cls._max_log_size = max_log_size
        if backup_count:
            cls._backup_count = backup_count
        if console_level:
            os.environ['LOG_CONSOLE_LEVEL'] = console_level
        if file_level:
            os.environ['LOG_FILE_LEVEL'] = file_level

    @classmethod
    def log_call(cls, level: int = logging.DEBUG) -> Callable:
        """Decorator to log function entry and exit.

        Args:
            level: Logging level to use for call messages

        Returns:
            Function decorator
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                logger = cls.get_logger(func.__module__)
                logger.log(level, f"→ Entering {func.__name__}")
                try:
                    result = func(*args, **kwargs)
                    logger.log(level, f"← Exiting {func.__name__}")
                    return result
                except Exception as e:
                    logger.exception(f"⚠ Error in {func.__name__}: {str(e)}")
                    raise

            return wrapper

        return decorator


# Initialize logging when module is imported
Logger.get_logger(__name__).debug("Logger module initialized")