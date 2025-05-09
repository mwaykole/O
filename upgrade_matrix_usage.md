# OpenDataHub Upgrade Matrix Testing Tool

This tool helps test upgrade scenarios for OpenDataHub between different versions and channels. It performs pre-upgrade and post-upgrade tests to ensure a smooth upgrade process.

## Prerequisites

- OpenShift cluster access
- `oc` command-line tool
- `uv` command-line tool
- Python 3.8 or higher
- Git
- AWS credentials (for certain tests)
- UV 

## Basic Usage

```bash
./run_upgrade_matrix.sh <current_version> <current_channel> <new_version> <new_channel>
```

### Example
```bash
./run_upgrade_matrix.sh 2.10 stable 2.12 stable
```

## Command Line Options

### Required Arguments
- `current_version`: The version to upgrade from (e.g., "2.10")
- `current_channel`: The channel of the current version (e.g., "stable")
- `new_version`: The version to upgrade to (e.g., "2.12")
- `new_channel`: The channel of the new version (e.g., "stable")

### Optional Arguments
- `-s, --scenario SCENARIO`: Run specific scenario(s). Can be used multiple times.
  - Available scenarios: `serverless`, `rawdeployment`, `serverless,rawdeployment`
- `--skip-cleanup`: Skip cleanup before each scenario
- `--from-image IMAGE`: Custom source image path
  - Default: `quay.io/rhoai/rhoai-fbc-fragment:rhoai-{version}`
- `--to-image IMAGE`: Custom target image path
  - Default: `quay.io/rhoai/rhoai-fbc-fragment:rhoai-{version}`

## Available Scenarios

1. `serverless`: Tests serverless deployment with service mesh
   - Includes Service Mesh Operator
   - Includes Serverless Operator
   - Uses `--serverless --servicemesh` flags

2. `rawdeployment`: Tests raw deployment without additional components
   - Basic deployment testing
   - No additional operators
   - No additional flags

3. `serverless,rawdeployment`: Tests both serverless and raw deployment with all components
   - Includes Service Mesh Operator
   - Includes Authorino Operator
   - Includes Serverless Operator
   - Uses `--serverless --authorino --servicemesh` flags

## Examples

### Basic Upgrade Test
```bash
./run_upgrade_matrix.sh 2.10 stable 2.12 stable
```

### Test Specific Scenario
```bash
./run_upgrade_matrix.sh -s serverless 2.10 stable 2.12 stable
```

### Test Multiple Scenarios
```bash
./run_upgrade_matrix.sh -s serverless -s rawdeployment 2.10 stable 2.12 stable
```

### Skip Cleanup
```bash
./run_upgrade_matrix.sh --skip-cleanup 2.10 stable 2.12 stable
```

### Use Custom Images
```bash
# Custom source image only
./run_upgrade_matrix.sh --from-image custom.registry/rhoai:1.5.0 2.10 stable 2.12 stable

# Both custom source and target images
./run_upgrade_matrix.sh --from-image custom.registry/rhoai:1.5.0 --to-image custom.registry/rhoai:1.6.0 2.10 stable 2.12 stable
```

## Test Process

The script performs the following steps for each scenario:

1. **Pre-flight Checks**
   - Verifies all dependencies are installed
   - Checks OpenShift cluster connection
   - Validates AWS credentials

2. **Pre-upgrade Phase**
   - Cleans up existing resources (unless --skip-cleanup is used)
   - Installs the current version
   - Runs pre-upgrade tests
   - Records test results

3. **Upgrade Phase**
   - Performs the upgrade to the new version
   - Waits for pods to stabilize (5 minutes)
   - Verifies pod status

4. **Post-upgrade Phase**
   - Runs post-upgrade tests
   - Verifies system functionality
   - Records test results

## Output and Logging

The script provides detailed output including:
- Command execution status with color-coded messages
- Progress bars for waiting periods
- Pod status information
- Test results for each phase
- Final summary of all scenarios
The script provides a summary of test results at the end of execution, showing:
- Pre-upgrade test status
- Post-upgrade test status
- Overall scenario status
### Log Files
Logs are stored in the `logs` directory with timestamps:
- Pre-upgrade logs: `logs/pre-{scenario}-{timestamp}.log`
- Post-upgrade logs: `logs/post-{scenario}-{timestamp}.log`

## Error Handling

The script includes comprehensive error handling:
- Validates all inputs before starting
- Checks for required dependencies
- Verifies scenario names
- Provides clear error messages
- Maintains test results even if some scenarios fail

## Cleanup

By default, the script performs cleanup before each scenario to ensure a clean test environment. You can skip cleanup using the `--skip-cleanup` option, which is useful for:
- Debugging failed tests
- Continuing from a previous run
- Testing in an existing environment

## Dependencies

The script requires the following repositories:
- OpenDataHub Tests: https://github.com/opendatahub-io/opendatahub-tests.git

## Troubleshooting

Common issues and solutions:

1. **AWS Credentials Missing**
   - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables
   - Or provide them via command line arguments

2. **Namespace Conflicts**
   - Use the cleanup option to remove existing resources
   - Or manually delete conflicting resources

3. **Test Failures**
   - Check the logs in the `logs` directory
   - Verify all dependencies are installed
   - Ensure you have proper cluster permissions

## Contributing

To contribute to this script:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Test Failure Handling

The script handles test failures in several ways:

1. **Command Execution Failures**
   - If a command fails, the script will:
     - Display a red "[FAILED]" message with the exit status
     - Continue with the next step
     - Record the failure in the test results

2. **Test Phase Failures**
   - For each test phase (pre-upgrade and post-upgrade):
     - Test results are parsed from the log file
     - Failures are recorded in the test status arrays
     - The script continues to the next phase
     - Detailed results are stored in log files

3. **Scenario Status Tracking**
   - Each scenario's status is tracked separately:
     - Pre-upgrade status
     - Post-upgrade status
     - Overall scenario status
   - A scenario is marked as failed if:
     - Pre-upgrade tests fail
     - Post-upgrade tests fail
     - No test results are found

4. **Final Results**
   - At the end of execution, the script:
     - Displays a summary of all scenarios
     - Shows status for each phase
     - Indicates overall success/failure
     - Returns appropriate exit code (0 for success, 1 for failure)

5. **Log Files**
   - Failed test details are preserved in log files:
     - `logs/pre-{scenario}-{timestamp}.log`
     - `logs/post-{scenario}-{timestamp}.log`
   - These logs contain:
     - Test output
     - Error messages
     - Stack traces
     - Test summary

6. **Error Recovery**
   - The script continues running even if some tests fail
   - All scenarios are attempted unless a critical error occurs
   - Results are preserved for analysis
   - Cleanup is performed unless `--skip-cleanup` is used

