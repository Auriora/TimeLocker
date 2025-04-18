# 3.2 External Interface Requirements

| ID            | Requirement                                                                                               | Priority    | Rationale                                                     |
|---------------|-----------------------------------------------------------------------------------------------------------|-------------|---------------------------------------------------------------|
| **EIR‑UI‑01** | User Interface: GTK desktop application with wizard‑based setup, dashboard, configuration dialogs, and restore browser. | Must‑have   | Provides consistent and accessible user experience.           |
| **EIR‑HW‑01** | Hardware Interfaces: Access to local file system, external drives via OS.                                 | Must‑have   | Essential for backup and restore operations.                  |
| **EIR‑SW‑01** | Software Interfaces: Restic CLI, OS key‑ring APIs, cron/systemd, network stack (TLS).                    | Must‑have   | Required for core functionality and security.                 |
| **EIR‑COM‑01** | Communication Interfaces: HTTPS/TLS for cloud storage and API interactions.                              | Must‑have   | Ensures secure data transmission.                             |
