# OpenShift Operator Installation Tool

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![OpenShift Compatible](https://img.shields.io/badge/OpenShift-4.x-lightgrey.svg)

A Python CLI tool for installing and managing OpenShift operators with parallel installation support.

## 📋 Table of Contents
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
  - [Basic Usage](#basic-usage)
  - [Upgrade Matrix](#upgrade-matrix)
  - [Advanced Options](#advanced-options)
- [How It Works](#-how-it-works)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## ✨ Features
- Install single or multiple OpenShift operators
- Parallel installation for faster deployments
- Configurable timeouts and retries
- Detailed logging to `test.log`
- Upgrade matrix testing for operator upgrades
- Supports:
  - Serverless Operator
  - Service Mesh Operator  
  - Authorino Operator

## 📂 Project Structure
```
O
.
├── cli/
│   ├── args.py            # Command line argument parsing
│   └── commands.py        # CLI command implementations
├── logger/
│   └── logger.py          # Logging configuration
├── utils/
│   ├── operator/
│   │   └── operator.py    # Core operator logic
│   ├── upgrade/
│   │   ├── matrix.py      # Upgrade matrix functionality
│   │   └── run_upgrade_matrix.sh  # Upgrade matrix shell script
│   └── utils.py           # Utility functions
├── main.py                # CLI entry point
├── README.md              # This document
└── test.log               # Generated log file
```

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/mwaykole/O.git
cd O
```
2. Install dependencies:
```
pip install -e .    
```
3. Verify installation:
```
python main.py --help
```

## 💻 Usage

### Basic Usage
```bash
# Install single operator
python main.py --serverless

# Install multiple operators
python main.py --serverless --servicemesh

# Install kserve raw config
python main.py --rhoai --rhoai-channel=<channel> --rhoai-image=<image> --raw=True

# Install kserve Serverles config
python main.py --rhoai --rhoai-channel=<channel> --rhoai-image=<image> --raw=False --all

# Install all operators 
python main.py --all

# create dsc and dsci with rhoai operator installarion
python main.py --rhoai --rhoai-channel=<channel> --rhoai-image=<image> --raw=False --deploy-rhoai-resources

# Verbose output
python main.py --all --verbose
```

### Upgrade Matrix
The upgrade matrix feature allows you to test operator upgrades between different versions and channels.

```bash
# Basic upgrade matrix test
python main.py --run-matrix 2.20 stable 2.19 fast

# Run specific scenarios
python main.py --run-matrix 2.20 stable 2.19 fast --scenario serverless --scenario rawdeployment

# Skip cleanup between scenarios
python main.py --run-matrix 2.20 stable 2.19 fast --skip-cleanup

# Use custom images
python main.py --run-matrix 2.20 stable 2.19 fast \
    --from-image custom.registry/rhoai:1.5.0 \
    --to-image custom.registry/rhoai:1.6.0
```

Available scenarios:
- `serverless`: Test upgrade with serverless configuration
- `rawdeployment`: Test upgrade with raw deployment configuration
- `serverless,rawdeployment`: Test both configurations

The upgrade matrix will:
1. Install the source version
2. Run pre-upgrade tests
3. Perform the upgrade
4. Run post-upgrade tests
5. Generate detailed logs in the `logs` directory

### Advanced Options
```bash
# Custom oc binary path
python main.py --serverless --oc-binary /path/to/oc

# Custom timeout (seconds)
python main.py --all --timeout 900

# View logs
tail -f test.log
```

## 🔍 How It Works
The upgrade matrix functionality:
1. Validates the configuration and required files
2. Executes the upgrade matrix script with specified parameters
3. Provides live output during execution
4. Handles errors and retries automatically
5. Generates detailed logs for analysis

## 🛠️ Development
To contribute to the project:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 🐛 Troubleshooting
Common issues and solutions:
- If the upgrade matrix fails, check the logs in the `logs` directory
- Ensure you have the correct permissions for the upgrade script
- Verify that the specified versions and channels are valid

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
