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

**When to use this template**: This folder contains documents that outline a set of intended actions, usually with a specific goal and timeline. Plans are more
concrete than proposals and are created after a proposal has been accepted.
**Location**: `docs/plans/`

## 2. What Belongs Here?

- Project plans, sprint plans, release plans.
- Detailed action plans for specific initiatives.
- Roadmaps (if not in `0-project-management`).

## 3. What Does NOT Belong Here?

- Initial ideas or suggestions (see `../proposals/`).
- Architectural decisions (see `../2-architecture/`).
- Daily updates or change logs (see `../updates/`).

## 4. Usage Notes

- **Checklist for Authors**:
    - [ ] Fill in all placeholder values (e.g., `[Name or Team]`).
    - [ ] Delete this `Usage Notes` section before publishing.
    - [ ] Ensure the document is linked from the relevant `README.md` file.

- **Naming Convention**: N/A for this file.

### Plan Lifecycle

Plans use one of these states:

- `draft`: being written; not approved for execution
- `reviewing`: awaiting a decision
- `accepted`: approved but execution has not started
- `active`: execution is in progress and task statuses must be maintained
- `completed`: success criteria were met and linked evidence was reviewed
- `superseded`: replaced by a newer plan, issue queue, or implementation direction
- `rejected`: reviewed and intentionally not pursued

Moving a plan to `completed` requires a linked update or equivalent validation evidence. Superseded and completed plans remain in place when other documents
link to them; they are historical context, not active work. Review `active` plans monthly and before release.

## 5. Available Templates

- `_template.md`: A generic template for any plan.
- `_template.test-coverage-plan.md`: A specific template for creating a plan to improve test coverage.

## Active Plans

- [`2026-04-23-173102-cli-consolidation-stabilization-plan.md`](./2026-04-23-173102-cli-consolidation-stabilization-plan.md) — active phased cleanup for repository resolution, service-manager fan-out, monitoring seams, and documentation tracing.

## Completed Plans

- [`2026-04-23-165145-adjacent-static-analysis-cleanup-plan.md`](./2026-04-23-165145-adjacent-static-analysis-cleanup-plan.md)
- [`2025-11-22-testing-scheduling-telemetry-plan.md`](./2025-11-22-testing-scheduling-telemetry-plan.md)
- [`2025-11-16-skipped-tests-remediation.md`](./2025-11-16-skipped-tests-remediation.md)
- [`cli_helpers_extraction.md`](./cli_helpers_extraction.md)
- [`restore-namespace-implementation-plan.md`](./restore-namespace-implementation-plan.md)

## Superseded Plans

- [`complete-implementation-plan.md`](./complete-implementation-plan.md) — replaced by the live GitHub issue queue and the active plan inventory above.

# References

- Link to additional resources, specs, or tickets
