# Backup Operations Test Cases

## Test Case Information

- **Test Case ID**: TC-BO-001
- **Test Case Name**: Create Full Backup
- **Created By**: TimeLocker QA Team
- **Creation Date**: 2023-04-23
- **Last Updated**: 2023-04-23
- **Related Requirements**: REQ-BO-001, REQ-BO-002
- **Priority**: High

## Test Objective

Verify that a user can successfully create a full backup of selected data sources.

## Preconditions

- TimeLocker application is installed and running
- At least one repository is configured
- User has appropriate permissions to access the data sources

## Test Data

- Repository: "TestLocalRepo"
- Data source: "/home/user/documents"
- Backup name: "Documents Backup"

## Test Steps

| Step # | Description                                      | Expected Result                                               |
|--------|--------------------------------------------------|---------------------------------------------------------------|
| 1      | Open TimeLocker application                      | Application opens successfully                                |
| 2      | Navigate to "Backups" section                    | Backups section is displayed                                  |
| 3      | Click "Create Backup" button                     | Create Backup dialog is displayed                             |
| 4      | Select repository "TestLocalRepo"                | Repository is selected                                        |
| 5      | Enter backup name "Documents Backup"             | Name is accepted                                              |
| 6      | Click "Add Data Source" button                   | File browser dialog is displayed                              |
| 7      | Navigate to and select "/home/user/documents"    | Data source is added to the list                              |
| 8      | Click "Start Backup" button                      | Backup process begins                                         |
| 9      | Wait for backup to complete                      | Backup completes successfully                                 |
| 10     | Verify backup progress is displayed in real-time | Progress information is shown during backup                   |
| 11     | Verify backup appears in the backup list         | Backup is visible in the list with correct name and timestamp |

## Post-conditions

- A new backup snapshot is created in the selected repository
- The backup contains all files from the selected data source
- The backup is listed in the application's backup history

## Special Requirements

- None

## Dependencies

- TC-RM-001 (Add Local Repository)

## Notes

- The backup process may take a long time depending on the size of the data source.
- The application should handle large files and directories gracefully.

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author             | Description of Changes |
|---------|------------|--------------------|------------------------|
| 1.0     | 2023-04-23 | TimeLocker QA Team | Initial version        |

---

## Test Case Information

- **Test Case ID**: TC-BO-002
- **Test Case Name**: Create Incremental Backup
- **Created By**: TimeLocker QA Team
- **Creation Date**: 2023-04-23
- **Last Updated**: 2023-04-23
- **Related Requirements**: REQ-BO-001, REQ-BO-003
- **Priority**: High

## Test Objective

Verify that the application can create an incremental backup that only includes changes since the last backup.

## Preconditions

- TimeLocker application is installed and running
- At least one repository is configured
- A previous full backup exists for the data source
- Some files in the data source have been modified since the last backup

## Test Data

- Repository: "TestLocalRepo"
- Data source: "/home/user/documents"
- Modified files: Add a new file "new_document.txt" and modify "existing_document.txt"

## Test Steps

| Step # | Description                                    | Expected Result                                               |
|--------|------------------------------------------------|---------------------------------------------------------------|
| 1      | Open TimeLocker application                    | Application opens successfully                                |
| 2      | Navigate to "Backups" section                  | Backups section is displayed                                  |
| 3      | Click "Create Backup" button                   | Create Backup dialog is displayed                             |
| 4      | Select repository "TestLocalRepo"              | Repository is selected                                        |
| 5      | Select the same data source as previous backup | Data source is added to the list                              |
| 6      | Click "Start Backup" button                    | Backup process begins                                         |
| 7      | Wait for backup to complete                    | Backup completes successfully                                 |
| 8      | Verify only changed files are transferred      | Transfer statistics show only modified files were processed   |
| 9      | Verify backup appears in the backup list       | Backup is visible in the list with correct name and timestamp |

## Post-conditions

- A new incremental backup snapshot is created in the selected repository
- The backup contains only the files that were added or modified since the last backup
- The backup is listed in the application's backup history

## Special Requirements

- None

## Dependencies

- TC-BO-001 (Create Full Backup)

## Notes

- The application should automatically detect that this is an incremental backup and only process changed files.
- The backup size and duration should be significantly smaller than the full backup.

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date       | Author             | Description of Changes |
|---------|------------|--------------------|------------------------|
| 1.0     | 2023-04-23 | TimeLocker QA Team | Initial version        |