# 3.2 External Interface Requirements

| ID            | Requirement                                                                                               | Priority    | Rationale                                                     |
|---------------|-----------------------------------------------------------------------------------------------------------|-------------|---------------------------------------------------------------|
| <a id="eirUi01">**EIR-UI-01**</a> | User Interface: GTK desktop application with wizard-based setup, dashboard, configuration dialogs, and restore browser. | Must-have   | Provides consistent and accessible user experience.           |
| <a id="eirHw01">**EIR-HW-01**</a> | Hardware Interfaces: Access to local file system, external drives via OS.                                 | Must-have   | Essential for backup and restore operations.                  |
| <a id="eirSw01">**EIR-SW-01**</a> | Software Interfaces: Restic CLI, OS key-ring APIs, cron/systemd, network stack (TLS).                    | Must-have   | Required for core functionality and security.                 |
| <a id="eirCom01">**EIR-COM-01**</a> | Communication Interfaces: HTTPS/TLS for cloud storage and API interactions.                              | Must-have   | Ensures secure data transmission.                             |
