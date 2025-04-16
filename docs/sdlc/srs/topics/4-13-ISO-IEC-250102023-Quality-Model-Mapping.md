# 4.13 ISO / IEC 25010:2023 Quality Model Mapping

| Characteristic → Sub‑characteristic | SRS Coverage                                        | Status |
| ----------------------------------- | --------------------------------------------------- | ------ |
| **Functional Suitability**          | § 3.1 Functional Requirements; UC‑BK‑001 (main SRS) | Good   |
| • Functional completeness           | FR‑RM‑*, FR‑BK‑*, FR‑RC‑*, FR‑PM‑*                  | Good   |
| • Functional correctness            | FR‑BK‑004, FR‑RC‑003                                | Good   |
| • Functional appropriateness        | Personas rationale (main SRS)                       | Good   |
| **Performance Efficiency**          | § 3.4.1 Performance; NFR‑AUD‑01/02 (main SRS)       | Good   |
| • Time behaviour                    | Startup ≤ 2 s, UI ≤ 200 ms, throughput ≥ 80 MB/s    | Good   |
| • Resource utilisation              | CPU ≤ 60 %, NFR‑SEC‑12                              | Good   |
| • Capacity                          | 10 TB / 10 M files                                  | Good   |
| **Compatibility**                   | § 3.4.8 Interoperability; NFR‑COMP‑01 (main SRS)    | Good   |
| • Co‑existence                      | NFR‑COMP‑01                                         | Good   |
| • Interoperability                  | Restic v2, S3 v4, SFTP                              | Good   |
| **Usability**                       | § 3.4.3 Usability; WCAG 2.2 AA (main SRS)           | Good   |
| **Reliability**                     | § 3.4.2 Reliability & Stability (main SRS)          | Good   |
| **Security**                        | § 3.4.6 Security & Compliance (main SRS)            | Strong |
| **Maintainability**                 | § 3.4.4 Maintainability & Support; NFR‑MAINT‑03     | Good   |
| **Portability**                     | § 3.4.5 Portability (main SRS)                      | Good   |

*Quality‑in‑use KPIs (effectiveness, efficiency, satisfaction, risk) are tracked via usability tests and documented in `docs/compliance/quality_in_use_test_plan.md`.*