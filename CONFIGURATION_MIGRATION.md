# TimeLocker Configuration Migration

## Overview

TimeLocker has been updated to follow the XDG Base Directory Specification for configuration file placement. This provides better organization and follows Linux
desktop standards.

## Configuration Locations

### User Configuration (Default)

- **New Location**: `~/.config/timelocker/config.json`
- **Legacy Location**: `~/.timelocker/config.json` (still supported as fallback)

### System Configuration (When running as root)

- **Primary**: `/etc/timelocker/config.json`
- **Fallback**: `/etc/xdg/timelocker/config.json`

## Automatic Migration

TimeLocker automatically detects and migrates legacy configurations:

1. **Detection**: On startup, TimeLocker checks if a legacy configuration exists at `~/.timelocker/config.json`
2. **Migration**: If found and no new configuration exists, it automatically migrates:
    - Copies configuration files to the new location
    - Creates backup of original files
    - Verifies migration integrity using checksums
    - Creates migration marker file
3. **Preservation**: Original files are left intact for safety

## Migration Features

### Safety Measures

- **Backup Creation**: Original files are backed up before migration
- **Checksum Verification**: File integrity is verified after copying
- **Atomic Operations**: Migration is performed safely to prevent corruption
- **Rollback Capability**: Original files remain untouched

### Migration Tracking

- **Migration Marker**: `.migrated_from_legacy` file tracks successful migrations
- **Backup Directory**: `migration_backups/` contains timestamped backups
- **Detailed Logging**: All migration steps are logged for troubleshooting

## CLI Commands

### View Configuration Information

```bash
tl config info
```

Shows detailed information about:

- Current configuration directory and file paths
- System vs user context
- XDG compliance status
- Migration status
- Backup information

### View Current Configuration

```bash
tl config show
```

Displays the current configuration including repositories, targets, and settings.

### Setup Configuration

```bash
tl config setup
```

Interactive wizard that automatically handles migration if needed.

## Environment Variables

TimeLocker respects XDG environment variables:

- `XDG_CONFIG_HOME`: Custom config directory (defaults to `~/.config`)

## Backward Compatibility

TimeLocker maintains backward compatibility:

- Legacy configurations continue to work
- Fallback to legacy location if new location doesn't exist
- No breaking changes to existing workflows

## Manual Migration

If automatic migration fails, you can manually migrate:

```bash
# Create new directory
mkdir -p ~/.config/timelocker

# Copy configuration
cp ~/.timelocker/config.json ~/.config/timelocker/

# Copy any other files (if they exist)
cp -r ~/.timelocker/* ~/.config/timelocker/
```

## Troubleshooting

### Check Migration Status

```bash
tl config info
```

### View Migration Logs

Migration activities are logged with INFO level. Enable verbose logging:

```bash
tl config show --verbose
```

### Migration Backup Location

Backups are stored in: `~/.config/timelocker/migration_backups/`

### Common Issues

1. **Permission Errors**: Ensure write permissions to `~/.config/`
2. **Disk Space**: Ensure sufficient space for configuration copy
3. **Concurrent Access**: Avoid running multiple TimeLocker instances during migration

## Benefits of XDG Compliance

1. **Standards Compliance**: Follows Linux desktop standards
2. **Better Organization**: Separates config from data and cache
3. **User Expectations**: Matches behavior of other modern applications
4. **System Integration**: Works better with backup and sync tools
5. **Multi-User Support**: Cleaner separation between user and system configs

## System Administrator Notes

For system-wide deployments:

- Place configuration in `/etc/timelocker/config.json`
- Use `/etc/xdg/timelocker/config.json` for XDG-compliant system defaults
- User configurations will override system configurations
- TimeLocker automatically detects root context and uses appropriate paths
