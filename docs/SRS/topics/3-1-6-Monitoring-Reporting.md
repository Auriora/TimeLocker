# 3.1.6 Monitoring &amp; Reporting

| ID             | Requirement                                                                                            | Priority    | Rationale                                       |
|----------------|--------------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------|
| **FR‑MON‑001** | Log all backup and restore operations with timestamps and status.                                      | Must‑have   | Auditability.                                   |
| **FR‑MON‑002** | Provide desktop and email notifications for success/failure.                                           | Must‑have   | User awareness.                                 |
| **FR‑MON‑003** | Generate exportable audit reports (PDF/CSV).                                                           | Should‑have | Compliance evidence.                            |
| **FR‑MON‑004** | Display storage utilisation and performance metrics.                                                   | Should‑have | Capacity planning.                              |
| **FR‑MON‑005** | Detect integrity breaches or audit‑log gaps and provide configurable breach‑notification workflow.     | Must‑have   | GDPR Art. 33 breach notification.               |
| **FR‑MON‑006** | Maintain hash‑chained, append‑only audit log with tamper detection.                                    | Must‑have   | GDPR Arts. 5‑2 & 30 accountability.             |
| **FR‑MON‑007** | Provide CLI command `audit verify` that exits non‑zero on hash‑chain break and surfaces result in GUI. | Must‑have   | Detect tampering quickly (GDPR accountability). |