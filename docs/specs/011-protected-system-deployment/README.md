---
title: Protected system deployment
doc_type: spec
artifact_type: overview
status: active
owner: Auriora Team
last_reviewed: 2026-08-12
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

- Requirements and design are approved.
- Daemonless runtime and supported deployment implementation are complete.
- Automated validation, MoE review, promotion, and lifecycle closure are in
  progress.
- Protected host mutation and the 90-second live idle observation remain a
  separate operational approval boundary.

## Package

- [Requirements](./requirements.md)
- [Canonical context](./canonical-context.md)
- [Design](./design.md)
- [Tasks](./tasks.md)
- [Traceability](./traceability.md)
- [Verification](./verification.md)

## Approval Boundary

Creating and refining this package does not authorize implementation,
installation, upgrade, rollback, service mutation, release publication, or
backup and retention execution. Protected host changes remain explicitly
approval-gated.
