---
title: "Testing Documentation"
doc_type: reference
id: "RM-006"
type: [ readme ]
status: active
owner: "Auriora Team"
last_reviewed: 2026-07-18
tags: [ readme, testing ]
links:
    tooling: [ ]
---

# Testing Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 2025-11-07

## 1. Purpose

**When to use this template**: This folder centralizes test strategies, coverage goals, QA playbooks, and release validation checklists.
**Location**: `docs/4-testing/`

## 2. What Belongs Here?

- Test strategy documents and matrices.
- Manual/automated QA procedures.
- Stable test strategy and quality-gate guidance.

## 3. What Does NOT Belong Here?

- Individual test logs (keep near CI artifacts).
- Implementation details (see `../3-implementation/`).
- Operational runbooks (see `../guides/`).

## 4. Available Documents

### Quick Start
- **[quickstart-testing.md](./quickstart-testing.md)** - Fast path for verifying environments and running tests

### MinIO Testing
- **[guide-minio-testing.md](./guide-minio-testing.md)** - Complete MinIO testing guide
- **[checklist-minio-testing.md](./checklist-minio-testing.md)** - MinIO testing checklist
- **[summary-minio-setup.md](./summary-minio-setup.md)** - MinIO setup summary

## 5. Available Templates

- Use the central [test-plan template](../templates/test-plan.md) for durable
  test strategy, environments, gates, and residual risks.

## 6. References

- [Testing Quick Start](./quickstart-testing.md) - Start here for testing
- CI artifacts and Git history preserve point-in-time test results.
