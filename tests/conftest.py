import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from rhoshift.cli.args import parse_args
from rhoshift.utils.stability_coordinator import StabilityLevel


@pytest.fixture
def mock_args():
    """Fixture to provide mock command line arguments"""
    with patch("sys.argv", ["script.py"]):
        return parse_args()


@pytest.fixture
def sample_config():
    """Fixture to provide a sample configuration dictionary"""
    return {
        "oc_binary": "oc",
        "max_retries": 3,
        "retry_delay": 10,
        "timeout": 300,
        "rhoai_image": "quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.20-nightly",
        "rhoai_channel": "stable",
        "raw": False,
        "create_dsc_dsci": False,
        "stability_level": StabilityLevel.ENHANCED,
        "enable_health_monitoring": True,
        "enable_auto_recovery": True,
        "kueue_management_state": None,
    }


@pytest.fixture
def enhanced_config():
    """Fixture for enhanced configuration with comprehensive stability"""
    return {
        "oc_binary": "oc",
        "max_retries": 5,
        "retry_delay": 15,
        "timeout": 600,
        "rhoai_image": "quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.25-nightly",
        "rhoai_channel": "odh-nightlies",
        "raw": True,
        "create_dsc_dsci": True,
        "stability_level": StabilityLevel.COMPREHENSIVE,
        "enable_health_monitoring": True,
        "enable_auto_recovery": True,
        "kueue_management_state": "Managed",
    }


@pytest.fixture
def mock_run_command():
    """Mock for run_command utility function"""
    with patch("rhoshift.utils.utils.run_command") as mock:
        mock.return_value = (0, "success", "")
        yield mock


@pytest.fixture
def mock_apply_manifest():
    """Mock for apply_manifest utility function"""
    with patch("rhoshift.utils.utils.apply_manifest") as mock:
        mock.return_value = (0, "success", "")
        yield mock


@pytest.fixture
def mock_oc_command():
    """Mock for oc command execution"""
    with patch("subprocess.run") as mock:
        mock.return_value = Mock(returncode=0, stdout="success", stderr="")
        yield mock


@pytest.fixture
def selected_operators_all():
    """Fixture for all operators selected"""
    return {
        "serverless": True,
        "servicemesh": True,
        "authorino": True,
        "cert-manager": True,
        "kueue": True,
        "keda": True,
        "rhoai": True,
    }


@pytest.fixture
def selected_operators_partial():
    """Fixture for partial operator selection"""
    return {
        "serverless": True,
        "servicemesh": False,
        "authorino": True,
        "cert-manager": False,
        "kueue": True,
        "keda": False,
        "rhoai": False,
    }


@pytest.fixture
def mock_logger():
    """Mock logger fixture"""
    with patch("logging.getLogger") as mock:
        logger_instance = Mock()
        mock.return_value = logger_instance
        yield logger_instance


@pytest.fixture
def temp_manifest_file():
    """Fixture to create a temporary manifest file"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        f.write(
            """
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: test-operator
  namespace: test-namespace
spec:
  channel: stable
  name: test-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
"""
        )
        temp_file = f.name

    yield temp_file

    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def mock_operator_status():
    """Mock operator status responses"""
    return {
        "ready": {"returncode": 0, "stdout": "Succeeded", "stderr": ""},
        "installing": {"returncode": 0, "stdout": "Installing", "stderr": ""},
        "failed": {
            "returncode": 1,
            "stdout": "Failed",
            "stderr": "Installation failed",
        },
    }


@pytest.fixture
def mock_dsci_existing():
    """Mock existing DSCI response"""
    return {"returncode": 0, "stdout": "redhat-ods-monitoring", "stderr": ""}


@pytest.fixture
def mock_dsci_not_found():
    """Mock DSCI not found response"""
    return {"returncode": 0, "stdout": "NOT_FOUND", "stderr": ""}


@pytest.fixture
def mock_health_status():
    """Mock health monitoring responses"""
    return {
        "healthy": {
            "status": "Healthy",
            "components": ["operator", "webhook", "controller"],
            "ready": True,
        },
        "degraded": {
            "status": "Degraded",
            "components": ["operator"],
            "ready": False,
            "issues": ["webhook not ready"],
        },
    }


@pytest.fixture(autouse=True)
def reset_constants():
    """Reset any module-level state between tests"""
    yield
    # Clean up any cached state if needed


@pytest.fixture
def mock_time():
    """Mock time.time() for consistent testing"""
    with patch("time.time") as mock:
        mock.return_value = 1634567890.0  # Fixed timestamp
        yield mock


@pytest.fixture
def mock_sleep():
    """Mock time.sleep() to speed up tests"""
    with patch("time.sleep") as mock:
        yield mock
