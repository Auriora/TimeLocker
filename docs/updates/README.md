---
title: "Updates Log Documentation"
id: "RM-017"
type: [ readme ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "27-10-2023"
tags: [readme, updates]
links:
  tooling: []
---

# Updates Log Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 08-11-2025

## 1. Purpose

**When to use this template**: This directory contains a chronological log of significant, human-authored updates. Think of it as a project diary or a changelog
that explains the *why* and *what* of a change.
**Location**: `docs/updates/`

## 2. What Belongs Here?

- Summaries of major feature implementations.
- Notes on significant refactoring or dependency changes.
- Manual records of important events not captured elsewhere.
- Entries should follow the naming convention: `YYYY-MM-DD-HHMMSS-descriptive-slug.md`.

## 3. What Does NOT Belong Here?

- Automated reports (see `../reports/`).
- Formal architectural decisions (see `../2-architecture/`).

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.
    - [ ] Add entry to `index.md` (newest first).

- **Naming Convention**: `YYYY-MM-DD-HHMMSS-descriptive-slug.md`
  - **Format**: Year-Month-Day-HourMinuteSecond-descriptive-slug
  - **Example**: `2025-11-08-082339-repository-manager-implementation.md`
  - **Rationale**: Timestamp ensures uniqueness and precise chronological ordering

## 5. Available Templates

- `_template.md`: A generic template for any update log entry.

# References

- Link to additional resources, specs, or tickets
