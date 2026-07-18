---
title: Adopt Spec Lifecycle Manager change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Purpose

Record the governance and documentation changes required to make active specs
the delivery contract without displacing durable docs, GitHub issues, or update
logs.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `AGENTS.md` | Routes agents to centralized rules. | high | Add lifecycle discovery only. |
| `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md` | Requires plan approval for complex work. | high | Retain approval gate. |
| `docs/plans/README.md` | Indexes active and historical standalone plans. | high | Active role is superseded. |

## Change Type

- **Primary type:** migration
- **Breaking change:** no
- **Durable docs required:** yes
- **External behavior affected:** no

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Route complex delivery work through active spec packages | modify | `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md` | same | yes |
| Recognize specs and lifecycle history | modify | `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | same | yes |
| Replace the live standalone CLI plan | supersede | `docs/plans/2026-04-23-173102-cli-consolidation-stabilization-plan.md` | `docs/specs/001-cli-consolidation-stabilization/` | yes |
| Record future spec closure | add | none | `docs/history/` | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Lifecycle and authority boundaries | `docs/specs/README.md` | complete | Active-spec entry point |
| Agent planning behavior | `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md` | complete | Approval gate retained |
| Documentation routing | `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | complete | Specs/history added |
| Closure policy | `docs/history/spec-closure-log.md`, `docs/history/spec-archive-index.md` | complete | Final commit remains a closure-time concern |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| product requirements | `docs/1-requirements/` | No product behavior changes. |
| architecture | `docs/2-architecture/` | No runtime boundary changes. |
| testing | `docs/4-testing/` | No test strategy changes. |

## Bug Fix Details

Not applicable; this is a documentation and governance migration.

## Open Questions

- None.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
