# System Tray Integration - Installation Guide

TimeLocker's system tray integration is **optional**. The CLI works perfectly without it.

> **Important**: TimeLocker does **not** have a full desktop GUI application. This guide covers the optional system tray integration for desktop notifications
> and status indicators. TimeLocker is primarily a CLI-based backup tool.

## Do You Need System Tray Integration?

**You DON'T need system tray dependencies if:**

- You're using TimeLocker only via CLI commands
- You're running on a headless server
- You're using TimeLocker via SSH
- You don't want system tray notifications

**You DO need system tray dependencies if:**

- You want system tray integration with desktop notifications
- You want visual status indicators in your system tray
- You're running TimeLocker on a desktop environment

## Installation

### Linux (Ubuntu/Debian)

First, install system-level dependencies:

```bash
# Install GObject Introspection development libraries
sudo apt-get update
sudo apt-get install -y \
    libgirepository1.0-dev \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    gir1.2-gtk-3.0 \
    gir1.2-appindicator3-0.1
```

Then install TimeLocker with system tray support:

```bash
pip install -e .[gui]
# or with dev dependencies
pip install -e .[dev,gui]
```

### Linux (Fedora/RHEL/CentOS)

```bash
# Install system dependencies
sudo dnf install -y \
    gobject-introspection-devel \
    cairo-devel \
    pkg-config \
    python3-devel \
    gtk3 \
    libappindicator-gtk3

# Install TimeLocker with system tray support
pip install -e .[gui]
```

### Linux (Arch)

```bash
# Install system dependencies
sudo pacman -S \
    gobject-introspection \
    cairo \
    pkg-config \
    python \
    gtk3 \
    libappindicator-gtk3

# Install TimeLocker with system tray support
pip install -e .[gui]
```

### macOS

```bash
# No system dependencies needed - rumps is pure Python
pip install -e .[gui]
```

### Windows

```bash
# No system dependencies needed - pystray uses native Windows APIs
pip install -e .[gui]
```

## Troubleshooting

### PyGObject Build Errors on Linux

If you get errors like:

```
ERROR: Dependency 'girepository-2.0' is required but not found.
```

This means you're missing system-level libraries. Install them as shown above for your distribution.

### System Tray Not Working

If the system tray doesn't appear after installing GUI dependencies:

1. **Check your desktop environment**: System tray support varies by desktop environment
    - GNOME: May need the "AppIndicator" extension
    - KDE: Should work out of the box
    - XFCE: Should work out of the box
    - i3/Sway: May need additional configuration

2. **Verify installation**:
   ```bash
   python -c "import gi; gi.require_version('AppIndicator3', '0.1'); from gi.repository import AppIndicator3; print('OK')"
   ```

3. **Check logs**:
   ```bash
   tl monitor logs --level DEBUG | grep -i tray
   ```

### Running Without System Tray

If you don't want to install system tray dependencies, TimeLocker works perfectly without them:

```bash
# Install without system tray support (CLI only)
pip install -e .
# or with dev dependencies
pip install -e .[dev]
```

The system tray initialization will fail silently (logged as a warning), but all CLI functionality works normally.

## Platform-Specific Notes

### Linux

- Uses GTK3 and AppIndicator3 for system tray
- Requires GObject Introspection libraries
- Best support on GNOME, KDE, XFCE

### macOS

- Uses `rumps` (Ridiculously Uncomplicated macOS Python Statusbar apps)
- Pure Python, no system dependencies needed
- Works on macOS 10.10+

### Windows

- Uses `pystray` for system tray
- Uses Pillow for icon rendering
- Works on Windows 7+

## Verifying Installation

After installing system tray dependencies, verify they work:

```bash
# Check if system tray is available
python -c "from TimeLocker.monitoring.system_tray_integration import SystemTrayIntegration; tray = SystemTrayIntegration(); print('Available' if tray.is_available() else 'Not available')"
```

## See Also

- [CLI Modules](../3-implementation/cli-modules.md)
