---
title: Prune historical documentation requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

TimeLocker's visible documentation tree mixes current product guidance with
completed plans, point-in-time reports, local issue snapshots, legacy Kiro
requirements/design references, and unimplemented future designs. Git history
will become the archive while `docs/` presents current durable truth, active
delivery state, and compact lifecycle breadcrumbs.

## Goals

- Remove historical delivery artifacts after preserving recoverability in Git.
- Remove or replace references to legacy `.kiro/specs/` requirements/designs.
- Keep only implemented current-state architecture, guides, reference, testing,
  process, active specs, and compact lifecycle history visibly navigable.
- Close and remove Spec 000 after its final package commit `c84dc3a`.

## Non-Goals

- Runtime code or test behavior changes.
- Implementing proposed REST API, GUI, database, or roadmap features.
- Closing active CLI consolidation Spec 001.

## Glossary

| Term | Definition |
|------|------------|
| Historical artifact | A completed, superseded, point-in-time, or stale delivery record whose recoverability is provided by Git. |
| Durable doc | A reviewed description of accepted current behavior or governance. |
| Compact breadcrumb | A closure/history row containing identity, commit evidence, disposition, and durable destinations without retaining the source package. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/README.md` | Documentation navigation and current product posture | high | Must become current-state only. |
| `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | Documentation classes and lifecycle policy | high | Must change from visible archives to Git-backed history. |
| `docs/specs/README.md` | Active spec lifecycle and closure contract | high | Must retain only active packages. |
| `docs/history/spec-closure-log.md` | Compact spec closure evidence | high | Retained. |
| Git history | Recoverable historical source content | high | Becomes the archive of record. |

## Durable Impact

| Durable area | Action | Target | Notes |
|--------------|--------|--------|-------|
| governance | modify | `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` | Stop retaining completed plans, reports, updates, and archives in the visible tree. |
| planning | modify | `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md` | Keep implementation evidence in specs/commits rather than permanent update files. |
| navigation | modify | `docs/README.md` | Remove historical collections and future-only designs from current navigation. |
| lifecycle | modify | `docs/specs/README.md`, `docs/history/` | Close/remove temporary packages with compact Git breadcrumbs. |
| current-state docs | clarify | architecture, implementation, testing, guides, reference | Remove legacy source links and stale status claims. |

## Staged Readiness

- **Current stage:** implement
- **Next stage:** verify and close
- **Ready to implement when:** approved deletion categories, retained current
  surfaces, rollback path, and validation gates are explicit.
- **Design-first exception:** no
- **Optional artifacts recommended:** `change-impact.md`, `traceability.md`, `verification.md`
- **Downstream review needed:** verification

## Requirements

### Requirement 1: Current-State Documentation Surface

**User Story:** As a contributor, I want `docs/` to contain current guidance and active delivery contracts, so that historical claims are not mistaken for current behavior.

#### Acceptance Criteria

1. GIVEN completed plans, reports, updates, local issue snapshots, and obsolete test artifacts, WHEN cleanup completes, THEN those files SHALL no longer be present in the visible documentation tree.
2. WHERE a document mixes current and future behavior, THE SYSTEM SHALL retain current behavior and remove or route unimplemented proposals out of current-state documentation.
3. WHERE an active spec exists, THE SYSTEM SHALL retain it until lifecycle closure requirements are met.

### Requirement 2: Git-Backed History

**User Story:** As a maintainer, I want Git to preserve removed historical context, so that the visible documentation tree stays lean without losing recoverability.

#### Acceptance Criteria

1. GIVEN a historical document is removed, WHEN historical context is needed, THEN its committed content SHALL remain recoverable through Git history.
2. WHERE lifecycle closure evidence is required, THE SYSTEM SHALL retain compact closure and archive-index breadcrumbs with commit identities.
3. WHEN a completed spec package is removed, THEN its final package commit SHALL be recorded before removal.

### Requirement 3: Legacy Reference Elimination

**User Story:** As a developer or agent, I want current documentation to avoid legacy requirements/design sources, so that implementation decisions use accepted current evidence.

#### Acceptance Criteria

1. WHEN current durable documentation is scanned, THEN it SHALL contain no links to `.kiro/specs/`, deleted plans, deleted reports, deleted updates, or removed local issue/task snapshots.
2. WHERE orphaned requirement IDs or obsolete release/test claims appear, THE SYSTEM SHALL remove or replace them with current code-derived or durable references.
3. WHEN internal links are checked, THEN all retained documentation links SHALL resolve or be explicitly identified as pre-existing out-of-scope defects.

## Correctness Properties

- **CP-001**: Every retained visible historical reference resolves to a compact lifecycle breadcrumb or Git commit, not a retained historical source document.
- **CP-002**: No active Spec 001 artifact or durable current-state behavior is deleted.
- **CP-003**: Deleted documentation remains recoverable from a recorded Git commit.

## Technical Context

- **Language/Version:** Markdown/YAML, Git
- **Primary Dependencies:** Spec Lifecycle Manager, Agent Workbench, repository link checker
- **Target Platform:** Repository documentation tree
- **Constraints:** Apply deletions through reviewable patches; preserve active Spec 001; no runtime code changes.
- **Performance Goals:** Reduce visible documentation count materially and eliminate legacy-reference search hits from retained durable docs.

## Success Criteria

- **SC-001**: All approved historical categories are absent from the final tree.
- **SC-002**: Retained durable docs have zero `.kiro/specs/` and deleted-artifact references.
- **SC-003**: Lifecycle lint, archive consistency, scoped Markdown/link validation, and `git diff --check` pass.

## Related Artifacts

- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
