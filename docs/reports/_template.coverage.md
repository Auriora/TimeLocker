---
title: "Report: Test Coverage"
id: "COV-{{id}}"
type: [ report ]
status: [ draft | in_review | approved ]
owner: "{{owner}}" # e.g., Author, Reporting Team
last_reviewed: "{{DD-MM-YYYY}}"
tags: [report, quality, coverage] # Practical tags for organization and search
links:
  tooling: []
---

# Report: Test Coverage

- **Owner**: {{owner}} # e.g., Author, Reporting Team
- **Status**: [Draft | In Review | Approved]
- **Created Date**: DD-MM-YYYY
- **Last Updated**: 2025-10-19
- **Audience**: [e.g., Stakeholders, Engineering Teams, QA]
- **Scope**: [e.g., Commit SHA, Release Version]

## 1. Purpose

This report provides a summary of the project's test coverage. Clearly state the objective and scope of this report.

## 2. Detailed Findings

### Coverage Summary

- Overall coverage: {{overall_coverage_percent}}%  (update from CI coverage artifact)
- Lines/Branches: lines={{lines_coverage_percent}}%, branches={{branches_coverage_percent}}%
- Measurement date: {{measurement_date}}

### How to reproduce

- Run tests with coverage locally or in CI:

    - pytest --cov=src --cov-report=xml --cov-report=term

- Upload or inspect `coverage.xml`/HTML report for module-level details.

### Breakdown by Module

| Module  | Lines | Covered |   % |
|---------|------:|--------:|----:|
| example |   100 |      80 | 80% |

Replace the above table with actual module rows from the coverage report. For projects with many modules, include the top N modules with the lowest %.

### Notable Gaps

- Modules with < {{low_coverage_threshold}}% coverage (replace threshold placeholder):
    - {{module_name}} — missing tests for XYZ functions (brief rationale)

- Categories to prioritise: business logic, security-sensitive code, public API surface, and any recently modified modules.

## 3. Recommendations

List any action items or next steps based on the report's findings.

- **Action 1**: Add unit tests for modules listed above. Owner: @dev-team. Due: {{due_date}}
- **Action 2**: Add integration tests for key flows that cross module boundaries. Owner: @qa-team.
- **Action 3**: Configure CI to publish coverage artifacts and fail PRs when overall coverage drops below {{ci_threshold}}%.
- **Action 4**: Run periodic coverage audits (monthly) and link results in `docs/reports/`.

# References

- Provide links to the raw output or the tool that generated the report.
- Link to additional resources, specifications, or related tickets.

### Notes

- Use this file as the canonical, short summary for release notes and planning.
- Replace placeholders ({{...}}) with values from CI, coverage tooling, or project trackers.
