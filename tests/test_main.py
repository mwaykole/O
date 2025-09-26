"""
Comprehensive tests for rhoshift.main module.
"""

import sys
from unittest.mock import Mock, patch

import pytest

from rhoshift.main import main
from rhoshift.utils.stability_coordinator import StabilityLevel


class TestMainFunction:
    """Test cases for main function"""

    def test_main_no_operators_selected(self):
        """Test main function when no operators are selected"""
        with patch("sys.argv", ["script.py"]):
            result = main()
            assert result == 1  # Should return error code

    @patch("rhoshift.cli.commands.install_operator")
    def test_main_single_operator_success(self, mock_install):
        """Test main function with a single operator - success"""
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 0  # Should return success code
        mock_install.assert_called_once()

        # Verify the config passed to install_operator
        call_args = mock_install.call_args
        operator_name = call_args[0][0]
        config = call_args[0][1]

        assert operator_name == "serverless"
        assert config["oc_binary"] == "oc"
        assert config["stability_level"] == StabilityLevel.ENHANCED

    @patch("rhoshift.cli.commands.install_operator")
    def test_main_single_operator_failure(self, mock_install):
        """Test main function with a single operator - failure"""
        mock_install.return_value = False

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 1  # Should return error code
        mock_install.assert_called_once()

    @patch("rhoshift.cli.commands.install_operators")
    def test_main_multiple_operators_success(self, mock_install):
        """Test main function with multiple operators - success"""
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless", "--rhoai"]):
            result = main()

        assert result == 0  # Should return success code
        mock_install.assert_called_once()

        # Verify the arguments passed to install_operators
        call_args = mock_install.call_args
        selected_ops = call_args[0][0]
        config = call_args[0][1]

        assert selected_ops["serverless"] is True
        assert selected_ops["rhoai"] is True
        assert selected_ops["servicemesh"] is False
        assert config["stability_level"] == StabilityLevel.ENHANCED

    @patch("rhoshift.cli.commands.install_operators")
    def test_main_multiple_operators_failure(self, mock_install):
        """Test main function with multiple operators - failure"""
        mock_install.return_value = False

        with patch("sys.argv", ["script.py", "--serverless", "--servicemesh"]):
            result = main()

        assert result == 1  # Should return error code
        mock_install.assert_called_once()

    @patch("rhoshift.utils.operator.cleanup.cleanup_all_operators")
    def test_main_cleanup_success(self, mock_cleanup):
        """Test main function with cleanup flag - success"""
        mock_cleanup.return_value = None

        with patch("sys.argv", ["script.py", "--cleanup"]):
            result = main()

        assert result is None  # Cleanup should return None
        mock_cleanup.assert_called_once()

    @patch("rhoshift.utils.operator.cleanup.cleanup_all_operators")
    def test_main_cleanup_exception(self, mock_cleanup):
        """Test main function with cleanup flag - exception"""
        mock_cleanup.side_effect = Exception("Cleanup failed")

        with patch("sys.argv", ["script.py", "--cleanup"]):
            result = main()

        assert result == 1  # Should return error code
        mock_cleanup.assert_called_once()

    @patch("rhoshift.cli.commands.install_operators")
    def test_main_all_operators(self, mock_install):
        """Test main function with --all flag"""
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--all"]):
            result = main()

        assert result == 0
        mock_install.assert_called_once()

        # Verify all operators are selected
        call_args = mock_install.call_args
        selected_ops = call_args[0][0]

        assert selected_ops["serverless"] is True
        assert selected_ops["servicemesh"] is True
        assert selected_ops["authorino"] is True
        assert selected_ops["cert-manager"] is True
        assert selected_ops["kueue"] is True
        assert selected_ops["keda"] is True
        assert selected_ops["rhoai"] is True

    @patch("rhoshift.cli.commands.install_operator")
    def test_main_exception_handling(self, mock_install):
        """Test main function exception handling"""
        mock_install.side_effect = Exception("Unexpected error")

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 1  # Should return error code

    @patch("rhoshift.utils.operator.cleanup.cleanup_all_operators")
    @patch("rhoshift.cli.commands.install_operators")
    def test_main_cleanup_and_install(self, mock_install, mock_cleanup):
        """Test main function with both cleanup and installation"""
        mock_cleanup.return_value = None
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--cleanup", "--serverless"]):
            result = main()

        # Cleanup should be called first
        mock_cleanup.assert_called_once()
        # Then installation should be called
        mock_install.assert_called_once()
        # Return value should be from installation (0 for success)
        assert result == 0

    @patch("rhoshift.utils.operator.cleanup.cleanup_all_operators")
    @patch("rhoshift.cli.commands.install_operators")
    def test_main_cleanup_fails_but_install_succeeds(self, mock_install, mock_cleanup):
        """Test main function when cleanup fails but installation succeeds"""
        mock_cleanup.side_effect = Exception("Cleanup failed")
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--cleanup", "--serverless"]):
            result = main()

        # Should return error code due to cleanup failure
        assert result == 1
        mock_cleanup.assert_called_once()
        # Installation should not be attempted after cleanup failure
        mock_install.assert_not_called()


class TestMainConfigurationParsing:
    """Test cases for configuration parsing in main function"""

    @patch("rhoshift.cli.commands.install_operator")
    def test_main_custom_oc_binary(self, mock_install):
        """Test main function with custom oc binary"""
        mock_install.return_value = True

        with patch(
            "sys.argv", ["script.py", "--serverless", "--oc-binary", "/custom/oc"]
        ):
            result = main()

        assert result == 0

        # Verify custom oc binary is in config
        call_args = mock_install.call_args
        config = call_args[0][1]
        assert config["oc_binary"] == "/custom/oc"

    @patch("rhoshift.cli.commands.install_operator")
    def test_main_custom_retry_settings(self, mock_install):
        """Test main function with custom retry settings"""
        mock_install.return_value = True

        with patch(
            "sys.argv",
            [
                "script.py",
                "--serverless",
                "--retries",
                "5",
                "--retry-delay",
                "20",
                "--timeout",
                "600",
            ],
        ):
            result = main()

        assert result == 0

        # Verify custom settings are in config
        call_args = mock_install.call_args
        config = call_args[0][1]
        assert config["max_retries"] == 5
        assert config["retry_delay"] == 20
        assert config["timeout"] == 600

    @patch("rhoshift.cli.commands.install_operators")
    def test_main_rhoai_configuration(self, mock_install):
        """Test main function with RHOAI-specific configuration"""
        mock_install.return_value = True

        test_image = "quay.io/rhoai/test-image:latest"
        with patch(
            "sys.argv",
            [
                "script.py",
                "--rhoai",
                "--rhoai-channel",
                "odh-nightlies",
                "--rhoai-image",
                test_image,
                "--raw",
                "True",
                "--deploy-rhoai-resources",
            ],
        ):
            result = main()

        assert result == 0

        # Verify RHOAI configuration
        call_args = mock_install.call_args
        selected_ops = call_args[0][0]
        config = call_args[0][1]

        assert selected_ops["rhoai"] is True
        assert config["rhoai_channel"] == "odh-nightlies"
        assert config["rhoai_image"] == test_image
        assert config["raw"] == "True"  # String, not boolean
        assert config["create_dsc_dsci"] is True

    @patch("rhoshift.cli.commands.install_operators")
    def test_main_kueue_configuration(self, mock_install):
        """Test main function with Kueue configuration"""
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--kueue", "Managed"]):
            result = main()

        assert result == 0

        # Verify Kueue configuration
        call_args = mock_install.call_args
        selected_ops = call_args[0][0]
        config = call_args[0][1]

        assert selected_ops["kueue"] == "Managed"
        assert config["kueue_management_state"] == "Managed"

    @patch("rhoshift.cli.commands.install_operators")
    def test_main_kueue_default_configuration(self, mock_install):
        """Test main function with Kueue default configuration"""
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--kueue"]):  # No value provided
            result = main()

        assert result == 0

        # Verify Kueue default configuration
        call_args = mock_install.call_args
        selected_ops = call_args[0][0]
        config = call_args[0][1]

        assert selected_ops["kueue"] == "Unmanaged"  # Default value
        assert config["kueue_management_state"] == "Unmanaged"

    @patch("rhoshift.cli.commands.install_operators")
    def test_main_verbose_logging(self, mock_install):
        """Test main function with verbose logging"""
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless", "--verbose"]):
            result = main()

        assert result == 0
        # The verbose flag affects logging but doesn't change the config passed to operators
        mock_install.assert_called_once()


class TestMainPreflightChecks:
    """Test cases for preflight checks in main function"""

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    @patch("rhoshift.cli.commands.install_operator")
    def test_main_preflight_checks_success(self, mock_install, mock_preflight):
        """Test main function with successful preflight checks"""
        mock_preflight.return_value = (True, [])
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 0
        mock_preflight.assert_called_once()
        mock_install.assert_called_once()

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    @patch("rhoshift.cli.commands.install_operator")
    def test_main_preflight_checks_failure(self, mock_install, mock_preflight):
        """Test main function with failed preflight checks"""
        mock_preflight.return_value = (False, ["Cluster not ready"])

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 1  # Should fail before installation
        mock_preflight.assert_called_once()
        mock_install.assert_not_called()  # Should not attempt installation

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    @patch("rhoshift.cli.commands.install_operator")
    def test_main_preflight_checks_with_warnings(self, mock_install, mock_preflight):
        """Test main function with preflight warnings but success"""
        mock_preflight.return_value = (True, ["Warning: limited resources"])
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 0  # Should succeed despite warnings
        mock_preflight.assert_called_once()
        mock_install.assert_called_once()


class TestMainComplexScenarios:
    """Test cases for complex main function scenarios"""

    @patch("rhoshift.utils.operator.cleanup.cleanup_all_operators")
    @patch("rhoshift.cli.commands.install_operators")
    def test_main_complex_rhoai_with_cleanup(self, mock_install, mock_cleanup):
        """Test main function with cleanup, all operators, and RHOAI-specific flags"""
        mock_cleanup.return_value = None
        mock_install.return_value = True

        test_image = "quay.io/rhoai/test-image:latest"
        with patch(
            "sys.argv",
            [
                "script.py",
                "--cleanup",
                "--all",
                "--rhoai-channel",
                "odh-nightlies",
                "--rhoai-image",
                test_image,
                "--raw",
                "False",
                "--deploy-rhoai-resources",
                "--kueue",
                "Managed",
            ],
        ):
            result = main()

        # Verify cleanup was called
        mock_cleanup.assert_called_once()

        # Verify operator installation was attempted with correct config
        mock_install.assert_called_once()
        call_args = mock_install.call_args
        selected_ops = call_args[0][0]
        config = call_args[0][1]

        # Verify all operators were selected (due to --all)
        assert all(selected_ops.values())

        # Verify RHOAI-specific configuration
        assert config["rhoai_channel"] == "odh-nightlies"
        assert config["rhoai_image"] == test_image
        assert config["raw"] == "False"
        assert config["create_dsc_dsci"] is True
        assert config["kueue_management_state"] == "Managed"

        # Verify return value
        assert result == 0  # Should return success

    @patch("rhoshift.cli.commands.install_operators")
    @patch("time.time")
    def test_main_timing_measurement(self, mock_time, mock_install):
        """Test main function timing measurement"""
        mock_time.side_effect = [1000.0, 1120.5]  # Start and end times
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless", "--servicemesh"]):
            result = main()

        assert result == 0
        mock_install.assert_called_once()
        # Timing should be measured (120.5 seconds in this mock)

    @patch("rhoshift.cli.commands.install_operators")
    def test_main_health_monitoring_configuration(self, mock_install):
        """Test main function with health monitoring configuration"""
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 0

        # Verify health monitoring is enabled in config
        call_args = mock_install.call_args
        config = call_args[0][1]
        assert config["enable_health_monitoring"] is True
        assert config["enable_auto_recovery"] is True

    def test_main_summary_flag(self):
        """Test main function with summary flag"""
        with patch("sys.argv", ["script.py", "--summary"]):
            with patch(
                "rhoshift.utils.constants.OpenShiftOperatorInstallManifest"
            ) as mock_manifest:
                mock_manifest.list_operators.return_value = ["serverless-operator"]
                mock_manifest.get_operator_config.return_value = Mock(
                    display_name="Test Operator",
                    channel="stable",
                    namespace="test-namespace",
                )

                result = main()

        # Summary should be displayed and function should exit
        assert result is None

    @patch("rhoshift.cli.commands.install_operator")
    def test_main_single_operator_edge_cases(self, mock_install):
        """Test main function single operator edge cases"""
        mock_install.return_value = True

        # Test each individual operator
        operators = ["serverless", "servicemesh", "authorino", "cert-manager", "keda"]

        for operator in operators:
            with patch("sys.argv", ["script.py", f"--{operator}"]):
                result = main()

            assert result == 0

        # Should have been called once for each operator
        assert mock_install.call_count == len(operators)


class TestMainErrorHandling:
    """Test cases for error handling in main function"""

    def test_main_invalid_arguments(self):
        """Test main function with invalid arguments"""
        # argparse should handle this and raise SystemExit
        with patch("sys.argv", ["script.py", "--invalid-argument"]):
            with pytest.raises(SystemExit):
                main()

    @patch("rhoshift.cli.commands.install_operator")
    def test_main_post_installation_health_check_failure(self, mock_install):
        """Test main function when post-installation health check fails"""
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless"]):
            with patch(
                "rhoshift.utils.health_monitor.check_operator_health"
            ) as mock_health:
                mock_health.side_effect = Exception("Health check failed")

                result = main()

        # Should still succeed even if health check fails
        assert result == 0

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    def test_main_preflight_check_exception(self, mock_preflight):
        """Test main function when preflight check raises exception"""
        mock_preflight.side_effect = Exception("Preflight check error")

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        # Should handle exception gracefully
        assert result == 1
