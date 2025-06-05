import pytest
from rhoshift.cli.args import parse_args, build_config, select_operators
import sys

def test_parse_args_default():
    """Test parsing arguments with default values"""
    with pytest.MonkeyPatch.context() as m:
        m.setattr(sys, 'argv', ['script.py'])
        args = parse_args()
        assert args.oc_binary == 'oc'
        assert args.retries == 3
        assert args.retry_delay == 10
        assert args.timeout == 300
        assert args.rhoai_channel == 'stable'
        assert args.raw is False
        assert not args.serverless
        assert not args.servicemesh
        assert not args.authorino
        assert not args.rhoai
        assert not args.all
        assert not args.cleanup

def test_parse_args_custom():
    """Test parsing arguments with custom values"""
    with pytest.MonkeyPatch.context() as m:
        m.setattr(sys, 'argv', [
            'script.py',
            '--serverless',
            '--rhoai',
            '--oc-binary', 'custom-oc',
            '--retries', '5',
            '--retry-delay', '20',
            '--timeout', '600',
            '--rhoai-channel', 'fast',
            '--raw', 'True',
            '--rhoai-image', 'custom-image:latest'
        ])
        args = parse_args()
        assert args.serverless
        assert args.rhoai
        assert args.oc_binary == 'custom-oc'
        assert args.retries == 5
        assert args.retry_delay == 20
        assert args.timeout == 600
        assert args.rhoai_channel == 'fast'
        assert args.raw == 'True'
        assert args.rhoai_image == 'custom-image:latest'

def test_build_config():
    """Test building configuration from arguments"""
    with pytest.MonkeyPatch.context() as m:
        m.setattr(sys, 'argv', ['script.py'])
        args = parse_args()
        config = build_config(args)
        assert isinstance(config, dict)
        assert 'oc_binary' in config
        assert 'max_retries' in config
        assert 'retry_delay' in config
        assert 'timeout' in config
        assert 'rhoai_image' in config
        assert 'rhoai_channel' in config
        assert 'raw' in config

def test_select_operators():
    """Test operator selection logic"""
    with pytest.MonkeyPatch.context() as m:
        # Test --all flag
        m.setattr(sys, 'argv', ['script.py', '--all'])
        args = parse_args()
        selected = select_operators(args)
        assert all(selected.values())

        # Test individual operators
        m.setattr(sys, 'argv', ['script.py', '--serverless', '--rhoai'])
        args = parse_args()
        selected = select_operators(args)
        assert selected['serverless']
        assert selected['rhoai']
        assert not selected['servicemesh']
        assert not selected['authorino'] 