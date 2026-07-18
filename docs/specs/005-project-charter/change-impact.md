---
title: Project charter change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Durable Source Mapping

- `README.md`: current project and user orientation.
- `docs/README.md`: current documentation and authority model.
- `AGENTS.md`: minimal agent router.
- Spec 001 requirements: active CLI delivery contract.

## Proposed Changes

| Change | Target | Result |
|--------|--------|--------|
| add | `CHARTER.md` | Durable mandate, boundaries, governance, and success authority. |
| clarify | `README.md` | Route project direction to the charter. |
| clarify | `docs/README.md` | Put charter in the starting path and authority model. |
| clarify | `AGENTS.md` | Route agents to the charter without duplicating it. |
| clarify | Spec 001 requirements | Record charter as enduring baseline above the delivery slice. |

## Unchanged Areas

- Runtime code, tests, configuration, packaging, APIs, and CLI behavior.
- Spec 001 requirements, acceptance criteria, tasks, design, and sequencing,
  except for a non-normative durable-baseline link.
- GitHub issue ownership and state.

## Promotion Targets

| Spec content | Durable destination |
|--------------|---------------------|
| Mandate, audience, principles, scope, exclusions | `CHARTER.md` |
| Governance, decision rights, success measures | `CHARTER.md` |
| Reader and authority paths | `README.md`, `docs/README.md`, `AGENTS.md` |
| Delivery relationship | Spec 001 requirements |
| Closure provenance | `docs/history/spec-closure-log.md`, `docs/history/spec-archive-index.md` |

## Closure Decision

Remove Spec 005 after promotion. Git and the lifecycle history retain delivery
evidence; no lasting requirement or decision may remain only in this package.
