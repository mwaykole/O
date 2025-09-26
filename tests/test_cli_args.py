"""
Comprehensive tests for rhoshift.cli.args module.
"""

import argparse
import sys

import pytest

from rhoshift.cli.args import build_config, parse_args, select_operators, str_to_bool


class TestStrToBool:
    """Test cases for str_to_bool function"""

    def test_str_to_bool_true_values(self):
        """Test str_to_bool with true values"""
        true_values = ["yes", "true", "t", "y", "1", "YES", "TRUE", "True"]
        for value in true_values:
            assert str_to_bool(value) is True

    def test_str_to_bool_false_values(self):
        """Test str_to_bool with false values"""
        false_values = ["no", "false", "f", "n", "0", "NO", "FALSE", "False"]
        for value in false_values:
            assert str_to_bool(value) is False

    def test_str_to_bool_boolean_passthrough(self):
        """Test str_to_bool with actual boolean values"""
        assert str_to_bool(True) is True
        assert str_to_bool(False) is False

    def test_str_to_bool_invalid_value(self):
        """Test str_to_bool with invalid values"""
        invalid_values = ["maybe", "invalid", "2", "none"]
        for value in invalid_values:
            with pytest.raises(argparse.ArgumentTypeError):
                str_to_bool(value)


class TestParseArgs:
    """Test cases for parse_args function"""

    def test_parse_args_default(self):
        """Test parsing arguments with default values"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py"])
            args = parse_args()
            assert args.oc_binary == "oc"
            assert args.retries == 3
            assert args.retry_delay == 10
            assert args.timeout == 300
            assert args.rhoai_channel == "stable"
            assert args.raw is False
            assert not args.serverless
            assert not args.servicemesh
            assert not args.authorino
            assert not args.rhoai
            assert not args.all
            assert not args.cleanup
            assert not args.deploy_rhoai_resources
            assert not args.summary
            assert args.kueue is None
            assert not args.keda

    def test_parse_args_all_operators(self):
        """Test parsing arguments with all operators selected"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--all"])
            args = parse_args()
            assert args.all
            assert args.oc_binary == "oc"  # Default should still be set

    def test_parse_args_individual_operators(self):
        """Test parsing arguments with individual operators"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys,
                "argv",
                [
                    "script.py",
                    "--serverless",
                    "--servicemesh",
                    "--authorino",
                    "--cert-manager",
                    "--rhoai",
                    "--keda",
                ],
            )
            args = parse_args()
            assert args.serverless
            assert args.servicemesh
            assert args.authorino
            assert getattr(args, "cert_manager", False)
            assert args.rhoai
            assert args.keda
            assert not args.all

    def test_parse_args_kueue_variations(self):
        """Test parsing Kueue argument variations"""
        # Test Kueue without value (default to Unmanaged)
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--kueue"])
            args = parse_args()
            assert args.kueue == "Unmanaged"

        # Test Kueue with Managed
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--kueue", "Managed"])
            args = parse_args()
            assert args.kueue == "Managed"

        # Test Kueue with Unmanaged
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--kueue", "Unmanaged"])
            args = parse_args()
            assert args.kueue == "Unmanaged"

    def test_parse_args_custom_configuration(self):
        """Test parsing arguments with custom configuration values"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys,
                "argv",
                [
                    "script.py",
                    "--serverless",
                    "--rhoai",
                    "--oc-binary",
                    "/custom/path/oc",
                    "--retries",
                    "5",
                    "--retry-delay",
                    "20",
                    "--timeout",
                    "600",
                    "--rhoai-channel",
                    "odh-nightlies",
                    "--raw",
                    "True",
                    "--rhoai-image",
                    "custom-image:latest",
                ],
            )
            args = parse_args()
            assert args.serverless
            assert args.rhoai
            assert args.oc_binary == "/custom/path/oc"
            assert args.retries == 5
            assert args.retry_delay == 20
            assert args.timeout == 600
            assert args.rhoai_channel == "odh-nightlies"
            assert args.raw == "True"  # String, not boolean
            assert args.rhoai_image == "custom-image:latest"

    def test_parse_args_rhoai_special_flags(self):
        """Test parsing RHOAI-specific flags"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys,
                "argv",
                [
                    "script.py",
                    "--rhoai",
                    "--deploy-rhoai-resources",
                    "--rhoai-channel",
                    "fast",
                    "--raw",
                    "false",
                    "--rhoai-image",
                    "quay.io/test:latest",
                ],
            )
            args = parse_args()
            assert args.rhoai
            assert args.deploy_rhoai_resources
            assert args.rhoai_channel == "fast"
            assert args.raw == "false"
            assert args.rhoai_image == "quay.io/test:latest"

    def test_parse_args_utility_flags(self):
        """Test parsing utility flags"""
        # Test cleanup
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--cleanup"])
            args = parse_args()
            assert args.cleanup

        # Test summary
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--summary"])
            args = parse_args()
            assert args.summary

        # Test verbose
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--verbose"])
            args = parse_args()
            assert args.verbose

    def test_parse_args_rhoai_image_required_with_rhoai(self):
        """Test that rhoai-image is required when --rhoai is specified"""
        with pytest.MonkeyPatch.context() as m:
            # This should work (rhoai-image has default when --rhoai is present)
            m.setattr(sys, "argv", ["script.py", "--rhoai"])
            args = parse_args()
            assert args.rhoai
            assert args.rhoai_image  # Should have default value

    def test_parse_args_type_conversion(self):
        """Test that arguments are properly type-converted"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys,
                "argv",
                [
                    "script.py",
                    "--retries",
                    "10",
                    "--retry-delay",
                    "25",
                    "--timeout",
                    "900",
                ],
            )
            args = parse_args()
            assert isinstance(args.retries, int)
            assert isinstance(args.retry_delay, int)
            assert isinstance(args.timeout, int)
            assert args.retries == 10
            assert args.retry_delay == 25
            assert args.timeout == 900

    def test_parse_args_conflicting_flags(self):
        """Test parsing with conflicting or overlapping flags"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys,
                "argv",
                [
                    "script.py",
                    "--all",  # This should override individual selections
                    "--serverless",  # Individual selection
                    "--cleanup",  # This could conflict with installation
                ],
            )
            args = parse_args()
            assert args.all
            assert args.serverless  # Individual flags still set
            assert args.cleanup

    def test_parse_args_empty_values(self):
        """Test parsing with empty or minimal values"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys,
                "argv",
                [
                    "script.py",
                    "--oc-binary",
                    "",
                    "--rhoai-channel",
                    "",
                    "--rhoai-image",
                    "",
                ],
            )
            # This should not crash
            args = parse_args()
            assert hasattr(args, "oc_binary")
            assert hasattr(args, "rhoai_channel")
            assert hasattr(args, "rhoai_image")


class TestBuildConfig:
    """Test cases for build_config function"""

    def test_build_config_default(self):
        """Test building configuration from default arguments"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py"])
            args = parse_args()
            config = build_config(args)

            assert isinstance(config, dict)
            assert "oc_binary" in config
            assert "max_retries" in config
            assert "retry_delay" in config
            assert "timeout" in config
            assert "rhoai_image" in config
            assert "rhoai_channel" in config
            assert "raw" in config

            # Check default values
            assert config["oc_binary"] == "oc"
            assert config["max_retries"] == 3
            assert config["retry_delay"] == 10
            assert config["timeout"] == 300
            assert config["rhoai_channel"] == "stable"
            assert config["raw"] is False

    def test_build_config_custom(self):
        """Test building configuration from custom arguments"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys,
                "argv",
                [
                    "script.py",
                    "--oc-binary",
                    "/usr/local/bin/oc",
                    "--retries",
                    "7",
                    "--retry-delay",
                    "30",
                    "--timeout",
                    "1200",
                    "--rhoai-channel",
                    "odh-nightlies",
                    "--raw",
                    "true",
                    "--rhoai-image",
                    "custom:tag",
                ],
            )
            args = parse_args()
            config = build_config(args)

            assert config["oc_binary"] == "/usr/local/bin/oc"
            assert config["max_retries"] == 7
            assert config["retry_delay"] == 30
            assert config["timeout"] == 1200
            assert config["rhoai_channel"] == "odh-nightlies"
            assert config["raw"] == "true"  # Note: this is a string, not boolean
            assert config["rhoai_image"] == "custom:tag"

    def test_build_config_type_consistency(self):
        """Test that build_config maintains proper types"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py"])
            args = parse_args()
            config = build_config(args)

            # These should be integers
            assert isinstance(config["max_retries"], int)
            assert isinstance(config["retry_delay"], int)
            assert isinstance(config["timeout"], int)

            # These should be strings
            assert isinstance(config["oc_binary"], str)
            assert isinstance(config["rhoai_channel"], str)
            assert isinstance(config["rhoai_image"], str)

            # This should be boolean
            assert isinstance(config["raw"], bool)

    def test_build_config_immutability(self):
        """Test that build_config creates independent dictionaries"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py"])
            args = parse_args()
            config1 = build_config(args)
            config2 = build_config(args)

            # Should be separate dictionaries
            assert config1 is not config2
            assert config1 == config2

            # Modifying one shouldn't affect the other
            config1["oc_binary"] = "modified"
            assert config1["oc_binary"] != config2["oc_binary"]


class TestSelectOperators:
    """Test cases for select_operators function"""

    def test_select_operators_all_flag(self):
        """Test operator selection with --all flag"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--all"])
            args = parse_args()
            selected = select_operators(args)

            # All operators should be selected
            expected_operators = [
                "serverless",
                "servicemesh",
                "authorino",
                "cert-manager",
                "rhoai",
                "kueue",
                "keda",
            ]
            for operator in expected_operators:
                assert selected[operator] is True

            # Verify all values are True
            assert all(selected.values())

    def test_select_operators_individual(self):
        """Test operator selection with individual flags"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--serverless", "--rhoai", "--keda"])
            args = parse_args()
            selected = select_operators(args)

            assert selected["serverless"] is True
            assert selected["rhoai"] is True
            assert selected["keda"] is True
            assert selected["servicemesh"] is False
            assert selected["authorino"] is False
            assert selected["cert-manager"] is False
            assert selected["kueue"] is False

    def test_select_operators_none_selected(self):
        """Test operator selection when no operators are selected"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py"])
            args = parse_args()
            selected = select_operators(args)

            # All should be False
            assert all(value is False for value in selected.values())

    def test_select_operators_kueue_variations(self):
        """Test operator selection with Kueue variations"""
        # Test Kueue without value
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--kueue"])
            args = parse_args()
            selected = select_operators(args)
            assert selected["kueue"] == "Unmanaged"  # Actual value, not boolean

        # Test Kueue with Managed
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--kueue", "Managed"])
            args = parse_args()
            selected = select_operators(args)
            assert selected["kueue"] == "Managed"

    def test_select_operators_cert_manager_hyphen_conversion(self):
        """Test that cert-manager hyphen is properly handled"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--cert-manager"])
            args = parse_args()
            selected = select_operators(args)

            # The function should handle the hyphen-to-underscore conversion
            assert selected["cert-manager"] is True

    def test_select_operators_mixed_selection(self):
        """Test operator selection with mixed individual and all"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys, "argv", ["script.py", "--all", "--serverless"]
            )  # Redundant but valid
            args = parse_args()
            selected = select_operators(args)

            # --all should make everything True
            assert all(selected.values())

    def test_select_operators_return_type(self):
        """Test that select_operators returns correct types"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--serverless", "--kueue", "Managed"])
            args = parse_args()
            selected = select_operators(args)

            assert isinstance(selected, dict)
            assert isinstance(selected["serverless"], bool)
            assert isinstance(selected["servicemesh"], bool)
            # Kueue is special - it returns the actual value, not just True/False
            assert selected["kueue"] in ["Managed", "Unmanaged", False]

    def test_select_operators_consistency(self):
        """Test that select_operators is consistent across calls"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(sys, "argv", ["script.py", "--serverless", "--rhoai"])
            args = parse_args()
            selected1 = select_operators(args)
            selected2 = select_operators(args)

            assert selected1 == selected2
            assert selected1 is not selected2  # Should be different dict objects


class TestArgumentIntegration:
    """Integration tests for argument parsing workflow"""

    def test_complete_argument_workflow(self):
        """Test complete argument parsing and configuration workflow"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                sys,
                "argv",
                [
                    "script.py",
                    "--serverless",
                    "--rhoai",
                    "--kueue",
                    "Managed",
                    "--deploy-rhoai-resources",
                    "--oc-binary",
                    "/usr/bin/oc",
                    "--retries",
                    "5",
                    "--timeout",
                    "600",
                    "--rhoai-channel",
                    "odh-nightlies",
                    "--rhoai-image",
                    "test-image:latest",
                    "--verbose",
                ],
            )

            # Parse arguments
            args = parse_args()

            # Build configuration
            config = build_config(args)

            # Select operators
            selected_ops = select_operators(args)

            # Verify the complete workflow
            assert args.serverless
            assert args.rhoai
            assert args.kueue == "Managed"
            assert args.deploy_rhoai_resources
            assert args.verbose

            assert config["oc_binary"] == "/usr/bin/oc"
            assert config["max_retries"] == 5
            assert config["timeout"] == 600
            assert config["rhoai_channel"] == "odh-nightlies"

            assert selected_ops["serverless"] is True
            assert selected_ops["rhoai"] is True
            assert selected_ops["kueue"] == "Managed"
            assert selected_ops["servicemesh"] is False

    def test_error_handling_invalid_arguments(self):
        """Test error handling for invalid arguments"""
        with pytest.MonkeyPatch.context() as m:
            # Test invalid Kueue value
            m.setattr(sys, "argv", ["script.py", "--kueue", "Invalid"])
            with pytest.raises(
                SystemExit
            ):  # argparse raises SystemExit on invalid choice
                parse_args()

    def test_help_and_version_arguments(self):
        """Test help and version arguments"""
        with pytest.MonkeyPatch.context() as m:
            # Test that help doesn't crash
            m.setattr(sys, "argv", ["script.py", "--help"])
            with pytest.raises(SystemExit):  # argparse exits after showing help
                parse_args()
