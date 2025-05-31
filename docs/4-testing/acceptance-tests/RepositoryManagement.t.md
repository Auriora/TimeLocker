# Repository Management Test Suite

Tags: repository, configuration, GDPR
Meta: priority = high, module = repository

## S1 Repository Registration

* C1 Add Local Repository
  Tags: local, basic
    * Open TimeLocker application
    * Click "Add Repository" button
    * Select "Local" repository type
    * Enter valid local path
    * Click "Save" button
    * Verify repository is added to the list
    * Verify audit log contains REPO_ADD event

* C2 Add S3 Repository with Valid Credentials
  Tags: S3, cloud, credentials
    * Open TimeLocker application
    * Click "Add Repository" button
    * Select "S3" repository type
    * Enter valid S3 endpoint
    * Enter valid access key and secret key
    * Click "Save" button
    * Verify repository is added to the list
    * Verify credentials are stored in OS key-ring
    * Verify audit log contains REPO_ADD event

* C3 Add Repository with Invalid Credentials
  Tags: negative, validation
    * Open TimeLocker application
    * Click "Add Repository" button
    * Select "SFTP" repository type
    * Enter valid SFTP endpoint
    * Enter invalid username/password
    * Click "Save" button
    * Verify error message is displayed
    * Verify invalid fields are highlighted
    * Verify repository is not added to the list

## S2 GDPR Region Compliance

* C4 Add S3 Repository in Non-EEA Region with Enforcement Enabled
  Tags: S3, GDPR, region, negative
    * Open TimeLocker application
    * Set user policy enforce_region=true
    * Click "Add Repository" button
    * Select "S3" repository type
    * Enter valid S3 endpoint in non-EEA region
    * Enter valid credentials
    * Click "Save" button
    * Verify GDPR warning is displayed
    * Verify repository is not added to the list

* C5 Add S3 Repository in Non-EEA Region with Warning Only
  Tags: S3, GDPR, region, warning
    * Open TimeLocker application
    * Set user policy enforce_region=false
    * Click "Add Repository" button
    * Select "S3" repository type
    * Enter valid S3 endpoint in non-EEA region
    * Enter valid credentials
    * Click "Save" button
    * Verify warning banner is displayed
    * Click "Proceed" button
    * Verify repository is added to the list
    * Verify audit log contains REPO_ADD event with region warning flag

## S3 Repository Editing

* C6 Edit Repository Endpoint
  Tags: edit, configuration
    * Open TimeLocker application
    * Navigate to "Manage Repositories" section
    * Select an existing repository
    * Click "Edit" button
    * Modify the repository endpoint
    * Click "Save" button
    * Verify repository is updated with new endpoint
    * Verify audit log contains REPO_UPDATE event with pre-edit and post-edit states

* C7 Edit Repository Credentials
  Tags: edit, credentials, security
    * Open TimeLocker application
    * Navigate to "Manage Repositories" section
    * Select an existing repository
    * Click "Edit" button
    * Update credentials
    * Click "Save" button
    * Verify repository is updated with new credentials
    * Verify credentials are stored securely in OS key-ring
    * Verify audit log contains REPO_UPDATE event

* C8 Edit Repository with Invalid Configuration
  Tags: edit, negative, validation
    * Open TimeLocker application
    * Navigate to "Manage Repositories" section
    * Select an existing repository
    * Click "Edit" button
    * Enter invalid endpoint
    * Click "Save" button
    * Verify error message is displayed
    * Verify invalid fields are highlighted
    * Verify repository configuration remains unchanged

## S4 Repository Removal

* C9 Remove Repository with No Active Backups
  Tags: delete, basic
    * Open TimeLocker application
    * Navigate to "Manage Repositories" section
    * Select a repository with no active backups
    * Click "Delete" button
    * Confirm deletion in the dialog
    * Verify repository is removed from the list
    * Verify audit log contains REPO_DELETE event

* C10 Remove Repository with Active Backups
  Tags: delete, warning, data-protection
    * Open TimeLocker application
    * Navigate to "Manage Repositories" section
    * Select a repository with active backups
    * Click "Delete" button
    * Verify additional confirmation dialog is displayed with warning about active backups
    * Confirm deletion
    * Verify repository is removed from the list
    * Verify scheduled backups using this repository are cancelled
    * Verify audit log contains REPO_DELETE event

* C11 Cancel Repository Removal
  Tags: delete, cancel
    * Open TimeLocker application
    * Navigate to "Manage Repositories" section
    * Select an existing repository
    * Click "Delete" button
    * Click "Cancel" in the confirmation dialog
    * Verify repository remains in the list
    * Verify no audit log entry is created
