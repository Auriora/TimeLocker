# Repository URI Guide for TimeLocker

This guide explains how to construct repository URIs for different storage backends supported by restic/TimeLocker.

## 📍 Repository URI Formats

### 1. **Local Filesystem**

Store backups on local disk or mounted drives.

**Format:**

```
/path/to/repository
file:///path/to/repository
```

**Examples:**

```bash
# Local directory
/home/user/backups/restic-repo

# External drive
/mnt/backup-drive/restic-repo

# Network mounted drive
/mnt/nas/backups/restic-repo

# Explicit file protocol
file:///home/user/backups/restic-repo
```

### 2. **AWS S3**

Store backups in Amazon S3 buckets.

**Format:**

```
s3:s3.amazonaws.com/bucket-name
s3:s3.amazonaws.com/bucket-name/path/to/repo
s3:s3.region.amazonaws.com/bucket-name
```

**Examples:**

```bash
# Default region (us-east-1)
s3:s3.amazonaws.com/my-backup-bucket

# Specific region
s3:s3.eu-west-1.amazonaws.com/my-backup-bucket

# With path prefix
s3:s3.us-west-2.amazonaws.com/my-bucket/backups/server1

# Your current repository
s3:s3.af-south-1.amazonaws.com/5560-restic
```

**Required Environment Variables:**

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="your-region"
```

### 3. **Google Cloud Storage**

Store backups in Google Cloud Storage buckets.

**Format:**

```
gs:bucket-name:/path/to/repo
```

**Examples:**

```bash
# Root of bucket
gs:my-backup-bucket:/

# With path
gs:my-backup-bucket:/backups/server1
```

**Authentication:**

- Use `gcloud auth application-default login`
- Or set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### 4. **Microsoft Azure Blob Storage**

Store backups in Azure Blob Storage.

**Format:**

```
azure:container-name:/path/to/repo
```

**Examples:**

```bash
# Root of container
azure:backup-container:/

# With path
azure:backup-container:/backups/server1
```

**Required Environment Variables:**

```bash
export AZURE_ACCOUNT_NAME="your-storage-account"
export AZURE_ACCOUNT_KEY="your-account-key"
```

### 5. **Backblaze B2**

Store backups in Backblaze B2 cloud storage.

**Format:**

```
b2:bucket-name:/path/to/repo
```

**Examples:**

```bash
# Root of bucket
b2:my-backup-bucket:/

# With path
b2:my-backup-bucket:/backups/server1
```

**Required Environment Variables:**

```bash
export B2_ACCOUNT_ID="your-account-id"
export B2_ACCOUNT_KEY="your-account-key"
```

### 6. **SFTP/SSH**

Store backups on remote servers via SFTP.

**Format:**

```
sftp:user@host:/path/to/repo
sftp:user@host:port:/path/to/repo
```

**Examples:**

```bash
# Default SSH port (22)
sftp:backup@backup-server.com:/home/backup/restic-repo

# Custom port
sftp:backup@backup-server.com:2222:/home/backup/restic-repo

# With SSH key authentication
sftp:backup@192.168.1.100:/var/backups/restic-repo
```

**Authentication:**

- SSH key authentication (recommended)
- Password authentication (less secure)

### 7. **REST Server**

Store backups on a restic REST server.

**Format:**

```
rest:http://host:port/path
rest:https://host:port/path
```

**Examples:**

```bash
# HTTP (not recommended for production)
rest:http://backup-server:8000/

# HTTPS (recommended)
rest:https://backup-server:8000/repo1

# With authentication
rest:https://user:password@backup-server:8000/
```

### 8. **Rclone**

Use rclone for various cloud storage providers.

**Format:**

```
rclone:remote:path/to/repo
```

**Examples:**

```bash
# Dropbox via rclone
rclone:dropbox:backups/restic-repo

# OneDrive via rclone
rclone:onedrive:backups/restic-repo

# Any rclone-supported backend
rclone:myremote:path/to/repo
```

## 🔍 **How to Find Your Repository URI**

### Method 1: Check Environment Variables

```bash
echo $RESTIC_REPOSITORY
```

### Method 2: Check TimeLocker Configuration

```bash
cd src && python3 -m TimeLocker.cli config list-repos
```

### Method 3: Check Original Configuration Files

```bash
# From your extracted config
cat extracted_configs/restic_config.json | jq '.repositories'

# From original restic config
sudo cat /var/restic/.resticrc | grep RESTIC_REPOSITORY
```

## 🛠️ **Creating New Repository URIs**

### For AWS S3:

1. **Create S3 bucket** in AWS Console
2. **Get credentials** (Access Key ID + Secret Access Key)
3. **Construct URI:** `s3:s3.region.amazonaws.com/bucket-name`

### For Local Storage:

1. **Create directory:** `mkdir -p /path/to/backup/repo`
2. **Set permissions:** `chmod 700 /path/to/backup/repo`
3. **Use path as URI:** `/path/to/backup/repo`

### For SFTP:

1. **Set up SSH access** to remote server
2. **Create directory** on remote server
3. **Construct URI:** `sftp:user@host:/path/to/repo`

## 📋 **Using Repository URIs with TimeLocker**

### List Snapshots:

```bash
cd src && python3 -m TimeLocker.cli list -r "s3:s3.af-south-1.amazonaws.com/5560-restic"
```

### Create Backup:

```bash
cd src && python3 -m TimeLocker.cli backup -r "s3:s3.af-south-1.amazonaws.com/5560-restic" /path/to/backup
```

### Import from Environment:

```bash
# Set environment variables first
export RESTIC_REPOSITORY="s3:s3.region.amazonaws.com/bucket"
export RESTIC_PASSWORD="your-password"

# Then import
cd src && python3 -m TimeLocker.cli config import-restic
```

## 🔐 **Security Notes**

1. **Always use encryption** (restic encrypts by default)
2. **Secure your repository password** - store it safely
3. **Use HTTPS/TLS** for remote repositories when possible
4. **Limit access permissions** on local repositories
5. **Use IAM roles** instead of access keys when possible (AWS)

## 🎯 **Your Current Setup**

Based on your extracted configuration:

- **Repository URI:** `s3:s3.af-south-1.amazonaws.com/5560-restic`
- **Type:** AWS S3
- **Region:** af-south-1 (Africa - Cape Town)
- **Encryption:** ✅ Enabled
- **Status:** ✅ Working and accessible

You can use this URI directly with TimeLocker commands!
