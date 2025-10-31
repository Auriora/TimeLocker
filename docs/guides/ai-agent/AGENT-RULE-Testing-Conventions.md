---
type:        "agent_requested"
name:        "Testing conventions"
priority:    25
scope:       "tests/**"
description: "This rule provides a standardized testing format and policy for all projects."
cross_reference: ["preferences.md"]
apply_when:   "task_involves_tests == true"
---

# AI Agent Rule/Guide: Testing Conventions

- **Type**: agent_requested
- **Priority**: 25
- **Scope**: tests/**
- **Description**: This rule provides a standardized testing format and policy for all projects.
- **Cross-Reference**: preferences.md
- **Apply When**: task_involves_tests == true

## 1. Purpose

This rule establishes standardized testing conventions and policies for all projects, ensuring consistency, maintainability, and effectiveness of the test
suite. It guides the AI agent on how to approach and implement testing-related tasks.

## 2. Rule/Guideline Details

- **Test File Placement**: Always place tests next to the code they exercise when practical (e.g., `src/module/__tests__/` or `tests/module.test.ts`).
- **Consistent Test File Naming**: Prefer `*.test.ts` or `test_*.ts` depending on project conventions; include the `test` prefix if the project standard
  requires it.
- **Preferred Test Runner**: Prefer the repository's designated test runner (e.g., `vitest` for this repo).

### PR Checklist Additions (when tests are affected)

When making changes that affect tests, ensure the following are considered for the PR checklist:

-   [ ] Added/updated unit tests for changed behavior.
-   [ ] Added/updated minimal integration or smoke tests if public behavior changed.

## 3. Examples

- Unit tests for `src/utils/formatters.ts` → `tests/utils/formatters.test.ts` or `src/utils/formatters.test.ts` (follow repo convention).
- Integration tests that exercise multiple modules → `tests/integration/feature-name.test.ts`.

## 4. Rationale / Justification

Standardized testing conventions improve code quality, reduce onboarding time for new contributors, and ensure that tests are easily discoverable and
executable. Consistent test file placement and naming conventions contribute to a well-organized project structure, while a preferred test runner streamlines
the testing process.

## 5. Related Information

This rule is cross-referenced with `preferences.md` for general project preferences and guidance on applying other rules.

# References

- [General Preferences](./AGENT-GUIDE-General-Preferences.md)