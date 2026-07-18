---
title: Adopt Spec Lifecycle Manager verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Verification

## Validation Plan

| Gate | Command or review | Pass criterion | Status |
|------|-------------------|----------------|--------|
| Package discovery | Spec Lifecycle Manager `scan_specs` | Specs 000 and 001 discovered; no package errors | passed |
| Package lint | `lint_spec_package` for Specs 000 and 001 | No unwaived errors | passed |
| Readiness | `stage_readiness` and `active_spec_preflight` | Next work and blockers are explicit | passed; Spec 001 selects T005 |
| Evidence | `task_state_audit` for both packages | Completed work has acceptable evidence | passed; informational broad-task advice retained |
| History | `archive_index` | No unwaived structural errors | passed with expected pending-cleanup-commit warning |
| Links | repository-relative Markdown link check | All changed internal links resolve | passed; 25 files checked |
| Formatting | `git diff --check` | No whitespace errors | passed |

## Quality Gates

- Both active packages must lint without unwaived errors.
- Spec 000 must have no incomplete implementation task after validation.
- Spec 001 must resolve to T005 as its next runnable task.
- Changed internal links and Markdown formatting must pass repository checks.
- Any commit-dependent closure warning must be recorded rather than hidden.

## Evidence Log

- 2026-07-18: Repository classified as `documented_no_specs`; no pre-existing
  spec packages or archive history were found.
- 2026-07-18: User explicitly approved the migration plan before edits.
- 2026-07-18: Lifecycle scan discovered two current-format active packages and
  no package errors. Both package linters passed without warnings after the
  verification sections were completed.
- 2026-07-18: Spec 001 readiness selected T005 and reported no blocking gaps.
- 2026-07-18: Archive-index validation reported no errors and one expected
  warning: a cleanup commit cannot be recorded before this migration is committed.
- 2026-07-18: A read-only link check resolved links across 25 changed
  documentation files; `git diff --check` passed.
- 2026-07-18: `prompts_validate` reported `PROMPTS_DIR_MISSING` at the
  repository-local fallback path. This repository intentionally uses the
  externally installed MCP plugin and does not vendor its prompt assets, so the
  repository-local prompt check is not applicable to this conversion.

## Durable Promotion And Cleanup

| Spec content | Durable destination or deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| Lifecycle authority | `docs/specs/README.md`, `AGENTS.md` | complete | Updated in T002/T004 |
| Planning and documentation rules | `docs/guides/ai-agent/` | complete | Updated in T004 |
| Legacy plan migration | `docs/plans/README.md`, Spec 001 | complete | Updated in T003 |
| Closure rules | `docs/history/` | complete | Updated in T004 |
| Implementation record | `docs/updates/` | complete | Updated in T004 |

### Spec Cleanup Decision

- **Cleanup action:** keep active
- **Reason:** The final spec state must be committed before closure or removal.
- **Final spec commit:** pending
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** no
- **Closure cleanup commit:** pending
- **Active indexes updated:** no
- **Durable docs linked back to evidence where useful:** yes
- **Residual spec-only content:** final validation evidence and commit identity

## Ship Or Closure Risk

- **Risk level:** low
- **Breaking change:** no
- **Blast radius checked:** yes
- **Rollback path:** revert the documentation change
- **Requires human review:** no
- **Release notes needed:** no
- **Follow-up issue or spec needed:** no

### Risk Rationale

The change affects governance and documentation only. The principal residual
risk is ambiguity if Spec 000 is left active after its final state is committed.

## Residual Risks

- The archive index cleanup commit remains pending until this migration is committed.
- Spec 000 remains active until its final state can be referenced by a commit.
- Repository-local prompt validation is unavailable because the lifecycle
  plugin and its prompts are externally installed; package MCP operations work.

## Readiness Decision

- **Ready for promotion:** yes
- **Ready for release:** not applicable
- **Ready for closure:** no — validation and a final spec commit are pending
