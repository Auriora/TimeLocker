# 4.8 ASVS Control Mapping

| ASVS v4.0 Control | Description (simplified) | SRS Requirement IDs |
| --- | --- | --- |
| **V1.2** – Document secure design and architecture decisions | Architecture & threat modelling documented | FR‑SEC‑007, Appendix 4.7 |
| **V2.1** – Protect authentication credentials in storage | Credentials stored in OS key‑ring | FR‑SEC‑002 |
| **V4.1** – Enforce access‑control policy across all functions | RBAC & vault locking | FR‑SEC‑004, FR‑SEC‑003 |
| **V6.1** – Use strong, industry‑standard encryption algorithms | AES‑256 for data at rest | FR‑SEC‑001 |
| **V8.3** – Protect sensitive data in backups and logs | Encrypted backups, redacted logs | FR‑SEC‑001, FR‑MON‑006 |
| **V9.1** – Use TLS 1.2+ with modern ciphers | TLS 1.3 enforced for remote transfers | FR‑SEC‑001 |
| **V11.2** – Ensure audit logging is tamper‑evident | Hash‑chained, append‑only log | FR‑MON‑006, FR‑MON‑007, NFR‑AUD‑01, NFR‑AUD‑02, NFR‑AUD‑03, NFR‑AUD‑04 |
| **V14.2** – Secure default configuration | Privacy‑by‑default settings in onboarding | FR‑SEC‑007 |

    *Note: Full traceability matrix to be maintained in `docs/compliance/ASVS_traceability_matrix.csv`.*