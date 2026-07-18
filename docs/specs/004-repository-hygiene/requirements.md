---
title: Repository hygiene requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

TimeLocker's durable documentation contains conflicting agent instructions,
stale front-door links, duplicated templates, and historical working material.
This package defines the bounded governance cleanup that must finish before
implementation resumes in Spec 001.

## Goals

- Establish one coherent source of agent instructions.
- Make the repository front door and documentation paths describe the current
  tree and configuration.
- Retain only current, durable documentation and a small reusable template set.
- Preserve deterministic lifecycle sequencing for the active CLI spec.

## Non-Goals

- Implementing Spec 001 tasks T005-T010.
- Changing TimeLocker runtime behavior or public CLI behavior.
- Replacing the externally installed Spec Lifecycle Manager or copying its
  package templates into this repository.
- Rewriting historical Git evidence.

## Glossary

| Term | Definition |
|------|------------|
| Durable documentation | Current source-of-truth material retained after a delivery spec closes. |
| Working-history document | A plan, update diary, investigation log, or superseded design whose history belongs in Git. |
| Front door | Root files and indexes used to orient contributors and agents. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `AGENTS.md` | Routes agents to centralized repository rules. | high | Contains one conflicting updates-directory instruction. |
| `docs/guides/ai-agent/` | Declared single source of truth for agent behavior. | high | Several rules contain copied guidance from unrelated projects. |
| `README.md` | Project overview, setup, structure, and contributor entry points. | high | Several paths and the coverage badge are stale. |
| `docs/specs/README.md` | Active spec lifecycle and authority boundaries. | high | Spec 004 must be sequenced ahead of Spec 001 implementation. |
| `docs/DOCUMENTATION-STATUS.md` | Durable-document inventory and legacy-removal policy. | high | Cleanup must remain consistent with this policy. |

## Durable Impact

Detailed mappings are recorded in `change-impact.md`.

## Staged Readiness

- **Current stage:** implementation
- **Next stage:** verification and promotion
- **Ready to implement when:** requirements, design, task dependencies,
  traceability, and the approved relationship to Spec 001 are coherent.
- **Design-first exception:** no
- **Optional artifacts recommended:** `change-impact.md`, `verification.md`,
  `traceability.md`
- **Downstream review needed:** none

## Requirements

### Requirement 1: Single Agent-Instruction Authority

**User Story:** As a repository contributor, I want one current set of agent
instructions, so that automation does not follow contradictory workflows.

#### Acceptance Criteria

1. GIVEN repository agent instructions, WHEN an agent resolves authority, THEN
   `docs/guides/ai-agent/` SHALL be the sole detailed rule source and
   `AGENTS.md` SHALL remain a minimal pointer without a forbidden updates path.
2. GIVEN `.kiro/steering/` and centralized rules, WHEN cleanup completes, THEN
   duplicate steering files SHALL be absent and `.kiro/settings/mcp.json` SHALL
   remain available.
3. GIVEN centralized rules, WHEN they are reviewed, THEN copied references to
   admin-assistant, Microsoft 365, TypeScript/Vitest, Flask/SQLAlchemy, and the
   nonexistent logging guide SHALL be replaced with TimeLocker-specific policy.

### Requirement 2: Accurate Front Door And Resource Paths

**User Story:** As a new contributor, I want the README, changelog, and resource
paths to match the repository, so that setup and discovery do not lead to
missing files.

#### Acceptance Criteria

1. GIVEN `README.md` and `CHANGELOG.md`, WHEN their local links and repository
   descriptions are checked, THEN they SHALL not direct readers to removed
   plans, updates, archives, requirements files, or nonexistent documentation
   trees.
2. GIVEN the configured coverage threshold, WHEN the README badge is read, THEN
   it SHALL show the 50 percent threshold enforced by `pyproject.toml`.
3. GIVEN documentation assets and their consumers, WHEN paths are resolved,
   THEN assets SHALL live under `docs/resources/`, the README image SHALL load,
   and conversion scripts SHALL use the canonical JSON location.

### Requirement 3: Lean Durable Documentation

**User Story:** As a maintainer, I want only current durable documentation in
`docs/`, so that legacy plans and redundant templates do not pollute discovery.

#### Acceptance Criteria

1. GIVEN the pickle investigation, WHEN current code and tests establish its
   outcome, THEN the obsolete investigation plan SHALL be removed rather than
   presented as a troubleshooting guide.
2. GIVEN scattered durable-document templates, WHEN cleanup completes, THEN a
   compact central set SHALL live under `docs/templates/` and redundant
   per-section templates SHALL be removed or redirected.
3. GIVEN empty legacy directories, WHEN cleanup completes, THEN local plans,
   updates, archive, reports, issues, traceability, and obsolete project-
   management directories SHALL not remain discoverable.

### Requirement 4: Explicit Spec Sequencing And Closure

**User Story:** As a lifecycle operator, I want governance cleanup explicitly
sequenced with Spec 001, so that two packages do not create competing product
implementation work.

#### Acceptance Criteria

1. GIVEN Specs 001 and 004 are both active, WHEN work is selected, THEN Spec 004
   SHALL be the only implementation package and Spec 001 T005 SHALL name Spec
   004 as its prerequisite.
2. GIVEN cleanup validation succeeds, WHEN Spec 004 closes, THEN durable
   guidance SHALL contain the accepted state, lifecycle history SHALL record
   closure, and Spec 001 SHALL remain ready to resume.

## Correctness Properties

- **CP-001:** No tracked current document references a forbidden legacy docs
  directory as an active workflow or destination.
- **CP-002:** Every tracked documentation resource consumer resolves to an
  existing canonical path.
- **CP-003:** At most one active package is eligible for implementation during
  this cleanup; Spec 001 becomes eligible only after Spec 004 closes.

## Technical Context

- **Language/Version:** Markdown and Python 3.12+
- **Primary Dependencies:** Git, repository documentation scripts, Spec
  Lifecycle Manager, Agent Workbench
- **Target Platform:** TimeLocker repository checkout
- **Constraints:** docs/governance-only except resource-consumer path fixes
- **Performance Goals:** not applicable

## Success Criteria

- **SC-001:** Lifecycle lint, readiness, evidence, and closure checks report no
  blocking findings for Spec 004.
- **SC-002:** Repository link, Markdown, path-reference, and diff checks pass.
- **SC-003:** Relevant focused tests and the full test suite pass, or any
  pre-existing limitation is recorded with exact evidence.

## Related Artifacts

- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
