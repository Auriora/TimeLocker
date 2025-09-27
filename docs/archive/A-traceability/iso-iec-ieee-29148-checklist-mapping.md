# 5.4 ISO/IEC/IEEE 29148 Checklist Mapping

| 29148 Clause | "Shall" Statement                                  | Where Addressed                                                                                                     |
|--------------|----------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| 6.4.3.a      | Each requirement shall be uniquely identified.     | All FR-/NFR- IDs                                                                                                    |
| 6.4.3.b      | Each requirement shall be verifiable.              | Verifiable metrics in FR/NFR tables                                                                                 |
| 6.4.3.c      | Requirements shall be traceable upward & downward. | Appendices [5.1](5-1-GDPR-Impact-Mapping.md), [5.2](5-2-ASVS-Control-Mapping.md), [5.3](5-3-WCAG-2-2-AA-Mapping.md) |
| 6.4.3.d      | Each requirement shall include rationale.          | Rationale column in all FR tables                                                                                   |
| 6.4.4        | External interfaces shall be identified.           | § [3.2 External Interface Requirements](3-2-External-Interface-Requirements.md) (main SRS)                          |
| 6.4.5        | Changes to requirements shall be managed.          | Appendix [6.3 Issues List](6-3-Issue-List.md); release gate docs                                                    |
| 6.4.6        | System states & modes shall be defined.            | Appendix [6.2 Analysis Models](6-2-Analysis-Models.md)                                                              |
| 6.4.7        | Safety & security requirements shall be specified. | [FR-SEC-*](3-1-3-Security.md) IDs, [NFR-SEC-*](3-4-6-Security-Compliance.md) IDs                                    |
| 6.4.8        | Environmental constraints shall be documented.     | § 2.4 Constraints; § [3.4.5 Portability](3-4-5-Portability.md) (main SRS)                                           |
| 6.4.9        | Quality attributes shall be provided.              | § [3.4 Non-Functional Requirements](3-4-Non-Functional-Requirements.md) (main SRS)                                  |

*Note: Full traceability matrix to be maintained in `docs/compliance/29148_traceability_matrix.csv`.*