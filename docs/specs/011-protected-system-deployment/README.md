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
and externally managed temporary artifacts with one supported, repeatable,
transactional workflow for installing, upgrading, inspecting, and rolling back
protected TimeLocker releases.

The package exists because Spec 010 proved the immutable-release architecture
but also demonstrated that its T011 acceptance harness is not a general
administrator deployment interface.

## Current Stage

- Requirements are drafted for review.
- Design and task authoring have not started.
- Implementation is not approved.
- Spec 010 remains the active implementation and acceptance package.
- Spec 011 requirements and design may proceed concurrently because they do not
  change runtime behavior. Implementation must wait until Spec 010 completes
  T013 closure and promotes its accepted deployment behavior.

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
