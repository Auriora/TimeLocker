# GUI Dependencies Setup (Optional)

TimeLocker's system tray integration is **optional**. The CLI works perfectly without it.

## Quick Install

### Linux (Ubuntu/Debian)

```bash
# Install system dependencies first
sudo apt-get install -y libgirepository1.0-dev libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0 gir1.2-appindicator3-0.1

# Then install TimeLocker with GUI support
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

See [docs/guides/gui-dependencies.md](docs/guides/gui-dependencies.md) for complete installation instructions and troubleshooting.
