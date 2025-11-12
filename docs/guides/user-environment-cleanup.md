# TimeLocker User Environment Cleanup Guide

This guide explains how to clean your TimeLocker user environment to start with a fresh configuration.

## Quick Cleanup

Use the provided cleanup script:

```bash
./scripts/clean-user-environment.sh
```

The script will:
- Prompt for confirmation before deleting anything
- Remove all TimeLocker configuration, data, and cache files
- Stop and disable any systemd services
- Provide feedback on what was removed

## What Gets Removed

### Configuration
- `~/.config/timelocker/` - Main configuration directory
  - `config.json` - Repository and policy configuration
  - `credentials/` - Stored backend credentials
  - `policies/` - Backup and retention policies
  - `scheduling/` - Schedule definitions
  - `monitoring/` - Monitoring data
  - `logs/` - Application logs
  - And more...

### Data
- `~/.local/share/timelocker/` - Application data
  - `backup.log` - Backup history
  - `templates/` - Configuration templates

### State
- `~/.local/state/timelocker/` - Runtime state
  - `status/` - Current operation status
  - `performance/` - Performance metrics
  - `backup_notifications/` - Notification state

### Cache
- `~/.cache/timelocker/` - Temporary cache files

### Legacy
- `~/.timelocker/` - Legacy configuration directory (pre-XDG)

### Scripts
- `~/.local/bin/timelocker-*.sh` - Generated automation scripts

### Platform-Specific
- `~/Library/Application Support/TimeLocker/` (macOS)
- `~/AppData/Local/TimeLocker/` (Windows)

### Systemd Services
- `~/.config/systemd/user/timelocker*.service`
- `~/.config/systemd/user/timelocker*.timer`

## Manual Cleanup

If you prefer to clean up manually or selectively:

### Remove All Configuration
```bash
rm -rf ~/.config/timelocker
rm -rf ~/.local/share/timelocker
rm -rf ~/.local/state/timelocker
rm -rf ~/.cache/timelocker
rm -rf ~/.timelocker
```

### Remove Scripts Only
```bash
rm -f ~/.local/bin/timelocker-*.sh
```

### Remove Systemd Services
```bash
systemctl --user stop timelocker-backup.service
systemctl --user stop timelocker-backup.timer
systemctl --user disable timelocker-backup.service
systemctl --user disable timelocker-backup.timer
rm -f ~/.config/systemd/user/timelocker*.{service,timer}
systemctl --user daemon-reload
```

### Check for Cron Jobs
```bash
crontab -l | grep timelocker
# If found, edit and remove:
crontab -e
```

## Verification

After cleanup, verify the environment is clean:

```bash
# Should show no repositories
tl repos list

# Should show default/empty configuration
tl config show

# Check for remaining files
find ~ -maxdepth 3 -name "*timelocker*" -o -name "*TimeLocker*" 2>/dev/null
```

## Backup Before Cleanup

If you want to preserve your configuration before cleanup:

```bash
# Backup configuration
mkdir -p ~/timelocker-backup
cp -r ~/.config/timelocker ~/timelocker-backup/config-$(date +%Y%m%d-%H%M%S)

# Or export configuration
tl config export ~/timelocker-backup/config-export.json
```

## Starting Fresh

After cleanup, you can start with a clean configuration:

```bash
# Create a new repository
tl repos add myrepo file:///path/to/backup/repo

# Create a selection
tl selections create documents --include '~/Documents/**'

# Run your first backup
tl backup run --selection documents
```

## Troubleshooting

### Permission Denied
If you get permission errors, check file ownership:
```bash
ls -la ~/.config/timelocker
```

### Files Still Present
Some files may be in use. Stop any running TimeLocker processes:
```bash
ps aux | grep timelocker
# Kill any running processes if needed
```

### Systemd Services Won't Stop
Force stop and remove:
```bash
systemctl --user stop timelocker-backup.service --force
systemctl --user reset-failed
```

## See Also

- [Configuration Guide](../2-architecture/configuration-management.md)
- [Installation Guide](../guides/installation.md)
- [Testing Guide](../4-testing/testing-strategy.md)
