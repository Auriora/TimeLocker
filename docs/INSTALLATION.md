# TimeLocker Installation Guide

## Current Status

**TimeLocker MVP v1.0.0 - 95% Complete and Production Ready**

- ✅ All 367 tests passing (100% pass rate)
- ✅ Test coverage: 83.3% (exceeds 80% target)
- ✅ All core features implemented and working

## Introduction

This guide provides detailed instructions for installing TimeLocker, a high-level interface for backup operations using the Restic backup tool. TimeLocker
simplifies backup operations by providing a robust, object-oriented interface that handles repository management, file selection patterns, and backup
configurations across multiple storage backends.

## Intended audience

This guide is intended for:

- System administrators who need to set up backup solutions
- Developers who want to integrate TimeLocker into their projects
- End users who want to use TimeLocker for personal backup needs

## Prerequisites

Before installing TimeLocker, ensure your system meets the following requirements:

### System Requirements

- Operating System: Linux, macOS, or Windows
- Disk Space: At least 100MB for the application and dependencies
- Memory: Minimum 512MB RAM (1GB recommended)

### Software Requirements

- Python 3.12 or higher
- pip (Python package installer)
- Restic backup tool installed and accessible in PATH
- Git (for cloning the repository)

### Additional Requirements for Cloud Storage

- For Amazon S3: AWS account with appropriate permissions
- For Backblaze B2: B2 account with appropriate permissions

## Installation

### Installing Python

#### On Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3-pip git

# Fedora
sudo dnf install python3.12 python3-pip git

# Arch Linux
sudo pacman -S python python-pip git
```

#### On macOS

```bash
# Using Homebrew
brew install python@3.12 git
```

#### On Windows

1. Download Python 3.12 from [python.org](https://www.python.org/downloads/)
2. Run the installer and check "Add Python to PATH"
3. Download and install Git from [git-scm.com](https://git-scm.com/download/win)

### Installing Restic

#### On Linux

```bash
# Ubuntu/Debian
sudo apt install restic

# Fedora
sudo dnf install restic

# Arch Linux
sudo pacman -S restic
```

#### On macOS

```bash
# Using Homebrew
brew install restic
```

#### On Windows

1. Download the latest release from [GitHub](https://github.com/restic/restic/releases)
2. Extract the executable to a directory in your PATH

### Installing TimeLocker

1. Clone the repository:

```bash
git clone https://github.com/Auriora/TimeLocker.git
cd TimeLocker
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Verify the installation:

```bash
# Set PYTHONPATH for development installation
export PYTHONPATH=src

# Test basic import
python -c "from TimeLocker.backup_manager import BackupManager; print('TimeLocker installed successfully')"

# Run full test suite to verify installation
python -m pytest --tb=short

# Check test coverage
python -m pytest --cov=TimeLocker --cov-report=term-missing
```

Expected results:

- All 367 tests should pass
- Test coverage should be ≥ 80% (currently 83.3%)

## Configuration

### Basic Configuration

TimeLocker requires minimal configuration to get started. The main configuration involves setting up your backup repositories and targets.

### Environment Variables

For cloud storage backends, you may need to set the following environment variables:

#### For AWS S3

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=your_region
```

#### For Backblaze B2

```bash
export B2_ACCOUNT_ID=your_account_id
export B2_ACCOUNT_KEY=your_account_key
```

## Verification

To verify that TimeLocker is installed correctly and working properly, you can run a simple test:

```python
from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType

# Initialize backup manager
manager = BackupManager()

# Create a backup target
selection = FileSelection()
selection.add_path("/path/to/test/folder")
target = BackupTarget(selection, tags=["test"])

# Check if the manager is initialized correctly
print("Backup manager initialized:", manager is not None)
print("Backup target created:", target is not None)
```

## Troubleshooting

### Common Issues

#### Issue: Python version not found

**Solution**: Ensure Python 3.12 or higher is installed and in your PATH. Run `python --version` to check.

#### Issue: Restic not found

**Solution**: Ensure Restic is installed and in your PATH. Run `restic version` to check.

#### Issue: Dependency installation fails

**Solution**: Try updating pip with `pip install --upgrade pip` and then retry installing dependencies.

#### Issue: Cloud storage authentication fails

**Solution**: Verify that your environment variables are set correctly and that your credentials have the necessary permissions.

### Getting Help

If you encounter issues not covered in this guide, please:

1. Check the [Troubleshooting section in the README](../README.md#troubleshooting)
2. Search for similar issues in the [GitHub Issues](https://github.com/Auriora/TimeLocker/issues)
3. Create a new issue if your problem is not already reported

## Next Steps

Now that you have successfully installed TimeLocker, you can:

1. Create your first backup repository
2. Configure backup targets with file selection patterns
3. Set up scheduled backups
4. Explore advanced features like pattern groups and snapshot management

For more information, refer to the [Quick Start Guide](README.md#quick-start) and [Examples](README.md#more-detailed-examples) in the README.

## Related Resources

- [README](../README.md) - Project overview and quick start guide
- [Command Builder Documentation](command_builder.md) - Details on using the command builder
- [Support Guide](../SUPPORT.md) - How to get help with TimeLocker
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute to TimeLocker

## Document Information

- Version: 1.0.0
- Last Updated: 2024-07-01
- Author: TimeLocker Team