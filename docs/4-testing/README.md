---
title: "Testing Documentation"
id: "RM-006"
type: [ readme ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "27-10-2023"
tags: [ readme, testing ]
links:
    tooling: [ ]
---

# Testing Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 27-10-2023

## 1. Purpose

**When to use this template**: This folder centralizes test strategies, coverage goals, QA playbooks, and release validation checklists.
**Location**: `docs/4-testing/`

## 2. What Belongs Here?

- Test strategy documents and matrices.
- Manual/automated QA procedures.
- Coverage reports and quality gates (summaries, detailed reports go in `../reports/`).

## 3. What Does NOT Belong Here?

- Individual test logs (keep near CI artifacts).
- Implementation details (see `../3-implementation/`).
- Operational runbooks (see `../guides/`).

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.

- **Naming Convention**: `<type>-<description>.md` (e.g., `PLAN-Release-1.0-Test-Plan.md`, `STRAT-Performance-Testing.md`, `CASE-Login-Functionality.md`).

## 5. Available Templates

- `_template.md`: A generic template, best suited for **STRAT** (Test Strategy) documents.
- `_template.plan.md`: A template specifically for **PLAN** (Test Plan) documents.

# References

- Link to additional resources, specs, or tickets
