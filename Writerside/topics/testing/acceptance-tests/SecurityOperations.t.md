# Security Operations Test Suite
Tags: security, privacy, GDPR, metadata
Meta: priority = high, module = security

## S1 Personal Data Export
* C1 Export All Personal Metadata
Tags: export, data-portability
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Export Personal Data" option
    * Select all data categories
    * Choose JSON format
    * Specify valid export destination and filename
    * Click "Export" button
    * Verify export completes successfully
    * Verify exported file contains all selected data
    * Verify data dictionary is included
    * Verify audit log contains METADATA_EXPORT_SUCCESS entry

* C2 Export Selected Metadata Categories
Tags: export, selective
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Export Personal Data" option
    * Select only specific data categories (e.g., settings, logs)
    * Choose JSON format
    * Specify valid export destination
    * Click "Export" button
    * Verify export completes successfully
    * Verify exported file contains only selected categories
    * Verify audit log contains METADATA_EXPORT_SUCCESS entry

* C3 Export with Encryption
Tags: export, encryption, sensitive-data
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Export Personal Data" option
    * Select data categories including credentials
    * Enable encryption option
    * Enter encryption password
    * Specify export destination
    * Click "Export" button
    * Verify export completes successfully
    * Verify sensitive data is encrypted in export file
    * Verify audit log contains METADATA_EXPORT_SUCCESS entry

## S2 Export Error Handling
* C4 Export to Invalid Location
Tags: export, error, validation
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Export Personal Data" option
    * Select data categories
    * Specify invalid or non-writable export destination
    * Click "Export" button
    * Verify error message is displayed
    * Verify user is prompted to select different location
    * Select valid location
    * Verify export completes successfully

* C5 Export with Insufficient Disk Space
Tags: export, error, disk-space
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Export Personal Data" option
    * Select all data categories
    * Specify destination with insufficient space
    * Click "Export" button
    * Verify error message is displayed
    * Verify user is prompted to select different location or reduce data
    * Select valid location with sufficient space
    * Verify export completes successfully

## S3 Personal Data Erasure
* C6 Erase All Personal Metadata
Tags: erasure, right-to-be-forgotten
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Erase Personal Data" option
    * Verify warning about permanent data loss is displayed
    * Select all data categories
    * Confirm erasure intent
    * Enter password for secondary authentication
    * Confirm final warning
    * Verify erasure completes successfully
    * Verify selected data is no longer accessible
    * Verify audit log contains anonymized METADATA_ERASURE_SUCCESS entry

* C7 Erase Selected Metadata Categories
Tags: erasure, selective
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Erase Personal Data" option
    * Select only specific data categories
    * Confirm erasure intent
    * Enter password for secondary authentication
    * Confirm final warning
    * Verify erasure completes successfully
    * Verify only selected categories are erased
    * Verify non-selected categories remain intact
    * Verify audit log contains METADATA_ERASURE_SUCCESS entry

## S4 Erasure Error Handling
* C8 Erasure with Active Operations
Tags: erasure, error, active-operations
    * Open TimeLocker application
    * Start a backup operation
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Erase Personal Data" option
    * Select data categories
    * Verify warning about active operations is displayed
    * Choose to proceed
    * Complete authentication
    * Verify active operations are stopped
    * Verify erasure completes successfully
    * Verify audit log contains METADATA_ERASURE_SUCCESS entry

* C9 Erasure with Authentication Failure
Tags: erasure, error, authentication
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Erase Personal Data" option
    * Select data categories
    * Confirm erasure intent
    * Enter incorrect password for authentication
    * Verify authentication failure message is displayed
    * Verify erasure is denied
    * Verify audit log contains failed erasure attempt

* C10 Erasure of Critical System Data
Tags: erasure, warning, system-integrity
    * Open TimeLocker application
    * Navigate to "Settings" > "Privacy & Data" section
    * Select "Erase Personal Data" option
    * Select critical system data categories
    * Verify warning about application reconfiguration is displayed
    * Choose to proceed
    * Complete authentication
    * Verify erasure completes successfully
    * Verify application prompts for reconfiguration if needed
    * Verify audit log contains METADATA_ERASURE_SUCCESS entry