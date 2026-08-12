---
title: Event-driven tray status
doc_type: spec
artifact_type: overview
status: active
owner: Auriora Team
last_reviewed: 2026-08-12
---

# Event-Driven Tray Status

## Purpose

Replace the tray's periodic status polling with an authenticated event-driven
status path, and make the status it presents accurate, quiet, and useful.

This is one package because the backend subscription contract, status snapshot,
tray presentation, authorization, deployment, and recovery behavior form one
end-to-end feature. Splitting them would leave either an unused protocol or a
tray without a reliable source of truth.

## Current Stage

- Requirements, design, tasks, traceability, change impact, canonical context,
  and verification planning produced a deployed Linux acceptance candidate.
- **Architecture decision, 2026-07-28:** approval of the continuously resident
  privileged backend is withdrawn. TimeLocker must have zero idle service
  residency; protected queries and actions must use bounded one-shot execution.
- T011 live acceptance exposed a read-notify-read feedback loop in the resident
  backend. Further acceptance, promotion, and release work for that runtime
  design is halted.
- Accurate status semantics and tray presentation remain reusable, but the
  transport and privileged-process design require disposition through Spec 011.
- T011 is dispositioned to Spec 011; T012 review and T013 promotion/closure are
  the only remaining work in this package.
- There are no active predecessor specs. Spec 009 is closed and its promoted
  durable documents are the current-state baseline.
- The working tree already contains the separately requested removal of the
  inactive `Open TimeLocker` tray item. Implementation must preserve and
  reconcile that change rather than overwrite it.

## Package

- [Requirements](./requirements.md)
- [Technical design](./design.md)
- [Tasks](./tasks.md)
- [Change impact](./change-impact.md)
- [Traceability](./traceability.md)
- [Verification](./verification.md)
- [Canonical context](./canonical-context.md)

## Approval Boundary

No further implementation or live acceptance of the resident backend is
approved. Documentation reconciliation and safe shutdown guidance are approved.
The user explicitly approved Spec 011 implementation on 2026-08-12 after Spec
010 closure. Protected host mutation, live backup or retention execution,
publication, and rollback retain their separate operational approval gates.
