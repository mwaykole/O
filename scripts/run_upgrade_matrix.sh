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
# Default wait time of 20 minutes (1200 seconds)
TOTAL_WAIT_TIME=1200
FROM_IMAGE=""
TO_IMAGE=""

# Log directory setup
LOG_DIR="/tmp/rhoshift-logs"
MAIN_LOG="/tmp/rhoshift.log"
TEST_DIR="${LOG_DIR}/opendatahub-tests"
mkdir -p "$LOG_DIR"

# Set up logging
exec 1> >(tee -a "${LOG_DIR}/upgrade-matrix-$(date +%Y%m%d%H%M).log")
exec 2>&1

# Logging function
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_entry="[${timestamp}] [${level}] $message"
    
    # Write to main log file
    echo "$log_entry" >> "$MAIN_LOG"
    
    # Also display on console with colors
    case $level in
        "INFO")
            echo -e "\033[1;32m${log_entry}\033[0m"
            ;;
        "WARNING")
            echo -e "\033[1;33m${log_entry}\033[0m"
            ;;
        "ERROR")
            echo -e "\033[1;31m${log_entry}\033[0m"
            ;;
        "DEBUG")
            echo -e "\033[1;34m${log_entry}\033[0m"
            ;;
        *)
            echo -e "\033[1;37m${log_entry}\033[0m"
            ;;
    esac
}

# Global variables for tracking test results
declare -A test_results
declare -A scenario_status
declare -A pre_test_status
declare -A post_test_status

# Check for required environment variables
if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    log "WARNING" "AWS credentials not set. Some tests may fail."
    log "WARNING" "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
fi

# Function to print and execute commands
run_cmd() {
    log "INFO" "Executing command: $*"
    "$@" 2>&1 | tee -a "${LOG_DIR}/command-$(date +%Y%m%d%H%M).log"
    local status=$?
    if [ $status -ne 0 ]; then
        log "ERROR" "Command failed with status $status: $*"
        return $status
    fi
    log "DEBUG" "Command completed successfully: $*"
    return 0
}

# Error handling
error_exit() {
    log "ERROR" "$1"
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

# Function to clone or update test repository
setup_test_repo() {
    if [ -d "$TEST_DIR" ]; then
        log "INFO" "Updating existing test repository in $TEST_DIR"
        cd "$TEST_DIR" || error_exit "Failed to change to test directory: $TEST_DIR"
        run_cmd git pull --quiet
        cd - > /dev/null || error_exit "Failed to return to previous directory"
    else
        log "INFO" "Cloning test repository to $TEST_DIR"
        run_cmd git clone --quiet "$TEST_REPO" "$TEST_DIR"
    fi
}

# Function to run tests with output
run_tests() {
    local test_type=$1
    local scenario=$2
    local log_file=$3

    log "INFO" "Running ${test_type}-upgrade tests for ${scenario}"
    case "$scenario" in
        "rawdeployment")
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

    # Run tests and capture output
    log "INFO" "Running ${test_type}-upgrade tests for ${scenario}"
    log "DEBUG" "Changing to test directory: $TEST_DIR"
    cd "$TEST_DIR" || error_exit "Failed to change to test directory: $TEST_DIR"
    
    if uv run pytest "--${test_type}-upgrade"  --upgrade-deployment-modes="${scenario}" \
          --tc=dependent_operators:"${dependent_operators}" --tc=distribution:downstream  \
         2>&1 | tee -a "$log_file"; then
        parse_test_results "$log_file" "$scenario" "$test_type"
        cd - > /dev/null || error_exit "Failed to return to previous directory"
        return 0
    else
        parse_test_results "$log_file" "$scenario" "$test_type"
        log "WARNING" "Tests failed for ${test_type}-upgrade in scenario ${scenario}"
        log "WARNING" "See detailed results in: $log_file"
        cd - > /dev/null || error_exit "Failed to return to previous directory"
        return 1
    fi
}

# Print final test results
print_final_results() {
    log "INFO" "==================== FINAL TEST RESULTS ===================="

    local all_passed=true

    for scenario in "${!scenarios[@]}"; do
        log "INFO" "SCENARIO: ${scenario}"
        log "INFO" "  PRE-UPGRADE:  ${pre_test_status[$scenario]} - ${test_results["${scenario}_pre"]}"
        log "INFO" "  POST-UPGRADE: ${post_test_status[$scenario]} - ${test_results["${scenario}_post"]}"
        log "INFO" "  OVERALL:      ${scenario_status[$scenario]}"

        if [[ "${scenario_status[$scenario]}" != "passed" ]]; then
            all_passed=false
        fi
    done

    log "INFO" "============================================================="

    if $all_passed; then
        log "INFO" "[SUCCESS] All upgrade scenarios completed successfully"
        return 0
    else
        log "ERROR" "[FAILURE] Some scenarios failed. See details above."
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
    echo "  -w, --wait-time SECONDS   Set the wait time in seconds (default: 1200) after upgrade"
    echo ""
    echo "Example:"
    echo "  $0 -s serverless -s rawdeployment 2.10 stable 2.12 stable"
    echo "  $0 --skip-cleanup 2.10 stable 2.12 stable"
    echo "  $0 --from-image custom.registry/rhoai:1.5.0 --to-image custom.registry/rhoai:1.6.0 2.10 stable 2.12 stable"
    echo "  $0 -w 1800 2.10 stable 2.12 stable"
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
        -w|--wait-time)
            TOTAL_WAIT_TIME="$2"
            shift 2
            ;;
        *)
            # If it's not an option, it must be the version/channel arguments
            if [ -z "${version1:-}" ]; then
                version1=$1
                channel1=$2
                version2=$3
                channel2=$4
                shift 4
            else
                echo "Error: Invalid number of arguments"
                print_usage
                exit 1
            fi
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

log "INFO" "Using source image: $fromimage"
log "INFO" "Using target image: $toimage"

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
    local interval=10
    local elapsed=0
    
    log "INFO" "$message"
    
    while [ $elapsed -lt $duration ]; do
        sleep $interval
        elapsed=$((elapsed + interval))
        local percentage=$((elapsed * 100 / duration))
        log "DEBUG" "Progress: [${percentage}%] completed ${elapsed} seconds of ${duration} seconds"
    done
}

# Function to check pod status
check_pod_status() {
    local namespace="redhat-ods-applications"
    local not_running_pods
    
    not_running_pods=$(oc get pods -n "$namespace" -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}' | grep -v Running)
    
    if [ -n "$not_running_pods" ]; then
        log "WARNING" "Found pods not in Running state:"
        log "WARNING" "$not_running_pods"
        return 1
    else
        log "INFO" "All pods are in Running state"
        return 0
    fi
}

# Process each scenario
for scenario in "${SCENARIOS_TO_RUN[@]}"; do
    log "INFO" "==================== [SCENARIO: ${scenario^^}] ===================="
    timestamp=$(date +%Y%m%d%H%M)
    pre_log="${LOG_DIR}/pre-${scenario}-${timestamp}.log"
    post_log="${LOG_DIR}/post-${scenario}-${timestamp}.log"
    scenario_log="${LOG_DIR}/scenario-${scenario}-${timestamp}.log"

    # Start logging scenario execution
    exec 1> >(tee -a "$scenario_log")
    exec 2>&1

    # Set parameters
    if [ "$scenario" == "rawdeployment" ]; then
        raw="True"
    else
        raw="False"
    fi

    # Cleanup before scenario (if not skipped)
    if [ "$SKIP_CLEANUP" = false ]; then
        log "INFO" "Preparing environment for scenario"
        run_cmd rhoshift --cleanup
    else
        log "WARNING" "Skipping cleanup - continuing with existing environment"
    fi

    # PRE-UPGRADE PHASE
    log "INFO" "[PHASE 1] PRE-UPGRADE INSTALLATION"
    log "INFO" "Installing version: $version1 with options: ${scenarios[$scenario]}"
    # shellcheck disable=SC2086
    run_cmd rhoshift ${scenarios[$scenario]} \
        --rhoai \
        --rhoai-channel="$channel1" \
        --rhoai-image="$fromimage" \
        --raw="$raw" \
        --deploy-rhoai-resources

    # Setup test repository
    setup_test_repo

    # PRE-UPGRADE TESTS
    run_tests "pre" "$scenario" "$pre_log"

    # UPGRADE PHASE
    log "INFO" "[PHASE 2] UPGRADE EXECUTION"
    log "INFO" "Upgrading to version: $version2"
    run_cmd rhoshift --rhoai \
        --rhoai-channel="$channel2" \
        --rhoai-image="$toimage" \
        --raw="$raw"

    # Verify deployment with progress bar
    log "INFO" "[VERIFICATION] Checking system status"
    show_progress $TOTAL_WAIT_TIME "Waiting for pods to stabilize..."
    check_pod_status || log "WARNING" "Some pods may not be ready, but continuing with tests..."

    # POST-UPGRADE TESTS
    log "INFO" "[PHASE 3] POST-UPGRADE VALIDATION"
    run_tests "post" "$scenario" "$post_log"

    log "INFO" "==================== [SCENARIO COMPLETE] ===================="
    
    # Restore original stdout/stderr
    exec 1>&3
    exec 2>&4
done

# Print final results
print_final_results
exit $?