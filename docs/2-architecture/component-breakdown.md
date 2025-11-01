---
title: "Architecture Document: Component Breakdown"
id: "arch-component-breakdown"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "01-11-2025"
tags: [architecture, components, requirements]
links:
    tooling: []
---

# Architecture Document: Component Breakdown

- **Owner**: Architecture Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: Engineering Teams, QA, Product Management

## 1. Context

This document maps TimeLocker subsystems to their purposes, responsibilities, and linked requirements. It supports planning, ownership assignment, and
compliance tracking across user interfaces, core services, infrastructure utilities, and storage backends.

## 2. Decision

### 2.1 User Interfaces

#### Desktop GUI

- **Purpose**: Rich, user-friendly orchestration client.
- **Responsibilities**:
    - Repository configuration and management.
    - Backup and restore execution.
    - Policy configuration.
    - Monitoring, reporting, and notifications.
- **Requirements**: FR-RM-003, FR-MON-002, FR-MON-004.

#### CLI

- **Purpose**: Scriptable automation surface.
- **Responsibilities**:
    - Mirrors GUI operations.
    - Enables batch workflows and scheduler integration.
- **Requirements**: FR-INT-001, FR-MON-007.

#### REST API

- **Purpose**: Integration interface for external tooling.
- **Responsibilities**:
    - Remote orchestration.
    - Status monitoring.
    - Configuration management endpoints.
- **Requirements**: FR-INT-002.

### 2.2 Core Services Layer

#### Repository Management

- **Purpose**: Manage repositories across storage backends.
- **Responsibilities**: Creation, configuration, validation, credential management, plugin registration, GDPR compliance.
- **Requirements**: FR-RM-001 … FR-RM-005.

#### Backup Operations

- **Purpose**: Execute full and incremental backups.
- **Responsibilities**: Scheduling, integrity validation, parallel execution, policy alignment.
- **Requirements**: FR-BK-001 … FR-BK-005.

#### Recovery Operations

- **Purpose**: Restore data from snapshots.
- **Responsibilities**: Full/partial restoration, verification, disaster recovery workflows.
- **Requirements**: FR-RC-001 … FR-RC-004.

#### Policy Management

- **Purpose**: Configure retention and backup cadence.
- **Responsibilities**: Retention policies, frequency, tag-based rules, lifecycle management.
- **Requirements**: FR-PM-001 … FR-PM-004.

#### Monitoring & Reporting

- **Purpose**: Operational visibility and audits.
- **Responsibilities**: Logging, notifications, audit reports, storage utilisation monitoring, integrity breach detection.
- **Requirements**: FR-MON-001 … FR-MON-007.

#### Security Services

- **Purpose**: Safeguard data and credentials.
- **Responsibilities**: Encryption, credential storage, vault locking, RBAC, GDPR compliance features.
- **Requirements**: FR-SEC-001 … FR-SEC-008.

### 2.3 Infrastructure Layer

#### Restic Engine

- **Purpose**: Core backup engine integration.
- **Responsibilities**: Execute backup/restore, snapshot management, encryption operations.
- **Requirements**: FR-BK-001, FR-BK-002, FR-BK-004, FR-RC-001, FR-RC-002.

#### Plugin System

- **Purpose**: Extensibility for backends.
- **Responsibilities**: Dynamic repository implementation registration and lifecycle management.
- **Requirements**: FR-RM-002.

#### Error Handling

- **Purpose**: Resilience and consistency.
- **Responsibilities**: Retry strategies, consistency maintenance, error reporting.
- **Requirements**: FR-ERR-001, FR-ERR-002.

#### Resource Management

- **Purpose**: Operational efficiency.
- **Responsibilities**: Bandwidth throttling, backup windows, pruning and cleanup automation.
- **Requirements**: FR-RES-001, FR-RES-002.

#### Audit Logging

- **Purpose**: Tamper-proof activity trail.
- **Responsibilities**: Hash-chained logs, tamper detection, verification workflows.
- **Requirements**: FR-MON-006, FR-MON-007.

#### Cross-Platform Support

- **Purpose**: Consistent multi-OS behaviour.
- **Responsibilities**: Platform abstraction layers and environment parity.
- **Requirements**: FR-INT-003.

### 2.4 Storage Backends

#### Local Files

- **Purpose**: Local filesystem storage.
- **Responsibilities**: Path management, local IO.
- **Requirements**: FR-RM-001.

#### Cloud Storage

- **Purpose**: S3/B2 and similar endpoints.
- **Responsibilities**: Protocol support, region validation, authentication.
- **Requirements**: FR-RM-001, FR-RM-004, FR-RM-005.

#### Network Storage

- **Purpose**: Network protocols (SFTP, SMB, NFS).
- **Responsibilities**: Network authentication and secure connectivity.
- **Requirements**: FR-RM-001.

## 3. Consequences

- ✅ Explicit requirement mapping aids traceability and testing focus.
- ✅ Responsibility delineation supports team assignment and modular development.
- ⚠️ Requirement identifiers must stay in sync with the SRS; stale mappings reduce audit value.
- ⚠️ Over-segmentation may introduce coordination overhead if teams are small.

## 4. Alternatives Considered

1. **Ad-hoc documentation embedded in code**
    - Pros: Close to implementation.
    - Cons: Hard for stakeholders to consume; lacks requirement traceability. Rejected.

2. **High-level summary without requirement links**
    - Pros: Faster to maintain.
    - Cons: Insufficient for compliance and planning. Rejected in favor of explicit mappings.

# References

- Requirements catalogue: `docs/1-requirements/`
- Monitoring strategy: `docs/4-testing/`
