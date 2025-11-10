# Recovery Operations Troubleshooting Guide

**Audience**: End Users and System Administrators  
**Level**: Intermediate to Advanced  
**Last Updated**: 2025-11-10

## Overview

This guide provides detailed troubleshooting steps for common issues encountered during recovery operations in TimeLocker. Each issue includes symptoms, causes, and step-by-step solutions.

## Table of Contents

- [Snapshot Issues](#snapshot-issues)
- [Permission and Access Issues](#permission-and-access-issues)
- [Storage and Space Issues](#storage-and-space-issues)
- [Performance Issues](#performance-issues)
- [Verification and Integrity Issues](#verification-and-integrity-issues)
- [Network and Connectivity Issues](#network-and-connectivity-issues)
- [Recovery Operation Issues](#recovery-operation-issues)
- [Data Corruption Issues](#data-corruption-issues)

## Snapshot Issues

### Snapshot Not Found

**Symptoms**:
- Error: "Snapshot 'abc123' not found"
- Recovery operation fails immediately
- Snapshot ID not listed in repository

**Possible Causes**:
1. Incorrect snapshot ID
2. Snapshot deleted or expired
3. Repository not accessible
4. Wrong repository specified

**Diagnostic Steps**:

```bash
# 1. List all available snapshots
timelocker snapshot list --repository my-backup

# 2. Verify repository access
timelocker repository check my-backup

# 3. Check snapshot with similar ID
timelocker snapshot list --repository my-backup | grep abc

# 4. Check repository configuration
timelocker repository info my-backup
```

**Solutions**:

```bash
# Solution 1: Use correct snapshot ID
timelocker snapshot list --repository my-backup
timelocker restore full <correct-snapshot-id> --target /restore/backup

# Solution 2: Use latest snapshot
timelocker restore full --latest --repository my-backup --target /restore/backup

# Solution 3: Search by date
timelocker snapshot list --repository my-backup --date "2025-11-09"
timelocker restore full <snapshot-id> --target /restore/backup

# Solution 4: Verify repository credentials
timelocker repository check my-backup --verbose
```

### Snapshot Corrupted or Incomplete

**Symptoms**:
- Error: "Snapshot integrity check failed"
- Missing files during restoration
- Checksum mismatches

**Diagnostic Steps**:

```bash
# 1. Verify snapshot integrity
timelocker snapshot verify abc123

# 2. Check snapshot metadata
timelocker snapshot info abc123 --verbose

# 3. Compare with other snapshots
timelocker snapshot list --repository my-backup

# 4. Check repository integrity
timelocker repository check my-backup --full
```

**Solutions**:

```bash
# Solution 1: Use different snapshot
timelocker snapshot list --before "2025-11-09"
timelocker restore full <alternative-snapshot> --target /restore/backup

# Solution 2: Repair repository (if supported)
timelocker repository repair my-backup

# Solution 3: Selective recovery of valid files
timelocker restore selective abc123 --target /restore/partial \
  --continue-on-error --verify

# Solution 4: Contact backup administrator
# Document the issue and snapshot ID for investigation
```

## Permission and Access Issues

### Permission Denied on Target Path

**Symptoms**:
- Error: "Permission denied: /restore/backup"
- Cannot create target directory
- Cannot write files to target

**Diagnostic Steps**:

```bash
# 1. Check target directory permissions
ls -ld /restore/backup

# 2. Check parent directory permissions
ls -ld /restore

# 3. Check current user permissions
id
groups

# 4. Check filesystem mount options
mount | grep /restore
```

**Solutions**:

```bash
# Solution 1: Create directory with proper permissions
mkdir -p /restore/backup
chmod 755 /restore/backup

# Solution 2: Change ownership
sudo chown $USER:$USER /restore/backup

# Solution 3: Run with elevated privileges
sudo timelocker restore full abc123 --target /restore/backup

# Solution 4: Use alternative target path
timelocker restore full abc123 --target ~/restore/backup

# Solution 5: Adjust umask
umask 022
timelocker restore full abc123 --target /restore/backup
```

### Repository Access Denied

**Symptoms**:
- Error: "Access denied to repository"
- Authentication failures
- Cannot list snapshots

**Diagnostic Steps**:

```bash
# 1. Check repository credentials
timelocker repository info my-backup

# 2. Test repository access
timelocker repository check my-backup

# 3. Verify credentials in keyring
timelocker credential show my-backup

# 4. Check repository URL
timelocker repository list
```

**Solutions**:

```bash
# Solution 1: Update repository credentials
timelocker credential store my-backup

# Solution 2: Re-authenticate
timelocker repository auth my-backup

# Solution 3: Check repository URL
timelocker repository info my-backup
timelocker repository update my-backup --url <correct-url>

# Solution 4: Verify network access (for remote repositories)
ping repository-host
telnet repository-host 22
```

## Storage and Space Issues

### Insufficient Disk Space

**Symptoms**:
- Error: "No space left on device"
- Recovery fails partway through
- System becomes unresponsive

**Diagnostic Steps**:

```bash
# 1. Check available space
df -h /restore

# 2. Check inode usage
df -i /restore

# 3. Estimate required space
timelocker snapshot info abc123 --size

# 4. Check for large files
du -sh /restore/*
```

**Solutions**:

```bash
# Solution 1: Clean up space
rm -rf /restore/old-data
df -h /restore

# Solution 2: Use different target location
df -h
timelocker restore full abc123 --target /mnt/large-disk/restore

# Solution 3: Selective recovery
timelocker restore selective abc123 --target /restore/critical \
  --include "/critical/data/**"

# Solution 4: Compress during recovery (if supported)
timelocker restore full abc123 --target /restore/backup --compress

# Solution 5: Split recovery into parts
timelocker restore selective abc123 --target /restore/part1 \
  --include "/data/part1/**"
# Clean up and continue with next part
```

### Disk I/O Errors

**Symptoms**:
- Error: "Input/output error"
- Recovery hangs or fails randomly
- System logs show disk errors

**Diagnostic Steps**:

```bash
# 1. Check system logs
dmesg | grep -i error
journalctl -xe | grep -i "i/o"

# 2. Check disk health
sudo smartctl -a /dev/sda

# 3. Check filesystem
sudo fsck -n /dev/sda1

# 4. Monitor I/O
iostat -x 5
```

**Solutions**:

```bash
# Solution 1: Use different target disk
timelocker restore full abc123 --target /mnt/backup-disk/restore

# Solution 2: Repair filesystem
sudo umount /restore
sudo fsck -y /dev/sda1
sudo mount /restore

# Solution 3: Reduce I/O load
# Stop other disk-intensive processes
timelocker restore full abc123 --target /restore/backup --max-retries 10

# Solution 4: Contact system administrator
# Document errors and disk information
```

## Performance Issues

### Slow Recovery Speed

**Symptoms**:
- Recovery taking much longer than expected
- Low transfer rates
- High CPU or disk usage

**Diagnostic Steps**:

```bash
# 1. Check recovery status
timelocker restore status recovery-001 --verbose

# 2. Monitor system resources
top
htop
iostat -x 5

# 3. Check network speed (for remote repositories)
iperf3 -c repository-host

# 4. Check disk performance
hdparm -t /dev/sda
```

**Solutions**:

```bash
# Solution 1: Use selective recovery
timelocker restore selective abc123 --target /restore/specific \
  --include "/specific/path/**"

# Solution 2: Reduce concurrent operations
# Stop other backup/restore operations
timelocker restore list
timelocker restore cancel <other-operation-id>

# Solution 3: Optimize network settings (for remote repositories)
# Adjust TCP window size, enable compression
timelocker restore full abc123 --target /restore/backup \
  --network-optimize

# Solution 4: Use local cache (if available)
timelocker restore full abc123 --target /restore/backup \
  --use-cache

# Solution 5: Schedule during off-peak hours
# Use cron or systemd timer for large recoveries
```

### High Memory Usage

**Symptoms**:
- System running out of memory
- Recovery process killed by OOM killer
- System becomes unresponsive

**Diagnostic Steps**:

```bash
# 1. Check memory usage
free -h
top -o %MEM

# 2. Check recovery process memory
ps aux | grep timelocker

# 3. Check system logs
dmesg | grep -i "out of memory"
journalctl -xe | grep -i oom

# 4. Check swap usage
swapon --show
```

**Solutions**:

```bash
# Solution 1: Increase swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Solution 2: Use pagination for browsing
timelocker snapshot browse abc123 --page-size 100

# Solution 3: Disable caching
timelocker restore full abc123 --target /restore/backup --no-cache

# Solution 4: Split recovery into smaller operations
timelocker restore selective abc123 --target /restore/part1 \
  --include "/data/part1/**"

# Solution 5: Close other applications
# Free up memory before starting recovery
```

## Verification and Integrity Issues

### Checksum Mismatch

**Symptoms**:
- Error: "Checksum mismatch for file"
- Verification failures
- Files marked as corrupted

**Diagnostic Steps**:

```bash
# 1. Check verification report
timelocker restore verify recovery-001 --report report.json
cat report.json | jq '.failed_validations'

# 2. Verify specific file
timelocker restore verify recovery-001 --path /restore/backup/file.txt

# 3. Check snapshot integrity
timelocker snapshot verify abc123

# 4. Compare with original
timelocker snapshot info abc123 --file /path/to/file.txt
```

**Solutions**:

```bash
# Solution 1: Retry failed files
timelocker restore retry recovery-001 --failed-only

# Solution 2: Re-verify after retry
timelocker restore verify recovery-001

# Solution 3: Restore from different snapshot
timelocker snapshot list --before "2025-11-09"
timelocker restore full <alternative-snapshot> --target /restore/backup

# Solution 4: Restore without verification (use with caution)
timelocker restore full abc123 --target /restore/backup --no-verify

# Solution 5: Report issue
# Document snapshot ID, file paths, and checksums
```

### Incomplete Restoration

**Symptoms**:
- Not all files restored
- Missing directories
- Partial file restoration

**Diagnostic Steps**:

```bash
# 1. Check recovery status
timelocker restore status recovery-001 --verbose

# 2. Compare file counts
timelocker snapshot info abc123 --file-count
find /restore/backup -type f | wc -l

# 3. Check for errors
timelocker restore status recovery-001 --errors

# 4. Review recovery log
tail -n 100 /var/log/timelocker/recovery.log
```

**Solutions**:

```bash
# Solution 1: Resume recovery
timelocker restore resume recovery-001

# Solution 2: Retry with continue-on-error
timelocker restore full abc123 --target /restore/backup \
  --continue-on-error --max-retries 5

# Solution 3: Identify missing files
timelocker restore diff recovery-001 --report missing-files.txt

# Solution 4: Restore missing files separately
timelocker restore selective abc123 --target /restore/backup \
  --include-from missing-files.txt

# Solution 5: Start fresh recovery
rm -rf /restore/backup
timelocker restore full abc123 --target /restore/backup --verify
```

## Network and Connectivity Issues

### Network Timeout

**Symptoms**:
- Error: "Connection timed out"
- Recovery fails during transfer
- Intermittent connectivity

**Diagnostic Steps**:

```bash
# 1. Check network connectivity
ping repository-host
traceroute repository-host

# 2. Check DNS resolution
nslookup repository-host
dig repository-host

# 3. Test repository connection
timelocker repository check my-backup --verbose

# 4. Check firewall rules
sudo iptables -L
sudo firewall-cmd --list-all
```

**Solutions**:

```bash
# Solution 1: Increase timeout
timelocker restore full abc123 --target /restore/backup \
  --timeout 300

# Solution 2: Enable retry on network errors
timelocker restore full abc123 --target /restore/backup \
  --max-retries 10 --retry-delay 30

# Solution 3: Use VPN or alternative network
# Connect to VPN
timelocker restore full abc123 --target /restore/backup

# Solution 4: Check proxy settings
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
timelocker restore full abc123 --target /restore/backup

# Solution 5: Resume after network recovery
timelocker restore resume recovery-001
```

### SSL/TLS Certificate Errors

**Symptoms**:
- Error: "SSL certificate verification failed"
- Cannot connect to remote repository
- Certificate warnings

**Diagnostic Steps**:

```bash
# 1. Check certificate
openssl s_client -connect repository-host:443

# 2. Verify certificate chain
curl -v https://repository-host

# 3. Check system certificates
ls /etc/ssl/certs/

# 4. Test with certificate verification disabled
timelocker repository check my-backup --no-verify-ssl
```

**Solutions**:

```bash
# Solution 1: Update CA certificates
sudo update-ca-certificates

# Solution 2: Add custom certificate
sudo cp custom-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# Solution 3: Specify certificate path
timelocker restore full abc123 --target /restore/backup \
  --ca-cert /path/to/ca-cert.pem

# Solution 4: Disable SSL verification (not recommended for production)
timelocker restore full abc123 --target /restore/backup \
  --no-verify-ssl

# Solution 5: Contact repository administrator
# Request valid SSL certificate
```

## Recovery Operation Issues

### Operation Stuck or Hanging

**Symptoms**:
- Recovery operation not progressing
- No progress updates
- Process appears frozen

**Diagnostic Steps**:

```bash
# 1. Check operation status
timelocker restore status recovery-001 --verbose

# 2. Check process status
ps aux | grep timelocker
top -p <pid>

# 3. Check system resources
df -h
free -h
iostat -x 5

# 4. Check for deadlocks
strace -p <pid>
```

**Solutions**:

```bash
# Solution 1: Wait for timeout
# Some operations may take time, especially for large files

# Solution 2: Cancel and restart
timelocker restore cancel recovery-001
timelocker restore full abc123 --target /restore/backup

# Solution 3: Kill and cleanup
kill -9 <pid>
timelocker restore cleanup recovery-001
timelocker restore full abc123 --target /restore/backup

# Solution 4: Check for resource contention
# Stop other processes
timelocker restore full abc123 --target /restore/backup

# Solution 5: Restart TimeLocker service
sudo systemctl restart timelocker
timelocker restore full abc123 --target /restore/backup
```

### Cannot Cancel Operation

**Symptoms**:
- Cancel command has no effect
- Operation continues running
- Cannot start new operations

**Diagnostic Steps**:

```bash
# 1. Check operation status
timelocker restore status recovery-001

# 2. Check process
ps aux | grep timelocker

# 3. Check for locks
lsof | grep timelocker

# 4. Check system logs
journalctl -u timelocker -n 100
```

**Solutions**:

```bash
# Solution 1: Force cancel
timelocker restore cancel recovery-001 --force

# Solution 2: Kill process
kill -TERM <pid>
# Wait a few seconds
kill -KILL <pid>

# Solution 3: Cleanup operation
timelocker restore cleanup recovery-001 --force

# Solution 4: Restart service
sudo systemctl restart timelocker

# Solution 5: Manual cleanup
rm -rf /var/lib/timelocker/operations/recovery-001
```

## Data Corruption Issues

### Corrupted Files After Recovery

**Symptoms**:
- Files cannot be opened
- Application errors when accessing files
- Checksum verification passes but files are corrupted

**Diagnostic Steps**:

```bash
# 1. Verify file integrity
timelocker restore verify recovery-001 --path /restore/backup/file.txt

# 2. Compare with snapshot
timelocker snapshot info abc123 --file /path/to/file.txt

# 3. Check file permissions
ls -l /restore/backup/file.txt

# 4. Try opening file
file /restore/backup/file.txt
hexdump -C /restore/backup/file.txt | head
```

**Solutions**:

```bash
# Solution 1: Restore file again
timelocker restore selective abc123 --target /restore/backup \
  --include "/path/to/file.txt" --overwrite

# Solution 2: Restore from different snapshot
timelocker snapshot list --before "2025-11-09"
timelocker restore selective <snapshot> --target /restore/backup \
  --include "/path/to/file.txt"

# Solution 3: Check snapshot integrity
timelocker snapshot verify abc123
# If snapshot is corrupted, use different snapshot

# Solution 4: Restore to different location
timelocker restore selective abc123 --target /restore/test \
  --include "/path/to/file.txt"
# Compare files

# Solution 5: Report issue
# Document snapshot ID, file path, and corruption details
```

## Getting Help

If you cannot resolve an issue using this guide:

1. **Check logs**: Review TimeLocker logs for detailed error messages
   ```bash
   tail -n 100 /var/log/timelocker/recovery.log
   journalctl -u timelocker -n 100
   ```

2. **Gather diagnostic information**:
   ```bash
   timelocker diagnostic --output diagnostic-report.txt
   ```

3. **Search documentation**: Check other guides and API reference

4. **Contact support**: Provide diagnostic information and detailed description

5. **Report bugs**: If you've found a bug, report it with:
   - TimeLocker version
   - Operating system and version
   - Detailed steps to reproduce
   - Error messages and logs
   - Diagnostic report

## See Also

- [Recovery Operations User Guide](recovery-operations-guide.md)
- [Recovery Operations API Reference](../../reference/recovery-operations-api.md)
- [Backup Operations Troubleshooting](backup-operations-troubleshooting.md)
- [Repository Management Guide](repository-management-guide.md)
