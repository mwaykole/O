# RHOShift - OpenShift Operator Installation Toolkit

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![OpenShift Compatible](https://img.shields.io/badge/OpenShift-4.x-lightgrey.svg)
![Stability Level](https://img.shields.io/badge/stability-enhanced-brightgreen.svg)

A comprehensive, enterprise-grade toolkit for managing OpenShift operators with enhanced stability features, automatic dependency resolution, and Red Hat OpenShift AI (RHOAI) integration.

## 📋 Table of Contents
- [Features](#-features)
- [Enhanced Stability Features](#-enhanced-stability-features)
- [Supported Operators](#-supported-operators)
- [Installation](#-installation)
- [Usage](#-usage)
- [Advanced Usage](#-advanced-usage)
- [Dependency Management](#-dependency-management)
- [RHOAI Integration](#-rhoai-integration)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## ✨ Features

### 🚀 **Core Functionality**
- **6 Enterprise Operators**: Complete operator stack for modern OpenShift deployments
- **Enhanced Stability System**: 3-tier stability levels with comprehensive error handling
- **Automatic Dependency Resolution**: Smart installation order with dependency detection
- **Pre-flight Validation**: Cluster readiness and permission verification
- **Health Monitoring**: Real-time operator status tracking and reporting
- **Auto-recovery**: Intelligent error classification and automatic retry logic

### 🛡️ **Enterprise-Grade Reliability**
- **Comprehensive Error Handling**: 59+ exception handlers throughout codebase
- **Webhook Certificate Resilience**: Automatic timing issue resolution for RHOAI
- **Resource Conflict Detection**: Prevention of operator namespace conflicts
- **Smart Retry Logic**: Exponential backoff with contextual error recovery
- **Parallel Installation**: Optimized performance for multiple operators

### 🔧 **Advanced Integration**
- **RHOAI DSC/DSCI Management**: Complete DataScienceCluster lifecycle control
- **Kueue Management States**: Dynamic DSC integration with Managed/Unmanaged modes
- **KedaController Automation**: Automatic KEDA controller creation and validation
- **Kuadrant Automation**: Automatic Kuadrant CR creation for RHCL
- **LeaderWorkerSet Automation**: Automatic LeaderWorkerSetOperator CR creation for LWS
- **Configurable Timeouts**: Flexible timing control for enterprise environments

## 🛡️ Enhanced Stability Features

RHOShift includes a comprehensive stability system designed for enterprise deployments:

### **Stability Levels**
- **🟢 Enhanced (Default)**: Pre-flight checks + health monitoring + auto-recovery
- **🔵 Comprehensive**: Maximum resilience with advanced error classification
- **⚪ Basic**: Standard installation with basic error handling

### **Pre-flight Validation**
- ✅ Cluster connectivity and authentication
- ✅ Required permissions verification
- ✅ Resource quota validation
- ✅ Operator catalog accessibility
- ✅ Namespace conflict detection
- ✅ DSCI compatibility validation for RHOAI installations

### **Health Monitoring**
- 📊 Real-time operator status tracking
- 🔍 Multi-resource health validation
- 📈 Installation progress reporting
- ⚡ Performance metrics and timing

### **Auto-recovery Features**
- 🔄 Intelligent retry mechanisms
- 🧠 Error classification (transient vs. permanent)
- ⏰ Exponential backoff strategies
- 🛠️ Automatic resource cleanup and recreation

## 📦 Supported Operators

| Operator | Package | Namespace | Channel | Dependencies |
|----------|---------|-----------|---------|--------------|
| **cert-manager** | `openshift-cert-manager-operator` | `cert-manager-operator` | `stable-v1` | None |
| **Kueue** | `kueue-operator` | `openshift-kueue-operator` | `stable-v1.0` | cert-manager |
| **KEDA** | `openshift-custom-metrics-autoscaler-operator` | `openshift-keda` | `stable` | None |
| **RHCL** | `rhcl-operator` | `openshift-operators` | `stable` | None |
| **LWS** | `leader-worker-set` | `openshift-lws-operator` | `stable-v1.0` | None |
| **RHOAI/ODH** | `opendatahub-operator` | `openshift-operators` | `stable` | None |

## 🚀 Installation

### Quick Install
```bash
git clone https://github.com/mwaykole/O.git
cd O
pip install -e .
```

### Verify Installation
```bash
rhoshift --help
rhoshift --summary
```

## 💻 Usage

### **Basic Commands**
```bash
# Install single operator with enhanced stability
rhoshift --cert-manager

# Install multiple operators with batch optimization
rhoshift --cert-manager --keda --kueue --rhcl --lws

# Install with dependency resolution (Kueue + cert-manager)
rhoshift --kueue

# Install all operators (includes DSCI validation for RHOAI)
rhoshift --all

# Install all with RHOAI channel preference
rhoshift --all --rhoai-channel=odh-nightlies

# Show detailed operator summary
rhoshift --summary

# Clean up all operators
rhoshift --cleanup
```

### **RHOAI with DSC/DSCI**
```bash
# Install RHOAI with complete setup
rhoshift --rhoai \
  --rhoai-channel=odh-nightlies \
  --rhoai-image=brew.registry.redhat.io/rh-osbs/iib:1049242 \
  --deploy-rhoai-resources

# Install RHOAI with Kueue integration
rhoshift --rhoai --kueue Managed \
  --rhoai-channel=stable \
  --rhoai-image=quay.io/rhoai/rhoai-fbc-fragment:rhoai-2.25-nightly \
  --deploy-rhoai-resources
```

### **Kueue Management States**
```bash
# Install Kueue as Managed (RHOAI controls it)
rhoshift --kueue Managed

# Install Kueue as Unmanaged (independent) - Default
rhoshift --kueue Unmanaged
rhoshift --kueue  # Same as above

# Switch management states (updates existing DSC)
rhoshift --kueue Managed    # Switch to Managed
rhoshift --kueue Unmanaged  # Switch to Unmanaged
```

## 🔧 Advanced Usage

### **Enterprise Deployment**
```bash
# Complete ML/AI stack with queue management
rhoshift --all --kueue Managed \
  --rhoai-channel=stable \
  --rhoai-image=brew.registry.redhat.io/rh-osbs/iib:1049242 \
  --deploy-rhoai-resources \
  --timeout=900

# Development environment setup
rhoshift --cert-manager --kueue Unmanaged --keda --rhcl --lws
```

### **Custom Configuration**
```bash
# Custom timeouts and retries for enterprise clusters
rhoshift --all \
  --timeout=1200 \
  --retries=5 \
  --retry-delay=15

# Custom oc binary path
rhoshift --cert-manager --oc-binary=/usr/local/bin/oc

# Verbose output for debugging
rhoshift --kueue Managed --verbose
```

## 🔗 Dependency Management

RHOShift automatically handles operator dependencies:

### **Automatic Resolution**
- **Kueue** → **cert-manager**: Installing Kueue automatically includes cert-manager
- **Installation Order**: Dependencies installed first, primary operators second
- **Conflict Detection**: Prevents namespace and resource conflicts

### **Smart Validation**
```bash
# This command installs BOTH cert-manager AND Kueue in correct order:
rhoshift --kueue
# Output:
# 🔍 Pre-flight checks passed. Cluster is ready for installation.
# ⚠️  Missing dependency: kueue-operator requires openshift-cert-manager-operator
# 🚀 Installing 2 operators with enhanced stability...
# ✅ cert-manager installed successfully
# ✅ kueue installed successfully
```

## 🤖 RHOAI Integration

### **DataScienceCluster Management**
RHOShift provides complete DSC/DSCI lifecycle management:

```bash
# Create RHOAI with DSC/DSCI
rhoshift --rhoai --deploy-rhoai-resources

# RHOAI with Kueue integration
rhoshift --rhoai --kueue Managed --deploy-rhoai-resources
```

### **DSC Behavior**
- **Existing DSC**: Automatically updates Kueue managementState
- **No DSC**: State applied when DSC is created via `--deploy-rhoai-resources`
- **Webhook Resilience**: Automatic handling of certificate timing issues

### **Output Examples**
```bash
# When DSC exists and gets updated:
🔄 Updating DSC with Kueue managementState: Managed
✅ Successfully updated DSC with Kueue managementState: Managed

# When no DSC exists:
ℹ️  No existing DSC found. Kueue managementState will be applied when DSC is created.
```

## ⚙️ Configuration

### **CLI Options**
```bash
Operator Selection:
  --cert-manager        Install cert-manager Operator
  --rhoai               Install RHOAI Operator
  --kueue [{Managed,Unmanaged}]  Install Kueue with DSC integration
  --keda                Install KEDA (Custom Metrics Autoscaler)
  --rhcl                Install RHCL (Red Hat Connectivity Link) and create Kuadrant CR
  --lws                 Install LWS (Leader Worker Set) and create LeaderWorkerSetOperator CR
  --all                 Install all operators
  --cleanup             Clean up all operators
  --summary             Show operator summary

Configuration:
  --oc-binary OC_BINARY     Path to oc CLI (default: oc)
  --retries RETRIES         Max retry attempts (default: 3)
  --retry-delay RETRY_DELAY Delay between retries (default: 10s)
  --timeout TIMEOUT         Command timeout (default: 300s)

RHOAI Options:
  --rhoai-channel CHANNEL   RHOAI channel (stable/odh-nightlies)
  --rhoai-image IMAGE       RHOAI container image
  --raw RAW                 Enable raw serving (True/False)
  --deploy-rhoai-resources  Create DSC and DSCI
```

### **Environment Variables**
```bash
export LOG_FILE_LEVEL=DEBUG      # File logging level
export LOG_CONSOLE_LEVEL=INFO    # Console logging level
```

### **Logging**
- **Location**: `/tmp/rhoshift.log`
- **Rotation**: 10MB max size, 5 backup files
- **Levels**: DEBUG (file) / INFO (console)
- **Colors**: Supported in compatible terminals

## 🔍 Troubleshooting

### **Common Issues**

#### **Permission Errors**
```bash
# Verify cluster access
oc whoami
oc auth can-i create subscriptions -n openshift-operators
```

#### **Installation Failures**
```bash
# Check logs
tail -f /tmp/rhoshift.log

# Verify operator catalogs
oc get catalogsource -n openshift-marketplace

# Check with enhanced timeouts
rhoshift --kueue --timeout=900 --retries=5
```

#### **Dependency Issues**
```bash
# Verify dependencies are resolved
rhoshift --summary

# Manual dependency installation
rhoshift --cert-manager
rhoshift --kueue
```

#### **RHOAI/DSC Issues**
```bash
# Check DSC status
oc get dsc,dsci -A

# Verify webhook certificates
oc get pods -n opendatahub-operators

# Manual DSC creation
rhoshift --rhoai --deploy-rhoai-resources --timeout=900
```

#### **DSCI Immutable Field Conflicts**
```bash
# Error: MonitoringNamespace is immutable
# This happens when existing DSCI has different monitoring namespace

# Check existing DSCI configuration
oc get dsci default-dsci -o yaml

# Solution 1: Force recreate DSCI (recommended)
rhoshift --rhoai --deploy-rhoai-resources

# Solution 2: Use existing DSCI configuration
# RHOShift will automatically detect and adapt to existing DSCI
```

### **Debug Mode**
```bash
# Enable verbose output
rhoshift --all --verbose

# Check stability report
rhoshift --summary
```

## 🛠️ Development

### **Prerequisites**
- Python 3.8+
- OpenShift CLI (oc)
- OpenShift cluster access
- cluster-admin privileges

### **Project Structure**
```
rhoshift/
├── rhoshift/
│   ├── cli/              # Command-line interface
│   ├── logger/           # Logging system
│   ├── utils/
│   │   ├── operator/     # Operator management
│   │   ├── resilience.py # Error handling & recovery
│   │   ├── health_monitor.py # Health monitoring
│   │   ├── stability_coordinator.py # Stability management
│   │   └── constants.py  # Operator configurations
│   └── main.py          # Entry point
├── scripts/
│   ├── cleanup/         # Cleanup utilities
│   └── run_upgrade_matrix.sh # Upgrade testing
└── tests/               # Test suite
```

### **Running Tests**
```bash
pytest tests/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Create Pull Request

### **Development Guidelines**
- Follow Python PEP 8 standards
- Add tests for new features
- Update documentation
- Ensure backward compatibility

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/mwaykole/O/issues)
- **Documentation**: This README and `--help` output
- **Logs**: `/tmp/rhoshift.log` for detailed debugging

---

**RHOShift** - Enterprise-grade OpenShift operator management with enhanced stability and reliability features.
