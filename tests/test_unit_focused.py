"""
Focused unit tests for rhoshift package with proper mocking.
This test suite focuses on unit testing individual functions and classes
without hitting external dependencies like the OpenShift cluster.
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestArgumentParsing:
    """Test argument parsing functionality"""

    def test_str_to_bool_function(self):
        """Test str_to_bool utility function"""
        from rhoshift.cli.args import str_to_bool

        # Test true values
        assert str_to_bool("yes") is True
        assert str_to_bool("true") is True
        assert str_to_bool("1") is True
        assert str_to_bool(True) is True

        # Test false values
        assert str_to_bool("no") is False
        assert str_to_bool("false") is False
        assert str_to_bool("0") is False
        assert str_to_bool(False) is False

        # Test invalid values
        with pytest.raises(Exception):
            str_to_bool("invalid")

    def test_parse_args_serverless(self):
        """Test parsing serverless operator arguments"""
        from rhoshift.cli.args import parse_args

        with patch("sys.argv", ["script.py", "--serverless"]):
            args = parse_args()
            assert args.serverless is True
            assert args.oc_binary == "oc"

    def test_parse_args_all_operators(self):
        """Test parsing all operators arguments"""
        from rhoshift.cli.args import parse_args, select_operators

        with patch("sys.argv", ["script.py", "--all"]):
            args = parse_args()
            selected = select_operators(args)

            assert args.all is True
            assert all(selected.values())  # All operators should be selected

    def test_build_config_basic(self):
        """Test basic configuration building"""
        from rhoshift.cli.args import build_config, parse_args

        with patch("sys.argv", ["script.py", "--timeout", "600"]):
            args = parse_args()
            config = build_config(args)

            assert config["timeout"] == 600
            assert config["oc_binary"] == "oc"
            assert isinstance(config, dict)


class TestConstants:
    """Test constants and configuration functionality"""

    def test_operator_config_dataclass(self):
        """Test OperatorConfig dataclass functionality"""
        from rhoshift.utils.constants import OperatorConfig

        config = OperatorConfig(
            name="test-operator",
            display_name="Test Operator",
            namespace="test-namespace",
            channel="stable",
        )

        assert config.name == "test-operator"
        assert config.display_name == "Test Operator"
        assert config.namespace == "test-namespace"
        assert config.channel == "stable"

    def test_operator_list_functionality(self):
        """Test operator listing functionality"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest

        operators = OpenShiftOperatorInstallManifest.list_operators()
        assert isinstance(operators, list)
        assert len(operators) > 0
        assert "serverless-operator" in operators

    def test_manifest_generation_basic(self):
        """Test basic manifest generation"""
        from rhoshift.utils.constants import get_dsc_manifest, get_dsci_manifest

        # Test DSCI manifest
        dsci = get_dsci_manifest()
        assert "DSCInitialization" in dsci
        assert "default-dsci" in dsci

        # Test DSC manifest
        dsc = get_dsc_manifest()
        assert "DataScienceCluster" in dsc
        assert "default-dsc" in dsc

    def test_wait_time_constants(self):
        """Test WaitTime constants"""
        from rhoshift.utils.constants import WaitTime

        assert WaitTime.WAIT_TIME_10_MIN == 600
        assert WaitTime.WAIT_TIME_5_MIN == 300
        assert WaitTime.WAIT_TIME_1_MIN == 60
        assert WaitTime.WAIT_TIME_30_SEC == 30


class TestHealthMonitoring:
    """Test health monitoring enums and classes"""

    def test_health_status_enum(self):
        """Test HealthStatus enum values"""
        from rhoshift.utils.health_monitor import HealthStatus

        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_resource_type_enum(self):
        """Test ResourceType enum values"""
        from rhoshift.utils.health_monitor import ResourceType

        assert ResourceType.OPERATOR_CSV.value == "csv"
        assert ResourceType.SUBSCRIPTION.value == "subscription"
        assert ResourceType.DEPLOYMENT.value == "deployment"

    def test_health_check_dataclass(self):
        """Test HealthCheck dataclass"""
        from rhoshift.utils.health_monitor import HealthCheck, ResourceType

        check = HealthCheck(
            name="test-check",
            resource_type=ResourceType.POD,
            namespace="test-namespace",
        )

        assert check.name == "test-check"
        assert check.resource_type == ResourceType.POD
        assert check.namespace == "test-namespace"


class TestStabilityCoordinator:
    """Test stability coordinator functionality"""

    def test_stability_level_enum(self):
        """Test StabilityLevel enum"""
        from rhoshift.utils.stability_coordinator import StabilityLevel

        assert StabilityLevel.BASIC.value == 1
        assert StabilityLevel.ENHANCED.value == 2
        assert StabilityLevel.COMPREHENSIVE.value == 3

    def test_stability_config_creation(self):
        """Test StabilityConfig creation"""
        from rhoshift.utils.stability_coordinator import StabilityConfig, StabilityLevel

        config = StabilityConfig(level=StabilityLevel.ENHANCED)
        assert config.level == StabilityLevel.ENHANCED
        assert isinstance(config.max_retries, int)
        assert isinstance(config.timeout, int)

    def test_stability_coordinator_initialization(self):
        """Test StabilityCoordinator initialization"""
        from rhoshift.utils.stability_coordinator import (
            StabilityConfig,
            StabilityCoordinator,
        )

        config = StabilityConfig()
        coordinator = StabilityCoordinator(config)

        assert coordinator.config == config
        assert coordinator.oc_binary == "oc"


class TestEnhancedOperator:
    """Test enhanced operator functionality"""

    def test_enhanced_operator_initialization(self):
        """Test EnhancedOpenShiftOperatorInstaller initialization"""
        from rhoshift.utils.operator.enhanced_operator import (
            EnhancedOpenShiftOperatorInstaller,
        )
        from rhoshift.utils.stability_coordinator import StabilityLevel

        installer = EnhancedOpenShiftOperatorInstaller()

        assert installer.stability_config.level == StabilityLevel.ENHANCED
        assert installer.oc_binary == "oc"
        assert hasattr(installer, "coordinator")

    @patch("rhoshift.utils.utils.run_command")
    def test_validate_dsci_compatibility_no_rhoai(self, mock_run_command):
        """Test DSCI validation when RHOAI is not selected"""
        from rhoshift.utils.operator.enhanced_operator import (
            EnhancedOpenShiftOperatorInstaller,
        )

        selected_ops = {"serverless": True, "rhoai": False}
        config = {"rhoai_channel": "stable"}

        compatible, warnings = (
            EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
                selected_ops, config
            )
        )

        assert compatible is True
        assert warnings == []
        mock_run_command.assert_not_called()


class TestUtilityFunctions:
    """Test utility functions with proper mocking"""

    @patch("subprocess.run")
    def test_run_command_success(self, mock_subprocess):
        """Test run_command with successful execution"""
        from rhoshift.utils.utils import run_command

        # Mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        rc, stdout, stderr = run_command("echo test")

        assert rc == 0
        assert stdout == "test output"
        assert stderr == ""

    @patch("subprocess.run")
    def test_run_command_failure(self, mock_subprocess):
        """Test run_command with failed execution"""
        from rhoshift.utils.utils import run_command

        # Mock subprocess failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "command failed"
        mock_subprocess.return_value = mock_result

        rc, stdout, stderr = run_command("false")

        assert rc == 1
        assert stdout == ""
        assert stderr == "command failed"


class TestMainFunctionFlow:
    """Test main function flow with proper mocking"""

    def test_main_no_operators_selected(self):
        """Test main when no operators are selected"""
        from rhoshift.main import main

        with patch("sys.argv", ["script.py"]):
            result = main()

        assert result == 1  # Should return error code

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    @patch("rhoshift.cli.commands.install_operator")
    def test_main_single_operator_mocked(self, mock_install, mock_preflight):
        """Test main function with single operator - fully mocked"""
        mock_preflight.return_value = (True, [])
        mock_install.return_value = True

        from rhoshift.main import main

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 0
        mock_install.assert_called_once()

    @patch("rhoshift.utils.operator.cleanup.cleanup_all_operators")
    def test_main_cleanup_function(self, mock_cleanup):
        """Test main function cleanup"""
        mock_cleanup.return_value = None

        from rhoshift.main import main

        with patch("sys.argv", ["script.py", "--cleanup"]):
            result = main()

        assert result is None
        mock_cleanup.assert_called_once()


class TestOperatorInstaller:
    """Test operator installer functionality"""

    def test_get_operator_configs(self):
        """Test getting operator configurations"""
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller

        configs = OpenShiftOperatorInstaller.get_operator_configs()

        assert isinstance(configs, dict)
        assert len(configs) > 0
        assert "serverless-operator" in configs

        # Check structure
        for operator_name, config in configs.items():
            assert "manifest" in config
            assert "namespace" in config
            assert "display_name" in config


class TestLogging:
    """Test logging functionality"""

    def test_logger_creation(self):
        """Test logger creation"""
        from rhoshift.logger.logger import Logger

        logger = Logger.get_logger(__name__)
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_logger_singleton(self):
        """Test logger singleton behavior"""
        from rhoshift.logger.logger import Logger

        logger1 = Logger()
        logger2 = Logger()

        # Should be same instance (singleton)
        assert logger1 is logger2


class TestResilientOperations:
    """Test resilient operations"""

    def test_execute_resilient_operation_basic(self):
        """Test basic resilient operation execution"""
        from rhoshift.utils.resilience import execute_resilient_operation

        def mock_operation():
            return "success"

        success, result, warnings = execute_resilient_operation(
            mock_operation, "test operation"
        )

        assert success is True
        assert result == "success"
        assert isinstance(warnings, list)

    def test_execute_resilient_operation_failure(self):
        """Test resilient operation with failure"""
        from rhoshift.utils.resilience import execute_resilient_operation

        def failing_operation():
            raise Exception("operation failed")

        success, result, warnings = execute_resilient_operation(
            failing_operation, "failing operation", max_retries=1
        )

        assert success is False
        assert isinstance(result, Exception) or "failed" in str(result)
        assert isinstance(warnings, list)


class TestDSCIValidation:
    """Test DSCI validation functionality"""

    @patch("rhoshift.utils.utils.run_command")
    def test_dsci_compatibility_check_no_rhoai(self, mock_run_command):
        """Test DSCI compatibility when RHOAI not selected"""
        from rhoshift.utils.operator.enhanced_operator import (
            EnhancedOpenShiftOperatorInstaller,
        )

        selected_ops = {"serverless": True, "rhoai": False}
        config = {}

        compatible, warnings = (
            EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
                selected_ops, config
            )
        )

        assert compatible is True
        assert warnings == []
        mock_run_command.assert_not_called()

    @patch("rhoshift.utils.utils.run_command")
    def test_dsci_compatibility_check_no_existing_dsci(self, mock_run_command):
        """Test DSCI compatibility when no existing DSCI"""
        from rhoshift.utils.operator.enhanced_operator import (
            EnhancedOpenShiftOperatorInstaller,
        )

        mock_run_command.return_value = (0, "NOT_FOUND", "")

        selected_ops = {"rhoai": True}
        config = {"rhoai_channel": "stable"}

        compatible, warnings = (
            EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
                selected_ops, config
            )
        )

        assert compatible is True
        assert warnings == []


class TestConfigurationWorkflow:
    """Test complete configuration workflow"""

    def test_complete_config_workflow(self):
        """Test complete argument parsing to configuration workflow"""
        from rhoshift.cli.args import build_config, parse_args, select_operators

        with patch(
            "sys.argv",
            [
                "script.py",
                "--serverless",
                "--rhoai",
                "--oc-binary",
                "/custom/oc",
                "--timeout",
                "600",
            ],
        ):
            args = parse_args()
            config = build_config(args)
            selected = select_operators(args)

        # Verify parsing
        assert args.serverless is True
        assert args.rhoai is True
        assert args.oc_binary == "/custom/oc"
        assert args.timeout == 600

        # Verify config building
        assert config["oc_binary"] == "/custom/oc"
        assert config["timeout"] == 600

        # Verify operator selection
        assert selected["serverless"] is True
        assert selected["rhoai"] is True
        assert selected["servicemesh"] is False


class TestManifestGeneration:
    """Test manifest generation without cluster dependencies"""

    def test_dsci_manifest_basic(self):
        """Test basic DSCI manifest generation"""
        from rhoshift.utils.constants import get_dsci_manifest

        manifest = get_dsci_manifest()

        # Check basic structure
        assert "apiVersion: dscinitialization.opendatahub.io/v1" in manifest
        assert "kind: DSCInitialization" in manifest
        assert "name: default-dsci" in manifest
        assert "applicationsNamespace:" in manifest
        assert "monitoring:" in manifest

    def test_dsc_manifest_with_kueue(self):
        """Test DSC manifest generation with Kueue"""
        from rhoshift.utils.constants import get_dsc_manifest

        manifest = get_dsc_manifest(kueue_management_state="Managed")

        assert "DataScienceCluster" in manifest
        assert "kueue:" in manifest
        assert "managementState: Managed" in manifest

    def test_operator_manifest_generation(self):
        """Test operator manifest generation"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest

        manifest_gen = OpenShiftOperatorInstallManifest()
        manifest = manifest_gen.generate_operator_manifest("serverless-operator")

        assert "Subscription" in manifest
        assert "serverless-operator" in manifest
        assert "stable" in manifest


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_invalid_operator_config(self):
        """Test handling of invalid operator configuration"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest

        with pytest.raises(ValueError):
            OpenShiftOperatorInstallManifest.get_operator_config("invalid-operator")

    def test_empty_operator_selection(self):
        """Test handling of empty operator selection"""
        from rhoshift.cli.args import parse_args, select_operators

        with patch("sys.argv", ["script.py"]):  # No operators selected
            args = parse_args()
            selected = select_operators(args)

        # All should be False/None
        assert not any(selected.values())

    def test_dependency_resolution(self):
        """Test dependency resolution functionality"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest

        # Kueue should include cert-manager dependency
        resolved = OpenShiftOperatorInstallManifest.resolve_dependencies(
            ["kueue-operator"]
        )

        assert "kueue-operator" in resolved
        assert "openshift-cert-manager-operator" in resolved
        # Dependency should come first
        cert_manager_index = resolved.index("openshift-cert-manager-operator")
        kueue_index = resolved.index("kueue-operator")
        assert cert_manager_index < kueue_index


class TestMockedInstallations:
    """Test installations with proper mocking to avoid cluster calls"""

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_operator"
    )
    def test_individual_operator_install_methods(self, mock_install):
        """Test individual operator installation methods"""
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller

        mock_install.return_value = (0, "Installation successful", "")

        # Test each operator installation method
        operators_to_test = [
            ("install_serverless_operator", "serverless-operator"),
            ("install_servicemeshoperator", "servicemeshoperator"),
            ("install_authorino_operator", "authorino-operator"),
            (
                "install_openshift_cert_manager_operator",
                "openshift-cert-manager-operator",
            ),
            ("install_kueue_operator", "kueue-operator"),
            (
                "install_openshift_custom_metrics_autoscaler_operator",
                "openshift-custom-metrics-autoscaler-operator",
            ),
        ]

        for method_name, expected_operator in operators_to_test:
            if hasattr(OpenShiftOperatorInstaller, method_name):
                method = getattr(OpenShiftOperatorInstaller, method_name)
                rc, stdout, stderr = method()

                assert rc == 0
                assert stderr == ""

                # Verify correct operator was passed to install_operator
                mock_install.assert_called_with(expected_operator)

        # Should have called install_operator once for each method tested
        assert mock_install.call_count == len(operators_to_test)

    @patch(
        "rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller.install_operator_with_stability"
    )
    def test_enhanced_operator_install_methods(self, mock_install):
        """Test enhanced operator installation methods"""
        from rhoshift.utils.operator.enhanced_operator import (
            EnhancedOpenShiftOperatorInstaller,
        )

        mock_install.return_value = (0, "Enhanced installation successful", "")

        # Test enhanced serverless installation
        rc, stdout, stderr = (
            EnhancedOpenShiftOperatorInstaller.install_serverless_operator_enhanced()
        )

        assert rc == 0
        assert stderr == ""
        mock_install.assert_called_once_with("serverless-operator")


class TestLoggerFunctionality:
    """Test logger functionality"""

    def test_logger_get_logger(self):
        """Test getting logger instances"""
        from rhoshift.logger.logger import Logger

        logger1 = Logger.get_logger("test1")
        logger2 = Logger.get_logger("test2")
        logger3 = Logger.get_logger("test1")  # Same name as logger1

        assert logger1.name == "test1"
        assert logger2.name == "test2"
        assert logger3.name == "test1"

        # Same name should return same instance
        assert logger1 is logger3
        assert logger1 is not logger2

    def test_logger_basic_functionality(self):
        """Test basic logger functionality"""
        from rhoshift.logger.logger import Logger

        logger = Logger.get_logger("test_logger")

        # These should not raise exceptions
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.debug("Test debug message")


class TestImportValidation:
    """Validate that all modules can be imported successfully"""

    def test_all_core_imports(self):
        """Test that all core modules can be imported"""
        # Main entry points
        from rhoshift.cli.args import parse_args
        from rhoshift.cli.commands import install_operator

        # Logger
        from rhoshift.logger.logger import Logger
        from rhoshift.main import main

        # Utils
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        from rhoshift.utils.health_monitor import HealthStatus
        from rhoshift.utils.operator.enhanced_operator import (
            EnhancedOpenShiftOperatorInstaller,
        )

        # Operators
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller
        from rhoshift.utils.resilience import execute_resilient_operation
        from rhoshift.utils.stability_coordinator import StabilityLevel
        from rhoshift.utils.utils import run_command

        # All imports should succeed
        assert all(
            [
                main,
                parse_args,
                install_operator,
                OpenShiftOperatorInstallManifest,
                run_command,
                HealthStatus,
                execute_resilient_operation,
                StabilityLevel,
                OpenShiftOperatorInstaller,
                EnhancedOpenShiftOperatorInstaller,
                Logger,
            ]
        )

    def test_package_structure(self):
        """Test package structure integrity"""
        import rhoshift
        import rhoshift.cli
        import rhoshift.logger
        import rhoshift.utils
        import rhoshift.utils.operator

        # All package modules should be importable
        assert rhoshift is not None
        assert rhoshift.cli is not None
        assert rhoshift.utils is not None
        assert rhoshift.utils.operator is not None
        assert rhoshift.logger is not None
