---
title: Repository review skill requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

TimeLocker needs a reusable, repository-aware review workflow that examines code
and durable documentation through complementary expert roles. Existing generic
PR automation does not encode the charter, Restic boundary, lifecycle rules, or
the evidence and finding contract needed for whole-repository reviews.

## Goals

- Add a repository-local Codex skill for code and documentation review.
- Define a balanced TimeLocker expert panel with non-overlapping review duties.
- Require evidence-backed, deduplicated, actionable findings.
- Preserve repository authority, documentation lifecycle, and Spec 001 state.

## Non-Goals

- Reviewing or changing the TimeLocker runtime in this delivery slice.
- Replacing CI, GitHub review automation, maintainers, or security testing.
- Automatically writing review reports into durable documentation.
- Authorizing subagents, external services, or repository mutations during a review.

## Durable Source Baseline

- `CHARTER.md` owns mandate, boundaries, governance, and success measures.
- `AGENTS.md` and `docs/guides/ai-agent/` own agent behavior and workflows.
- `docs/1-requirements/`, `docs/2-architecture/`, `docs/3-implementation/`,
  and `docs/4-testing/` own accepted current-state guidance.
- `docs/specs/001-cli-consolidation-stabilization/` remains the sole runtime
  delivery package and stays ready at T005.

## Requirements

### Requirement 1: Provide a project-specific review panel

**User Story:** As a maintainer, I want complementary experts to review the
repository, so that important product, recovery, design, security, reliability,
operations, and documentation risks are not missed.

#### Acceptance Criteria

1. GIVEN a TimeLocker repository review, WHEN the skill runs, THEN it SHALL
   apply the approved seven expert roles and their explicit evidence focus.
2. WHERE role observations overlap, THE SKILL SHALL synthesize them into one
   finding without losing role attribution.

### Requirement 2: Produce trustworthy findings

**User Story:** As a contributor, I want findings tied to repository evidence,
so that I can reproduce, prioritize, and address them.

#### Acceptance Criteria

1. GIVEN a reported problem, WHEN it is emitted, THEN it SHALL include a stable
   ID, severity, confidence, evidence, consequence, remedy, and routing.
2. IF evidence is incomplete or a check was not executed, THEN the skill SHALL
   label the item as a risk or unverified concern rather than a confirmed defect.
3. WHERE no actionable finding exists, THE SKILL SHALL say so and report the
   review scope and validation limitations.

### Requirement 3: Respect repository authority and safety

**User Story:** As a project steward, I want reviews to respect TimeLocker's
governance and lifecycle, so that review activity does not create competing
requirements, historical clutter, or unauthorized changes.

#### Acceptance Criteria

1. GIVEN any review scope, WHEN evidence is gathered, THEN the skill SHALL use
   the charter, agent rules, durable docs, active specs, code, tests, config,
   and Git state according to their documented authority.
2. WHILE a request is review-only, THE SKILL SHALL remain read-only and SHALL
   not create durable reports, modify files, or change lifecycle task state.
3. IF remediation is requested, THEN the skill SHALL route implementation
   through repository planning, lifecycle, approval, and validation rules.

### Requirement 4: Package and validate a discoverable skill

**User Story:** As an AI developer, I want a repository-local skill with clear
trigger metadata, so that TimeLocker review requests use the same workflow.

#### Acceptance Criteria

1. GIVEN a request to review TimeLocker code, documentation, architecture,
   security, tests, or overall repository quality, WHEN skills are selected,
   THEN `review-timelocker` SHALL be discoverable as the applicable skill.
2. WHEN the skill package is validated, THEN its metadata, references, links,
   and sample review contract SHALL pass the selected checks.

## Correctness Properties

- **CP-001:** Every confirmed finding has reproducible repository evidence.
- **CP-002:** One underlying issue maps to one synthesized finding ID.
- **CP-003:** Review-only execution makes no repository or lifecycle mutation.
- **CP-004:** Spec 001 remains unchanged and ready at T005.

## Technical Context

- **Change class:** repository-local skill packaging and governance
- **Durable target:** `.agents/skills/review-timelocker/`
- **Skill resources:** `SKILL.md`, `agents/openai.yaml`, focused references
- **Concurrent package:** Spec 001, protected from edits
- **Template authority:** Skill Creator generator and Spec Lifecycle Manager fallback

## Success Criteria

- **SC-001:** Skill validation exits successfully.
- **SC-002:** A bounded read-only exercise produces the required review structure.
- **SC-003:** Markdown, link, and Git checks pass for changed files.
- **SC-004:** Spec 006 closes without changing Spec 001 task state or runtime files.

## Related Artifacts

- Design: `design.md`
- Tasks: `tasks.md`
- Change Impact: `change-impact.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
