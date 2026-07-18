---
title: Adopt Spec Lifecycle Manager requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

TimeLocker's planning guidance currently treats standalone files in
`docs/plans/` as active execution contracts. The project needs a staged,
evidence-bearing lifecycle that distinguishes temporary implementation intent
from durable current-state documentation.

## Goals

- Establish `docs/specs/` as the home for active implementation packages.
- Preserve GitHub issues as the assignment tracker and `docs/updates/` as the
  implementation diary.
- Migrate the only active legacy plan without rewriting completed history.
- Provide durable promotion, closure-log, and archive-index rules.

## Non-Goals

- Vendoring or configuring the external lifecycle plugin in the repository.
- Migrating completed or superseded plans into active spec packages.
- Creating duplicate project summaries, backlogs, or roadmaps.
- Changing TimeLocker runtime behavior.

## Glossary

| Term | Definition |
|------|------------|
| Active spec | Temporary package that governs an approved implementation change. |
| Durable doc | Current-state documentation that remains authoritative after spec closure. |
| Promotion | Moving accepted content from a completed spec into durable documentation. |
| Closure | Recording final evidence and removing or archiving a completed active package. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `AGENTS.md` | Agents load centralized repository rules and write task updates. | high | Entry point remains intentionally compact. |
| `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md` | Complex work requires a plan and explicit approval. | high | Extended to use lifecycle packages. |
| `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | Documentation location and freshness rules are centralized. | high | Extended with specs and history. |
| `docs/plans/README.md` | Standalone plans currently carry active work. | high | Becomes a legacy-plan index. |
| `docs/0-project-management/tasks-to-issues-map.md` | GitHub issue state is authoritative. | high | Authority boundary is retained. |

## Durable Impact

| Durable area | Action | Target | Notes |
|--------------|--------|--------|-------|
| governance | modify | `AGENTS.md` | Add the active-spec entry point. |
| planning | supersede | `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md` | Replace standalone plan execution with spec triage and staged artifacts. |
| documentation | modify | `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | Recognize specs and lifecycle history. |
| history | add | `docs/history/spec-closure-log.md` | Record closed package evidence. |
| history | add | `docs/history/spec-archive-index.md` | Index removed, archived, or retained packages. |

## Staged Readiness

- **Current stage:** verification
- **Next stage:** final-spec commit and closure cleanup
- **Ready to design when:** satisfied by the approved migration plan.
- **Design-first exception:** no
- **Optional artifacts recommended:** `change-impact.md`, `verification.md`, `traceability.md`
- **Downstream review needed:** closure after remediation validation

## Requirements

### Requirement 1: Establish the lifecycle authority

**User Story:** As a contributor, I want one documented delivery lifecycle, so
that active intent, durable truth, issue tracking, and implementation history do
not conflict.

#### Acceptance Criteria

1. GIVEN a complex or governance-sensitive change, WHEN work is triaged, THEN
   the repository SHALL direct it to an active package under `docs/specs/`.
2. WHERE a spec is active, THE SYSTEM SHALL treat it as the implementation
   contract while retaining durable docs as the current-state authority.
3. WHERE GitHub issues or update logs are used, THE SYSTEM SHALL preserve their
   assignment-tracking and chronological-history roles.

### Requirement 2: Migrate only live work

**User Story:** As a maintainer, I want current work migrated without rewriting
history, so that evidence remains trustworthy.

#### Acceptance Criteria

1. GIVEN the legacy plan inventory, WHEN migration runs, THEN only the active
   CLI consolidation plan SHALL become a new active spec package.
2. WHILE completed and superseded plans remain referenced, THE SYSTEM SHALL
   retain them as historical documents.
3. IF completed tasks are carried into the new package, THEN their completion
   SHALL include existing evidence references.

### Requirement 3: Make closure auditable

**User Story:** As a future agent, I want promotion and closure evidence, so
that temporary specs do not become permanent competing documentation.

#### Acceptance Criteria

1. BEFORE a spec closes, THE SYSTEM SHALL require validation evidence and
   durable promotion or an explicit deferral.
2. WHEN a package is removed, archived, or retained as history, THEN the
   closure log and archive index SHALL identify the final spec commit.

## Correctness Properties

- **CP-001**: At most one active delivery contract exists for the same scope.
- **CP-002**: No active spec may close while accepted behavior exists only in
  the spec package.
- **CP-003**: Historical completed work is never represented as pending work.

## Technical Context

- **Language/Version:** Markdown and repository governance files
- **Primary Dependencies:** Spec Lifecycle Manager MCP surface
- **Target Platform:** Repository contributors and coding agents
- **Constraints:** Documentation-only migration; preserve existing Git history
- **Performance Goals:** Package discovery and next-task selection remain bounded

## Success Criteria

- **SC-001**: Lifecycle discovery reports both active packages with no package-lint errors.
- **SC-002**: The legacy plans index reports no active standalone plans.
- **SC-003**: Planning, documentation, issue, update, and closure roles are cross-linked without duplicate authority.

## Related Artifacts

- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
