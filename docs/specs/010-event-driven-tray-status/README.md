---
title: Event-driven tray status
doc_type: spec
artifact_type: overview
status: active
owner: Auriora Team
last_reviewed: 2026-07-27
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
  and verification planning are approved for implementation.
- **Implementation approval:** user approval recorded on 2026-07-27.
- T001 is the first implementation slice.
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

Implementation is approved within this package. Protected host deployment,
operator-group mutation, live backup or retention execution, release
publication, and rollback retain their normal explicit approval gates.
