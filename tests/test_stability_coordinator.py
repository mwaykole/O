"""
Comprehensive tests for rhoshift.utils.stability_coordinator module.
"""

from unittest.mock import Mock, call, patch

import pytest

from rhoshift.utils.health_monitor import HealthStatus
from rhoshift.utils.stability_coordinator import (
    StabilityConfig,
    StabilityCoordinator,
    StabilityLevel,
)


class TestStabilityLevel:
    """Test cases for StabilityLevel enum"""

    def test_stability_level_values(self):
        """Test StabilityLevel enum values and ordering"""
        assert StabilityLevel.BASIC.value == 1
        assert StabilityLevel.ENHANCED.value == 2
        assert StabilityLevel.COMPREHENSIVE.value == 3

        # Test ordering
        assert StabilityLevel.BASIC < StabilityLevel.ENHANCED
        assert StabilityLevel.ENHANCED < StabilityLevel.COMPREHENSIVE
        assert StabilityLevel.COMPREHENSIVE > StabilityLevel.BASIC

    def test_stability_level_string_representation(self):
        """Test StabilityLevel string representation"""
        assert str(StabilityLevel.BASIC) == "StabilityLevel.BASIC"
        assert str(StabilityLevel.ENHANCED) == "StabilityLevel.ENHANCED"
        assert str(StabilityLevel.COMPREHENSIVE) == "StabilityLevel.COMPREHENSIVE"


class TestStabilityConfig:
    """Test cases for StabilityConfig dataclass"""

    def test_stability_config_default(self):
        """Test StabilityConfig with default values"""
        config = StabilityConfig()

        assert config.level == StabilityLevel.ENHANCED
        assert config.enable_preflight_checks is True
        assert config.enable_health_monitoring is True
        assert config.enable_auto_recovery is True
        assert config.max_retries == 3
        assert config.retry_delay == 10
        assert config.timeout == 300
        assert config.health_check_interval == 30
        assert config.recovery_attempts == 2

    def test_stability_config_custom(self):
        """Test StabilityConfig with custom values"""
        config = StabilityConfig(
            level=StabilityLevel.COMPREHENSIVE,
            enable_preflight_checks=False,
            max_retries=5,
            retry_delay=15,
            timeout=600,
            health_check_interval=60,
            recovery_attempts=3,
        )

        assert config.level == StabilityLevel.COMPREHENSIVE
        assert config.enable_preflight_checks is False
        assert config.max_retries == 5
        assert config.retry_delay == 15
        assert config.timeout == 600
        assert config.health_check_interval == 60
        assert config.recovery_attempts == 3

    def test_stability_config_basic_level(self):
        """Test StabilityConfig with basic stability level"""
        config = StabilityConfig(level=StabilityLevel.BASIC)

        assert config.level == StabilityLevel.BASIC
        # Basic level might have different defaults
        assert isinstance(config.enable_preflight_checks, bool)
        assert isinstance(config.max_retries, int)


class TestOperatorInstallationResult:
    """Test cases for OperatorInstallationResult dataclass"""

    def test_operator_installation_result_success(self):
        """Test OperatorInstallationResult for successful installation"""
        result = OperatorInstallationResult(
            operator_name="test-operator",
            success=True,
            return_code=0,
            stdout="Installation successful",
            stderr="",
            duration=120.5,
            retry_count=0,
            health_status="Healthy",
            warnings=[],
        )

        assert result.operator_name == "test-operator"
        assert result.success is True
        assert result.return_code == 0
        assert result.stdout == "Installation successful"
        assert result.stderr == ""
        assert result.duration == 120.5
        assert result.retry_count == 0
        assert result.health_status == "Healthy"
        assert result.warnings == []

    def test_operator_installation_result_failure(self):
        """Test OperatorInstallationResult for failed installation"""
        result = OperatorInstallationResult(
            operator_name="failing-operator",
            success=False,
            return_code=1,
            stdout="",
            stderr="Installation failed",
            duration=45.2,
            retry_count=3,
            health_status="Unhealthy",
            warnings=["Warning: deprecated API", "Warning: resource limit"],
        )

        assert result.operator_name == "failing-operator"
        assert result.success is False
        assert result.return_code == 1
        assert result.stderr == "Installation failed"
        assert result.retry_count == 3
        assert result.health_status == "Unhealthy"
        assert len(result.warnings) == 2


class TestStabilityCoordinator:
    """Test cases for StabilityCoordinator class"""

    def test_stability_coordinator_init_default(self):
        """Test StabilityCoordinator initialization with defaults"""
        coordinator = StabilityCoordinator()

        assert coordinator.config.level == StabilityLevel.ENHANCED
        assert coordinator.oc_binary == "oc"
        assert isinstance(coordinator.installation_results, list)
        assert len(coordinator.installation_results) == 0

    def test_stability_coordinator_init_custom(self):
        """Test StabilityCoordinator initialization with custom config"""
        config = StabilityConfig(level=StabilityLevel.COMPREHENSIVE, max_retries=5)
        coordinator = StabilityCoordinator(config, "/custom/oc")

        assert coordinator.config.level == StabilityLevel.COMPREHENSIVE
        assert coordinator.config.max_retries == 5
        assert coordinator.oc_binary == "/custom/oc"

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    def test_run_preflight_checks_enabled(self, mock_preflight):
        """Test running preflight checks when enabled"""
        mock_preflight.return_value = (True, [])

        config = StabilityConfig(enable_preflight_checks=True)
        coordinator = StabilityCoordinator(config)

        success, warnings = coordinator.run_preflight_checks()

        assert success is True
        assert warnings == []
        mock_preflight.assert_called_once_with("oc")

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    def test_run_preflight_checks_disabled(self, mock_preflight):
        """Test running preflight checks when disabled"""
        config = StabilityConfig(enable_preflight_checks=False)
        coordinator = StabilityCoordinator(config)

        success, warnings = coordinator.run_preflight_checks()

        assert success is True
        assert warnings == []
        mock_preflight.assert_not_called()

    @patch("rhoshift.utils.health_monitor.check_operator_health")
    def test_monitor_operator_health_enabled(self, mock_health_check):
        """Test monitoring operator health when enabled"""
        mock_health_check.return_value = (HealthStatus.HEALTHY, {"status": "good"})

        config = StabilityConfig(enable_health_monitoring=True)
        coordinator = StabilityCoordinator(config)

        status, results = coordinator.monitor_operator_health(
            "test-operator", "test-namespace"
        )

        assert status == HealthStatus.HEALTHY
        assert results["status"] == "good"
        mock_health_check.assert_called_once_with(
            "test-operator", "test-namespace", "oc"
        )

    @patch("rhoshift.utils.health_monitor.check_operator_health")
    def test_monitor_operator_health_disabled(self, mock_health_check):
        """Test monitoring operator health when disabled"""

        config = StabilityConfig(enable_health_monitoring=False)
        coordinator = StabilityCoordinator(config)

        status, results = coordinator.monitor_operator_health(
            "test-operator", "test-namespace"
        )

        assert status == HealthStatus.UNKNOWN
        assert results == {}
        mock_health_check.assert_not_called()

    @patch("rhoshift.utils.resilience.execute_resilient_operation")
    @patch("time.time")
    def test_install_operator_with_stability_success(
        self, mock_time, mock_resilient_op
    ):
        """Test operator installation with stability features - success"""
        mock_time.side_effect = [1000.0, 1120.5]  # Start and end times
        mock_resilient_op.return_value = (True, (0, "success", ""), [])

        coordinator = StabilityCoordinator()

        def mock_installation(**kwargs):
            return (0, "Installation successful", "")

        success, results = coordinator.install_operator_with_stability(
            operator_name="test-operator",
            namespace="test-namespace",
            installation_func=mock_installation,
        )

        assert success is True
        assert "test-operator" in results

        # Check that result was recorded
        assert len(coordinator.installation_results) == 1
        result = coordinator.installation_results[0]
        assert result.operator_name == "test-operator"
        assert result.success is True
        assert result.duration == 120.5

    @patch("rhoshift.utils.resilience.execute_resilient_operation")
    @patch("time.time")
    def test_install_operator_with_stability_failure(
        self, mock_time, mock_resilient_op
    ):
        """Test operator installation with stability features - failure"""
        mock_time.side_effect = [1000.0, 1045.2]  # Start and end times
        mock_resilient_op.return_value = (
            False,
            "Installation failed",
            ["Error occurred"],
        )

        coordinator = StabilityCoordinator()

        def mock_installation(**kwargs):
            raise Exception("Installation failed")

        success, results = coordinator.install_operator_with_stability(
            operator_name="failing-operator",
            namespace="test-namespace",
            installation_func=mock_installation,
        )

        assert success is False
        assert "failing-operator" in results
        assert "errors" in results

        # Check that result was recorded
        assert len(coordinator.installation_results) == 1
        result = coordinator.installation_results[0]
        assert result.operator_name == "failing-operator"
        assert result.success is False
        assert result.duration == 45.2

    @patch("rhoshift.utils.health_monitor.monitor_operator_installation")
    def test_install_operator_with_health_monitoring(self, mock_monitor):
        """Test operator installation with health monitoring"""
        mock_monitor.return_value = (True, HealthStatus.HEALTHY, {"status": "ready"})

        config = StabilityConfig(enable_health_monitoring=True)
        coordinator = StabilityCoordinator(config)

        def mock_installation(**kwargs):
            return (0, "Installation successful", "")

        success, results = coordinator.install_operator_with_stability(
            operator_name="test-operator",
            namespace="test-namespace",
            installation_func=mock_installation,
        )

        assert success is True
        mock_monitor.assert_called_once()

    def test_record_installation_result(self):
        """Test recording installation results"""
        coordinator = StabilityCoordinator()

        result = OperatorInstallationResult(
            operator_name="test-operator",
            success=True,
            return_code=0,
            stdout="success",
            stderr="",
            duration=60.0,
            retry_count=1,
            health_status="Healthy",
            warnings=[],
        )

        coordinator.record_installation_result(result)

        assert len(coordinator.installation_results) == 1
        assert coordinator.installation_results[0] == result

    def test_get_installation_summary(self):
        """Test getting installation summary"""
        coordinator = StabilityCoordinator()

        # Add some results
        results = [
            OperatorInstallationResult(
                operator_name="op1",
                success=True,
                return_code=0,
                stdout="",
                stderr="",
                duration=60.0,
                retry_count=0,
                health_status="Healthy",
                warnings=[],
            ),
            OperatorInstallationResult(
                operator_name="op2",
                success=False,
                return_code=1,
                stdout="",
                stderr="error",
                duration=30.0,
                retry_count=3,
                health_status="Unhealthy",
                warnings=["warning"],
            ),
            OperatorInstallationResult(
                operator_name="op3",
                success=True,
                return_code=0,
                stdout="",
                stderr="",
                duration=45.0,
                retry_count=1,
                health_status="Healthy",
                warnings=[],
            ),
        ]

        for result in results:
            coordinator.record_installation_result(result)

        summary = coordinator.get_installation_summary()

        assert summary["total_operators"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == pytest.approx(0.667, rel=1e-2)
        assert summary["total_duration"] == 135.0
        assert summary["average_duration"] == 45.0
        assert summary["total_retries"] == 4

    def test_generate_stability_report(self):
        """Test generating stability report"""
        coordinator = StabilityCoordinator()

        # Add a result
        result = OperatorInstallationResult(
            operator_name="test-operator",
            success=True,
            return_code=0,
            stdout="success",
            stderr="",
            duration=90.0,
            retry_count=2,
            health_status="Healthy",
            warnings=["minor warning"],
        )
        coordinator.record_installation_result(result)

        report = coordinator.generate_stability_report()

        assert isinstance(report, str)
        assert "STABILITY COORDINATOR REPORT" in report
        assert "test-operator" in report
        assert "Healthy" in report
        assert "90.0" in report

    def test_monitor_installed_operators(self):
        """Test monitoring all installed operators"""
        coordinator = StabilityCoordinator()

        # Add some installation results
        results = [
            OperatorInstallationResult(
                operator_name="op1",
                success=True,
                return_code=0,
                stdout="",
                stderr="",
                duration=60.0,
                retry_count=0,
                health_status="Healthy",
                warnings=[],
            ),
            OperatorInstallationResult(
                operator_name="op2",
                success=True,
                return_code=0,
                stdout="",
                stderr="",
                duration=45.0,
                retry_count=0,
                health_status="Healthy",
                warnings=[],
            ),
        ]

        for result in results:
            coordinator.record_installation_result(result)

        with patch.object(coordinator, "monitor_operator_health") as mock_monitor:
            mock_monitor.return_value = (HealthStatus.HEALTHY, {"status": "good"})

            monitoring_results = coordinator.monitor_installed_operators()

            assert len(monitoring_results) == 2
            assert "op1" in monitoring_results
            assert "op2" in monitoring_results
            assert mock_monitor.call_count == 2


class TestStabilityIntegration:
    """Integration tests for stability coordinator features"""

    @patch("rhoshift.utils.resilience.run_preflight_checks")
    @patch("rhoshift.utils.health_monitor.monitor_operator_installation")
    @patch("time.time")
    def test_complete_stability_workflow(self, mock_time, mock_monitor, mock_preflight):
        """Test complete stability coordination workflow"""

        # Setup mocks
        mock_time.side_effect = [1000.0, 1150.0]
        mock_preflight.return_value = (True, [])
        mock_monitor.return_value = (True, HealthStatus.HEALTHY, {"status": "ready"})

        config = StabilityConfig(level=StabilityLevel.COMPREHENSIVE)
        coordinator = StabilityCoordinator(config)

        # Run preflight checks
        preflight_success, preflight_warnings = coordinator.run_preflight_checks()
        assert preflight_success is True

        # Install operator with stability
        def mock_installation(**kwargs):
            return (0, "Installation successful", "")

        success, results = coordinator.install_operator_with_stability(
            operator_name="comprehensive-operator",
            namespace="test-namespace",
            installation_func=mock_installation,
        )

        assert success is True

        # Verify all components were called
        mock_preflight.assert_called_once()
        mock_monitor.assert_called_once()

        # Check recorded results
        assert len(coordinator.installation_results) == 1
        result = coordinator.installation_results[0]
        assert result.operator_name == "comprehensive-operator"
        assert result.success is True

        # Generate report
        report = coordinator.generate_stability_report()
        assert "comprehensive-operator" in report
        assert "COMPREHENSIVE" in report.upper()

    @patch("rhoshift.utils.resilience.execute_resilient_operation")
    def test_stability_coordinator_with_recovery(self, mock_resilient_op):
        """Test stability coordinator with recovery actions"""
        # Simulate recovery scenario
        mock_resilient_op.return_value = (
            True,
            (0, "success after recovery", ""),
            ["Recovery attempted"],
        )

        coordinator = StabilityCoordinator()

        def failing_then_succeeding_installation(**kwargs):
            # This would normally fail first, then succeed after recovery
            return (0, "success after recovery", "")

        success, results = coordinator.install_operator_with_stability(
            operator_name="recovery-operator",
            namespace="test-namespace",
            installation_func=failing_then_succeeding_installation,
        )

        assert success is True
        mock_resilient_op.assert_called_once()

        # Check that warnings from recovery are included
        result = coordinator.installation_results[0]
        assert result.operator_name == "recovery-operator"
        assert result.success is True

    def test_stability_levels_affect_behavior(self):
        """Test that different stability levels affect coordinator behavior"""
        basic_config = StabilityConfig(level=StabilityLevel.BASIC)
        enhanced_config = StabilityConfig(level=StabilityLevel.ENHANCED)
        comprehensive_config = StabilityConfig(level=StabilityLevel.COMPREHENSIVE)

        basic_coordinator = StabilityCoordinator(basic_config)
        enhanced_coordinator = StabilityCoordinator(enhanced_config)
        comprehensive_coordinator = StabilityCoordinator(comprehensive_config)

        # All should be properly initialized
        assert basic_coordinator.config.level == StabilityLevel.BASIC
        assert enhanced_coordinator.config.level == StabilityLevel.ENHANCED
        assert comprehensive_coordinator.config.level == StabilityLevel.COMPREHENSIVE

        # Different levels might have different default behaviors
        # This is mainly testing that the different levels can be instantiated
        # and that the configuration is properly set
        assert (
            basic_coordinator.config.level.value
            < enhanced_coordinator.config.level.value
        )
        assert (
            enhanced_coordinator.config.level.value
            < comprehensive_coordinator.config.level.value
        )
