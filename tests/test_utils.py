"""
Comprehensive tests for rhoshift.utils.utils module.
"""

import pytest
import subprocess
import tempfile
import os
from unittest.mock import patch, Mock, mock_open, call
from rhoshift.utils.utils import (
    run_command,
    apply_manifest,
    wait_for_resource_for_specific_status,
    check_oc_connectivity,
    validate_oc_binary
)


class TestRunCommand:
    """Test cases for run_command function"""
    
    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='success output',
            stderr=''
        )
        
        rc, stdout, stderr = run_command('echo "test"')
        
        assert rc == 0
        assert stdout == 'success output'
        assert stderr == ''
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test failed command execution"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='error message'
        )
        
        rc, stdout, stderr = run_command('false')
        
        assert rc == 1
        assert stdout == ''
        assert stderr == 'error message'
    
    @patch('subprocess.run')
    def test_run_command_with_timeout(self, mock_run):
        """Test command execution with timeout"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='output',
            stderr=''
        )
        
        rc, stdout, stderr = run_command('echo "test"', timeout=30)
        
        assert rc == 0
        call_args = mock_run.call_args
        assert call_args[1]['timeout'] == 30
    
    @patch('subprocess.run')
    def test_run_command_timeout_exception(self, mock_run):
        """Test command execution timeout exception"""
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 30)
        
        rc, stdout, stderr = run_command('sleep 60', timeout=30)
        
        assert rc == 124  # Timeout exit code
        assert 'Command timed out' in stderr
    
    @patch('subprocess.run')
    def test_run_command_with_retries(self, mock_run):
        """Test command execution with retries"""
        # First two calls fail, third succeeds
        mock_run.side_effect = [
            Mock(returncode=1, stdout='', stderr='error1'),
            Mock(returncode=1, stdout='', stderr='error2'),
            Mock(returncode=0, stdout='success', stderr='')
        ]
        
        rc, stdout, stderr = run_command('flaky-command', max_retries=3, retry_delay=0.1)
        
        assert rc == 0
        assert stdout == 'success'
        assert mock_run.call_count == 3
    
    @patch('subprocess.run')
    def test_run_command_all_retries_fail(self, mock_run):
        """Test command execution when all retries fail"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='persistent error'
        )
        
        rc, stdout, stderr = run_command('failing-command', max_retries=3, retry_delay=0.1)
        
        assert rc == 1
        assert stderr == 'persistent error'
        assert mock_run.call_count == 3
    
    @patch('subprocess.run')
    @patch('logging.getLogger')
    def test_run_command_logging(self, mock_logger, mock_run):
        """Test command execution with logging"""
        logger_instance = Mock()
        mock_logger.return_value = logger_instance
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout='output',
            stderr=''
        )
        
        run_command('echo "test"', log_output=True)
        
        # Verify logging was attempted
        assert logger_instance.debug.called or logger_instance.info.called
    
    @patch('subprocess.run')
    def test_run_command_exception_handling(self, mock_run):
        """Test command execution exception handling"""
        mock_run.side_effect = Exception("Unexpected error")
        
        rc, stdout, stderr = run_command('bad-command')
        
        assert rc != 0
        assert 'Unexpected error' in stderr


class TestApplyManifest:
    """Test cases for apply_manifest function"""
    
    @patch('rhoshift.utils.utils.run_command')
    def test_apply_manifest_success(self, mock_run_command):
        """Test successful manifest application"""
        mock_run_command.return_value = (0, 'applied', '')
        
        result = apply_manifest('test: manifest')
        
        assert result == (0, 'applied', '')
        mock_run_command.assert_called_once()
        
        # Check that the command includes the manifest
        call_args = mock_run_command.call_args[0][0]
        assert 'oc apply -f -' in call_args
    
    @patch('rhoshift.utils.utils.run_command')
    def test_apply_manifest_failure(self, mock_run_command):
        """Test failed manifest application"""
        mock_run_command.return_value = (1, '', 'apply failed')
        
        with pytest.raises(Exception) as excinfo:
            apply_manifest('invalid: manifest')
        
        assert 'Manifest application failed' in str(excinfo.value)
    
    @patch('rhoshift.utils.utils.run_command')
    def test_apply_manifest_with_retries(self, mock_run_command):
        """Test manifest application with retries"""
        # First call fails, second succeeds
        mock_run_command.side_effect = [
            (1, '', 'temporary error'),
            (0, 'applied', '')
        ]
        
        result = apply_manifest('test: manifest', max_retries=2, retry_delay=0.1)
        
        assert result == (0, 'applied', '')
        assert mock_run_command.call_count == 2
    
    @patch('rhoshift.utils.utils.run_command')
    def test_apply_manifest_custom_oc_binary(self, mock_run_command):
        """Test manifest application with custom oc binary"""
        mock_run_command.return_value = (0, 'applied', '')
        
        apply_manifest('test: manifest', oc_binary='/custom/oc')
        
        call_args = mock_run_command.call_args[0][0]
        assert '/custom/oc apply -f -' in call_args
    
    @patch('rhoshift.utils.utils.run_command')
    def test_apply_manifest_with_timeout(self, mock_run_command):
        """Test manifest application with timeout"""
        mock_run_command.return_value = (0, 'applied', '')
        
        apply_manifest('test: manifest', timeout=120)
        
        call_args = mock_run_command.call_args
        assert call_args[1]['timeout'] == 120


class TestWaitForResourceForSpecificStatus:
    """Test cases for wait_for_resource_for_specific_status function"""
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('time.sleep')
    def test_wait_for_resource_success(self, mock_sleep, mock_run_command):
        """Test waiting for resource with successful status"""
        mock_run_command.return_value = (0, 'Ready', '')
        
        success, output, error = wait_for_resource_for_specific_status(
            status='Ready',
            cmd='oc get pod test-pod -o jsonpath="{.status.phase}"',
            timeout=60,
            interval=5
        )
        
        assert success is True
        assert output == 'Ready'
        assert error == ''
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('time.sleep')
    def test_wait_for_resource_timeout(self, mock_sleep, mock_run_command):
        """Test waiting for resource with timeout"""
        mock_run_command.return_value = (0, 'Pending', '')
        
        success, output, error = wait_for_resource_for_specific_status(
            status='Ready',
            cmd='oc get pod test-pod -o jsonpath="{.status.phase}"',
            timeout=10,
            interval=5
        )
        
        assert success is False
        assert output == 'Pending'
        assert 'timed out' in error.lower()
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('time.sleep')
    def test_wait_for_resource_case_sensitive(self, mock_sleep, mock_run_command):
        """Test waiting for resource with case sensitivity"""
        mock_run_command.return_value = (0, 'ready', '')
        
        # Case sensitive - should fail
        success, output, error = wait_for_resource_for_specific_status(
            status='Ready',
            cmd='oc get pod test-pod -o jsonpath="{.status.phase}"',
            timeout=10,
            interval=5,
            case_sensitive=True
        )
        
        assert success is False
        assert output == 'ready'
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('time.sleep')
    def test_wait_for_resource_case_insensitive(self, mock_sleep, mock_run_command):
        """Test waiting for resource without case sensitivity"""
        mock_run_command.return_value = (0, 'ready', '')
        
        # Case insensitive - should succeed
        success, output, error = wait_for_resource_for_specific_status(
            status='Ready',
            cmd='oc get pod test-pod -o jsonpath="{.status.phase}"',
            timeout=60,
            interval=5,
            case_sensitive=False
        )
        
        assert success is True
        assert output == 'ready'
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('time.sleep')
    def test_wait_for_resource_command_failure(self, mock_sleep, mock_run_command):
        """Test waiting for resource when command fails"""
        mock_run_command.return_value = (1, '', 'command failed')
        
        success, output, error = wait_for_resource_for_specific_status(
            status='Ready',
            cmd='oc get pod nonexistent-pod',
            timeout=10,
            interval=5
        )
        
        assert success is False
        assert error == 'command failed'
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('time.sleep')
    def test_wait_for_resource_eventual_success(self, mock_sleep, mock_run_command):
        """Test waiting for resource that eventually succeeds"""
        # First call returns Pending, second returns Ready
        mock_run_command.side_effect = [
            (0, 'Pending', ''),
            (0, 'Ready', '')
        ]
        
        success, output, error = wait_for_resource_for_specific_status(
            status='Ready',
            cmd='oc get pod test-pod -o jsonpath="{.status.phase}"',
            timeout=60,
            interval=5
        )
        
        assert success is True
        assert output == 'Ready'
        assert mock_run_command.call_count == 2


class TestCheckOcConnectivity:
    """Test cases for check_oc_connectivity function"""
    
    @patch('rhoshift.utils.utils.run_command')
    def test_check_oc_connectivity_success(self, mock_run_command):
        """Test successful oc connectivity check"""
        mock_run_command.return_value = (0, 'system:admin', '')
        
        result = check_oc_connectivity()
        
        assert result is True
        mock_run_command.assert_called_once_with('oc whoami', timeout=30)
    
    @patch('rhoshift.utils.utils.run_command')
    def test_check_oc_connectivity_failure(self, mock_run_command):
        """Test failed oc connectivity check"""
        mock_run_command.return_value = (1, '', 'connection failed')
        
        result = check_oc_connectivity()
        
        assert result is False
    
    @patch('rhoshift.utils.utils.run_command')
    def test_check_oc_connectivity_custom_binary(self, mock_run_command):
        """Test oc connectivity check with custom binary"""
        mock_run_command.return_value = (0, 'user', '')
        
        result = check_oc_connectivity('/custom/oc')
        
        assert result is True
        mock_run_command.assert_called_once_with('/custom/oc whoami', timeout=30)
    
    @patch('rhoshift.utils.utils.run_command')
    def test_check_oc_connectivity_timeout(self, mock_run_command):
        """Test oc connectivity check with timeout"""
        mock_run_command.return_value = (124, '', 'timeout')
        
        result = check_oc_connectivity(timeout=10)
        
        assert result is False
        mock_run_command.assert_called_once_with('oc whoami', timeout=10)


class TestValidateOcBinary:
    """Test cases for validate_oc_binary function"""
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_oc_binary_success(self, mock_run_command):
        """Test successful oc binary validation"""
        mock_run_command.return_value = (0, 'Client Version: 4.12.0', '')
        
        result = validate_oc_binary()
        
        assert result is True
        mock_run_command.assert_called_once_with('oc version --client', timeout=30)
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_oc_binary_failure(self, mock_run_command):
        """Test failed oc binary validation"""
        mock_run_command.return_value = (127, '', 'command not found')
        
        result = validate_oc_binary()
        
        assert result is False
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_oc_binary_custom_path(self, mock_run_command):
        """Test oc binary validation with custom path"""
        mock_run_command.return_value = (0, 'Client Version: 4.12.0', '')
        
        result = validate_oc_binary('/custom/path/oc')
        
        assert result is True
        mock_run_command.assert_called_once_with('/custom/path/oc version --client', timeout=30)
    
    @patch('rhoshift.utils.utils.run_command')
    def test_validate_oc_binary_exception(self, mock_run_command):
        """Test oc binary validation with exception"""
        mock_run_command.side_effect = Exception("Unexpected error")
        
        result = validate_oc_binary()
        
        assert result is False


class TestIntegrationScenarios:
    """Integration test scenarios combining multiple functions"""
    
    @patch('rhoshift.utils.utils.run_command')
    def test_full_operator_installation_workflow(self, mock_run_command):
        """Test a complete operator installation workflow"""
        # Mock successful responses for the workflow
        mock_run_command.side_effect = [
            (0, 'system:admin', ''),  # oc whoami
            (0, 'Client Version: 4.12.0', ''),  # oc version
            (0, 'namespace/test-ns created', ''),  # namespace creation
            (0, 'subscription.operators.coreos.com/test-operator created', ''),  # subscription
            (0, 'Succeeded', ''),  # operator status check
        ]
        
        # Validate oc binary
        assert validate_oc_binary() is True
        
        # Check connectivity
        assert check_oc_connectivity() is True
        
        # Apply namespace manifest
        namespace_manifest = """
apiVersion: v1
kind: Namespace
metadata:
  name: test-ns
"""
        result = apply_manifest(namespace_manifest)
        assert result[0] == 0
        
        # Apply operator subscription
        operator_manifest = """
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: test-operator
  namespace: test-ns
spec:
  channel: stable
  name: test-operator
  source: redhat-operators
"""
        result = apply_manifest(operator_manifest)
        assert result[0] == 0
        
        # Wait for operator to be ready
        success, output, error = wait_for_resource_for_specific_status(
            status='Succeeded',
            cmd='oc get csv -n test-ns -o jsonpath="{.items[0].status.phase}"',
            timeout=300,
            interval=10
        )
        assert success is True
        assert output == 'Succeeded'
