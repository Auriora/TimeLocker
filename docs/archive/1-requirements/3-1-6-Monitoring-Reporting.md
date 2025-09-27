# 3.1.6 Monitoring &amp; Reporting

| ID                                  | Requirement                                                                                            | Priority    | Rationale                                       |
|-------------------------------------|--------------------------------------------------------------------------------------------------------|-------------|-------------------------------------------------|
| <a id="frMon001">**FR-MON-001**</a> | Log all backup and restore operations with timestamps and status.                                      | Must-have   | Auditability.                                   |
| <a id="frMon002">**FR-MON-002**</a> | Provide desktop and email notifications for success/failure.                                           | Must-have   | User awareness.                                 |
| <a id="frMon003">**FR-MON-003**</a> | Generate exportable audit reports (PDF/CSV).                                                           | Should-have | Compliance evidence.                            |
| <a id="frMon004">**FR-MON-004**</a> | Display storage utilisation and performance metrics.                                                   | Should-have | Capacity planning.                              |
| <a id="frMon005">**FR-MON-005**</a> | Detect integrity breaches or audit-log gaps and provide configurable breach-notification workflow.     | Must-have   | GDPR Art. 33 breach notification.               |
| <a id="frMon006">**FR-MON-006**</a> | Maintain hash-chained, append-only audit log with tamper detection.                                    | Must-have   | GDPR Arts. 5-2 & 30 accountability.             |
| <a id="frMon007">**FR-MON-007**</a> | Provide CLI command `audit verify` that exits non-zero on hash-chain break and surfaces result in GUI. | Must-have   | Detect tampering quickly (GDPR accountability). |