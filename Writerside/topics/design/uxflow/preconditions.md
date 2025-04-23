# Preconditions

This document outlines the necessary preconditions that must be met before a user can effectively use the TimeLocker application. These preconditions ensure that the application functions correctly and provides the expected user experience.

## System Requirements

Before using TimeLocker, the following system requirements must be met:

- **Operating System**: Compatible with Windows, macOS, or Linux
- **Disk Space**: Sufficient free space for the application and backup storage
- **Memory**: Minimum 4GB RAM recommended
- **Processor**: 1.5 GHz or faster processor
- **Network**: Internet connection required for cloud storage options

## Software Dependencies

The following software dependencies must be installed and properly configured:

- **Python**: Version 3.12 or higher
- **Restic**: Latest stable version
- **Required Python Packages**: All dependencies listed in requirements.txt

## User Permissions

The user must have:

- **File System Permissions**: Read access to files/folders to be backed up
- **Write Permissions**: Write access to the backup destination
- **Administrative Rights**: May be required for certain operations (e.g., system scheduler access)

## Repository Requirements

For backup operations to succeed:

- **Repository Access**: Valid credentials for the selected repository type
- **Repository Space**: Sufficient storage space in the target repository
- **Repository Compatibility**: Repository format compatible with the Restic version

## Knowledge Prerequisites

While TimeLocker is designed to be user-friendly, users should have:

- **Basic Computer Skills**: Familiarity with file navigation and selection
- **Basic Backup Concepts**: Understanding of what backups are and why they're important
- **Technical Users**: For advanced features, understanding of backup concepts like retention policies and encryption

## Verification Steps

Before starting the application for the first time, users should:

1. Verify that all system requirements are met
2. Ensure Restic is properly installed and accessible
3. Check that they have appropriate permissions for backup sources and destinations
4. Prepare repository access credentials if using remote repositories