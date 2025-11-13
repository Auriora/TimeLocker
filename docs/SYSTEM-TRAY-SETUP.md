# System Tray Integration Setup (Optional)

TimeLocker's system tray integration is **optional**. The CLI works perfectly without it.

> **Note**: This is for system tray integration only, not a full desktop GUI application. TimeLocker is primarily a CLI tool with optional desktop notifications
> and status indicators.

## Quick Install

### Linux (Ubuntu/Debian)

```bash
# Install system dependencies first
sudo apt-get install -y libgirepository1.0-dev libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0 gir1.2-appindicator3-0.1

# Then install TimeLocker with system tray support
pip install -e .[gui]
```

### macOS

```bash
# No system dependencies needed
pip install -e .[gui]
```

### Windows

```bash
# No system dependencies needed
pip install -e .[gui]
```

## Do You Need This?

**NO** if you're:

- Using CLI only
- Running on a headless server
- Connecting via SSH

**YES** if you want:

- System tray notifications
- Desktop integration
- Visual status indicators

## Full Documentation

See [guides/gui-dependencies.md](guides/gui-dependencies.md) for complete installation instructions and troubleshooting.

## What This Provides

The system tray integration includes:

- **Status Indicator**: Visual indicator in system tray showing backup status
- **Desktop Notifications**: Alerts for backup completion, errors, and warnings
- **Quick Access**: Right-click menu for common operations
- **Background Monitoring**: Non-intrusive status updates

## What This Does NOT Provide

This is **not** a full desktop GUI application. TimeLocker does not have:

- Graphical backup configuration interface
- Visual repository management
- Interactive backup wizards
- Dashboard or control panel

For all configuration and operations, use the CLI commands. The system tray is purely for monitoring and notifications.
