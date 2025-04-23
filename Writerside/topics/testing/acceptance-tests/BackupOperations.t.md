# Backup Operations Test Suite
Tags: backup, snapshot, integrity
Meta: priority = high, module = backup

## S1 Manual Backup Creation
* C1 Create Full Backup
Tags: full-backup, basic
    * Open TimeLocker application
    * Select a configured repository
    * Click "Create Backup" button
    * Select data sources to backup
    * Click "Start Backup" button
    * Verify backup progress is displayed in real-time
    * Verify backup completes successfully
    * Verify snapshot is created in the repository
    * Verify audit log contains backup success entry

* C2 Create Incremental Backup
Tags: incremental, optimization
    * Open TimeLocker application
    * Select a repository with existing backup
    * Click "Create Backup" button
    * Select same data sources as previous backup
    * Click "Start Backup" button
    * Verify backup progress is displayed
    * Verify only changed files are transferred
    * Verify backup completes successfully
    * Verify audit log contains backup success entry

* C3 Backup with Inclusion/Exclusion Patterns
Tags: patterns, filtering
    * Open TimeLocker application
    * Click "Create Backup" button
    * Select data sources
    * Add inclusion pattern "*.docx"
    * Add exclusion pattern "temp/*"
    * Click "Start Backup" button
    * Verify only matching files are backed up
    * Verify excluded files are not backed up
    * Verify backup completes successfully

## S2 Backup Validation
* C4 Validate Backup Integrity
Tags: validation, integrity
    * Open TimeLocker application
    * Create a new backup
    * Wait for backup to complete
    * Verify system automatically runs "restic check"
    * Verify integrity check passes
    * Verify audit log contains validation entry

* C5 Backup with Corrupted Data
Tags: negative, corruption
    * Open TimeLocker application
    * Create a backup with intentionally corrupted test file
    * Wait for backup to complete
    * Verify system detects corruption during validation
    * Verify appropriate error message is displayed
    * Verify audit log contains error entry

## S3 Scheduled Backups
* C6 Configure Daily Backup Schedule
Tags: schedule, automation
    * Open TimeLocker application
    * Navigate to "Backup Schedule" section
    * Select a repository
    * Select data sources
    * Set schedule to "Daily" at specific time
    * Save schedule configuration
    * Verify schedule is created
    * Wait for scheduled time
    * Verify backup starts automatically
    * Verify backup completes successfully
    * Verify next schedule is recalculated

* C7 Configure Custom Cron Schedule
Tags: schedule, cron, advanced
    * Open TimeLocker application
    * Navigate to "Backup Schedule" section
    * Select a repository
    * Select data sources
    * Select "Custom" schedule
    * Enter valid cron expression
    * Save schedule configuration
    * Verify schedule is created with correct timing
    * Wait for scheduled time
    * Verify backup starts automatically

## S4 Error Handling
* C8 Network Interruption During Backup
Tags: error, network, retry
    * Open TimeLocker application
    * Start backup to remote repository
    * Simulate network interruption during upload
    * Verify system attempts to retry connection
    * Restore network connection
    * Verify backup continues and completes
    * Verify audit log contains retry events

* C9 Backup Failure After Retry Exhaustion
Tags: error, failure
    * Open TimeLocker application
    * Start backup to remote repository
    * Simulate persistent network failure
    * Verify system retries multiple times
    * Verify system eventually marks backup as failed
    * Verify error notification is displayed to user
    * Verify audit log contains ERROR_NETWORK event