"""
Comprehensive tests for rhoshift.utils.resilience module.
"""

from unittest.mock import Mock, call, patch

import pytest

from rhoshift.utils.resilience import (
    ErrorPattern,
    ErrorType,
    PreflightChecker,
    ResilientOperatorManager,
    execute_resilient_operation,
    run_preflight_checks,
)


class TestErrorCategory:
    """Test cases for ErrorCategory enum"""

    def test_error_category_values(self):
        """Test ErrorCategory enum values"""
        assert ErrorCategory.TRANSIENT.value == "transient"
        assert ErrorCategory.PERMANENT.value == "permanent"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.PERMISSION.value == "permission"
        assert ErrorCategory.RESOURCE.value == "resource"
        assert ErrorCategory.UNKNOWN.value == "unknown"

    def test_error_category_string_representation(self):
        """Test ErrorCategory string representation"""
        assert str(ErrorCategory.TRANSIENT) == "ErrorCategory.TRANSIENT"
        assert str(ErrorCategory.PERMANENT) == "ErrorCategory.PERMANENT"


class TestClassifyError:
    """Test cases for classify_error function"""

    def test_classify_transient_errors(self):
        """Test classification of transient errors"""
        transient_errors = [
            "connection timeout",
            "temporary failure",
            "resource temporarily unavailable",
            "server overloaded",
            "rate limit exceeded",
        ]

        for error in transient_errors:
            category = classify_error(error)
            assert category == ErrorCategory.TRANSIENT

    def test_classify_network_errors(self):
        """Test classification of network errors"""
        network_errors = [
            "connection refused",
            "network unreachable",
            "host unreachable",
            "DNS resolution failed",
            "connection reset",
        ]

        for error in network_errors:
            category = classify_error(error)
            assert category == ErrorCategory.NETWORK

    def test_classify_permission_errors(self):
        """Test classification of permission errors"""
        permission_errors = [
            "permission denied",
            "access denied",
            "unauthorized",
            "forbidden",
            "authentication failed",
        ]

        for error in permission_errors:
            category = classify_error(error)
            assert category == ErrorCategory.PERMISSION

    def test_classify_resource_errors(self):
        """Test classification of resource errors"""
        resource_errors = [
            "resource not found",
            "namespace does not exist",
            "insufficient resources",
            "quota exceeded",
            "out of memory",
        ]

        for error in resource_errors:
            category = classify_error(error)
            assert category == ErrorCategory.RESOURCE

    def test_classify_permanent_errors(self):
        """Test classification of permanent errors"""
        permanent_errors = [
            "syntax error",
            "invalid configuration",
            "malformed manifest",
            "version conflict",
            "immutable field",
        ]

        for error in permanent_errors:
            category = classify_error(error)
            assert category == ErrorCategory.PERMANENT

    def test_classify_unknown_errors(self):
        """Test classification of unknown errors"""
        unknown_errors = [
            "some random error message",
            "unexpected failure",
            "weird edge case error",
        ]

        for error in unknown_errors:
            category = classify_error(error)
            assert category == ErrorCategory.UNKNOWN


class TestShouldRetryError:
    """Test cases for should_retry_error function"""

    def test_should_retry_transient_errors(self):
        """Test that transient errors should be retried"""
        assert should_retry_error("connection timeout") is True
        assert should_retry_error("temporary failure") is True
        assert should_retry_error("server overloaded") is True

    def test_should_retry_network_errors(self):
        """Test that network errors should be retried"""
        assert should_retry_error("connection refused") is True
        assert should_retry_error("network unreachable") is True

    def test_should_not_retry_permanent_errors(self):
        """Test that permanent errors should not be retried"""
        assert should_retry_error("syntax error") is False
        assert should_retry_error("invalid configuration") is False
        assert should_retry_error("malformed manifest") is False

    def test_should_not_retry_permission_errors(self):
        """Test that permission errors should not be retried by default"""
        assert should_retry_error("permission denied") is False
        assert should_retry_error("unauthorized") is False

    def test_should_retry_resource_errors_conditionally(self):
        """Test that some resource errors should be retried"""
        # These might resolve themselves
        assert should_retry_error("insufficient resources") is True
        assert should_retry_error("quota exceeded") is True

        # These are permanent
        assert should_retry_error("resource not found") is False
        assert should_retry_error("namespace does not exist") is False


class TestRetryWithBackoff:
    """Test cases for retry_with_backoff function"""

    @patch("time.sleep")
    def test_retry_with_backoff_success_first_try(self, mock_sleep):
        """Test retry with backoff when operation succeeds on first try"""
        mock_operation = Mock(return_value="success")

        result = retry_with_backoff(
            mock_operation, max_retries=3, initial_delay=1, backoff_multiplier=2
        )

        assert result == "success"
        assert mock_operation.call_count == 1
        assert mock_sleep.call_count == 0

    @patch("time.sleep")
    def test_retry_with_backoff_success_after_retries(self, mock_sleep):
        """Test retry with backoff when operation succeeds after retries"""
        mock_operation = Mock(
            side_effect=[
                Exception("transient error"),
                Exception("temporary failure"),
                "success",
            ]
        )

        result = retry_with_backoff(
            mock_operation, max_retries=3, initial_delay=1, backoff_multiplier=2
        )

        assert result == "success"
        assert mock_operation.call_count == 3
        assert mock_sleep.call_count == 2

        # Verify exponential backoff
        expected_delays = [1, 2]  # 1 * 1, 1 * 2
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    @patch("time.sleep")
    def test_retry_with_backoff_permanent_failure(self, mock_sleep):
        """Test retry with backoff when operation has permanent failure"""
        mock_operation = Mock(side_effect=Exception("syntax error"))

        with pytest.raises(Exception) as excinfo:
            retry_with_backoff(
                mock_operation, max_retries=3, initial_delay=1, backoff_multiplier=2
            )

        assert "syntax error" in str(excinfo.value)
        assert mock_operation.call_count == 1  # No retries for permanent errors
        assert mock_sleep.call_count == 0

    @patch("time.sleep")
    def test_retry_with_backoff_max_retries_exceeded(self, mock_sleep):
        """Test retry with backoff when max retries are exceeded"""
        mock_operation = Mock(side_effect=Exception("connection timeout"))

        with pytest.raises(Exception) as excinfo:
            retry_with_backoff(
                mock_operation, max_retries=3, initial_delay=1, backoff_multiplier=2
            )

        assert "connection timeout" in str(excinfo.value)
        assert mock_operation.call_count == 4  # Initial + 3 retries
        assert mock_sleep.call_count == 3

    @patch("time.sleep")
    def test_retry_with_backoff_custom_parameters(self, mock_sleep):
        """Test retry with backoff with custom parameters"""
        mock_operation = Mock(side_effect=[Exception("temporary failure"), "success"])

        result = retry_with_backoff(
            mock_operation,
            max_retries=5,
            initial_delay=2,
            backoff_multiplier=3,
            max_delay=10,
        )

        assert result == "success"
        assert mock_operation.call_count == 2
        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args_list[0][0][0] == 2  # initial_delay


class TestExecuteResilientOperation:
    """Test cases for execute_resilient_operation function"""

    @patch("rhoshift.utils.resilience.retry_with_backoff")
    def test_execute_resilient_operation_success(self, mock_retry):
        """Test resilient operation execution with success"""
        mock_retry.return_value = "operation successful"

        success, result, warnings = execute_resilient_operation(
            lambda: "test operation",
            "test operation description",
            context={"test": "context"},
            max_retries=3,
        )

        assert success is True
        assert result == "operation successful"
        assert isinstance(warnings, list)
        mock_retry.assert_called_once()

    @patch("rhoshift.utils.resilience.retry_with_backoff")
    def test_execute_resilient_operation_failure(self, mock_retry):
        """Test resilient operation execution with failure"""
        mock_retry.side_effect = Exception("operation failed")

        success, result, warnings = execute_resilient_operation(
            lambda: "test operation",
            "test operation description",
            context={"test": "context"},
            max_retries=3,
        )

        assert success is False
        assert "operation failed" in str(result)
        assert isinstance(warnings, list)
        assert len(warnings) > 0

    @patch("rhoshift.utils.resilience.retry_with_backoff")
    def test_execute_resilient_operation_with_recovery(self, mock_retry):
        """Test resilient operation execution with recovery actions"""
        mock_retry.side_effect = Exception("resource not found")

        def mock_recovery_action(context, error):
            return "recovery attempted"

        success, result, warnings = execute_resilient_operation(
            lambda: "test operation",
            "test operation description",
            context={"test": "context"},
            max_retries=3,
            recovery_actions=[mock_recovery_action],
        )

        assert success is False
        assert isinstance(warnings, list)
        # Recovery was attempted
        assert any("recovery" in warning.lower() for warning in warnings)

    def test_execute_resilient_operation_context_handling(self):
        """Test resilient operation execution with context handling"""

        def test_operation():
            return "success"

        success, result, warnings = execute_resilient_operation(
            test_operation,
            "test operation",
            context={"namespace": "test-ns", "operator": "test-op"},
            max_retries=1,
        )

        assert success is True
        assert result == "success"


class TestRunPreflightChecks:
    """Test cases for run_preflight_checks function"""

    @patch("rhoshift.utils.utils.check_oc_connectivity")
    @patch("rhoshift.utils.utils.validate_oc_binary")
    @patch("rhoshift.utils.utils.run_command")
    def test_run_preflight_checks_all_pass(
        self, mock_run_command, mock_validate_oc, mock_check_connectivity
    ):
        """Test preflight checks when all checks pass"""
        mock_validate_oc.return_value = True
        mock_check_connectivity.return_value = True
        mock_run_command.side_effect = [
            (0, "cluster-admin", ""),  # whoami
            (0, "Available", ""),  # API server status
            (0, "redhat-operators", ""),  # operator sources
        ]

        ready, warnings = run_preflight_checks()

        assert ready is True
        assert isinstance(warnings, list)
        # Should have minimal warnings for a healthy cluster

    @patch("rhoshift.utils.utils.check_oc_connectivity")
    @patch("rhoshift.utils.utils.validate_oc_binary")
    def test_run_preflight_checks_oc_binary_invalid(
        self, mock_validate_oc, mock_check_connectivity
    ):
        """Test preflight checks when oc binary is invalid"""
        mock_validate_oc.return_value = False
        mock_check_connectivity.return_value = False

        ready, warnings = run_preflight_checks()

        assert ready is False
        assert len(warnings) > 0
        assert any("oc binary" in warning.lower() for warning in warnings)

    @patch("rhoshift.utils.utils.check_oc_connectivity")
    @patch("rhoshift.utils.utils.validate_oc_binary")
    def test_run_preflight_checks_no_connectivity(
        self, mock_validate_oc, mock_check_connectivity
    ):
        """Test preflight checks when there's no cluster connectivity"""
        mock_validate_oc.return_value = True
        mock_check_connectivity.return_value = False

        ready, warnings = run_preflight_checks()

        assert ready is False
        assert len(warnings) > 0
        assert any("connectivity" in warning.lower() for warning in warnings)

    @patch("rhoshift.utils.utils.check_oc_connectivity")
    @patch("rhoshift.utils.utils.validate_oc_binary")
    @patch("rhoshift.utils.utils.run_command")
    def test_run_preflight_checks_insufficient_permissions(
        self, mock_run_command, mock_validate_oc, mock_check_connectivity
    ):
        """Test preflight checks when user has insufficient permissions"""
        mock_validate_oc.return_value = True
        mock_check_connectivity.return_value = True
        mock_run_command.side_effect = [
            (0, "developer", ""),  # whoami - not admin
            (1, "", "forbidden"),  # API server status - no access
            (1, "", "permission denied"),  # operator sources - no access
        ]

        ready, warnings = run_preflight_checks()

        assert ready is False
        assert len(warnings) > 0
        assert any("permission" in warning.lower() for warning in warnings)

    @patch("rhoshift.utils.utils.check_oc_connectivity")
    @patch("rhoshift.utils.utils.validate_oc_binary")
    @patch("rhoshift.utils.utils.run_command")
    def test_run_preflight_checks_custom_oc_binary(
        self, mock_run_command, mock_validate_oc, mock_check_connectivity
    ):
        """Test preflight checks with custom oc binary"""
        mock_validate_oc.return_value = True
        mock_check_connectivity.return_value = True
        mock_run_command.return_value = (0, "success", "")

        ready, warnings = run_preflight_checks("/custom/oc")

        # Verify custom oc binary was used
        mock_validate_oc.assert_called_with("/custom/oc")
        mock_check_connectivity.assert_called_with("/custom/oc")


class TestCreateRecoveryPlan:
    """Test cases for create_recovery_plan function"""

    def test_create_recovery_plan_network_error(self):
        """Test recovery plan creation for network errors"""
        plan = create_recovery_plan(
            ErrorCategory.NETWORK,
            "connection refused",
            {"operator": "test-operator", "namespace": "test-ns"},
        )

        assert isinstance(plan, list)
        assert len(plan) > 0
        # Should include network-related recovery actions
        assert any(
            "network" in action.__name__.lower() for action in plan if callable(action)
        )

    def test_create_recovery_plan_resource_error(self):
        """Test recovery plan creation for resource errors"""
        plan = create_recovery_plan(
            ErrorCategory.RESOURCE,
            "namespace does not exist",
            {"namespace": "missing-ns"},
        )

        assert isinstance(plan, list)
        assert len(plan) > 0
        # Should include resource creation actions

    def test_create_recovery_plan_permission_error(self):
        """Test recovery plan creation for permission errors"""
        plan = create_recovery_plan(
            ErrorCategory.PERMISSION, "access denied", {"user": "test-user"}
        )

        assert isinstance(plan, list)
        # Permission errors might not have automatic recovery

    def test_create_recovery_plan_unknown_error(self):
        """Test recovery plan creation for unknown errors"""
        plan = create_recovery_plan(
            ErrorCategory.UNKNOWN, "mysterious error", {"context": "test"}
        )

        assert isinstance(plan, list)
        # Unknown errors should have generic recovery actions


class TestExecuteRecoveryAction:
    """Test cases for execute_recovery_action function"""

    @patch("rhoshift.utils.utils.run_command")
    def test_execute_recovery_action_namespace_creation(self, mock_run_command):
        """Test executing namespace creation recovery action"""
        mock_run_command.return_value = (0, "namespace created", "")

        def create_namespace_action(context, error):
            namespace = context.get("namespace", "default")
            return f"Created namespace {namespace}"

        result = execute_recovery_action(
            create_namespace_action,
            {"namespace": "test-ns"},
            "namespace does not exist",
        )

        assert "Created namespace test-ns" in result

    def test_execute_recovery_action_failure(self):
        """Test executing recovery action that fails"""

        def failing_action(context, error):
            raise Exception("Recovery failed")

        result = execute_recovery_action(
            failing_action, {"test": "context"}, "some error"
        )

        assert "Recovery failed" in result

    def test_execute_recovery_action_success(self):
        """Test executing successful recovery action"""

        def successful_action(context, error):
            return "Recovery completed successfully"

        result = execute_recovery_action(
            successful_action, {"test": "context"}, "some error"
        )

        assert result == "Recovery completed successfully"


class TestIntegrationScenarios:
    """Integration test scenarios for resilience features"""

    @patch("time.sleep")
    @patch("rhoshift.utils.utils.run_command")
    def test_resilient_operator_installation_workflow(
        self, mock_run_command, mock_sleep
    ):
        """Test complete resilient operator installation workflow"""
        # Simulate transient failure followed by success
        mock_run_command.side_effect = [
            (1, "", "connection timeout"),  # First attempt fails
            (0, "subscription created", ""),  # Second attempt succeeds
        ]

        def install_operator():
            rc, stdout, stderr = mock_run_command()
            if rc != 0:
                raise Exception(stderr)
            return stdout

        success, result, warnings = execute_resilient_operation(
            install_operator,
            "Install test operator",
            context={"operator": "test-operator", "namespace": "test-ns"},
            max_retries=3,
        )

        assert success is True
        assert result == "subscription created"
        assert mock_run_command.call_count == 2

    @patch("rhoshift.utils.utils.check_oc_connectivity")
    @patch("rhoshift.utils.utils.validate_oc_binary")
    @patch("rhoshift.utils.utils.run_command")
    def test_complete_preflight_and_recovery_workflow(
        self, mock_run_command, mock_validate_oc, mock_check_connectivity
    ):
        """Test complete preflight checks and recovery workflow"""
        # Setup successful preflight checks
        mock_validate_oc.return_value = True
        mock_check_connectivity.return_value = True
        mock_run_command.side_effect = [
            (0, "cluster-admin", ""),  # whoami
            (0, "Available", ""),  # API server
            (0, "redhat-operators", ""),  # operator sources
        ]

        # Run preflight checks
        ready, warnings = run_preflight_checks()
        assert ready is True

        # Simulate operator installation with recovery
        def operator_installation():
            # Simulate namespace missing error
            raise Exception("namespace test-ns does not exist")

        success, result, recovery_warnings = execute_resilient_operation(
            operator_installation,
            "Install operator",
            context={"operator": "test-op", "namespace": "test-ns"},
            max_retries=2,
        )

        # Should fail but attempt recovery
        assert success is False
        assert len(recovery_warnings) > 0
