---
title: "Plans Documentation"
id: "RM-010"
type: [ readme ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "18-07-2026"
tags: [readme, plans]
links:
  tooling: []
---

# Plans Documentation

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 18-07-2026

## 1. Purpose

This folder preserves standalone implementation plans created before TimeLocker
adopted the Spec Lifecycle Manager. New active implementation work belongs in
[`docs/specs/`](../specs/README.md); do not create new plans here.
**Location**: `docs/plans/`

## 2. What Belongs Here?

- Completed, superseded, or rejected legacy plans retained for link stability.
- Templates retained only to interpret historical documents.

## 3. What Does NOT Belong Here?

- New active implementation plans (use `../specs/`).
- Initial ideas or suggestions (see `../proposals/`).
- Architectural decisions (see `../2-architecture/`).
- Daily updates or change logs (see `../updates/`).

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.

- **Naming Convention**: N/A for this file.

### Legacy Plan Lifecycle

Plans use one of these states:

- `draft`: being written; not approved for execution
- `reviewing`: awaiting a decision
- `accepted`: approved but execution has not started
- `active`: execution is in progress and task statuses must be maintained
- `completed`: success criteria were met and linked evidence was reviewed
- `superseded`: replaced by a newer plan, issue queue, or implementation direction
- `rejected`: reviewed and intentionally not pursued

No standalone plan should remain `active`. A legacy active plan must be migrated
into one current-format spec package or explicitly closed. Superseded and
completed plans remain in place when other documents link to them; they are
historical context, not active work.

## 5. Available Templates

- `_template.md`: A generic template for any plan.
- `_template.test-coverage-plan.md`: A specific template for creating a plan to improve test coverage.

## Active Plans

- None. Current delivery work is indexed in [`docs/specs/`](../specs/README.md).

## Completed Plans

- [`2026-04-23-165145-adjacent-static-analysis-cleanup-plan.md`](./2026-04-23-165145-adjacent-static-analysis-cleanup-plan.md)
- [`2025-11-22-testing-scheduling-telemetry-plan.md`](./2025-11-22-testing-scheduling-telemetry-plan.md)
- [`2025-11-16-skipped-tests-remediation.md`](./2025-11-16-skipped-tests-remediation.md)
- [`cli_helpers_extraction.md`](./cli_helpers_extraction.md)
- [`restore-namespace-implementation-plan.md`](./restore-namespace-implementation-plan.md)

## Superseded Plans

- [`2026-04-23-173102-cli-consolidation-stabilization-plan.md`](./2026-04-23-173102-cli-consolidation-stabilization-plan.md) — migrated to
  [`Spec 001`](../specs/001-cli-consolidation-stabilization/requirements.md).
- [`complete-implementation-plan.md`](./complete-implementation-plan.md) — replaced by the live GitHub issue queue and the active plan inventory above.

# References

- Link to additional resources, specs, or tickets
