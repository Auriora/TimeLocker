#!/bin/bash
#
# Install GUI dependencies for TimeLocker system tray integration
#
# This script installs the system-level dependencies required for
# PyGObject on Linux, then installs TimeLocker with GUI support.
#

set -e

echo "TimeLocker GUI Dependencies Installer"
echo "======================================"
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux system"
    echo ""
    
    # Detect distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        echo "Cannot detect Linux distribution"
        exit 1
    fi
    
    case $OS in
        ubuntu|debian)
            echo "Installing dependencies for Ubuntu/Debian..."
            sudo apt-get update
            sudo apt-get install -y \
                libgirepository1.0-dev \
                libcairo2-dev \
                pkg-config \
                python3-dev \
                gir1.2-gtk-3.0 \
                gir1.2-appindicator3-0.1
            ;;
        fedora|rhel|centos)
            echo "Installing dependencies for Fedora/RHEL/CentOS..."
            sudo dnf install -y \
                gobject-introspection-devel \
                cairo-devel \
                pkg-config \
                python3-devel \
                gtk3 \
                libappindicator-gtk3
            ;;
        arch|manjaro)
            echo "Installing dependencies for Arch Linux..."
            sudo pacman -S --noconfirm \
                gobject-introspection \
                cairo \
                pkg-config \
                python \
                gtk3 \
                libappindicator-gtk3
            ;;
        *)
            echo "Unsupported distribution: $OS"
            echo "Please install GObject Introspection libraries manually"
            exit 1
            ;;
    esac
    
    echo ""
    echo "System dependencies installed successfully!"
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS - no system dependencies needed"
    
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "Detected Windows - no system dependencies needed"
    
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo ""
echo "Installing TimeLocker with GUI support..."
pip install -e .[gui]

echo ""
echo "======================================"
echo "Installation complete!"
echo "======================================"
echo ""
echo "Verify installation:"
echo "  python -c \"from TimeLocker.monitoring.system_tray_integration import SystemTrayIntegration; tray = SystemTrayIntegration(); print('Available' if tray.is_available() else 'Not available')\""
echo ""
