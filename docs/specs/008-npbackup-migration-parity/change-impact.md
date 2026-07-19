---
title: NPBackup migration parity change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Change Impact

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/guides/user/recovery-operations-guide.md` | Current backup execution workflow | high | Needs explicit compression and traversal options. |
| `docs/guides/developer/scheduling-guide.md` | Current schedule and renderer workflow | high | Needs persisted fields and staging boundary. |

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Backup compression | add | backup CLI/request/target and Restic adapter | user backup guidance | yes |
| Filesystem traversal | add | backup CLI/request/target and Restic adapter | user backup guidance | yes |
| Schedule parity | modify | schedule commands and renderers | scheduling guide | yes |
| Host installation | migration | approved Phase 2 only | installation and scheduling guides | yes, after acceptance |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Backup execution parity | `docs/guides/user/recovery-operations-guide.md` | complete | Promoted after focused tests passed. |
| Stored schedule parity and safe staging | `docs/guides/developer/scheduling-guide.md` | complete | Credential and cutover gates remain explicit. |

## Unchanged Boundaries

- No repository or credential format changes.
- No automatic service installation or crontab mutation.
- No retention enforcement or prune behavior in Phase 1.
- Spec 007 retains release approval and lifecycle closure authority.
