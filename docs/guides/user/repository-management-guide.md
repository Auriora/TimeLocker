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
tl repos add <name> <uri> [options]

# Examples
tl repos add production "s3:s3.af-south-1.amazonaws.com/prod-backup"
tl repos add local-backup file:///home/user/backups
tl repos add remote-sftp "sftp://user@server:/backup/path"

# Add with description and set as default
tl repos add production "s3://bucket/path" \
  --description "Production backup repository" \
  --set-default
```

### List Repositories

```bash
# List all configured repositories
tl repos list
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
tl repos default <name>

# Example
tl repos default production
```

### Remove a Repository

```bash
# Remove a repository (with confirmation)
tl repos remove <name>

# Example
tl repos remove old-backup
```

## 🚀 **Using Named Repositories**

### With Repository Names

```bash
# Use repository name instead of URI
tl snapshots list --repository production
tl backup create /home/user/documents --repository production
tl snapshots restore <snapshot-id> /restore/path --repository production

# All commands support repository names
tl repos init new-repo
tl backup verify --repository production
```

### With Default Repository

```bash
# No need to specify --repository when using default repository
tl snapshots list
tl backup create /home/user/documents
tl snapshots restore <snapshot-id> /restore/path
```

### Backward Compatibility

```bash
# Direct URIs still work
tl snapshots list --repository "s3://bucket/path"
tl backup create /home/user/docs --repository file:///local/path
```

## 🔧 **Repository Types**

TimeLocker automatically detects repository types:

| URI Pattern          | Type         | Example                             |
|----------------------|--------------|-------------------------------------|
| `s3://` or `s3:`     | S3           | `s3:s3.region.amazonaws.com/bucket` |
| `b2://` or `b2:`     | Backblaze B2 | `b2://bucket/path`                  |
| `sftp://` or `sftp:` | SFTP         | `sftp://user@host:/path`            |
| `file://`            | Local        | `file:///home/user/backup`          |

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
      "uri": "file:///tmp/test-backup",
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
tl config import restic
```
> Note: `tl config import restic` is not yet implemented in the current CLI. Please configure repositories manually using `tl repos add` and set the default with `tl repos default`.


### Manual Migration

```bash
# Add your existing repositories with names
tl repos add main "s3:s3.region.amazonaws.com/main-backup"
tl repos add archive file:///mnt/archive/backup

# Set a default
tl repos default main

# Test the migration
tl snapshots list --repository main  # Should work the same as before
tl snapshots list                    # Uses default repository
```

## 💡 **Best Practices**

### Repository Naming

- Use descriptive names: `production`, `staging`, `archive`
- Avoid spaces: use `local-test` instead of `local test`
- Be consistent: `prod-db`, `prod-files`, `prod-logs`

### Default Repository

- Set your most frequently used repository as default
- Use specific names for special operations
- Change default as needed: `tl repos default staging`

### Organization

```bash
# Organize by environment
tl repos add prod-main "s3://prod-bucket/main"
tl repos add prod-db "s3://prod-bucket/database"
tl repos add staging-main "s3://staging-bucket/main"

# Organize by purpose
tl repos add daily-backup file:///mnt/daily
tl repos add weekly-archive file:///mnt/weekly
tl repos add offsite-backup "sftp://backup-server:/vault"
```

## 🛠️ **Troubleshooting**

### Repository Not Found

```bash
# Error: Repository 'myrepo' not found
tl snapshots list --repository myrepo

# Solution: Check available repositories
tl repos list

# Or add the repository
tl repos add myrepo "s3://bucket/path"
```

### No Default Repository

```bash
# Error: No repository specified and no default repository set
tl snapshots list

# Solution: Set a default repository
tl repos default production
```

### Repository Already Exists

```bash
# Error: Repository 'production' already exists
tl repos add production "s3://new-bucket"

# Solution: Remove old repository first or use different name
tl repos remove production
tl repos add production "s3://new-bucket"
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
tl backup create /important/data --repository "$REPO"
```

### Multiple Environments

```bash
# Development
tl repos add dev-local file:///tmp/dev-backup
tl repos default dev-local

# Production
tl repos add prod-s3 "s3://prod-bucket/backup"
tl repos default prod-s3
```

This new repository management system makes TimeLocker much more user-friendly while maintaining full backward compatibility with existing configurations and
scripts.
