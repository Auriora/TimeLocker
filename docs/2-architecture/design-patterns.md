---
title: "Architecture Document: Design Patterns"
id: "arch-design-patterns"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "01-11-2025"
tags: [architecture, patterns]
links:
    tooling: []
---

# Architecture Document: Design Patterns

- **Owner**: Architecture Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: Engineering Teams, Code Reviewers

## 1. Context

TimeLocker applies established design patterns to keep the codebase modular, testable, and aligned with functional requirements. This document identifies the
primary patterns in use and ties them to the subsystems they support.

## 2. Decision

### 2.1 Creational Patterns

- **Factory Method**
    - *Usage*: Create repository instances based on repository type.
    - *Benefits*: Encapsulates repository creation logic; centralises backend selection.
    - *Requirements*: FR-RM-001, FR-RM-002.

- **Builder**
    - *Usage*: Construct complex backup configurations (targets, policies, patterns).
    - *Benefits*: Separates construction from representation; supports fluent APIs.
    - *Requirements*: FR-BK-001, FR-BK-002, FR-BK-003.

### 2.2 Structural Patterns

- **Adapter**
    - *Usage*: Map Restic CLI commands to TimeLocker abstractions.
    - *Benefits*: Enables integration without leaking Restic-specific details.
    - *Requirements*: FR-BK-001, FR-BK-002, FR-BK-004.

- **Facade**
    - *Usage*: Provide unified entry points for backup, restore, and repository routines.
    - *Benefits*: Simplifies orchestration for UI/CLI/API consumers.
    - *Requirements*: FR-BK-001, FR-BK-002, FR-BK-003, FR-BK-004.

- **Proxy**
    - *Usage*: Gate repository access through credential and policy checks.
    - *Benefits*: Adds security and validation layers before invoking infrastructure operations.
    - *Requirements*: FR-SEC-003, FR-SEC-004.

### 2.3 Behavioral Patterns

- **Observer**
    - *Usage*: Emit notifications and monitoring events for backup state changes.
    - *Benefits*: Decouples event generation from alerting channels.
    - *Requirements*: FR-MON-002.

- **Strategy**
    - *Usage*: Swap backup strategies (full, incremental, differential) at runtime.
    - *Benefits*: Enables experimentation without modifying callers.
    - *Requirements*: FR-BK-001, FR-BK-002.

- **Command**
    - *Usage*: Encapsulate backup and restore operations as discrete tasks.
    - *Benefits*: Supports queuing, retries, logging, and potential undo semantics.
    - *Requirements*: FR-BK-001, FR-BK-002, FR-BK-003.

## 3. Consequences

- ✅ Shared vocabulary accelerates code reviews and onboarding.
- ✅ Patterns reinforce separation of concerns across services and UI layers.
- ⚠️ Over-application of patterns can increase abstraction overhead; keep usage intentional.
- ⚠️ Documentation must be refreshed when refactors introduce new paradigms (e.g., CQRS, event sourcing).

## 4. Alternatives Considered

1. **Ad-hoc implementations without explicit pattern alignment**
    - Pros: Potentially faster for small features.
    - Cons: Harder to reason about and maintain at scale. Rejected for long-term maintainability.

2. **Exclusive reliance on microservice patterns (e.g., saga, event sourcing)**
    - Pros: Strong for distributed systems.

- Cons: Overkill for current deployment footprint; may be revisited when multi-service orchestration is needed.

# References

- [Component Breakdown](component-breakdown.md)
- [Scalability & Performance](scalability-performance.md)
