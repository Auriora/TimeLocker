---
title: Repository review skill tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Tasks

**Input:** `docs/specs/006-repository-review-skill/`
**Approval:** User approved the expert panel, repository-local skill scope, and
temporary Spec 006 workflow on 2026-07-18.

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004
```

## Phase 1: Lifecycle Baseline

- [x] T001 Establish and validate the bounded Spec 006 package.
  - Depends on: none
  - Requirements: Requirement 1-4, CP-004
  - Files: `docs/specs/006-repository-review-skill/`, `docs/specs/README.md`
  - Acceptance: Package artifacts are coherent, concurrency is explicit, and
    Spec 001 remains unchanged and ready at T005.
  - Evidence mode: validation
  - Evidence: `lint_spec_package` returned error=0, warn=0, info=0;
    `stage_readiness` returned ready-to-implement with every reported gap count
    at 0; `active_spec_preflight` kept Spec 001 ready at T005.

## Phase 2: Skill Implementation

- [x] T002 Initialize and implement the repository-local review skill.
  - Depends on: T001
  - Requirements: Requirement 1-4, CP-001-CP-003
  - Files: `.agents/skills/review-timelocker/`
  - Acceptance: The skill defines the approved panel, authority preflight,
    evidence workflow, read-only boundary, finding contract, and discovery metadata.
  - Evidence mode: implementation
  - Evidence: Skill Creator initialized the durable skill package with
    `SKILL.md`, `agents/openai.yaml`, and two focused references; implementation defines
    seven expert roles, authority and evidence workflow, read-only/remediation
    boundary, stable `TLR-###` finding schema, synthesis, routing, and discovery metadata.

## Phase 3: Validation And Closure

- [x] T003 Validate and exercise the skill.
  - Depends on: T002
  - Requirements: Requirement 2, Requirement 4, CP-001-CP-004, SC-001-SC-003
  - Files: skill package and bounded TimeLocker review inputs
  - Acceptance: Structural checks pass and a read-only exercise demonstrates
    the required scope receipt, role coverage, evidence discipline, and output schema.
  - Evidence mode: validation
  - Evidence: Skill Creator `quick_validate.py` exited 0; metadata, reference,
    role-count, finding-field, clean-result, and placeholder assertions passed; a
    bounded read-only contract exercise produced a scope receipt, applied five
    relevant roles, recorded two out-of-scope lenses, emitted no actionable
    findings, and preserved the Git status fingerprint.

- [x] T004 Promote routing, finalize evidence, and close Spec 006.
  - Depends on: T003
  - Requirements: Requirement 3, Requirement 4, CP-004, SC-004
  - Files: `AGENTS.md`, lifecycle index and history, Spec 006
  - Acceptance: Durable skill routing is discoverable, Spec 001 remains ready,
    final package state is committed, and Spec 006 is removed with closure evidence.
  - Evidence mode: validation
  - Evidence: Commit `0e10ec0` preserves the durable skill, agent routing, all
    six package artifacts, and validation evidence; lifecycle checks pass,
    removal metadata is prepared, and Spec 001 remains ready at T005.
  - [x] T004.1 Run final Markdown, link, Git, skill, and lifecycle checks.
    - Evidence mode: validation
    - Evidence: `quick_validate.py`, metadata/reference assertions,
      `python scripts/link_checker.py`, `git diff --check`, Spec 006
      `lint_spec_package`, and Spec 001 `active_spec_preflight` passed; the
      visible-document Markdown check had no structure or link errors.
  - [x] T004.2 Commit the complete final active package state.
    - Evidence mode: implementation
    - Evidence: Commit `0e10ec0` contains the durable skill, routing, active
      package, and the completed T001-T003 evidence before cleanup.
  - [x] T004.3 Remove the package and record lifecycle history.
    - Evidence mode: implementation
    - Evidence: `promotion_plan` returned `missing_targets=[]`; change impact
      and verification map removal to `docs/history/spec-closure-log.md` and
      `docs/history/spec-archive-index.md`; `archive_index` had 0 diagnostics.

## Execution Rules

- Do not edit runtime code, tests, configuration, or Spec 001 artifacts.
- Do not run subagents or external review services in this slice.
- Use the Skill Creator generator before customizing the new skill.
- Keep review output outside durable docs unless separately approved for promotion.
- Remove Spec 006 after final-state commit and durable closure recording.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Change Impact: `change-impact.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
