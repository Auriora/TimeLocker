---
title: "User Guide: Installation"
id: "user-guide-installation"
type: [ guide ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "2026-07-26"
tags: [guide, user, installation]
links:
  tooling: []
---

# User Guide: Installation

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 2026-07-26
- **Audience**: End Users, Administrators

## 1. Purpose

Provide steps for a user/source installation across supported Python platforms
and explain the separately administered protected Linux deployment.

## 2. Goal

After completing this guide you will have TimeLocker installed, dependencies configured (Python, Restic), and the CLI validated with optional development setup.

## 3. Prerequisites

- Supported operating system: Linux, macOS, or Windows.
- Python 3.12 or 3.13. TimeLocker declares `>=3.12,<3.14`.
- Restic 0.18.0 or later available on `PATH`.
- Internet access to install Python and Restic.
- Git if cloning from source.
- Optional: AWS/B2 credentials for cloud backends.

## 4. Step-by-Step Instructions

### 4.1 Review Release Status

- **Current status**: Beta, version 0.9.1 is prepared but not published.
- **Distribution**: Source checkout only; TimeLocker is not currently published
  to PyPI.
- **Quality gate**: The configured test suite enforces at least 50% coverage.

### 4.2 Understand TimeLocker

TimeLocker is a Python-based high-level interface over Restic for backup management, offering repository orchestration, file selection patterns, and
multi-backend support.

### 4.3 Install System Requirements

#### Linux

```bash
sudo apt update
sudo apt install python3.12 python3-pip git  # Ubuntu/Debian; Python 3.13 is also supported
# sudo dnf install python3.12 python3-pip git  # Fedora; use python3.13 if preferred
# sudo pacman -S python python-pip git         # Arch
```

The independent system tray is optional and does not affect backup, restore, or
other CLI commands. On Linux Mint/Ubuntu, install GTK 3, PyGObject, and the Ayatana
AppIndicator typelib when you want tray support:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1
```

TimeLocker prefers `AyatanaAppIndicator3` and retains the legacy
`AppIndicator3` fallback. A pyenv-managed Python does not normally see
distribution `python3-gi`; use the supported system Python in a virtual
environment created with `--system-site-packages`, or install the build
prerequisites needed for `python -m pip install '.[gui]'`.

#### macOS

```bash
brew install python@3.12 git  # python@3.13 is also supported
```

#### Windows

1. Download Python 3.12 or 3.13 from [python.org](https://www.python.org/downloads/).
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

#### From Source (Current Supported Path)

```bash
git clone https://github.com/Auriora/TimeLocker.git
cd TimeLocker
python -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .                # User installation

# Contributors use an editable install with development dependencies
python -m pip install -e '.[dev]'
```

### 4.6 Verify Installation

```bash
timelocker --help
tl --help
python -c "from TimeLocker.backup_manager import BackupManager; print('TimeLocker installed successfully')"
python -m pytest -m "not performance and not stress and not minio"
```

Expected results: both CLI commands display help. For contributor installs, the
normal suite passes and enforces coverage of at least 50%. Live MinIO tests are
owned by the separately provisioned profile documented in
[`docs/4-testing/README.md`](../../4-testing/README.md).

### 4.7 Protected Linux Deployment

Host-level backup and retention use an administrator-installed deployment that
is distinct from a user/source installation. It provides:

```text
/usr/local/bin/timelocker
/usr/local/bin/tl
/usr/local/bin/timelocker-tray
/usr/local/libexec/timelocker-system-control
/opt/timelocker/releases/RELEASE_ID/
/opt/timelocker/selected-release.json
/etc/timelocker/
/var/lib/timelocker/
```

The stable launchers ignore the caller's pyenv, checkout, home directory, and
current working directory. A staged release is selected only after its CLI,
backend, and tray entrypoints pass compatibility probes. System control is
exposed through `/run/timelocker/control.sock`.

The repository contains validated deployment primitives and packaged assets;
it does not currently expose a general end-user installer command. An
administrator must stage the release, install the root-owned assets, configure
the protected target and credentials by reference, approve retention, and
enable the required systemd units.

Verify an installed host without reading secrets:

```bash
/usr/local/bin/timelocker version --short
/usr/local/bin/timelocker runs list --limit 5
/usr/local/bin/timelocker logs view --scope system --lines 20
/usr/local/bin/timelocker system backup --help
/usr/local/bin/timelocker system retention --help
systemctl status timelocker-control.socket
systemctl status timelocker-retention.timer
/usr/local/bin/timelocker-tray status --once
```

Protected reads and `system backup`/`system retention` requests require current
membership in `timelocker-operators`. These commands use the privileged backend
without elevating the caller process.
Installation, group changes, policy approval, service changes, release
selection, and rollback require root.

### 4.8 Validated Platform Matrix

The `0.9.1` wheel and source distribution are clean-install tested on every
combination below. Each test runs `version --short` and root help through both
the `timelocker` and `tl` entry points.

| Operating system | Python 3.12 | Python 3.13 |
|------------------|-------------|-------------|
| Linux | wheel and sdist | wheel and sdist |
| macOS | wheel and sdist | wheel and sdist |
| Windows | wheel and sdist | wheel and sdist |

This validates wheel/source installation and safe CLI startup. Backup and restore operations
still require a compatible Restic executable and any backend-specific
credentials. No PyPI distribution is currently published; use the source path
above until an authorized release provides downloadable artifacts.

The protected immutable-release, local-backend, systemd scheduling, and
independent-tray deployment has live acceptance evidence on Linux Mint. The
portable architecture includes a Windows adapter, but a protected Windows
deployment is not yet claimed as live-accepted.

### 4.9 Understand Modern Packaging Features

- `pyproject.toml` for modern builds (PEP 517/518).
- Optional dependency groups (`dev`, `gui`). S3 and B2 runtime dependencies are
  included in the base installation.
- Entry points install both `timelocker` and `tl` commands.

### 4.10 Configure Environment

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

## 5. Troubleshooting

- **CLI command not found**: Ensure the Python scripts directory is on `PATH` or reinstall with pip.
- **Tests failing**: Verify Restic 0.18.0 or later is on `PATH` and install
  contributor dependencies with `python -m pip install -e '.[dev]'`.
- **`pip install timelocker` fails**: No PyPI distribution is currently
  supported; install from a source checkout as shown above.
- **Protected CLI uses the wrong checkout or pyenv**: use
  `/usr/local/bin/timelocker`. A protected deployment must fail closed rather
  than fall back to user state.
- **System runs are not visible**: confirm the backend socket is active and the
  user has current `timelocker-operators` membership.

## 6. Frequently Asked Questions (FAQ)

- **Do I need Restic if I only use local repositories?** Yes, TimeLocker orchestrates Restic for all backup operations.
- **Can I run TimeLocker without virtual environments?** Yes, but using a virtual environment avoids dependency conflicts.

# References

- Restic installation docs: <https://restic.readthedocs.io>
- Python downloads: <https://www.python.org/downloads/>
- TimeLocker repository: <https://github.com/Auriora/TimeLocker>
- [Independent tray setup](../../SYSTEM-TRAY-SETUP.md)
- [Scheduling guide](../developer/scheduling-guide.md)
- [Backup operations troubleshooting](./backup-operations-troubleshooting.md)
