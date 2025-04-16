# 3.4.4 Maintainability &amp; Support

| ID               | Requirement                                                                                                              | Priority    | Rationale                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------- | ------------------------------------------------- |
| **NFR‑MAINT‑01** | Codebase shall be modularised into UI, core, and plugin modules.                                                         | Must‑have   | Facilitates modification and extension.           |
| **NFR‑MAINT‑02** | Unit‑test coverage ≥ 80 %.                                                                                               | Must‑have   | Supports regression prevention and analysability. |
| **NFR‑MAINT‑03** | Source code shall pass static analysis (flake8 for Python, clang‑tidy for C/C++) with zero critical issues before merge. | Must‑have   | Ensures code quality and maintainability.         |
| **NFR‑MAINT‑04** | Application shall deliver updates via in‑app auto‑update mechanism.                                                      | Should‑have | Simplifies support and patch distribution.        |
