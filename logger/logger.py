import logging
import sys
import os
from functools import wraps
from typing import Optional, Callable, Any
from pathlib import Path


class Logger:
    """
    A comprehensive logging utility with these features:
    - Default logs to test.log with DEBUG level
    - Console logs with INFO level
    - Automatic log rotation
    - Function call logging decorator
    - Environment variable configuration
    - Thread-safe operations
    """

    _configured = False
    _default_log_file = 'test.log'
    _max_log_size = 5 * 1024 * 1024  # 5MB
    _backup_count = 3

    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """Get a configured logger instance.

        Args:
            name: Logger name (usually __name__)

        Returns:
            Configured logger instance
        """
        if not cls._configured:
            cls._configure_root_logger()
            cls._configured = True
        return logging.getLogger(name)

    @classmethod
    def _configure_root_logger(cls) -> None:
        """Configure the root logger with file and console handlers."""
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Create logs directory if it doesn't exist
        log_path = Path(cls._get_log_file())
        log_path.parent.mkdir(exist_ok=True, parents=True)

        # Formatter with colored levels if available
        formatter = cls._create_formatter()

        # File handler with rotation
        file_handler = cls._create_file_handler(log_path, formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = cls._create_console_handler(formatter)
        logger.addHandler(console_handler)

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
                filename=log_path,
                maxBytes=cls._max_log_size,
                backupCount=cls._backup_count,
                encoding='utf-8'
            )
        except ImportError:
            handler = logging.FileHandler(
                filename=log_path,
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
    def _get_log_file(cls) -> str:
        """Get the log file path from environment or default."""
        return os.getenv('LOG_FILE', cls._default_log_file)

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
        if cls._configured:
            cls.get_logger(__name__).warning("Logger already configured, settings not applied")
            return

        if default_log_file:
            cls._default_log_file = default_log_file
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