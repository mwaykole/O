# OpenDataHub Upgrade Matrix Script

This script automates the testing of OpenDataHub upgrades across different deployment scenarios. It performs pre-upgrade and post-upgrade tests to ensure a smooth upgrade process.

## Prerequisites

Before running the script, ensure you have the following dependencies installed:

- OpenShift CLI (`oc`)
- Python 3.x
- Git
- UV (Python package manager)

You must also be logged into an OpenShift cluster:
```bash
oc login <your-cluster-url>
```

## AWS Credentials

Some tests require AWS credentials. You can provide them in two ways:

1. Environment variables:
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

2. Command line arguments (passed automatically by the script)

## Usage

```bash
./run_upgrade_matrix.sh [options] <current_version> <current_channel> <new_version> <new_channel>
```

### Arguments

- `current_version`: The version currently installed (e.g., "1.5.0")
- `current_channel`: The channel of the current version (e.g., "stable")
- `new_version`: The version to upgrade to (e.g., "1.6.0")
- `new_channel`: The channel of the new version (e.g., "stable")

### Options

- `-h, --help`: Display help message and exit
- `-s, --scenario SCENARIO`: Specify which scenarios to run (can be used multiple times)
- `--skip-cleanup`: Skip cleanup before each scenario

### Available Scenarios

1. `serverless`: Tests serverless deployment with service mesh
2. `rawdeployment`: Tests raw deployment without additional components
3. `serverless,rawdeployment`: Tests both serverless and raw deployment with all components

## Examples

1. Run all scenarios:
```bash
./run_upgrade_matrix.sh 1.5.0 stable 1.6.0 stable
```

2. Run specific scenarios:
```bash
./run_upgrade_matrix.sh -s serverless -s rawdeployment 1.5.0 stable 1.6.0 stable
```

3. Skip cleanup:
```bash
./run_upgrade_matrix.sh --skip-cleanup 1.5.0 stable 1.6.0 stable
```

4. Combine options:
```bash
./run_upgrade_matrix.sh -s serverless --skip-cleanup 1.5.0 stable 1.6.0 stable
```

## Test Process

The script performs the following steps for each scenario:

1. **Pre-flight Checks**
   - Verifies all dependencies are installed
   - Checks OpenShift cluster connection

2. **Pre-upgrade Phase**
   - Cleans up existing resources (unless --skip-cleanup is used)
   - Installs the current version
   - Runs pre-upgrade tests

3. **Upgrade Phase**
   - Performs the upgrade to the new version
   - Verifies deployment status

4. **Post-upgrade Phase**
   - Runs post-upgrade tests
   - Validates system functionality

## Test Results

Test results are stored in the `logs` directory with timestamps:
- Pre-upgrade logs: `logs/pre-<scenario>-<timestamp>.log`
- Post-upgrade logs: `logs/post-<scenario>-<timestamp>.log`

The script provides a summary of test results at the end of execution, showing:
- Pre-upgrade test status
- Post-upgrade test status
- Overall scenario status

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

