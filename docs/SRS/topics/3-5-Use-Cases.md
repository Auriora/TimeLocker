# 3.5 Use Cases

This document lists the primary use cases that drive the functional requirements in the Desktop Backup Application (DBA) SRS. Each use case is uniquely identified (UC‑XX‑###) and references the actors, goals, and success criteria.

| ID                              | Name                      | Primary Actors            | Brief Goal                                       |
|---------------------------------|---------------------------|---------------------------|--------------------------------------------------|
| **[UC‑RM‑001](UC-RM-001.md)**   | Register Repository       | Everyday User, Power User | Add a new backup repository (local, S3, SFTP…).  |
| **[UC‑RM‑002](UC-RM-002.md)**   | Edit / Remove Repository  | Everyday User, Power User | Modify or delete an existing repository.         |
| **[UC‑BK‑001](UC‑BK‑001.md)**   | Create Backup             | Everyday User, Power User | Initiate or schedule a backup to a repository.   |
| **[UC‑BK‑002](UC-BK-002.md)**   | Validate Backup Integrity | System                    | Verify snapshot consistency with `restic check`. |
| **[UC‑SC‑001](UC-SC-001.md)**   | Configure Backup Schedule | Everyday User             | Set automated backup frequency.                  |
| **[UC‑RC‑001](UC-RC-001.md)**   | Restore Snapshot          | Everyday User             | Recover files/folders from a chosen snapshot.    |
| **[UC‑RC‑002](UC-RC-002.md)**   | Disaster Recovery         | Power User                | Restore full system from bare‑metal.             |
| **[UC‑PM‑001](UC-PM-001.md)**   | Update Retention Policy   | Power User                | Adjust rules for pruning old backups.            |
| **[UC‑SEC‑001](UC-SEC-001.md)** | Export Personal Metadata  | Everyday User             | Download stored personal settings & logs.        |
| **[UC‑SEC‑002](UC-SEC-002.md)** | Erase Personal Metadata   | Everyday User             | Delete stored personal settings & logs.          |
| **[UC‑MON‑001](UC-MON-001.md)** | View Backup Status        | Everyday User             | Monitor current/last backup progress & result.   |
| **[UC‑MON‑002](UC-MON-002.md)** | Verify Audit Log          | Power User                | Run `audit verify` and review tamper check.      |
| **[UC‑ERR‑001](UC-ERR-001.md)** | Handle Backup Error       | System                    | Retry failed backup & surface error to user.     |
| **[UC‑INT‑001](UC-INT-001.md)** | Scripted Backup via CLI   | Power User                | Trigger backup using command‑line interface.     |

