# Security Operations Test Cases

## Test Case Information
- **Test Case ID**: TC-SO-001
- **Test Case Name**: Export Personal Data
- **Created By**: TimeLocker QA Team
- **Creation Date**: 2023-04-23
- **Last Updated**: 2023-04-23
- **Related Requirements**: REQ-SO-001, REQ-SO-002
- **Priority**: High

## Test Objective
Verify that a user can successfully export their personal data in compliance with GDPR data portability requirements.

## Preconditions
- TimeLocker application is installed and running
- User has created repositories and backups
- User has appropriate permissions to write to the export destination

## Test Data
- Export destination: "/home/user/exports"
- Export format: JSON
- Data categories: All (settings, repositories, backup history, logs)

## Test Steps
| Step # | Description | Expected Result |
|--------|-------------|-----------------|
| 1      | Open TimeLocker application | Application opens successfully |
| 2      | Navigate to "Settings" > "Privacy & Data" section | Privacy & Data section is displayed |
| 3      | Select "Export Personal Data" option | Export Personal Data dialog is displayed |
| 4      | Select all data categories | All categories are selected |
| 5      | Choose JSON format | Format is selected |
| 6      | Enter export destination "/home/user/exports" | Path is accepted |
| 7      | Click "Export" button | Export process begins |
| 8      | Wait for export to complete | Export completes successfully |
| 9      | Navigate to the export destination | Export file exists in the specified location |
| 10     | Open the export file | File contains all selected data categories in JSON format |
| 11     | Verify data dictionary is included | Data dictionary explaining the exported data structure is present |

## Post-conditions
- Personal data is exported to the specified location
- The export file contains all selected data categories
- The export operation is logged in the application's history

## Special Requirements
- None

## Dependencies
- None

## Notes
- Sensitive data such as passwords should be properly masked or encrypted in the export.
- The export should include a data dictionary explaining the structure and meaning of the exported data.

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0 | 2023-04-23 | TimeLocker QA Team | Initial version |

---

## Test Case Information
- **Test Case ID**: TC-SO-002
- **Test Case Name**: Erase Personal Data
- **Created By**: TimeLocker QA Team
- **Creation Date**: 2023-04-23
- **Last Updated**: 2023-04-23
- **Related Requirements**: REQ-SO-003, REQ-SO-004
- **Priority**: High

## Test Objective
Verify that a user can successfully erase their personal data in compliance with GDPR right to be forgotten requirements.

## Preconditions
- TimeLocker application is installed and running
- User has created repositories and backups
- No active backup or restore operations are in progress

## Test Data
- User password: "SecurePassword123"
- Data categories to erase: All (settings, repositories, backup history, logs)

## Test Steps
| Step # | Description | Expected Result |
|--------|-------------|-----------------|
| 1      | Open TimeLocker application | Application opens successfully |
| 2      | Navigate to "Settings" > "Privacy & Data" section | Privacy & Data section is displayed |
| 3      | Select "Erase Personal Data" option | Erase Personal Data dialog is displayed |
| 4      | Verify warning about permanent data loss is displayed | Warning is displayed |
| 5      | Select all data categories | All categories are selected |
| 6      | Click "Continue" button | Secondary authentication dialog is displayed |
| 7      | Enter user password "SecurePassword123" | Password is accepted |
| 8      | Click "Confirm Erasure" button | Final warning dialog is displayed |
| 9      | Confirm final warning | Erasure process begins |
| 10     | Wait for erasure to complete | Erasure completes successfully |
| 11     | Verify selected data is no longer accessible | Application shows default state for erased data |
| 12     | Verify audit log contains anonymized erasure entry | Audit log shows erasure event without personal identifiers |

## Post-conditions
- Selected personal data is permanently erased from the application
- The application returns to a default state for the erased data categories
- An anonymized record of the erasure is maintained in the audit log

## Special Requirements
- None

## Dependencies
- None

## Notes
- The erasure process should be irreversible.
- The application should provide clear warnings about the permanent nature of the erasure.
- Secondary authentication should be required to prevent unauthorized erasure.

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0 | 2023-04-23 | TimeLocker QA Team | Initial version |