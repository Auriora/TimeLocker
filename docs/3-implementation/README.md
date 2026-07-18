---
title: "Implementation Documentation Index"
doc_type: reference
id: "impl-index"
type: [ implementation ]
status: active
owner: "Auriora Team"
last_reviewed: 2026-07-18
tags: [implementation, index]
links:
    tooling: []
---

# Implementation Documentation Index

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 01-11-2025
- **Audience**: Developers, QA, Release Engineering

## 1. Context

`docs/3-implementation/` houses implementation guides, code walkthroughs, and development resources. This index replaces legacy references to non-existent
documents and highlights the active materials available to contributors.

## 2. Decision

### 2.1 Development Guides

- `command-builder.md` – CLI command construction utility reference.
- [Durable-document template](../templates/durable-document.md) – Starting
  point for current implementation guidance and code-structure references.

### 2.2 Supporting References

- Root README: `../README.md`
- Architecture documentation: `../2-architecture/`
- Testing documentation: `../4-testing/`
- Guides: `../guides/`

## 3. Consequences

- ✅ Provides accurate navigation for implementation-focused contributors.
- ✅ Removes stale links to missing files.
- ⚠️ Requires updates when new implementation guides are added.

## 4. Alternatives Considered

1. **Keep outdated README content**
    - Pros: None.
    - Cons: Links to missing documents; confuses readers. Rejected.

2. **Rely solely on root README**
    - Pros: Single entry point.
    - Cons: Implementation-specific materials become harder to find. Dedicated index retained.

# References

- Templates: [`docs/templates/`](../templates/README.md)
