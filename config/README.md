# Configuration Examples

This directory contains example configuration files for TimeLocker.

## Files

### test-config.example.json
Example test configuration for integration tests with MinIO and other backends.
Copy to `../test-config.json` in the project root and customize for your test environment.

```bash
cp config/test-config.example.json test-config.json
```

### config_keyring_example.json
Example configuration showing how to use system keyring for password management.
Demonstrates the `password_command` approach using Python's keyring library.

### config_password_file_example.json
Example configuration showing how to use a password file for credential management.
Demonstrates the `password_file` approach for storing repository passwords.

### config_fixed.json
Example of a complete TimeLocker configuration with all sections defined.
Shows general settings, backup/restore options, security, UI, notifications, and monitoring.

## Usage

These are example files only. To use them:

1. Copy the relevant example to your desired location
2. Customize the values for your environment
3. Never commit files containing actual credentials to version control

## Notes

- Working configuration files (with actual credentials) should be kept in the project root
- The `.gitignore` file is configured to exclude `test-config.json` and similar files
- See the main documentation for detailed configuration instructions
