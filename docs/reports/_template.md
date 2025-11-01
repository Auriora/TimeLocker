---
title: "Report: {{title}}"
id: "report-{{id}}"
type: [ report ]
status: [ draft | in_review | approved ]
owner: "{{owner}}" # e.g., Author, Reporting Team
last_reviewed: "{{DD-MM-YYYY}}"
tags: [report, quality, tag1, tag2] # Practical tags for organization and search
links:
  tooling: [ruff, mypy, bandit]
---

# Report: {{title}}

- **Owner**: {{owner}} # e.g., Author, Reporting Team
- **Status**: [Draft | In Review | Approved]
- **Created Date**: DD-MM-YYYY
- **Audience**: [e.g., Stakeholders, Engineering Teams, QA]
- **Scope**: [e.g., Commit SHA, Release Version]

## 1. Purpose

Provide a high-level overview of the findings. What is the key takeaway? Clearly state the objective and scope of this report.

## 2. Detailed Findings

Use tables, lists, or code blocks to present the data.

| Finding | Severity | Details |
|---------|----------|---------|
|         |          |         |

## 3. Recommendations

List any action items or next steps based on the report's findings.

- **Action 1**: [Description]
- **Action 2**: [Description]

<!-- Add more numbered sections as needed, e.g., ## 4. [Another Section Title] -->

# References

- Provide links to the raw output or the tool that generated the report.
- Link to additional resources, specifications, or related tickets.
