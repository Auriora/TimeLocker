# 3.1.3 Security

| ID             | Requirement                                                                          | Priority    | Rationale                                 |
|----------------|--------------------------------------------------------------------------------------|-------------|-------------------------------------------|
| **FR‑SEC‑001** | Encrypt data in transit (TLS) and at rest (Restic encryption).                       | Must‑have   | Protect sensitive data.                   |
| **FR‑SEC‑002** | Store repository credentials securely in OS key‑ring.                                | Must‑have   | Prevent credential leakage.               |
| **FR‑SEC‑003** | Implement backup vault locking to prevent concurrent conflicting writes.             | Should‑have | Compliance and safety.                    |
| **FR‑SEC‑004** | Provide RBAC with predefined roles (Admin, Operator, Viewer).                        | Should‑have | Governance and least privilege.           |
| **FR‑SEC‑005** | Provide user‑initiated export of personal metadata in JSON format.                   | Must‑have   | GDPR Art. 20 data portability.            |
| **FR‑SEC‑006** | Provide user‑initiated erasure of stored personal metadata without deleting backups. | Must‑have   | GDPR Art. 17 right to erasure.            |
| **FR‑SEC‑007** | Default to secure, privacy‑by‑default configuration and onboarding consent notice.   | Must‑have   | GDPR Art. 25 privacy by design & default. |
| **FR‑SEC‑008** | Bundle DPIA checklist and compliance documentation with each release.                | Could‑have  | GDPR Art. 35 DPIA.                        |