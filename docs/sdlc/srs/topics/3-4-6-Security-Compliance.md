# 3.4.6 Security &amp; Compliance

| ID             | Requirement                                                                                         | Priority    | Rationale                                                |
| -------------- | --------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------- |
| <a id="nfrSec01"></a>**NFR-SEC-01** | Data at rest shall be encrypted with AES-256.                                                       | Must-have   | Ensures confidentiality (ASVS V6).                       |
| <a id="nfrSec02"></a>**NFR-SEC-02** | Data in transit shall use TLS 1.3 with modern cipher suites.                                        | Must-have   | Protects against network eavesdropping.                  |
| <a id="nfrSec03"></a>**NFR-SEC-03** | Application shall implement GDPR data-subject rights (access, rectification, erasure, portability). | Must-have   | Mandatory legal compliance.                              |
| <a id="nfrSec04"></a>**NFR-SEC-04** | Quarterly vulnerability scans shall be performed and critical issues remediated before release.     | Should-have | Maintains security posture.                              |
| <a id="nfrSec12"></a>**NFR-SEC-12** | Region validation must add <= 50 ms overhead to repository connection setup.                         | Should-have | Minimises performance impact while enforcing compliance. |