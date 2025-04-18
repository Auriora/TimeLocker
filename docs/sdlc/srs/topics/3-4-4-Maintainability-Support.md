# 3.4.4 Maintainability &amp; Support

| ID               | Requirement                                                                                                              | Priority    | Rationale                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------- | ------------------------------------------------- |
| <a id="nfrMaint01">**NFR-MAINT-01**</a> | Codebase shall be modularised into UI, core, and plugin modules.                                                         | Must-have   | Facilitates modification and extension.           |
| <a id="nfrMaint02">**NFR-MAINT-02**</a> | Unit-test coverage >= 80 %.                                                                                               | Must-have   | Supports regression prevention and analysability. |
| <a id="nfrMaint03">**NFR-MAINT-03**</a> | Source code shall pass static analysis (flake8 for Python, clang-tidy for C/C++) with zero critical issues before merge. | Must-have   | Ensures code quality and maintainability.         |
| <a id="nfrMaint04">**NFR-MAINT-04**</a> | Application shall deliver updates via in-app auto-update mechanism.                                                      | Should-have | Simplifies support and patch distribution.        |