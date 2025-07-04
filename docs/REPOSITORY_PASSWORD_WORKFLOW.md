# Repository Password Management Workflow

## Overview

TimeLocker now supports password storage during repository addition, making it easier to work with existing repositories and enabling seamless non-interactive
operations.

## 🔄 **Enhanced Workflow**

### **Scenario 1: Adding an Existing Repository**

When you have an existing restic repository (created outside TimeLocker):

```bash
# Add existing repository with password
tl config repositories add production "s3://bucket/backup" \
  --password "existing_repo_password" \
  --description "Production backup repository" \
  --set-default

# Or let TimeLocker prompt for password
tl config repositories add production "s3://bucket/backup"
# TimeLocker will ask: "Would you like to store a password for repository 'production'?"
# If yes: "Password for repository 'production': "
```

**Result:**

- ✅ Repository added to TimeLocker configuration
- ✅ Password encrypted and stored in credential manager
- ✅ Ready for non-interactive operations

### **Scenario 2: Creating a New Repository**

For brand new repositories:

```bash
# Step 1: Add repository configuration
tl config repositories add newrepo "/path/to/new/repo" \
  --description "New backup repository"

# Step 2: Initialize the repository (creates it)
tl repo init newrepo --password "new_secure_password"
```

**Result:**

- ✅ Repository configuration added
- ✅ Repository initialized with restic
- ✅ Password automatically stored during initialization

### **Scenario 3: Environment Variable Setup**

For automated systems:

```bash
# Set environment variable
export TIMELOCKER_PASSWORD="secure_password"

# Add repository (password detected automatically)
tl config repositories add automated "/backup/repo"
```

**Result:**

- ✅ Repository added with environment variable password
- ✅ Password stored in credential manager for future use
- ✅ Environment variable still works as fallback

## 🔐 **Password Storage Details**

### **When Passwords Are Stored**

1. **During `tl config repositories add`** (NEW!)
    - If `--password` provided → stored immediately
    - If environment variable set → detected and stored
    - If neither → prompts user to optionally store password

2. **During `tl repo init`**
    - Password required for initialization → automatically stored

3. **Via `tl credentials store`**
    - Manual credential storage for any repository

### **Password Resolution Priority**

When TimeLocker needs a repository password:

1. **Explicit password** (provided directly in command)
2. **Credential manager** (with auto-unlock for non-interactive)
3. **Environment variables** (`TIMELOCKER_PASSWORD`, `RESTIC_PASSWORD`)
4. **User prompt** (if interactive mode allowed)

### **Repository ID Generation**

Passwords are stored using a repository ID based on the repository location:

```python
repository_id = hashlib.sha256(repository_location.encode()).hexdigest()[:16]
```

This ensures:

- ✅ Same repository = same ID regardless of how it's accessed
- ✅ Different repositories = different IDs (no conflicts)
- ✅ Consistent across TimeLocker sessions

## 🚀 **Usage Examples**

### **Quick Setup for Existing Repository**

```bash
# One command setup for existing repository
tl config repositories add prod "s3://company-backup/prod" \
  --password "$(pass show backup/prod)" \
  --set-default

# Ready to use immediately
tl list -r prod
tl backup documents -r prod
```

### **Automated System Setup**

```bash
#!/bin/bash
# Setup script for automated backups

export TIMELOCKER_PASSWORD="$BACKUP_PASSWORD"

# Add repositories (passwords auto-detected and stored)
tl config repositories add daily "/backup/daily"
tl config repositories add weekly "/backup/weekly" --set-default

# Backups will now work without prompts
tl backup documents -r daily
tl backup system -r weekly
```

### **Migration from Raw Restic**

```bash
# You have existing restic repositories
export RESTIC_REPOSITORY="/backup/repo"
export RESTIC_PASSWORD="existing_password"

# Import into TimeLocker
tl config repositories add imported "$RESTIC_REPOSITORY"
# Password automatically detected from RESTIC_PASSWORD

# Now use TimeLocker commands
tl list -r imported
tl backup documents -r imported
```

## 🔒 **Security Benefits**

### **Enhanced Security**

- **Encrypted storage** using Fernet (AES 128 + HMAC)
- **Auto-unlock** using system fingerprint for non-interactive operations
- **No clear-text passwords** in configuration files
- **Audit logging** of all credential access

### **Operational Benefits**

- **No password prompts** for automated backups
- **Environment variable fallback** for containers/CI
- **Backward compatibility** with existing workflows
- **Cross-platform support** (Linux, Windows, macOS)

## 📋 **Command Reference**

### **Add Repository with Password**

```bash
tl config repositories add <name> <uri> [OPTIONS]

OPTIONS:
  --password, -p TEXT        Repository password
  --description, -d TEXT     Repository description  
  --set-default             Set as default repository
  --config-dir PATH         Configuration directory
  --verbose, -v             Enable verbose output
```

### **Examples**

```bash
# Existing repository with known password
tl config repositories add prod "s3://bucket/path" --password "secret123"

# Existing repository, prompt for password
tl config repositories add prod "s3://bucket/path"

# New repository (add config, then initialize)
tl config repositories add new "/path/to/new"
tl repo init new --password "newsecret"

# Environment variable detection
export TIMELOCKER_PASSWORD="secret123"
tl config repositories add auto "/backup/repo"  # Password auto-detected
```

## 🎯 **Best Practices**

### **For Production Systems**

1. **Use credential manager** for secure password storage
2. **Set environment variables** as fallback for containers
3. **Enable auto-unlock** for non-interactive operations
4. **Monitor audit logs** for security compliance

### **For Development**

1. **Use different repositories** for dev/staging/prod
2. **Store passwords during setup** to avoid repeated prompts
3. **Use descriptive names** for easy identification
4. **Set appropriate defaults** for common workflows

### **For Migration**

1. **Import existing repositories** with current passwords
2. **Test credential storage** before removing environment variables
3. **Update automation scripts** to use TimeLocker commands
4. **Verify backup operations** work without prompts

This enhanced workflow makes TimeLocker much more user-friendly for both existing repository integration and automated operations! 🚀
