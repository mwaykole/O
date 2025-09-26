"""
Fixed unit tests that properly isolate functionality without hitting the cluster.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import sys


class TestArgumentParsingIsolated:
    """Isolated argument parsing tests"""
    
    def test_str_to_bool_all_cases(self):
        """Test str_to_bool function thoroughly"""
        from rhoshift.cli.args import str_to_bool
        
        # True cases
        true_values = ['yes', 'true', 't', 'y', '1', 'YES', 'TRUE']
        for val in true_values:
            assert str_to_bool(val) is True
        
        # False cases  
        false_values = ['no', 'false', 'f', 'n', '0', 'NO', 'FALSE']
        for val in false_values:
            assert str_to_bool(val) is False
        
        # Boolean passthrough
        assert str_to_bool(True) is True
        assert str_to_bool(False) is False
    
    def test_parse_args_basic_operators(self):
        """Test parsing basic operator arguments"""
        from rhoshift.cli.args import parse_args
        
        # Test serverless only
        with patch('sys.argv', ['script.py', '--serverless']):
            args = parse_args()
            assert args.serverless is True
            assert args.rhoai is False
        
        # Test all operators
        with patch('sys.argv', ['script.py', '--all']):
            args = parse_args()
            assert args.all is True
    
    def test_select_operators_logic(self):
        """Test operator selection logic"""
        from rhoshift.cli.args import parse_args, select_operators
        
        # Test all flag
        with patch('sys.argv', ['script.py', '--all']):
            args = parse_args()
            selected = select_operators(args)
            assert all(selected.values())
        
        # Test individual selection
        with patch('sys.argv', ['script.py', '--serverless']):
            args = parse_args()
            selected = select_operators(args)
            assert selected['serverless'] is True
            assert selected['servicemesh'] is False


class TestConstantsIsolated:
    """Isolated constants tests"""
    
    def test_operator_config_dataclass(self):
        """Test OperatorConfig dataclass"""
        from rhoshift.utils.constants import OperatorConfig
        
        config = OperatorConfig(
            name="test-op",
            display_name="Test Operator",
            namespace="test-ns", 
            channel="stable"
        )
        
        assert config.name == "test-op"
        assert config.display_name == "Test Operator"
        assert config.namespace == "test-ns"
        assert config.channel == "stable"
    
    def test_wait_time_constants(self):
        """Test WaitTime constants"""
        from rhoshift.utils.constants import WaitTime
        
        assert WaitTime.WAIT_TIME_10_MIN == 600
        assert WaitTime.WAIT_TIME_5_MIN == 300
        assert WaitTime.WAIT_TIME_1_MIN == 60
        assert WaitTime.WAIT_TIME_30_SEC == 30
    
    def test_manifest_generation_structure(self):
        """Test manifest generation produces valid YAML structure"""
        from rhoshift.utils.constants import get_dsci_manifest, get_dsc_manifest
        
        # Test DSCI
        dsci = get_dsci_manifest()
        assert 'apiVersion:' in dsci
        assert 'kind: DSCInitialization' in dsci
        assert 'metadata:' in dsci
        assert 'spec:' in dsci
        
        # Test DSC
        dsc = get_dsc_manifest()
        assert 'apiVersion:' in dsc
        assert 'kind: DataScienceCluster' in dsc
        assert 'metadata:' in dsc
        assert 'spec:' in dsc
    
    def test_operator_list_functionality(self):
        """Test operator listing"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        
        operators = OpenShiftOperatorInstallManifest.list_operators()
        assert isinstance(operators, list)
        assert len(operators) > 0
        
        # Check some expected operators
        expected = ['serverless-operator', 'servicemeshoperator', 'authorino-operator']
        for op in expected:
            assert op in operators


class TestEnumsAndDataClasses:
    """Test enums and data classes in isolation"""
    
    def test_health_status_enum(self):
        """Test HealthStatus enum"""
        from rhoshift.utils.health_monitor import HealthStatus
        
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"
    
    def test_stability_level_enum(self):
        """Test StabilityLevel enum"""
        from rhoshift.utils.stability_coordinator import StabilityLevel
        
        assert StabilityLevel.BASIC.value == 1
        assert StabilityLevel.ENHANCED.value == 2
        assert StabilityLevel.COMPREHENSIVE.value == 3
        
        # Test value comparisons
        assert StabilityLevel.BASIC.value < StabilityLevel.ENHANCED.value
        assert StabilityLevel.ENHANCED.value < StabilityLevel.COMPREHENSIVE.value
    
    def test_stability_config_creation(self):
        """Test StabilityConfig creation"""
        from rhoshift.utils.stability_coordinator import StabilityConfig, StabilityLevel
        
        # Test default config
        config = StabilityConfig()
        assert config.level == StabilityLevel.ENHANCED
        
        # Test custom config
        custom_config = StabilityConfig(level=StabilityLevel.COMPREHENSIVE)
        assert custom_config.level == StabilityLevel.COMPREHENSIVE


class TestMockingPatterns:
    """Test proper mocking patterns that actually work"""
    
    @patch('subprocess.run')
    def test_subprocess_mocking_pattern(self, mock_subprocess):
        """Test subprocess mocking that actually works"""
        from rhoshift.utils.utils import run_command
        
        # Create proper mock response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'test output'
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result
        
        rc, stdout, stderr = run_command('echo test')
        
        assert rc == 0
        assert 'test' in stdout  # Allow for newlines and variations
        assert stderr == ''
    
    @patch('rhoshift.utils.utils.run_command')
    def test_run_command_direct_mocking(self, mock_run_command):
        """Test direct run_command mocking"""
        from rhoshift.utils.utils import apply_manifest
        
        mock_run_command.return_value = (0, 'applied successfully', '')
        
        result = apply_manifest('test: manifest')
        
        assert result[0] == 0
        assert result[1] == 'applied successfully'
        mock_run_command.assert_called_once()
    
    def test_operator_configs_without_cluster(self):
        """Test operator configs without hitting cluster"""
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller
        
        # This should work without cluster access
        configs = OpenShiftOperatorInstaller.get_operator_configs()
        
        assert isinstance(configs, dict)
        assert len(configs) > 0
        assert 'serverless-operator' in configs
        
        # Verify structure
        serverless_config = configs['serverless-operator']
        assert 'manifest' in serverless_config
        assert 'namespace' in serverless_config
        assert 'display_name' in serverless_config


class TestDSCILogicIsolated:
    """Test DSCI logic in isolation"""
    
    @patch('rhoshift.utils.utils.run_command')
    def test_dsci_compatibility_no_rhoai(self, mock_run_command):
        """Test DSCI compatibility when RHOAI not selected"""
        from rhoshift.utils.operator.enhanced_operator import EnhancedOpenShiftOperatorInstaller
        
        selected_ops = {'serverless': True, 'rhoai': False}
        config = {}
        
        compatible, warnings = EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
        
        assert compatible is True
        assert warnings == []
        # Should not call run_command when RHOAI not selected
        mock_run_command.assert_not_called()
    
    @patch('rhoshift.utils.utils.run_command')
    def test_dsci_compatibility_no_existing_dsci(self, mock_run_command):
        """Test DSCI compatibility when no existing DSCI"""
        from rhoshift.utils.operator.enhanced_operator import EnhancedOpenShiftOperatorInstaller
        
        # Mock no existing DSCI
        mock_run_command.return_value = (0, 'NOT_FOUND', '')
        
        selected_ops = {'rhoai': True}
        config = {'rhoai_channel': 'stable'}
        
        compatible, warnings = EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
        
        assert compatible is True
        assert warnings == []
        mock_run_command.assert_called_once()
    
    @patch('rhoshift.utils.utils.run_command')
    def test_dsci_compatibility_with_conflict(self, mock_run_command):
        """Test DSCI compatibility with namespace conflict"""
        from rhoshift.utils.operator.enhanced_operator import EnhancedOpenShiftOperatorInstaller
        
        # Mock existing DSCI with different namespace
        mock_run_command.return_value = (0, 'redhat-ods-monitoring', '')
        
        selected_ops = {'rhoai': True}
        config = {'rhoai_channel': 'odh-nightlies', 'create_dsc_dsci': False}
        
        compatible, warnings = EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
            selected_ops, config
        )
        
        assert compatible is True
        assert len(warnings) == 1
        assert 'DSCI compatibility' in warnings[0]
        assert 'Using existing configuration' in warnings[0]


class TestFunctionalityWithoutCluster:
    """Test functionality that doesn't require cluster access"""
    
    def test_dependency_resolution(self):
        """Test dependency resolution logic"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        
        # Test Kueue dependency resolution
        resolved = OpenShiftOperatorInstallManifest.resolve_dependencies(['kueue-operator'])
        
        assert 'kueue-operator' in resolved
        assert 'openshift-cert-manager-operator' in resolved
        
        # Dependency should come first
        cert_idx = resolved.index('openshift-cert-manager-operator')
        kueue_idx = resolved.index('kueue-operator')
        assert cert_idx < kueue_idx
    
    def test_operator_compatibility_validation(self):
        """Test operator compatibility validation"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        
        # Test with valid operators
        warnings = OpenShiftOperatorInstallManifest.validate_operator_compatibility([
            'serverless-operator', 'servicemeshoperator'
        ])
        assert isinstance(warnings, list)
        
        # Test with empty list
        warnings = OpenShiftOperatorInstallManifest.validate_operator_compatibility([])
        assert warnings == []
    
    def test_manifest_content_validation(self):
        """Test that manifests contain expected content"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        
        manifest_gen = OpenShiftOperatorInstallManifest()
        
        # Test serverless manifest
        manifest = manifest_gen.generate_operator_manifest('serverless-operator')
        
        required_content = [
            'apiVersion: operators.coreos.com/v1alpha1',
            'kind: Subscription',
            'name: serverless-operator',
            'namespace: openshift-serverless',
            'channel: stable'
        ]
        
        for content in required_content:
            assert content in manifest


class TestErrorHandlingIsolated:
    """Test error handling in isolation"""
    
    def test_invalid_operator_config_error(self):
        """Test proper error for invalid operator config"""
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest
        
        with pytest.raises(ValueError) as excinfo:
            OpenShiftOperatorInstallManifest.get_operator_config('invalid-operator')
        
        assert 'Unknown operator' in str(excinfo.value)
    
    def test_invalid_operator_install_error(self):
        """Test proper error handling for invalid operator installation"""
        from rhoshift.cli.commands import install_operator
        
        # This should raise ValueError, not return False
        with pytest.raises(ValueError) as excinfo:
            install_operator('invalid-operator', {'oc_binary': 'oc'})
        
        assert 'Unknown operator' in str(excinfo.value)
    
    @patch('rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator')
    def test_rhoai_enhanced_error_handling(self, mock_install):
        """Test enhanced RHOAI error handling"""
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller
        
        # Test immutable field error
        mock_install.side_effect = Exception("MonitoringNamespace is immutable")
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_rhoai_operator_enhanced(
            rhoai_image="test:latest",
            rhoai_channel="stable",
            raw=False,
            create_dsc_dsci=False
        )
        
        assert rc == 1
        assert stdout == ""
        assert "DSCI conflict" in stderr
        assert "Use --deploy-rhoai-resources" in stderr


class TestLoggerIsolated:
    """Test logger functionality in isolation"""
    
    def test_logger_creation_and_usage(self):
        """Test logger creation and basic usage"""
        from rhoshift.logger.logger import Logger
        
        # Test getting logger
        logger = Logger.get_logger('test_logger')
        assert logger is not None
        assert logger.name == 'test_logger'
        
        # Test different loggers
        logger2 = Logger.get_logger('test_logger_2')
        assert logger2.name == 'test_logger_2'
        assert logger is not logger2
        
        # Test same name returns same instance
        logger3 = Logger.get_logger('test_logger')
        assert logger is logger3
    
    def test_logger_methods_exist(self):
        """Test that logger has expected methods"""
        from rhoshift.logger.logger import Logger
        
        logger = Logger.get_logger('method_test')
        
        # These methods should exist and be callable
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning') 
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
        
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)
        assert callable(logger.debug)


class TestCleanupFunctionality:
    """Test cleanup functionality"""
    
    def test_cleanup_function_exists(self):
        """Test that cleanup functions exist"""
        from rhoshift.utils.operator.cleanup import cleanup, cleanup_all_operators
        
        assert callable(cleanup)
        assert callable(cleanup_all_operators)
    
    @patch('rhoshift.utils.utils.run_command')
    @patch('os.path.exists')
    @patch('os.chmod')
    def test_cleanup_execution_mocked(self, mock_chmod, mock_exists, mock_run_command):
        """Test cleanup execution with proper mocking"""
        from rhoshift.utils.operator.cleanup import cleanup_all_operators
        
        # Mock file exists
        mock_exists.return_value = True
        # Mock run_command success
        mock_run_command.return_value = (0, 'cleanup completed', '')
        
        # This should not raise an exception
        result = cleanup_all_operators()
        
        # Function should complete (return None or success)
        assert result is None or result == (0, 'cleanup completed', '')


class TestResilientOperationsIsolated:
    """Test resilient operations in isolation"""
    
    def test_execute_resilient_operation_success(self):
        """Test resilient operation success case"""
        from rhoshift.utils.resilience import execute_resilient_operation
        
        def successful_operation():
            return "operation completed"
        
        success, result, warnings = execute_resilient_operation(
            successful_operation,
            "test operation"
        )
        
        assert success is True
        assert result == "operation completed"
        assert isinstance(warnings, list)
    
    def test_execute_resilient_operation_failure(self):
        """Test resilient operation failure case"""
        from rhoshift.utils.resilience import execute_resilient_operation
        
        def failing_operation():
            raise Exception("operation failed")
        
        success, result, warnings = execute_resilient_operation(
            failing_operation,
            "failing operation",
            max_retries=1
        )
        
        assert success is False
        assert isinstance(warnings, list)
        # Result should contain error information
        assert "operation failed" in str(result) or isinstance(result, Exception)


class TestMainFunctionProperlyMocked:
    """Test main function with comprehensive mocking"""
    
    def test_main_no_operators(self):
        """Test main with no operators selected"""
        from rhoshift.main import main
        
        with patch('sys.argv', ['script.py']):
            result = main()
        
        assert result == 1
    
    @patch('rhoshift.utils.resilience.run_preflight_checks')
    @patch('rhoshift.cli.commands.install_operator') 
    @patch('rhoshift.utils.health_monitor.check_operator_health')
    @patch('time.time')
    def test_main_serverless_fully_mocked(self, mock_time, mock_health, mock_install, mock_preflight):
        """Test main with serverless - fully mocked"""
        from rhoshift.main import main
        
        # Mock all external dependencies
        mock_preflight.return_value = (True, [])
        mock_install.return_value = True
        mock_health.return_value = (None, {})  # Health check success
        mock_time.side_effect = [1000.0, 1060.0]  # 60 second duration
        
        with patch('sys.argv', ['script.py', '--serverless']):
            result = main()
        
        assert result == 0
        mock_preflight.assert_called_once()
        mock_install.assert_called_once()
    
    @patch('rhoshift.utils.operator.cleanup.cleanup_all_operators')
    @patch('rhoshift.cli.commands.install_operators')
    @patch('time.time')
    def test_main_cleanup_and_install_mocked(self, mock_time, mock_install, mock_cleanup):
        """Test main with cleanup and install - fully mocked"""
        from rhoshift.main import main
        
        mock_cleanup.return_value = None
        mock_install.return_value = True
        mock_time.side_effect = [1000.0, 1120.0]  # 120 second duration
        
        with patch('sys.argv', ['script.py', '--cleanup', '--serverless']):
            result = main()
        
        assert result == 0
        mock_cleanup.assert_called_once()
        mock_install.assert_called_once()


class TestOperatorInstallationMocked:
    """Test operator installation with proper mocking"""
    
    @patch('rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_operator')
    def test_individual_operator_methods(self, mock_install):
        """Test individual operator installation methods"""
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller
        
        mock_install.return_value = (0, "Installation successful", "")
        
        # Test serverless
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_serverless_operator()
        assert rc == 0
        assert "successful" in stdout.lower()
        
        # Test servicemesh  
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_servicemeshoperator()
        assert rc == 0
        assert "successful" in stdout.lower()
        
        # Should have called install_operator twice
        assert mock_install.call_count == 2
    
    @patch('rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator')
    def test_enhanced_rhoai_success(self, mock_install):
        """Test enhanced RHOAI installation success"""
        from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller
        
        mock_install.return_value = {'status': 'success'}
        
        rc, stdout, stderr = OpenShiftOperatorInstaller.install_rhoai_operator_enhanced(
            rhoai_image="test:latest",
            rhoai_channel="stable",
            raw=False,
            create_dsc_dsci=False
        )
        
        assert rc == 0
        assert "successful" in stdout.lower()
        assert stderr == ""


class TestPackageStructureValidation:
    """Validate package structure and imports"""
    
    def test_core_module_imports(self):
        """Test that core modules import successfully"""
        # These should not raise ImportError
        import rhoshift
        import rhoshift.main
        import rhoshift.cli
        import rhoshift.cli.args
        import rhoshift.cli.commands
        import rhoshift.utils
        import rhoshift.utils.constants
        import rhoshift.utils.operator
        import rhoshift.utils.operator.operator
        import rhoshift.utils.operator.enhanced_operator
        import rhoshift.logger
        
        # All should be importable
        assert all([
            rhoshift, rhoshift.main, rhoshift.cli, rhoshift.cli.args,
            rhoshift.cli.commands, rhoshift.utils, rhoshift.utils.constants,
            rhoshift.utils.operator, rhoshift.utils.operator.operator,
            rhoshift.utils.operator.enhanced_operator, rhoshift.logger
        ])
    
    def test_key_functions_callable(self):
        """Test that key functions are callable"""
        from rhoshift.main import main
        from rhoshift.cli.args import parse_args, build_config, select_operators
        from rhoshift.cli.commands import install_operator, install_operators
        from rhoshift.utils.constants import get_dsci_manifest, get_dsc_manifest
        from rhoshift.utils.resilience import execute_resilient_operation, run_preflight_checks
        from rhoshift.utils.operator.cleanup import cleanup_all_operators
        
        functions = [
            main, parse_args, build_config, select_operators,
            install_operator, install_operators, get_dsci_manifest, 
            get_dsc_manifest, execute_resilient_operation, 
            run_preflight_checks, cleanup_all_operators
        ]
        
        for func in functions:
            assert callable(func), f"Function {func.__name__} is not callable"


class TestConfigurationFlow:
    """Test configuration flow without external dependencies"""
    
    def test_complete_config_workflow_isolated(self):
        """Test complete configuration workflow"""
        from rhoshift.cli.args import parse_args, build_config, select_operators
        
        # Test with minimal args that don't require external validation
        with patch('sys.argv', ['script.py', '--serverless', '--timeout', '600']):
            args = parse_args()
            config = build_config(args)
            selected = select_operators(args)
        
        # Verify parsing
        assert args.serverless is True
        assert args.timeout == 600
        
        # Verify config
        assert config['timeout'] == 600
        assert config['oc_binary'] == 'oc'
        
        # Verify selection
        assert selected['serverless'] is True
        assert selected['servicemesh'] is False
    
    def test_kueue_management_state_handling(self):
        """Test Kueue management state handling"""
        from rhoshift.cli.args import parse_args, select_operators
        
        # Test default Kueue
        with patch('sys.argv', ['script.py', '--kueue']):
            args = parse_args()
            selected = select_operators(args)
        
        assert selected['kueue'] == 'Unmanaged'
        
        # Test explicit Managed
        with patch('sys.argv', ['script.py', '--kueue', 'Managed']):
            args = parse_args()
            selected = select_operators(args)
        
        assert selected['kueue'] == 'Managed'
