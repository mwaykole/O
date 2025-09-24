# RHOAI Tool Kit

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![OpenShift Compatible](https://img.shields.io/badge/OpenShift-4.x-lightgrey.svg)

A comprehensive toolkit for managing and upgrading Red Hat OpenShift AI (RHOAI) installations with parallel installation support.

## 📋 Table of Contents
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [Logging](#-logging)
- [Configuration](#-configuration)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## ✨ Features
- Install single or multiple OpenShift operators
- Parallel installation for faster deployments
- Configurable timeouts and retries
- Comprehensive logging system
- Supports:
  - Serverless Operator
  - Service Mesh Operator
  - Authorino Operator
  - cert-manager Operator (Kueue dependency)
  - RHOAI Operator
  - Kueue Operator **with DSC Integration**
  - KEDA (Custom Metrics Autoscaler) Operator
- **Automatic Dependency Resolution**: Installs required operators in correct order
- **Smart Validation**: Pre-installation compatibility and conflict detection
- **🆕 Kueue DSC Integration**: Automatically updates RHOAI DataScienceCluster with Kueue management state

## 📁 Project Structure

```
rhoshift/
├── rhoshift/              # Main package directory
│   ├── __init__.py
│   ├── main.py           # CLI entry point
│   ├── cli/              # Command-line interface
│   │   ├── __init__.py
│   │   ├── args.py      # Argument parsing
│   │   └── commands.py  # Command implementations
│   ├── logger/          # Logging utilities
│   │   ├── __init__.py
│   │   └── logger.py    # Logging configuration
│   └── utils/           # Core utilities
│       ├── __init__.py
│       ├── constants.py # Constants and configurations
│       ├── operator.py  # Operator management
│       └── utils.py     # Utility functions
├── run_upgrade_matrix.sh  # Upgrade matrix execution script
├── upgrade_matrix_usage.md # Upgrade matrix documentation
├── pyproject.toml        # Project dependencies and configuration
└── README.md            # This document
```

## 📋 Components

### Core Components
- **CLI**: Command-line interface for operator management
- **Logger**: Logging configuration and utilities (logs to `/tmp/rhoshift.log`)
- **Utils**: Core utilities and operator management logic

### RHOAI Components
- **RHOAI Upgrade Matrix**: Utilities for testing RHOAI upgrades
- **Upgrade Matrix Scripts**: Execution and documentation for upgrade testing

### Maintenance Scripts
- **Cleanup Scripts**: Utilities for cleaning up operator installations
- **Worker Node Scripts**: Utilities for managing worker node configurations

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/mwaykole/O.git
cd O
```

2. Install dependencies:
```bash
pip install -e .
```

3. Verify installation:
```bash
rhoshift --help
```

### 🔧 New CLI Options

```bash
rhoshift --help
usage: rhoshift [-h] [--serverless] [--servicemesh] [--authorino] [--cert-manager]
                [--rhoai] [--kueue [{Managed,Unmanaged}]] [--keda] [--all] [--cleanup]
                [--deploy-rhoai-resources] [--summary] [--oc-binary OC_BINARY]
                [--retries RETRIES] [--retry-delay RETRY_DELAY] [--timeout TIMEOUT]
                [--rhoai-channel RHOAI_CHANNEL] [--raw RAW] [--rhoai-image RHOAI_IMAGE]

Operator Selection:
  --serverless          Install OpenShift Serverless Operator
  --servicemesh         Install Service Mesh Operator
  --authorino           Install Authorino Operator
  --cert-manager        Install cert-manager Operator (latest v1.16.1)
  --rhoai               Install RHOAI Operator
  --kueue [{Managed,Unmanaged}]  Install Kueue Operator with DSC managementState (default: Unmanaged)
  --keda                Install KEDA (Custom Metrics Autoscaler) Operator
  --all                 Install all operators
  --cleanup             Clean up all RHOAI, serverless, servicemesh, Authorino operators
  --deploy-rhoai-resources      Create DSC and DSCI with RHOAI installation
  --summary             Show detailed summary of all supported operators and versions
```

## 💻 Usage

### Basic Commands

```bash
# Install single operator
rhoshift --serverless

# Install multiple operators
rhoshift --serverless --servicemesh

# Install cert-manager operator
rhoshift --cert-manager

# Install Kueue operator with default managementState (Unmanaged)
# Automatically installs cert-manager dependency
rhoshift --kueue

# Install Kueue operator with specific managementState in DSC
rhoshift --kueue Managed     # Sets Kueue as Managed in DSC
rhoshift --kueue Unmanaged   # Sets Kueue as Unmanaged in DSC

# Install KEDA (Custom Metrics Autoscaler) operator
rhoshift --keda

# Install RHOAI with raw configuration
rhoshift --rhoai --rhoai-channel=<channel> --rhoai-image=<image> --raw=True

# Install RHOAI with Serverless configuration
rhoshift --rhoai --rhoai-channel=<channel> --rhoai-image=<image> --raw=False --all

# Install all operators (Kueue will be set to Unmanaged in DSC)
rhoshift --all

# Create DSC and DSCI with RHOAI operator installation
rhoshift --rhoai --deploy-rhoai-resources

# Clean up all operators
rhoshift --cleanup
```

### 🔗 Operator Dependencies & Validation

The tool automatically handles operator dependencies and provides smart validation:

#### **Automatic Dependency Resolution**
- **Kueue** requires **cert-manager**: Installing Kueue automatically includes cert-manager
- Dependencies are installed in the correct order to prevent failures
- Missing dependencies are automatically detected and added

```bash
# This command will install BOTH cert-manager AND Kueue (in correct order)
# Kueue will be set to Unmanaged in DSC (if DSC exists)
rhoshift --kueue

# You'll see output like:
# 📦 Auto-adding dependency: cert-manager
# Installing 2 operators in order: cert-manager → kueue
# 🔄 Updating DSC with Kueue managementState: Unmanaged
# ✅ Successfully updated DSC with Kueue managementState: Unmanaged
```

#### **Smart Validation**
- **Compatibility Checking**: Warns about potential operator conflicts
- **Namespace Validation**: Detects if operators conflict in shared namespaces
- **Pre-Installation Validation**: Catches issues before installation starts

```bash
# Example validation warnings:
# ⚠️  Note: Kueue and KEDA may have resource conflicts. Monitor for admission webhook issues.
# ⚠️  Installation order will be adjusted for dependencies: cert-manager → kueue
```

#### **Supported Dependencies**
| Primary Operator | Required Dependencies |
|-----------------|----------------------|
| Kueue           | cert-manager         |

> **Note**: When installing Kueue individually (`--kueue`), you will see dependency warnings. For automatic dependency installation, use batch mode (`--cert-manager --kueue`) or install dependencies manually first.

### 🎯 Kueue DSC Integration

**New Feature**: Kueue operator installation now automatically updates the RHOAI DataScienceCluster (DSC) when a management state is specified.

#### **Kueue Management States**
- **`Managed`**: RHOAI controls Kueue configuration and lifecycle
- **`Unmanaged`**: Kueue runs independently, not managed by RHOAI

#### **Usage Examples**

```bash
# Install Kueue as Managed (RHOAI controls it)
rhoshift --kueue Managed

# Install Kueue as Unmanaged (independent operation) - DEFAULT
rhoshift --kueue Unmanaged
rhoshift --kueue  # Same as above

# Switch between states (updates existing DSC)
rhoshift --kueue Managed    # Change to Managed
rhoshift --kueue Unmanaged  # Change back to Unmanaged
```

#### **Behavior**
- **DSC Exists**: Automatically updates Kueue managementState in existing DSC
- **No DSC**: Shows info message that state will be applied when DSC is created
- **Error Handling**: Graceful warnings if DSC update fails

#### **Output Examples**
```bash
# When DSC exists and gets updated:
🔄 Updating DSC with Kueue managementState: Unmanaged
✅ Successfully updated DSC with Kueue managementState: Unmanaged

# When no DSC exists:
ℹ️  No existing DSC found. Kueue managementState will be applied when DSC is created.
```

### Advanced Options

```bash
# Custom oc binary path
rhoshift --serverless --oc-binary /path/to/oc

# Custom timeout (seconds)
rhoshift --all --timeout 900

# Install queue management and auto-scaling operators together
# (cert-manager will be automatically installed as Kueue dependency)
rhoshift --kueue Managed --keda

# Install complete ML/AI stack with queue management
rhoshift --rhoai --kueue Managed --keda --rhoai-channel=stable --rhoai-image=quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.25-nightly

# Show summary of all supported operators and their versions
rhoshift --summary

# Install only cert-manager for other uses
rhoshift --cert-manager

# Verbose output
rhoshift --all --verbose
```

### Upgrade Matrix Testing

To run the upgrade matrix tests, you can use either method:

1. Using the shell script:
```bash
./run_upgrade_matrix.sh [options] <current_version> <current_channel> <new_version> <new_channel>
```

2. Using the Python command:
```bash
run-upgrade-matrix [options] <current_version> <current_channel> <new_version> <new_channel>
```

Options:
- `-s, --scenario`: Run specific scenario(s) (serverless, rawdeployment, serverless,rawdeployment)
- `--skip-cleanup`: Skip cleanup before each scenario
- `--from-image`: Custom source image path
- `--to-image`: Custom target image path

Example:
```bash
# Using shell script
./run_upgrade_matrix.sh -s serverless -s rawdeployment 2.10 stable 2.12 stable

# Using Python command
run-upgrade-matrix -s serverless -s rawdeployment 2.10 stable 2.12 stable
```

## 📝 Logging

The toolkit uses a comprehensive logging system:
- Logs are stored in `/tmp/rhoshift.log`
- Console output shows INFO level and above
- File logging captures DEBUG level and above
- Automatic log rotation (10MB max size, 5 backup files)
- Colored output in supported terminals

To view logs:
```bash
tail -f /tmp/rhoshift.log
```

## 🔧 Configuration

### Environment Variables
- `LOG_FILE_LEVEL`: Set file logging level (default: DEBUG)
- `LOG_CONSOLE_LEVEL`: Set console logging level (default: INFO)

### Command Options
- `--oc-binary`: Path to oc CLI (default: oc)
- `--retries`: Max retry attempts (default: 3)
- `--retry-delay`: Delay between retries in seconds (default: 10)
- `--timeout`: Command timeout in seconds (default: 300)

## 🛠️ Development

### Prerequisites
- Python 3.8 or higher
- OpenShift CLI (oc)
- Access to an OpenShift cluster

### Running Tests
```bash
pytest tests/
```

## 🔍 Troubleshooting

### Common Issues
1. **Operator Installation Fails**
   - Check cluster access: `oc whoami`
   - Verify operator catalog: `oc get catalogsource`
   - Check logs: `tail -f /tmp/rhoshift.log`

2. **Permission Issues**
   - Ensure you have cluster-admin privileges
   - Check namespace permissions

3. **Timeout Errors**
   - Increase timeout: `--timeout 900`
   - Check cluster resources

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 