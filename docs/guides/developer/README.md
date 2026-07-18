---
title: "Developer Guides Documentation"
id: "RM-008"
type: [ readme ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "27-10-2023"
tags: [readme, guides, developer]
links:
  tooling: []
---

# Developer Guides Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 27-10-2023

## 1. Purpose

**When to use this template**: This folder captures contributor workflows, operational procedures, and development environment configuration. These guides are
aimed at developers working on the project.
**Location**: `docs/guides/developer/`

## 2. What Belongs Here?

- Development environment setup guides.
- Operational playbooks (alerts, on-call expectations).
- Tooling instructions (linting, testing, release flows).
- AI agent playbooks and guidelines.

## 3. What Does NOT Belong Here?

- Planning artifacts; use active specs or the issue tracker.
- Architecture decisions (see `../../2-architecture/`).
- Task updates; record them in the active spec or issue tracker.

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.

- **Naming Convention**: N/A for this file.

## 5. Available Templates & Guides

- `_template.md`: Generic developer guide template.
- `automation-examples.md`: Scheduling automation patterns (env vars, systemd, cron, containers).
- `scheduling-guide.md`: Step-by-step jobs scheduling playbook.
- `plugin-wrapper-development.md`: Guide for developing backup tool plugin wrappers.
- `performance-optimization-guide.md`: Performance optimization strategies.
- `test-isolation-quick-reference.md`: Test isolation and XDG compliance reference.

# References

- Link to additional resources, specs, or tickets
