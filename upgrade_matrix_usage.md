# RHOAI Upgrade Matrix Testing Tool

This tool helps test upgrade scenarios for Red Hat OpenShift AI (RHOAI) between different versions and channels. It performs pre-upgrade and post-upgrade tests to ensure a smooth upgrade process using the OpenDataHub test suite.

## Prerequisites

- OpenShift cluster access with appropriate permissions
- `oc` command-line tool (logged into the cluster)
- `uv` command-line tool for Python package management
- Python 3.8 or higher
- Git
- AWS credentials (for certain tests) - set as environment variables:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`

## Installation

The upgrade matrix tool is installed as part of the rhoshift package and provides two ways to run:

1. **Python CLI command** (recommended):
```bash
run-upgrade-matrix [options] <current_version> <current_channel> <new_version> <new_channel>
```

2. **Direct shell script**:
```bash
./scripts/run_upgrade_matrix.sh [options] <current_version> <current_channel> <new_version> <new_channel>
```

## Basic Usage

### Simple Upgrade Test
```bash
# Using Python CLI (recommended)
run-upgrade-matrix 2.10 stable 2.12 stable

# Using shell script directly
./scripts/run_upgrade_matrix.sh 2.10 stable 2.12 stable
```

### Example with specific scenarios
```bash
run-upgrade-matrix -s serverless -s rawdeployment 2.10 stable 2.12 stable
```

## Command Line Options

### Required Arguments (positional)
- `current_version`: The version to upgrade from (e.g., "2.10")
- `current_channel`: The channel of the current version (e.g., "stable", "fast")
- `new_version`: The version to upgrade to (e.g., "2.12")
- `new_channel`: The channel of the new version (e.g., "stable", "fast")

### Optional Arguments
- `-h, --help`: Show help message and exit
- `-s, --scenario SCENARIO`: Run specific scenario(s). Can be used multiple times.
  - Available scenarios: `serverless`, `rawdeployment`, `serverless,rawdeployment`
- `--skip-cleanup`: Skip cleanup before each scenario (useful for debugging)
- `--from-image IMAGE`: Custom source image path
  - Default: `quay.io/rhoai/rhoai-fbc-fragment:rhoai-{version}`
- `--to-image IMAGE`: Custom target image path
  - Default: `quay.io/rhoai/rhoai-fbc-fragment:rhoai-{version}`
- `-w, --wait-time SECONDS`: Wait time in seconds for pods to stabilize after upgrade
  - Default: 1200 (20 minutes)

## Available Test Scenarios

The tool supports three main scenarios that test different deployment configurations:

### 1. `rawdeployment`
- **Description**: Tests basic RHOAI deployment without additional operators
- **Configuration**: Raw serving enabled (`--raw=True`)
- **Operators**: None (baseline RHOAI only)
- **Use case**: Basic functionality testing

### 2. `serverless`
- **Description**: Tests RHOAI with serverless and service mesh capabilities
- **Configuration**: Raw serving disabled (`--raw=False`)
- **Operators**: Service Mesh, Serverless
- **rhoshift flags**: `--serverless --servicemesh`
- **Use case**: Serverless model serving scenarios

### 3. `serverless,rawdeployment`
- **Description**: Tests complete RHOAI stack with all supported operators
- **Configuration**: Raw serving disabled (`--raw=False`)
- **Operators**: Service Mesh, Authorino, Serverless
- **rhoshift flags**: `--serverless --authorino --servicemesh`
- **Use case**: Full-featured deployment testing

## Usage Examples

### Basic Examples
```bash
# Test all scenarios (default behavior)
run-upgrade-matrix 2.10 stable 2.12 stable

# Test specific scenario
run-upgrade-matrix -s serverless 2.10 stable 2.12 stable

# Test multiple specific scenarios
run-upgrade-matrix -s serverless -s rawdeployment 2.10 stable 2.12 stable
```

### Advanced Examples
```bash
# Custom wait time (30 minutes)
run-upgrade-matrix -w 1800 2.10 stable 2.12 stable

# Skip cleanup (useful for debugging)
run-upgrade-matrix --skip-cleanup 2.10 stable 2.12 stable

# Custom source image only
run-upgrade-matrix --from-image custom.registry/rhoai:1.5.0 2.10 stable 2.12 stable

# Both custom source and target images
run-upgrade-matrix \
  --from-image custom.registry/rhoai:1.5.0 \
  --to-image custom.registry/rhoai:1.6.0 \
  2.10 stable 2.12 stable

# Cross-channel upgrade with specific scenario
run-upgrade-matrix -s serverless,rawdeployment 2.10 fast 2.12 stable
```

## Test Process Flow

For each selected scenario, the tool executes the following phases:

### Phase 1: Pre-flight Checks
- Validates all required dependencies are installed
- Checks OpenShift cluster connection (`oc whoami`)
- Warns if AWS credentials are not set
- Validates scenario names and arguments

### Phase 2: Pre-upgrade Setup
- **Cleanup**: Removes existing RHOAI resources (unless `--skip-cleanup` is used)
- **Installation**: Installs the source version with scenario-specific operators
- **Test Repository**: Clones/updates OpenDataHub test repository to `/tmp/rhoshift-logs/opendatahub-tests`
- **Pre-upgrade Tests**: Runs comprehensive pre-upgrade test suite

### Phase 3: Upgrade Execution
- **Upgrade**: Installs the target version using the same configuration
- **Stabilization**: Waits for pods to stabilize (configurable wait time)
- **Verification**: Checks pod status in `redhat-ods-applications` namespace

### Phase 4: Post-upgrade Validation
- **Post-upgrade Tests**: Runs comprehensive post-upgrade test suite
- **Results**: Captures and parses test results
- **Logging**: Stores detailed logs for analysis

## Output and Logging

### Log Files Location
All logs are stored in `/tmp/rhoshift-logs/`:
- **Main log**: `/tmp/rhoshift.log` - General rhoshift operations
- **Upgrade matrix log**: `/tmp/rhoshift-logs/upgrade-matrix-YYYYMMDDHHMM.log` - Full execution log
- **Scenario logs**: `/tmp/rhoshift-logs/scenario-{scenario}-{timestamp}.log` - Per-scenario logs
- **Test logs**:
  - `/tmp/rhoshift-logs/pre-{scenario}-{timestamp}.log` - Pre-upgrade test results
  - `/tmp/rhoshift-logs/post-{scenario}-{timestamp}.log` - Post-upgrade test results
- **Command logs**: `/tmp/rhoshift-logs/command-{timestamp}.log` - Individual command outputs

### Console Output Features
- **Color-coded messages**: Green (INFO), Yellow (WARNING), Red (ERROR), Blue (DEBUG)
- **Progress indicators**: Shows progress during wait periods
- **Real-time status**: Live command execution output
- **Phase indicators**: Clear separation of test phases
- **Results summary**: Final status of all scenarios

### Test Results Format
Test results are parsed and displayed showing:
- **Pre-upgrade status**: passed/failed with test summary
- **Post-upgrade status**: passed/failed with test summary
- **Overall scenario status**: passed/failed based on both phases
- **Test details**: Number of tests passed/failed/skipped

## Error Handling and Recovery

### Failure Types
1. **Command Execution Failures**: Individual commands may fail but testing continues
2. **Test Phase Failures**: Pre or post-upgrade tests may fail
3. **Critical Failures**: Missing dependencies, cluster connection issues

### Recovery Strategies
- **Continue on test failures**: Other scenarios still execute
- **Log preservation**: All failure details saved to log files
- **Status tracking**: Each scenario tracked independently
- **Cleanup handling**: Resources cleaned between scenarios (unless skipped)

### Exit Codes
- **0**: All scenarios passed successfully
- **1**: One or more scenarios failed or critical error occurred

## Dependencies and Test Repository

### External Dependencies
The tool automatically manages the OpenDataHub test repository:
- **Repository**: https://github.com/opendatahub-io/opendatahub-tests.git
- **Location**: `/tmp/rhoshift-logs/opendatahub-tests`
- **Management**: Automatically cloned on first run, updated on subsequent runs

### Test Configuration
Tests are executed with the following configuration:
- **Test type**: `--pre-upgrade` or `--post-upgrade`
- **Deployment modes**: Matches the selected scenario
- **Distribution**: `downstream` (for RHOAI)
- **Dependent operators**: Automatically configured based on scenario

## Troubleshooting

### Common Issues and Solutions

#### AWS Credentials Missing
```bash
# Set environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"  # pragma: allowlist secret
```

#### Cluster Connection Issues
```bash
# Verify cluster connection
oc whoami
oc get nodes
```

#### Namespace Conflicts
```bash
# Manual cleanup if needed
rhoshift --cleanup
# Or use skip-cleanup to preserve state
run-upgrade-matrix --skip-cleanup ...
```

#### Test Failures
- Check detailed logs in `/tmp/rhoshift-logs/`
- Verify cluster has sufficient resources
- Ensure proper RBAC permissions
- Check network connectivity for image pulls

#### Script Not Found (Python CLI)
If `run-upgrade-matrix` command is not found:
```bash
# Verify installation
pip show rhoshift
# Or use direct script
./scripts/run_upgrade_matrix.sh [args]
```

### Debugging Tips
1. **Use skip-cleanup**: `--skip-cleanup` to preserve state between runs
2. **Check logs**: Start with the main upgrade matrix log file
3. **Single scenario**: Test one scenario at a time with `-s`
4. **Extended wait**: Increase wait time with `-w` for slower clusters
5. **Manual verification**: Check pod status manually with `oc get pods -n redhat-ods-applications`

## Development and Contributing

### Running in Development
```bash
# From project root
./scripts/run_upgrade_matrix.sh [args]

# Or via Python module
python -m rhoshift.rhoai_upgrade_matrix.cli [args]
```

### Adding New Scenarios
To add new scenarios, modify the `scenarios` array in `scripts/run_upgrade_matrix.sh`:
```bash
declare -A scenarios=(
    ["new-scenario"]="--new-operator --other-flags"
)
```

### Test Integration
The tool integrates with:
- **rhoshift CLI**: For operator installation and cleanup
- **OpenDataHub tests**: For comprehensive test coverage
- **uv/pytest**: For Python test execution
- **OpenShift**: For cluster operations and verification

## API Reference

### Python CLI Entry Point
```python
# Located in: rhoshift.rhoai_upgrade_matrix.cli:main
# Command: run-upgrade-matrix
```

### Shell Script Location
```bash
# Package resource: rhoshift/scripts/run_upgrade_matrix.sh
# Development: scripts/run_upgrade_matrix.sh
```

This documentation reflects the current implementation as of the latest version. For the most up-to-date information, refer to the help output:
```bash
run-upgrade-matrix --help
```
