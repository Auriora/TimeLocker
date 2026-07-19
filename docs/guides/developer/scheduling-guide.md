---
title: "Operator Guide: Scheduling Backups"
id: "dev-guide-scheduling"
type: [ guide ]
status: [ approved ]
owner: "Operations Team"
last_reviewed: "19-07-2026"
tags: [guide, developer, operator, scheduling]
links:
  tooling: []
---

# Operator Guide: Scheduling Backups

- **Owner**: Operations Team
- **Status**: Approved
- **Audience**: Developers and operators

## Purpose and boundaries

Use TimeLocker to define a recurring backup, generate reviewable cron or
systemd assets, and stage a migration from another scheduler. Schedule
generation does not install or enable anything. Installing a system unit,
choosing repository credentials, and disabling an existing backup job are
separate operator decisions.

Each executable schedule must explicitly bind:

- one repository name or URI;
- either one configured selection or one or more source paths;
- its configuration directory when it is not the default; and
- an optional protected environment-file path, never copied secret values.

Schedules may also persist repeatable `--tags` and `--exclude` values,
`--compression auto|off|max`, and the
`--one-file-system/--cross-filesystems` traversal choice. Missing fields retain
the legacy defaults and emit no additional backup arguments.

## Create a disabled schedule

Use a selection template:

```bash
tl schedule create nightly-documents \
  --repository primary \
  --selection documents \
  --environment-file ~/.config/timelocker/backup.env \
  --frequency daily \
  --disabled \
  --config-dir ~/.config/timelocker
```

Or supply repeatable direct sources:

```bash
tl schedule create nightly-config \
  --repository primary \
  --source /etc \
  --source /srv/application/config \
  --environment-file ~/.config/timelocker/backup.env \
  --system \
  --tags Bruce-5560 \
  --exclude 'cache/*' \
  --compression max \
  --one-file-system \
  --cron '30 1 * * *' \
  --disabled \
  --config-dir ~/.config/timelocker
```

`--system` preserves the privilege boundary for sources that require root
access. It does not grant privileges or install a unit.

Protect the referenced environment file and keep it outside generated assets:

```bash
chmod 600 ~/.config/timelocker/backup.env
```

See [Per-Repository Credentials](../user/per-repo-credentials.md) for the
credential choices. Do not copy a masked credential from another backup tool.

## Generate and review assets

Generate both candidate formats without installing either:

```bash
mkdir -p ~/.local/share/timelocker/staged-schedules
tl schedule generate-scripts nightly-config \
  --platform systemd \
  --output ~/.local/share/timelocker/staged-schedules \
  --config-dir ~/.config/timelocker
tl schedule generate-scripts nightly-config \
  --platform cron \
  --output ~/.local/share/timelocker/staged-schedules \
  --config-dir ~/.config/timelocker
```

Before installation:

1. Confirm the generated backup command contains `backup create`, the intended
   repository, all sources or the selection, the intended `--config-dir`, and
   every reviewed tag, exclusion, compression, and traversal option.
2. Confirm it contains no password or other credential value.
3. Run the generated wrapper manually in the intended user or root context.
4. Complete a backup and a digest-verified TimeLocker restore.
5. Review the displayed install commands; generation has not run them.

For systemd assets, `EnvironmentFile=` references the protected file. The cron
wrapper sources the same file with fail-fast shell settings. A missing environment file causes the
backup to fail instead of silently switching credentials.

## Staged NPBackup replacement

Keep the NPBackup job enabled while TimeLocker is staged:

1. Discover and record the actual NPBackup scheduling mechanism and protected
   source list using its supported, masked interface.
2. Create a disabled TimeLocker schedule with matching sources and an
   independently chosen TimeLocker credential source.
3. Generate and review the TimeLocker assets.
4. With explicit approval, install the system-level timer or root cron entry.
5. Observe successful scheduled TimeLocker backups and perform a restore test.
6. Only then make a separate cutover decision to disable NPBackup.

Do not extract masked NPBackup secrets, install a privileged timer, or disable
NPBackup as part of schedule generation.

## Validation and troubleshooting

```bash
tl schedule list --json --config-dir ~/.config/timelocker
tl schedule show nightly-config --config-dir ~/.config/timelocker
bash -n ~/.local/share/timelocker/staged-schedules/nightly-config_cron.sh
systemd-analyze verify \
  ~/.local/share/timelocker/staged-schedules/timelocker-nightly-config.service \
  ~/.local/share/timelocker/staged-schedules/timelocker-nightly-config.timer
```

`schedule list`, `schedule show`, and `schedule test` expose or validate the
stored execution options without reading the referenced environment file.
Cron, systemd, and Windows assets are rendered from the same argument-safe
command builder, so spaces and shell metacharacters remain single arguments.

If the command reports a missing repository, selection, or source, recreate or
edit the schedule so the execution target is explicit. If access fails only in
the scheduler, compare its user, environment-file permissions, executable
path, and configuration directory with the successful manual run.

## References

- [Installation](../user/installation.md)
- [Per-Repository Credentials](../user/per-repo-credentials.md)
- [Scheduling Architecture](../../2-architecture/scheduling-system.md)
