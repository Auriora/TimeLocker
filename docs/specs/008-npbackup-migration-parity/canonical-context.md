---
title: NPBackup migration parity canonical context
doc_type: spec
artifact_type: canonical-context
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Canonical Context

## Purpose

Prevent historical plans, masked sensitive data, or an uncommitted checkout
from being mistaken for authority during the staged NPBackup migration.

## Authority Hierarchy

- `CHARTER.md` owns safety, recovery, credentials, and operator boundaries.
- Spec 007 commit `433c0aa` owns the machine-accepted backup, restore, tray, and
  executable-schedule baseline.
- This package owns migration parity and sequencing only.
- Current source, tests, and generated argv own implemented behavior.
- The live root crontab and NPBackup masked interface own existing-job evidence.

## Always-Canonical External Sources

| Source | Authority reason | Handling |
|--------|------------------|----------|
| `AGENTS.md` and `CHARTER.md` | Repository governance and safety boundary | Stop for a scope decision on conflict. |
| `docs/guides/ai-agent/` | Operational agent rules | Apply by documented priority. |
| source, tests, generated argv, and live masked host evidence | Implemented and operator truth | Reconcile conflicts into the package. |

## Spec-Canonical Working Sources

| Source | Role | Scope | Notes |
|--------|------|-------|-------|
| `requirements.md` | accepted intent | Spec 008 | Phase 2 actions still require named approvals. |
| `design.md` | implementation approach | Spec 008 | Does not authorize host mutation. |
| `tasks.md` | execution index | Spec 008 | Read with traceability and verification. |

## Imported Sources

| Spec path | Source path | Source revision or date | Status | Canonical scope | Promotion target |
|-----------|-------------|-------------------------|--------|-----------------|------------------|
| `canonical-context.md` | Spec 007 verification | `433c0aa` | summarized | machine-acceptance dependency | current user/operator guides |
| `canonical-context.md` | live masked NPBackup evidence | 2026-07-19 | summarized | existing job semantics only | installation and scheduling guides |

## Non-Canonical Background Sources

| Source | Reason non-canonical | Handling |
|--------|----------------------|----------|
| NPBackup ciphertext and unexpanded implementation internals | Not a usable credential or reviewed TimeLocker contract | Never copy, print, or infer plaintext values. |
| deleted or archived historical plans | No current-state authority | Use only for provenance when explicitly needed. |

## Promotion Map

| Spec-local content | Durable destination or route | Required before closure |
|--------------------|------------------------------|-------------------------|
| accepted backup execution options | `docs/guides/user/recovery-operations-guide.md` | yes |
| accepted schedule fields and staging workflow | `docs/guides/developer/scheduling-guide.md` | yes |
| unresolved credential, observation, and cutover work | T005-T008 or explicit follow-up spec | yes |

## Sensitive Context Boundary

The NPBackup repository URI, repository password, and AWS-compatible values are
intentionally absent from this package and session evidence. A byte-identical
copy exists at the root-owned, mode-0600
`/etc/timelocker/npbackup-migration.env`; only its path, metadata, expected
variable names, and successful non-empty load check are recorded. Other safe
metadata includes the six source paths, option/retention shape,
exclusion-source categories, schedule, execution identity, and recent snapshot
identity.

## Sequencing Decision

Spec 008 may be active while Spec 007 awaits release/closure decisions because
it depends on the committed Spec 007 implementation and cannot publish a
release or close Spec 007. Phase 2 host mutations require their own approvals.
