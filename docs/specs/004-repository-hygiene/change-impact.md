---
title: Repository hygiene change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Purpose

Map the cleanup from stale or duplicated documentation into its durable current
destinations.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/guides/ai-agent/` | Central agent policy | high | Normalize copied content in place. |
| `README.md` | Project front door | high | Repair from current tracked tree and config. |
| `docs/DOCUMENTATION-STATUS.md` | Legacy removal and durable-doc policy | high | Retain and verify. |
| `docs/specs/README.md` | Lifecycle operating contract | high | Add temporary sequencing, then restore single-package state. |

## Change Type

- **Primary type:** documentation
- **Breaking change:** no
- **Durable docs required:** yes
- **External behavior affected:** no

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Agent authority cleanup | clarify/remove | `AGENTS.md`, `.kiro/steering/`, agent guides | `AGENTS.md`, `docs/guides/ai-agent/` | yes |
| Front-door repair | modify | `README.md`, `CHANGELOG.md`, current tree/config | same files | yes |
| Documentation resource normalization | rename | `docs/.resources/` | `docs/resources/` | yes |
| Durable template consolidation | clarify/remove | scattered `_template` files | `docs/templates/` | yes |
| Pickle investigation cleanup | remove | investigation plus current code/tests | code/tests; no troubleshooting plan | yes |
| Lifecycle sequencing | clarify | Specs 001 and 004 | Spec 001 plus lifecycle history | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Agent authority and TimeLocker-specific rules | `AGENTS.md`, `docs/guides/ai-agent/` | pending | Must be current before closure. |
| Front-door and resource conventions | `README.md`, `CHANGELOG.md`, `docs/resources/` | pending | Paths must resolve. |
| Template policy | `docs/templates/README.md` | pending | No spec template copy. |
| Spec sequencing outcome | Spec 001 and `docs/history/spec-closure-log.md` | pending | Spec 004 is temporary. |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| Runtime architecture | `docs/2-architecture/`, `src/TimeLocker/` | Documentation governance only. |
| CLI implementation scope | Spec 001 | Explicitly deferred until Spec 004 closes. |
| Product branding | `resources/` | Separate from documentation assets. |
| Lifecycle templates | installed lifecycle skill fallback | Repository copy would create new duplication. |

## Open Questions

- None; path, removal, template, and sequencing decisions are approved.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
