from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import yaml


class InstallMode(Enum):
    """Supported operator installation modes."""

    OWN_NAMESPACE = "OwnNamespace"
    SINGLE_NAMESPACE = "SingleNamespace"
    MULTI_NAMESPACE = "MultiNamespace"
    ALL_NAMESPACES = "AllNamespaces"


class CatalogSource(Enum):
    """Available catalog sources."""

    REDHAT_OPERATORS = "redhat-operators"
    CERTIFIED_OPERATORS = "certified-operators"
    COMMUNITY_OPERATORS = "community-operators"
    REDHAT_MARKETPLACE = "redhat-marketplace"


@dataclass
class OperatorConfig:
    """Configuration for an operator installation."""

    name: str
    display_name: str
    namespace: str
    channel: str
    catalog_source: CatalogSource = CatalogSource.REDHAT_OPERATORS
    install_mode: InstallMode = InstallMode.ALL_NAMESPACES
    create_namespace: bool = True
    starting_csv: Optional[str] = None
    install_plan_approval: str = "Automatic"
    additional_resources: Optional[List[Dict[str, Any]]] = None
    csv_name_prefix: Optional[str] = (
        None  # For cases where CSV name differs from operator name
    )
    post_install_hook: Optional[str] = None


class OpenShiftOperatorInstallManifest:
    """Optimized operator manifest generator with reduced duplication."""

    MARKETPLACE_NAMESPACE = "openshift-marketplace"

    DEPENDENCIES = {
        "kueue-operator": [
            "openshift-cert-manager-operator"
        ],  # Kueue requires cert-manager
    }

    OPERATORS = {
        "kueue-operator": OperatorConfig(
            name="kueue-operator",
            display_name="Red Hat build of Kueue",
            namespace="openshift-kueue-operator",
            channel="stable-v1.3",
            install_mode=InstallMode.ALL_NAMESPACES,
            additional_resources=[],  # Will be populated with dependencies
            post_install_hook="verify_cert_manager_dependency",
        ),
        "openshift-cert-manager-operator": OperatorConfig(
            name="openshift-cert-manager-operator",
            display_name="Red Hat build of cert-manager Operator for Red Hat OpenShift",
            namespace="cert-manager-operator",
            channel="stable-v1",
            install_mode=InstallMode.ALL_NAMESPACES,
            csv_name_prefix="cert-manager-operator",
            starting_csv=None,
        ),
        "openshift-custom-metrics-autoscaler-operator": OperatorConfig(
            name="openshift-custom-metrics-autoscaler-operator",
            display_name="KEDA (Custom Metrics Autoscaler)",
            namespace="openshift-keda",
            channel="stable",
            catalog_source=CatalogSource.REDHAT_OPERATORS,
            install_mode=InstallMode.OWN_NAMESPACE,
            csv_name_prefix="custom-metrics-autoscaler",
            post_install_hook="create_keda_controller",
        ),
        "opendatahub-operator": OperatorConfig(
            name="opendatahub-operator",
            display_name="Open Data Hub Operator",
            namespace="openshift-operators",
            channel="stable",
            catalog_source=CatalogSource.COMMUNITY_OPERATORS,
            install_mode=InstallMode.ALL_NAMESPACES,
            create_namespace=False,  # Uses existing openshift-operators
        ),
        "rhcl-operator": OperatorConfig(
            name="rhcl-operator",
            display_name="Red Hat Connectivity Link",
            namespace="openshift-operators",
            channel="stable",
            install_mode=InstallMode.ALL_NAMESPACES,
            create_namespace=False,
            post_install_hook="create_kuadrant",
        ),
        "leader-worker-set": OperatorConfig(
            name="leader-worker-set",
            display_name="Red Hat build of Leader Worker Set",
            namespace="openshift-lws-operator",
            channel="stable-v1.0",
            install_mode=InstallMode.OWN_NAMESPACE,
            post_install_hook="create_lws_operator",
        ),
    }

    @classmethod
    def generate_namespace(cls, namespace: str) -> Dict[str, Any]:
        """Generate namespace manifest."""
        return {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": namespace},
        }

    @classmethod
    def generate_operator_group(cls, config: OperatorConfig) -> Dict[str, Any]:
        """Generate OperatorGroup manifest based on install mode."""
        manifest = {
            "apiVersion": "operators.coreos.com/v1",
            "kind": "OperatorGroup",
            "metadata": {"name": f"{config.name}-group", "namespace": config.namespace},
        }

        if config.install_mode == InstallMode.ALL_NAMESPACES:
            manifest["spec"] = {}  # Empty spec = all namespaces
        elif config.install_mode == InstallMode.OWN_NAMESPACE:
            manifest["spec"] = {"targetNamespaces": [config.namespace]}
        else:
            manifest["spec"] = {"targetNamespaces": [config.namespace]}

        return manifest

    @classmethod
    def check_existing_operator_group(
        cls, namespace: str, oc_binary: str = "oc"
    ) -> Tuple[bool, Optional[str]]:
        """Check if an operator group already exists in the namespace."""
        from rhoshift.utils.utils import run_command

        cmd = f"{oc_binary} get operatorgroup -n {namespace} -o json"
        rc, stdout, stderr = run_command(cmd, log_output=False)

        if rc != 0:
            if "not found" in stderr or "No resources found" in stderr:
                return False, None  # No operator group exists
            return False, f"Error checking operator groups: {stderr}"

        try:
            import json

            result = json.loads(stdout)
            items = result.get("items", [])

            if not items:
                return False, None  # No operator groups
            elif len(items) == 1:
                og_name = items[0].get("metadata", {}).get("name", "")
                return True, og_name  # One operator group exists
            else:
                if namespace in ["openshift-operators"]:
                    return True, "shared_namespace_multiple_groups"
                else:
                    og_names = [
                        item.get("metadata", {}).get("name", "") for item in items
                    ]
                    return (
                        True,
                        f"Multiple operator groups found: {', '.join(og_names)}",
                    )

        except json.JSONDecodeError:
            return False, "Invalid JSON response"

    @classmethod
    def resolve_latest_channel(
        cls, package_name: str, oc_binary: str = "oc"
    ) -> Optional[str]:
        """Query the cluster for the default (latest) channel of a package.

        Returns the defaultChannel from the PackageManifest, or None if
        the lookup fails (e.g. disconnected cluster, missing package).
        """
        from rhoshift.utils.utils import run_command
        import logging

        logger = logging.getLogger(__name__)

        cmd = (
            f"{oc_binary} get packagemanifest {package_name} "
            "-o jsonpath='{.status.defaultChannel}'"
        )
        rc, stdout, stderr = run_command(cmd, max_retries=1, log_output=False)
        if rc == 0 and stdout.strip().strip("'"):
            channel = stdout.strip().strip("'")
            logger.info(
                f"Resolved latest channel for {package_name}: {channel}"
            )
            return channel

        logger.warning(
            f"Could not resolve latest channel for {package_name}, "
            f"falling back to configured default"
        )
        return None

    @classmethod
    def generate_subscription(
        cls, config: OperatorConfig, oc_binary: str = "oc"
    ) -> Dict[str, Any]:
        """Generate Subscription manifest."""
        subscription_name = (
            config.csv_name_prefix if config.csv_name_prefix else config.name
        )

        channel = cls.resolve_latest_channel(config.name, oc_binary) or config.channel

        manifest = {
            "apiVersion": "operators.coreos.com/v1alpha1",
            "kind": "Subscription",
            "metadata": {
                "name": subscription_name,
                "namespace": config.namespace,
                "labels": {
                    f"operators.coreos.com/{subscription_name}.{config.namespace}": ""
                },
            },
            "spec": {
                "channel": channel,
                "installPlanApproval": config.install_plan_approval,
                "name": config.name,
                "source": config.catalog_source.value,
                "sourceNamespace": cls.MARKETPLACE_NAMESPACE,
            },
        }

        if config.starting_csv:
            manifest["spec"]["startingCSV"] = config.starting_csv

        return manifest

    @classmethod
    def generate_operator_manifest(
        cls, operator_key: str, oc_binary: str = "oc"
    ) -> str:
        """Generate complete operator manifest with conflict prevention."""
        if operator_key not in cls.OPERATORS:
            raise ValueError(f"Unknown operator: {operator_key}")

        config = cls.OPERATORS[operator_key]
        manifests = []

        # Add namespace if needed
        if config.create_namespace:
            manifests.append(cls.generate_namespace(config.namespace))

        # Check for existing operator groups and handle conflicts
        should_create_og = True
        if config.create_namespace or config.namespace not in ["openshift-operators"]:
            og_exists, og_info = cls.check_existing_operator_group(
                config.namespace, oc_binary
            )
            if og_exists:
                if og_info == "shared_namespace_multiple_groups":
                    # Shared namespace with multiple groups - don't create another
                    should_create_og = False
                elif og_info and "Multiple" in og_info:
                    # Multiple operator groups found in dedicated namespace - this will cause issues
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"⚠️  {og_info} in namespace {config.namespace}. This may cause installation issues."
                    )
                    logger.warning(
                        "   Consider cleaning up duplicate operator groups before installation."
                    )
                    should_create_og = False  # Don't add another one
                else:
                    # Single operator group exists - don't create another
                    should_create_og = False
        elif config.namespace == "openshift-operators":
            # For openshift-operators, check if we need to create an operator group
            og_exists, og_info = cls.check_existing_operator_group(
                config.namespace, oc_binary
            )
            if og_exists:
                should_create_og = False  # Don't create if any operator group exists in sharedshared namespace

        if should_create_og:
            manifests.append(cls.generate_operator_group(config))

        # Add subscription
        manifests.append(cls.generate_subscription(config, oc_binary))

        # Add any additional resources
        if config.additional_resources:
            manifests.extend(config.additional_resources)

        # Convert to YAML string
        yaml_docs = []
        for manifest in manifests:
            yaml_docs.append(yaml.dump(manifest, default_flow_style=False))

        return "\n---\n".join(yaml_docs)

    @classmethod
    def get_operator_config(cls, operator_key: str) -> OperatorConfig:
        """Get operator configuration."""
        if operator_key not in cls.OPERATORS:
            raise ValueError(f"Unknown operator: {operator_key}")
        return cls.OPERATORS[operator_key]

    @classmethod
    def list_operators(cls) -> List[str]:
        """List all available operators."""
        return list(cls.OPERATORS.keys())

    @classmethod
    def get_dependencies(cls, operator_key: str) -> List[str]:
        """Get dependencies for an operator."""
        return cls.DEPENDENCIES.get(operator_key, [])

    @classmethod
    def resolve_dependencies(cls, operators: List[str]) -> List[str]:
        """Resolve dependencies and return operators in installation order."""
        result = []
        visited = set()

        def add_operator(op_key: str):
            if op_key in visited:
                return
            visited.add(op_key)

            # Add dependencies first
            for dep in cls.get_dependencies(op_key):
                if dep not in visited:
                    add_operator(dep)

            # Add the operator itself
            if op_key not in result:
                result.append(op_key)

        # Process all requested operators
        for op_key in operators:
            add_operator(op_key)

        return result

    @classmethod
    def validate_operator_compatibility(cls, operators: List[str]) -> List[str]:
        """Validate operator compatibility, dependencies, and return warnings."""
        warnings = []

        # Check for unknown operators
        for op_key in operators:
            if op_key not in cls.OPERATORS:
                warnings.append(f"Unknown operator: {op_key}")
                continue

        # Check dependencies
        missing_deps = []
        for op_key in operators:
            if op_key in cls.OPERATORS:
                deps = cls.get_dependencies(op_key)
                for dep in deps:
                    if dep not in operators:
                        missing_deps.append(f"{op_key} requires {dep}")

        if missing_deps:
            warnings.extend([f"Missing dependency: {dep}" for dep in missing_deps])

        # Check for namespace conflicts
        namespaces = {}
        for op_key in operators:
            if op_key not in cls.OPERATORS:
                continue

            config = cls.OPERATORS[op_key]
            if config.namespace in namespaces:
                existing_op = namespaces[config.namespace]
                if existing_op != op_key:  # Same namespace, different operators
                    warnings.append(
                        f"Namespace conflict: {config.namespace} used by both "
                        f"{existing_op} and {op_key}"
                    )
            namespaces[config.namespace] = op_key

        # Check for specific operator conflicts
        if (
            "kueue-operator" in operators
            and "openshift-custom-metrics-autoscaler-operator" in operators
        ):
            warnings.append(
                "Note: Kueue and KEDA may have resource conflicts. "
                "Monitor for admission webhook issues."
            )

        # Dependency resolution info
        if operators:
            resolved_order = cls.resolve_dependencies(operators)
            if resolved_order != operators:
                warnings.append(
                    f"Installation order will be adjusted for dependencies: "
                    f"{' → '.join(resolved_order)}"
                )

        return warnings

    @classmethod
    def update_operator_config(cls, operator_key: str, **updates) -> None:
        """Update operator configuration dynamically."""
        if operator_key not in cls.OPERATORS:
            raise ValueError(f"Unknown operator: {operator_key}")

        config = cls.OPERATORS[operator_key]
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"Invalid config key: {key}")

    @classmethod
    def ensure_latest_versions(cls) -> Dict[str, str]:
        """
        Ensure all operators are configured to use the latest available versions.
        Returns a dictionary of operators and their target versions.
        Channels are resolved dynamically from the cluster's PackageManifest.
        """
        version_info = {}
        for op_key, config in cls.OPERATORS.items():
            resolved = cls.resolve_latest_channel(config.name) or config.channel
            version_info[op_key] = {
                "channel": resolved,
                "expected_version": "latest",
                "description": f"{config.display_name} - latest from {resolved}",
            }
        return version_info

    @classmethod
    def get_installation_summary(cls) -> str:
        """Generate a summary of all supported operators and their configurations."""
        summary = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                     RHOSHIFT OPERATOR INSTALLATION SUMMARY                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  All operators are configured to install latest stable versions             ║
║  Dependencies are automatically resolved and installed in correct order     ║
║  Operator Group conflicts are detected and prevented                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

📦 SUPPORTED OPERATORS:
"""

        versions = cls.ensure_latest_versions()
        for op_key in cls.list_operators():
            config = cls.get_operator_config(op_key)
            version_info = versions.get(op_key, {})

            summary += f"""
🔧 {config.display_name}
   ├─ Operator: {op_key}
   ├─ Channel: {version_info.get("channel", config.channel)} (resolved from cluster)
   ├─ Namespace: {config.namespace}
   ├─ Install Mode: {config.install_mode.value}
   └─ {version_info.get("description", "Latest stable version")}
"""

        summary += """
📋 DEPENDENCIES:
"""
        for op_key, deps in cls.DEPENDENCIES.items():
            if deps:
                summary += f"   • {op_key} → requires: {', '.join(deps)}\n"

        summary += """
🚀 USAGE EXAMPLES:
   # Install cert-manager (latest v1.16.1)
   rhoshift --cert-manager

   # Install with dependency resolution
   rhoshift --kueue  # Auto-installs cert-manager first

   # Install multiple operators
   rhoshift --cert-manager --kueue --keda

   # Install all operators
   rhoshift --all
"""
        return summary

    @property
    def KUEUE_MANIFEST(self) -> str:
        return self.generate_operator_manifest("kueue-operator")

    @property
    def KEDA_MANIFEST(self) -> str:
        return self.generate_operator_manifest(
            "openshift-custom-metrics-autoscaler-operator"
        )

    @property
    def CERT_MANAGER_MANIFEST(self) -> str:
        return self.generate_operator_manifest("openshift-cert-manager-operator")


def get_dsci_manifest(
    kserve_raw=True,
    applications_namespace="redhat-ods-applications",
    monitoring_namespace="redhat-ods-monitoring",
):
    def to_state(flag):
        return "Removed" if flag else "Managed"

    return f"""apiVersion: dscinitialization.opendatahub.io/v1
kind: DSCInitialization
metadata:
  labels:
    app.kubernetes.io/created-by: rhods-operator
    app.kubernetes.io/instance: default-dsci
    app.kubernetes.io/managed-by: kustomize
    app.kubernetes.io/name: dscinitialization
    app.kubernetes.io/part-of: rhods-operator
  name: default-dsci
spec:
  applicationsNamespace: {applications_namespace}
  monitoring:
    managementState: Managed
    namespace: {monitoring_namespace}
  serviceMesh:
    controlPlane:
      metricsCollection: Istio
      name: data-science-smcp
      namespace: istio-system
    managementState: {to_state(kserve_raw)}
  trustedCABundle:
    customCABundle: ''
    managementState: Managed
"""


class WaitTime:
    WAIT_TIME_10_MIN = 10 * 60  # 10 minutes in seconds
    WAIT_TIME_5_MIN = 5 * 60  # 5 minutes in seconds
    WAIT_TIME_1_MIN = 60  # 1 minute in seconds
    WAIT_TIME_30_SEC = 30  # 30 seconds


def get_dsc_manifest(
    enable_dashboard=True,
    enable_kserve=True,
    enable_raw_serving=True,
    enable_modelmeshserving=True,
    operator_namespace="rhods-operator",
    kueue_management_state=None,
):
    def to_state(flag):
        return "Managed" if flag else "Removed"

    # Build the base manifest
    manifest = f"""apiVersion: datasciencecluster.opendatahub.io/v1
kind: DataScienceCluster
metadata:
  labels:
    app.kubernetes.io/created-by: {operator_namespace}
    app.kubernetes.io/instance: default-dsc
    app.kubernetes.io/managed-by: kustomize
    app.kubernetes.io/name: datasciencecluster
    app.kubernetes.io/part-of: {operator_namespace}
  name: default-dsc
spec:
  components:
    dashboard:
      managementState: {to_state(enable_dashboard)}
    kserve:
      managementState: {to_state(enable_kserve)}
      nim:
        managementState: Managed
      serving:
        ingressGateway:
          certificate:
            type: OpenshiftDefaultIngress
        managementState: {to_state(enable_raw_serving ^ True)}
        name: knative-serving"""

    # Add Kueue component if kueue_management_state is specified
    if kueue_management_state is not None:
        manifest += f"""
    kueue:
      managementState: {kueue_management_state}"""

    # Add modelmeshserving component
    manifest += f"""
    modelmeshserving:
      managementState: {to_state(enable_modelmeshserving)}
"""
    return manifest
