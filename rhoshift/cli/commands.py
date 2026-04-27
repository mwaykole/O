# commands.py
import sys

sys.dont_write_bytecode = True

import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, Optional

from rhoshift.utils.operator.enhanced_operator import EnhancedOpenShiftOperatorInstaller
from rhoshift.utils.operator.operator import OpenShiftOperatorInstaller
from rhoshift.utils.stability_coordinator import StabilityLevel
from rhoshift.utils.utils import run_command

logger = logging.getLogger(__name__)


def install_operator(op_name: str, config: Dict[str, Any]) -> bool:
    """Install a single operator with enhanced stability features."""

    # Critical operators that benefit from enhanced stability
    enhanced_operators = {
        "keda": EnhancedOpenShiftOperatorInstaller.install_keda_operator_enhanced,
        "rhoai": EnhancedOpenShiftOperatorInstaller.install_rhoai_operator_enhanced,
    }

    stability_level = config.get("stability_level", StabilityLevel.ENHANCED)
    if (
        op_name in enhanced_operators
        and stability_level.value >= StabilityLevel.ENHANCED.value
    ):
        logger.info(f"🛡️  Using enhanced stability installer for {op_name}")
        try:
            rc, stdout, stderr = enhanced_operators[op_name](**config)
            if rc == 0:
                logger.info(
                    f"✅ Enhanced installation of {op_name} completed successfully"
                )
                return True
            else:
                logger.error(f"❌ Enhanced installation of {op_name} failed: {stderr}")
                return False
        except Exception as e:
            logger.error(
                f"❌ Enhanced installation of {op_name} failed with error: {e}"
            )
            return False

    def get_operator_map():
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest

        operator_map = {}

        cli_to_operator_config = {
            "cert-manager": (
                "openshift-cert-manager-operator",
                "install_cert_manager_operator",
            ),
            "kueue": ("kueue-operator", "install_kueue_operator"),
            "keda": (
                "openshift-custom-metrics-autoscaler-operator",
                "install_keda_operator",
            ),
            "rhcl": ("rhcl-operator", "install_rhcl_operator"),
            "lws": ("leader-worker-set", "install_lws_operator"),
        }

        for cli_name, (op_key, method_name) in cli_to_operator_config.items():
            try:
                op_config = OpenShiftOperatorInstallManifest.get_operator_config(op_key)

                icons = {
                    "cert-manager": "🔐",
                    "kueue": "📋",
                    "keda": "📊",
                    "rhcl": "🔗",
                    "lws": "👥",
                }

                operator_map[cli_name] = {
                    "installer": getattr(OpenShiftOperatorInstaller, method_name),
                    "csv_name": op_config.name,
                    "namespace": op_config.namespace,
                    "display": f"{icons.get(cli_name, '⚙️')} {op_config.display_name}",
                    "op_key": op_key,
                    "config": op_config,
                }
            except (AttributeError, ValueError) as e:
                logger.warning(f"Skipping {cli_name}: {e}")

        return operator_map

    operator_map = get_operator_map()

    if op_name in operator_map:
        from rhoshift.utils.constants import OpenShiftOperatorInstallManifest

        warnings = OpenShiftOperatorInstallManifest.validate_operator_compatibility(
            [operator_map[op_name]["op_key"]]
        )
        for warning in warnings:
            logger.warning(f"⚠️  {warning}")

    # Special handling for RHOAI
    operator_map["rhoai"] = {
        "installer": OpenShiftOperatorInstaller.install_rhoai_operator_enhanced,
        "channel": config.get("rhoai_channel"),
        "rhoai_image": config.get("rhoai_image"),
        "raw": config.get("raw", False),
        "create_dsc_dsci": config.get("create_dsc_dsci", False),
        "kueue_management_state": config.get(
            "kueue_management_state"
        ),  # Pass Kueue management state
        "csv_name": "opendatahub-operator"
        if config.get("rhoai_channel") == "odh-nightlies"
        else "rhods-operator",
        "namespace": "opendatahub-operators"
        if config.get("rhoai_channel") == "odh-nightlies"
        else "redhat-ods-operator",
        "display": "🤖 ODH Operator"
        if config.get("rhoai_channel") == "odh-nightlies"
        else "🤖 RHOAI Operator",
    }
    if op_name not in operator_map:
        raise ValueError(f"Unknown operator: {op_name}")

    info = operator_map[op_name]
    logger.info(f"{info['display']} installation started...")

    try:
        info["installer"](**config)
        results = OpenShiftOperatorInstaller.wait_for_operator(
            operator_name=info["csv_name"],
            namespace=info["namespace"],
            oc_binary=config.get("oc_binary", "oc"),
            timeout=config.get("timeout", 600),
            interval=2,
        )

        if results.get(info["csv_name"], {}).get("status") == "installed":
            logger.info(f"{info['display']} installed successfully")
            success = True
        else:
            logger.error(f"Installation of {info['display']} failed")
            success = False

    except Exception as e:
        logger.error(f"Failed to install {info['display']}: {e}")
        success = False

    logger.warning("installed" if success else "failed")
    logger.warning(info["csv_name"])

    return success


def install_operators(selected_ops: Dict[str, bool], config: Dict[str, Any]) -> bool:
    """Install multiple operators with enhanced batch stability and dependency resolution"""
    selected_operator_names = [
        op_name for op_name, selected in selected_ops.items() if selected
    ]

    if not selected_operator_names:
        logger.warning("No operators selected for installation")
        return True

    # Validate DSCI compatibility for RHOAI installations
    if selected_ops.get("rhoai", False):
        try:
            from rhoshift.utils.operator.enhanced_operator import (
                EnhancedOpenShiftOperatorInstaller,
            )

            dsci_compatible, dsci_warnings = (
                EnhancedOpenShiftOperatorInstaller.validate_dsci_compatibility(
                    selected_ops, config
                )
            )

            if not dsci_compatible:
                logger.error(
                    "❌ DSCI compatibility validation failed. Aborting installation."
                )
                return False

            for warning in dsci_warnings:
                logger.info(f"🔍 DSCI: {warning}")
        except Exception as e:
            logger.warning(f"⚠️  DSCI validation failed, continuing: {e}")

    stability_level = config.get("stability_level", StabilityLevel.ENHANCED)
    if (
        stability_level.value >= StabilityLevel.ENHANCED.value
        and len(selected_operator_names) > 1
    ):
        logger.info(
            f"🛡️  Using enhanced batch installation with {stability_level.name.lower()} stability"
        )
        try:
            from rhoshift.utils.operator.enhanced_operator import (
                install_operators_with_enhanced_stability,
            )

            return install_operators_with_enhanced_stability(selected_ops, config)
        except Exception as e:
            logger.warning(
                f"⚠️  Enhanced batch installation failed, falling back to standard: {e}"
            )

    from rhoshift.utils.constants import OpenShiftOperatorInstallManifest

    cli_to_operator_key = {
        "cert-manager": "openshift-cert-manager-operator",
        "kueue": "kueue-operator",
        "keda": "openshift-custom-metrics-autoscaler-operator",
        "rhcl": "rhcl-operator",
        "lws": "leader-worker-set",
    }

    operator_keys = []
    for op_name in selected_operator_names:
        if op_name in cli_to_operator_key:
            operator_keys.append(cli_to_operator_key[op_name])

    if operator_keys:
        warnings = OpenShiftOperatorInstallManifest.validate_operator_compatibility(
            operator_keys
        )
        if warnings:
            logger.warning("⚠️  Batch installation compatibility warnings:")
            for warning in warnings:
                logger.warning(f"   - {warning}")

        resolved_order = OpenShiftOperatorInstallManifest.resolve_dependencies(
            operator_keys
        )

        reverse_cli_map = {v: k for k, v in cli_to_operator_key.items()}
        for op_key in resolved_order:
            if op_key in reverse_cli_map:
                cli_name = reverse_cli_map[op_key]
                if cli_name not in selected_operator_names:
                    logger.info(f"📦 Auto-adding dependency: {cli_name}")
                    selected_ops[cli_name] = True
                    selected_operator_names.append(cli_name)

        ordered_cli_names = []
        for op_key in resolved_order:
            if op_key in reverse_cli_map:
                ordered_cli_names.append(reverse_cli_map[op_key])

        if selected_ops.get("rhoai", False):
            ordered_cli_names.append("rhoai")
    else:
        ordered_cli_names = selected_operator_names

    logger.info(
        f"Installing {len(ordered_cli_names)} operators in order: {' → '.join(ordered_cli_names)}"
    )

    # Install operators in dependency order
    success = True
    for op_name in ordered_cli_names:
        if selected_ops.get(op_name, False):
            logger.info(f"🚀 Installing operator: {op_name}")
            if not install_operator(op_name, config):
                success = False
                logger.error(f"❌ Failed to install {op_name}")
                break  # Stop on first failure
            else:
                logger.info(f"✅ Successfully installed {op_name}")

    return success


def _wait_for_pods_stable(
    namespace: str = "redhat-ods-applications",
    wait_time: int = 600,
    oc_binary: str = "oc",
) -> bool:
    """Wait for pods to stabilize after upgrade, checking readiness periodically."""
    logger.info(f"⏳ Waiting up to {wait_time}s for pods to stabilize in {namespace}...")
    interval = 30
    elapsed = 0

    while elapsed < wait_time:
        cmd = (
            f"{oc_binary} get pods -n {namespace} --no-headers "
            f"-o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[*].ready,STATUS:.status.phase "
            f"2>/dev/null"
        )
        rc, stdout, _ = run_command(cmd, log_output=False)
        if rc == 0:
            lines = [l for l in stdout.strip().splitlines() if l.strip()]
            not_ready = [l for l in lines if "true" not in l.lower() or "Running" not in l]
            if not not_ready:
                logger.info(f"✅ All pods ready in {namespace} after {elapsed}s")
                return True
            logger.info(
                f"⏱️  {len(not_ready)} pod(s) not ready yet ({elapsed}/{wait_time}s)..."
            )
        time.sleep(interval)
        elapsed += interval

    logger.warning(f"⚠️  Pod stabilization timed out after {wait_time}s")
    return False


def _run_upgrade_tests(
    phase: str,
    test_dir: str,
    test_path: Optional[str] = None,
    test_markers: Optional[str] = None,
    deployment_mode: str = "rawdeployment",
) -> Dict[str, Any]:
    """Run pre or post upgrade tests and return structured results."""
    marker_flag = f"--{phase}-upgrade"
    cmd_parts = [
        "uv", "run", "pytest",
        marker_flag,
        f"--upgrade-deployment-modes={deployment_mode}",
        "--tc=distribution:downstream",
        "-v",
    ]
    if test_markers:
        cmd_parts.extend(["-m", test_markers])
    if test_path:
        cmd_parts.append(test_path)

    cmd = " ".join(cmd_parts)
    logger.info(f"🧪 Running {phase}-upgrade tests: {cmd}")

    rc, stdout, stderr = run_command(cmd, timeout=3600, cwd=test_dir, log_output=True)

    passed = rc == 0
    summary = ""
    for line in stdout.splitlines():
        if "passed" in line or "failed" in line or "error" in line:
            summary = line.strip()

    return {
        "phase": phase,
        "passed": passed,
        "return_code": rc,
        "summary": summary or ("All tests passed" if passed else f"Tests failed (rc={rc})"),
    }


def _clone_test_repo(
    repo_url: str = "https://github.com/opendatahub-io/opendatahub-tests.git",
    target_dir: Optional[str] = None,
) -> str:
    """Clone or update the test repository. Returns the path."""
    if target_dir is None:
        target_dir = os.path.join(
            tempfile.gettempdir(), "rhoshift-upgrade-tests", "opendatahub-tests"
        )

    if os.path.isdir(os.path.join(target_dir, ".git")):
        logger.info(f"📂 Updating existing test repo at {target_dir}")
        run_command(f"git -C {target_dir} pull --quiet", log_output=False)
    else:
        logger.info(f"📥 Cloning test repo to {target_dir}")
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        rc, _, stderr = run_command(
            f"git clone --quiet {repo_url} {target_dir}",
            timeout=300,
            log_output=True,
        )
        if rc != 0:
            raise RuntimeError(f"Failed to clone test repo: {stderr}")

    return target_dir


def run_upgrade(config: Dict[str, Any]) -> int:
    """Orchestrate a full RHOAI upgrade workflow.

    Steps:
      1. Cleanup (optional)
      2. Install base version with --deploy-rhoai-resources
      3. Clone test repo & run pre-upgrade tests
      4. Upgrade to target version (preserves DSC/DSCI)
      5. Wait for pods to stabilize
      6. Run post-upgrade tests
      7. Generate and print upgrade report

    Returns 0 on success, 1 on failure.
    """
    from_image = config["from_image"]
    to_image = config["to_image"]
    from_channel = config.get("from_channel") or config.get("rhoai_channel", "fast")
    to_channel = config.get("to_channel") or config.get("rhoai_channel", "fast")
    oc_binary = config.get("oc_binary", "oc")
    wait_time = config.get("wait_time", 600)
    skip_tests = config.get("skip_tests", False)
    skip_cleanup = config.get("skip_cleanup", False)
    test_path = config.get("test_path")
    test_markers = config.get("test_markers")

    report = {
        "from_image": from_image,
        "to_image": to_image,
        "from_channel": from_channel,
        "to_channel": to_channel,
        "phases": {},
    }

    start_time = time.time()

    # --- Phase 0: Cleanup ---
    if not skip_cleanup:
        logger.info("🧹 [Phase 0/6] Cleaning up existing installation...")
        try:
            from rhoshift.utils.operator.cleanup import cleanup

            cleanup()
            report["phases"]["cleanup"] = {"status": "success"}
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            report["phases"]["cleanup"] = {"status": "failed", "error": str(e)}
            return 1
    else:
        logger.info("⏭️  Skipping cleanup (--skip-cleanup)")

    # --- Phase 1: Install base version ---
    logger.info(f"📦 [Phase 1/6] Installing base version: {from_image}")
    base_config = {
        **config,
        "rhoai_image": from_image,
        "rhoai_channel": from_channel,
        "create_dsc_dsci": True,
    }
    base_success = install_operator("rhoai", base_config)
    report["phases"]["base_install"] = {
        "status": "success" if base_success else "failed",
        "image": from_image,
        "channel": from_channel,
    }
    if not base_success:
        logger.error("❌ Base version installation failed. Aborting upgrade.")
        return 1
    logger.info("✅ Base version installed successfully")

    # --- Phase 2: Pre-upgrade tests ---
    pre_results = {"phase": "pre", "passed": True, "summary": "skipped"}
    test_dir = None
    if not skip_tests:
        logger.info("🧪 [Phase 2/6] Running pre-upgrade tests...")
        try:
            test_dir = _clone_test_repo()
            pre_results = _run_upgrade_tests(
                phase="pre",
                test_dir=test_dir,
                test_path=test_path,
                test_markers=test_markers,
            )
        except Exception as e:
            logger.error(f"❌ Pre-upgrade test setup failed: {e}")
            pre_results = {"phase": "pre", "passed": False, "summary": str(e)}
    else:
        logger.info("⏭️  Skipping pre-upgrade tests (--skip-tests)")

    report["phases"]["pre_upgrade_tests"] = pre_results
    if not pre_results["passed"]:
        logger.warning(f"⚠️  Pre-upgrade tests failed: {pre_results['summary']}")
        logger.warning("Continuing with upgrade despite pre-test failures...")

    # --- Phase 3: Upgrade ---
    logger.info(f"⬆️  [Phase 3/6] Upgrading to: {to_image}")
    upgrade_config = {
        **config,
        "rhoai_image": to_image,
        "rhoai_channel": to_channel,
        "create_dsc_dsci": False,
    }
    upgrade_success = install_operator("rhoai", upgrade_config)
    report["phases"]["upgrade"] = {
        "status": "success" if upgrade_success else "failed",
        "image": to_image,
        "channel": to_channel,
    }
    if not upgrade_success:
        logger.error("❌ Upgrade failed.")
        return 1
    logger.info("✅ Upgrade applied successfully")

    # --- Phase 4: Wait for stabilization ---
    logger.info(f"⏳ [Phase 4/6] Waiting {wait_time}s for pods to stabilize...")
    ns = "opendatahub" if to_channel == "odh-nightlies" else "redhat-ods-applications"
    pods_stable = _wait_for_pods_stable(
        namespace=ns, wait_time=wait_time, oc_binary=oc_binary
    )
    report["phases"]["stabilization"] = {
        "status": "success" if pods_stable else "warning",
        "wait_time": wait_time,
    }

    # --- Phase 5: Post-upgrade tests ---
    post_results = {"phase": "post", "passed": True, "summary": "skipped"}
    if not skip_tests:
        logger.info("🧪 [Phase 5/6] Running post-upgrade tests...")
        if test_dir is None:
            test_dir = _clone_test_repo()
        post_results = _run_upgrade_tests(
            phase="post",
            test_dir=test_dir,
            test_path=test_path,
            test_markers=test_markers,
        )
    else:
        logger.info("⏭️  Skipping post-upgrade tests (--skip-tests)")

    report["phases"]["post_upgrade_tests"] = post_results

    # --- Phase 6: Report ---
    elapsed = time.time() - start_time
    report["elapsed_seconds"] = round(elapsed, 1)

    try:
        upgrade_report = OpenShiftOperatorInstaller.generate_upgrade_report(
            from_channel=from_channel,
            to_channel=to_channel,
            from_image=from_image,
            to_image=to_image,
            oc_binary=oc_binary,
        )
        report["cluster_state"] = upgrade_report
    except Exception as e:
        logger.warning(f"⚠️  Failed to generate cluster state report: {e}")

    logger.info("=" * 70)
    logger.info("📊 UPGRADE REPORT")
    logger.info("=" * 70)
    logger.info(f"  From: {from_image}")
    logger.info(f"  To:   {to_image}")
    logger.info(f"  Time: {elapsed:.0f}s")
    logger.info(
        f"  Base install:    {report['phases'].get('base_install', {}).get('status', 'n/a')}"
    )
    logger.info(f"  Pre-upgrade:     {pre_results.get('summary', 'n/a')}")
    logger.info(
        f"  Upgrade:         {report['phases'].get('upgrade', {}).get('status', 'n/a')}"
    )
    logger.info(
        f"  Stabilization:   {report['phases'].get('stabilization', {}).get('status', 'n/a')}"
    )
    logger.info(f"  Post-upgrade:    {post_results.get('summary', 'n/a')}")
    logger.info("=" * 70)

    report_path = os.path.join(tempfile.gettempdir(), "rhoshift-upgrade-report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"📄 Full report saved to: {report_path}")

    all_passed = (
        report["phases"].get("upgrade", {}).get("status") == "success"
        and pre_results.get("passed", True)
        and post_results.get("passed", True)
    )

    if all_passed:
        logger.info("🎉 Upgrade completed successfully!")
        return 0
    else:
        logger.error("❌ Upgrade completed with failures. See report above.")
        return 1
