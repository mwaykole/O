"""
Comprehensive tests for rhoshift.utils.health_monitor module.
"""

import pytest
from unittest.mock import patch, Mock
from rhoshift.utils.health_monitor import (
    HealthStatus,
    ResourceType,
    HealthCheck,
    ResourceHealth,
    OperatorHealthMonitor,
    check_operator_health,
    generate_health_report
)


class TestHealthStatus:
    """Test cases for HealthStatus enum"""
    
    def test_health_status_values(self):
        """Test HealthStatus enum values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"
    
    def test_health_status_comparison(self):
        """Test HealthStatus comparison operations"""
        assert HealthStatus.HEALTHY != HealthStatus.DEGRADED
        assert HealthStatus.UNHEALTHY != HealthStatus.UNKNOWN
        
        # Test string representation
        assert str(HealthStatus.HEALTHY) == "HealthStatus.HEALTHY"


class TestResourceType:
    """Test cases for ResourceType enum"""
    
    def test_resource_type_values(self):
        """Test ResourceType enum values"""
        assert ResourceType.OPERATOR_CSV.value == "csv"
        assert ResourceType.SUBSCRIPTION.value == "subscription"
        assert ResourceType.DEPLOYMENT.value == "deployment"
        assert ResourceType.POD.value == "pod"
        assert ResourceType.SERVICE.value == "service"
        assert ResourceType.DSCI.value == "dsci"
        assert ResourceType.DSC.value == "dsc"
        assert ResourceType.OPERATOR_GROUP.value == "operatorgroup"


class TestHealthCheck:
    """Test cases for HealthCheck dataclass"""
    
    def test_health_check_creation(self):
        """Test HealthCheck instance creation"""
        health_check = HealthCheck(
            name="test-check",
            resource_type=ResourceType.POD,
            namespace="test-namespace",
            resource_name="test-pod"
        )
        
        assert health_check.name == "test-check"
        assert health_check.resource_type == ResourceType.POD
        assert health_check.namespace == "test-namespace"
        assert health_check.resource_name == "test-pod"
        assert health_check.timeout == 300  # Default
        assert health_check.critical is True  # Default
    
    def test_health_check_custom_values(self):
        """Test HealthCheck with custom values"""
        health_check = HealthCheck(
            name="custom-check",
            resource_type=ResourceType.DEPLOYMENT,
            namespace="custom-namespace",
            timeout=600,
            critical=False
        )
        
        assert health_check.timeout == 600
        assert health_check.critical is False


class TestResourceHealth:
    """Test cases for ResourceHealth dataclass"""
    
    def test_resource_health_creation(self):
        """Test ResourceHealth instance creation"""
        resource_health = ResourceHealth(
            resource_type=ResourceType.POD,
            name="test-pod",
            namespace="test-namespace",
            status=HealthStatus.HEALTHY,
            message="Pod is running"
        )
        
        assert resource_health.resource_type == ResourceType.POD
        assert resource_health.name == "test-pod"
        assert resource_health.namespace == "test-namespace"
        assert resource_health.status == HealthStatus.HEALTHY
        assert resource_health.message == "Pod is running"
        assert resource_health.details == {}  # Default
        assert resource_health.last_checked is None  # Default


class TestOperatorHealthMonitor:
    """Test cases for OperatorHealthMonitor class"""
    
    def test_operator_health_monitor_init(self):
        """Test OperatorHealthMonitor initialization"""
        monitor = OperatorHealthMonitor()
        assert monitor.oc_binary == "oc"
        assert isinstance(monitor.health_cache, dict)
        assert len(monitor.health_cache) == 0
        
        # Test with custom oc binary
        custom_monitor = OperatorHealthMonitor("/custom/oc")
        assert custom_monitor.oc_binary == "/custom/oc"
    
    @patch('rhoshift.utils.utils.run_command')
    def test_check_operator_health_via_monitor(self, mock_run_command):
        """Test operator health check using monitor"""
        # Mock successful responses for various health checks
        mock_run_command.return_value = (0, 'healthy', '')
        
        monitor = OperatorHealthMonitor()
        status, results = monitor.check_operator_health('test-operator', 'test-namespace')
        
        assert isinstance(status, HealthStatus)
        assert isinstance(results, list)
        # Should have made some health check calls
        assert mock_run_command.call_count > 0


class TestCheckOperatorHealth:
    """Test cases for check_operator_health convenience function"""
    
    @patch('rhoshift.utils.health_monitor.OperatorHealthMonitor')
    def test_check_operator_health_convenience_function(self, mock_monitor_class):
        """Test check_operator_health convenience function"""
        mock_monitor = Mock()
        mock_monitor.check_operator_health.return_value = (HealthStatus.HEALTHY, [])
        mock_monitor_class.return_value = mock_monitor
        
        status, results = check_operator_health('test-operator', 'test-namespace')
        
        assert status == HealthStatus.HEALTHY
        assert results == []
        mock_monitor_class.assert_called_once_with("oc")
        mock_monitor.check_operator_health.assert_called_once_with('test-operator', 'test-namespace')
    
    @patch('rhoshift.utils.health_monitor.OperatorHealthMonitor')
    def test_check_operator_health_custom_oc_binary(self, mock_monitor_class):
        """Test check_operator_health with custom oc binary"""
        mock_monitor = Mock()
        mock_monitor.check_operator_health.return_value = (HealthStatus.HEALTHY, [])
        mock_monitor_class.return_value = mock_monitor
        
        check_operator_health('test-operator', 'test-namespace', '/custom/oc')
        
        mock_monitor_class.assert_called_once_with("/custom/oc")


class TestGenerateHealthReport:
    """Test cases for generate_health_report convenience function"""
    
    @patch('rhoshift.utils.health_monitor.OperatorHealthMonitor')
    def test_generate_health_report_convenience_function(self, mock_monitor_class):
        """Test generate_health_report convenience function"""
        mock_monitor = Mock()
        mock_monitor.generate_health_report.return_value = "Health Report"
        mock_monitor_class.return_value = mock_monitor
        
        health_results = [
            ResourceHealth(
                resource_type=ResourceType.POD,
                name="test-pod",
                namespace="test-namespace",
                status=HealthStatus.HEALTHY,
                message="Pod is healthy"
            )
        ]
        
        report = generate_health_report(health_results)
        
        assert report == "Health Report"
        mock_monitor_class.assert_called_once_with()
        mock_monitor.generate_health_report.assert_called_once_with(health_results)
    
