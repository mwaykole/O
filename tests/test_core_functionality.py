"""
Core functionality tests for rhoshift package.
This test suite focuses on the main functionality and integration points.
"""

# Standard library imports
import sys
from unittest.mock import Mock, call, patch

from rhoshift.cli.args import build_config, parse_args, select_operators
from rhoshift.cli.commands import install_operator, install_operators
from rhoshift.logger.logger import Logger

# Local application imports
from rhoshift.main import main
from rhoshift.utils.constants import (
    OpenShiftOperatorInstallManifest,
    get_dsc_manifest,
    get_dsci_manifest,
)
from rhoshift.utils.health_monitor import HealthStatus, check_operator_health
from rhoshift.utils.operator.enhanced_operator import EnhancedOpenShiftOperatorInstaller
from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller
from rhoshift.utils.resilience import execute_resilient_operation, run_preflight_checks
from rhoshift.utils.stability_coordinator import (
    StabilityConfig,
    StabilityCoordinator,
    StabilityLevel,
)
from rhoshift.utils.utils import apply_manifest, run_command


class TestCoreImports:
    """Test that all core modules can be imported"""

    def test_import_main_modules(self):
        """Test importing main modules"""
        # These should not raise ImportError

        assert callable(main)
        assert callable(parse_args)
        assert callable(build_config)
        assert callable(select_operators)
        assert callable(install_operator)
        assert callable(install_operators)

    def test_import_utils_modules(self):
        """Test importing utils modules"""

        # Verify main classes and functions exist
        assert OpenShiftOperatorInstallManifest is not None
        assert callable(get_dsci_manifest)
        assert callable(get_dsc_manifest)
        assert callable(run_command)
        assert callable(apply_manifest)
        assert HealthStatus is not None
        assert callable(check_operator_health)
        assert callable(execute_resilient_operation)
        assert callable(run_preflight_checks)
        assert StabilityLevel is not None
        assert StabilityConfig is not None
        assert StabilityCoordinator is not None

    def test_import_operator_modules(self):
        """Test importing operator modules"""

        assert OpenShiftOperatorInstaller is not None
        assert EnhancedOpenShiftOperatorInstaller is not None


class TestEndToEndWorkflow:
    """End-to-end workflow tests with mocking"""

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_operator"
    )
    def test_single_operator_installation_workflow(self, mock_install):
        """Test complete single operator installation workflow"""
        # Mock the actual installation function instead of individual components
        mock_install.return_value = (
            0,
            "Serverless operator installed successfully",
            "",
        )

        # Test serverless operator installation
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_serverless_operator()

        assert rc == 0
        assert "successfully" in stdout.lower()
        assert stderr == ""
        mock_install.assert_called_once_with("serverless-operator")

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    @patch("rhoshift.cli.commands.install_operator")
    def test_main_function_workflow(self, mock_install, mock_preflight):
        """Test main function workflow"""
        mock_preflight.return_value = (True, [])
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 0
        mock_preflight.assert_called_once()
        mock_install.assert_called_once()

    @patch(
        "rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility"
    )
    @patch("rhoshift.cli.commands.install_operator")
    def test_enhanced_operator_workflow(self, mock_install, mock_dsci):
        """Test enhanced operator workflow"""
        mock_dsci.return_value = (True, [])
        mock_install.return_value = True

        selected_ops = {"serverless": True, "rhoai": True}
        config = {"oc_binary": "oc", "rhoai_channel": "stable"}

        result = install_operators(selected_ops, config)

        assert result is True
        mock_dsci.assert_called_once()


class TestStabilityLevels:
    """Test stability level functionality"""

    def test_stability_levels_exist(self):
        """Test that stability levels are properly defined"""

        assert StabilityLevel.BASIC.value == 1
        assert StabilityLevel.ENHANCED.value == 2
        assert StabilityLevel.COMPREHENSIVE.value == 3

        # Test ordering using values since direct comparison might not be supported
        assert StabilityLevel.BASIC.value < StabilityLevel.ENHANCED.value
        assert StabilityLevel.ENHANCED.value < StabilityLevel.COMPREHENSIVE.value

    def test_stability_config_creation(self):
        """Test stability configuration creation"""

        config = StabilityConfig(level=StabilityLevel.ENHANCED)
        assert config.level == StabilityLevel.ENHANCED

        comprehensive_config = StabilityConfig(level=StabilityLevel.COMPREHENSIVE)
        assert comprehensive_config.level == StabilityLevel.COMPREHENSIVE

    def test_stability_coordinator_creation(self):
        """Test stability coordinator creation"""

        config = StabilityConfig(level=StabilityLevel.ENHANCED)
        coordinator = StabilityCoordinator(config)

        assert coordinator.config.level == StabilityLevel.ENHANCED


class TestOperatorConfigurations:
    """Test operator configuration functionality"""

    def test_operator_manifest_generation(self):
        """Test that operator manifests can be generated"""

        manifest_gen = OpenShiftOperatorInstallManifest()

        # Test serverless manifest
        manifest = manifest_gen.generate_operator_manifest("serverless-operator")
        assert "apiVersion: operators.coreos.com/v1alpha1" in manifest
        assert "kind: Subscription" in manifest
        assert "serverless-operator" in manifest

    def test_operator_list_functionality(self):
        """Test operator listing functionality"""

        operators = OpenShiftOperatorInstallManifest.list_operators()
        assert isinstance(operators, list)
        assert len(operators) > 0
        assert "serverless-operator" in operators

    def test_dependency_resolution(self):
        """Test dependency resolution functionality"""

        # Test that Kueue includes cert-manager dependency
        resolved = OpenShiftOperatorInstallManifest.resolve_dependencies(
            ["kueue-operator"]
        )
        assert "openshift-cert-manager-operator" in resolved
        assert "kueue-operator" in resolved


class TestDSCIManifests:
    """Test DSCI/DSC manifest generation"""

    def test_dsci_manifest_generation(self):
        """Test DSCI manifest generation"""

        # Test default DSCI
        manifest = get_dsci_manifest()
        assert "apiVersion: dscinitialization.opendatahub.io/v1" in manifest
        assert "kind: DSCInitialization" in manifest
        assert "name: default-dsci" in manifest

        # Test custom DSCI
        custom_manifest = get_dsci_manifest(
            applications_namespace="custom-apps",
            monitoring_namespace="custom-monitoring",
        )
        assert "applicationsNamespace: custom-apps" in custom_manifest
        assert "namespace: custom-monitoring" in custom_manifest

    def test_dsc_manifest_generation(self):
        """Test DSC manifest generation"""

        # Test default DSC
        manifest = get_dsc_manifest()
        assert "apiVersion: datasciencecluster.opendatahub.io/v1" in manifest
        assert "kind: DataScienceCluster" in manifest
        assert "name: default-dsc" in manifest

        # Test DSC with Kueue
        kueue_manifest = get_dsc_manifest(kueue_management_state="Managed")
        assert "kueue:" in kueue_manifest
        assert "managementState: Managed" in kueue_manifest


class TestHealthMonitoring:
    """Test health monitoring functionality"""

    def test_health_status_enum(self):
        """Test HealthStatus enum"""

        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    @patch("rhoshift.utils.health_monitor.OperatorHealthMonitor")
    def test_check_operator_health_function(self, mock_monitor_class):
        """Test check_operator_health convenience function"""

        mock_monitor = Mock()
        mock_monitor.check_operator_health.return_value = (HealthStatus.HEALTHY, [])
        mock_monitor_class.return_value = mock_monitor

        status, results = check_operator_health("test-operator", "test-namespace")

        assert status == HealthStatus.HEALTHY
        assert isinstance(results, list)


class TestUtilityFunctions:
    """Test core utility functions"""

    @patch("subprocess.run")
    def test_run_command_basic(self, mock_run):
        """Test basic run_command functionality"""

        # Mock the subprocess.run to return what we expect
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = "success"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        rc, stdout, stderr = run_command("echo test")

        assert rc == 0
        assert stdout == "success"
        assert stderr == ""

    @patch("rhoshift.utils.utils.run_command")
    def test_apply_manifest_basic(self, mock_run_command):
        """Test basic apply_manifest functionality"""

        mock_run_command.return_value = (0, "applied", "")

        result = apply_manifest("test: manifest")

        assert result[0] == 0
        assert result[1] == "applied"


class TestArgumentParsing:
    """Test argument parsing functionality"""

    def test_parse_args_basic(self):
        """Test basic argument parsing"""

        with patch("sys.argv", ["script.py", "--serverless"]):
            args = parse_args()
            assert args.serverless is True
            assert args.oc_binary == "oc"

    def test_select_operators_functionality(self):
        """Test operator selection functionality"""

        with patch("sys.argv", ["script.py", "--all"]):
            args = parse_args()
            selected = select_operators(args)

            # All operators should be selected
            assert all(selected.values())

    def test_build_config_functionality(self):
        """Test configuration building functionality"""

        with patch("sys.argv", ["script.py", "--timeout", "600"]):
            args = parse_args()
            config = build_config(args)

            assert config["timeout"] == 600
            assert isinstance(config, dict)


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    @patch("rhoshift.utils.utils.run_command")
    def test_operator_status_checking(self, mock_run_command):
        """Test checking operator status"""

        mock_run_command.return_value = (0, "Succeeded", "")

        # This tests that the operator installer can be used
        configs = OpenShiftOperatorInstaller.get_operator_configs()
        assert len(configs) > 0
        assert "serverless-operator" in configs

    @patch("rhoshift.utils.utils.run_command")
    def test_dsci_conflict_detection(self, mock_run_command):
        """Test DSCI conflict detection"""

        mock_run_command.return_value = (0, "redhat-ods-monitoring", "")

        selected_ops = {"rhoai": True}
        config = {"rhoai_channel": "odh-nightlies", "create_dsc_dsci": False}

        compatible, warnings = (
            EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
                selected_ops, config
            )
        )

        assert compatible is True
        assert len(warnings) > 0
        assert "DSCI compatibility" in warnings[0]

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    @patch("rhoshift.cli.commands.install_operators")
    def test_all_operators_installation_flow(self, mock_install, mock_preflight):
        """Test --all operators installation flow"""

        mock_preflight.return_value = (True, [])
        mock_install.return_value = True

        with patch("sys.argv", ["script.py", "--all"]):
            result = main()

        assert result == 0
        mock_install.assert_called_once()

        # Verify all operators were selected
        call_args = mock_install.call_args
        selected_ops = call_args[0][0]
        assert selected_ops["serverless"] is True
        assert selected_ops["rhoai"] is True
        assert selected_ops["kueue"] is True


class TestErrorScenarios:
    """Test error handling scenarios"""

    def test_main_no_operators_selected(self):
        """Test main when no operators selected"""

        with patch("sys.argv", ["script.py"]):
            result = main()

        assert result == 1

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    def test_main_preflight_failure(self, mock_preflight):
        """Test main when preflight checks fail"""

        mock_preflight.return_value = (False, ["Cluster not ready"])

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 1

    @patch("rhoshift.cli.commands.install_operator")
    def test_operator_installation_failure(self, mock_install):
        """Test operator installation failure"""

        mock_install.return_value = False

        with patch("sys.argv", ["script.py", "--serverless"]):
            result = main()

        assert result == 1


class TestConfigurationHandling:
    """Test configuration handling across the application"""

    def test_config_propagation(self):
        """Test that configuration is properly propagated"""

        with patch(
            "sys.argv",
            [
                "script.py",
                "--serverless",
                "--oc-binary",
                "/custom/oc",
                "--retries",
                "5",
                "--timeout",
                "600",
            ],
        ):
            args = parse_args()
            config = build_config(args)

        assert config["oc_binary"] == "/custom/oc"
        assert config["max_retries"] == 5
        assert config["timeout"] == 600

    def test_rhoai_specific_config(self):
        """Test RHOAI-specific configuration handling"""

        test_image = "test-image:latest"
        with patch(
            "sys.argv",
            [
                "script.py",
                "--rhoai",
                "--rhoai-channel",
                "odh-nightlies",
                "--rhoai-image",
                test_image,
                "--deploy-rhoai-resources",
            ],
        ):
            args = parse_args()
            config = build_config(args)

        assert config["rhoai_channel"] == "odh-nightlies"
        assert config["rhoai_image"] == test_image

    def test_kueue_config_handling(self):
        """Test Kueue configuration handling"""

        # Test Kueue without value (default)
        with patch("sys.argv", ["script.py", "--kueue"]):
            args = parse_args()
            selected = select_operators(args)

        assert selected["kueue"] == "Unmanaged"

        # Test Kueue with explicit value
        with patch("sys.argv", ["script.py", "--kueue", "Managed"]):
            args = parse_args()
            selected = select_operators(args)

        assert selected["kueue"] == "Managed"


class TestManifestGeneration:
    """Test manifest generation functionality"""

    def test_operator_manifest_contains_required_fields(self):
        """Test that generated operator manifests contain required fields"""

        manifest_gen = OpenShiftOperatorInstallManifest()
        manifest = manifest_gen.generate_operator_manifest("serverless-operator")

        required_fields = [
            "apiVersion: operators.coreos.com/v1alpha1",
            "kind: Subscription",
            "name: serverless-operator",
            "spec:",
            "channel:",
            "source:",
        ]

        for field in required_fields:
            assert field in manifest

    def test_dsci_manifest_structure(self):
        """Test DSCI manifest structure"""

        manifest = get_dsci_manifest()

        required_sections = [
            "apiVersion: dscinitialization.opendatahub.io/v1",
            "kind: DSCInitialization",
            "name: default-dsci",
            "spec:",
            "applicationsNamespace:",
            "monitoring:",
            "serviceMesh:",
        ]

        for section in required_sections:
            assert section in manifest

    def test_dsc_manifest_structure(self):
        """Test DSC manifest structure"""

        manifest = get_dsc_manifest()

        required_sections = [
            "apiVersion: datasciencecluster.opendatahub.io/v1",
            "kind: DataScienceCluster",
            "name: default-dsc",
            "spec:",
            "components:",
            "dashboard:",
            "kserve:",
            "modelmeshserving:",
        ]

        for section in required_sections:
            assert section in manifest


class TestIntegrationPoints:
    """Test key integration points in the application"""

    def test_enhanced_operator_installer_integration(self):
        """Test enhanced operator installer integration"""

        installer = EnhancedOpenShiftOperatorInstaller(
            stability_level=StabilityLevel.ENHANCED
        )

        assert installer.stability_config.level == StabilityLevel.ENHANCED
        assert hasattr(installer, "coordinator")

    @patch("rhoshift.utils.utils.run_command")
    def test_preflight_checks_integration(self, mock_run_command):
        """Test preflight checks integration"""

        mock_run_command.return_value = (0, "success", "")

        ready, warnings = run_preflight_checks()

        assert isinstance(ready, bool)
        assert isinstance(warnings, list)

    def test_logger_integration(self):
        """Test logger integration"""

        logger = Logger.get_logger(__name__)
        assert logger is not None

        # Test that logger can be used
        logger.info("Test message")
        logger.warning("Test warning")
        logger.error("Test error")
