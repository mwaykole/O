import pytest
from unittest.mock import patch, MagicMock
from rhoshift.main import main
import sys

def test_main_no_operators_selected():
    """Test main function when no operators are selected"""
    with patch('sys.argv', ['script.py']):
        result = main()
        assert result == 1  # Should return error code

def test_main_single_operator():
    """Test main function with a single operator"""
    with patch('sys.argv', ['script.py', '--serverless']), \
         patch('rhoshift.cli.commands.install_operator') as mock_install:
        mock_install.return_value = True
        result = main()
        assert result == 0  # Should return success code
        mock_install.assert_called_once()

def test_main_multiple_operators():
    """Test main function with multiple operators"""
    with patch('sys.argv', ['script.py', '--serverless', '--rhoai']), \
         patch('rhoshift.cli.commands.install_operators') as mock_install:
        mock_install.return_value = True
        result = main()
        assert result == 0  # Should return success code
        mock_install.assert_called_once()

def test_main_cleanup():
    """Test main function with cleanup flag"""
    with patch('sys.argv', ['script.py', '--cleanup']), \
         patch('rhoshift.utils.operator.cleanup') as mock_cleanup:
        result = main()
        assert result is None  # Cleanup should return None
        mock_cleanup.assert_called_once()

def test_main_installation_failure():
    """Test main function when installation fails"""
    with patch('sys.argv', ['script.py', '--serverless']), \
         patch('rhoshift.cli.commands.install_operator') as mock_install:
        mock_install.return_value = False
        result = main()
        assert result == 1  # Should return error code

def test_main_exception_handling():
    """Test main function exception handling"""
    with patch('sys.argv', ['script.py', '--serverless']), \
         patch('rhoshift.cli.commands.install_operator') as mock_install:
        mock_install.side_effect = Exception("Test error")
        result = main()
        assert result == 1  # Should return error code

def test_main_complex_rhoai_cleanup():
    """Test main function with cleanup, all operators, and RHOAI-specific flags"""
    test_image = "quay.io/rhoai/test-image:latest"
    with patch('sys.argv', [
        'script.py',
        '--cleanup',
        '--all',
        '--rhoai',
        '--rhoai-channel=odh-nightlies',
        f'--rhoai-image={test_image}',
        '--raw=False',
        '--deploy-rhoai-resources'
    ]), \
    patch('rhoshift.utils.operator.cleanup') as mock_cleanup, \
    patch('rhoshift.cli.commands.install_operators') as mock_install:
        
        # Mock successful cleanup
        mock_cleanup.return_value = None
        
        # Mock successful operator installation
        mock_install.return_value = True
        
        result = main()
        
        # Verify cleanup was called
        mock_cleanup.assert_called_once()
        
        # Verify operator installation was attempted with correct config
        mock_install.assert_called_once()
        call_args = mock_install.call_args[0]
        selected_ops = call_args[0]
        config = call_args[1]
        
        # Verify all operators were selected
        assert all(selected_ops.values())
        
        # Verify RHOAI-specific configuration
        assert config['rhoai_channel'] == 'odh-nightlies'
        assert config['rhoai_image'] == test_image
        assert config['raw'] == 'False'
        assert config['create_dsc_dsci'] is True
        
        # Verify return value
        assert result is None  # Cleanup should return None 