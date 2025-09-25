"""
Comprehensive tests for rhoshift.utils.operator.operator module.
"""

import pytest
from unittest.mock import patch, Mock, call, mock_open
from rhoshift.utils.operator.operator import (
    OpenShiftOperatorInstaller,
)
from rhoshift.utils.constants import WaitTime


class TestOpenShiftOperatorInstaller:
    """Test cases for OpenShiftOperatorInstaller class"""
    
    def test_get_operator_configs(self):
        """Test getting operator configurations"""
        configs = OpenShiftOperatorInstaller.get_operator_configs()
        
        assert isinstance(configs, dict)
        assert len(configs) > 0
        
        # Check that standard operators are included
        expected_operators = [
            'serverless-operator',
            'servicemeshoperator',
            'authorino-operator',
            'openshift-cert-manager-operator',
            'kueue-operator',
            'openshift-custom-metrics-autoscaler-operator'
        ]
        
        for operator in expected_operators:
            assert operator in configs
            config = configs[operator]
            assert 'manifest' in config
            assert 'namespace' in config
            assert 'display_name' in config
            assert 'config' in config
    
    def test_operator_configs_property(self):
        """Test OPERATOR_CONFIGS property backward compatibility"""
        installer = OpenShiftOperatorInstaller()
        configs = installer.OPERATOR_CONFIGS
        
        assert isinstance(configs, dict)
        assert len(configs) > 0
    
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.utils.wait_for_resource_for_specific_status')
    def test_install_operator_success(self, mock_wait, mock_apply):
        """Test successful operator installation"""
        mock_apply.return_value = (0, "applied", "")
        mock_wait.return_value = (True, "Succeeded", "")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_operator(
            'serverless-operator',
            oc_binary='oc',
            timeout=300
        )
        
        assert rc == 0
        assert "successfully" in stdout.lower()
        assert stderr == ""
        mock_apply.assert_called()
        mock_wait.assert_called()
    
    @patch('rhoshift.utils.utils.apply_manifest')
    def test_install_operator_manifest_failure(self, mock_apply):
        """Test operator installation when manifest application fails"""
        mock_apply.side_effect = Exception("Manifest application failed")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_operator(
            'serverless-operator',
            oc_binary='oc'
        )
        
        assert rc == 1
        assert stdout == ""
        assert "failed" in stderr.lower()
    
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.utils.wait_for_resource_for_specific_status')
    def test_install_operator_timeout(self, mock_wait, mock_apply):
        """Test operator installation timeout"""
        mock_apply.return_value = (0, "applied", "")
        mock_wait.return_value = (False, "Installing", "Timeout")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_operator(
            'serverless-operator',
            oc_binary='oc',
            timeout=60
        )
        
        assert rc == 1
        assert stdout == ""
        assert "timeout" in stderr.lower() or "failed" in stderr.lower()
    
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.utils.wait_for_resource_for_specific_status')
    def test_install_operator_custom_parameters(self, mock_wait, mock_apply):
        """Test operator installation with custom parameters"""
        mock_apply.return_value = (0, "applied", "")
        mock_wait.return_value = (True, "Succeeded", "")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_operator(
            'serverless-operator',
            oc_binary='/custom/oc',
            timeout=600,
            max_retries=5,
            retry_delay=20
        )
        
        assert rc == 0
        # Verify custom parameters were used
        mock_apply.assert_called()
        call_args = mock_apply.call_args
        assert call_args[1]['oc_binary'] == '/custom/oc'
        assert call_args[1]['timeout'] == 600
    
    def test_install_serverless_operator(self):
        """Test serverless operator installation"""
        with patch.object(OpenShiftOperatorInstaller, 'install_operator') as mock_install:
            mock_install.return_value = (0, "Success", "")
            
            result = OpenShiftOperatorInstaller.install_serverless_operator()
            
            assert result[0] == 0
            mock_install.assert_called_once_with('serverless-operator')
    
    def test_install_servicemesh_operator(self):
        """Test service mesh operator installation"""
        with patch.object(OpenShiftOperatorInstaller, 'install_operator') as mock_install:
            mock_install.return_value = (0, "Success", "")
            
            result = OpenShiftOperatorInstaller.install_servicemeshoperator()
            
            assert result[0] == 0
            mock_install.assert_called_once_with('servicemeshoperator')
    
    def test_install_authorino_operator(self):
        """Test Authorino operator installation"""
        with patch.object(OpenShiftOperatorInstaller, 'install_operator') as mock_install:
            mock_install.return_value = (0, "Success", "")
            
            result = OpenShiftOperatorInstaller.install_authorino_operator()
            
            assert result[0] == 0
            mock_install.assert_called_once_with('authorino-operator')
    
    def test_install_cert_manager_operator(self):
        """Test cert-manager operator installation"""
        with patch.object(OpenShiftOperatorInstaller, 'install_operator') as mock_install:
            mock_install.return_value = (0, "Success", "")
            
            result = OpenShiftOperatorInstaller.install_openshift_cert_manager_operator()
            
            assert result[0] == 0
            mock_install.assert_called_once_with('openshift-cert-manager-operator')
    
    def test_install_kueue_operator(self):
        """Test Kueue operator installation"""
        with patch.object(OpenShiftOperatorInstaller, 'install_operator') as mock_install:
            mock_install.return_value = (0, "Success", "")
            
            result = OpenShiftOperatorInstaller.install_kueue_operator()
            
            assert result[0] == 0
            mock_install.assert_called_once_with('kueue-operator')
    
    def test_install_keda_operator(self):
        """Test KEDA operator installation"""
        with patch.object(OpenShiftOperatorInstaller, 'install_operator') as mock_install:
            mock_install.return_value = (0, "Success", "")
            
            result = OpenShiftOperatorInstaller.install_openshift_custom_metrics_autoscaler_operator()
            
            assert result[0] == 0
            mock_install.assert_called_once_with('openshift-custom-metrics-autoscaler-operator')
    
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.utils.wait_for_resource_for_specific_status')
    @patch('rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.deploy_dsc_dsci')
    def test_install_rhoai_operator_success(self, mock_deploy_dsc_dsci, mock_wait, mock_apply):
        """Test successful RHOAI operator installation"""
        mock_apply.return_value = (0, "applied", "")
        mock_wait.return_value = (True, "Succeeded", "")
        mock_deploy_dsc_dsci.return_value = None
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_rhoai_operator(
            rhoai_image="test-image:latest",
            rhoai_channel="stable",
            create_dsc_dsci=True
        )
        
        assert rc == 0
        assert "successfully" in stdout.lower()
        mock_deploy_dsc_dsci.assert_called_once()
    
    @patch('rhoshift.utils.utils.apply_manifest')
    def test_install_rhoai_operator_manifest_failure(self, mock_apply):
        """Test RHOAI operator installation with manifest failure"""
        mock_apply.side_effect = Exception("Manifest failed")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_rhoai_operator(
            rhoai_image="test-image:latest",
            rhoai_channel="stable"
        )
        
        assert rc == 1
        assert "failed" in stderr.lower()
    
    @patch('rhoshift.utils.utils.run_command')
    def test_force_delete_rhoai_dsc_dsci(self, mock_run_command):
        """Test force deletion of RHOAI DSC/DSCI resources"""
        mock_run_command.return_value = (0, "deleted", "")
        
        results = OpenShiftOperatorInstaller.force_delete_rhoai_dsc_dsci()
        
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Check that deletion commands were called
        assert mock_run_command.call_count > 0
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.utils.wait_for_resource_for_specific_status')
    @patch('time.sleep')
    def test_deploy_dsc_dsci_success(self, mock_sleep, mock_wait, mock_apply, mock_run_command):
        """Test successful DSC/DSCI deployment"""
        # Setup mocks
        mock_run_command.return_value = (0, "NOT_FOUND", "")  # No existing DSCI
        mock_apply.return_value = (0, "applied", "")
        mock_wait.return_value = (True, "Ready", "")
        
        # Call the method
        OpenShiftOperatorInstaller.deploy_dsc_dsci(
            channel="stable",
            kserve_raw=False,
            create_dsc_dsci=False
        )
        
        # Verify DSCI and DSC were applied
        assert mock_apply.call_count >= 2  # DSCI and DSC
        mock_wait.assert_called()
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('time.sleep')
    def test_deploy_dsc_dsci_with_existing_conflict(self, mock_sleep, mock_apply, mock_run_command):
        """Test DSC/DSCI deployment with existing DSCI conflict"""
        # Setup existing DSCI with different monitoring namespace
        mock_run_command.return_value = (0, "redhat-ods-monitoring", "")
        mock_apply.return_value = (0, "applied", "")
        
        # Should not apply DSCI due to conflict
        OpenShiftOperatorInstaller.deploy_dsc_dsci(
            channel="odh-nightlies",  # This would prefer opendatahub namespace
            create_dsc_dsci=False
        )
        
        # Should still apply DSC but not DSCI
        assert mock_apply.call_count >= 1
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.force_delete_rhoai_dsc_dsci')
    def test_deploy_dsc_dsci_with_recreation(self, mock_force_delete, mock_apply, mock_run_command):
        """Test DSC/DSCI deployment with forced recreation"""
        mock_run_command.return_value = (0, "existing", "")
        mock_apply.return_value = (0, "applied", "")
        mock_force_delete.return_value = {"delete_dsc": {"status": "success"}}
        
        OpenShiftOperatorInstaller.deploy_dsc_dsci(
            channel="stable",
            create_dsc_dsci=True  # Force recreation
        )
        
        mock_force_delete.assert_called_once()
        assert mock_apply.call_count >= 2  # DSCI and DSC
    
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('time.sleep')
    def test_deploy_dsc_dsci_webhook_certificate_retry(self, mock_sleep, mock_apply):
        """Test DSC/DSCI deployment with webhook certificate retry logic"""
        # First attempt fails with certificate error, second succeeds
        mock_apply.side_effect = [
            Exception("certificate has expired or is not yet valid"),
            (0, "applied", ""),  # DSCI succeeds on retry
            (0, "applied", "")   # DSC succeeds
        ]
        
        with patch('rhoshift.utils.utils.run_command') as mock_run_command:
            mock_run_command.return_value = (0, "NOT_FOUND", "")
            
            with patch('rhoshift.utils.utils.wait_for_resource_for_specific_status') as mock_wait:
                mock_wait.return_value = (True, "Ready", "")
                
                OpenShiftOperatorInstaller.deploy_dsc_dsci(
                    channel="stable",
                    create_dsc_dsci=False
                )
        
        # Should have retried DSCI application
        assert mock_apply.call_count == 3  # Failed DSCI, successful DSCI, DSC
        mock_sleep.assert_called()  # Sleep for retry
    
    @patch('rhoshift.utils.utils.apply_manifest')
    def test_deploy_dsc_dsci_immutable_field_error(self, mock_apply):
        """Test DSC/DSCI deployment with immutable field error"""
        mock_apply.side_effect = Exception("MonitoringNamespace is immutable")
        
        with patch('rhoshift.utils.utils.run_command') as mock_run_command:
            mock_run_command.return_value = (0, "NOT_FOUND", "")
            
            with pytest.raises(Exception) as excinfo:
                OpenShiftOperatorInstaller.deploy_dsc_dsci(
                    channel="stable",
                    create_dsc_dsci=False
                )
            
            assert "immutable" in str(excinfo.value).lower()
    
    def test_deploy_dsc_dsci_with_kueue_management_state(self):
        """Test DSC/DSCI deployment with Kueue management state"""
        with patch('rhoshift.utils.utils.run_command') as mock_run_command:
            with patch('rhoshift.utils.utils.apply_manifest') as mock_apply:
                with patch('rhoshift.utils.utils.wait_for_resource_for_specific_status') as mock_wait:
                    mock_run_command.return_value = (0, "NOT_FOUND", "")
                    mock_apply.return_value = (0, "applied", "")
                    mock_wait.return_value = (True, "Ready", "")
                    
                    with patch('time.sleep'):
                        OpenShiftOperatorInstaller.deploy_dsc_dsci(
                            channel="stable",
                            kueue_management_state="Managed"
                        )
        
        # Verify DSC was applied with Kueue configuration
        dsc_calls = [call for call in mock_apply.call_args_list if 'DataScienceCluster' in str(call)]
        assert len(dsc_calls) > 0
    
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_install_all_and_wait(self, mock_executor):
        """Test installing all operators in parallel"""
        # Mock the executor and futures
        mock_future = Mock()
        mock_future.result.return_value = (0, "Success", "")
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        
        results = OpenShiftOperatorInstaller.install_all_and_wait()
        
        assert isinstance(results, dict)
        # Should have attempted to install multiple operators
        mock_executor.return_value.__enter__.return_value.submit.assert_called()
    
    @patch('rhoshift.utils.utils.run_command')
    def test_uninstall_operator_success(self, mock_run_command):
        """Test successful operator uninstallation"""
        mock_run_command.return_value = (0, "uninstalled", "")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.uninstall_operator(
            'test-operator',
            'test-namespace'
        )
        
        assert rc == 0
        assert "uninstalled" in stdout
        mock_run_command.assert_called()
    
    @patch('rhoshift.utils.utils.run_command')
    def test_uninstall_operator_failure(self, mock_run_command):
        """Test failed operator uninstallation"""
        mock_run_command.return_value = (1, "", "Uninstall failed")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.uninstall_operator(
            'test-operator',
            'test-namespace'
        )
        
        assert rc == 1
        assert stderr == "Uninstall failed"
    
    def test_uninstall_operator_exception(self):
        """Test operator uninstallation with exception"""
        with patch('rhoshift.utils.utils.run_command') as mock_run_command:
            mock_run_command.side_effect = Exception("Unexpected error")
            
            with pytest.raises(Exception) as excinfo:
                OpenShiftOperatorInstaller.uninstall_operator(
                    'test-operator',
                    'test-namespace'
                )
            
            assert "Unexpected error" in str(excinfo.value)


class TestOperatorManifestGeneration:
    """Test cases for operator manifest generation"""
    
    def test_operator_manifest_content(self):
        """Test that operator manifests contain required content"""
        configs = OpenShiftOperatorInstaller.get_operator_configs()
        
        for operator_name, config in configs.items():
            manifest = config['manifest']
            
            # Basic YAML structure
            assert 'apiVersion: operators.coreos.com/v1alpha1' in manifest
            assert 'kind: Subscription' in manifest
            assert f'name: {operator_name}' in manifest
            assert f'namespace: {config["namespace"]}' in manifest
            
            # Required subscription fields
            assert 'spec:' in manifest
            assert 'channel:' in manifest
            assert 'source:' in manifest
            assert 'sourceNamespace:' in manifest
    
    def test_namespace_manifest_generation(self):
        """Test namespace manifest generation"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        
        manifest_gen = OpenShiftOperatorInstallManifest()
        namespace_manifest = manifest_gen.generate_namespace_manifest('test-namespace')
        
        assert 'apiVersion: v1' in namespace_manifest
        assert 'kind: Namespace' in namespace_manifest
        assert 'name: test-namespace' in namespace_manifest


class TestRHOAISpecificFeatures:
    """Test cases for RHOAI-specific features"""
    
    @patch('rhoshift.utils.utils.run_command')
    def test_kueue_dsc_integration_existing_dsc(self, mock_run_command):
        """Test Kueue DSC integration with existing DSC"""
        # Mock existing DSC
        mock_run_command.side_effect = [
            (0, 'default-dsc', ''),  # DSC exists
            (0, 'patched', ''),      # Patch successful
        ]
        
        from rhoshift.utils.operator.operator import update_kueue_in_dsc
        
        result = update_kueue_in_dsc('Managed')
        
        assert result[0] == 0
        assert mock_run_command.call_count == 2
    
    @patch('rhoshift.utils.utils.run_command')
    def test_kueue_dsc_integration_no_existing_dsc(self, mock_run_command):
        """Test Kueue DSC integration without existing DSC"""
        # Mock no existing DSC
        mock_run_command.return_value = (1, '', 'not found')
        
        from rhoshift.utils.operator.operator import update_kueue_in_dsc
        
        result = update_kueue_in_dsc('Managed')
        
        # Should indicate no DSC found
        assert result[0] == 1
        assert 'not found' in result[2] or 'No existing DSC' in result[1]


class TestErrorHandlingAndEdgeCases:
    """Test cases for error handling and edge cases"""
    
    def test_install_operator_invalid_operator(self):
        """Test installing invalid operator name"""
        with pytest.raises(KeyError):
            OpenShiftOperatorInstaller.install_operator('invalid-operator-name')
    
    @patch('rhoshift.utils.utils.apply_manifest')
    def test_install_operator_manifest_timeout(self, mock_apply):
        """Test operator installation with manifest application timeout"""
        import subprocess
        mock_apply.side_effect = subprocess.TimeoutExpired('oc', 30)
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_operator(
            'serverless-operator'
        )
        
        assert rc == 1
        assert "timeout" in stderr.lower() or "failed" in stderr.lower()
    
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.utils.wait_for_resource_for_specific_status')
    def test_install_operator_partial_success(self, mock_wait, mock_apply):
        """Test operator installation with partial success"""
        mock_apply.return_value = (0, "applied", "")
        mock_wait.return_value = (False, "Installing", "Still installing")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_operator(
            'serverless-operator',
            timeout=1  # Very short timeout
        )
        
        assert rc == 1
        assert "timeout" in stderr.lower() or "failed" in stderr.lower()
    
    def test_install_operator_with_empty_config(self):
        """Test operator installation with minimal configuration"""
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_operator(
            'serverless-operator'
        )
        
        # Should not crash even with minimal config
        assert isinstance(rc, int)
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)


class TestPerformanceAndConcurrency:
    """Test cases for performance and concurrency"""
    
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_parallel_installation_performance(self, mock_executor):
        """Test parallel installation performance"""
        # Mock successful parallel execution
        mock_future = Mock()
        mock_future.result.return_value = (0, "Success", "")
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        
        import time
        start_time = time.time()
        
        results = OpenShiftOperatorInstaller.install_all_and_wait()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly with mocked execution
        assert duration < 5.0
        assert isinstance(results, dict)
    
    def test_memory_efficiency_with_large_manifests(self):
        """Test memory efficiency with large manifests"""
        # Generate a large manifest
        large_manifest_content = "test: data\n" * 10000
        
        with patch('rhoshift.utils.constants.OpenShiftOperatorInstallManifest.generate_operator_manifest') as mock_gen:
            mock_gen.return_value = large_manifest_content
            
            configs = OpenShiftOperatorInstaller.get_operator_configs()
            
            # Should handle large manifests without memory issues
            assert len(configs) > 0
            for config in configs.values():
                assert len(config['manifest']) > 0


class TestIntegrationScenarios:
    """Integration test scenarios"""
    
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.utils.wait_for_resource_for_specific_status')
    @patch('time.sleep')
    def test_complete_rhoai_installation_workflow(self, mock_sleep, mock_wait, mock_apply):
        """Test complete RHOAI installation workflow"""
        # Setup successful responses
        mock_apply.return_value = (0, "applied", "")
        mock_wait.return_value = (True, "Ready", "")
        
        with patch('rhoshift.utils.utils.run_command') as mock_run_command:
            mock_run_command.return_value = (0, "NOT_FOUND", "")
            
            # Install RHOAI with DSC/DSCI
            rc, stdout, stderr = OpenShiftOperatorInstaller.install_rhoai_operator(
                rhoai_image="test-image:latest",
                rhoai_channel="stable",
                create_dsc_dsci=True,
                kueue_management_state="Managed"
            )
        
        assert rc == 0
        assert "successfully" in stdout.lower()
        
        # Verify multiple manifest applications (CatalogSource, Subscription, DSCI, DSC)
        assert mock_apply.call_count >= 4
    
    @patch('rhoshift.utils.utils.apply_manifest')
    @patch('rhoshift.utils.utils.wait_for_resource_for_specific_status')
    def test_operator_installation_with_dependencies(self, mock_wait, mock_apply):
        """Test operator installation that has dependencies"""
        mock_apply.return_value = (0, "applied", "")
        mock_wait.return_value = (True, "Succeeded", "")
        
        # Test Kueue which depends on cert-manager
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_kueue_operator()
        
        assert rc == 0
        assert "successfully" in stdout.lower()
    
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_batch_operator_installation(self, mock_executor):
        """Test batch installation of multiple operators"""
        # Mock successful batch execution
        mock_future = Mock()
        mock_future.result.return_value = (0, "Success", "")
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        
        results = OpenShiftOperatorInstaller.install_all_and_wait()
        
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Should have attempted parallel installation
        mock_executor.return_value.__enter__.return_value.submit.assert_called()
