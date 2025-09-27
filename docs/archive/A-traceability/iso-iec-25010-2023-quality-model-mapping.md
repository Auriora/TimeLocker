# 5.6 ISO / IEC 25010:2023 Quality Model Mapping

| Characteristic → Sub-characteristic | SRS Coverage                                                                                                                                                     | Status |
|-------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| **Functional Suitability**          | § [3.1 Functional Requirements](3-1-Functional-Requirements.md); [UC-BK-001](UC-BK-001.md) (main SRS)                                                            | Good   |
| * Functional completeness           | [FR-RM-*](3-1-1-Repository-Management.md), [FR-BK-*](3-1-2-Backup-Operations.md), [FR-RC-*](3-1-4-Recovery-Operations.md), [FR-PM-*](3-1-5-Policy-Management.md) | Good   |
| * Functional correctness            | [FR-BK-004](3-1-2-Backup-Operations.md#frBk004), [FR-RC-003](3-1-4-Recovery-Operations.md#frRc003)                                                               | Good   |
| * Functional appropriateness        | Personas rationale (main SRS)                                                                                                                                    | Good   |
| **Performance Efficiency**          | § [3.4.1 Performance](3-4-1-Performance.md); [NFR-AUD-01](3-4-1-Performance.md#nfrAud01)/[02](3-4-1-Performance.md#nfrAud02) (main SRS)                          | Good   |
| * Time behaviour                    | Startup <= 2 s, UI <= 200 ms, throughput >= 80 MB/s                                                                                                              | Good   |
| * Resource utilisation              | CPU <= 60 %, [NFR-SEC-12](3-4-6-Security-Compliance.md#nfrSec12)                                                                                                 | Good   |
| * Capacity                          | 10 TB / 10 M files                                                                                                                                               | Good   |
| **Compatibility**                   | § [3.4.8 Interoperability](3-4-8-Interoperability.md); [NFR-COMP-01](3-4-8-Interoperability.md#nfrComp01) (main SRS)                                             | Good   |
| * Co-existence                      | [NFR-COMP-01](3-4-8-Interoperability.md#nfrComp01)                                                                                                               | Good   |
| * Interoperability                  | Restic v2, S3 v4, SFTP                                                                                                                                           | Good   |
| **Usability**                       | § [3.4.3 Usability](3-4-3-Usability.md); WCAG 2.2 AA (main SRS)                                                                                                  | Good   |
| **Reliability**                     | § [3.4.2 Reliability & Stability](3-4-2-Reliability-Stability.md) (main SRS)                                                                                     | Good   |
| **Security**                        | § [3.4.6 Security & Compliance](3-4-6-Security-Compliance.md) (main SRS)                                                                                         | Strong |
| **Maintainability**                 | § [3.4.4 Maintainability & Support](3-4-4-Maintainability-Support.md); [NFR-MAINT-03](3-4-4-Maintainability-Support.md#nfrMaint03)                               | Good   |
| **Portability**                     | § [3.4.5 Portability](3-4-5-Portability.md) (main SRS)                                                                                                           | Good   |

*Quality-in-use KPIs (effectiveness, efficiency, satisfaction, risk) are tracked via usability tests and documented
in `docs/compliance/quality_in_use_test_plan.md`.*