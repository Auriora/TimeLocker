# 3.4.6 Security &amp; Compliance

| ID             | Requirement                                                                                         | Priority    | Rationale                                                |
| -------------- | --------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------- |
| **NFR‑SEC‑01** | Data at rest shall be encrypted with AES‑256.                                                       | Must‑have   | Ensures confidentiality (ASVS V6).                       |
| **NFR‑SEC‑02** | Data in transit shall use TLS 1.3 with modern cipher suites.                                        | Must‑have   | Protects against network eavesdropping.                  |
| **NFR‑SEC‑03** | Application shall implement GDPR data‑subject rights (access, rectification, erasure, portability). | Must‑have   | Mandatory legal compliance.                              |
| **NFR‑SEC‑04** | Quarterly vulnerability scans shall be performed and critical issues remediated before release.     | Should‑have | Maintains security posture.                              |
| **NFR‑SEC‑12** | Region validation must add ≤ 50 ms overhead to repository connection setup.                         | Should‑have | Minimises performance impact while enforcing compliance. |
