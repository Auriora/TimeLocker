---
title: Event-driven tray status canonical context
doc_type: spec
artifact_type: canonical-context
status: active
owner: Auriora Team
last_reviewed: 2026-07-27
---

# Canonical Context

## Purpose

This package changes behavior promoted by closed Spec 009 and spans several
durable documents. This map prevents removed specification history or proposed
event behavior from being mistaken for current implementation truth.

## Authority Hierarchy

The package is canonical only for the approved implementation slice while
active. It does not override user/platform instructions, `AGENTS.md`,
`CHARTER.md`, security policy, source contracts, tests, generated artifacts,
or live system evidence.

## Always-Canonical External Sources

| Source | Authority reason | Handling |
|--------|------------------|----------|
| `AGENTS.md` and `docs/guides/ai-agent/` | Repository behavior and workflow instructions | Read before implementation and validation. |
| `CHARTER.md` | Mandate, boundaries, governance, and approval rights | Stop if scope expands to a full GUI, remote service, or changed security boundary. |
| Current source, tests, package metadata, and live evidence | Implementation and runtime truth | Reconcile conflicts; do not overwrite based on draft prose. |
| `pyproject.toml` and `docs/4-testing/README.md` | Test discovery and final coverage profile | Use focused tests first and the configured profile before closure. |

## Spec-Canonical Working Sources

| Source | Role | Scope | Notes |
|--------|------|-------|-------|
| `requirements.md` | Intended observable behavior | Spec 010 | Requires approval before implementation. |
| `design.md` | Snapshot/event architecture | Spec 010 | Reconcile if implementation changes transport or security decisions. |
| `tasks.md` | Dependency-aware execution index | Spec 010 | Never implement from tasks alone. |
| `traceability.md` | Requirement/task/verification routing | Spec 010 | Gaps block readiness. |
| `verification.md` | Required evidence and approval gates | Spec 010 | Live host actions require explicit approval. |

## Imported Sources

| Spec path | Source path | Source revision or date | Status | Canonical scope | Promotion target |
|-----------|-------------|-------------------------|--------|-----------------|------------------|
| requirements/design/change impact | `docs/1-requirements/system-operations.md` | reviewed 2026-07-26 | summarized | Current authorization, tray, and portability baseline | same path |
| requirements/design/change impact | `docs/2-architecture/system-architecture.md` | reviewed 2026-07-26 | supersedes | Polling tray boundary for this slice only | same path |
| design/tasks | `docs/3-implementation/service-layer-integration.md` | reviewed 2026-07-18 | adapted | Existing `system_control` ownership | same path |
| requirements/change impact | `docs/SYSTEM-TRAY-SETUP.md` | current checkout | supersedes | Current menu and polling-related operation for this slice | same path |

## Non-Canonical Background Sources

| Source | Reason non-canonical | Handling |
|--------|----------------------|----------|
| Removed `docs/specs/009-system-cli-tray-retention/` recovered from Git | Closed delivery scaffolding | Use only for historical rationale; durable promoted docs own current state. |
| `docs/history/spec-closure-log.md` and archive index | Lifecycle history | Use for identity and provenance, not product behavior. |
| Generic integration event-bus documentation | Different in-process integration boundary | Do not reuse as the protected system event contract without explicit reconciliation. |

## Promotion Map

| Spec-local content | Durable destination or route | Required before closure |
|--------------------|------------------------------|-------------------------|
| Event-driven tray behavior and authorization | `docs/1-requirements/system-operations.md` | yes |
| Snapshot/event architecture and platform split | `docs/2-architecture/system-architecture.md` | yes |
| Component ownership and interfaces | `docs/3-implementation/service-layer-integration.md` | yes |
| Setup, status rows, failure, reconnect, and rollback | `docs/SYSTEM-TRAY-SETUP.md` and user/developer guides | yes |
| Concrete Windows live service and acceptance | follow-up spec or issue | yes, as routed work |
| Full desktop application | product backlog/roadmap | no implementation; retain exclusion |

## Worktree Caution

The working tree contains a user-requested, tested removal of the inactive
`Open TimeLocker` menu item that predates this package. It is implementation
evidence to reconcile under T006, not permission to revert or silently broaden
the current commit.

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Design: [design.md](./design.md)
- Tasks: [tasks.md](./tasks.md)
- Change impact: [change-impact.md](./change-impact.md)
- Verification: [verification.md](./verification.md)
