"""
Comprehensive tests for rhoshift.utils.operator.enhanced_operator module.
"""

import pytest
from unittest.mock import patch, Mock, call
from rhoshift.utils.operator.enhanced_operator import (
    EnhancedOpenShiftOperatorInstaller,
    install_operators_with_enhanced_stability,
    enhance_existing_operator_installation
)
from rhoshift.utils.stability_coordinator import StabilityLevel, StabilityConfig
from rhoshift.utils.health_monitor import HealthStatus


class TestEnhancedOpenShiftOperatorInstaller:
    """Test cases for EnhancedOpenShiftOperatorInstaller class"""
    
    def test_enhanced_installer_initialization_default(self):
        """Test enhanced installer initialization with defaults"""
        installer = EnhancedOpenShiftOperatorInstaller()
        
        assert installer.stability_config.level == StabilityLevel.ENHANCED
        assert installer.oc_binary == "oc"
        assert installer.coordinator is not None
    
    def test_enhanced_installer_initialization_custom(self):
        """Test enhanced installer initialization with custom parameters"""
        installer = EnhancedOpenShiftOperatorInstaller(
            stability_level=StabilityLevel.COMPREHENSIVE,
            oc_binary="/custom/oc"
        )
        
        assert installer.stability_config.level == StabilityLevel.COMPREHENSIVE
        assert installer.oc_binary == "/custom/oc"
    
    @patch('rhoshift.utils.operator.enhanced_operator.OpenShiftOperatorInstallManifest')
    @patch.object(EnhancedOpenShiftOperatorInstaller, '__init__', return_value=None)
    def test_install_operator_with_stability_success(self, mock_init, mock_manifest):
        """Test install_operator_with_stability method success"""
        # Setup mock installer
        installer = EnhancedOpenShiftOperatorInstaller.__new__(EnhancedOpenShiftOperatorInstaller)
        installer.coordinator = Mock()
        installer.coordinator.install_operator_with_stability.return_value = (True, {'success': True})
        
        # Mock manifest
        mock_manifest_gen = Mock()
        mock_manifest_gen.OPERATORS = {
            'test-operator': Mock(namespace='test-namespace')
        }
        mock_manifest.return_value = mock_manifest_gen
        
        result = EnhancedOpenShiftOperatorInstaller.install_operator_with_stability(
            'test-operator',
            stability_level=StabilityLevel.ENHANCED
        )
        
        assert result[0] == 0  # Success return code
        assert "Successfully installed test-operator" in result[1]
        assert result[2] == ""  # No error
    
    @patch('rhoshift.utils.operator.enhanced_operator.OpenShiftOperatorInstallManifest')
    @patch.object(EnhancedOpenShiftOperatorInstaller, '__init__', return_value=None)
    def test_install_operator_with_stability_failure(self, mock_init, mock_manifest):
        """Test install_operator_with_stability method failure"""
        # Setup mock installer
        installer = EnhancedOpenShiftOperatorInstaller.__new__(EnhancedOpenShiftOperatorInstaller)
        installer.coordinator = Mock()
        installer.coordinator.install_operator_with_stability.return_value = (False, {'errors': ['Installation failed']})
        
        # Mock manifest
        mock_manifest_gen = Mock()
        mock_manifest_gen.OPERATORS = {
            'test-operator': Mock(namespace='test-namespace')
        }
        mock_manifest.return_value = mock_manifest_gen
        
        result = EnhancedOpenShiftOperatorInstaller.install_operator_with_stability(
            'test-operator',
            stability_level=StabilityLevel.ENHANCED
        )
        
        assert result[0] == 1  # Failure return code
        assert result[1] == ""  # No success message
        assert "Installation failed" in result[2]  # Error message
    
    def test_install_serverless_operator_enhanced(self):
        """Test enhanced serverless operator installation"""
        with patch.object(EnhancedOpenShiftOperatorInstaller, 'install_operator_with_stability') as mock_install:
            mock_install.return_value = (0, "Success", "")
            
            result = EnhancedOpenShiftOperatorInstaller.install_serverless_operator_enhanced()
            
            assert result[0] == 0
            mock_install.assert_called_once_with('serverless-operator')
    
    @patch('rhoshift.utils.operator.enhanced_operator.execute_resilient_operation')
    @patch('rhoshift.utils.operator.enhanced_operator.apply_manifest')
    def test_install_keda_operator_enhanced_success(self, mock_apply, mock_resilient):
        """Test enhanced KEDA operator installation success"""
        # Mock successful KedaController creation
        mock_resilient.return_value = (True, "KedaController created", [])
        mock_apply.return_value = (0, "applied", "")
        
        with patch.object(EnhancedOpenShiftOperatorInstaller, 'install_operator_with_stability') as mock_install:
            mock_install.return_value = (0, "KEDA operator installed", "")
            
            with patch.object(EnhancedOpenShiftOperatorInstaller, '_wait_for_keda_readiness') as mock_wait:
                mock_wait.return_value = True
                
                result = EnhancedOpenShiftOperatorInstaller.install_keda_operator_enhanced()
                
                assert result[0] == 0
                mock_install.assert_called_once()
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('time.sleep')
    def test_wait_for_keda_readiness_success(self, mock_sleep, mock_run_command):
        """Test waiting for KEDA readiness - success"""
        mock_run_command.return_value = (0, "Installation Succeeded", "")
        
        result = EnhancedOpenShiftOperatorInstaller._wait_for_keda_readiness()
        
        assert result is True
        mock_run_command.assert_called_once()
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('time.sleep')
    def test_wait_for_keda_readiness_timeout(self, mock_sleep, mock_run_command):
        """Test waiting for KEDA readiness - timeout"""
        mock_run_command.return_value = (0, "Installing", "")
        
        result = EnhancedOpenShiftOperatorInstaller._wait_for_keda_readiness(timeout=1)
        
        assert result is False
        # Should have been called multiple times due to timeout
        assert mock_run_command.call_count >= 1
    
    @patch('rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator')
    def test_install_rhoai_operator_enhanced_success(self, mock_install_rhoai):
        """Test enhanced RHOAI operator installation success"""
        mock_install_rhoai.return_value = (0, "RHOAI installed", "")
        
        result = EnhancedOpenShiftOperatorInstaller.install_rhoai_operator_enhanced()
        
        assert result[0] == 0
        assert "RHOAI operator with DSC/DSCI installed successfully" in result[1]
        assert result[2] == ""
    
    @patch('rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator')
    def test_install_rhoai_operator_enhanced_failure(self, mock_install_rhoai):
        """Test enhanced RHOAI operator installation failure"""
        mock_install_rhoai.side_effect = Exception("Installation failed")
        
        result = EnhancedOpenShiftOperatorInstaller.install_rhoai_operator_enhanced()
        
        assert result[0] == 1
        assert result[1] == ""
        assert "RHOAI installation failed" in result[2]
    
    @patch('rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator')
    def test_install_rhoai_operator_enhanced_immutable_error(self, mock_install_rhoai):
        """Test enhanced RHOAI operator installation with immutable field error"""
        mock_install_rhoai.side_effect = Exception("MonitoringNamespace is immutable")
        
        result = EnhancedOpenShiftOperatorInstaller.install_rhoai_operator_enhanced()
        
        assert result[0] == 1
        assert result[1] == ""
        assert "DSCI conflict" in result[2]
        assert "Use --deploy-rhoai-resources" in result[2]
    
    def test_generate_installation_report(self):
        """Test generating installation report"""
        installer = EnhancedOpenShiftOperatorInstaller()
        installer.coordinator = Mock()
        installer.coordinator.generate_stability_report.return_value = "Test Report"
        
        report = installer.generate_installation_report()
        
        assert report == "Test Report"
        installer.coordinator.generate_stability_report.assert_called_once()
    
    def test_monitor_all_operators(self):
        """Test monitoring all operators"""
        installer = EnhancedOpenShiftOperatorInstaller()
        installer.coordinator = Mock()
        installer.coordinator.monitor_installed_operators.return_value = {"op1": {"status": "healthy"}}
        
        results = installer.monitor_all_operators()
        
        assert results == {"op1": {"status": "healthy"}}
        installer.coordinator.monitor_installed_operators.assert_called_once()
    
    @patch('rhoshift.utils.resilience.run_preflight_checks')
    def test_validate_cluster_readiness(self, mock_preflight):
        """Test cluster readiness validation"""
        mock_preflight.return_value = (True, ["warning1", "warning2"])
        
        ready, warnings = EnhancedOpenShiftOperatorInstaller.validate_cluster_readiness("oc")
        
        assert ready is True
        assert warnings == ["warning1", "warning2"]
        mock_preflight.assert_called_once_with("oc")
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_dsci_compatibility_no_rhoai(self, mock_run_command):
        """Test DSCI compatibility validation when RHOAI is not selected"""
        selected_ops = {'serverless': True, 'rhoai': False}
        config = {'rhoai_channel': 'stable'}
        
        compatible, warnings = EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
        
        assert compatible is True
        assert warnings == []
        mock_run_command.assert_not_called()
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_dsci_compatibility_no_existing_dsci(self, mock_run_command):
        """Test DSCI compatibility validation when no existing DSCI"""
        mock_run_command.return_value = (0, 'NOT_FOUND', '')
        
        selected_ops = {'rhoai': True}
        config = {'rhoai_channel': 'stable'}
        
        compatible, warnings = EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
        
        assert compatible is True
        assert warnings == []
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_dsci_compatibility_conflict_without_recreation(self, mock_run_command):
        """Test DSCI compatibility validation with conflict but no recreation"""
        mock_run_command.return_value = (0, 'redhat-ods-monitoring', '')
        
        selected_ops = {'rhoai': True}
        config = {'rhoai_channel': 'odh-nightlies', 'create_dsc_dsci': False}
        
        compatible, warnings = EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
        
        assert compatible is True
        assert len(warnings) == 1
        assert "DSCI compatibility" in warnings[0]
        assert "Using existing configuration" in warnings[0]
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_dsci_compatibility_conflict_with_recreation(self, mock_run_command):
        """Test DSCI compatibility validation with conflict and recreation"""
        mock_run_command.return_value = (0, 'redhat-ods-monitoring', '')
        
        selected_ops = {'rhoai': True}
        config = {'rhoai_channel': 'odh-nightlies', 'create_dsc_dsci': True}
        
        compatible, warnings = EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
        
        assert compatible is True
        assert len(warnings) == 1
        assert "DSCI will be recreated" in warnings[0]
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_dsci_compatibility_no_conflict(self, mock_run_command):
        """Test DSCI compatibility validation with no conflict"""
        mock_run_command.return_value = (0, 'redhat-ods-monitoring', '')
        
        selected_ops = {'rhoai': True}
        config = {'rhoai_channel': 'stable', 'create_dsc_dsci': False}
        
        compatible, warnings = EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
        
        assert compatible is True
        assert len(warnings) == 1
        assert "DSCI compatible" in warnings[0]
    
    @patch('rhoshift.utils.health_monitor.check_operator_health')
    @patch('rhoshift.utils.health_monitor.generate_health_report')
    def test_check_operator_health_status(self, mock_generate_report, mock_check_health):
        """Test checking operator health status"""
        mock_check_health.return_value = (HealthStatus.HEALTHY, {'status': 'good'})
        mock_generate_report.return_value = "Health report"
        
        status, report = EnhancedOpenShiftOperatorInstaller.check_operator_health_status(
            "test-operator", "test-namespace"
        )
        
        assert status == HealthStatus.HEALTHY
        assert report == "Health report"
        mock_check_health.assert_called_once_with("test-operator", "test-namespace", "oc")
        mock_generate_report.assert_called_once_with({'status': 'good'})


class TestInstallOperatorsWithEnhancedStability:
    """Test cases for install_operators_with_enhanced_stability function"""
    
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_cluster_readiness')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_dsci_compatibility')
    def test_install_operators_cluster_not_ready(self, mock_dsci_validation, mock_cluster_validation):
        """Test installation when cluster is not ready"""
        mock_cluster_validation.return_value = (False, ["Cluster not ready"])
        
        selected_ops = {'serverless': True}
        config = {'oc_binary': 'oc'}
        
        result = install_operators_with_enhanced_stability(selected_ops, config)
        
        assert result is False
        mock_dsci_validation.assert_not_called()
    
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_cluster_readiness')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_dsci_compatibility')
    def test_install_operators_dsci_not_compatible(self, mock_dsci_validation, mock_cluster_validation):
        """Test installation when DSCI is not compatible"""
        mock_cluster_validation.return_value = (True, [])
        mock_dsci_validation.return_value = (False, ["DSCI incompatible"])
        
        selected_ops = {'rhoai': True}
        config = {'oc_binary': 'oc'}
        
        result = install_operators_with_enhanced_stability(selected_ops, config)
        
        assert result is False
    
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_cluster_readiness')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_dsci_compatibility')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'install_serverless_operator_enhanced')
    def test_install_operators_success(self, mock_serverless_install, mock_dsci_validation, mock_cluster_validation):
        """Test successful operators installation"""
        mock_cluster_validation.return_value = (True, [])
        mock_dsci_validation.return_value = (True, [])
        mock_serverless_install.return_value = (0, "Success", "")
        
        selected_ops = {'serverless': True, 'servicemesh': False, 'rhoai': False}
        config = {'oc_binary': 'oc'}
        
        with patch.object(EnhancedOpenShiftOperatorInstaller, '__init__', return_value=None):
            installer = EnhancedOpenShiftOperatorInstaller.__new__(EnhancedOpenShiftOperatorInstaller)
            installer.generate_installation_report = Mock(return_value="Report")
            installer.monitor_all_operators = Mock(return_value={})
            
            with patch('rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller', return_value=installer):
                result = install_operators_with_enhanced_stability(selected_ops, config)
        
        assert result is True
        mock_serverless_install.assert_called_once()
    
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_cluster_readiness')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_dsci_compatibility')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'install_operator_with_stability')
    def test_install_operators_partial_failure(self, mock_operator_install, mock_dsci_validation, mock_cluster_validation):
        """Test operators installation with partial failure"""
        mock_cluster_validation.return_value = (True, [])
        mock_dsci_validation.return_value = (True, [])
        mock_operator_install.side_effect = [(0, "Success", ""), (1, "", "Failed")]
        
        selected_ops = {'servicemesh': True, 'authorino': True, 'serverless': False, 'rhoai': False}
        config = {'oc_binary': 'oc'}
        
        with patch.object(EnhancedOpenShiftOperatorInstaller, '__init__', return_value=None):
            installer = EnhancedOpenShiftOperatorInstaller.__new__(EnhancedOpenShiftOperatorInstaller)
            installer.generate_installation_report = Mock(return_value="Report")
            installer.monitor_all_operators = Mock(return_value={})
            
            with patch('rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller', return_value=installer):
                result = install_operators_with_enhanced_stability(selected_ops, config)
        
        assert result is False
        assert mock_operator_install.call_count == 2
    
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_cluster_readiness')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_dsci_compatibility')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'install_rhoai_operator_enhanced')
    def test_install_operators_with_enhanced_rhoai(self, mock_rhoai_install, mock_dsci_validation, mock_cluster_validation):
        """Test installation with enhanced RHOAI installer"""
        mock_cluster_validation.return_value = (True, [])
        mock_dsci_validation.return_value = (True, [])
        mock_rhoai_install.return_value = (0, "Success", "")
        
        selected_ops = {'rhoai': True, 'serverless': False}
        config = {'oc_binary': 'oc'}
        
        with patch.object(EnhancedOpenShiftOperatorInstaller, '__init__', return_value=None):
            installer = EnhancedOpenShiftOperatorInstaller.__new__(EnhancedOpenShiftOperatorInstaller)
            installer.generate_installation_report = Mock(return_value="Report")
            installer.monitor_all_operators = Mock(return_value={})
            
            with patch('rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller', return_value=installer):
                result = install_operators_with_enhanced_stability(selected_ops, config)
        
        assert result is True
        mock_rhoai_install.assert_called_once()
    
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_cluster_readiness')
    @patch.object(EnhancedOpenShiftOperatorInstaller, 'validate_dsci_compatibility')
    def test_install_operators_exception_handling(self, mock_dsci_validation, mock_cluster_validation):
        """Test installation with exception handling"""
        mock_cluster_validation.return_value = (True, [])
        mock_dsci_validation.return_value = (True, [])
        
        selected_ops = {'serverless': True, 'rhoai': False}
        config = {'oc_binary': 'oc'}
        
        with patch.object(EnhancedOpenShiftOperatorInstaller, 'install_operator_with_stability') as mock_install:
            mock_install.side_effect = Exception("Unexpected error")
            
            with patch.object(EnhancedOpenShiftOperatorInstaller, '__init__', return_value=None):
                installer = EnhancedOpenShiftOperatorInstaller.__new__(EnhancedOpenShiftOperatorInstaller)
                installer.generate_installation_report = Mock(return_value="Report")
                installer.monitor_all_operators = Mock(return_value={})
                
                with patch('rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller', return_value=installer):
                    result = install_operators_with_enhanced_stability(selected_ops, config)
        
        assert result is False


class TestEnhanceExistingOperatorInstallation:
    """Test cases for enhance_existing_operator_installation function"""
    
    def test_enhance_existing_operator_installation(self):
        """Test enhancing existing operator installation"""
        # This function primarily demonstrates integration
        # The actual implementation shows how to enhance existing methods
        
        # Call the function
        enhance_existing_operator_installation()
        
        # This should complete without errors
        # The function primarily contains example code for integration


class TestIntegrationScenarios:
    """Integration test scenarios for enhanced operator installation"""
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('rhoshift.utils.resilience.run_preflight_checks')
    def test_complete_enhanced_installation_workflow(self, mock_preflight, mock_run_command):
        """Test complete enhanced installation workflow"""
        # Setup successful preflight checks
        mock_preflight.return_value = (True, [])
        
        # Setup successful DSCI check
        mock_run_command.return_value = (0, 'NOT_FOUND', '')
        
        # Test with multiple operators
        selected_ops = {
            'serverless': True,
            'keda': True,
            'rhoai': True,
            'servicemesh': False,
            'authorino': False,
            'cert-manager': False
        }
        
        config = {
            'oc_binary': 'oc',
            'rhoai_channel': 'stable',
            'create_dsc_dsci': False
        }
        
        with patch.object(EnhancedOpenShiftOperatorInstaller, 'install_serverless_operator_enhanced') as mock_serverless:
            with patch.object(EnhancedOpenShiftOperatorInstaller, 'install_keda_operator_enhanced') as mock_keda:
                with patch.object(EnhancedOpenShiftOperatorInstaller, 'install_rhoai_operator_enhanced') as mock_rhoai:
                    mock_serverless.return_value = (0, "Serverless installed", "")
                    mock_keda.return_value = (0, "KEDA installed", "")
                    mock_rhoai.return_value = (0, "RHOAI installed", "")
                    
                    result = install_operators_with_enhanced_stability(selected_ops, config)
        
        assert result is True
        mock_serverless.assert_called_once()
        mock_keda.assert_called_once()
        mock_rhoai.assert_called_once()
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('rhoshift.utils.resilience.run_preflight_checks')
    def test_enhanced_installation_with_dsci_conflict_resolution(self, mock_preflight, mock_run_command):
        """Test enhanced installation with DSCI conflict resolution"""
        # Setup successful preflight checks
        mock_preflight.return_value = (True, [])
        
        # Setup DSCI conflict scenario
        mock_run_command.return_value = (0, 'redhat-ods-monitoring', '')
        
        selected_ops = {'rhoai': True}
        config = {
            'oc_binary': 'oc',
            'rhoai_channel': 'odh-nightlies',  # This conflicts with existing DSCI
            'create_dsc_dsci': True  # Force recreation
        }
        
        with patch.object(EnhancedOpenShiftOperatorInstaller, 'install_rhoai_operator_enhanced') as mock_rhoai:
            mock_rhoai.return_value = (0, "RHOAI installed with DSC/DSCI recreated", "")
            
            result = install_operators_with_enhanced_stability(selected_ops, config)
        
        assert result is True
        mock_rhoai.assert_called_once()
    
    def test_stability_level_configuration_impact(self):
        """Test that different stability levels are properly configured"""
        # Test basic level
        basic_installer = EnhancedOpenShiftOperatorInstaller(stability_level=StabilityLevel.BASIC)
        assert basic_installer.stability_config.level == StabilityLevel.BASIC
        
        # Test enhanced level (default)
        enhanced_installer = EnhancedOpenShiftOperatorInstaller()
        assert enhanced_installer.stability_config.level == StabilityLevel.ENHANCED
        
        # Test comprehensive level
        comprehensive_installer = EnhancedOpenShiftOperatorInstaller(stability_level=StabilityLevel.COMPREHENSIVE)
        assert comprehensive_installer.stability_config.level == StabilityLevel.COMPREHENSIVE
        
        # Verify levels are different
        assert basic_installer.stability_config.level != enhanced_installer.stability_config.level
        assert enhanced_installer.stability_config.level != comprehensive_installer.stability_config.level
