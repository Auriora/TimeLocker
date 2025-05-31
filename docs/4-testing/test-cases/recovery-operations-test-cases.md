# Recovery Operations Test Cases

## Test Case Information

- **Test Case ID**: TC-RO-001
- **Test Case Name**: Restore Entire Snapshot
- **Created By**: TimeLocker QA Team
- **Creation Date**: 2023-04-23
- **Last Updated**: 2023-04-23
- **Related Requirements**: REQ-RO-001, REQ-RO-002
- **Priority**: High

## Test Objective

Verify that a user can successfully restore an entire backup snapshot to a specified location.

## Preconditions

- TimeLocker application is installed and running
- At least one repository is configured
- At least one backup snapshot exists in the repository
- User has appropriate permissions to write to the destination location

## Test Data

- Repository: "TestLocalRepo"
- Snapshot ID: Latest snapshot in the repository
- Destination path: "/home/user/restored"

## Test Steps

| Step # | Description                                       | Expected Result                                   |
|--------|---------------------------------------------------|---------------------------------------------------|
| 1      | Open TimeLocker application                       | Application opens successfully                    |
| 2      | Navigate to "Snapshots" tab                       | Snapshots tab is displayed                        |
| 3      | Select the latest snapshot                        | Snapshot details are displayed                    |
| 4      | Click "Restore" button                            | Restore dialog is displayed                       |
| 5      | Select "Restore entire snapshot" option           | Option is selected                                |
| 6      | Enter destination path "/home/user/restored"      | Path is accepted                                  |
| 7      | Click "Start Restore" button                      | Restore process begins                            |
| 8      | Wait for restore to complete                      | Restore completes successfully                    |
| 9      | Verify restore progress is displayed in real-time | Progress information is shown during restore      |
| 10     | Navigate to the destination path                  | Destination directory contains all restored files |
| 11     | Verify all files are restored correctly           | Files match the original backup content           |

## Post-conditions

- All files from the snapshot are restored to the specified destination
- File permissions and timestamps are preserved
- The restore operation is logged in the application's history

## Special Requirements

- Sufficient disk space at the destination location

## Dependencies

- TC-BO-001 (Create Full Backup)

## Notes

- The restore process may take a long time depending on the size of the snapshot.
- The application should handle large files and directories gracefully.

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author             | Description of Changes |
|---------|------------|--------------------|------------------------|
| 1.0     | 2023-04-23 | TimeLocker QA Team | Initial version        |

---

## Test Case Information

- **Test Case ID**: TC-RO-002
- **Test Case Name**: Restore Specific Files
- **Created By**: TimeLocker QA Team
- **Creation Date**: 2023-04-23
- **Last Updated**: 2023-04-23
- **Related Requirements**: REQ-RO-001, REQ-RO-003
- **Priority**: High

## Test Objective

Verify that a user can successfully restore specific files from a backup snapshot.

## Preconditions

- TimeLocker application is installed and running
- At least one repository is configured
- At least one backup snapshot exists in the repository
- User has appropriate permissions to write to the destination location

## Test Data

- Repository: "TestLocalRepo"
- Snapshot ID: Latest snapshot in the repository
- Files to restore: "/home/user/documents/important.docx", "/home/user/documents/critical.xlsx"
- Destination path: "/home/user/restored"

## Test Steps

| Step # | Description                                  | Expected Result                                                 |
|--------|----------------------------------------------|-----------------------------------------------------------------|
| 1      | Open TimeLocker application                  | Application opens successfully                                  |
| 2      | Navigate to "Snapshots" tab                  | Snapshots tab is displayed                                      |
| 3      | Select the latest snapshot                   | Snapshot details are displayed                                  |
| 4      | Click "Browse" button                        | File browser dialog is displayed showing snapshot contents      |
| 5      | Navigate to "/home/user/documents/"          | Directory contents are displayed                                |
| 6      | Select "important.docx" and "critical.xlsx"  | Files are selected                                              |
| 7      | Click "Restore Selected" button              | Restore dialog is displayed                                     |
| 8      | Enter destination path "/home/user/restored" | Path is accepted                                                |
| 9      | Click "Start Restore" button                 | Restore process begins                                          |
| 10     | Wait for restore to complete                 | Restore completes successfully                                  |
| 11     | Navigate to the destination path             | Destination directory contains only the selected restored files |
| 12     | Verify files are restored correctly          | Files match the original backup content                         |

## Post-conditions

- Only the selected files are restored to the specified destination
- File permissions and timestamps are preserved
- The restore operation is logged in the application's history

## Special Requirements

- None

## Dependencies

- TC-BO-001 (Create Full Backup)

## Notes

- The application should maintain the original directory structure for the restored files.
- If files with the same name already exist at the destination, the application should prompt for conflict resolution.

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author             | Description of Changes |
|---------|------------|--------------------|------------------------|
| 1.0     | 2023-04-23 | TimeLocker QA Team | Initial version        |