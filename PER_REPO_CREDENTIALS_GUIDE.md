# Per-Repository Backend Credentials - User Guide

## Overview

TimeLocker now supports storing different credentials for each S3 or B2 repository. This allows you to:

- Use multiple S3 repositories with different AWS accounts
- Use multiple MinIO instances with different credentials
- Use multiple B2 repositories with different accounts
- Keep credentials secure and encrypted

## Quick Start

### Adding a Repository with Credentials

When you add an S3 or B2 repository, TimeLocker will prompt you to store credentials:

```bash
$ tl repos add my-minio "s3://minio.local/my-bucket"

Repository name: my-minio
Repository URI: s3://minio.local/my-bucket

Would you like to store a password for repository 'my-minio'? [y/N]: y
Password for repository 'my-minio': ********

Would you like to store AWS credentials for repository 'my-minio'? [Y/n]: y

AWS Credentials:
AWS Access Key ID: ********
AWS Secret Access Key: ********
AWS Region (optional, press Enter to skip): us-east-1

✅ Repository 'my-minio' added successfully!

📍 URI: s3://minio.local/my-bucket
📝 Description: my-minio repository
🎯 Default: No
🔐 Password: Stored securely
🔑 AWS Credentials: Stored securely
```

### Using the Repository

Once credentials are stored, they're automatically used:

```bash
# Backup to repository - credentials loaded automatically
$ tl backup -r my-minio /data

# List snapshots - credentials loaded automatically
$ tl list -r my-minio
```

## Managing Credentials

### Set or Update Credentials

Update credentials for an existing repository:

```bash
$ tl repos credentials-set my-minio

Setting AWS credentials for repository 'my-minio'
AWS Access Key ID: ********
AWS Secret Access Key: ********
AWS Region (optional, press Enter to skip): us-west-2

✅ S3 credentials stored successfully for repository 'my-minio'!
```

### Check Credential Status

See if credentials are configured (without showing the actual values):

```bash
$ tl repos credentials-show my-minio

✅ AWS credentials are configured for repository 'my-minio'

Note: Actual credential values are encrypted and not displayed
```

### Remove Credentials

Remove stored credentials (will fall back to environment variables):

```bash
$ tl repos credentials-remove my-minio

Remove S3 credentials for repository 'my-minio'? [y/N]: y

✅ S3 credentials removed for repository 'my-minio'
```

## Multiple Repositories Example

### Scenario: Two MinIO Instances

```bash
# Add first MinIO instance
$ tl repos add minio-prod "s3://minio-prod.company.com/backups"
# Enter production credentials

# Add second MinIO instance
$ tl repos add minio-dev "s3://minio-dev.company.com/backups"
# Enter development credentials

# Each repository uses its own credentials
$ tl backup -r minio-prod /data    # Uses production credentials
$ tl backup -r minio-dev /data     # Uses development credentials
```

### Scenario: AWS S3 and MinIO

```bash
# Add AWS S3 repository
$ tl repos add aws-backup "s3://s3.us-east-1.amazonaws.com/my-backups"
# Enter AWS credentials

# Add MinIO repository
$ tl repos add local-minio "s3://minio.local/backups"
# Enter MinIO credentials

# Each uses different credentials
$ tl backup -r aws-backup /data      # Uses AWS credentials
$ tl backup -r local-minio /data     # Uses MinIO credentials
```

## Credential Resolution Order

TimeLocker looks for credentials in this order:

1. **Per-repository credentials** (stored in credential manager)
2. **Constructor parameters** (when creating repository programmatically)
3. **Environment variables** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.)

This means:
- If you store credentials for a repository, they take priority
- If no stored credentials, environment variables are used
- Existing repositories using environment variables continue to work

## Security

### How Credentials Are Stored

- Credentials are **encrypted** using the credential manager
- Stored in `~/.timelocker/credentials/credentials.enc`
- **Never** stored in plain text in `config.json`
- Protected by master password or auto-unlock

### Credential Manager

The credential manager may prompt for a master password:

```bash
TimeLocker master password: ********
```

Or use auto-unlock based on system fingerprint (non-interactive).

### Audit Logging

All credential operations are logged:
- When credentials are stored
- When credentials are accessed
- When credentials are removed

Logs are in `~/.timelocker/credentials/credential_audit.log`

## Supported Backends

### S3 (AWS S3, MinIO, Wasabi, etc.)

Credentials required:
- **AWS Access Key ID** (required)
- **AWS Secret Access Key** (required)
- **AWS Region** (optional)

### B2 (Backblaze B2)

Credentials required:
- **B2 Account ID** (required)
- **B2 Account Key** (required)

## Troubleshooting

### Credentials Not Working

1. Check if credentials are stored:
   ```bash
   $ tl repos credentials-show my-repo
   ```

2. If not stored, add them:
   ```bash
   $ tl repos credentials-set my-repo
   ```

3. Verify repository URI is correct:
   ```bash
   $ tl repos list
   ```

### Credential Manager Locked

If you see "Credential manager locked":

1. Try unlocking with environment variable:
   ```bash
   $ export TIMELOCKER_MASTER_PASSWORD="your-password"
   $ tl repos credentials-show my-repo
   ```

2. Or let it prompt you for the password

### Migrating from Environment Variables

If you currently use environment variables:

1. Your existing setup continues to work (backward compatible)
2. To migrate to per-repository credentials:
   ```bash
   $ tl repos credentials-set my-repo
   # Enter the same credentials you have in environment variables
   ```
3. Remove environment variables if desired

## Best Practices

1. **Use per-repository credentials** for multiple repositories with different accounts
2. **Use environment variables** for single repository or CI/CD environments
3. **Regularly rotate credentials** using `credentials-set`
4. **Remove credentials** when decommissioning repositories
5. **Check credential status** before troubleshooting access issues

## Command Reference

```bash
# Add repository (prompts for credentials)
tl repos add <name> <uri>

# Set/update credentials
tl repos credentials-set <name>

# Show credential status
tl repos credentials-show <name>

# Remove credentials
tl repos credentials-remove <name>

# Remove credentials without confirmation
tl repos credentials-remove <name> --yes
```

## Examples

### Example 1: Multiple AWS Accounts

```bash
# Production account
tl repos add aws-prod "s3://s3.us-east-1.amazonaws.com/prod-backups"
# Enter production AWS credentials

# Staging account
tl repos add aws-staging "s3://s3.us-west-2.amazonaws.com/staging-backups"
# Enter staging AWS credentials
```

### Example 2: MinIO with Different Tenants

```bash
# Tenant A
tl repos add tenant-a "s3://minio.local/tenant-a-backups"
# Enter tenant A credentials

# Tenant B
tl repos add tenant-b "s3://minio.local/tenant-b-backups"
# Enter tenant B credentials
```

### Example 3: Updating Rotated Credentials

```bash
# After rotating AWS credentials
tl repos credentials-set my-repo
# Enter new credentials
```

## FAQ

**Q: Are my credentials stored in plain text?**
A: No, all credentials are encrypted using the credential manager.

**Q: Can I use environment variables instead?**
A: Yes, environment variables still work as a fallback.

**Q: What happens if I don't store credentials?**
A: TimeLocker will use environment variables or prompt you when needed.

**Q: Can I see my stored credentials?**
A: No, for security reasons, stored credentials cannot be displayed. You can only check if they exist.

**Q: How do I change credentials?**
A: Use `tl repos credentials-set <name>` to update credentials.

**Q: Can I use this with local repositories?**
A: No, this feature is only for S3 and B2 repositories that require backend credentials.

**Q: Is this compatible with existing repositories?**
A: Yes, fully backward compatible. Existing repositories continue to work.

