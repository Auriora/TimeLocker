---
title: "Architecture Document: System Architecture"
id: "arch-system-architecture"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "01-11-2025"
tags: [architecture, system, layers]
links:
    tooling: []
---

# Architecture Document: System Architecture

- **Owner**: Architecture Team
- **Status**: Approved
- **Created Date**: 19-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: Engineering Teams, Solution Architects

## 1. Context

To provide a resilient and extensible backup platform, TimeLocker separates concerns across presentation, orchestration, infrastructure, and storage. This
layered approach enables independent evolution of interfaces, services, and backend integrations.

## 2. Decision

TimeLocker adopts a four-layer architecture shown below.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │  Desktop GUI    │  │     CLI        │  │    REST API      │  │
│  └─────────────────┘  └────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Core Services Layer                       │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ Repository      │  │ Backup         │  │ Recovery         │  │
│  │ Management      │  │ Operations     │  │ Operations       │  │
│  └─────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ Policy          │  │ Monitoring &   │  │ Security         │  │
│  │ Management      │  │ Reporting      │  │ Services         │  │
│  └─────────────────┘  └────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                         │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ Restic Engine   │  │ Plugin System  │  │ Error Handling   │  │
│  └─────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ Resource        │  │ Audit Logging  │  │ Cross-Platform   │  │
│  │ Management      │  │                │  │ Support          │  │
│  └─────────────────┘  └────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Storage Backends                          │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │   Local Files   │  │  Cloud Storage │  │ Network Storage  │  │
│  │                 │  │  (S3, B2)      │  │ (SFTP, SMB, NFS) │  │
│  └─────────────────┘  └────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Layer responsibilities**

- **User Interfaces** (Desktop GUI, CLI, REST API): Entry points for human or programmatic operators. They translate intent into service calls and surface
  monitoring insights.
- **Core Services**: Encapsulate business logic for repositories, backups, recovery, policy enforcement, monitoring/reporting, and security orchestration.
- **Infrastructure Layer**: Provides the execution substrate—Restic integration, plugin architecture, error handling, resource management, audit logging, and
  cross-platform abstractions.
- **Storage Backends**: Support local, cloud (S3, B2), and network protocols (SFTP, SMB, NFS) as pluggable persistence targets.

## 3. Consequences

- ✅ Layered separation simplifies testing and isolates responsibilities.
- ✅ Extensible plugin system allows onboarding new backends without changing core flows.
- ⚠️ Requires well-defined contracts between layers; improper boundaries can introduce coupling.
- ⚠️ Cross-layer observability must be maintained to avoid gaps in monitoring.

## 4. Alternatives Considered

1. **Monolithic service mixing UI and orchestration**
    - Pros: Fewer moving parts.
    - Cons: Limits scalability and maintainability; discarded in favor of layered design.

2. **Microservices per responsibility**
    - Pros: Independent scaling.
    - Cons: Higher operational overhead for current scope; deferred until scale requires it.

# References

- [Component Breakdown](./component-breakdown.md)
- [Data Flow](./data-flow.md)
- [Scalability & Performance](./scalability-performance.md)