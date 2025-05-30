import pytest
from unittest.mock import patch, MagicMock
from rhoshift.cli.commands import install_operator, install_operators

@pytest.fixture
def mock_oc():
    """Fixture to mock oc command execution"""
    with patch('rhoshift.utils.operator.oc.execute_command') as mock:
        yield mock

def test_install_operator_success(mock_oc):
    """Test successful operator installation"""
    mock_oc.return_value = (0, "Success", "")
    config = {
        'oc_binary': 'oc',
        'max_retries': 3,
        'retry_delay': 1,
        'timeout': 300
    }
    result = install_operator('serverless', config)
    assert result is True
    assert mock_oc.called

def test_install_operator_failure(mock_oc):
    """Test failed operator installation"""
    mock_oc.return_value = (1, "", "Error")
    config = {
        'oc_binary': 'oc',
        'max_retries': 3,
        'retry_delay': 1,
        'timeout': 300
    }
    result = install_operator('serverless', config)
    assert result is False

def test_install_operator_retry(mock_oc):
    """Test operator installation with retries"""
    mock_oc.side_effect = [
        (1, "", "Error"),
        (1, "", "Error"),
        (0, "Success", "")
    ]
    config = {
        'oc_binary': 'oc',
        'max_retries': 3,
        'retry_delay': 1,
        'timeout': 300
    }
    result = install_operator('serverless', config)
    assert result is True
    assert mock_oc.call_count == 3

def test_install_operators_success(mock_oc):
    """Test successful installation of multiple operators"""
    mock_oc.return_value = (0, "Success", "")
    config = {
        'oc_binary': 'oc',
        'max_retries': 3,
        'retry_delay': 1,
        'timeout': 300
    }
    selected_ops = {
        'serverless': True,
        'servicemesh': True,
        'authorino': False,
        'rhoai': False
    }
    result = install_operators(selected_ops, config)
    assert result is True
    assert mock_oc.call_count == 2  # Called for each selected operator

def test_install_operators_partial_failure(mock_oc):
    """Test installation of multiple operators with partial failure"""
    mock_oc.side_effect = [
        (0, "Success", ""),  # serverless succeeds
        (1, "", "Error")     # servicemesh fails
    ]
    config = {
        'oc_binary': 'oc',
        'max_retries': 3,
        'retry_delay': 1,
        'timeout': 300
    }
    selected_ops = {
        'serverless': True,
        'servicemesh': True,
        'authorino': False,
        'rhoai': False
    }
    result = install_operators(selected_ops, config)
    assert result is False
    assert mock_oc.call_count == 2 