# 3.1.2 Backup Operations

| ID            | Requirement                                                      | Priority   | Rationale                       |
|---------------|------------------------------------------------------------------|------------|---------------------------------|
| **FR‑BK‑001** | Perform full backups of specified data sources.                  | Must‑have  | Baseline backup capability.     |
| **FR‑BK‑002** | Support incremental backups to reduce storage and transfer time. | Must‑have  | Efficiency for ongoing backups. |
| **FR‑BK‑003** | Enable scheduled backups (hourly, daily, weekly, custom cron).   | Must‑have  | Automation and reliability.     |
| **FR‑BK‑004** | Validate backup integrity after creation using Restic `check`.   | Must‑have  | Ensures recoverability.         |
| **FR‑BK‑005** | Execute parallel backup operations when system resources permit. | Could‑have | Performance optimisation.       |