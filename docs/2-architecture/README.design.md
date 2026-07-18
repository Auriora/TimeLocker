---
title: "Architecture Document: Design Index"
id: "arch-design-index"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "01-11-2025"
tags: [architecture, index]
links:
    tooling: []
---

# Architecture Document: Design Index

- **Owner**: Architecture Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 13-11-2025
- **Audience**: Engineering, UX, Product Stakeholders

## 1. Context

This index surfaces the primary architecture documents in `docs/2-architecture/`, spanning system design, data modeling, security, and future planning. It
complements the main `README.md` by providing quick navigation for design-centric readers.

## 2. Decision

### 2.1 Core Architecture Set

#### System Overview

- [Design Overview](./overview.md)
- [Technical Architecture](./technical-architecture.md)
- [System Architecture](./system-architecture.md)
- [Component Breakdown](./component-breakdown.md)
- [Data Flow](./data-flow.md)
- [Design Patterns](./design-patterns.md)

#### System Components

- [Scheduling System](./scheduling-system.md) - Automated backup scheduling and platform integration
- [Security System](./security-system.md) - Credential management and access control
- [Integration Layer](./integration-layer.md) - Service communication and dependency injection
- [Performance Monitoring](./performance-monitoring.md) - Metrics, profiling, and benchmarking

#### Cross-Cutting Concerns

- [Security Considerations](./security-considerations.md)
- [Scalability & Performance](./scalability-performance.md)
- [Test Isolation Strategy](./test-isolation-strategy.md)

#### Review

- [File Locations Review](./file-locations-review.md)
- [Path Review Summary](./path-review-summary.md)

## 3. Consequences

- ✅ Readers have a single launch point into architecture materials.
- ✅ Removes stale references to deprecated UX documents.
- ⚠️ Requires updates when new architecture sections are added or renamed.

## 4. Alternatives Considered

1. **Retain previous README with UX links**
    - Pros: Richer navigation.
    - Cons: Linked to non-existent documents; confusing. Updated to match current repository state.

2. **Lean on repository root README only**
    - Pros: One entry point.
    - Cons: Architecture topics become harder to locate. Dedicated index retained.

# References

- Root architecture README: `docs/2-architecture/README.md`
- Implementation docs: `docs/3-implementation/`
