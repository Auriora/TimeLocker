# Use Case Catalog

This document provides a complete catalog of all use cases for the TimeLocker system, organized by functional area.

## Repository Management

### [UC-RM-001: Create Repository](UC-RM-001.md)

**Actor**: User  
**Goal**: Create a new backup repository  
**Priority**: Must Have

### [UC-RM-002: Configure Repository](UC-RM-002.md)

**Actor**: User  
**Goal**: Configure repository settings and parameters  
**Priority**: Must Have

## Backup Operations

### [UC-BK-001: Create Backup](UC-BK-001.md)

**Actor**: User  
**Goal**: Create a backup of selected files and directories  
**Priority**: Must Have

### [UC-BK-002: Schedule Backup](UC-BK-002.md)

**Actor**: User  
**Goal**: Schedule automatic backups  
**Priority**: Should Have

## Recovery Operations

### [UC-RC-001: Browse Snapshots](UC-RC-001.md)

**Actor**: User  
**Goal**: Browse available backup snapshots  
**Priority**: Must Have

### [UC-RC-002: Restore Files](UC-RC-002.md)

**Actor**: User  
**Goal**: Restore files from a backup snapshot  
**Priority**: Must Have

## Security

### [UC-SEC-001: Encrypt Repository](UC-SEC-001.md)

**Actor**: User  
**Goal**: Enable encryption for backup repository  
**Priority**: Must Have

### [UC-SEC-002: Manage Access Control](UC-SEC-002.md)

**Actor**: Administrator  
**Goal**: Manage user access and permissions  
**Priority**: Should Have

## Policy Management

### [UC-PM-001: Define Retention Policy](UC-PM-001.md)

**Actor**: User  
**Goal**: Define backup retention policies  
**Priority**: Should Have

## Monitoring & Reporting

### [UC-MON-001: View Backup Status](UC-MON-001.md)

**Actor**: User  
**Goal**: View current backup status and progress  
**Priority**: Must Have

### [UC-MON-002: Generate Reports](UC-MON-002.md)

**Actor**: User  
**Goal**: Generate backup and system reports  
**Priority**: Could Have

## Integration

### [UC-INT-001: External System Integration](UC-INT-001.md)

**Actor**: System  
**Goal**: Integrate with external systems and services  
**Priority**: Could Have

## Error Handling

### [UC-ERR-001: Handle Backup Errors](UC-ERR-001.md)

**Actor**: System  
**Goal**: Handle and recover from backup errors  
**Priority**: Must Have

## Use Case Summary

| Functional Area        | Use Cases | Must Have | Should Have | Could Have |
|------------------------|-----------|-----------|-------------|------------|
| Repository Management  | 2         | 2         | 0           | 0          |
| Backup Operations      | 2         | 1         | 1           | 0          |
| Recovery Operations    | 2         | 2         | 0           | 0          |
| Security               | 2         | 1         | 1           | 0          |
| Policy Management      | 1         | 0         | 1           | 0          |
| Monitoring & Reporting | 2         | 1         | 0           | 1          |
| Integration            | 1         | 0         | 0           | 1          |
| Error Handling         | 1         | 1         | 0           | 0          |
| **Total**              | **13**    | **8**     | **3**       | **2**      |

## Navigation

- [Back to Requirements Overview](README.md)
- [View Complete SRS](srs-4-use-cases.md)
- [Requirements Prioritization Matrix](requirements-prioritization-matrix.md)
