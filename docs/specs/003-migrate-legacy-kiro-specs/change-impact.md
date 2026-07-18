---
title: Migrate legacy Kiro specifications change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Purpose

Replace a second, hidden specification authority with the repository's current
numbered lifecycle while keeping completed and deferred delivery state out of
the visible active documentation tree.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/specs/README.md` | Active lifecycle package contract. | high | |
| `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | Current-state docs and Git-backed history policy. | high | |
| `docs/history/spec-archive-index.md` | Compact recovery and disposition index. | high | |

## Change Type

- **Primary type:** migration
- **Breaking change:** documentation paths only
- **Durable docs required:** yes
- **External behavior affected:** no

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Legacy active requirements/design/tasks | remove | `.kiro/specs/` | current durable docs, verified active packages, or Git history | yes |
| Deferred REST/import proposals | remove | `.kiro/specs/_archived/` | Git history; reactivate only through future intake | no |
| CLI refactoring source | supersede | `.kiro/specs/cli-refactoring/` | `docs/specs/001-cli-consolidation-stabilization/` | yes |
| Migration dispositions | add | Spec 003 verification | `docs/history/` compact closure record | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Implemented feature behavior missing from current docs | owning durable requirements/architecture/implementation/reference docs | pending | Only where reconciliation finds a real gap. |
| Verified unfinished work | new numbered active spec | pending | Only if current evidence supports it. |
| Completed/stale/deferred source disposition | Git plus `docs/history/` | pending | One compact batch record preferred. |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| runtime behavior | `src/`, `tests/` | Migration is docs-only. |
| active CLI scope | `docs/specs/001-cli-consolidation-stabilization/` | Already migrated and remains authoritative. |

## Open Questions

None.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
