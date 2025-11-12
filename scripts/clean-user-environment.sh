#!/bin/bash
#
# TimeLocker User Environment Cleanup Script
#
# This script removes all TimeLocker configuration, data, and cache files
# from the user's home directory to provide a clean slate for testing.
#
# WARNING: This will delete all TimeLocker configuration, credentials,
# backup history, logs, and cached data. Make sure you have backups of
# anything important before running this script.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}TimeLocker User Environment Cleanup${NC}"
echo "======================================"
echo ""
echo "This script will remove:"
echo "  • Configuration: ~/.config/timelocker/"
echo "  • Data: ~/.local/share/timelocker/"
echo "  • State: ~/.local/state/timelocker/"
echo "  • Cache: ~/.cache/timelocker/"
echo "  • Legacy: ~/.timelocker/"
echo "  • Scripts: ~/.local/bin/timelocker-*.sh"
echo "  • Other: ~/Library/Application Support/TimeLocker/"
echo "  • Other: ~/AppData/Local/TimeLocker/"
echo ""
echo -e "${RED}WARNING: This will delete all TimeLocker data and configuration!${NC}"
echo ""

# Prompt for confirmation
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Function to remove directory with feedback
remove_dir() {
    local dir="$1"
    if [ -d "$dir" ]; then
        echo -e "  ${YELLOW}Removing:${NC} $dir"
        rm -rf "$dir"
        echo -e "  ${GREEN}✓ Removed${NC}"
    else
        echo -e "  ${GREEN}✓ Not found:${NC} $dir (already clean)"
    fi
}

# Function to remove file with feedback
remove_file() {
    local file="$1"
    if [ -f "$file" ]; then
        echo -e "  ${YELLOW}Removing:${NC} $file"
        rm -f "$file"
        echo -e "  ${GREEN}✓ Removed${NC}"
    else
        echo -e "  ${GREEN}✓ Not found:${NC} $file (already clean)"
    fi
}

# Remove configuration directory
echo "1. Configuration directory:"
remove_dir "$HOME/.config/timelocker"

# Remove data directory
echo ""
echo "2. Data directory:"
remove_dir "$HOME/.local/share/timelocker"

# Remove state directory
echo ""
echo "3. State directory:"
remove_dir "$HOME/.local/state/timelocker"

# Remove cache directory
echo ""
echo "4. Cache directory:"
remove_dir "$HOME/.cache/timelocker"

# Remove legacy directory
echo ""
echo "5. Legacy directory:"
remove_dir "$HOME/.timelocker"

# Remove macOS Application Support (if exists)
echo ""
echo "6. macOS Application Support:"
remove_dir "$HOME/Library/Application Support/TimeLocker"

# Remove Windows AppData (if exists)
echo ""
echo "7. Windows AppData:"
remove_dir "$HOME/AppData/Local/TimeLocker"

# Remove scripts
echo ""
echo "8. TimeLocker scripts:"
for script in "$HOME/.local/bin/timelocker-"*.sh; do
    if [ -f "$script" ]; then
        remove_file "$script"
    fi
done

# Check for systemd user services
echo ""
echo "9. Systemd user services:"
if [ -d "$HOME/.config/systemd/user" ]; then
    for service in "$HOME/.config/systemd/user/timelocker"*.{service,timer}; do
        if [ -f "$service" ]; then
            echo -e "  ${YELLOW}Found:${NC} $service"
            # Try to stop and disable if systemctl is available
            if command -v systemctl &> /dev/null; then
                service_name=$(basename "$service")
                echo -e "  ${YELLOW}Stopping and disabling:${NC} $service_name"
                systemctl --user stop "$service_name" 2>/dev/null || true
                systemctl --user disable "$service_name" 2>/dev/null || true
            fi
            remove_file "$service"
        fi
    done
    # Reload systemd daemon if available
    if command -v systemctl &> /dev/null; then
        echo -e "  ${YELLOW}Reloading systemd daemon...${NC}"
        systemctl --user daemon-reload 2>/dev/null || true
    fi
else
    echo -e "  ${GREEN}✓ No systemd user directory found${NC}"
fi

# Check for cron jobs
echo ""
echo "10. Checking for cron jobs:"
if command -v crontab &> /dev/null; then
    if crontab -l 2>/dev/null | grep -q "timelocker\|TimeLocker"; then
        echo -e "  ${YELLOW}WARNING:${NC} Found TimeLocker entries in crontab"
        echo "  Please manually review and remove them with: crontab -e"
    else
        echo -e "  ${GREEN}✓ No TimeLocker cron jobs found${NC}"
    fi
else
    echo -e "  ${GREEN}✓ crontab not available${NC}"
fi

echo ""
echo -e "${GREEN}======================================"
echo "Cleanup completed successfully!"
echo "======================================${NC}"
echo ""
echo "Your user environment is now clean."
echo "You can start fresh with TimeLocker configuration."
echo ""
echo "To verify, run:"
echo "  tl repos list"
echo ""
echo "This should show no repositories configured."
