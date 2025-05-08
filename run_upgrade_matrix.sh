#!/bin/bash
set -euo pipefail

# Configuration
# CHANNEL="fast"
TEST_REPO="https://github.com/opendatahub-io/opendatahub-tests.git"
DEPENDENCIES=("oc" "uv" "python" "git")
# shellcheck disable=SC2034
REQUIRED_NAMESPACES=("redhat-ods-operator" "redhat-ods-applications")

# Global variables for tracking test results
declare -A test_results
declare -A scenario_status
declare -A pre_test_status
declare -A post_test_status

# Function to print and execute commands
run_cmd() {
    echo -e "\n\033[1;34m[RUNNING]\033[0m $*"
    "$@"
    local status=$?
    if [ $status -ne 0 ]; then
        echo -e "\033[1;31m[FAILED]\033[0m Command exited with status $status"
        return $status
    fi
    return 0
}

# Error handling
error_exit() {
    echo -e "\033[1;31m[ERROR]\033[0m $1" 1>&2
    exit 1
}

# Check dependencies
check_dependencies() {
    for cmd in "${DEPENDENCIES[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            error_exit "Required command not found: $cmd"
        fi
    done
    run_cmd oc whoami || error_exit "Not logged into OpenShift cluster"
}

# Parse test results from log file
parse_test_results() {
    local log_file=$1
    local scenario=$2
    local phase=$3

    # Extract test summary
    local summary=$(grep -E '[0-9]+ (passed|failed|skipped)' "$log_file" | tail -1)

    # Store results
    if [[ -n "$summary" ]]; then
        test_results["${scenario}_${phase}"]="$summary"

        # Determine if all tests passed
        if [[ "$summary" =~ failed ]]; then
            if [[ "$phase" == "pre" ]]; then
                pre_test_status["$scenario"]="failed"
            else
                post_test_status["$scenario"]="failed"
            fi
            scenario_status["$scenario"]="failed"
        else
            if [[ "$phase" == "pre" ]]; then
                pre_test_status["$scenario"]="passed"
            else
                post_test_status["$scenario"]="passed"
            fi
            # Only mark scenario as passed if both pre and post are passed
            if [[ "${pre_test_status[$scenario]}" == "passed" && "${post_test_status[$scenario]}" == "passed" ]]; then
                scenario_status["$scenario"]="passed"
            fi
        fi
    else
        test_results["${scenario}_${phase}"]="No test results found"
        if [[ "$phase" == "pre" ]]; then
            pre_test_status["$scenario"]="failed"
        else
            post_test_status["$scenario"]="failed"
        fi
        scenario_status["$scenario"]="failed"
    fi
}

# Run tests with output
run_tests() {
    local test_type=$1
    local scenario=$2
    local log_file=$3

    echo -e "\n\033[1;36m[TEST PHASE]\033[0m ${test_type}-upgrade for ${scenario}"
    case "$scenario" in
        "rawdeployment")
            dependent_operators=''
            ;;
        "serverless,rawdeployment")
            dependent_operators='servicemeshoperator,authorino-operator,serverless-operator'
            ;;
        "serverless")
            dependent_operators='servicemeshoperator,serverless-operator'
            ;;
        *)
            error_exit "Unknown scenario: $scenario"
            ;;
    esac

    if run_cmd uv run pytest "--${test_type}-upgrade"  --upgrade-deployment-modes="${scenario}" \
          --tc=dependent_operators:"${dependent_operators}" --tc=distribution:downstream  \
         2>&1 | tee "$log_file"; then
        parse_test_results "$log_file" "$scenario" "$test_type"
        return 0
    else
        parse_test_results "$log_file" "$scenario" "$test_type"
        return 1
    fi
}

# Print final test results
print_final_results() {
    echo -e "\n\033[1;35m==================== FINAL TEST RESULTS ====================\033[0m"

    local all_passed=true

    for scenario in "${!scenarios[@]}"; do
        echo -e "\n\033[1;33mSCENARIO: ${scenario}\033[0m"
        echo -e "  PRE-UPGRADE:  ${pre_test_status[$scenario]} - ${test_results["${scenario}_pre"]}"
        echo -e "  POST-UPGRADE: ${post_test_status[$scenario]} - ${test_results["${scenario}_post"]}"
        echo -e "  OVERALL:      ${scenario_status[$scenario]}"

        if [[ "${scenario_status[$scenario]}" != "passed" ]]; then
            all_passed=false
        fi
    done

    echo -e "\n\033[1;35m============================================================\033[0m"

    if $all_passed; then
        echo -e "\n\033[1;32m[SUCCESS] All upgrade scenarios completed successfully\033[0m"
        return 0
    else
        echo -e "\n\033[1;31m[FAILURE] Some scenarios failed. See details above.\033[0m"
        return 1
    fi
}

# Main execution
if [ $# -ne 4 ]; then
    error_exit "Usage: $0 <current_version> <current_channel> <new_version> <new_channel>\nExample: $0 1.5.0 stable 1.6.0 stable"
fi

version1=$1
channel1=$2
version2=$3
channel2=$4
fromimage="quay.io/rhoai/rhoai-fbc-fragment:rhoai-${version1}"
toimage="quay.io/rhoai/rhoai-fbc-fragment:rhoai-${version2}"

declare -A scenarios=(
    ["serverless,rawdeployment"]="--serverless --authorino --servicemesh"
    ["serverless"]="--serverless --servicemesh "
    ["rawdeployment"]=""
)

# Initialize status tracking
for scenario in "${!scenarios[@]}"; do
    scenario_status["$scenario"]="pending"
    pre_test_status["$scenario"]="pending"
    post_test_status["$scenario"]="pending"
done

# Pre-flight checks
check_dependencies

# Process each scenario
for scenario in "${!scenarios[@]}"; do
    echo -e "\n\033[1;35m==================== [SCENARIO: ${scenario^^}] ====================\033[0m"
    timestamp=$(date +%Y%m%d%H%M)
    mkdir -p logs
    pre_log="logs/pre-${scenario}-${timestamp}.log"
    post_log="logs/post-${scenario}-${timestamp}.log"

    # Set parameters
    if [ "$scenario" == "rawdeployment" ]; then
        raw="True"
    else
        raw="False"
    fi

    # Cleanup before scenario
    echo -e "\n\033[1;33m[CLEANUP]\033[0m Preparing environment for scenario"
    run_cmd python main.py --cleanup

    # PRE-UPGRADE PHASE
    echo -e "\n\033[1;32m[PHASE 1] PRE-UPGRADE INSTALLATION\033[0m"
    echo "Installing version: $version1 with options: ${scenarios[$scenario]}"
    # shellcheck disable=SC2086
    run_cmd python main.py ${scenarios[$scenario]} \
        --rhoai \
        --rhoai-channel="$channel1" \
        --rhoai-image="$fromimage" \
        --raw="$raw" \
        --deploy-rhoai-resources

    # Clone/update tests
    if [ -d "opendatahub-tests" ]; then
        run_cmd cd opendatahub-tests
        run_cmd git pull --quiet
        run_cmd cd ..
    else
        run_cmd git clone --quiet "$TEST_REPO"
    fi

    # PRE-UPGRADE TESTS
    run_cmd cd opendatahub-tests
    run_tests "pre" "$scenario" "../$pre_log"
    run_cmd cd ..

    # UPGRADE PHASE
    echo -e "\n\033[1;32m[PHASE 2] UPGRADE EXECUTION\033[0m"
    echo "Upgrading to version: $version2"
    run_cmd python main.py --rhoai \
        --rhoai-channel="$channel2" \
        --rhoai-image="$toimage" \
        --raw="$raw"

    # Verify deployment
    echo -e "\n\033[1;33m[VERIFICATION]\033[0m Checking system status"
    sleep 10

    # POST-UPGRADE TESTS
    echo -e "\n\033[1;32m[PHASE 3] POST-UPGRADE VALIDATION\033[0m"
    run_cmd cd opendatahub-tests
    run_tests "post" "$scenario" "../$post_log"
    run_cmd cd ..

    echo -e "\033[1;35m==================== [SCENARIO COMPLETE] ====================\033[0m"
done

# Print final results
print_final_results
exit $?