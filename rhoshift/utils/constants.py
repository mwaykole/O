class OpenShiftOperatorInstallManifest:
    SERVERLESS_MANIFEST = """\
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-serverless
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: serverless-operator-group
  namespace: openshift-serverless
spec: {}
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: serverless-operator
  namespace: openshift-serverless
spec:
  channel: stable
  name: serverless-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
"""

    SERVICEMESH_MANIFEST = """\
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: servicemeshoperator
  namespace: openshift-operators
  labels:
    operators.coreos.com/servicemeshoperator.openshift-operators: ""
spec:
  channel: stable
  installPlanApproval: Automatic
  name: servicemeshoperator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
"""

    AUTHORINO_MANIFEST = """\
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: authorino-operator
  namespace: openshift-operators
  labels:
    operators.coreos.com/authorino-operator.openshift-operators: ""
spec:
  channel: stable
  installPlanApproval: Automatic
  name: authorino-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
"""


def get_dsci_manifest(kserve_raw=True,
                      applications_namespace="redhat-ods-applications",
                      monitoring_namespace="redhat-ods-monitoring"):
    def to_state(flag): return "Removed" if flag else "Managed"

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


def get_dsc_manifest(enable_dashboard=True,
                     enable_kserve=True,
                     enable_raw_serving=True,
                     enable_modelmeshserving=True,
                     operator_namespace="rhods-operator"):
    def to_state(flag): return "Managed" if flag else "Removed"

    return f"""apiVersion: datasciencecluster.opendatahub.io/v1
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
        name: knative-serving
    modelmeshserving:
      managementState: {to_state(enable_modelmeshserving)}
"""
