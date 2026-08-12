---
title: Protected system deployment
doc_type: spec
artifact_type: overview
status: draft
owner: Auriora Team
last_reviewed: 2026-07-28
---

# Protected System Deployment

## Purpose

Replace acceptance-specific deployment commands, operator-authored manifests,
externally managed temporary artifacts, and the continuously resident protected
backend with one supported, repeatable, daemonless workflow for installing,
upgrading, inspecting, rolling back, querying, and invoking bounded protected
TimeLocker operations.

The package exists because Spec 010 proved the immutable-release architecture
but also demonstrated that its T011 acceptance harness is not a general
administrator deployment interface.

## Current Stage

- Requirements are being reconciled with the approved zero-idle-residency
  constraint.
- Design and task authoring have not started.
- Implementation is not approved.
- Spec 010 resident-backend acceptance is halted; only independently valid
  status semantics may be retained.
- Spec 011 now owns removal of the resident privileged backend as well as the
  supported deployment transaction.

## Package

- [Requirements](./requirements.md)
- [Canonical context](./canonical-context.md)

Design, tasks, change impact, traceability, and verification artifacts will be
added in their lifecycle stages after the requirements are reviewed.

## Approval Boundary

Creating and refining this package does not authorize implementation,
installation, upgrade, rollback, service mutation, release publication, or
backup and retention execution. Protected host changes remain explicitly
approval-gated.
