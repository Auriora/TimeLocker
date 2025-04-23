# Repository Management Test Cases

## Test Case Information
- **Test Case ID**: TC-RM-001
- **Test Case Name**: Add Local Repository
- **Created By**: TimeLocker QA Team
- **Creation Date**: 2023-04-23
- **Last Updated**: 2023-04-23
- **Related Requirements**: REQ-RM-001, REQ-RM-002
- **Priority**: High

## Test Objective
Verify that a user can successfully add a local repository to the TimeLocker application.

## Preconditions
- TimeLocker application is installed and running
- User has appropriate permissions to create directories on the local file system

## Test Data
- Repository name: "TestLocalRepo"
- Repository path: "/path/to/local/repository"
- Repository password: "SecurePassword123"

## Test Steps
| Step # | Description | Expected Result |
|--------|-------------|-----------------|
| 1      | Open TimeLocker application | Application opens successfully |
| 2      | Navigate to "Repositories" section | Repositories section is displayed |
| 3      | Click "Add Repository" button | Add Repository dialog is displayed |
| 4      | Select "Local" repository type | Local repository options are displayed |
| 5      | Enter repository name "TestLocalRepo" | Name is accepted |
| 6      | Enter repository path "/path/to/local/repository" | Path is accepted |
| 7      | Enter repository password "SecurePassword123" | Password is accepted and masked |
| 8      | Click "Save" button | Repository is created and added to the list |
| 9      | Verify repository appears in the repository list | Repository is visible in the list with correct name and type |

## Post-conditions
- A new local repository is created at the specified path
- The repository is initialized with the provided password
- The repository is added to the list of available repositories in the application

## Special Requirements
- None

## Dependencies
- None

## Notes
- If the repository path already exists, the application should prompt the user to confirm overwriting or provide a different path.

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0 | 2023-04-23 | TimeLocker QA Team | Initial version |

---

## Test Case Information
- **Test Case ID**: TC-RM-002
- **Test Case Name**: Add S3 Repository
- **Created By**: TimeLocker QA Team
- **Creation Date**: 2023-04-23
- **Last Updated**: 2023-04-23
- **Related Requirements**: REQ-RM-001, REQ-RM-003
- **Priority**: High

## Test Objective
Verify that a user can successfully add an S3 repository to the TimeLocker application.

## Preconditions
- TimeLocker application is installed and running
- User has valid S3 credentials
- Internet connection is available

## Test Data
- Repository name: "TestS3Repo"
- S3 endpoint: "s3.amazonaws.com"
- S3 bucket: "timelocker-test-bucket"
- Access key: "AKIAIOSFODNN7EXAMPLE"
- Secret key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
- Repository password: "SecurePassword123"

## Test Steps
| Step # | Description | Expected Result |
|--------|-------------|-----------------|
| 1      | Open TimeLocker application | Application opens successfully |
| 2      | Navigate to "Repositories" section | Repositories section is displayed |
| 3      | Click "Add Repository" button | Add Repository dialog is displayed |
| 4      | Select "S3" repository type | S3 repository options are displayed |
| 5      | Enter repository name "TestS3Repo" | Name is accepted |
| 6      | Enter S3 endpoint "s3.amazonaws.com" | Endpoint is accepted |
| 7      | Enter S3 bucket "timelocker-test-bucket" | Bucket name is accepted |
| 8      | Enter access key "AKIAIOSFODNN7EXAMPLE" | Access key is accepted |
| 9      | Enter secret key "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" | Secret key is accepted and masked |
| 10     | Enter repository password "SecurePassword123" | Password is accepted and masked |
| 11     | Click "Save" button | Repository is created and added to the list |
| 12     | Verify repository appears in the repository list | Repository is visible in the list with correct name and type |

## Post-conditions
- A new S3 repository is created in the specified bucket
- The repository is initialized with the provided password
- The repository is added to the list of available repositories in the application
- Credentials are stored securely in the OS keyring

## Special Requirements
- Internet connection
- Valid S3 credentials

## Dependencies
- None

## Notes
- If the S3 bucket doesn't exist, the application should create it if the user has sufficient permissions.
- The application should validate the S3 credentials before creating the repository.

## Change Tracking

This section records the history of changes made to this document. Add a new row for each significant update.

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0 | 2023-04-23 | TimeLocker QA Team | Initial version |