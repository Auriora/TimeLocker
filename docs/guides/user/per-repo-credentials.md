---
title: "User Guide: Per-Repository Credentials"
id: "user-guide-per-repo-credentials"
type: [ guide ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "18-07-2026"
tags: [guide, user, credentials]
links:
  tooling: []
---

# User Guide: Per-Repository Credentials

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 18-07-2026
- **Audience**: End Users

## 1. Purpose

Explain how to store and manage distinct credentials for each TimeLocker repository (S3, MinIO, Backblaze B2), ensuring secure, encrypted handling of secrets.

## 2. Goal

After completing this guide you can add repositories with unique credentials, rotate or remove stored secrets, and understand how TimeLocker resolves
authentication data.

## 3. Prerequisites

- TimeLocker CLI installed.
- Credential Manager initialised with an operator-chosen master password.
- Repositories already defined or planned (URIs for S3, MinIO, B2, etc.).

## 4. Step-by-Step Instructions

### 4.1 Add a Repository With Credentials

```bash
$ tl repos add my-minio "s3://minio.lan/my-bucket"
Would you like to store a password for repository 'my-minio'? [y/N]: y
Password for repository 'my-minio': ********
Would you like to store AWS credentials for repository 'my-minio'? [Y/n]: y
```

Provide access key, secret, optional region when prompted. On success the CLI confirms the repository, description, default flag, and stored credentials.

### 4.2 Use the Repository

Stored credentials load automatically for subsequent operations:

```bash
tl backup -r my-minio /data
```

No additional prompts required.

For unattended operation, provide the credential-store master password through
one explicit secret source:

```bash
# Process environment (suitable when a service manager injects secrets)
export TIMELOCKER_MASTER_PASSWORD='use-your-secret-provider-here'

# Or a protected file
install -m 600 /dev/null "$HOME/.config/timelocker/master-password"
export TIMELOCKER_MASTER_PASSWORD_FILE="$HOME/.config/timelocker/master-password"
```

Write the password into the protected file using your normal secret-management
tool. On POSIX systems TimeLocker rejects password files accessible to group or
other users. It also rejects missing, empty, non-regular, and symbolic files.
Do not place the password itself in shell history or version control.

### 4.3 Update Stored Credentials

```bash
tl repos credentials-set my-minio
```

Enter new access key/secret when prompted. The CLI confirms successful storage.

### 4.4 Check Credential Status

```bash
tl repos credentials-show my-minio
```

Displays whether credentials exist without revealing secrets.

### 4.5 Remove Stored Credentials

```bash
tl repos credentials-remove my-minio
```

Falls back to environment variables or command parameters for authentication.

### 4.6 Work With Multiple Repositories

Example:

```bash
# MinIO
$ tl repos add minio-prod "s3://minio-prod.company.com/backups"
# AWS S3
$ tl repos add aws-backup "s3://s3.us-east-1.amazonaws.com/my-backups"
```

Each repository retains its own credentials, enabling seamless switching.

### 4.7 Credential Resolution Order

1. Stored per-repository credentials.
2. Explicit parameters provided programmatically.
3. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.).

## 5. Troubleshooting

- **Credential manager locked**: Unlock when prompted or run `tl credentials unlock` before repository commands.
- **Unattended unlock fails**: Set `TIMELOCKER_MASTER_PASSWORD`, or set
  `TIMELOCKER_MASTER_PASSWORD_FILE` to a regular file restricted to its owner.
- **Store was created by an older auto-unlock build**: Host-derived keys are no
  longer supported because they were predictable. Treat repository credentials
  in that store as exposed, re-enter them into a store protected by an
  operator-chosen password, and rotate the repository-side secrets.
- **Missing credentials**: Re-run `tl repos credentials-set <name>` or export environment variables temporarily.
- **Audit trail review**: Check `~/.timelocker/credentials/credential_audit.log` for credential operations.

## 6. Frequently Asked Questions (FAQ)

- **Where are credentials stored?** Encrypted in the active TimeLocker
  configuration directory's `credentials/credentials.enc` file.
- **Do credentials sync to configuration files?** No, `config.json` never stores secrets; the credential store or environment variables provide them.
- **How does non-interactive unlock work?** TimeLocker uses only an explicit
  `TIMELOCKER_MASTER_PASSWORD` value or protected
  `TIMELOCKER_MASTER_PASSWORD_FILE`; it never derives the password from the host.

# References

- Credential manager implementation: `docs/3-implementation/command-builder.md`
- Repository management guide: `docs/guides/user/repository-management-guide.md`
- AWS credential environment variables: <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html>
