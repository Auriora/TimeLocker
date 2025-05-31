# Recovery Operations Test Suite

Tags: restore, recovery, snapshot
Meta: priority = high, module = recovery

## S1 Full Snapshot Restoration

* C1 Restore Entire Snapshot
  Tags: full-restore, basic
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select an existing snapshot
    * Click "Restore" button
    * Choose destination path
    * Select "Restore entire snapshot" option
    * Click "Start Restore" button
    * Verify restore progress is displayed in real-time
    * Verify restore completes successfully
    * Verify all files are restored to destination
    * Verify audit log contains RESTORE_SUCCESS entry

* C2 Restore Snapshot with Hash Verification
  Tags: verification, integrity
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select an existing snapshot
    * Click "Restore" button
    * Choose destination path
    * Enable "Verify file hashes" option
    * Click "Start Restore" button
    * Verify restore progress is displayed
    * Verify hash verification is performed
    * Verify restore completes successfully
    * Verify audit log contains RESTORE_SUCCESS entry with verification flag

## S2 Partial Restoration

* C3 Restore Specific Files
  Tags: partial-restore, selective
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select an existing snapshot
    * Browse snapshot contents
    * Select specific files to restore
    * Choose destination path
    * Click "Start Restore" button
    * Verify only selected files are restored
    * Verify restore completes successfully
    * Verify audit log contains RESTORE_SUCCESS entry

* C4 Restore Specific Folder
  Tags: partial-restore, folder
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select an existing snapshot
    * Browse snapshot contents
    * Select a folder to restore
    * Choose destination path
    * Click "Start Restore" button
    * Verify folder and all its contents are restored
    * Verify restore completes successfully
    * Verify audit log contains RESTORE_SUCCESS entry

## S3 Conflict Resolution

* C5 Restore with File Conflicts
  Tags: conflict, overwrite
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select an existing snapshot
    * Select files to restore
    * Choose destination with existing files
    * Click "Start Restore" button
    * Verify conflict resolution dialog appears
    * Select "Overwrite" option
    * Verify files are overwritten
    * Verify restore completes successfully

* C6 Restore with Rename Option
  Tags: conflict, rename
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select an existing snapshot
    * Select files to restore
    * Choose destination with existing files
    * Click "Start Restore" button
    * Verify conflict resolution dialog appears
    * Select "Rename" option
    * Verify files are restored with new names
    * Verify original files remain unchanged
    * Verify restore completes successfully

* C7 Restore with Skip Option
  Tags: conflict, skip
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select an existing snapshot
    * Select files to restore
    * Choose destination with existing files
    * Click "Start Restore" button
    * Verify conflict resolution dialog appears
    * Select "Skip" option
    * Verify conflicting files are not restored
    * Verify non-conflicting files are restored
    * Verify restore completes successfully

## S4 Error Handling

* C8 Restore with Insufficient Disk Space
  Tags: error, disk-space
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select a large snapshot
    * Choose destination with insufficient space
    * Click "Start Restore" button
    * Verify space check fails
    * Verify error message is displayed
    * Verify user is prompted to choose another destination
    * Choose destination with sufficient space
    * Verify restore completes successfully

* C9 Network Interruption During Restore
  Tags: error, network, retry
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select a snapshot from remote repository
    * Select files to restore
    * Click "Start Restore" button
    * Simulate network interruption during restore
    * Verify system attempts to retry connection
    * Restore network connection
    * Verify restore continues and completes
    * Verify audit log contains retry events

* C10 User Cancels Restore Operation
  Tags: cancel, user-action
    * Open TimeLocker application
    * Navigate to "Snapshots" tab
    * Select a large snapshot
    * Click "Start Restore" button
    * Wait for restore to begin
    * Click "Cancel" button
    * Verify restore operation stops
    * Verify partial files are cleaned up
    * Verify audit log contains RESTORE_CANCELLED entry