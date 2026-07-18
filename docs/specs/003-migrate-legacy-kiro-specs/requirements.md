---
title: Migrate legacy Kiro specifications
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

TimeLocker retains fifteen legacy specification packages under `.kiro/specs/`.
They mix completed delivery history, deferred proposals, stale test-remediation
work, and potentially unfinished security work. This migration must eliminate
the legacy specification surface without turning `docs/specs/` into a visible
archive.

## Goals

- Reconcile every legacy package against current code, tests, and durable docs.
- Preserve only verified active work as numbered lifecycle-manager packages.
- Promote accepted current behavior and route deferred work before removing the
  legacy source tree.
- Preserve recovery and closure evidence through Git and compact history rows.

## Non-Goals

- Implement feature behavior described by the legacy packages.
- Treat unchecked legacy boxes as proof that work remains.
- Restore completed or deferred packages as active visible specifications.
- Change runtime code, tests, or external issue state during migration.

## Glossary

| Term | Definition |
|------|------------|
| Legacy package | A requirements/design/tasks package under `.kiro/specs/`. |
| Active migration | A new numbered package for current, verified, approved unfinished work. |
| Closed source | A completed, superseded, stale, or deferred package preserved in Git rather than the visible docs tree. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | `docs/specs/` contains temporary active delivery packages; Git is the archive. | high | Governing policy. |
| `docs/specs/README.md` | Package contract, authority boundaries, and closure flow. | high | Spec 001 is currently active. |
| `docs/history/spec-archive-index.md` | Compact discovery for removed and superseded delivery contracts. | high | Must remain consistent with closure log. |
| `.kiro/specs/` | Legacy migration input only. | low | Task markers are not trusted without current evidence. |

## Durable Impact

See `change-impact.md`. The migration updates the active-spec index and compact
history, may clarify current durable documents, and removes `.kiro/specs/` after
its tracked state is preserved in Git.

## Staged Readiness

- **Current stage:** implement
- **Next stage:** verify
- **Ready to design when:** satisfied by the approved migration classification.
- **Design-first exception:** no
- **Optional artifacts recommended:** `change-impact.md`, `verification.md`, `traceability.md`
- **Downstream review needed:** verification

## Requirements

### Requirement 1: Reconcile Every Legacy Package

**User Story:** As a maintainer, I want every legacy package classified from
current evidence, so that stale task state is not copied into the new lifecycle.

#### Acceptance Criteria

1. GIVEN the fifteen legacy packages, WHEN migration is prepared, THEN each SHALL be classified as already migrated, completed, near-complete, active candidate, stale remediation, or deferred proposal.
2. WHERE a legacy task is unchecked, THE SYSTEM SHALL verify current code, tests, or durable documentation before treating it as unfinished.
3. IF current evidence cannot establish a safe disposition, THEN THE SYSTEM SHALL keep the item explicitly unresolved rather than inventing completion.

### Requirement 2: Keep Active Specifications Lean

**User Story:** As a contributor, I want only current approved work under
`docs/specs/`, so that agents do not mistake delivery history for active scope.

#### Acceptance Criteria

1. GIVEN a completed, superseded, stale, or deferred package, WHEN migration completes, THEN it SHALL NOT remain as an active numbered package.
2. WHERE verified unfinished work remains, THE SYSTEM SHALL create the smallest coherent numbered lifecycle package with requirements, design, tasks, evidence expectations, and durable impact.
3. WHEN the migration closes, THEN Spec 001 and any newly verified active package SHALL be the only feature packages listed in `docs/specs/README.md`.

### Requirement 3: Preserve Durable Evidence and Remove Legacy Authority

**User Story:** As a maintainer, I want the legacy tree removed without losing
recovery evidence, so that the repository has one specification lifecycle.

#### Acceptance Criteria

1. GIVEN tracked legacy files, WHEN they are removed, THEN their recovery commits and disposition SHALL be recorded in Git and compact lifecycle history.
2. WHEN current docs are scanned after migration, THEN they SHALL contain no authoritative links to `.kiro/specs/`.
3. WHEN lifecycle and link validation run, THEN the active packages, history records, and retained links SHALL be internally consistent.

## Correctness Properties

- **CP-001**: Every legacy package has exactly one primary disposition.
- **CP-002**: No completed or deferred legacy package becomes active merely because it contains requirements text.
- **CP-003**: Every active migrated package has current evidence for its unfinished scope.
- **CP-004**: Removing `.kiro/specs/` does not remove the only durable description of implemented current behavior.

## Technical Context

- **Language/Version:** Markdown lifecycle packages; Python repository evidence
- **Primary Dependencies:** Spec Lifecycle Manager, Agent Workbench, Git
- **Target Platform:** Repository documentation tree
- **Constraints:** docs-only migration; GitHub issue mutation and runtime implementation are out of scope
- **Performance Goals:** not applicable

## Success Criteria

- **SC-001**: Fifteen packages have evidence-backed dispositions.
- **SC-002**: Lifecycle scan reports only healthy active numbered packages.
- **SC-003**: No retained Markdown link targets `.kiro/specs/`.
- **SC-004**: Link, lifecycle, archive, and formatting checks pass.

## Related Artifacts

- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
