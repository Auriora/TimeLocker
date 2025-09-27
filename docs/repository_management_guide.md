# Repository Management Guide

TimeLocker now supports named repositories, allowing you to use memorable names instead of long URIs for your backup repositories.

## 🎯 **Key Features**

- **Named Repositories**: Use short names like "production" instead of full URIs
- **Default Repository**: Set a default repository to avoid specifying `-r` every time
- **Backward Compatibility**: All existing URI-based commands continue to work
- **Auto-Detection**: Repository types are automatically detected from URIs
- **Separate Configuration**: Clean separation between repositories, backup targets, and settings

## 📋 **Repository Management Commands**

### Add a Repository

```bash
# Add a repository with a name
tl config add-repo <name> <uri> [options]

# Examples
tl config add-repo production "s3:s3.af-south-1.amazonaws.com/prod-backup"
tl config add-repo local-backup "/home/user/backups"
tl config add-repo remote-sftp "sftp://user@server:/backup/path"

# Add with description and set as default
tl config add-repo production "s3://bucket/path" \
  --description "Production backup repository" \
  --set-default
```

### List Repositories

```bash
# List all configured repositories
tl config list-repos
```

Output shows:

- Repository name
- Type (s3, local, sftp, etc.)
- URI
- Description
- Default repository indicator (✓)

### Set Default Repository

```bash
# Set a repository as default
tl config set-default-repo <name>

# Example
tl config set-default-repo production
```

### Remove a Repository

```bash
# Remove a repository (with confirmation)
tl config remove-repo <name>

# Example
tl config remove-repo old-backup
```

## 🚀 **Using Named Repositories**

### With Repository Names

```bash
# Use repository name instead of URI
tl list -r production
tl backup -r production /home/user/documents
tl restore -r production /restore/path

# All commands support repository names
tl init -r new-repo
tl verify -r production
```

### With Default Repository

```bash
# No need to specify -r when using default repository
tl list
tl backup /home/user/documents
tl restore /restore/path
```

### Backward Compatibility

```bash
# Direct URIs still work
tl list -r "s3://bucket/path"
tl backup -r "/local/path" /home/user/docs
```

## 🔧 **Repository Types**

TimeLocker automatically detects repository types:

| URI Pattern          | Type         | Example                             |
|----------------------|--------------|-------------------------------------|
| `s3://` or `s3:`     | S3           | `s3:s3.region.amazonaws.com/bucket` |
| `b2://` or `b2:`     | Backblaze B2 | `b2://bucket/path`                  |
| `sftp://` or `sftp:` | SFTP         | `sftp://user@host:/path`            |
| `/path` or `file://` | Local        | `/home/user/backup`                 |

## 📝 **Configuration Structure**

The configuration is now cleanly separated:

```json
{
  "general": {
    "default_repository": "production"
  },
  "repositories": {
    "production": {
      "uri": "s3:s3.af-south-1.amazonaws.com/prod-backup",
      "description": "Production backup repository",
      "type": "s3",
      "created": "2025-06-30T09:00:00"
    },
    "local-test": {
      "uri": "/tmp/test-backup",
      "description": "Local test repository",
      "type": "local",
      "created": "2025-06-30T09:05:00"
    }
  },
  "backup_targets": {
    // Backup target configurations
  }
}
```

## 🔄 **Migration from URIs**

### Import Existing Configuration

If you have existing restic environment variables:

```bash
# Import from restic environment
export RESTIC_REPOSITORY="s3:s3.region.amazonaws.com/bucket"
export RESTIC_PASSWORD="your-password"
tl config import-restic
```

### Manual Migration

```bash
# Add your existing repositories with names
tl config add-repo main "s3:s3.region.amazonaws.com/main-backup"
tl config add-repo archive "/mnt/archive/backup"

# Set a default
tl config set-default-repo main

# Test the migration
tl list -r main  # Should work the same as before
tl list          # Uses default repository
```

## 💡 **Best Practices**

### Repository Naming

- Use descriptive names: `production`, `staging`, `archive`
- Avoid spaces: use `local-test` instead of `local test`
- Be consistent: `prod-db`, `prod-files`, `prod-logs`

### Default Repository

- Set your most frequently used repository as default
- Use specific names for special operations
- Change default as needed: `tl config set-default-repo staging`

### Organization

```bash
# Organize by environment
tl config add-repo prod-main "s3://prod-bucket/main"
tl config add-repo prod-db "s3://prod-bucket/database"
tl config add-repo staging-main "s3://staging-bucket/main"

# Organize by purpose
tl config add-repo daily-backup "/mnt/daily"
tl config add-repo weekly-archive "/mnt/weekly"
tl config add-repo offsite-backup "sftp://backup-server:/vault"
```

## 🛠️ **Troubleshooting**

### Repository Not Found

```bash
# Error: Repository 'myrepo' not found
tl list -r myrepo

# Solution: Check available repositories
tl config list-repos

# Or add the repository
tl config add-repo myrepo "s3://bucket/path"
```

### No Default Repository

```bash
# Error: No repository specified and no default repository set
tl list

# Solution: Set a default repository
tl config set-default-repo production
```

### Repository Already Exists

```bash
# Error: Repository 'production' already exists
tl config add-repo production "s3://new-bucket"

# Solution: Remove old repository first or use different name
tl config remove-repo production
tl config add-repo production "s3://new-bucket"
```

## 🔗 **Integration with Existing Workflows**

### Scripts and Automation

```bash
#!/bin/bash
# Backup script using named repositories

# Set repository based on environment
if [[ "$ENV" == "production" ]]; then
    REPO="prod-backup"
else
    REPO="staging-backup"
fi

# Run backup
tl backup -r "$REPO" /important/data
```

### Multiple Environments

```bash
# Development
tl config add-repo dev-local "/tmp/dev-backup"
tl config set-default-repo dev-local

# Production
tl config add-repo prod-s3 "s3://prod-bucket/backup"
tl config set-default-repo prod-s3
```

This new repository management system makes TimeLocker much more user-friendly while maintaining full backward compatibility with existing configurations and
scripts.
