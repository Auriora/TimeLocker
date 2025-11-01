---
title: "User Guide: Repository Management"
id: "user-guide-repository-management"
type: [ guide ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "01-11-2025"
tags: [guide, user, repositories]
links:
  tooling: []
---

# User Guide: Repository Management

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: End Users

## 1. Purpose

Introduce named repositories in TimeLocker, enabling human-friendly aliases, defaults, and streamlined CLI usage while maintaining compatibility with raw URIs.

## 2. Goal

By the end of this guide you can add, list, update, and remove named repositories, configure defaults, and migrate from URI-only workflows.

## 3. Prerequisites

- TimeLocker CLI installed.
- Access to repository URIs (local, S3, B2, SFTP, etc.).
- Optional: credentials configured per repository (`docs/guides/user/per-repo-credentials.md`).

## 4. Step-by-Step Instructions

### 4.1 Add Repositories

```bash
tl repos add <name> <uri> [options]
tl repos add production "s3:s3.af-south-1.amazonaws.com/prod-backup"
tl repos add local-backup file:///home/user/backups
```

Use `--description` and `--set-default` to annotate and set defaults.

### 4.2 List and Inspect

```bash
tl repos list
```

Displays name, type, URI, description, and default indicator.

### 4.3 Manage Defaults

```bash
tl repos default <name>
```

Once a default is set, commands such as `tl snapshots list` and `tl backup create` omit `--repository` unless you override it.

### 4.4 Remove or Modify Repositories

```bash
tl repos remove <name>
```

Prompts for confirmation before deletion.

### 4.5 Use Named Repositories in Commands

```bash
tl snapshots list --repository production
 tl backups create /home/user/docs --repository production
```

Defaults allow `tl snapshots list` without specifying a repository.

### 4.6 Repository Type Detection

TimeLocker auto-detects type from URI:

| URI Pattern          | Type         |
|----------------------|--------------|
| `s3://` or `s3:`     | S3           |
| `b2://` or `b2:`     | Backblaze B2 |
| `sftp://` or `sftp:` | SFTP         |
| `file://`            | Local        |

### 4.7 Configuration Structure

Named repositories appear in `config.json`:

```json
{
  "general": {"default_repository": "production"},
  "repositories": {
    "production": {
      "uri": "s3:s3.af-south-1.amazonaws.com/prod-backup",
      "description": "Production backup repository",
      "type": "s3",
      "created": "2025-06-30T09:00:00"
    }
  }
}
```

### 4.8 Migrate From Environment Variables

```bash
export RESTIC_REPOSITORY="s3:s3.region.amazonaws.com/bucket"
export RESTIC_PASSWORD="your-password"
# tl config import restic  # (planned)
# Manual migration
 tl repos add main "s3:s3.region.amazonaws.com/main-backup"
 tl repos default main
```

## 5. Troubleshooting

- **Repository not found**: Re-run `tl repos list` to ensure the alias exists and check for typos.
- **Default repository unexpected**: Run `tl repos default <name>` to update, or `tl repos list` to verify the default indicator.
- **Legacy URIs still required**: All commands accept URIs; named repositories are an additive convenience.

## 6. Frequently Asked Questions (FAQ)

- **Can I rename a repository?** Remove and re-add with the new name; configuration entries use the alias as a key.
- **Do defaults affect automation?** Yes, scheduled scripts without `--repository` target the current default.
- **How should I name repositories?** Use descriptive, hyphenated names (`prod-main`, `archive-offsite`) for clarity.

# References

- Credentials guide: `docs/guides/user/per-repo-credentials.md`
- Installation guide: `docs/guides/user/installation.md`
- S3 compatibility: `docs/guides/user/s3-compatible-services.md`
