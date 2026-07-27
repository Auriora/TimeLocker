---
title: Event-driven tray status change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-27
---

# Change Impact

## Purpose

Record the durable behavior changed by event-driven tray status and the
documents that must describe the accepted implementation before closure.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/1-requirements/system-operations.md` | Independent authorized tray and safe system visibility. | high | Modify tray and platform requirements. |
| `docs/2-architecture/system-architecture.md` | Tray polls the protected AF_UNIX backend. | high | Supersede polling with snapshot plus events. |
| `docs/3-implementation/service-layer-integration.md` | `system_control` owns protocol, backend, records, and tray client. | high | Add event ownership without changing layer ownership. |
| `docs/SYSTEM-TRAY-SETUP.md` | Current menu, authorization, Linux setup, and troubleshooting. | high | Update menu and event-channel operation. |
| `docs/reference/timelocker-cli-command-hierarchy.md` | Tray executable and reserved actions. | high | Remove placeholder UI action from visible behavior. |
| `docs/guides/user/backup-operations-troubleshooting.md` | Current stale-status and backend guidance. | high | Add event socket and reconnect diagnostics. |

## Change Type

- **Primary type:** feature
- **Secondary types:** bug_fix, refactor, operational, clarification
- **Breaking change:** no for documented CLI actions; event protocol requires a
  coherent release
- **Durable docs required:** yes
- **External behavior affected:** yes, optional tray and deployment assets

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Replace tray status polling with authenticated event invalidations and snapshots. | modify | system architecture and code | `docs/2-architecture/system-architecture.md` | yes |
| Define continuous subscription authorization and privacy. | add | system operations requirements | `docs/1-requirements/system-operations.md` | yes |
| Make last backup mean last successful completion. | bug_fix | run model and tray code | requirements and tray setup | yes |
| Replace non-functional status/open menu actions with honest status rows. | bug_fix | tray code | `docs/SYSTEM-TRAY-SETUP.md` | yes |
| Silence healthy background tray output. | bug_fix | tray entrypoint | tray setup and troubleshooting | yes |
| Add event socket, probes, and rollback checks. | operational | deployment code/assets | installation, tray setup, version management | yes |
| Preserve Windows-portable contracts without support claim. | clarify | platform adapters | requirements and architecture | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Accepted behavior and security invariants | `docs/1-requirements/system-operations.md` | pending | |
| Snapshot/event architecture and platform boundary | `docs/2-architecture/system-architecture.md` | pending | |
| Component ownership and integration seams | `docs/3-implementation/service-layer-integration.md` | pending | |
| Menu, setup, failure, and restart behavior | `docs/SYSTEM-TRAY-SETUP.md` | pending | |
| Tray executable/action reference | `docs/reference/timelocker-cli-command-hierarchy.md` | pending | |
| Event-channel diagnostics | `docs/guides/user/backup-operations-troubleshooting.md` | pending | |
| Installation and release activation | `docs/guides/user/installation.md`, `docs/processes/version-management.md` | pending | |
| Test profiles or live acceptance guidance | `docs/4-testing/` if reusable guidance changes | pending | Promote only durable procedure. |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| Project mandate | `CHARTER.md` | Optional local tray status remains within the CLI-first mandate. |
| Restic backup/restore semantics | current backup and recovery docs | Event delivery does not change Restic execution or repository format. |
| Retention policy | `docs/1-requirements/system-operations.md` | Trigger and policy semantics remain unchanged. |
| Full desktop UI scope | `CHARTER.md`, `docs/README.md` | Still excluded. |

## Bug Fix Details

- **Observed behavior:** newest backup attempt start time is labeled last backup;
  healthy polling prints every cycle; `View Status` refreshes but opens no view;
  `Open TimeLocker` has no app to open.
- **Expected behavior:** last successful completion is explicit, healthy service
  is quiet, status is visible in menu rows, and placeholder UI actions are
  absent.
- **Root cause evidence:** `tray_client.py` selects the latest run by
  `started_at`; `tray_entry.py` prints every refresh; platform menus define
  actions without a rendered view or registered app callback.
- **Regression risk:** moderate because status, security, IPC, packaging, and
  user-session presentation cross process and platform boundaries.
- **Durable doc update needed:** yes, all promotion targets above.

## Open Questions

None. Scope expansion to a full UI or live Windows deployment requires a
separate approved intake.

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Design: [design.md](./design.md)
- Tasks: [tasks.md](./tasks.md)
- Verification: [verification.md](./verification.md)
