# BackupTarget Test Suite
Tags: backup, target
Meta: component = TimeLocker, module = backup

## S1 Target Creation
* C1 Test creating a basic backup target
Tags: creation
    * Create a FileSelection instance
    * Create a BackupTarget with the selection
    * Verify the target's selection is the FileSelection instance
    * Verify the target's tags is an empty list
* C2 Test creating a backup target with tags
Tags: creation, tags
    * Create a FileSelection instance
    * Create a list of tags
    * Create a BackupTarget with the selection and tags
    * Verify the target's tags match the provided tags

## S2 Initialization Edge Cases
* C1 Test initializing with None selection
Tags: init, edge-case
    * Attempt to create a BackupTarget with None as the selection
    * Verify an AttributeError is raised
* C2 Test initializing with None tags
Tags: init, edge-case
    * Create a FileSelection instance
    * Create a BackupTarget with the selection and None as tags
    * Verify the target's tags is an empty list
* C3 Test initializing with selection and tags
Tags: init
    * Create a FileSelection instance
    * Create a list of tags
    * Create a BackupTarget with the selection and tags
    * Verify the target's selection is the FileSelection instance
    * Verify the target's tags match the provided tags

## S3 Target Validation
* C1 Test validation requires at least one folder
Tags: validation, folder
    * Create a FileSelection instance
    * Create a BackupTarget with the selection
    * Add only a file path to the selection
    * Verify validate() raises a ValueError
    * Create a new FileSelection with a folder path
    * Create a new BackupTarget with this selection
    * Verify validate() returns True
* C2 Test validation raises ValueError for invalid selection
Tags: validation, error
    * Create a mock FileSelection that raises ValueError on validate()
    * Create a BackupTarget with this mock selection
    * Call validate() on the target
    * Verify a ValueError is raised
* C3 Test validation returns True for valid selection
Tags: validation
    * Create a mock FileSelection that returns True on validate()
    * Create a BackupTarget with this mock selection
    * Call validate() on the target
    * Verify True is returned

## S4 Pattern Management
* C1 Test backup target with include/exclude patterns
Tags: pattern
    * Create a FileSelection instance
    * Add a folder path to the selection
    * Add an include pattern (e.g., "*.txt")
    * Add an exclude pattern (e.g., "*.tmp")
    * Create a BackupTarget with this selection
    * Verify validate() returns True
    * Verify the include pattern is in the selection's include_patterns
    * Verify the exclude pattern is in the selection's exclude_patterns
* C2 Test backup target with pattern groups
Tags: pattern-group
    * Create a FileSelection instance
    * Add a folder path to the selection
    * Add a pattern group (e.g., "office_documents")
    * Create a BackupTarget with this selection
    * Verify validate() returns True
    * Verify expected patterns (e.g., "*.doc", "*.pdf") are in the selection's include_patterns