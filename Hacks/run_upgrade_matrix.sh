#!/bin/bash

# Configuration
upgrade_from="2.19"
upgrade_to="2.20"
test_dir="opendatahub-tests"
log_dir="/var/www/html"

# Clone the repository
git clone https://github.com/opendatahub-io/opendatahub-tests.git
cd "$test_dir" || exit

# Scenario 1: Serverless and ModelMesh
echo "Running Scenario 1: Serverless and ModelMesh"

# Pre-upgrade steps
python main.py --cleanup
python main.py --all --rhoai --rhoai-channel=fast --rhoai-image="quay.io/rhoai/rhoai-fbc-fragment:rhoai-${upgrade_from}-nightly" --raw=False --deploy-rhoai-resources

# Pre-upgrade tests
echo "Running pre-upgrade tests for Scenario 1"
PYTHONUNBUFFERED=1 stdbuf -oL -eL uv run pytest -m "pre_upgrade and serverless and modelmesh" --tc=distribution:downstream 2>&1 | tee "${log_dir}/pre_upgrade_${upgrade_to}.log"

# Post-upgrade steps
cd .. || exit
python main.py --all --rhoai --rhoai-channel=fast --rhoai-image="quay.io/rhoai/rhoai-fbc-fragment:rhoai-${upgrade_to}-nightly" --raw=False

# Post-upgrade tests
echo "Running post-upgrade tests for Scenario 1"
cd "$test_dir" || exit
PYTHONUNBUFFERED=1 stdbuf -oL -eL uv run pytest -m "post_upgrade and serverless and modelmesh" --tc=distribution:downstream 2>&1 | tee "${log_dir}/post_upgrade_${upgrade_to}.log"

# Scenario 2: Raw Deployment
echo "Running Scenario 2: Raw Deployment"

# Pre-upgrade steps
cd .. || exit
python main.py --cleanup
python main.py --rhoai --rhoai-channel=fast --rhoai-image="quay.io/rhoai/rhoai-fbc-fragment:rhoai-${upgrade_from}-nightly" --raw=True --deploy-rhoai-resources

# Pre-upgrade tests
echo "Running pre-upgrade tests for Scenario 2"
cd "$test_dir" || exit
PYTHONUNBUFFERED=1 stdbuf -oL -eL uv run pytest -m "pre_upgrade and rawdeployment" --tc=distribution:downstream 2>&1 | tee "${log_dir}/pre_upgrade_${upgrade_to}_1.log"

# Post-upgrade steps
cd .. || exit
python main.py --all --rhoai --rhoai-channel=fast --rhoai-image="quay.io/rhoai/rhoai-fbc-fragment:rhoai-${upgrade_to}-nightly" --raw=True

# Post-upgrade tests
echo "Running post-upgrade tests for Scenario 2"
cd "$test_dir" || exit
PYTHONUNBUFFERED=1 stdbuf -oL -eL uv run pytest -m "post_upgrade and rawdeployment" --tc=distribution:downstream 2>&1 | tee "${log_dir}/post_upgrade_${upgrade_to}_1.log"

echo "All upgrade tests completed"