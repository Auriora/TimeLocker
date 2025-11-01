---
title: "Reference: Repository URI Guide"
id: "ref-uri-guide"
type: [ reference ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "01-11-2025"
tags: [ reference, storage, restic ]
links:
    tooling: [ ]
---

# Reference: Repository URI Guide

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: Developers, Operators integrating storage backends

## 1. Purpose

Define the canonical URI formats and credential requirements for storage backends supported by TimeLocker/Restic. Use this document when configuring
repositories, troubleshooting connectivity, or onboarding new storage targets.

## 2. Specification

### 2.1 Local Filesystem

- **Format**: `file:///path/to/repository`
- **Use cases**: Local disk, mounted drives, NFS shares.

```bash
# Local directory
file:///home/user/backups/restic-repo

# External drive
file:///mnt/backup-drive/restic-repo

# Network-mounted drive
file:///mnt/nas/backups/restic-repo
```

### 2.2 AWS S3

- **Format**: `s3:s3.amazonaws.com/bucket-name[/path]` or region-specific hostnames (`s3:s3.<region>.amazonaws.com/bucket`)
- **Environment variables**:
  ```bash
  export AWS_ACCESS_KEY_ID="your-access-key"
  export AWS_SECRET_ACCESS_KEY="your-secret-key"
  export AWS_DEFAULT_REGION="your-region"
  ```

```bash
# Default region (us-east-1)
s3:s3.amazonaws.com/my-backup-bucket

# Specific region
s3:s3.eu-west-1.amazonaws.com/my-backup-bucket

# With path prefix
s3:s3.us-west-2.amazonaws.com/my-bucket/backups/server1

# Example in-use repository
s3:s3.af-south-1.amazonaws.com/5560-restic
```

### 2.3 Google Cloud Storage

- **Format**: `gs:bucket-name:/path/to/repo`
- **Authentication**: `gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS`.

```bash
# Root of bucket
gs:my-backup-bucket:/

# With path
gs:my-backup-bucket:/backups/server1
```

### 2.4 Microsoft Azure Blob Storage

- **Format**: `azure:container-name:/path/to/repo`
- **Environment variables**:
  ```bash
  export AZURE_ACCOUNT_NAME="your-storage-account"
  export AZURE_ACCOUNT_KEY="your-account-key"
  ```

```bash
# Root of container
azure:backup-container:/

# With path
azure:backup-container:/backups/server1
```

### 2.5 Backblaze B2

- **Format**: `b2:bucket-name:/path/to/repo`
- **Environment variables**:
  ```bash
  export B2_ACCOUNT_ID="your-account-id"
  export B2_ACCOUNT_KEY="your-account-key"
  ```

```bash
# Root of bucket
b2:my-backup-bucket:/

# With path
b2:my-backup-bucket:/backups/server1
```

### 2.6 SFTP / SSH

- **Format**: `sftp:user@host:/path` (optional port: `sftp:user@host:port:/path`)
- **Authentication**: SSH keys recommended; password auth supported but less secure.

```bash
# Default SSH port (22)
sftp:backup@backup-server.com:/home/backup/restic-repo

# Custom port
sftp:backup@backup-server.com:2222:/home/backup/restic-repo

# SSH key authentication
sftp:backup@192.168.1.100:/var/backups/restic-repo
```

### 2.7 REST Server

- **Format**: `rest:http://host:port/path` or `rest:https://host:port/path`
- **Notes**: Prefer HTTPS; embed credentials using `rest:https://user:password@host:port/`.

```bash
# HTTP (development only)
rest:http://backup-server:8000/

# HTTPS (recommended)
rest:https://backup-server:8000/repo1

# With authentication
rest:https://user:password@backup-server:8000/
```

### 2.8 Rclone-Based Backends

- **Format**: `rclone:remote:path` (configure remote separately via `rclone config`)
- **Usage**: Suitable for providers exposed via Rclone; follow provider-specific guidance.

## 3. Usage Notes

- Include URI protocols (`https://`, `http://`) for S3-compatible services to avoid defaulting to AWS endpoints.
- When integrating self-hosted services (e.g., MinIO), configure TLS overrides (`insecure_tls`) via repository settings as required.
- Repository names in TimeLocker can reference these URIs, allowing credential management to resolve secrets per repository.
- Test connectivity with the provider’s native CLI (e.g., `aws`, `gsutil`, `az`, `rclone`) before configuring TimeLocker.

## 4. Change Log

- 01-11-2025: Reformatted to reference template; added Rclone guidance.
- 19-12-2024: Initial draft created.

# References

- Restic documentation: <https://restic.readthedocs.io/en/latest/020_backends.html>
- TimeLocker user guides: `docs/guides/user/s3-compatible-services.md`
