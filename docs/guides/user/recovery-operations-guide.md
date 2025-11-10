# Recovery Operations User Guide

**Audience**: End Users  
**Level**: Beginner to Advanced  
**Last Updated**: 2025-11-10

## Overview

This guide explains how to use TimeLocker's recovery operations to restore data from backup snapshots. Whether you need to recover a single file or restore an entire backup, this guide will walk you through the process.

## Table of Contents

- [Getting Started](#getting-started)
- [Browsing Snapshots](#browsing-snapshots)
- [Full Recovery](#full-recovery)
- [Selective Recovery](#selective-recovery)
- [Monitoring Recovery Progress](#monitoring-recovery-progress)
- [Verifying Restored Data](#verifying-restored-data)
- [Common Scenarios](#common-scenarios)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

Before performing recovery operations, ensure you have:

1. Access to a repository containing backup snapshots
2. Sufficient disk space at the target location
3. Appropriate permissions to write to the target location
4. The snapshot ID or criteria to identify the snapshot to restore

### Basic Concepts

- **Snapshot**: A point-in-time backup containing files and metadata
- **Full Recovery**: Restoring all files from a snapshot
- **Selective Recovery**: Restoring only specific files or directories
- **Target Path**: The location where restored files will be placed
- **Verification**: Checking that restored files match the original backup data

## Browsing Snapshots

Before restoring data, you can browse snapshot contents to identify what you need to recover.

### Listing Available Snapshots

```bash
# List all snapshots in a repository
timelocker snapshot list --repository my-backup

# List snapshots with specific tags
timelocker snapshot list --repository my-backup --tag full

# List recent snapshots
timelocker snapshot list --repository my-backup --last 7d
```

### Exploring Snapshot Contents

```bash
# Browse snapshot root directory
timelocker snapshot browse abc123

# Browse specific path in snapshot
timelocker snapshot browse abc123 --path /home/user/documents

# Search for files in snapshot
timelocker snapshot search abc123 --pattern "*.pdf"

# Search with size filter
timelocker snapshot search abc123 --pattern "*.jpg" --min-size 1M --max-size 10M
```

### Comparing Snapshots

```bash
# Compare two snapshots
timelocker snapshot compare abc123 def456

# Compare specific path across snapshots
timelocker snapshot compare abc123 def456 --path /home/user/documents
```

## Full Recovery

Full recovery restores all files from a snapshot to a target location.

### Basic Full Recovery

```bash
# Restore entire snapshot to target directory
timelocker restore full abc123 --target /restore/backup

# Restore with verification
timelocker restore full abc123 --target /restore/backup --verify

# Restore preserving permissions and timestamps
timelocker restore full abc123 --target /restore/backup --preserve-all
```

### Full Recovery Options

```bash
# Overwrite existing files
timelocker restore full abc123 --target /restore/backup --overwrite

# Skip existing files
timelocker restore full abc123 --target /restore/backup --skip-existing

# Rename conflicting files
timelocker restore full abc123 --target /restore/backup --rename-conflicts

# Continue on errors
timelocker restore full abc123 --target /restore/backup --continue-on-error

# Set maximum retries
timelocker restore full abc123 --target /restore/backup --max-retries 5
```

### Restoring to Original Location

```bash
# Restore to original paths (use with caution!)
timelocker restore full abc123 --target / --original-paths

# Dry run to preview what would be restored
timelocker restore full abc123 --target / --original-paths --dry-run
```

## Selective Recovery

Selective recovery allows you to restore only specific files or directories.

### Pattern-Based Selection

```bash
# Restore only PDF files
timelocker restore selective abc123 --target /restore/docs \
  --include "*.pdf"

# Restore multiple file types
timelocker restore selective abc123 --target /restore/docs \
  --include "*.pdf" --include "*.docx" --include "*.xlsx"

# Restore with exclusions
timelocker restore selective abc123 --target /restore/data \
  --include "**/*" --exclude "*/temp/*" --exclude "*.tmp"

# Restore specific directory tree
timelocker restore selective abc123 --target /restore/projects \
  --include "/home/user/projects/**" --exclude "**/node_modules/**"
```

### Size and Date Filtering

```bash
# Restore files within size range
timelocker restore selective abc123 --target /restore/files \
  --min-size 1K --max-size 10M

# Restore recently modified files
timelocker restore selective abc123 --target /restore/recent \
  --modified-after "30 days ago"

# Restore files from date range
timelocker restore selective abc123 --target /restore/range \
  --modified-after "2025-01-01" --modified-before "2025-03-31"

# Combined filters
timelocker restore selective abc123 --target /restore/filtered \
  --include "*.jpg" --min-size 1M --modified-after "7 days ago"
```

### Using Selection Templates

```bash
# List available templates
timelocker selection template list

# Restore using template
timelocker restore selective abc123 --target /restore/docs \
  --template documents

# Restore using template with additional patterns
timelocker restore selective abc123 --target /restore/docs \
  --template documents --include "*.odt"
```

## Monitoring Recovery Progress

### Real-Time Progress Display

```bash
# Restore with progress display
timelocker restore full abc123 --target /restore/backup --progress

# Restore with detailed progress
timelocker restore full abc123 --target /restore/backup --progress --verbose
```

### Checking Recovery Status

```bash
# List active recovery operations
timelocker restore status

# Check specific operation status
timelocker restore status recovery-001

# Monitor operation until completion
timelocker restore status recovery-001 --follow
```

### Cancelling Recovery Operations

```bash
# Cancel a running recovery operation
timelocker restore cancel recovery-001

# Cancel with cleanup
timelocker restore cancel recovery-001 --cleanup
```

## Verifying Restored Data

### Automatic Verification

```bash
# Restore with automatic verification
timelocker restore full abc123 --target /restore/backup --verify

# Verify during restoration
timelocker restore full abc123 --target /restore/backup --verify-during
```

### Manual Verification

```bash
# Verify completed recovery operation
timelocker restore verify recovery-001

# Verify specific files
timelocker restore verify recovery-001 --path /restore/backup/file.txt

# Generate verification report
timelocker restore verify recovery-001 --report verification-report.json
```

### Handling Verification Failures

```bash
# Retry failed files
timelocker restore retry recovery-001 --failed-only

# Re-verify after retry
timelocker restore verify recovery-001
```

## Common Scenarios

### Scenario 1: Recovering Deleted Files

```bash
# 1. Find the snapshot before deletion
timelocker snapshot list --before "2025-11-09"

# 2. Browse snapshot to locate files
timelocker snapshot browse abc123 --path /home/user/documents

# 3. Restore deleted files
timelocker restore selective abc123 --target /restore/recovered \
  --include "/home/user/documents/deleted-file.txt"
```

### Scenario 2: Disaster Recovery

```bash
# 1. Identify latest good snapshot
timelocker snapshot list --last 1

# 2. Verify snapshot integrity
timelocker snapshot verify abc123

# 3. Perform full recovery with verification
timelocker restore full abc123 --target /restore/system \
  --verify --preserve-all --continue-on-error

# 4. Monitor progress
timelocker restore status --follow

# 5. Verify restoration
timelocker restore verify recovery-001 --report disaster-recovery-report.json
```

### Scenario 3: Recovering Specific File Versions

```bash
# 1. Compare snapshots to find version
timelocker snapshot compare abc123 def456 --path /home/user/document.txt

# 2. Browse older snapshot
timelocker snapshot browse abc123 --path /home/user

# 3. Restore specific version
timelocker restore selective abc123 --target /restore/versions \
  --include "/home/user/document.txt"
```

### Scenario 4: Recovering Large Datasets

```bash
# 1. Check available space
df -h /restore

# 2. Estimate recovery size
timelocker snapshot info abc123 --size

# 3. Perform recovery with progress monitoring
timelocker restore full abc123 --target /restore/large-dataset \
  --progress --verify --max-retries 5

# 4. Monitor in separate terminal
watch -n 5 'timelocker restore status recovery-001'
```

### Scenario 5: Selective Document Recovery

```bash
# 1. Search for documents in snapshot
timelocker snapshot search abc123 --pattern "*.pdf" --pattern "*.docx"

# 2. Preview what will be restored
timelocker restore selective abc123 --target /restore/docs \
  --include "*.pdf" --include "*.docx" --dry-run

# 3. Perform selective recovery
timelocker restore selective abc123 --target /restore/docs \
  --include "*.pdf" --include "*.docx" --verify
```

## Troubleshooting

### Issue: Snapshot Not Found

**Symptoms**: Error message "Snapshot not found"

**Solutions**:
```bash
# Verify snapshot exists
timelocker snapshot list --repository my-backup

# Check snapshot ID
timelocker snapshot info abc123

# Verify repository access
timelocker repository check my-backup
```

### Issue: Permission Denied

**Symptoms**: Error message "Permission denied" when restoring

**Solutions**:
```bash
# Check target directory permissions
ls -ld /restore/backup

# Create target directory with proper permissions
mkdir -p /restore/backup
chmod 755 /restore/backup

# Run with appropriate user permissions
sudo timelocker restore full abc123 --target /restore/backup
```

### Issue: Insufficient Disk Space

**Symptoms**: Recovery fails with "No space left on device"

**Solutions**:
```bash
# Check available space
df -h /restore

# Estimate required space
timelocker snapshot info abc123 --size

# Use selective recovery to restore less data
timelocker restore selective abc123 --target /restore/partial \
  --include "/critical/data/**"

# Clean up space and retry
rm -rf /restore/old-data
timelocker restore retry recovery-001
```

### Issue: Slow Recovery Performance

**Symptoms**: Recovery is taking longer than expected

**Solutions**:
```bash
# Check transfer rate
timelocker restore status recovery-001 --verbose

# Use selective recovery for specific files
timelocker restore selective abc123 --target /restore/specific \
  --include "/specific/path/**"

# Check network connectivity (for remote repositories)
ping repository-host

# Monitor system resources
top
iostat -x 5
```

### Issue: Verification Failures

**Symptoms**: Files fail integrity verification

**Solutions**:
```bash
# Check verification report
timelocker restore verify recovery-001 --report report.json
cat report.json

# Retry failed files
timelocker restore retry recovery-001 --failed-only

# Verify snapshot integrity
timelocker snapshot verify abc123

# Try different snapshot
timelocker snapshot list --before "2025-11-09"
timelocker restore full def456 --target /restore/backup --verify
```

### Issue: Recovery Operation Stuck

**Symptoms**: Recovery operation appears to hang

**Solutions**:
```bash
# Check operation status
timelocker restore status recovery-001 --verbose

# Check system resources
top
df -h

# Cancel and retry
timelocker restore cancel recovery-001
timelocker restore full abc123 --target /restore/backup --max-retries 5

# Check logs
tail -f /var/log/timelocker/recovery.log
```

## Best Practices

### Before Recovery

1. **Verify snapshot integrity** before starting recovery
2. **Check available disk space** at target location
3. **Test with dry run** for large recoveries
4. **Browse snapshot contents** to verify what will be restored
5. **Plan target location** to avoid conflicts

### During Recovery

1. **Monitor progress** regularly
2. **Check system resources** (disk space, memory, network)
3. **Keep recovery logs** for troubleshooting
4. **Avoid interrupting** recovery operations
5. **Use continue-on-error** for large recoveries

### After Recovery

1. **Verify restored data** integrity
2. **Check file permissions** and ownership
3. **Review verification report** for any issues
4. **Test restored files** before deleting originals
5. **Document recovery** for future reference

## Advanced Topics

### Scripting Recovery Operations

```bash
#!/bin/bash
# Automated recovery script

SNAPSHOT_ID="abc123"
TARGET="/restore/backup"
LOG_FILE="/var/log/recovery-$(date +%Y%m%d-%H%M%S).log"

# Pre-recovery checks
echo "Starting recovery at $(date)" | tee -a "$LOG_FILE"
timelocker snapshot verify "$SNAPSHOT_ID" | tee -a "$LOG_FILE"

# Perform recovery
timelocker restore full "$SNAPSHOT_ID" --target "$TARGET" \
  --verify --preserve-all --continue-on-error \
  2>&1 | tee -a "$LOG_FILE"

# Post-recovery verification
timelocker restore verify recovery-001 --report report.json \
  2>&1 | tee -a "$LOG_FILE"

echo "Recovery completed at $(date)" | tee -a "$LOG_FILE"
```

### Parallel Recovery

For large datasets, consider splitting recovery into parallel operations:

```bash
# Recover different directories in parallel
timelocker restore selective abc123 --target /restore/dir1 \
  --include "/data/dir1/**" &

timelocker restore selective abc123 --target /restore/dir2 \
  --include "/data/dir2/**" &

timelocker restore selective abc123 --target /restore/dir3 \
  --include "/data/dir3/**" &

# Wait for all to complete
wait
```

## See Also

- [Recovery Operations API Reference](../../reference/recovery-operations-api.md)
- [Recovery Operations Models Reference](../../reference/recovery-operations-models-reference.md)
- [Backup Operations User Guide](backup-operations-guide.md)
- [Repository Management Guide](repository-management-guide.md)
- [Recovery Operations Troubleshooting](recovery-operations-troubleshooting.md)
