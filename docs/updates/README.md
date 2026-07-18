---
title: "Updates Log Documentation"
id: "RM-017"
type: [ readme ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "18-07-2026"
tags: [readme, updates]
links:
  tooling: []
---

# Updates Log Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 18-07-2026

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
- Active implementation scope, acceptance criteria, or task state (see `../specs/`).

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

### Update Lifecycle

- `draft`: evidence or wording is incomplete and must not be cited as an approved outcome
- `in_review`: implementation evidence is present and awaiting review
- `approved`: claims, links, and validation evidence have been reviewed

An update may describe incomplete implementation while still being `approved`; approval means the record is accurate, not that every follow-up is complete.
Investigations must link to later fixes or explicitly say the finding remains open. Review draft entries before release and do not leave completed work in draft
indefinitely.

For spec-governed work, link the relevant package and summarize recorded task
evidence; do not duplicate its requirements, design, or full task checklist.

## 5. Available Templates

- `_template.md`: A generic template for any update log entry.

# References

- Link to additional resources, specs, or tickets
