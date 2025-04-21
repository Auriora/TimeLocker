# Requirements Prioritization Matrix

## Introduction

This document presents a prioritization matrix for the TimeLocker project requirements using the MoSCoW method (Must have, Should have, Could have, Won't have). Each requirement has been analyzed based on:

- **Business Value**: The importance to stakeholders and users
- **Implementation Effort**: The estimated effort required to implement
- **Dependencies**: Other requirements or systems that this depends on
- **Risks**: Potential issues that could impact implementation or value

## Functional Requirements

### Repository Management

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| FR-RM-001 | Support multiple repository types (local, SFTP, S3, SMB, etc.) | Must-have | High | Medium | None | Medium - Integration challenges with some backends | Core capability to address diverse storage back-ends. Without this, the product cannot fulfill its primary purpose of flexible backup storage. |
| FR-RM-002 | Allow dynamic registration of repository implementations via plugin architecture | Should-have | Medium | High | FR-RM-001 | High - Plugin architecture adds complexity | Enables community extensions and future storage options. While valuable for extensibility, the core functionality can exist without this initially. |
| FR-RM-003 | Provide UI to add, edit, and remove repositories with credential management | Must-have | High | Medium | FR-RM-001 | Low | Essential for configuration and security. Users need an intuitive way to manage repositories, and secure credential handling is critical for security. |
| FR-RM-004 | Allow users to restrict repository region to EEA/UK and warn if chosen region is outside | Should-have | Medium | Low | FR-RM-001, FR-RM-003 | Low | GDPR Ch. V international transfers compliance. Important for regulatory compliance but can be implemented after core functionality. |
| FR-RM-005 | Validate repository endpoint region at configuration and runtime | Must-have | High | Medium | FR-RM-001, FR-RM-004 | Medium - Requires reliable region detection | Ensures ongoing compliance if bucket is moved or DNS changes. Critical for maintaining GDPR compliance throughout the application lifecycle. |

### Backup Operations

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| FR-BK-001 | Perform full backups of specified data sources | Must-have | High | Medium | FR-RM-001 | Low | Baseline backup capability. This is the core functionality of the application. |
| FR-BK-002 | Support incremental backups to reduce storage and transfer time | Must-have | High | Medium | FR-BK-001 | Medium - Data consistency challenges | Efficiency for ongoing backups. Significantly reduces resource usage and improves user experience for regular backups. |
| FR-BK-003 | Enable scheduled backups (hourly, daily, weekly, custom cron) | Must-have | High | Medium | FR-BK-001 | Low | Automation and reliability. Scheduled backups ensure consistent protection without manual intervention. |
| FR-BK-004 | Validate backup integrity after creation using Restic `check` | Must-have | High | Low | FR-BK-001 | Low | Ensures recoverability. Without validation, backups may be corrupted and unusable when needed. |
| FR-BK-005 | Execute parallel backup operations when system resources permit | Could-have | Medium | High | FR-BK-001 | High - Resource contention, race conditions | Performance optimization. While beneficial for large backups, it adds complexity and the core functionality works without it. |

### Security

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| FR-SEC-001 | Encrypt data in transit (TLS) and at rest (Restic encryption) | Must-have | High | Medium | None | Medium - Key management complexity | Protect sensitive data. Fundamental security requirement for any backup solution handling potentially sensitive data. |
| FR-SEC-002 | Store repository credentials securely in OS key-ring | Must-have | High | Medium | None | Medium - OS integration challenges | Prevent credential leakage. Secure credential storage is essential to prevent unauthorized access to backups. |
| FR-SEC-003 | Implement backup vault locking to prevent concurrent conflicting writes | Should-have | Medium | Medium | FR-BK-001 | Medium - Lock management complexity | Compliance and safety. Important for data integrity but can be implemented after core functionality. |
| FR-SEC-004 | Provide RBAC with predefined roles (Admin, Operator, Viewer) | Should-have | Medium | High | None | High - Authentication integration | Governance and least privilege. Valuable for multi-user environments but adds significant complexity. |
| FR-SEC-005 | Provide user-initiated export of personal metadata in JSON format | Must-have | High | Low | None | Low | GDPR Art. 20 data portability. Legal requirement for GDPR compliance with relatively low implementation effort. |
| FR-SEC-006 | Provide user-initiated erasure of stored personal metadata without deleting backups | Must-have | High | Medium | None | Medium - Ensuring complete metadata removal | GDPR Art. 17 right to erasure. Legal requirement for GDPR compliance. |
| FR-SEC-007 | Default to secure, privacy-by-default configuration and onboarding consent notice | Must-have | High | Low | None | Low | GDPR Art. 25 privacy by design & default. Legal requirement with relatively low implementation effort. |
| FR-SEC-008 | Bundle DPIA checklist and compliance documentation with each release | Could-have | Low | Low | None | Low | GDPR Art. 35 DPIA. Helpful for compliance but not a core functional requirement. |

### Recovery Operations

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| FR-RC-001 | Support point-in-time restore of entire snapshot | Must-have | High | Medium | FR-BK-001 | Medium - Handling large restores | Core recovery capability. Without this, backups have limited value. |
| FR-RC-002 | Enable partial file/folder restore | Must-have | High | Medium | FR-RC-001 | Low | Flexibility for users. Common use case that significantly improves utility. |
| FR-RC-003 | Verify restoration success via checksum comparison | Should-have | Medium | Low | FR-RC-001, FR-RC-002 | Low | Assurance of data integrity. Important but not critical for initial functionality. |
| FR-RC-004 | Provide disaster-recovery workflow for bare-metal scenarios | Could-have | Medium | High | FR-RC-001 | High - OS-specific challenges | Business continuity. Advanced feature that adds value but significantly increases complexity. |

### Policy Management

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| FR-PM-001 | Define retention policies (e.g. keep last n, daily, weekly, monthly) | Must-have | High | Medium | FR-BK-001 | Low | Storage management. Essential for managing backup storage efficiently over time. |
| FR-PM-002 | Configure backup frequency per target | Must-have | High | Low | FR-BK-003 | Low | Meets varying RPOs. Provides necessary flexibility for different data importance levels. |
| FR-PM-003 | Tag backups and apply tag-based policies | Should-have | Medium | Medium | FR-PM-001 | Low | Granular control. Enhances management capabilities but not essential for core functionality. |
| FR-PM-004 | Implement data life-cycle management with pruning and archival | Should-have | Medium | High | FR-PM-001 | Medium - Data transition complexity | Long-term storage optimization. Valuable for cost management but adds complexity. |

### Monitoring & Reporting

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| FR-MON-001 | Log all backup and restore operations with timestamps and status | Must-have | High | Low | None | Low | Auditability. Basic logging is essential for troubleshooting and verification. |
| FR-MON-002 | Provide desktop and email notifications for success/failure | Must-have | High | Medium | FR-MON-001 | Low | User awareness. Critical for ensuring users know when backups fail. |
| FR-MON-003 | Generate exportable audit reports (PDF/CSV) | Should-have | Medium | Medium | FR-MON-001 | Low | Compliance evidence. Valuable for formal environments but not essential for core functionality. |
| FR-MON-004 | Display storage utilization and performance metrics | Should-have | Medium | Medium | FR-MON-001 | Low | Capacity planning. Helpful for management but not critical for basic operation. |
| FR-MON-005 | Detect integrity breaches or audit-log gaps and provide configurable breach-notification workflow | Must-have | High | High | FR-MON-001, FR-MON-006 | Medium - False positive management | GDPR Art. 33 breach notification. Legal requirement with significant implementation complexity. |
| FR-MON-006 | Maintain hash-chained, append-only audit log with tamper detection | Must-have | High | High | FR-MON-001 | Medium - Performance impact | GDPR Arts. 5-2 & 30 accountability. Legal requirement with significant technical complexity. |
| FR-MON-007 | Provide CLI command `audit verify` that exits non-zero on hash-chain break and surfaces result in GUI | Must-have | High | Medium | FR-MON-006 | Low | Detect tampering quickly (GDPR accountability). Important for security verification. |

### Error Handling & Resource Management

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| FR-ERR-001 | Implement retry with exponential back-off for transient failures | Must-have | High | Medium | None | Low | Resilience. Critical for reliable operation in real-world conditions. |
| FR-ERR-002 | Maintain backup consistency in case of interruptions | Must-have | High | High | FR-BK-001 | Medium - Complex recovery scenarios | Data integrity. Essential to prevent corrupted or incomplete backups. |
| FR-RES-001 | Support bandwidth throttling and backup windows | Should-have | Medium | Medium | FR-BK-001 | Low | Resource optimization. Improves user experience but not critical for functionality. |
| FR-RES-002 | Automate pruning and cleanup of outdated backups | Must-have | High | Medium | FR-PM-001 | Low | Storage control. Essential for long-term storage management. |

### Integration

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| FR-INT-001 | Provide CLI commands mirroring GUI operations | Should-have | Medium | Medium | None | Low | Scripting and automation. Valuable for advanced users but not essential for most. |
| FR-INT-002 | Expose REST/JSON-RPC API for remote orchestration | Could-have | Low | High | None | Medium - Security exposure | Integration with external tools. Advanced feature with limited initial user base. |
| FR-INT-003 | Support cross-platform operation (Linux, Windows, macOS) | Must-have | High | High | None | High - Platform-specific issues | User reach. Essential for addressing the target market effectively. |

## Non-Functional Requirements

### Performance

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| NFR-PERF-01 | Application start-up <= 2 s on reference hardware | Must-have | High | Medium | None | Medium - Hardware variability | Fast launch improves user experience. Critical for user satisfaction and perceived quality. |
| NFR-PERF-02 | UI action response <= 200 ms | Must-have | High | Medium | None | Medium - Complex operations | Ensures perception of responsiveness. Essential for usability and user satisfaction. |
| NFR-PERF-03 | Backup throughput >= 80 MB/s on local SSD | Should-have | Medium | Medium | FR-BK-001 | High - Hardware dependencies | Provides efficient backup performance. Important but highly dependent on hardware. |
| NFR-PERF-04 | CPU usage <= 60% average during backup, with dynamic throttling | Should-have | Medium | Medium | FR-BK-001 | Medium - Workload variability | Prevents resource starvation. Important for user experience but not critical. |
| NFR-AUD-01 | Each audit-log append must complete in <= 1 ms on reference hardware | Must-have | High | Medium | FR-MON-006 | Medium - Performance tuning | Maintains low overhead for immutable logging. Critical for system performance. |
| NFR-AUD-02 | Verification of a 10 MB rotated log must finish in <= 2 s | Must-have | High | Medium | FR-MON-006 | Medium - Algorithm optimization | Enables regular tamper checks. Important for security verification performance. |

### Security & Compliance

| ID | Requirement | Priority | Business Value | Implementation Effort | Dependencies | Risks | Rationale |
|----|-------------|----------|---------------|------------------------|--------------|-------|-----------|
| NFR-SEC-01 | Data at rest shall be encrypted with AES-256 | Must-have | High | Low | FR-SEC-001 | Low | Ensures confidentiality. Industry standard security requirement. |
| NFR-SEC-02 | Data in transit shall use TLS 1.3 with modern cipher suites | Must-have | High | Low | FR-SEC-001 | Low | Protects against network eavesdropping. Current security best practice. |
| NFR-SEC-03 | Application shall implement GDPR data-subject rights | Must-have | High | High | FR-SEC-005, FR-SEC-006, FR-SEC-007 | Medium - Comprehensive implementation | Mandatory legal compliance. Required for operation in EU markets. |
| NFR-SEC-04 | Quarterly vulnerability scans shall be performed | Should-have | Medium | Medium | None | Low | Maintains security posture. Important for ongoing security but not a functional requirement. |
| NFR-SEC-12 | Region validation must add <= 50 ms overhead | Should-have | Medium | Medium | FR-RM-004, FR-RM-005 | Medium - Performance tuning | Minimizes performance impact. Balance between security and performance. |

## Prioritization Summary

### Must-Have Requirements (31)
These requirements are essential for the core functionality, legal compliance, and basic user experience. Without these, the product would not be viable.

- **Repository Management**: FR-RM-001, FR-RM-003, FR-RM-005
- **Backup Operations**: FR-BK-001, FR-BK-002, FR-BK-003, FR-BK-004
- **Security**: FR-SEC-001, FR-SEC-002, FR-SEC-005, FR-SEC-006, FR-SEC-007
- **Recovery Operations**: FR-RC-001, FR-RC-002
- **Policy Management**: FR-PM-001, FR-PM-002
- **Monitoring & Reporting**: FR-MON-001, FR-MON-002, FR-MON-005, FR-MON-006, FR-MON-007
- **Error Handling & Resource Management**: FR-ERR-001, FR-ERR-002, FR-RES-002
- **Integration**: FR-INT-003
- **Performance**: NFR-PERF-01, NFR-PERF-02, NFR-AUD-01, NFR-AUD-02
- **Security & Compliance**: NFR-SEC-01, NFR-SEC-02, NFR-SEC-03

### Should-Have Requirements (14)
These requirements provide important functionality and enhance the user experience, but the product can launch without them initially.

- **Repository Management**: FR-RM-002, FR-RM-004
- **Security**: FR-SEC-003, FR-SEC-004
- **Recovery Operations**: FR-RC-003
- **Policy Management**: FR-PM-003, FR-PM-004
- **Monitoring & Reporting**: FR-MON-003, FR-MON-004
- **Error Handling & Resource Management**: FR-RES-001
- **Integration**: FR-INT-001
- **Performance**: NFR-PERF-03, NFR-PERF-04
- **Security & Compliance**: NFR-SEC-04, NFR-SEC-12

### Could-Have Requirements (4)
These requirements would be beneficial but are not essential and can be deferred to later releases.

- **Backup Operations**: FR-BK-005
- **Security**: FR-SEC-008
- **Recovery Operations**: FR-RC-004
- **Integration**: FR-INT-002

### Won't-Have Requirements (0)
No requirements have been identified as unnecessary or out of scope for the foreseeable future.

## Implementation Strategy

Based on this prioritization, we recommend the following implementation strategy:

1. **Phase 1**: Implement all Must-Have requirements to create a Minimum Viable Product (MVP)
2. **Phase 2**: Add Should-Have requirements to enhance functionality and user experience
3. **Phase 3**: Incorporate Could-Have requirements as resources permit

This approach ensures that core functionality and compliance requirements are addressed first, while allowing for incremental improvements in later releases.