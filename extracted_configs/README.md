# Extracted Restic Configuration for TimeLocker

This directory contains the extracted restic/npbackup configuration that has been converted for use with TimeLocker.

## Files

- `restic_config.json` - Main configuration file extracted from the existing restic/npbackup setup
- `set_environment.sh` - Script to set up environment variables for testing
- `README.md` - This documentation file

## Configuration Summary

### Repository Information

- **Type**: AWS S3
- **URI**: `s3:s3.af-south-1.amazonaws.com/5560-restic`
- **Region**: `af-south-1`
- **Encryption**: Enabled

### Backup Targets

- **Paths**: 6 directories
    - `/home`
    - `/etc`
    - `/var`
    - `/srv`
    - `/root`
    - `/nix/var`
- **Exclude Patterns**: 261 patterns from npbackup configuration

### Backup Settings

- **Compression**: max
- **One File System**: true
- **Retention Policy**:
    - Last: 5 snapshots
    - Daily: 7 snapshots
    - Weekly: 4 snapshots
    - Monthly: 3 snapshots

### Original Scheduling

- **Cron Schedule**: `30 17 * * *` (Daily at 17:30)
- **Command**:
  `/opt/npbackup/npbackup-gui/npbackup-gui -c /var/restic/.config/npbackup/npbackup.conf --backup --run-as-cli --repo-name default --log-file /var/log/npbackup-gui-cron.log --force`

## Quick Start

### 1. Set up environment variables

```bash
source extracted_configs/set_environment.sh
```

### 2. Test repository connection

```bash
restic snapshots --latest 1
```

### 3. Validate extracted configuration

```bash
python3 scripts/validate_extracted_config.py extracted_configs/restic_config.json
```

### 4. Import into TimeLocker

```bash
python3 scripts/import_to_timelocker.py extracted_configs/restic_config.json
```

## Security Notes

⚠️ **Important Security Information**:

- The configuration files contain sensitive credentials (AWS keys, repository password)
- File permissions are set to 600 (owner read/write only)
- Original configurations backed up to `/tmp/restic_config_backup_*`
- Do not commit these files to version control

## Migration Strategy

### Option A: Parallel Operation (Recommended for testing)

1. Keep existing npbackup cron job running
2. Import configuration into TimeLocker
3. Test TimeLocker operations manually
4. Once confident, disable npbackup cron job
5. Set up TimeLocker scheduling

### Option B: Direct Migration

1. Disable existing npbackup cron job
2. Import configuration into TimeLocker
3. Set up TimeLocker scheduling immediately
4. Monitor for issues

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   sudo chown $USER:$USER extracted_configs/restic_config.json
   ```

2. **Repository Connection Failed**
    - Verify AWS credentials are set as environment variables
    - Check network connectivity to S3
    - Ensure repository password is correct

3. **Import Fails**
    - Check TimeLocker installation
    - Verify Python path includes TimeLocker modules
    - Ensure credential manager master password is correct

## Support

If you encounter issues:

1. Check the validation output for specific error messages
2. Verify all prerequisites are installed
3. Review the TimeLocker documentation
4. Test repository access manually with restic commands

---

**Generated**: 2025-06-29T15:37:54.770690  
**Source**: NPBackup v3.0 configuration  
**Extraction Tool**: TimeLocker Configuration Extractor
