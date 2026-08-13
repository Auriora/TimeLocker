---
title: "Requirements Documentation"
doc_type: reference
id: "RM-003"
type: [ readme ]
status: active
owner: "Auriora Team"
last_reviewed: 2026-07-26
tags: [readme, requirements]
links:
  tooling: []
---

# Requirements Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 27-10-2023

## 1. Purpose

**When to use this template**: This folder captures product expectations, user stories, functional/non-functional requirements, and stakeholder personas.
**Location**: `docs/1-requirements/`

## 2. What Belongs Here?

- Product requirements, SRS documents, user journeys.
- Acceptance criteria and success metrics.
- Personas, market analysis snippets relevant to scope.

## 3. What Does NOT Belong Here?

- Implementation details (see `../3-implementation/`).
- Architectural decisions (see `../2-architecture/`).
- Test execution results (see `../4-testing/`).

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.

- **Naming Convention**: `<type>-<description>.md` (e.g., `SRS-Overview.md`, `WF-Outlook-Calendar.md`). For sequenced documents, use a numeric prefix:
  `[number]-<type>-<description>.md`.

## 5. Available Templates

- Use the central [durable-document template](../templates/durable-document.md)
  for accepted current-state requirements. Use an active spec for proposed
  implementation work.

## 6. Current Requirements

- [System Operations Requirements](./system-operations.md) — protected launcher,
  authorization, backup/retention, visibility, privacy, tray, and platform
  invariants.

# References

- Link to additional resources, specs, or tickets
