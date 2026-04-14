"""
Comprehensive tests for rhoshift.cli.commands module.
"""

from unittest.mock import Mock, call, patch

import pytest

from rhoshift.cli.commands import install_operator, install_operators
from rhoshift.utils.stability_coordinator import StabilityLevel


class TestInstallOperator:
    """Test cases for install_operator function"""

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_cert_manager_operator"
    )
    def test_install_operator_cert_manager_success(self, mock_install):
        """Test successful cert-manager operator installation"""
        mock_install.return_value = (0, "Installation successful", "")

        config = {
            "oc_binary": "oc",
            "max_retries": 3,
            "retry_delay": 10,
            "timeout": 300,
        }

        result = install_operator("cert-manager", config)

        assert result is True
        mock_install.assert_called_once()

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_kueue_operator"
    )
    def test_install_operator_kueue_success(self, mock_install):
        """Test successful Kueue operator installation"""
        mock_install.return_value = (0, "Installation successful", "")

        config = {"oc_binary": "oc"}
        result = install_operator("kueue", config)

        assert result is True
        mock_install.assert_called_once_with(**config)

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_keda_operator"
    )
    def test_install_operator_keda_success(self, mock_install):
        """Test successful KEDA operator installation"""
        mock_install.return_value = (0, "Installation successful", "")

        config = {"oc_binary": "oc"}
        result = install_operator("keda", config)

        assert result is True
        mock_install.assert_called_once_with(**config)

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhcl_operator"
    )
    def test_install_operator_rhcl_success(self, mock_install):
        """Test successful RHCL operator installation"""
        mock_install.return_value = (0, "Installation successful", "")

        config = {"oc_binary": "oc"}
        result = install_operator("rhcl", config)

        assert result is True
        mock_install.assert_called_once_with(**config)

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_lws_operator"
    )
    def test_install_operator_lws_success(self, mock_install):
        """Test successful LWS operator installation"""
        mock_install.return_value = (0, "Installation successful", "")

        config = {"oc_binary": "oc"}
        result = install_operator("lws", config)

        assert result is True
        mock_install.assert_called_once_with(**config)

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator"
    )
    def test_install_operator_rhoai_success(self, mock_install):
        """Test successful RHOAI operator installation"""
        mock_install.return_value = (0, "Installation successful", "")

        config = {
            "oc_binary": "oc",
            "rhoai_image": "test-image:latest",
            "rhoai_channel": "stable",
            "raw": False,
            "create_dsc_dsci": True,
            "kueue_management_state": "Managed",
        }

        result = install_operator("rhoai", config)

        assert result is True
        mock_install.assert_called_once_with(**config)

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_cert_manager_operator"
    )
    def test_install_operator_failure(self, mock_install):
        """Test failed operator installation"""
        mock_install.return_value = (1, "", "Installation failed")

        config = {"oc_binary": "oc"}
        result = install_operator("cert-manager", config)

        assert result is False

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_cert_manager_operator"
    )
    def test_install_operator_exception(self, mock_install):
        """Test operator installation with exception"""
        mock_install.side_effect = Exception("Unexpected error")

        config = {"oc_binary": "oc"}
        result = install_operator("cert-manager", config)

        assert result is False

    def test_install_operator_invalid_operator(self):
        """Test installation of invalid operator"""
        config = {"oc_binary": "oc"}
        result = install_operator("invalid-operator", config)

        assert result is False

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator"
    )
    def test_install_operator_rhoai_with_all_params(self, mock_install):
        """Test RHOAI operator installation with all parameters"""
        mock_install.return_value = (0, "Installation successful", "")

        config = {
            "oc_binary": "/custom/oc",
            "rhoai_image": "custom-image:v2.0",
            "rhoai_channel": "odh-nightlies",
            "raw": True,
            "create_dsc_dsci": False,
            "kueue_management_state": "Unmanaged",
            "max_retries": 5,
            "timeout": 600,
        }

        result = install_operator("rhoai", config)

        assert result is True
        mock_install.assert_called_once_with(**config)


class TestInstallOperators:
    """Test cases for install_operators function"""

    @patch(
        "rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility"
    )
    @patch(
        "rhoshift.utils.constants.OpenShiftOperatorInstallManifest.validate_operator_compatibility"
    )
    @patch(
        "rhoshift.utils.constants.OpenShiftOperatorInstallManifest.resolve_dependencies"
    )
    @patch("rhoshift.cli.commands.install_operator")
    def test_install_operators_success(
        self, mock_install, mock_resolve, mock_validate, mock_dsci
    ):
        """Test successful installation of multiple operators"""
        # Setup mocks
        mock_dsci.return_value = (True, [])
        mock_validate.return_value = []
        mock_resolve.return_value = [
            "openshift-cert-manager-operator",
            "kueue-operator",
        ]
        mock_install.return_value = True

        selected_ops = {
            "cert-manager": True,
            "kueue": True,
            "keda": False,
            "rhcl": False,
            "lws": False,
            "rhoai": False,
        }

        config = {
            "oc_binary": "oc",
            "max_retries": 3,
            "stability_level": StabilityLevel.BASIC,
        }

        result = install_operators(selected_ops, config)

        assert result is True
        assert mock_install.call_count == 2  # Two operators selected

    @patch(
        "rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility"
    )
    @patch("rhoshift.cli.commands.install_operator")
    def test_install_operators_with_rhoai_dsci_validation(
        self, mock_install, mock_dsci
    ):
        """Test operators installation with RHOAI DSCI validation"""
        mock_dsci.return_value = (True, ["DSCI compatible"])
        mock_install.return_value = True

        selected_ops = {
            "cert-manager": False,
            "kueue": False,
            "keda": False,
            "rhcl": False,
            "lws": False,
            "rhoai": True,
        }

        config = {
            "oc_binary": "oc",
            "rhoai_channel": "stable",
            "create_dsc_dsci": False,
        }

        result = install_operators(selected_ops, config)

        assert result is True
        mock_dsci.assert_called_once_with(selected_ops, config)
        mock_install.assert_called_once_with("rhoai", config)

    @patch(
        "rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility"
    )
    def test_install_operators_dsci_incompatible(self, mock_dsci):
        """Test operators installation with DSCI incompatibility"""
        mock_dsci.return_value = (False, ["DSCI conflict"])

        selected_ops = {"rhoai": True}
        config = {"oc_binary": "oc"}

        result = install_operators(selected_ops, config)

        assert result is False

    @patch(
        "rhoshift.utils.operator.enhanced_operator.install_operators_with_enhanced_stability"
    )
    def test_install_operators_enhanced_batch(self, mock_enhanced):
        """Test operators installation with enhanced batch stability"""
        mock_enhanced.return_value = True

        selected_ops = {
            "cert-manager": True,
            "keda": True,
            "kueue": False,
            "rhcl": False,
            "lws": False,
            "rhoai": False,
        }

        config = {"oc_binary": "oc", "stability_level": StabilityLevel.ENHANCED}

        result = install_operators(selected_ops, config)

        assert result is True
        mock_enhanced.assert_called_once_with(selected_ops, config)

    @patch(
        "rhoshift.utils.operator.enhanced_operator.install_operators_with_enhanced_stability"
    )
    @patch("rhoshift.cli.commands.install_operator")
    def test_install_operators_enhanced_fallback(self, mock_install, mock_enhanced):
        """Test operators installation with enhanced fallback to standard"""
        mock_enhanced.side_effect = Exception("Enhanced installation failed")
        mock_install.return_value = True

        selected_ops = {
            "cert-manager": True,
            "keda": True,
            "kueue": False,
            "rhcl": False,
            "lws": False,
            "rhoai": False,
        }

        config = {"oc_binary": "oc", "stability_level": StabilityLevel.ENHANCED}

        result = install_operators(selected_ops, config)

        assert result is True
        mock_enhanced.assert_called_once()
        # Should fall back to standard installation
        assert mock_install.call_count > 0

    @patch(
        "rhoshift.utils.constants.OpenShiftOperatorInstallManifest.resolve_dependencies"
    )
    @patch("rhoshift.cli.commands.install_operator")
    def test_install_operators_dependency_resolution(self, mock_install, mock_resolve):
        """Test operators installation with dependency resolution"""
        # Kueue depends on cert-manager
        mock_resolve.return_value = [
            "openshift-cert-manager-operator",
            "kueue-operator",
        ]
        mock_install.return_value = True

        selected_ops = {
            "cert-manager": False,  # Not explicitly selected
            "kueue": True,  # But kueue depends on cert-manager
            "keda": False,
            "rhcl": False,
            "lws": False,
            "rhoai": False,
        }

        config = {"oc_binary": "oc"}

        result = install_operators(selected_ops, config)

        assert result is True
        # Should install both cert-manager (dependency) and kueue
        assert mock_install.call_count == 2

    @patch("rhoshift.cli.commands.install_operator")
    def test_install_operators_partial_failure(self, mock_install):
        """Test operators installation with partial failure"""
        # First operator succeeds, second fails
        mock_install.side_effect = [True, False]

        selected_ops = {
            "cert-manager": True,
            "keda": True,
            "kueue": False,
            "rhcl": False,
            "lws": False,
            "rhoai": False,
        }

        config = {"oc_binary": "oc"}

        result = install_operators(selected_ops, config)

        assert result is False
        assert mock_install.call_count == 2

    def test_install_operators_no_operators_selected(self):
        """Test operators installation when no operators are selected"""
        selected_ops = {
            "cert-manager": False,
            "kueue": False,
            "keda": False,
            "rhcl": False,
            "lws": False,
            "rhoai": False,
        }

        config = {"oc_binary": "oc"}

        result = install_operators(selected_ops, config)

        assert result is True  # No operators to install = success

    @patch(
        "rhoshift.utils.constants.OpenShiftOperatorInstallManifest.validate_operator_compatibility"
    )
    @patch("rhoshift.cli.commands.install_operator")
    def test_install_operators_with_warnings(self, mock_install, mock_validate):
        """Test operators installation with compatibility warnings"""
        mock_validate.return_value = ["Warning: potential conflict"]
        mock_install.return_value = True

        selected_ops = {
            "cert-manager": True,
            "keda": True,
            "rhcl": False,
            "lws": False,
            "kueue": False,
            "rhoai": False,
        }

        config = {"oc_binary": "oc"}

        result = install_operators(selected_ops, config)

        assert result is True
        mock_validate.assert_called_once()

    @patch("rhoshift.cli.commands.install_operator")
    def test_install_operators_installation_order(self, mock_install):
        """Test that operators are installed in dependency order"""
        mock_install.return_value = True

        selected_ops = {
            "cert-manager": True,
            "kueue": True,  # Depends on cert-manager
            "keda": False,
            "rhcl": False,
            "lws": False,
            "rhoai": True,  # Should be installed last
        }

        config = {"oc_binary": "oc"}

        result = install_operators(selected_ops, config)

        assert result is True

        # Verify installation calls
        calls = mock_install.call_args_list
        operator_names = [call[0][0] for call in calls]

        # RHOAI should be last due to special handling
        assert operator_names[-1] == "rhoai"

    @patch(
        "rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility"
    )
    def test_install_operators_dsci_validation_exception(self, mock_dsci):
        """Test operators installation with DSCI validation exception"""
        mock_dsci.side_effect = Exception("DSCI validation error")

        selected_ops = {"rhoai": True}
        config = {"oc_binary": "oc"}

        # Should not crash, should continue with warning
        result = install_operators(selected_ops, config)

        # The exact behavior depends on implementation, but it shouldn't crash
        assert isinstance(result, bool)


class TestInstallOperatorsIntegration:
    """Integration tests for install_operators function"""

    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_cert_manager_operator"
    )
    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator"
    )
    def test_complete_installation_workflow(self, mock_rhoai, mock_cert_manager):
        """Test complete installation workflow with multiple operators"""
        mock_cert_manager.return_value = (0, "Cert-manager installed", "")
        mock_rhoai.return_value = (0, "RHOAI installed", "")

        selected_ops = {
            "cert-manager": True,
            "kueue": False,
            "keda": False,
            "rhcl": False,
            "lws": False,
            "rhoai": True,
        }

        config = {
            "oc_binary": "oc",
            "rhoai_image": "test-image:latest",
            "rhoai_channel": "stable",
            "create_dsc_dsci": True,
            "kueue_management_state": "Managed",
        }

        result = install_operators(selected_ops, config)

        assert result is True
        mock_cert_manager.assert_called_once()
        mock_rhoai.assert_called_once()

    @patch(
        "rhoshift.utils.operator.enhanced_operator.EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility"
    )
    @patch(
        "rhoshift.utils.operator.operator.OpenShiftOperatorInstaller.install_rhoai_operator"
    )
    def test_rhoai_with_dsci_conflict_resolution(self, mock_rhoai, mock_dsci):
        """Test RHOAI installation with DSCI conflict resolution"""
        mock_dsci.return_value = (True, ["DSCI will be recreated"])
        mock_rhoai.return_value = (0, "RHOAI installed with new DSCI", "")

        selected_ops = {"rhoai": True}
        config = {
            "oc_binary": "oc",
            "rhoai_channel": "odh-nightlies",
            "create_dsc_dsci": True,  # Force recreation
        }

        result = install_operators(selected_ops, config)

        assert result is True
        mock_dsci.assert_called_once()
        mock_rhoai.assert_called_once()
