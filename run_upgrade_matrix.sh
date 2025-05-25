#!/bin/bash
set -euo pipefail

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
# CHANNEL="fast"
TEST_REPO="https://github.com/opendatahub-io/opendatahub-tests.git"
DEPENDENCIES=("oc" "uv" "python" "git")
# shellcheck disable=SC2034
REQUIRED_NAMESPACES=("redhat-ods-operator" "redhat-ods-applications")

# Default values
SKIP_CLEANUP=false
SCENARIOS_TO_RUN=()
TOTAL_WAIT_TIME=300  # 10 minutes in seconds
FROM_IMAGE=""
TO_IMAGE=""

# Global variables for tracking test results
declare -A test_results
declare -A scenario_status
declare -A pre_test_status
declare -A post_test_status

# Check for required environment variables
if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    echo "Warning: AWS credentials not set. Some tests may fail."
    echo "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
fi

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
            # For rawdeployment, we use empty string for dependent operators
            dependent_operators=""
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

    # Run tests and capture output, but don't exit on failure
    if uv run pytest "--${test_type}-upgrade"  --upgrade-deployment-modes="${scenario}" \
          --tc=dependent_operators:"${dependent_operators}" --tc=distribution:downstream  \
         2>&1 | tee "$log_file"; then
        parse_test_results "$log_file" "$scenario" "$test_type"
        return 0
    else
        # Even if tests fail, parse results and continue
        parse_test_results "$log_file" "$scenario" "$test_type"
        echo -e "\n\033[1;31m[WARNING] Tests failed for ${test_type}-upgrade in scenario ${scenario}\033[0m"
        echo -e "See detailed results in: $log_file"
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

# Function to print usage
print_usage() {
    echo "Usage: $0 [options] <current_version> <current_channel> <new_version> <new_channel>"
    echo ""
    echo "Options:"
    echo "  -h, --help                 Show this help message"
    echo "  -s, --scenario SCENARIO    Run specific scenario(s). Can be used multiple times."
    echo "                            Available scenarios: serverless, rawdeployment, serverless,rawdeployment"
    echo "  --skip-cleanup            Skip cleanup before each scenario"
    echo "  --from-image IMAGE        Custom source image path (default: quay.io/rhoai/rhoai-fbc-fragment:rhoai-{version})"
    echo "  --to-image IMAGE          Custom target image path (default: quay.io/rhoai/rhoai-fbc-fragment:rhoai-{version})"
    echo ""
    echo "Example:"
    echo "  $0 -s serverless -s rawdeployment 2.10 stable 2.12 stable"
    echo "  $0 --skip-cleanup 2.10 stable 2.12 stable"
    echo "  $0 --from-image custom.registry/rhoai:1.5.0 --to-image custom.registry/rhoai:1.6.0 2.10 stable 2.12 stable"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        -s|--scenario)
            SCENARIOS_TO_RUN+=("$2")
            shift 2
            ;;
        --skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        --from-image)
            FROM_IMAGE="$2"
            shift 2
            ;;
        --to-image)
            TO_IMAGE="$2"
            shift 2
            ;;
        *)
            # If it's not an option, it must be the version/channel arguments
            if [ $# -ne 4 ]; then
                echo "Error: Invalid number of arguments"
                print_usage
                exit 1
            fi
            version1=$1
            channel1=$2
            version2=$3
            channel2=$4
            shift 4
            ;;
    esac
done

# Validate required arguments
if [ -z "${version1:-}" ] || [ -z "${channel1:-}" ] || [ -z "${version2:-}" ] || [ -z "${channel2:-}" ]; then
    echo "Error: Missing required arguments"
    print_usage
    exit 1
fi

# Set image paths
if [ -z "$FROM_IMAGE" ]; then
    fromimage="quay.io/rhoai/rhoai-fbc-fragment:rhoai-${version1}"
else
    fromimage="$FROM_IMAGE"
fi

if [ -z "$TO_IMAGE" ]; then
    toimage="quay.io/rhoai/rhoai-fbc-fragment:rhoai-${version2}"
else
    toimage="$TO_IMAGE"
fi

echo "Using source image: $fromimage"
echo "Using target image: $toimage"

declare -A scenarios=(
    ["serverless,rawdeployment"]="--serverless --authorino --servicemesh"
    ["serverless"]="--serverless --servicemesh"
    ["rawdeployment"]=""
)

# If no specific scenarios provided, run all
if [ ${#SCENARIOS_TO_RUN[@]} -eq 0 ]; then
    SCENARIOS_TO_RUN=("${!scenarios[@]}")
fi

# Validate scenarios
for scenario in "${SCENARIOS_TO_RUN[@]}"; do
    if [[ ! -v "scenarios[$scenario]" ]]; then
        echo "Error: Invalid scenario '$scenario'"
        echo "Available scenarios: ${!scenarios[*]}"
        exit 1
    fi
done

# Initialize status tracking
for scenario in "${!scenarios[@]}"; do
    scenario_status["$scenario"]="pending"
    pre_test_status["$scenario"]="pending"
    post_test_status["$scenario"]="pending"
done

# Pre-flight checks
check_dependencies

# Function to show progress bar
show_progress() {
    local duration=$1
    local message=$2
    local interval=1
    local elapsed=0
    
    echo -e "\n\033[1;36m${message}\033[0m"
    echo -n "["
    
    while [ $elapsed -lt $duration ]; do
        sleep $interval
        elapsed=$((elapsed + interval))
        local progress=$((elapsed * 50 / duration))
        local remaining=$((50 - progress))
        
        printf "%${progress}s" | tr " " "="
        printf "%${remaining}s" | tr " " "-"
        printf "] %d%%\r" $((elapsed * 100 / duration))
    done
    echo
}

# Function to check pod status
check_pod_status() {
    local namespace="redhat-ods-applications"
    local not_running_pods
    
    not_running_pods=$(oc get pods -n "$namespace" -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}' | grep -v Running)
    
    if [ -n "$not_running_pods" ]; then
        echo -e "\n\033[1;31m[WARNING] Found pods not in Running state:\033[0m"
        echo "$not_running_pods"
        return 1
    else
        echo -e "\n\033[1;32m[SUCCESS] All pods are in Running state\033[0m"
        return 0
    fi
}

# Process each scenario
for scenario in "${SCENARIOS_TO_RUN[@]}"; do
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

    # Cleanup before scenario (if not skipped)
    if [ "$SKIP_CLEANUP" = false ]; then
        echo -e "\n\033[1;33m[CLEANUP]\033[0m Preparing environment for scenario"
        run_cmd python main.py --cleanup
    else
        echo -e "\n\033[1;33m[SKIPPING CLEANUP]\033[0m Continuing with existing environment"
    fi

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

    # Verify deployment with progress bar
    echo -e "\n\033[1;33m[VERIFICATION]\033[0m Checking system status"
    show_progress $TOTAL_WAIT_TIME "Waiting for pods to stabilize..."
    check_pod_status || echo -e "\033[1;33m[WARNING] Some pods may not be ready, but continuing with tests...\033[0m"

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