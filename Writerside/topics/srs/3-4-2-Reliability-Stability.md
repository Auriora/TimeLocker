# 3.4.2 Reliability &amp; Stability

| ID             | Requirement                                                               | Priority    | Rationale                                                     |
|----------------|---------------------------------------------------------------------------|-------------|---------------------------------------------------------------|
| <a id="nfrRel01">**NFR-REL-01**</a> | Application availability >= 99.5 % (excluding scheduled maintenance).      | Must-have   | Meets user expectations for backup reliability.               |
| <a id="nfrRel02">**NFR-REL-02**</a> | Mean Time Between Failures (MTBF) >= 500 h of continuous backup operation. | Should-have | Provides measurable reliability metric for engineering goals. |
| <a id="nfrRel03">**NFR-REL-03**</a> | Automatic resume of interrupted backups.                                  | Must-have   | Prevents data loss and manual intervention after failures.    |