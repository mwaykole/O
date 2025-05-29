import pytest
from rhoshift.cli.args import parse_args
from unittest.mock import patch

@pytest.fixture
def mock_args():
    """Fixture to provide mock command line arguments"""
    with patch('sys.argv', ['script.py']):
        return parse_args()

@pytest.fixture
def sample_config():
    """Fixture to provide a sample configuration dictionary"""
    return {
        'oc_binary': 'oc',
        'max_retries': 3,
        'retry_delay': 10,
        'timeout': 300,
        'rhoai_image': 'quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.20-nightly',
        'rhoai_channel': 'stable',
        'raw': False,
        'create_dsc_dsci': False
    }

