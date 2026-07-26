---
title: System CLI, tray, retention, and control-plane change impact
doc_type: spec
artifact_type: change-impact
status: draft
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Change Impact

## Purpose

Record the durable behavior changed by Spec 009: system command discovery,
contextual machine operations, independent tray ownership, structured system
run visibility, group authorization, and automatic retention.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `CHARTER.md` | CLI-first backup orchestration, safety, stable automation, observable operation | high | Governing mandate |
| `docs/2-architecture/system-architecture.md` | CLI, immutable launcher, protected backend, tray, run-store, and repository boundaries | high | Promoted by T011 |
| `docs/2-architecture/scheduling-system.md` | User schedules plus protected backup/retention triggers, locking, and run state | high | Promoted by T011 |
| `docs/3-implementation/service-layer-integration.md` | Focused services should own new behavior instead of expanding the compatibility facade | high | Guides client/service placement |
| `docs/guides/developer/scheduling-guide.md` | User/system scheduling, retention safety, cutover, and rollback | high | Promoted by T011 |
| `docs/guides/user/installation.md` | User/source install and protected Linux deployment boundaries | high | Promoted by T011 |
| `docs/SYSTEM-TRAY-SETUP.md` | Independent unprivileged tray installation and behavior | high | Superseded by T011 |
| `src/TimeLocker/cli_modules/commands/monitoring.py` | `logs view` reads the caller's cache log and ignores system run history | high | Bug and UX migration seam |
| `src/TimeLocker/monitoring/notification_service.py` | Notification construction initializes the system tray | high | Headless warning root cause |

## Change Type

- **Primary type:** feature
- **Secondary types:** refactor, migration, operational, bug_fix
- **Breaking change:** no
- **Durable docs required:** yes
- **External behavior affected:** yes

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Add root-owned system launchers and immutable release selection | add | Spec 009 | `docs/guides/user/installation.md`, `docs/processes/version-management.md` | yes |
| Route protected reads/actions through a versioned local backend | add | Spec 009 | `docs/2-architecture/system-architecture.md` | yes |
| Restrict system runs/logs to current operator-group members | add | Spec 009 | `docs/1-requirements/system-operations.md`, architecture and runbook docs | yes |
| Keep local logs distinct and add explicit system scope | modify | Current CLI behavior | CLI reference and troubleshooting guide | yes |
| Remove tray ownership from notification and CLI services | refactor | Current source | Architecture and tray setup documentation | yes |
| Add backup-success, independent, and explicit retention triggers | add | Spec 009 | Scheduling architecture and operator guide | yes |
| Add durable run records and interrupted-run reconciliation | add | Spec 009 | Architecture and operations docs | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| System privilege, group authorization, record redaction, retention invariants | `docs/1-requirements/system-operations.md` | complete | Added current protected-system requirements |
| Launcher, backend, IPC, run store, tray boundaries | `docs/2-architecture/system-architecture.md` | complete | Replaced the single-process model |
| Backup/retention triggers, shared lock, run recording | `docs/2-architecture/scheduling-system.md` | complete | Preserves user/platform schedule context |
| Focused client/backend services and removed tray coupling | `docs/3-implementation/service-layer-integration.md` | complete | Added a separate system-control boundary |
| Installation, group management, launcher verification | `docs/guides/user/installation.md` | complete | Linux reference and portability limits recorded |
| Production staging, dry-run approval, rollout, rollback | `docs/guides/developer/scheduling-guide.md` | complete | Accepted retention automation replaces manual-only text |
| Independent tray installation and lifecycle | `docs/SYSTEM-TRAY-SETUP.md` | complete | In-process guidance superseded |
| Command names and scopes | `docs/reference/timelocker-cli-command-hierarchy.md` | complete | Added runs, system log scope, tray, and admin boundary |
| User-facing diagnosis and permission errors | `docs/guides/user/backup-operations-troubleshooting.md` | complete | Local/system records and safe diagnosis documented |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| Repository engine ownership | `CHARTER.md` | Restic remains the backup engine |
| Supported repository families | `docs/2-architecture/system-architecture.md` | Local, S3, and B2 support is unchanged |
| Restore overwrite policy | `docs/2-architecture/system-architecture.md` | Spec 009 does not change restore behavior |
| User-scoped backup partitions | GitHub issue #70 | Explicitly outside this spec |
| Full desktop UI | `CHARTER.md` and issue tracker | Tray remains a companion client |

## Bug Fix Details

- **Observed behavior:** `timelocker logs view` shows only user-cache logs and
  CLI construction attempts to initialize the system tray twice.
- **Expected behavior:** local logs are clearly identified; authorized operators
  can query structured system runs/diagnostics; headless commands never
  initialize tray code.
- **Root cause evidence:** `logs_view` resolves
  `ConfigurationPathResolver.get_cache_directory()` directly, while
  `NotificationService` constructs `SystemTrayIntegration` and is instantiated
  by more than one CLI service path.
- **Regression risk:** monitoring initialization, notification delivery, CLI
  compatibility, system installation, and authorization behavior.
- **Durable doc update needed:** yes; see promotion targets.

## Open Questions

None blocking. Live Windows support remains a routed platform follow-up after
shared-contract and test-double acceptance.

## Related Artifacts

- Requirements: `requirements.md`
- Canonical context: `canonical-context.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Traceability: `traceability.md`
- Verification: `verification.md`
