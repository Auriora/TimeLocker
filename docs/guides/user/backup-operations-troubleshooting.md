# Backup Operations Troubleshooting Guide

**Status**: Active  
**Last Updated**: 2025-11-09  
**Audience**: Users and administrators

## Overview

This guide helps you diagnose and resolve common issues with TimeLocker's backup operations. It covers error messages, performance problems, and configuration issues.

## Quick Diagnostic Checklist

Before diving into specific issues, run through this checklist:

- [ ] Is the backup tool (Restic, Borg, etc.) installed and accessible?
- [ ] Is the repository accessible and properly initialized?
- [ ] Are credentials configured correctly?
- [ ] Is there sufficient disk space on source and destination?
- [ ] Are network connections stable (for remote repositories)?
- [ ] Are file permissions correct for source files?
- [ ] Is the backup policy configuration valid?
- [ ] Are data selection rules properly configured?

## Common Error Messages

### Backup Execution Errors

#### Error: "Backup tool not found"

```
ToolNotAvailableError: Backup tool not found at: /usr/bin/restic
```

**Cause**: The backup tool executable is not installed or not at the expected location.

**Solutions**:

1. **Verify Installation**:
   ```bash
   which restic
   # or
   which borg
   ```

2. **Install Missing Tool**:
   ```bash
   # For Restic
   sudo apt install restic
   # or download from https://restic.net
   
   # For Borg
   sudo apt install borgbackup
   ```

3. **Configure Tool Path**:
   ```python
   # In configuration
   tool_manager.set_tool_path("restic", "/custom/path/to/restic")
   ```

#### Error: "Repository not accessible"

```
BackupExecutionError: Repository not accessible: s3:backup-bucket/repo
```

**Cause**: Repository cannot be reached or credentials are invalid.

**Solutions**:

1. **Check Repository Connectivity**:
   ```bash
   # For S3 repositories
   aws s3 ls s3://backup-bucket/
   
   # For local repositories
   ls -la /path/to/repository
   ```

2. **Verify Credentials**:
   ```python
   # Check credential configuration
   credential_manager.list_credentials()
   
   # Test repository access
   repository.validate_repository()
   ```

3. **Check Network**:
   ```bash
   # Test network connectivity
   ping backup-server.example.com
   
   # Check firewall rules
   sudo iptables -L
   ```

#### Error: "Insufficient disk space"

```
BackupExecutionError: Insufficient disk space on repository
```

**Cause**: Not enough space available on the backup destination.

**Solutions**:

1. **Check Available Space**:
   ```bash
   df -h /path/to/repository
   ```

2. **Clean Up Old Snapshots**:
   ```python
   # Apply retention policy
   repository.apply_retention_policy(
       keep_daily=7,
       keep_weekly=4,
       keep_monthly=6
   )
   ```

3. **Prune Repository**:
   ```bash
   restic -r /path/to/repo prune
   ```

### Validation Errors

#### Error: "Invalid job configuration"

```
ValidationError: Invalid job configuration: missing required field 'repository_id'
```

**Cause**: Backup job configuration is incomplete or invalid.

**Solutions**:

1. **Check Required Fields**:
   ```python
   config = BackupJobConfig(
       job_id="backup-001",           # Required
       policy_id="daily-backup",      # Required
       repository_id="main-repo",     # Required
       data_selection_id="docs",      # Required
       tool_type="restic",            # Required
       execution_mode=ExecutionMode.ON_DEMAND,
       retry_config=RetryConfig(),
       notification_config=NotificationConfig()
   )
   ```

2. **Validate Before Execution**:
   ```python
   validation_result = orchestrator.validate_job_configuration(config)
   if not validation_result.is_valid:
       for error in validation_result.errors:
           print(f"Validation error: {error}")
   ```

#### Error: "Data selection rules incompatible with tool"

```
ValidationError: Data selection rules incompatible with backup tool 'borg'
```

**Cause**: Some data selection rules cannot be translated to the target backup tool's format.

**Solutions**:

1. **Check Tool Capabilities**:
   ```python
   capabilities = tool_manager.get_tool_capabilities("borg")
   print(f"Supported features: {capabilities.native_features}")
   ```

2. **Simplify Selection Rules**:
   ```python
   # Use basic patterns supported by all tools
   selection = FileSelection()
   selection.add_path("/data", SelectionType.INCLUDE)
   selection.add_pattern("*.tmp", SelectionType.EXCLUDE)
   ```

3. **Use Compatible Tool**:
   ```python
   # Switch to tool with better selection support
   config.tool_type = "restic"  # Better pattern support
   ```

### Retry and Recovery Errors

#### Error: "Maximum retry attempts exceeded"

```
BackupExecutionError: Maximum retry attempts exceeded (3 attempts)
Last error: Connection timeout
```

**Cause**: Backup failed repeatedly, exhausting retry attempts.

**Solutions**:

1. **Check Error Type**:
   ```python
   # Review error log for root cause
   for error in result.errors:
       print(f"Attempt {error.attempt}: {error.message}")
   ```

2. **Increase Retry Limit**:
   ```python
   config.retry_config = RetryConfig(
       max_retries=5,
       base_delay=2,
       max_delay=60
   )
   ```

3. **Fix Underlying Issue**:
   - Network connectivity problems
   - Repository access issues
   - Resource constraints

4. **Manual Retry**:
   ```python
   # Retry with manual execution mode
   config.execution_mode = ExecutionMode.MANUAL_RETRY
   result = orchestrator.execute_backup_job(config)
   ```

## Performance Issues

### Slow Backup Speed

**Symptoms**: Backup takes much longer than expected.

**Diagnostic Steps**:

1. **Check Progress Metrics**:
   ```python
   status = orchestrator.get_execution_status(job_id)
   print(f"Throughput: {status.throughput / 1024 / 1024:.2f} MB/s")
   print(f"Files processed: {status.files_processed}")
   ```

2. **Review Performance Metrics**:
   ```python
   metrics = result.performance_metrics
   print(f"Average throughput: {metrics.avg_throughput_mbps:.2f} MB/s")
   print(f"CPU utilization: {metrics.avg_cpu_percent:.1f}%")
   print(f"Peak memory: {metrics.peak_memory_mb:.2f} MB")
   ```

**Solutions**:

1. **Enable Parallel Processing**:
   ```python
   # Check if tool supports parallelization
   if Feature.PARALLEL_PROCESSING in capabilities.native_features:
       config.parallel_operations = 4  # Adjust based on system
   ```

2. **Adjust Compression Level**:
   ```python
   # Lower compression for faster backups
   config.compression_level = 3  # Instead of 9
   ```

3. **Optimize Network Settings**:
   ```python
   # For remote repositories
   config.additional_options = {
       "connections": 5,
       "pack-size": 16  # MB
   }
   ```

4. **Exclude Unnecessary Files**:
   ```python
   # Add more exclude patterns
   selection.add_pattern("*.cache", SelectionType.EXCLUDE)
   selection.add_pattern("node_modules/*", SelectionType.EXCLUDE)
   selection.add_pattern(".git/*", SelectionType.EXCLUDE)
   ```

### High Memory Usage

**Symptoms**: Backup process consumes excessive memory.

**Diagnostic Steps**:

1. **Monitor Memory Usage**:
   ```python
   metrics = result.performance_metrics
   print(f"Peak memory: {metrics.peak_memory_mb:.2f} MB")
   print(f"Average memory: {metrics.avg_memory_mb:.2f} MB")
   ```

**Solutions**:

1. **Limit Parallel Operations**:
   ```python
   config.parallel_operations = 1  # Reduce parallelism
   ```

2. **Adjust Tool Settings**:
   ```python
   config.additional_options = {
       "pack-size": 4,  # Smaller pack size
       "cache-size": 256  # Limit cache size (MB)
   }
   ```

3. **Process in Batches**:
   ```python
   # Split large backup into smaller jobs
   for batch in source_batches:
       batch_config = create_batch_config(batch)
       result = orchestrator.execute_backup_job(batch_config)
   ```

### CPU Bottleneck

**Symptoms**: High CPU usage, slow backup progress.

**Solutions**:

1. **Reduce Compression**:
   ```python
   config.compression_level = 1  # Minimal compression
   ```

2. **Limit Parallelism**:
   ```python
   config.parallel_operations = 2  # Reduce from higher value
   ```

3. **Schedule During Off-Peak**:
   ```python
   # Run backups when system is less busy
   config.execution_mode = ExecutionMode.SCHEDULED
   ```

## Configuration Issues

### Policy Configuration Problems

#### Issue: Policy not found

**Error**:
```
PolicyNotFoundError: Policy 'daily-backup' not found
```

**Solutions**:

1. **List Available Policies**:
   ```python
   policies = policy_service.list_policies()
   for policy in policies:
       print(f"Policy: {policy.id} - {policy.name}")
   ```

2. **Create Missing Policy**:
   ```python
   policy = Policy(
       id="daily-backup",
       name="Daily Backup",
       schedule="0 2 * * *",
       retention=RetentionPolicy(keep_daily=7)
   )
   policy_service.create_policy(policy)
   ```

### Data Selection Issues

#### Issue: No files selected for backup

**Symptoms**: Backup completes but no files are processed.

**Diagnostic Steps**:

1. **Preview Selection**:
   ```python
   preview = selection_service.preview_selection(selection_id)
   print(f"Files to backup: {len(preview.files)}")
   for file in preview.files[:10]:
       print(f"  {file}")
   ```

2. **Check Selection Rules**:
   ```python
   selection = selection_service.get_selection(selection_id)
   print(f"Include paths: {selection.includes}")
   print(f"Exclude patterns: {selection.exclude_patterns}")
   ```

**Solutions**:

1. **Verify Include Paths**:
   ```python
   # Ensure paths exist and are accessible
   for path in selection.includes:
       if not path.exists():
           print(f"Warning: Path does not exist: {path}")
   ```

2. **Review Exclude Patterns**:
   ```python
   # Check if patterns are too broad
   selection.exclude_patterns = [
       "*.tmp",  # Specific extensions
       "*.log",
       # Remove overly broad patterns like "*"
   ]
   ```

3. **Test Selection**:
   ```python
   from TimeLocker.cli_services import CLIServiceManager

   cli = CLIServiceManager()
   cli.run_selection_backup(
       selection_name="documents",
       repository="local-repo",
       dry_run=True,
       cli_options={"tool_type": "restic"}
   )
   ```

## Tool-Specific Issues

### Restic Issues

#### Issue: Repository locked

**Error**:
```
unable to create lock in backend: repository is already locked
```

**Solutions**:

1. **Check for Running Processes**:
   ```bash
   ps aux | grep restic
   ```

2. **Remove Stale Lock** (if no process is running):
   ```bash
   restic -r /path/to/repo unlock
   ```

3. **Wait for Lock Release**:
   ```python
   # Implement lock wait in configuration
   config.additional_options = {
       "lock-wait": 300  # Wait up to 5 minutes
   }
   ```

#### Issue: Pack file corruption

**Error**:
```
pack file is corrupted: checksum mismatch
```

**Solutions**:

1. **Run Repository Check**:
   ```bash
   restic -r /path/to/repo check
   ```

2. **Rebuild Index**:
   ```bash
   restic -r /path/to/repo rebuild-index
   ```

3. **Recover from Corruption**:
   ```bash
   restic -r /path/to/repo check --read-data
   restic -r /path/to/repo prune
   ```

### Borg Issues

#### Issue: Repository upgrade needed

**Error**:
```
repository version is too old, please upgrade
```

**Solutions**:

1. **Upgrade Repository**:
   ```bash
   borg upgrade /path/to/repo
   ```

2. **Check Borg Version**:
   ```bash
   borg --version
   ```

#### Issue: Checkpoint handling

**Error**:
```
checkpoint detected, resuming backup
```

**Note**: This is informational, not an error. Borg is resuming an interrupted backup.

**Actions**:
- Allow backup to continue
- Monitor progress
- Ensure stable connection for completion

## Monitoring and Debugging

### Enable Debug Logging

```python
import logging

# Enable debug logging for backup operations
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('TimeLocker.services.backup_orchestrator')
logger.setLevel(logging.DEBUG)
```

### Capture Detailed Metrics

```python
# Enable detailed performance monitoring
config.additional_options = {
    "verbose": True,
    "stats": True,
    "progress": True
}

result = orchestrator.execute_backup_job(config)

# Review detailed metrics
print(f"Duration: {result.duration}")
print(f"Files: {result.files_processed}")
print(f"Bytes: {result.bytes_transferred}")
print(f"Errors: {len(result.errors)}")
print(f"Warnings: {len(result.warnings)}")
```

### Progress Monitoring

```python
import time
from threading import Thread

def monitor_backup(job_id):
    """Monitor backup progress in real-time."""
    while True:
        try:
            status = orchestrator.get_execution_status(job_id)
            
            print(f"\rProgress: {status.progress_percentage:.1f}% | "
                  f"Files: {status.files_processed} | "
                  f"Speed: {status.throughput / 1024 / 1024:.2f} MB/s",
                  end='', flush=True)
            
            if status.status in [BackupStatus.COMPLETED, BackupStatus.FAILED]:
                print()  # New line
                break
                
            time.sleep(5)
            
        except JobNotFoundError:
            break

# Start monitoring
monitor_thread = Thread(target=monitor_backup, args=(job_id,))
monitor_thread.daemon = True
monitor_thread.start()

# Execute backup
result = orchestrator.execute_backup_job(config)

# Wait for monitoring to complete
monitor_thread.join()
```

## Best Practices

### 1. Test Before Production

Always test backup configurations in a non-production environment:

```python
# Create test configuration
test_config = BackupJobConfig(
    job_id="test-backup",
    policy_id="test-policy",
    repository_id="test-repo",
    data_selection_id="test-selection",
    tool_type="restic",
    execution_mode=ExecutionMode.ON_DEMAND,
    retry_config=RetryConfig(max_retries=1),
    notification_config=NotificationConfig()
)

# Validate configuration
validation = orchestrator.validate_job_configuration(test_config)
if validation.is_valid:
    # Run test backup
    result = orchestrator.execute_backup_job(test_config)
    print(f"Test backup: {result.status}")
```

### 2. Monitor Backup Health

Regularly check backup health:

```python
# Check recent backups
recent_backups = repository.list_snapshots(limit=10)
for snapshot in recent_backups:
    print(f"Snapshot: {snapshot.id}")
    print(f"  Date: {snapshot.time}")
    print(f"  Files: {snapshot.files}")
    print(f"  Size: {snapshot.size}")
```

### 3. Implement Notifications

Configure notifications for backup events:

```python
notification_config = NotificationConfig(
    on_success=True,
    on_failure=True,
    on_warning=True,
    min_duration_for_notification=300,  # 5 minutes
    email_recipients=["admin@example.com"],
    slack_webhook="https://hooks.slack.com/..."
)
```

### 4. Regular Maintenance

Perform regular repository maintenance:

```bash
# Weekly: Check repository integrity
restic -r /path/to/repo check

# Monthly: Prune old data
restic -r /path/to/repo forget --keep-daily 7 --keep-weekly 4 --prune

# Quarterly: Full repository check
restic -r /path/to/repo check --read-data
```

## Getting Help

### Collect Diagnostic Information

When reporting issues, collect:

1. **Error Messages**:
   ```python
   for error in result.errors:
       print(f"Error: {error.message}")
       print(f"Type: {error.error_type}")
       print(f"Context: {error.context}")
   ```

2. **Configuration**:
   ```python
   print(f"Tool: {config.tool_type}")
   print(f"Repository: {config.repository_id}")
   print(f"Policy: {config.policy_id}")
   ```

3. **System Information**:
   ```bash
   # OS and version
   uname -a
   
   # Tool versions
   restic version
   borg --version
   
   # Available resources
   df -h
   free -h
   ```

4. **Logs**:
   ```bash
   # TimeLocker logs
   tail -n 100 /var/log/timelocker/backup.log
   
   # System logs
   journalctl -u timelocker -n 100
   ```

### Support Resources

- **Documentation**: [TimeLocker Documentation](../../README.md)
- **API Reference**: [Backup Operations API](../../reference/backup-operations-api.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/timelocker/timelocker/issues)
- **Community Forum**: [TimeLocker Forum](https://forum.timelocker.org)

## See Also

- [Backup Operations API Reference](../../reference/backup-operations-api.md)
- [Plugin Wrapper Development Guide](../developer/plugin-wrapper-development.md)
- [Repository Management Guide](repository-management-guide.md)
