---
title: System CLI, tray, retention, and control canonical context
doc_type: spec
artifact_type: canonical-context
status: draft
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Canonical Context

## Purpose

Prevent current-state documentation from being mistaken for the accepted
future behavior of Spec 009. The scheduling and tray guides remain authoritative
for the installed application until implementation and promotion; this package
is authoritative only for the active implementation slice.

## Authority Hierarchy

System, developer, and user instructions remain highest. `AGENTS.md` routes
project mandate and governance to `CHARTER.md`, agent behavior to
`docs/guides/ai-agent/`, current implementation behavior to source, tests,
configuration, and live evidence, and active change intent to this lifecycle
package.

Spec-local context does not make planned behavior current. A conflict with
mandate, policy, source contracts, tests, generated contracts, or live system
evidence is a reconciliation input and must not be silently overridden.

## Always-Canonical External Sources

| Source | Authority reason | Handling |
|--------|------------------|----------|
| `AGENTS.md` | Repository instruction router | Read before changing governed paths. |
| `CHARTER.md` | Project mandate, boundaries, and governance | Stop for an explicit scope decision if the package conflicts with it. |
| `docs/guides/ai-agent/` | Agent workflow and operational rules | Follow the highest-priority applicable rule. |
| Source, tests, generated contracts, configuration, and live evidence | Current implementation and runtime truth | Reconcile disagreement; do not claim planned behavior is implemented. |

## Spec-Canonical Working Sources

| Source | Role | Scope | Notes |
|--------|------|-------|-------|
| `requirements.md` | Accepted intent | Spec 009 behavior and boundaries | User corrections through 2026-07-26 are included. |
| `design.md` | Proposed implementation approach | Spec 009 architecture and security model | Requires owner approval before source implementation. |
| `tasks.md` | Execution and approval index | Spec 009 delivery sequence | Load linked context before each task. |
| `traceability.md` | Delivery coverage contract | Requirement, design, task, verification, and promotion mappings | Coverage means mapped delivery, not completed implementation. |
| `verification.md` | Evidence contract | Validation, live acceptance, promotion, and closure | Pending results are not proof. |

## Imported Sources

| Source path | Reviewed | Status | Canonical scope | Promotion target |
|-------------|----------|--------|-----------------|------------------|
| `CHARTER.md` | 2026-07-26 | summarized | Mandate and non-goal boundaries only | `CHARTER.md` remains authoritative |
| `docs/guides/developer/scheduling-guide.md` | 2026-07-26 | background | Current installed scheduling and manual-retention behavior | Update after T010 acceptance |
| `docs/SYSTEM-TRAY-SETUP.md` | 2026-07-26 | background | Current in-process tray behavior and setup | Supersede after T007/T010 acceptance |
| `docs/2-architecture/system-architecture.md` | 2026-07-26 | background | Current service and CLI architecture | Update after accepted implementation |
| `docs/2-architecture/scheduling-system.md` | 2026-07-26 | background | Current schedule adapter architecture | Update after retention implementation |

No durable document is copied into this package. The listed current-state
documents remain authoritative for users and operators until T011 promotes
verified behavior.

## Non-Canonical Background Sources

| Source | Reason non-canonical for this slice | Handling |
|--------|-------------------------------------|----------|
| Closed or archived specs | Historical delivery evidence, not current behavior | Consult only for provenance or regression context. |
| Ad hoc installation scripts under `/tmp` | Ephemeral host-operation aids | Never treat as repository contract or commit them. |
| User-local TimeLocker and pyenv installations | Do not define the root-owned system deployment | Use only as observed compatibility evidence. |
| Raw system journal output | Operational evidence that may contain protected metadata | Do not copy into spec artifacts; record secret-free summaries. |

## Promotion Map

| Spec-local content | Durable destination or route | Required before closure |
|--------------------|------------------------------|-------------------------|
| System authorization and record visibility invariants | `docs/1-requirements/system-operations.md` | yes |
| Launcher, backend, transport, run store, and tray architecture | `docs/2-architecture/system-architecture.md` | yes |
| Retention triggers and mutation coordination | `docs/2-architecture/scheduling-system.md` | yes |
| Installed scheduling, retention, tray, and rollback behavior | Current developer and user guides listed in `change-impact.md` | yes |
| Live Windows implementation | Platform roadmap or follow-up package | yes, as an explicit deferral |

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Change impact: `change-impact.md`
- Traceability: `traceability.md`
- Verification: `verification.md`
