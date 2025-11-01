---
title: "User Guide: Timeshift Import"
id: "user-guide-timeshift-import"
type: [ guide ]
status: [ approved ]
owner: "Documentation Team"
last_reviewed: "01-11-2025"
tags: [ guide, user, migration ]
links:
    tooling: [ ]
---

# User Guide: Timeshift Import

- **Owner**: Documentation Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: End Users migrating from Timeshift

## 1. Purpose

Assist users in importing Timeshift JSON configurations into TimeLocker, preserving backup paths, exclude patterns, and repository mappings.

## 2. Goal

After this guide you can run the Timeshift importer, review mappings, and adjust repositories and targets for TimeLocker.

## 3. Prerequisites

- Timeshift configuration file accessible (`/etc/timeshift/timeshift.json` or alternative path).
- TimeLocker CLI installed with permission to read Timeshift configs.
- Awareness that Timeshift (filesystem snapshots) differs from TimeLocker (Restic backups).

## 4. Step-by-Step Instructions

### 4.1 Run the Importer

```bash
tl config import timeshift               # Default location
 tl config import timeshift --config-file /path/to/timeshift.json
 tl config import timeshift --dry-run      # Preview changes
```

### 4.2 Advanced Options

```bash
tl config import timeshift \
  --repo-name "my_backup_repo" \
  --target-name "system_backup" \
  --repo-path "/mnt/backup/timeshift"

tl config import timeshift --paths /home --paths /etc --paths /usr/local
 tl config import timeshift --yes          # Skip confirmation prompts
```

### 4.3 Understand Configuration Mapping

| Timeshift Setting         | TimeLocker Equivalent | Notes                                               |
|---------------------------|-----------------------|-----------------------------------------------------|
| `backup_device_uuid`      | Repository location   | Resolved to mount path + `/timeshift` when possible |
| Device type               | Repository type       | Set to `local`                                      |
| `exclude`, `exclude-apps` | `exclude_patterns`    | Converted to glob patterns with `**/` prefix        |
| System backup             | Backup paths          | Defaults to `/`                                     |
| Schedule settings         | —                     | Not imported                                        |

Default excludes applied automatically:

```
**/proc/**
**/sys/**
**/dev/**
**/tmp/**
**/run/**
**/mnt/**
**/media/**
**/.cache/**
**/lost+found/**
```

### 4.4 Resolve UUIDs

Importer attempts to convert UUIDs via `blkid` and `findmnt`. If resolution fails:

```bash
tl config import timeshift --repo-path "/mnt/backup/timeshift"
```

### 4.5 Complete Migration

1. Dry-run: `tl config import timeshift --dry-run`
2. Review output (repository path, backup paths, excludes).
3. Execute import with final options.
4. Initialise repository if required: `tl repos init timeshift_imported`
5. Test backup: `tl backup timeshift_system --dry-run`

### 4.6 Post-Import Checklist

1. Confirm repository path correctness.
2. Adjust backup paths to narrow scope if desired.
3. Review exclude patterns for accuracy.
4. Set up scheduling manually (systemd/cron).
5. Run backups to validate behaviour.

## 5. Troubleshooting

- **UUID resolution fails**: Use `sudo findmnt | grep timeshift` and specify `--repo-path` manually.
- **Permission errors**: Run importer with appropriate privileges (`sudo`) or copy the config to a readable location.
- **BTRFS warnings**: Expected; TimeLocker uses Restic and cannot import existing BTRFS snapshots.

## 6. Frequently Asked Questions (FAQ)

- **Where does the importer look for configs?** `/etc/timeshift/timeshift.json` then `/etc/timeshift.json`.
- **Are Timeshift schedules imported?** No, configure TimeLocker scheduling separately.
- **Does the importer create repositories automatically?** It configures them; run `tl repos init <name>` if the repository does not exist yet.

# References

- Integration scripts: `tl config import timeshift --help`
- Scheduling guide: `docs/guides/developer/scheduling-guide.md`
- Repository management: `docs/guides/user/repository-management-guide.md`
