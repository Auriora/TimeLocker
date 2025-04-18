# 4.8 ASVS Control Mapping

| ASVS v4.0 Control | Description (simplified) | SRS Requirement IDs |
| --- | --- | --- |
| **V1.2** – Document secure design and architecture decisions | Architecture & threat modelling documented | [FR‑SEC‑007](3-1-3-Security.md#frSec007), Appendix 4.7 |
| **V2.1** – Protect authentication credentials in storage | Credentials stored in OS key‑ring | [FR‑SEC‑002](3-1-3-Security.md#frSec002) |
| **V4.1** – Enforce access‑control policy across all functions | RBAC & vault locking | [FR‑SEC‑004](3-1-3-Security.md#frSec004), [FR‑SEC‑003](3-1-3-Security.md#frSec003) |
| **V6.1** – Use strong, industry‑standard encryption algorithms | AES‑256 for data at rest | [FR‑SEC‑001](3-1-3-Security.md#frSec001) |
| **V8.3** – Protect sensitive data in backups and logs | Encrypted backups, redacted logs | [FR‑SEC‑001](3-1-3-Security.md#frSec001), [FR‑MON‑006](3-1-6-Monitoring-Reporting.md#frMon006) |
| **V9.1** – Use TLS 1.2+ with modern ciphers | TLS 1.3 enforced for remote transfers | [FR‑SEC‑001](3-1-3-Security.md#frSec001) |
| **V11.2** – Ensure audit logging is tamper‑evident | Hash‑chained, append‑only log | [FR‑MON‑006](3-1-6-Monitoring-Reporting.md#frMon006), [FR‑MON‑007](3-1-6-Monitoring-Reporting.md#frMon007), [NFR‑AUD‑01](3-4-1-Performance.md#nfrAud01), [NFR‑AUD‑02](3-4-1-Performance.md#nfrAud02), [NFR‑AUD‑03](3-4-10-Auditability.md#nfrAud03), [NFR‑AUD‑04](3-4-10-Auditability.md#nfrAud04) |
| **V14.2** – Secure default configuration | Privacy‑by‑default settings in onboarding | [FR‑SEC‑007](3-1-3-Security.md#frSec007) |

    *Note: Full traceability matrix to be maintained in `docs/compliance/ASVS_traceability_matrix.csv`.*