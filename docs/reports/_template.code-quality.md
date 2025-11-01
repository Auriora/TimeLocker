---
title: "Report: Code Quality"
id: "CQR-{{id}}"
type: [ report ]
status: [ draft | in_review | approved ]
owner: "{{owner}}" # e.g., Author, Reporting Team
last_reviewed: "{{DD-MM-YYYY}}"
tags: [report, quality, code-quality] # Practical tags for organization and search
links:
  tooling: [ruff, mypy, bandit]
---

# Report: Code Quality

- **Owner**: {{owner}} # e.g., Author, Reporting Team
- **Status**: [Draft | In Review | Approved]
- **Created Date**: DD-MM-YYYY
- **Last Updated**: {{DD-MM-YYYY}}
- **Audience**: [e.g., Stakeholders, Engineering Teams, QA]
- **Scope**: [e.g., Commit SHA, Release Version]

## 1. Purpose

This report provides a high-level overview of code quality findings, including lint errors, type errors, and security issues. The key takeaway is to summarize
the current state of code quality. Clearly state the objective and scope of this report.

## 2. Detailed Findings

### Summary

- Lint errors: {{lint_errors_total}}  (replace with value from CI)
- Type errors: {{type_errors_total}}  (replace with mypy summary)
- Security issues: {{security_issues_total}}  (replace with bandit/scan summary)

### Lint

How to reproduce:

- Run ruff locally or in CI:

    - ruff check .

Template content to include from CI run:

- Top 5 most common lint rules violated
- Files with the most lint failures

Example:

- top_rules:
    - E501 (line too long): 12
    - F401 (unused import): 8

### Types

How to reproduce:

- Run mypy (recommended configuration: strict or project-specific config):

    - mypy src/ --show-error-codes

Template content to include:

- Number of files checked
- Number of errors
- Representative example errors with file and line

### Security

How to reproduce:

- Run bandit or other security linters (or use SCA tools where available):

    - bandit -r src/ -lll

Template content to include:

- List of findings (id, severity, filename, short description)
- Whether findings are false positives or need remediation

## 3. Recommendations

List any action items or next steps based on the report's findings.

- **Action 1**: Address high-severity security findings within 1 sprint. Owner: @security-owner
- **Action 2**: Fix all blocking type errors before the next release. Owner: @backend-owner
- **Action 3**: Add ruff and mypy checks to CI with severity thresholds and gating (fail pipeline on new issues).
- **Action 4**: Add automated reporting links (CI job artifacts, coverage dashboards) to this report's `links:` frontmatter.

# References

- Provide links to the raw output or the tool that generated the report.
- Link to additional resources, specifications, or related tickets.

### Notes

- Replace placeholders ({{...}}) with actual values produced by CI or tooling runs.
- Keep this report as a short, actionable summary targeted to maintainers and release managers.
