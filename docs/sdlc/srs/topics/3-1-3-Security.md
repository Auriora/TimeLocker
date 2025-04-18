# 3.1.3 Security

| ID             | Requirement                                                                          | Priority    | Rationale                                 |
|----------------|--------------------------------------------------------------------------------------|-------------|-------------------------------------------|
| <a id="frSec001">**FR-SEC-001**</a> | Encrypt data in transit (TLS) and at rest (Restic encryption).                       | Must-have   | Protect sensitive data.                   |
| <a id="frSec002">**FR-SEC-002**</a> | Store repository credentials securely in OS key-ring.                                | Must-have   | Prevent credential leakage.               |
| <a id="frSec003">**FR-SEC-003**</a> | Implement backup vault locking to prevent concurrent conflicting writes.             | Should-have | Compliance and safety.                    |
| <a id="frSec004">**FR-SEC-004**</a> | Provide RBAC with predefined roles (Admin, Operator, Viewer).                        | Should-have | Governance and least privilege.           |
| <a id="frSec005">**FR-SEC-005**</a> | Provide user-initiated export of personal metadata in JSON format.                   | Must-have   | GDPR Art. 20 data portability.            |
| <a id="frSec006">**FR-SEC-006**</a> | Provide user-initiated erasure of stored personal metadata without deleting backups. | Must-have   | GDPR Art. 17 right to erasure.            |
| <a id="frSec007">**FR-SEC-007**</a> | Default to secure, privacy-by-default configuration and onboarding consent notice.   | Must-have   | GDPR Art. 25 privacy by design & default. |
| <a id="frSec008">**FR-SEC-008**</a> | Bundle DPIA checklist and compliance documentation with each release.                | Could-have  | GDPR Art. 35 DPIA.                        |