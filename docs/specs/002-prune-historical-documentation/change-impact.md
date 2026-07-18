---
title: Prune historical documentation change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Purpose

Replace visible historical-document retention with a Git-backed archive and a
small current-state documentation surface.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/README.md` | Current navigation | high | Rewrite. |
| `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | Visible history retention and update-log requirements | high | Supersede those rules. |
| `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md` | Permanent update-entry requirement | high | Replace with spec/commit evidence. |
| `docs/specs/README.md` | Temporary spec lifecycle | high | Retain and clarify removal-first closure. |
| `docs/history/` | Compact closure evidence | high | Retain. |

## Change Type

- **Primary type:** documentation
- **Breaking change:** yes — historical documentation URLs are intentionally removed
- **Durable docs required:** yes
- **External behavior affected:** no

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Historical updates/plans/reports/archive/issues/task snapshots | remove | Git history | Git commits plus compact lifecycle rows where applicable | yes |
| Legacy Kiro requirements/design references | remove | `.kiro/specs/` | current code, durable docs, active Spec 001, or no replacement | yes |
| Future REST API/database/roadmap designs | remove | future-only architecture files | GitHub backlog or future active spec when approved | no |
| Documentation lifecycle policy | modify | agent rules and spec README | same durable files | yes |
| Current navigation/status | clarify | docs hub/status | same durable files | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Git-backed history rule | `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | pending | |
| Spec evidence/closure rule | `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md`, `docs/specs/README.md` | pending | |
| Lean current-state navigation | `docs/README.md`, `docs/DOCUMENTATION-STATUS.md` | pending | |
| Closure breadcrumbs | `docs/history/` | pending | |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| runtime behavior | `src/`, `tests/` | Documentation cleanup only. |
| active CLI delivery | `docs/specs/001-cli-consolidation-stabilization/` | Remains active and authoritative. |
| user operation contracts | retained guides/reference | Current content is consolidated, not behaviorally changed. |

## Open Questions

- None; deletion scope and Git-backed history preference were explicitly approved.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
