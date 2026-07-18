---
title: Project charter requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

TimeLocker has current product, documentation, and delivery guidance, but no
single enduring authority for its mandate, boundaries, decision rights, or
success measures. This package creates that authority without changing runtime
behavior or the delivery scope of active Spec 001.

## Goals

- Establish `CHARTER.md` as the durable project-governance authority.
- Define TimeLocker's purpose, audiences, principles, scope, and exclusions.
- Define role-based ownership, decision rights, success measures, and change
  governance without inventing an individual owner.
- Route repository front doors and Spec 001 to the charter without duplicating
  its content.

## Non-Goals

- Runtime, packaging, CLI, test, release, or architecture changes.
- A roadmap, delivery plan, funding commitment, or release-date promise.
- Approval of a REST API, database application, desktop GUI, or mobile client.
- Replacing GitHub issue ownership or Spec 001 delivery governance.

## Glossary

| Term | Definition |
|------|------------|
| Charter | Durable authority for project purpose, boundaries, governance, and success. |
| Durable documentation | Current accepted guidance that remains after temporary specs close. |
| Delivery spec | Temporary package governing an approved implementation slice. |
| Project steward | Role accountable for charter interpretation and governance decisions. |

## Durable Source Baseline

- `README.md` describes the current CLI-first Restic product and audiences.
- `docs/README.md` defines current product state and documentation authority.
- `docs/DOCUMENTATION-STATUS.md` records implemented and excluded product
  surfaces.
- Spec 001 governs the remaining CLI consolidation slice and stays subordinate
  to durable project governance.

## Requirements

### Requirement 1: Establish the enduring mandate

**User Story:** As a contributor, I want one durable statement of TimeLocker's
purpose and users, so that changes reinforce a coherent project direction.

#### Acceptance Criteria

1. GIVEN the current product state, WHEN the charter is read, THEN it SHALL
   describe TimeLocker as a CLI-first, Restic-backed backup and recovery
   project.
2. WHERE project value and audiences are described, THE CHARTER SHALL identify
   the operational problems TimeLocker solves without promising future-only
   surfaces.

### Requirement 2: Make project boundaries explicit

**User Story:** As a maintainer, I want clear inclusion and exclusion rules, so
that attractive but unrelated work does not silently expand project scope.

#### Acceptance Criteria

1. GIVEN a proposed change, WHEN it is compared with the charter, THEN the
   charter SHALL provide explicit in-scope and out-of-scope criteria.
2. IF a REST API, database application, desktop GUI, mobile client, or Restic
   replacement is proposed, THEN the charter SHALL classify it as outside the
   current mandate unless separately approved through governance.

### Requirement 3: Define governance and success

**User Story:** As a project steward, I want role-based decision rights and
measurable success signals, so that project choices are accountable and
reviewable.

#### Acceptance Criteria

1. WHERE ownership is described, THE CHARTER SHALL use the Auriora Team and
   project-steward roles without inventing an individual owner.
2. GIVEN a material charter, public-contract, scope, security, or compatibility
   change, WHEN it is proposed, THEN the charter SHALL require explicit review
   and an appropriate delivery record.
3. WHEN project health is assessed, THEN the charter SHALL provide measurable
   product, safety, quality, usability, and maintainability signals.

### Requirement 4: Establish authority and reader paths

**User Story:** As a human or AI contributor, I want repository entry points to
route me to the charter, so that I find the enduring rules before delivery
details.

#### Acceptance Criteria

1. GIVEN a reader starting from `README.md`, `docs/README.md`, or `AGENTS.md`,
   WHEN project direction is needed, THEN that document SHALL link to
   `CHARTER.md` rather than duplicate it.
2. WHILE Spec 001 remains active, THE SYSTEM SHALL state that the charter owns
   enduring project governance and Spec 001 owns only its approved delivery
   slice.

## Correctness Properties

- **CP-001:** Charter current-state claims do not contradict `README.md`,
  `docs/README.md`, or `docs/DOCUMENTATION-STATUS.md`.
- **CP-002:** Project mandate, exclusions, and governance have one authoritative
  durable home, with other documents linking to it.
- **CP-003:** Spec 001 remains lifecycle-ready at T005 and receives no runtime or
  task-scope changes.

## Technical Context

- **Change class:** documentation and governance only
- **Durable target:** root `CHARTER.md`
- **Related front doors:** `README.md`, `docs/README.md`, `AGENTS.md`
- **Active delivery package:** `docs/specs/001-cli-consolidation-stabilization/`
- **Template authority:** Spec Lifecycle Manager fallback for this temporary
  package; repository durable-document conventions for the charter

## Success Criteria

- **SC-001:** Charter review confirms coverage of mandate, boundaries,
  governance, success measures, and next steps.
- **SC-002:** Markdown and internal-link validation report no blocking findings.
- **SC-003:** Lifecycle checks report no Spec 005 closure blockers and Spec 001
  remains ready at T005.
- **SC-004:** After closure, `CHARTER.md` remains durable and Spec 005 is
  recoverable from Git only.

## Related Artifacts

- Design: `design.md`
- Tasks: `tasks.md`
- Change Impact: `change-impact.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
