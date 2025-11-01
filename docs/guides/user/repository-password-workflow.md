---
title: "User Guide: Repository Password Workflow"
id: "user-guide-repository-passwords"
type: [ guide ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "01-11-2025"
tags: [guide, user, credentials]
links:
  tooling: []
---

# User Guide: Repository Password Workflow

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: End Users

## 1. Purpose

Describe how TimeLocker stores and resolves repository passwords without the deprecated `--password` flag, enabling secure non-interactive operations.

## 2. Goal

After this guide you can add repositories, initialise new ones, and automate backups while TimeLocker manages passwords through the credential manager or
environment variables.

## 3. Prerequisites

- TimeLocker CLI v1.0.0 or later.
- Credential Manager configured (auto-unlock or master password).
- Optional: environment variables `TIMELOCKER_PASSWORD` or `RESTIC_PASSWORD` for legacy workflows.

## 4. Step-by-Step Instructions

### 4.1 Add an Existing Repository

```bash
tl config repositories add production "s3://bucket/backup" --description "Production" --set-default
```

Passwords are detected from the credential manager or environment variables; no `--password` flag is required.

### 4.2 Create a New Repository

```bash
tl config repositories add newrepo "/path/to/new/repo"
tl repo init newrepo
```

During `tl repo init` TimeLocker persists the password via the credential manager if available.

### 4.3 Configure Automation Environment

```bash
export TIMELOCKER_PASSWORD="secure_password"
tl config repositories add automated "/backup/repo"
```

Passwords detected from environment variables are stored for future runs.

### 4.4 Understand Storage Flow

1. `tl config repositories add` – stores passwords when credential manager or environment variables provide them.
2. `tl repo init` – resolves and stores passwords before initialisation.
3. `tl credentials store <repo>` – manually persist passwords as needed.

### 4.5 Command Reference

```bash
tl config repositories add <name> <uri> [--description TEXT] [--set-default]
tl config repositories add new "/path" && tl repo init new
export TIMELOCKER_PASSWORD="secret123" && tl config repositories add auto "/backup/repo"
```

## 5. Troubleshooting

- **Credential manager locked**: Run `tl credentials unlock` or respond to prompts; without access TimeLocker falls back to environment variables.
- **Password missing after add**: Rerun `tl credentials store <repo>` or set `TIMELOCKER_PASSWORD` and repeat the `tl config repositories add` command.
- **Automation failure**: Confirm environment variables are exported in scheduled scripts and audit logs show successful storage.

## 6. Frequently Asked Questions (FAQ)

- **How are passwords stored?** Encrypted using Fernet (AES-128 + HMAC) in `~/.TimeLocker/credentials/credentials.enc` with audit logs in
  `credential_audit.log`.
- **What is the precedence order?** Explicit CLI parameters (future), credential manager, environment variables, then interactive prompt if allowed.
- **What ID ties passwords to repositories?** A SHA-256 hash of the repository location (`hashlib.sha256(location).hexdigest()[:16]`) ensures consistent
  mapping.

# References

- Credential storage API: `tl credentials store`, `tl repos credentials-set/show/remove`
- Automation patterns: `docs/guides/developer/automation-examples.md`
- Per-repository credentials guide: `docs/guides/user/per-repo-credentials.md`
