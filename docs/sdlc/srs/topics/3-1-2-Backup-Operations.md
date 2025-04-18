# 3.1.2 Backup Operations

| ID            | Requirement                                                      | Priority   | Rationale                       |
|---------------|------------------------------------------------------------------|------------|---------------------------------|
| <a id="frBk001">**FR‑BK‑001**</a> | Perform full backups of specified data sources.                  | Must‑have  | Baseline backup capability.     |
| <a id="frBk002">**FR‑BK‑002**</a> | Support incremental backups to reduce storage and transfer time. | Must‑have  | Efficiency for ongoing backups. |
| <a id="frBk003">**FR‑BK‑003**</a> | Enable scheduled backups (hourly, daily, weekly, custom cron).   | Must‑have  | Automation and reliability.     |
| <a id="frBk004">**FR‑BK‑004**</a> | Validate backup integrity after creation using Restic `check`.   | Must‑have  | Ensures recoverability.         |
| <a id="frBk005">**FR‑BK‑005**</a> | Execute parallel backup operations when system resources permit. | Could‑have | Performance optimisation.       |
