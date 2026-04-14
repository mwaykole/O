#!/bin/bash
# RHOAI/Kserve Forceful Uninstall Script
# Version: 1.1.0
# Created: 2024-03-11
# Description: Comprehensive cleanup of all RHOAI/KServe related resources

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# === Banner ===
echo -e "${RED}██████╗ ██╗  ██╗ ██████╗  █████╗ ██╗"
echo -e "${RED}██╔══██╗██║  ██║██╔═══██╗██╔══██╗██║"
echo -e "${RED}██████╔╝███████║██║   ██║███████║██║"
echo -e "${RED}██╔══██╗██╔══██║██║   ██║██╔══██║██║"
echo -e "${RED}██║  ██║██║  ██║╚██████╔╝██║  ██║██║"
echo -e "${RED}╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝"
echo -e "${CYAN} ██████╗██╗     ███████╗ █████╗ ███╗   ██╗██   ██ ██████╗ "
echo -e "${CYAN}██╔════╝██║     ██╔════╝██╔══██╗████╗  ██║██╔══██╗██╔══██╗"
echo -e "${CYAN}██║     ██║     █████╗  ███████║██╔██╗ ██║██║  ██║██████╔╝"
echo -e "${CYAN}██║     ██║     ██╔══╝  ██╔══██║██║╚██╗██║██║  ██║██╔═══╝ "
echo -e "${CYAN}╚██████╗███████╗███████╗██║  ██║██║ ╚████║██████╔╝██║     "
echo -e "${CYAN} ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝     "
echo -e "${YELLOW}======================================================"
echo -e "${YELLOW}     COMPLETE RHOAI/KSERVE COMPONENT CLEANUP TOOL     "
echo -e "${YELLOW}======================================================"
echo -e "${NC}"

# Logging functions
log_info() {
echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
log_info "Checking prerequisites..."

if ! command -v oc &> /dev/null; then
        log_error "OpenShift CLI (oc) not found. Please install it first."
        exit 1
fi

log_success "Prerequisites check passed"
}

# Initialize variables
init_variables() {
log_info "Initializing variables..."

# Namespaces
export OPENSHIFT_MARKETPLACE_NAMESPACE="openshift-marketplace"
export RHODS_OPERATOR_NAMESPACE="redhat-ods-operator"
export RHODS_APPS_NAMESPACE="redhat-ods-applications"
export RHODS_AUTH_PROVIDER_NAMESPACE="redhat-ods-applications-auth-provider"
export RHODS_MONITORING_NAMESPACE="redhat-ods-monitoring"
export RHODS_NOTEBOOKS_NAMESPACE="rhods-notebooks"
export RHODS_MODEL_REGISTRY_NAMESPACE="rhoai-model-registries"
export OPENDATAHUB_NAMESPACE="opendatahub"
export OPENDATAHUB_OPERATORS_NAMESPACE="opendatahub-operators"
export OPENDATAHUB_AUTH_PROVIDER_NAMESPACE="opendatahub-auth-provider"
export OPENDATAHUB_MODEL_REGISTRY_NAMESPACE="odh-model-registries"
export ISTIO_NAMESPACE="istio-system"
export KNATIVE_SERVING_NAMESPACE="knative-serving"
export KNATIVE_EVENTING_NAMESPACE="knative-eventing"
export KUEUE_NAMESPACE="openshift-kueue-operator"
export KEDA_NAMESPACE="openshift-keda"
export CERT_MANAGER_NAMESPACE="cert-manager-operator"
export CERT_MANAGER_DATA_NAMESPACE="cert-manager"
export KUADRANT_NAMESPACE="kuadrant-system"
export LWS_NAMESPACE="openshift-lws-operator"

# Demo namespaces
export KSERVE_DEMO_NAMESPACE="kserve-demo"
export PIPELINE_DEMO_NAMESPACE="pipeline-demo"
export MINIO_NAMESPACE="minio"

log_success "Variables initialized"
}

# Function to delete resources with finalizer cleanup
delete_resources() {
local resource_type=$1
local namespace=${2:-}
local extra_flags=${3:-}

log_info "Deleting all ${resource_type} in namespace ${namespace:-all namespaces}"

if [ -n "$namespace" ]; then
        oc get "$resource_type" -n "$namespace" --no-headers -o name 2>/dev/null | while read -r resource; do
        log_info "Removing finalizers from ${resource}"
        oc patch "$resource" -n "$namespace" -p '{"metadata":{"finalizers":[]}}' --type=merge || true
        done

        oc delete "$resource_type" --all $extra_flags -n "$namespace"  || true
else
        oc get "$resource_type" --all-namespaces --no-headers -o name 2>/dev/null | while read -r resource; do
        log_info "Removing finalizers from ${resource}"
        oc patch "$resource" -p '{"metadata":{"finalizers":[]}}' --type=merge || true
        done

        oc delete "$resource_type" --all $extra_flags --all-namespaces  || true
fi
}

# Function to delete namespace with force
delete_namespace() {
local namespace=$1

if oc get namespace "$namespace" &>/dev/null; then
        log_info "Deleting namespace ${namespace}"

        # Delete all resources in the namespace first
        delete_resources "all" "$namespace" "--force --grace-period=0"

        # Remove finalizers from the namespace itself
        oc patch namespace "$namespace" -p '{"metadata":{"finalizers":[]}}' --type=merge || true

        # Delete the namespace
        oc delete namespace "$namespace" --force --grace-period=0  || true

        # Verify deletion
        if oc get namespace "$namespace" &>/dev/null; then
        log_warning "Namespace ${namespace} still exists. Retrying deletion..."
        sleep 5
        oc delete namespace "$namespace" --force --grace-period=0  || true
        fi

        log_success "Namespace ${namespace} deleted"
else
        log_info "Namespace ${namespace} not found, skipping deletion"
fi
}

# Clean up webhooks
cleanup_webhooks() {
log_info "Cleaning up webhooks..."
oc delete servingruntimes,isvc --all -A
# Validating webhooks
for webhook in $(oc get validatingwebhookconfiguration --no-headers | grep -E "kserve|knative|istio|opendatahub" | awk '{print $1}'); do
        log_info "Deleting validating webhook: ${webhook}"
        oc delete validatingwebhookconfiguration "$webhook"  || true
done

# Mutating webhooks
for webhook in $(oc get mutatingwebhookconfiguration --no-headers | grep -E "kserve|knative|istio|opendatahub" | awk '{print $1}'); do
        log_info "Deleting mutating webhook: ${webhook}"
        oc delete mutatingwebhookconfiguration "$webhook"  || true
done

log_success "Webhook cleanup completed"
}

# Clean up demo namespaces
cleanup_demo_namespaces() {
log_info "Cleaning up demo namespaces..."

local demo_namespaces=("$KSERVE_DEMO_NAMESPACE" "$PIPELINE_DEMO_NAMESPACE" "$MINIO_NAMESPACE")

for ns in "${demo_namespaces[@]}"; do
        delete_namespace "$ns"
done

log_success "Demo namespaces cleanup completed"
}

# Clean up RHOAI components
cleanup_rhoai_components() {
log_info "Cleaning up RHOAI components..."

# Delete KfDef instances (RHOAI 1.x)
log_info "Deleting KfDef instances..."
oc delete kfdef --all -n "$RHODS_NOTEBOOKS_NAMESPACE"  || true
oc delete kfdef --all -n "$RHODS_MONITORING_NAMESPACE"  || true
oc delete kfdef --all -n "$RHODS_APPS_NAMESPACE"  || true

# Delete RHOAI custom resources
log_info "Deleting RHOAI custom resources..."
local rhoai_resources=(
        "AcceleratorProfile"
        "DataSciencePipelinesApplication"
        "FeatureTracker"
        "OdhApplication"
        "OdhDashboardConfig"
        "OdhDocument"
        "PyTorchJob"
        "RayCluster"
        "TrustyAIService"
        "LMEvalJob"
        "clusterqueues.kueue.x-k8s.io"
        "resourceflavors.kueue.x-k8s.io"
        "workloadpriorityclasses.kueue.x-k8s.io"
        "workloads.kueue.x-k8s.io"
        "kubeflow.org.Notebook"
        "DataScienceCluster"
        "DSCInitialization"
)

for resource in "${rhoai_resources[@]}"; do
        delete_resources "$resource"
done

# Patch specific resources
log_info "Patching specific RHOAI resources..."
oc patch dsc default-dsc -p '{"metadata": {"finalizers": []}}' --type=merge  || true
oc patch dsc rhoai -p '{"metadata": {"finalizers": []}}' --type=merge  || true
oc delete dsc --all --force --grace-period=0 --wait=false  || true
oc patch dsci default-dsci -p '{"metadata": {"finalizers": []}}' --type=merge  || true
oc delete dsci --all --force --grace-period=0 --wait=false  || true

log_success "RHOAI components cleanup completed"
}

# Clean up operators and subscriptions
cleanup_operators() {
log_info "Cleaning up operators and subscriptions..."

# Subscriptions to delete: operator-name:namespace
local sub_entries=(
        "opendatahub-operator:openshift-operators"
        "openshift-pipelines-operator-rh:openshift-operators"
        "rhcl-operator:openshift-operators"
        "cert-manager-operator:cert-manager-operator"
        "kueue-operator:openshift-kueue-operator"
        "custom-metrics-autoscaler:openshift-keda"
        "leader-worker-set:openshift-lws-operator"
)

for entry in "${sub_entries[@]}"; do
        sub_name="${entry%%:*}"
        ns="${entry##*:}"
        log_info "Deleting subscription ${sub_name} in ${ns}"
        oc delete sub "$sub_name" -n "$ns" --force --grace-period=0 2>/dev/null || true
done

# RHCL creates dependent subscriptions automatically — clean them too
log_info "Deleting RHCL dependent subscriptions..."
for sub in $(oc get sub -n openshift-operators --no-headers 2>/dev/null | grep -iE "authorino|limitador|dns-operator" | awk '{print $1}'); do
        log_info "Deleting dependent sub ${sub}"
        oc delete sub "$sub" -n openshift-operators --force --grace-period=0 2>/dev/null || true
done
for sub in $(oc get sub -n kuadrant-system --no-headers 2>/dev/null | awk '{print $1}'); do
        oc delete sub "$sub" -n kuadrant-system --force --grace-period=0 2>/dev/null || true
done

# RHOAI subscription (may have custom name)
for sub in $(oc get sub -n redhat-ods-operator --no-headers 2>/dev/null | awk '{print $1}'); do
        log_info "Deleting RHOAI sub ${sub}"
        oc delete sub "$sub" -n redhat-ods-operator --force --grace-period=0 2>/dev/null || true
done

# Clean up Kuadrant CR (must be before CSV deletion)
log_info "Cleaning up Kuadrant resources..."
oc patch kuadrant kuadrant -n "$KUADRANT_NAMESPACE" -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
oc delete kuadrant --all -n "$KUADRANT_NAMESPACE" --force --grace-period=0 --wait=false 2>/dev/null || true

# Clean up LWS CR
log_info "Cleaning up LWS resources..."
oc patch leaderworkersetoperator cluster -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
oc delete leaderworkersetoperator cluster --force --grace-period=0 --wait=false 2>/dev/null || true

# Clean up Kueue CR (kueue.openshift.io — the standalone operator CR)
log_info "Cleaning up Kueue operator resources..."
oc patch kueue.kueue.openshift.io cluster -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
oc delete kueue.kueue.openshift.io cluster --force --grace-period=0 --wait=false 2>/dev/null || true

# Clean up Kueue workload resources (ClusterQueues, LocalQueues, ResourceFlavors)
oc delete clusterqueues.kueue.x-k8s.io --all --force --grace-period=0 2>/dev/null || true
oc delete localqueues.kueue.x-k8s.io --all -A --force --grace-period=0 2>/dev/null || true
oc delete resourceflavors.kueue.x-k8s.io --all --force --grace-period=0 2>/dev/null || true

# Clean up cert-manager-specific resources
log_info "Cleaning up cert-manager resources..."
oc delete certificates --all -A --force --grace-period=0 2>/dev/null || true
oc delete certificaterequests --all -A --force --grace-period=0 2>/dev/null || true
oc delete issuers --all -A --force --grace-period=0 2>/dev/null || true
oc delete clusterissuers --all -A --force --grace-period=0 2>/dev/null || true
oc delete challenges --all -A --force --grace-period=0 2>/dev/null || true
oc delete orders --all -A --force --grace-period=0 2>/dev/null || true

# Clean up KEDA-specific resources
log_info "Cleaning up KEDA resources..."
oc delete kedacontroller --all -A --force --grace-period=0 --wait=false 2>/dev/null || true
oc delete scaledobjects --all -A --force --grace-period=0 2>/dev/null || true
oc delete scaledjobs --all -A --force --grace-period=0 2>/dev/null || true

# Delete ALL non-system CSVs cluster-wide (handles copied CSVs from AllNamespaces mode)
log_info "Deleting all operator CSVs cluster-wide..."
for csv_name in $(oc get csv -A --no-headers 2>/dev/null | grep -v "packageserver" | awk '{print $2}' | sort -u); do
        log_info "Deleting CSV ${csv_name} from all namespaces..."
        for ns in $(oc get csv -A --no-headers 2>/dev/null | grep "$csv_name" | awk '{print $1}'); do
                oc delete csv "$csv_name" -n "$ns" --force --grace-period=0 2>/dev/null &
        done
        wait
done

# Delete InstallPlans in all operator namespaces
log_info "Deleting InstallPlans..."
for ns in openshift-operators cert-manager-operator openshift-kueue-operator openshift-keda openshift-lws-operator redhat-ods-operator; do
        oc delete installplan --all -n "$ns" --force --grace-period=0 2>/dev/null || true
done

# Delete RHOAI catalog source
log_info "Deleting RHOAI catalog sources..."
oc delete catalogsource rhoai-catalog-dev -n openshift-marketplace 2>/dev/null || true
oc delete catalogsource rhods-catalog-dev -n openshift-marketplace 2>/dev/null || true

log_success "Operators cleanup completed"
}

# Clean up CRDs
cleanup_crds() {
log_info "Cleaning up CRDs..."

# List of CRDs to delete
local crds_to_delete=(
    "kfdefs.kfdef.apps.kubeflow.org"
    "acceleratorprofiles.dashboard.opendatahub.io"
    "accounts.nim.opendatahub.io"
    "authorizationpolicies.security.istio.io"
    "auths.services.platform.opendatahub.io"
    "certificates.networking.internal.knative.dev"
    "clusterdomainclaims.networking.internal.knative.dev"
    "clusterlocalmodels.serving.kserve.io"
    "clusterstoragecontainers.serving.kserve.io"
    "codeflares.components.platform.opendatahub.io"
    "configurations.serving.knative.dev"
    "dashboards.components.platform.opendatahub.io"
    "datascienceclusters.datasciencecluster.opendatahub.io"
    "datasciencepipelines.components.platform.opendatahub.io"
    "datasciencepipelinesapplications.datasciencepipelinesapplications.opendatahub.io"
    "destinationrules.networking.istio.io"
    "domainmappings.serving.knative.dev"
    "dscinitializations.dscinitialization.opendatahub.io"
    "envoyfilters.networking.istio.io"
    "feastoperators.components.platform.opendatahub.io"
    "featuretrackers.features.opendatahub.io"
    "gateways.networking.istio.io"
    "hardwareprofiles.dashboard.opendatahub.io"
    "images.caching.internal.knative.dev"
    "inferencegraphs.serving.kserve.io"
    "inferenceservices.serving.kserve.io"
    "ingresses.networking.internal.knative.dev"
    "knativeeventings.operator.knative.dev"
    "knativeservings.operator.knative.dev"
    "kserves.components.platform.opendatahub.io"
    "kueues.components.platform.opendatahub.io"
    "localmodelnodegroups.serving.kserve.io"
    "metrics.autoscaling.internal.knative.dev"
    "modelcontrollers.components.platform.opendatahub.io"
    "modelmeshservings.components.platform.opendatahub.io"
    "modelregistries.components.platform.opendatahub.io"
    "modelregistries.modelregistry.opendatahub.io"
    "monitorings.services.platform.opendatahub.io"
    "odhapplications.dashboard.opendatahub.io"
    "odhdashboardconfigs.opendatahub.io"
    "odhdocuments.dashboard.opendatahub.io"
    "odhquickstarts.console.openshift.io"
    "peerauthentications.security.istio.io"
    "podautoscalers.autoscaling.internal.knative.dev"
    "predictors.serving.kserve.io"
    "proxyconfigs.networking.istio.io"
    "rays.components.platform.opendatahub.io"
    "requestauthentications.security.istio.io"
    "revisions.serving.knative.dev"
    "routes.serving.knative.dev"
    "serviceentries.networking.istio.io"
    "services.serving.knative.dev"
    "servingruntimes.serving.kserve.io"
    "sidecars.networking.istio.io"
    "telemetries.telemetry.istio.io"
    "trainedmodels.serving.kserve.io"
    "trainingoperators.components.platform.opendatahub.io"
    "trustyais.components.platform.opendatahub.io"
    "trustyaiservices.trustyai.opendatahub.io"
    "trustyaiservices.trustyai.opendatahub.io.trustyai.opendatahub.io"
    "virtualservices.networking.istio.io"
    "wasmplugins.extensions.istio.io"
    "workbenches.components.platform.opendatahub.io"
    "workloadentries.networking.istio.io"
    "workloadgroups.networking.istio.io"
    "notebooks.kubeflow.org"
    "appwrappers.workload.codeflare.dev"
    "quotasubtrees.quota.codeflare.dev"
    "schedulingspecs.workload.codeflare.dev"
    "rayclusters.ray.io"
    "rayjobs.ray.io"
    "rayservices.ray.io"
    "admissionchecks.kueue.x-k8s.io"
    "clusterqueues.kueue.x-k8s.io"
    "localqueues.kueue.x-k8s.io"
    "multikueueclusters.kueue.x-k8s.io"
    "multikueueconfigs.kueue.x-k8s.io"
    "provisioningrequestconfigs.kueue.x-k8s.io"
    "resourceflavors.kueue.x-k8s.io"
    "workloadpriorityclasses.kueue.x-k8s.io"
    "workloads.kueue.x-k8s.io"
    "lmevaljobs.trustyai.opendatahub.io"
    "certificates.cert-manager.io"
    "certificaterequests.cert-manager.io"
    "challenges.acme.cert-manager.io"
    "clusterissuers.cert-manager.io"
    "issuers.cert-manager.io"
    "orders.acme.cert-manager.io"
    "kueuecontrollers.keda.sh"
    "kedacontrollers.keda.sh"
    "scaledobjects.keda.sh"
    "scaledjobs.keda.sh"
    "triggerauthentications.keda.sh"
    "clustertriggerauthentications.keda.sh"

)

# Delete additional CRDs by pattern
log_info "Deleting CRDs by pattern...BG started"
(
log_info "Deleting CRDs by pattern..."
for crd in $(oc get crd --no-headers | grep -E "kserve|knative|istio|opendatahub|cert-manager|kueue|keda|kuadrant|authorino|limitador|leaderworkerset" | awk '{print $1}'); do
    log_info "Force-removing finalizers and deleting CRD: ${crd}"
    oc patch crd "$crd" --type=json -p='[{"op": "remove", "path": "/metadata/finalizers"}]' 2>/dev/null || true
    oc delete crd "$crd" --force --grace-period=0 --timeout=5s 2>/dev/null || true
done
) &
log_info "30 sec sleep...."
sleep 30
# Delete CRDs from the list
for crd in "${crds_to_delete[@]}"; do
        log_info "Deleting CRD: ${crd}"
        oc patch crd "$crd" -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
        oc delete crd "$crd" --ignore-not-found --force --grace-period=0 --timeout=5s 2>/dev/null || true
done

log_info "Deleting CRDs by pattern..."
for crd in $(oc get crd --no-headers | grep -E "kserve|knative|istio|opendatahub|cert-manager|kueue|keda|kuadrant|authorino|limitador|leaderworkerset" | awk '{print $1}'); do
        log_info "Deleting CRD: ${crd}"
        oc patch crd "$crd" -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
        oc delete crd "$crd" --ignore-not-found --force --grace-period=0 --timeout=5s 2>/dev/null || true
done

log_success "CRDs cleanup completed"
}

# Clean up namespaces
cleanup_namespaces() {
log_info "Cleaning up namespaces..."

local namespaces_to_delete=(
        "$RHODS_NOTEBOOKS_NAMESPACE"
        "$RHODS_APPS_NAMESPACE"
        "$RHODS_AUTH_PROVIDER_NAMESPACE"
        "$RHODS_MONITORING_NAMESPACE"
        "$RHODS_OPERATOR_NAMESPACE"
        "$RHODS_MODEL_REGISTRY_NAMESPACE"
        "$OPENDATAHUB_NAMESPACE"
        "$OPENDATAHUB_OPERATORS_NAMESPACE"
        "$OPENDATAHUB_AUTH_PROVIDER_NAMESPACE"
        "$OPENDATAHUB_MODEL_REGISTRY_NAMESPACE"
        "$ISTIO_NAMESPACE"
        "$KNATIVE_SERVING_NAMESPACE"
        "$KNATIVE_EVENTING_NAMESPACE"
        "$CERT_MANAGER_NAMESPACE"
        "$CERT_MANAGER_DATA_NAMESPACE"
        "$KUEUE_NAMESPACE"
        "$KEDA_NAMESPACE"
        "$KUADRANT_NAMESPACE"
        "$LWS_NAMESPACE"
)

for ns in "${namespaces_to_delete[@]}"; do
        delete_namespace "$ns"
done

# Force-clear any remaining terminating namespaces
log_info "Clearing finalizers on any terminating namespaces..."
for ns in $(oc get ns --no-headers 2>/dev/null | grep "Terminating" | awk '{print $1}'); do
        log_info "Force-clearing terminating namespace ${ns}..."
        oc get ns "$ns" -o json 2>/dev/null | \
                python3 -c 'import json,sys; o=json.load(sys.stdin); o["spec"]["finalizers"]=[]; print(json.dumps(o))' | \
                oc replace --raw "/api/v1/namespaces/$ns/finalize" -f - 2>/dev/null || true
done

log_success "Namespaces cleanup completed"
}

# Clean up Knative resources
cleanup_knative() {
log_info "Cleaning up Knative resources..."

local knative_namespaces=(
        "$KNATIVE_SERVING_NAMESPACE"
        "$KNATIVE_EVENTING_NAMESPACE"
)

for ns in "${knative_namespaces[@]}"; do
        if oc get namespace "$ns" &>/dev/null; then
        log_info "Deleting all resources in ${ns}"
        delete_resources "all" "$ns" "--force --grace-period=0"

        log_info "Deleting KnativeServing in ${ns}"
        delete_resources "KnativeServing" "$ns" "--force --grace-period=0"
        fi
done

log_success "Knative cleanup completed"
}

# Main cleanup function
main_cleanup() {
log_info "Starting RHOAI/Kserve forceful uninstallation..."

# Cleanup webhooks first to prevent interference
cleanup_webhooks

# Clean up demo namespaces
cleanup_demo_namespaces

# Clean up RHOAI components
cleanup_rhoai_components

# Clean up operators and subscriptions
cleanup_operators

# Clean up Knative resources
cleanup_knative

# Clean up CRDs
cleanup_crds

# Clean up namespaces (this should be last)
cleanup_namespaces

# Final webhook cleanup in case new ones were created
cleanup_webhooks

log_success "RHOAI/Kserve forceful uninstallation completed!"

# Final recommendations
echo -e "\n${YELLOW}Recommendations:${NC}"
echo "1. Verify cleanup with:"
echo "   oc get crd | grep -E 'opendatahub|kubeflow|kserve|ray|cert-manager|kueue|knative|istio|keda|kuadrant|authorino|limitador|leaderworkerset'"
echo "   oc get ns | grep -E 'redhat-ods|opendatahub|rhods|istio|knative|cert-manager|kueue|keda|kuadrant|lws'"
echo "   oc get csv -A | grep -v packageserver"
echo "   oc get sub -A"
echo "2. You may need to restart the cluster if some resources remain in terminating state"
}

# Main execution
main() {
check_prerequisites
init_variables
main_cleanup
}

# Execute main function
main
