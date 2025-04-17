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
export SERVERLESS_NAMESPACE="openshift-serverless"
export RHOAI_SERVERLESS_NAMESPACE="rhoai-serverless"
export AUTHORINO_NAMESPACE="authorino-auth-provider"

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

        oc delete "$resource_type" --all $extra_flags -n "$namespace" --ignore-not-found || true
else
        oc get "$resource_type" --all-namespaces --no-headers -o name 2>/dev/null | while read -r resource; do
        log_info "Removing finalizers from ${resource}"
        oc patch "$resource" -p '{"metadata":{"finalizers":[]}}' --type=merge || true
        done

        oc delete "$resource_type" --all $extra_flags --all-namespaces --ignore-not-found || true
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
        oc delete namespace "$namespace" --force --grace-period=0 --ignore-not-found || true

        # Verify deletion
        if oc get namespace "$namespace" &>/dev/null; then
        log_warning "Namespace ${namespace} still exists. Retrying deletion..."
        sleep 5
        oc delete namespace "$namespace" --force --grace-period=0 --ignore-not-found || true
        fi

        log_success "Namespace ${namespace} deleted"
else
        log_info "Namespace ${namespace} not found, skipping deletion"
fi
}

# Clean up webhooks
cleanup_webhooks() {
log_info "Cleaning up webhooks..."

# Validating webhooks
for webhook in $(oc get validatingwebhookconfiguration --no-headers | grep -E "kserve|knative|istio|opendatahub" | awk '{print $1}'); do
        log_info "Deleting validating webhook: ${webhook}"
        oc delete validatingwebhookconfiguration "$webhook" --ignore-not-found || true
done

# Mutating webhooks
for webhook in $(oc get mutatingwebhookconfiguration --no-headers | grep -E "kserve|knative|istio|opendatahub" | awk '{print $1}'); do
        log_info "Deleting mutating webhook: ${webhook}"
        oc delete mutatingwebhookconfiguration "$webhook" --ignore-not-found || true
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
oc delete kfdef --all -n "$RHODS_NOTEBOOKS_NAMESPACE" --ignore-not-found || true
oc delete kfdef --all -n "$RHODS_MONITORING_NAMESPACE" --ignore-not-found || true
oc delete kfdef --all -n "$RHODS_APPS_NAMESPACE" --ignore-not-found || true

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
oc patch dsc default-dsc -p '{"metadata": {"finalizers": []}}' --type=merge --ignore-not-found || true
oc patch dsc rhoai -p '{"metadata": {"finalizers": []}}' --type=merge --ignore-not-found || true
oc delete dsc --all --force --grace-period=0 --wait --ignore-not-found || true
oc patch dsci default-dsci -p '{"metadata": {"finalizers": []}}' --type=merge --ignore-not-found || true
oc delete dsci --all --force --grace-period=0 --wait --ignore-not-found || true

log_success "RHOAI components cleanup completed"
}

# Clean up operators and subscriptions
cleanup_operators() {
log_info "Cleaning up operators and subscriptions..."

# Delete subscriptions and CSVs
local operators=(
        "opendatahub-operator"
        "authorino-operator"
        "servicemeshoperator"
        "serverless-operator"
        "openshift-pipelines-operator-rh"
)

for operator in "${operators[@]}"; do
        log_info "Deleting subscription for ${operator}"
        oc delete sub "$operator" --force --grace-period=0 -n openshift-operators --ignore-not-found || true

        log_info "Deleting CSV for ${operator}"
        oc delete csv -n openshift-operators $(oc get csv -n openshift-operators | grep "$operator" | awk '{print $1}') --ignore-not-found || true
done

# Delete InstallPlans
log_info "Deleting InstallPlans..."
for installplan in $(oc get installPlan -n openshift-operators | grep -E 'authorino|serverless|servicemeshoperator|opendatahub|pipeline' | awk '{print $1}'); do
        oc delete installPlan -n openshift-operators "$installplan" --ignore-not-found || true
done

log_success "Operators cleanup completed"
}

# Clean up CRDs
cleanup_crds() {
log_info "Cleaning up CRDs..."

# List of CRDs to delete
local crds_to_delete=(
        "kfdefs.kfdef.apps.kubeflow.org"
        "acceleratorprofiles.dashboard.opendatahub.io"
        "datascienceclusters.datasciencecluster.opendatahub.io"
        "datasciencepipelinesapplications.datasciencepipelinesapplications.opendatahub.io"
        "dscinitializations.dscinitialization.opendatahub.io"
        "featuretrackers.features.opendatahub.io"
        "modelregistries.modelregistry.opendatahub.io"
        "odhapplications.dashboard.opendatahub.io"
        "odhdashboardconfigs.opendatahub.io"
        "odhdocuments.dashboard.opendatahub.io"
        "odhquickstarts.console.openshift.io"
        "trustyaiservices.trustyai.opendatahub.io"
        "lmevaljobs.trustyai.opendatahub.io"
        "trustyaiservices.trustyai.opendatahub.io.trustyai.opendatahub.io"
        "inferenceservices.serving.kserve.io"
        "inferencegraphs.serving.kserve.io"
        "servingruntimes.serving.kserve.io"
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
        "services.serving.knative.dev"
)

# Delete CRDs from the list
for crd in "${crds_to_delete[@]}"; do
        log_info "Deleting CRD: ${crd}"
        oc patch crd "$crd" -p '{"metadata":{"finalizers":[]}}' --type=merge --ignore-not-found || true
        oc delete crd "$crd" --force --grace-period=0 --ignore-not-found || true
done

# Delete additional CRDs by pattern
log_info "Deleting CRDs by pattern..."
for crd in $(oc get crd --no-headers | grep -E "kserve|knative|istio|opendatahub|serverless|authorino" | awk '{print $1}'); do
        log_info "Deleting CRD: ${crd}"
        oc patch crd "$crd" -p '{"metadata":{"finalizers":[]}}' --type=merge --ignore-not-found || true
        oc delete crd "$crd" --force --grace-period=0 --ignore-not-found || true
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
        "$SERVERLESS_NAMESPACE"
        "$RHOAI_SERVERLESS_NAMESPACE"
        "$AUTHORINO_NAMESPACE"
)

for ns in "${namespaces_to_delete[@]}"; do
        delete_namespace "$ns"
done

log_success "Namespaces cleanup completed"
}

# Clean up Istio resources
cleanup_istio() {
log_info "Cleaning up Istio resources..."

if oc get namespace "$ISTIO_NAMESPACE" &>/dev/null; then
        log_info "Deleting ServiceMeshControlPlane in ${ISTIO_NAMESPACE}"
        delete_resources "ServiceMeshControlPlane" "$ISTIO_NAMESPACE" "--force --grace-period=0"

        log_info "Patching and deleting SMCP resources"
        for smcp in $(oc get smcp -n "$ISTIO_NAMESPACE" --no-headers | awk '{print $1}'); do
        oc patch smcp "$smcp" -n "$ISTIO_NAMESPACE" -p '{"metadata": {"finalizers": []}}' --type=merge --ignore-not-found || true
        oc delete smcp "$smcp" -n "$ISTIO_NAMESPACE" --ignore-not-found || true
        done

        log_info "Patching and deleting SMMR resources"
        for smmr in $(oc get smmr -n "$ISTIO_NAMESPACE" --no-headers | awk '{print $1}'); do
        oc patch smmr "$smmr" -n "$ISTIO_NAMESPACE" -p '{"metadata": {"finalizers": []}}' --type=merge --ignore-not-found || true
        oc delete smmr "$smmr" -n "$ISTIO_NAMESPACE" --ignore-not-found || true
        done

        log_info "Deleting SMM resources"
        delete_resources "servicemeshmemberrolls.maistra.io" "$ISTIO_NAMESPACE" "--force --grace-period=0"
        delete_resources "servicemeshmembers.maistra.io" "$ISTIO_NAMESPACE" "--force --grace-period=0"

        log_info "Deleting maistra-admission-controller service"
        oc delete svc maistra-admission-controller -n openshift-operators --ignore-not-found || true
else
        log_info "Istio namespace not found, skipping Istio cleanup"
fi

log_success "Istio cleanup completed"
}

# Clean up Knative resources
cleanup_knative() {
log_info "Cleaning up Knative resources..."

local knative_namespaces=(
        "$KNATIVE_SERVING_NAMESPACE"
        "$KNATIVE_EVENTING_NAMESPACE"
        "$RHOAI_SERVERLESS_NAMESPACE"
        "$SERVERLESS_NAMESPACE"
)

for ns in "${knative_namespaces[@]}"; do
        if oc get namespace "$ns" &>/dev/null; then
        log_info "Deleting all resources in ${ns}"
        delete_resources "all" "$ns" "--force --grace-period=0"

        log_info "Deleting KnativeServing in ${ns}"
        delete_resources "KnativeServing" "$ns" "--force --grace-period=0"
        fi
done

log_info "Deleting OperatorGroup in openshift-serverless"
oc delete OperatorGroup serverless-operators -n openshift-serverless --ignore-not-found || true

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

# Clean up Istio resources
cleanup_istio

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
echo "   oc get crd | grep -E 'opendatahub|kubeflow|kserve|ray|kueue|knative|istio'"
echo "   oc get ns | grep -E 'redhat-ods|opendatahub|rhods|istio|knative|serverless'"
echo "2. You may need to restart the cluster if some resources remain in terminating state"
}

# Main execution
main() {
check_prerequisites
init_variables
main_cleanup
}

# Execute main function
main "$@"