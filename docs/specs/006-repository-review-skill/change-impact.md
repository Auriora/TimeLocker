---
title: Repository review skill change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Durable Source Mapping

- `CHARTER.md`: project mandate, review boundaries, and governance.
- `AGENTS.md`: repository routing for agents and tools.
- `docs/guides/ai-agent/`: operational, planning, documentation, code, and test rules.
- `.github/workflows/`: existing generic PR review automation, unchanged.

## Proposed Changes

| Change | Target | Result |
|--------|--------|--------|
| add | `.agents/skills/review-timelocker/` | Discoverable TimeLocker review skill and focused references. |
| clarify | `AGENTS.md` | Route repository review requests to the local skill. |
| temporary | `docs/specs/006-repository-review-skill/` | Delivery contract and evidence, removed after closure. |
| update | lifecycle indexes and history | Active then closed Spec 006 provenance. |

## Unchanged Areas

- Runtime code, tests, configuration, packaging, CLI, APIs, and data.
- Spec 001 artifacts, task state, acceptance criteria, and sequencing.
- Existing GitHub review workflows and external action configuration.

## Promotion Targets

| Spec content | Durable destination |
|--------------|---------------------|
| Review workflow and safety boundary | `.agents/skills/review-timelocker/SKILL.md` |
| Expert responsibilities | `.agents/skills/review-timelocker/references/expert-panel.md` |
| Finding and report contract | `.agents/skills/review-timelocker/references/review-contract.md` |
| Agent discovery route | `AGENTS.md`; skill metadata |
| Closure provenance | `docs/history/spec-closure-log.md`; `docs/history/spec-archive-index.md` |

## Closure Decision

Remove Spec 006 after promotion and final-state commit. Git and compact history
retain delivery evidence; no accepted behavior may remain only in the package.
