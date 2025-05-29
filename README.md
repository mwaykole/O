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
  - RHOAI Operator

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

## 💻 Usage

### Basic Commands

```bash
# Install single operator
rhoshift --serverless

# Install multiple operators
rhoshift --serverless --servicemesh

# Install RHOAI with raw configuration
rhoshift --rhoai --rhoai-channel=<channel> --rhoai-image=<image> --raw=True

# Install RHOAI with Serverless configuration
rhoshift --rhoai --rhoai-channel=<channel> --rhoai-image=<image> --raw=False --all

# Install all operators
rhoshift --all

# Create DSC and DSCI with RHOAI operator installation
rhoshift --rhoai --deploy-rhoai-resources

# Clean up all operators
rhoshift --cleanup
```

### Advanced Options

```bash
# Custom oc binary path
rhoshift --serverless --oc-binary /path/to/oc

# Custom timeout (seconds)
rhoshift --all --timeout 900

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