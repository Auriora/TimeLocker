---
title: CLI consolidation stabilization change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Purpose

Track the internal CLI seam changes and durable documentation promotion needed
for the remaining consolidation work.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/reference/timelocker-cli-command-hierarchy.md` | Public CLI hierarchy and command names. | high | Must remain unchanged. |
| `docs/3-implementation/service-layer-integration.md` | Service and compatibility boundaries. | medium | Refresh after accepted slices. |
| `docs/reference/repo-orientation-and-change-map.md` | File ownership and contributor navigation. | high | Refresh when responsibilities move. |

## Change Type

- **Primary type:** refactor
- **Breaking change:** no
- **Durable docs required:** yes
- **External behavior affected:** no

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Standardize command repository resolution | modify | repository resolver code and tests | `docs/3-implementation/service-layer-integration.md` | yes |
| Narrow CLI service-manager responsibility | modify | service/facade code and tests | `docs/3-implementation/service-layer-integration.md` | yes |
| Select one monitoring command-facing path | modify | monitoring code and tests | implementation and orientation docs | yes |
| Preserve command hierarchy | clarify | CLI tests | `docs/reference/timelocker-cli-command-hierarchy.md` | only if clarification is needed |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Final service boundaries | `docs/3-implementation/service-layer-integration.md` | pending | Promote with T009 |
| Final code ownership/navigation | `docs/reference/repo-orientation-and-change-map.md` | pending | Promote with T009 |
| User-visible CLI changes | `docs/reference/timelocker-cli-command-hierarchy.md` | not expected | Update only if validation discovers contract drift |
| Per-slice implementation evidence | Git commits, pull requests, and CI artifacts | pending | Record evidence for each landed slice in this package |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| product requirements | `docs/1-requirements/` | Refactor preserves product behavior. |
| architecture | `docs/2-architecture/` | No system-level component boundary changes are planned. |
| release process | `docs/processes/version-management.md` | No release mechanics change. |

## Bug Fix Details

Not applicable unless a focused slice discovers a behavior defect. Route any
new defect through reconciliation and update this artifact before expanding scope.

## Open Questions

- Whether external consumers call `CLIServiceManager` methods directly.
- Which monitoring integration should remain the command-facing owner.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
