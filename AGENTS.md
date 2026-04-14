## Learned User Preferences

- Do not treat OpenShift Serverless, Service Mesh, or Authorino as supported RHOShift install targets; remove or avoid reintroducing them across CLI, tests, cleanup, and upgrade docs.
- When adding operators, follow up with cluster validation after cleanup or full reinstall and adjust scripts when an operator fails to become ready.
- Prefer catalog-backed installs on the latest stable channel unless the user explicitly pins a RHOAI catalog image or channel.
- Install and run the tool from the local checkout with pip (for example editable install) when verifying behavior against a live cluster.
- Resolve operator subscription channels to the latest channel the catalog actually offers (for example for Kueue) when nothing is pinned, instead of assuming a fixed channel name such as `stable`.
- Do not embed cluster tokens, PyPI credentials, or other secrets in the repository, documentation, or copy-pastable shell examples; use environment variables or user-local configuration only.

## Learned Workspace Facts

- RHOShift is the `rhoshift` Python package: a CLI for installing, cleaning up, health-checking, and upgrade-testing RHOAI-related operators on OpenShift using `oc` and the Kubernetes/OpenShift client libraries.
- Supported first-class operators include cert-manager, Kueue, KEDA, RHOAI/ODH (`opendatahub-operator`), RHCL (`rhcl-operator`, `stable`), and LWS (`leader-worker-set` in `openshift-lws-operator`, `stable-v1.0`); `--all` enables all six of those operator flags at once.
- RHCL installation is wired to create a `Kuadrant` custom resource in the `kuadrant-system` namespace after the operator install path runs.
- LWS installation is wired to create the Leader Worker Set operator custom resource after the `leader-worker-set` operator install path runs.
- Upgrade matrix documentation and the `run-upgrade_matrix.sh` scenario list were reduced to the `rawdeployment` scenario after serverless-related scenarios were dropped.
- RHOAI DSC readiness can fail with Kueue API errors (for example missing `ResourceFlavor` under `kueue.x-k8s.io`) when Kueue CRDs or the cluster `Kueue` instance are not fully reconciled; install and cleanup paths include logic to clear stuck Kueue state where needed.
- The CLI is published on PyPI as `rhoshift`; releases are built with `python -m build` and uploaded with `twine` after bumping the version in `pyproject.toml`.
