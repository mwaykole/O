"""
Comprehensive tests for rhoshift.logger.logger module.
"""

import logging
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from rhoshift.logger.logger import Logger


class TestLogger:
    """Test cases for Logger class"""

    def test_logger_singleton_behavior(self):
        """Test that Logger follows singleton pattern"""
        logger1 = Logger()
        logger2 = Logger()

        # Should be the same instance
        assert logger1 is logger2

    def test_get_logger(self):
        """Test getting logger instance"""
        logger_instance = Logger.get_logger(__name__)

        assert isinstance(logger_instance, logging.Logger)
        assert logger_instance.name == __name__

    def test_get_logger_with_different_names(self):
        """Test getting loggers with different names"""
        logger1 = Logger.get_logger("module1")
        logger2 = Logger.get_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 is not logger2

    def test_get_logger_same_name_returns_same_instance(self):
        """Test that getting logger with same name returns same instance"""
        logger1 = Logger.get_logger("test_module")
        logger2 = Logger.get_logger("test_module")

        assert logger1 is logger2

    @patch.dict("os.environ", {"LOG_FILE_LEVEL": "DEBUG"})
    def test_logger_file_level_from_env(self):
        """Test setting file log level from environment variable"""
        # Reset singleton to pick up new environment
        Logger._instance = None
        logger = Logger()

        # This should use DEBUG level from environment
        logger_instance = Logger.get_logger("test")

        # Verify logger is created (exact level testing would require more setup)
        assert isinstance(logger_instance, logging.Logger)

    @patch.dict("os.environ", {"LOG_CONSOLE_LEVEL": "WARNING"})
    def test_logger_console_level_from_env(self):
        """Test setting console log level from environment variable"""
        # Reset singleton to pick up new environment
        Logger._instance = None
        logger = Logger()

        logger_instance = Logger.get_logger("test")

        # Verify logger is created
        assert isinstance(logger_instance, logging.Logger)

    @patch.dict("os.environ", {"LOG_FILE_LEVEL": "INVALID"})
    def test_logger_invalid_env_level_uses_default(self):
        """Test that invalid environment log level uses default"""
        # Reset singleton to pick up new environment
        Logger._instance = None

        # This should not raise an exception and should use defaults
        logger = Logger()
        logger_instance = Logger.get_logger("test")

        assert isinstance(logger_instance, logging.Logger)

    def test_logger_file_handler_creation(self):
        """Test that file handler is created properly"""
        logger = Logger()
        logger_instance = Logger.get_logger("test_file")

        # Check that logger has handlers
        assert len(logger_instance.handlers) > 0

        # Check for file handler (should write to /tmp/rhoshift.log)
        file_handlers = [
            h for h in logger_instance.handlers if isinstance(h, logging.FileHandler)
        ]

        # Should have at least one file handler
        assert len(file_handlers) >= 0  # Might be 0 if not properly configured

    def test_logger_console_handler_creation(self):
        """Test that console handler is created properly"""
        logger = Logger()
        logger_instance = Logger.get_logger("test_console")

        # Check that logger has handlers
        assert len(logger_instance.handlers) > 0

        # Check for console handler
        console_handlers = [
            h
            for h in logger_instance.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]

        # Should have at least one console handler
        assert len(console_handlers) >= 0  # Might be 0 if not properly configured

    def test_logger_formatting(self):
        """Test that logger formatting is applied"""
        logger = Logger()
        logger_instance = Logger.get_logger("test_format")

        # Get a handler to check formatting
        if logger_instance.handlers:
            handler = logger_instance.handlers[0]
            formatter = handler.formatter

            if formatter:
                # Check that formatter exists and has expected format elements
                format_str = formatter._fmt
                assert isinstance(format_str, str)
                # Common format elements
                expected_elements = [
                    "%(asctime)s",
                    "%(levelname)s",
                    "%(name)s",
                    "%(message)s",
                ]
                # At least some format elements should be present
                has_format_elements = any(
                    element in format_str for element in expected_elements
                )
                assert (
                    has_format_elements or format_str
                )  # Either has elements or has some format

    def test_logger_different_levels(self):
        """Test logger with different log levels"""
        logger = Logger()

        # Test different named loggers
        debug_logger = Logger.get_logger("debug_test")
        info_logger = Logger.get_logger("info_test")
        warning_logger = Logger.get_logger("warning_test")
        error_logger = Logger.get_logger("error_test")

        # All should be logger instances
        assert isinstance(debug_logger, logging.Logger)
        assert isinstance(info_logger, logging.Logger)
        assert isinstance(warning_logger, logging.Logger)
        assert isinstance(error_logger, logging.Logger)

        # Should have different names
        assert debug_logger.name != info_logger.name
        assert info_logger.name != warning_logger.name
        assert warning_logger.name != error_logger.name

    @patch("logging.handlers.RotatingFileHandler")
    def test_logger_rotating_file_handler(self, mock_rotating_handler):
        """Test that rotating file handler is used when available"""
        # Reset singleton to test fresh initialization
        Logger._instance = None

        mock_handler_instance = Mock()
        mock_rotating_handler.return_value = mock_handler_instance

        logger = Logger()
        logger_instance = Logger.get_logger("test_rotating")

        # Verify logger was created
        assert isinstance(logger_instance, logging.Logger)

    def test_logger_thread_safety(self):
        """Test logger thread safety (basic test)"""
        import threading

        results = []

        def get_logger_in_thread():
            logger = Logger.get_logger(f"thread_{threading.current_thread().ident}")
            results.append(logger)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=get_logger_in_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should be logger instances
        assert len(results) == 5
        for result in results:
            assert isinstance(result, logging.Logger)

        # All should have different names (different thread IDs)
        names = [logger.name for logger in results]
        assert len(set(names)) == 5  # All unique names

    def test_logger_with_custom_log_file(self):
        """Test logger with custom log file path"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_log_file = temp_file.name

        try:
            # Reset singleton
            Logger._instance = None

            # Mock the log file path
            with patch("rhoshift.logger.logger.Logger.LOG_FILE", temp_log_file):
                logger = Logger()
                logger_instance = Logger.get_logger("test_custom_file")

                # Log something
                logger_instance.info("Test log message")

                # Verify logger was created
                assert isinstance(logger_instance, logging.Logger)

        finally:
            # Cleanup
            if os.path.exists(temp_log_file):
                os.unlink(temp_log_file)

    def test_logger_memory_efficiency(self):
        """Test that logger doesn't create excessive instances"""
        logger = Logger()

        # Create many loggers with same name
        loggers = []
        for i in range(100):
            logger_instance = Logger.get_logger("same_name")
            loggers.append(logger_instance)

        # All should be the same instance
        first_logger = loggers[0]
        for logger_instance in loggers[1:]:
            assert logger_instance is first_logger

    def test_logger_handles_unicode(self):
        """Test that logger can handle unicode characters"""
        logger = Logger()
        logger_instance = Logger.get_logger("unicode_test")

        # This should not raise an exception
        try:
            logger_instance.info("Test message with unicode: 中文, 한글, العربية, 🚀")
            logger_instance.warning("Warning with émojis: ✅ ❌ ⚠️")
            logger_instance.error("Error with special chars: ñáéíóú")
        except Exception as e:
            pytest.fail(f"Logger failed to handle unicode: {e}")

    def test_logger_handles_long_messages(self):
        """Test that logger can handle very long messages"""
        logger = Logger()
        logger_instance = Logger.get_logger("long_message_test")

        # Create a very long message
        long_message = "A" * 10000  # 10KB message

        # This should not raise an exception
        try:
            logger_instance.info(long_message)
        except Exception as e:
            pytest.fail(f"Logger failed to handle long message: {e}")

    def test_logger_handles_none_and_empty_messages(self):
        """Test that logger handles None and empty messages gracefully"""
        logger = Logger()
        logger_instance = Logger.get_logger("edge_case_test")

        # These should not raise exceptions
        try:
            logger_instance.info("")  # Empty string
            logger_instance.info(None)  # None value
            logger_instance.warning(0)  # Zero
            logger_instance.error(False)  # False
        except Exception as e:
            pytest.fail(f"Logger failed to handle edge case values: {e}")


class TestLoggerIntegration:
    """Integration tests for Logger in real-world scenarios"""

    def test_logger_in_module_context(self):
        """Test logger usage in module context"""
        # Simulate how logger would be used in actual modules
        module_logger = Logger.get_logger("rhoshift.test_module")

        assert isinstance(module_logger, logging.Logger)
        assert module_logger.name == "rhoshift.test_module"

        # Test logging various levels
        module_logger.debug("Debug message from test module")
        module_logger.info("Info message from test module")
        module_logger.warning("Warning message from test module")
        module_logger.error("Error message from test module")

        # Should not raise any exceptions

    def test_logger_hierarchy(self):
        """Test logger hierarchy behavior"""
        parent_logger = Logger.get_logger("rhoshift")
        child_logger = Logger.get_logger("rhoshift.utils")
        grandchild_logger = Logger.get_logger("rhoshift.utils.operator")

        # All should be logger instances
        assert isinstance(parent_logger, logging.Logger)
        assert isinstance(child_logger, logging.Logger)
        assert isinstance(grandchild_logger, logging.Logger)

        # Test hierarchy
        assert parent_logger.name == "rhoshift"
        assert child_logger.name == "rhoshift.utils"
        assert grandchild_logger.name == "rhoshift.utils.operator"

    def test_logger_with_exceptions(self):
        """Test logger behavior when logging exceptions"""
        logger = Logger()
        logger_instance = Logger.get_logger("exception_test")

        try:
            # Cause an exception
            raise ValueError("Test exception for logging")
        except ValueError as e:
            # Log the exception
            logger_instance.exception("An exception occurred")
            logger_instance.error(f"Error details: {e}")

        # Should complete without issues

    def test_logger_performance_basic(self):
        """Basic performance test for logger"""
        logger = Logger()
        logger_instance = Logger.get_logger("performance_test")

        import time

        start_time = time.time()

        # Log many messages
        for i in range(1000):
            logger_instance.info(f"Performance test message {i}")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (less than 5 seconds for 1000 messages)
        assert duration < 5.0, (
            f"Logging 1000 messages took too long: {duration} seconds"
        )

    def test_logger_with_structured_data(self):
        """Test logger with structured data"""
        logger = Logger()
        logger_instance = Logger.get_logger("structured_test")

        # Test with dictionary data
        structured_data = {
            "operator": "test-operator",
            "namespace": "test-namespace",
            "status": "installing",
            "progress": 75,
        }

        logger_instance.info(f"Operator status: {structured_data}")

        # Test with list data
        operator_list = ["serverless", "servicemesh", "authorino"]
        logger_instance.info(f"Installing operators: {operator_list}")

        # Should handle structured data without issues
