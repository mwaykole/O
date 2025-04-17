# OpenShift Operator Installation Tool

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![OpenShift Compatible](https://img.shields.io/badge/OpenShift-4.x-lightgrey.svg)

A Python CLI tool for installing and managing OpenShift operators with parallel installation support.

## 📋 Table of Contents
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [How It Works](#-how-it-works)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## ✨ Features
- Install single or multiple OpenShift operators
- Parallel installation for faster deployments
- Configurable timeouts and retries
- Detailed logging to `test.log`
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
💻 Usage
```

```
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
# Advanced Options

```
# Custom oc binary path
python main.py --serverless --oc-binary /path/to/oc

# Custom timeout (seconds)
python main.py --all --timeout 900

# View logs
tail -f test.log

```

