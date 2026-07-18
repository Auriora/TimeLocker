---
title: "{{title}}"
id: "{{type id 2/3 alpha characters}}-{{id 3 numeric digits}}"
type: [ readme ]
status: [ draft | in_review | approved ]
owner: "{{owner}}"
last_reviewed: "{{DD-MM-YYYY}}"
tags: [ readme ]
links:
    tooling: [ ruff, mypy, bandit ]
---

# [Document Title]

- **Owner**: [Name or Team]
- **Status**: [Draft | In Review | Approved]
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY

## 1. Purpose

**When to use this template**: [Describe the specific scenario, e.g., "Use for any new feature that requires architectural changes."]
**Location**: [Specify the folder where documents created from this template should be stored, e.g., `docs/designs/`]

## 2. What Belongs Here?

- Markdown templates (`_template.md`, `_template.specific-name.md`) for different document types.
- Explanations of when and how to use each template.

## 3. What Does NOT Belong Here?

- Historical delivery records; use Git history rather than keeping snapshots in `docs/`.
- General guides on documentation practices (see `../guides/`).

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.

- **Naming Convention**: [Specify how to name files created from this template, e.g., `DD-MM-YYYY-feature-name.md`]

## 5. Available Templates

- `_template.md`: A template for creating new document templates, including guidance on purpose, location, and usage notes.

# References

- Link to additional resources, specs, or tickets
