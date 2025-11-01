---
title: "User Guide: Installation"
id: "user-guide-installation"
type: [ guide ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "01-11-2025"
tags: [guide, user, installation]
links:
  tooling: []
---

# User Guide: Installation

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: End Users, Administrators

## 1. Purpose

Provide comprehensive steps for installing TimeLocker, its dependencies, and verifying the setup across Linux, macOS, and Windows.

## 2. Goal

After completing this guide you will have TimeLocker installed, dependencies configured (Python, Restic), and the CLI validated with optional development setup.

## 3. Prerequisites

- Supported operating system (Linux, macOS, or Windows).
- Internet access to install Python and Restic.
- Git if cloning from source.
- Optional: AWS/B2 credentials for cloud backends.

## 4. Step-by-Step Instructions

### 4.1 Review Release Status

- **Current status**: *TimeLocker MVP v1.0.0 – 95% Complete and Production Ready*.
- Test metrics: 367 tests passing, coverage 83.3%, all core features implemented.

### 4.2 Understand TimeLocker

TimeLocker is a Python-based high-level interface over Restic for backup management, offering repository orchestration, file selection patterns, and
multi-backend support.

### 4.3 Install System Requirements

#### Linux

```bash
sudo apt update
sudo apt install python3.12 python3-pip git  # Ubuntu/Debian
# sudo dnf install python3.12 python3-pip git  # Fedora
# sudo pacman -S python python-pip git         # Arch
```

#### macOS

```bash
brew install python@3.12 git
```

#### Windows

1. Download Python 3.12 from [python.org](https://www.python.org/downloads/).
2. Run the installer and select "Add Python to PATH".
3. Install Git from [git-scm.com](https://git-scm.com/download/win).

### 4.4 Install Restic

#### Linux

```bash
sudo apt install restic       # Ubuntu/Debian
# sudo dnf install restic     # Fedora
# sudo pacman -S restic       # Arch
```

#### macOS

```bash
brew install restic
```

#### Windows

1. Download the latest release from [github.com/restic/restic/releases](https://github.com/restic/restic/releases).
2. Extract the executable into a directory on your `PATH`.

### 4.5 Install TimeLocker

#### From PyPI (Recommended)

```bash
pip install timelocker                 # Base install
pip install timelocker[dev]            # With development extras
pip install timelocker[aws]            # AWS S3 support
pip install timelocker[b2]             # Backblaze B2 support
pip install timelocker[aws,b2,dev]     # All extras
```

#### From Source (Development)

```bash
git clone https://github.com/Auriora/TimeLocker.git
cd TimeLocker
pip install -e .[dev]                  # Editable install with dev deps
```

### 4.6 Verify Installation

```bash
timelocker --help
tl --help
python -c "from TimeLocker.backup_manager import BackupManager; print('TimeLocker installed successfully')"
pytest --tb=short
pytest --cov=TimeLocker --cov-report=term-missing
```

Expected results: all tests pass and coverage ≥ 80%.

### 4.7 Understand Modern Packaging Features

- `pyproject.toml` for modern builds (PEP 517/518).
- Optional dependency groups (`dev`, `aws`, `b2`, `diagrams`).
- Entry points install both `timelocker` and `tl` commands.

### 4.8 Configure Environment

Basic configuration focuses on setting up repositories and targets. For cloud backends, export credentials:

```bash
# AWS S3
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=your_region

# Backblaze B2
export B2_ACCOUNT_ID=your_account_id
export B2_ACCOUNT_KEY=your_account_key
```

### 4.9 Optional: Manual Vacuum / Additional Sections

(If applicable, include other configuration tasks; original document contains extended instructions you may retain here.)

## 5. Troubleshooting

- **CLI command not found**: Ensure the Python scripts directory is on `PATH` or reinstall with pip.
- **Tests failing**: Verify Restic is on `PATH` and dependencies installed with `pip install timelocker[dev]`.
- **Missing extras**: Re-run installation with appropriate extras flag (e.g., `pip install timelocker[aws]`).

## 6. Frequently Asked Questions (FAQ)

- **Do I need Restic if I only use local repositories?** Yes, TimeLocker orchestrates Restic for all backup operations.
- **Can I run TimeLocker without virtual environments?** Yes, but using a virtual environment avoids dependency conflicts.

# References

- Restic installation docs: <https://restic.readthedocs.io>
- Python downloads: <https://www.python.org/downloads/>
- TimeLocker repository: <https://github.com/Auriora/TimeLocker>
