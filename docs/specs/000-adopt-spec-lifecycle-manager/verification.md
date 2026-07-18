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
| Task state | `task_state_audit` for both packages | Task markers and dependency state are coherent | passed; T006 complete with evidence |
| Evidence quality | `evidence_quality_check` for Spec 000 | Completed tasks cite concrete proof signals | passed; `error=0`, `warn=0` |
| History | `archive_index` | No unwaived structural errors | passed; `error=0`, `warn=0` |
| Links | repository-relative Markdown link check | All changed internal links resolve | passed; Agent Workbench found 0 broken links in 9 changed files |
| Formatting | `git diff --check` | No whitespace errors | passed |
| Markdown quality | Agent Workbench `check_markdown_set` | Structural findings pass; readability findings resolved or justified | passed with 53 machine-readable table-readability advisories explicitly waived |

## Quality Gates

- Both active packages must lint without unwaived errors.
- Spec 000 must have no incomplete implementation task after validation.
- Spec 001 must resolve to T005 as its next runnable task.
- Changed internal links and Markdown formatting must pass repository checks.
- Any commit-dependent closure warning must be recorded rather than hidden.

## Evidence Log

- 2026-07-18: `scan_specs` classified the repository as `documented_no_specs`;
  it found `0` pre-existing spec packages and `0` archive-history entries.
- 2026-07-18: T001 evidence in `tasks.md` records user approval before edits.
- 2026-07-18: `scan_specs` discovered `2` current-format active packages with
  `active_error=0`; both `lint_spec_package` runs returned `error=0` after the
  verification sections were completed.
- 2026-07-18: `active_spec_preflight` selected Spec 001 `T005` with `blocking=0`.
- 2026-07-18: `archive_index` returned `error=0`, `warn=1`, with expected code
  `ARCHIVE_INDEX_CLEANUP_COMMIT_PENDING` before commit `ce23d07` existed.
- 2026-07-18: The scoped link checker resolved `25/25` changed documentation
  files, and `git diff --check` returned exit code `0`.
- 2026-07-18: `prompts_validate` reported `PROMPTS_DIR_MISSING` at the
  repository-local fallback path. This repository intentionally uses the
  externally installed MCP plugin and does not vendor its prompt assets, so the
  repository-local prompt check is not applicable to this conversion.
- 2026-07-18: Commit `ce23d07` records the adoption implementation, including
  the superseded retained state of the legacy CLI plan and the complete initial
  Spec 000 package.
- 2026-07-18: Review task `T006` recorded `5` findings: incorrect legacy
  commit history, stale post-commit lifecycle wording, weak evidence, implicit
  acceptance/success-criterion mapping, and missing durable tooling fallback.
- 2026-07-18: `evidence_quality_check` reported `error=0`, `warn=11`: ten
  `EVIDENCE_WEAK` findings and one `EVIDENCE_VAGUE` finding. T006 replaces the
  affected task evidence with commit, command, path, and result signals.
- 2026-07-18: Agent Workbench `check_markdown_set` examined six Spec 000
  artifacts and reported 48 `markdown.table.readability` advisories. The wide
  rows are retained where the lifecycle parser requires single-row matrices;
  this is an explicit readability waiver, not structural or link validation.
- 2026-07-18: T006 final validation returned `lint error=0 warn=0`, evidence
  `error=0 warn=0`, archive `error=0 warn=0`, and `0` readiness or context gaps;
  Agent Workbench checked `9` changed documents with `0` broken links and `53`
  explicitly waived `markdown.table.readability` advisories.
- 2026-07-18: `closure_check` returned `ready=true` with `0` blockers; closure
  execution remains deferred until the remediation has a final-spec commit ID.

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
- **Reason:** Commit `ce23d07` records the adoption baseline, but the T006 review
  remediation changes the final package and must be validated and committed
  before closure or removal.
- **Adoption implementation commit:** `ce23d07`
- **Final spec commit:** pending
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** no
- **Closure cleanup commit:** pending
- **Active indexes updated:** no
- **Durable docs linked back to evidence where useful:** yes
- **Residual spec-only content:** the remediated final-spec commit identity

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
risk is closing Spec 000 before the remediated final package is committed.

## Residual Risks

- Spec 000 remains active until its remediated final state can be referenced by
  a new final-spec commit.
- Repository-local prompt validation is unavailable because the lifecycle
  plugin and its prompts are externally installed; package MCP operations work.
- Agent Workbench reports table-readability advisories for machine-readable
  lifecycle matrices. These are explicitly waived where shortening or splitting
  rows would weaken deterministic traceability; parser, frontmatter, and link
  checks remain required.

## Readiness Decision

- **Ready for promotion:** yes
- **Ready for release:** not applicable
- **Ready for closure:** structurally yes (`closure_check` returned `ready=true`);
  closure execution is deferred until the remediated final-spec commit exists
