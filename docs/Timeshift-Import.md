# Timeshift Import Feature

TimeLocker provides functionality to import configuration from Timeshift, a popular Linux system backup tool. This feature helps users migrate from Timeshift to
TimeLocker while preserving their backup settings and exclude patterns.

## Overview

The Timeshift import feature converts Timeshift's JSON configuration format to TimeLocker's repository and backup target configurations. This allows users to:

- Migrate existing backup configurations from Timeshift
- Preserve exclude patterns and backup settings
- Automatically convert device UUIDs to repository paths (when possible)
- Create appropriate backup targets for system-level backups

## Important Differences

**⚠️ Critical Note**: Timeshift and TimeLocker use different backup technologies:

- **Timeshift**: Creates filesystem snapshots of the entire system using rsync+hardlinks or BTRFS snapshots
- **TimeLocker**: Performs file-level backups using restic with deduplication and compression

The import process preserves Timeshift's approach by setting the backup path to `/` (root filesystem) and applying the same exclusion patterns. However, the
underlying backup technology differs, so restore procedures and snapshot management will be different.

## Usage

### Basic Import

```bash
# Import from default Timeshift configuration location
tl config import timeshift

# Import from specific configuration file
tl config import timeshift --config-file /path/to/timeshift.json

# Dry run to see what would be imported
tl config import timeshift --dry-run
```

### Advanced Options

```bash
# Specify custom repository and target names
tl config import timeshift \
  --repo-name "my_backup_repo" \
  --target-name "system_backup" \
  --repo-path "/mnt/backup/timeshift"

# Specify custom backup paths
tl config import timeshift \
  --paths /home \
  --paths /etc \
  --paths /usr/local

# Skip confirmation prompt (for automation)
tl config import timeshift --yes
```

## Configuration Mapping

### Repository Configuration

Timeshift's backup device UUID is converted to a TimeLocker repository:

| Timeshift Setting    | TimeLocker Equivalent | Notes                                               |
|----------------------|-----------------------|-----------------------------------------------------|
| `backup_device_uuid` | Repository location   | Automatically resolved to mount path + `/timeshift` |
| Device type          | Repository type       | Always set to "local"                               |
| -                    | Repository name       | Defaults to "timeshift_imported"                    |

### Backup Target Configuration

Timeshift's system-wide settings are converted to file-level backup targets:

| Timeshift Setting       | TimeLocker Equivalent | Notes                                                           |
|-------------------------|-----------------------|-----------------------------------------------------------------|
| System backup           | Backup paths          | Defaults to `/` (root filesystem) to match Timeshift's behavior |
| `exclude` patterns      | `exclude_patterns`    | Converted to glob patterns with `**/` prefix                    |
| `exclude-apps` patterns | `exclude_patterns`    | Merged with general excludes                                    |
| Schedule settings       | -                     | Not imported (different scheduling systems)                     |

### Default Exclude Patterns

The importer automatically adds common system excludes:

```
**/proc/**
**/sys/**
**/dev/**
**/tmp/**
**/run/**
**/mnt/**
**/media/**
**/.cache/**
**/lost+found/**
```

## UUID Resolution

The importer attempts to automatically resolve Timeshift's backup device UUID to a filesystem path:

1. Uses `blkid -U <uuid>` to find the device
2. Uses `findmnt` to find the mount point
3. Appends `/timeshift` to create the repository path

If resolution fails, you can manually specify the repository path:

```bash
tl config import timeshift --repo-path "/mnt/backup/timeshift"
```

## Example Import Process

1. **Read Timeshift Configuration**
   ```bash
   tl config import timeshift --dry-run
   ```

2. **Review the Output**
    - Check repository location is correct
    - Verify backup paths match your needs
    - Review exclude patterns

3. **Perform the Import**
   ```bash
   tl config import timeshift --repo-path "/correct/path"
   ```

4. **Initialize Repository** (if needed)
   ```bash
   tl repos init timeshift_imported
   ```

5. **Test Backup**
   ```bash
   tl backup timeshift_system --dry-run
   ```

## Post-Import Steps

After importing, you should:

1. **Review Repository Path**: Ensure the repository location is correct
2. **Adjust Backup Paths**: Timeshift backs up the entire system; you may want to be more selective
3. **Review Exclude Patterns**: Some patterns may need adjustment for file-level backups
4. **Set Up Scheduling**: Configure TimeLocker's scheduling separately
5. **Initialize Repository**: If connecting to an existing repository, ensure it's properly initialized
6. **Test Backups**: Run test backups to ensure everything works correctly

## Troubleshooting

### UUID Resolution Fails

If the importer cannot resolve the backup device UUID:

```bash
# Find your Timeshift backup location manually
sudo findmnt | grep timeshift

# Use the manual path option
tl config import timeshift --repo-path "/your/backup/path"
```

### Permission Errors

If you get permission errors reading Timeshift configuration:

```bash
# Run with sudo if needed
sudo tl config import timeshift

# Or copy the config file to a readable location
sudo cp /etc/timeshift/timeshift.json ~/timeshift-config.json
tl config import timeshift --config-file ~/timeshift-config.json
```

### BTRFS Mode Warning

If Timeshift was using BTRFS mode, you'll see a warning. This is normal - TimeLocker uses a different approach that works with any filesystem.

## Configuration File Locations

The importer checks these locations for Timeshift configuration:

1. `/etc/timeshift/timeshift.json` (standard location)
2. `/etc/timeshift.json` (alternative location)

## Limitations

- **Scheduling**: Timeshift schedules are not imported (different systems)
- **BTRFS Snapshots**: Cannot import existing BTRFS snapshots
- **System Restore**: TimeLocker focuses on file restoration, not full system restore
- **Incremental Logic**: Different incremental backup approaches

## Example Timeshift Configuration

```json
{
  "backup_device_uuid": "12345678-1234-1234-1234-123456789abc",
  "btrfs_mode": "false",
  "exclude": [
    "/home/*/.cache",
    "/tmp",
    "/var/tmp",
    "/var/log"
  ],
  "exclude-apps": [
    "/home/*/.mozilla/firefox/*/Cache",
    "/home/*/.cache/google-chrome"
  ],
  "schedule_daily": "true",
  "count_daily": "7"
}
```

This would be imported as:

- Repository: `timeshift_imported` at resolved UUID path
- Target: `timeshift_system` with system paths
- Excludes: All patterns converted to TimeLocker format

## See Also

- [Configuration Management](Configuration-Management.md)
- [Repository Management](Repository-Management.md)
- [Backup Targets](Backup-Targets.md)
- [CLI Reference](CLI-Reference.md)
