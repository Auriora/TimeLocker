# Requirements Traceability Matrix

## Introduction

This document provides a comprehensive traceability matrix that links each requirement in the Software Requirements Specification (SRS) to its source, related design elements, implementation components, and test cases. The purpose of this matrix is to ensure that all requirements are properly implemented and tested, and to identify any requirements that lack complete traceability.

## Matrix Structure

The traceability matrix is organized by functional and non-functional requirement categories. For each requirement, the following information is provided:

- **Requirement ID**: The unique identifier of the requirement
- **Requirement Description**: A brief description of the requirement
- **Source**: The source of the requirement (e.g., stakeholder, standard, regulation)
- **Design Elements**: Related design elements (e.g., architecture components, design decisions)
- **Implementation Components**: Source code files and classes that implement the requirement
- **Test Cases**: Unit tests, integration tests, and acceptance tests that verify the requirement
- **Status**: The current status of the requirement's traceability (Complete, Partial, Incomplete)

## Functional Requirements

### Repository Management

| Requirement ID | Requirement Description | Source | Design Elements | Implementation Components | Test Cases | Status |
|----------------|-------------------------|--------|----------------|---------------------------|------------|--------|
| FR-RM-001 | Support multiple repository types identified by *repo_type* (local, SFTP, S3, SMB, etc.). | Core capability to address diverse storage back-ends | Not found | src/TimeLocker/backup_repository.py (BackupRepository class)<br>src/TimeLocker/restic/restic_repository.py (ResticRepository class)<br>src/TimeLocker/restic/Repositories/local.py<br>src/TimeLocker/restic/Repositories/s3.py<br>src/TimeLocker/restic/Repositories/b2.py | tests/TimeLocker/restic/test_restic_repository.py<br>docs/SDLC/Testing/Acceptance Tests/RepositoryManagement.t.md (C1, C2) | Complete |
| FR-RM-002 | Allow dynamic registration of repository implementations via plugin architecture. | Enables community extensions and future storage options | Not found | src/TimeLocker/backup_repository.py (BackupRepository abstract class) | Not found | Incomplete |
| FR-RM-003 | Provide UI to add, edit, and remove repositories with credential management. | Essential for configuration and security | Not found | Not found | docs/SDLC/Testing/Acceptance Tests/RepositoryManagement.t.md (C1-C11) | Partial |
| FR-RM-004 | Allow users to restrict repository region to EEA/UK and warn if chosen region is outside. | GDPR Ch. V international transfers | Not found | Not found | docs/SDLC/Testing/Acceptance Tests/RepositoryManagement.t.md (C4, C5) | Partial |
| FR-RM-005 | Validate repository endpoint region at configuration and runtime; abort or warn according to user policy. | Ensures ongoing compliance if bucket is moved or DNS changes | Not found | src/TimeLocker/backup_repository.py (validate method)<br>src/TimeLocker/restic/restic_repository.py (validate method) | docs/SDLC/Testing/Acceptance Tests/RepositoryManagement.t.md (C4, C5) | Partial |

### Backup Operations

| Requirement ID | Requirement Description | Source | Design Elements | Implementation Components | Test Cases | Status |
|----------------|-------------------------|--------|----------------|---------------------------|------------|--------|
| FR-BK-001 | Support full and incremental backups with deduplication. | Core backup functionality | Not found | src/TimeLocker/backup_manager.py<br>src/TimeLocker/backup_repository.py (backup_target method) | docs/SDLC/Testing/Acceptance Tests/BackupOperations.t.md | Partial |
| FR-BK-002 | Allow scheduling of backups with configurable frequency. | User convenience and automation | Not found | Not found | docs/SDLC/Testing/Acceptance Tests/BackupOperations.t.md | Partial |
| FR-BK-003 | Support file/directory inclusion and exclusion patterns. | Flexibility in backup scope | Not found | src/TimeLocker/file_selections.py | Not found | Partial |
| FR-BK-004 | Provide backup verification and integrity checking. | Data reliability | Not found | src/TimeLocker/backup_repository.py (check method) | Not found | Partial |
| FR-BK-005 | Support backup retention policies. | Storage optimization | Not found | src/TimeLocker/backup_repository.py (RetentionPolicy class, apply_retention_policy method) | Not found | Partial |

### Security

| Requirement ID | Requirement Description | Source | Design Elements | Implementation Components | Test Cases | Status |
|----------------|-------------------------|--------|----------------|---------------------------|------------|--------|
| FR-SEC-001 | Encrypt all backup data at rest and in transit. | Data protection | Not found | Not found | docs/SDLC/Testing/Acceptance Tests/SecurityOperations.t.md | Partial |
| FR-SEC-002 | Store credentials securely using OS key-ring. | Credential protection | Not found | src/TimeLocker/restic/restic_repository.py (password method) | docs/SDLC/Testing/Acceptance Tests/RepositoryManagement.t.md (C2, C7) | Partial |
| FR-SEC-003 | Implement role-based access control for multi-user environments. | Access control | Not found | Not found | Not found | Incomplete |
| FR-SEC-004 | Provide audit logging for all security-relevant operations. | Accountability | Not found | Not found | docs/SDLC/Testing/Acceptance Tests/RepositoryManagement.t.md (C1, C2, C5, C6, C7, C9, C10) | Partial |

### Recovery Operations

| Requirement ID | Requirement Description | Source | Design Elements | Implementation Components | Test Cases | Status |
|----------------|-------------------------|--------|----------------|---------------------------|------------|--------|
| FR-RC-001 | Support full and selective restore operations. | Data recovery | Not found | src/TimeLocker/backup_repository.py (restore method) | docs/SDLC/Testing/Acceptance Tests/RecoveryOperations.t.md | Partial |
| FR-RC-002 | Allow point-in-time recovery using snapshot timestamps. | Temporal recovery | Not found | src/TimeLocker/backup_snapshot.py | docs/SDLC/Testing/Acceptance Tests/RecoveryOperations.t.md | Partial |
| FR-RC-003 | Provide restore verification. | Recovery reliability | Not found | Not found | Not found | Incomplete |

## Non-Functional Requirements

### Performance

| Requirement ID | Requirement Description | Source | Design Elements | Implementation Components | Test Cases | Status |
|----------------|-------------------------|--------|----------------|---------------------------|------------|--------|
| NFR-PERF-01 | Application start-up <= 2 s on reference hardware (quad-core CPU, 8 GB RAM). | Fast launch improves user experience | Not found | Not found | Not found | Incomplete |
| NFR-PERF-02 | UI action response <= 200 ms. | Ensures perception of responsiveness | Not found | Not found | Not found | Incomplete |
| NFR-PERF-03 | Backup throughput >= 80 MB/s on local SSD. | Provides efficient backup performance | Not found | Not found | Not found | Incomplete |
| NFR-PERF-04 | CPU usage <= 60 % average during backup, with dynamic throttling. | Prevents resource starvation | Not found | Not found | Not found | Incomplete |

### Security and Compliance

| Requirement ID | Requirement Description | Source | Design Elements | Implementation Components | Test Cases | Status |
|----------------|-------------------------|--------|----------------|---------------------------|------------|--------|
| NFR-SEC-12 | Region validation <= 50 ms overhead. | Performance during security checks | Not found | Not found | Not found | Incomplete |
| NFR-AUD-01 | Each audit-log append must complete in <= 1 ms on reference hardware. | Maintains low overhead for immutable logging | Not found | Not found | Not found | Incomplete |
| NFR-AUD-02 | Verification of a 10 MB rotated log must finish in <= 2 s. | Enables regular tamper checks | Not found | Not found | Not found | Incomplete |

## Traceability Gaps and Recommendations

### Identified Gaps

1. **Design Documentation**: No formal design documents were found in the repository. This creates a gap in traceability between requirements and implementation.

2. **Incomplete Implementation**: Some requirements (e.g., FR-RM-002, FR-SEC-003, FR-RC-003) lack clear implementation components.

3. **Insufficient Test Coverage**: Many requirements, especially non-functional requirements, lack specific test cases to verify their implementation.

4. **UI Implementation**: Requirements related to UI functionality (e.g., FR-RM-003) have acceptance tests but no clear implementation components.

### Recommendations

1. **Create Design Documentation**: Develop and maintain formal design documents that describe how requirements are translated into design elements. This should include:
   - Architecture Design Document
   - Detailed Design Specification
   - UI/UX Design Documentation

2. **Complete Implementation**: Implement missing functionality for requirements that currently lack implementation components:
   - FR-RM-002: Implement plugin architecture for repository types
   - FR-SEC-003: Implement role-based access control
   - FR-RC-003: Implement restore verification

3. **Enhance Test Coverage**: Develop comprehensive test cases for all requirements, especially:
   - Unit tests for all implementation components
   - Performance tests for non-functional requirements
   - Security tests for security-related requirements

4. **Improve Traceability Documentation**: Add traceability information to code and tests:
   - Add requirement IDs in code comments
   - Link test cases to specific requirements in test documentation
   - Create automated traceability reports

5. **Regular Traceability Reviews**: Conduct regular reviews of the traceability matrix to ensure it remains up-to-date as the project evolves.

## Conclusion

The Requirements Traceability Matrix provides a comprehensive view of the current state of requirements implementation and testing in the TimeLocker project. While many functional requirements have at least partial traceability, there are significant gaps in design documentation and test coverage, especially for non-functional requirements.

By addressing the identified gaps and implementing the recommendations, the project can improve its requirements traceability, leading to better quality, more reliable software that fully meets stakeholder needs.