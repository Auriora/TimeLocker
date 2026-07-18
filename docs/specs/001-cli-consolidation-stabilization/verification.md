---
title: CLI consolidation stabilization verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Verification

## Validation Plan

| Gate | Covers | Pass criterion | Evidence |
|------|--------|----------------|----------|
| Package lint/readiness | Spec integrity | No unwaived errors; next task is T005 | pending migration validation |
| CLI contract tests | Requirement 1, CP-001 | Help/discovery and unique-registration tests pass | record per slice |
| Resolver validation | Requirement 2, CP-002 | Focused tests pass and direct imports are eliminated or justified | T005 |
| Service-manager validation | Requirement 3, CP-003 | Focused tests pass and selected fan-out is removed | T006 |
| Monitoring validation | Requirement 4 | Focused tests pass and one command-facing path is documented | T007 |
| Full regression suite | Requirements 1-4 | Repository-required pytest suite passes or waivers are recorded | T008 |
| Durable promotion | Closure | Required docs and updates reflect accepted implementation | T009 |
| Closure readiness | Closure | Residual risk, deferrals, final commit, and cleanup action are recorded | T010 |

## Quality Gates

- Run CLI contract tests after every remaining implementation slice.
- Pair static dependency/import searches with focused behavioral tests.
- Do not remove compatibility behavior without caller inventory and impact review.
- Run the repository-required full test suite before promotion and closure.
- Record waivers, residual risks, and exact evidence for every incomplete gate.

## Evidence Log

- T001-T003: `docs/updates/2026-04-23-173102-cli-consolidation-first-slice.md`.
- T004: `docs/updates/2026-05-06-181418-cli-configservice-command-standardization.md`.
- T005-T008: pending.

## Evidence Recording Rules

For each remaining task, record the exact focused commands, result summary,
changed caller group, compatibility behavior retained, and residual risk. A
search result alone does not prove runtime behavior; pair it with focused tests.

## Durable Promotion And Cleanup

| Spec content | Durable destination or deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| Resolver/service/monitoring boundaries | `docs/3-implementation/service-layer-integration.md` | pending | T009 |
| Code navigation and ownership | `docs/reference/repo-orientation-and-change-map.md` | pending | T009 |
| Public command hierarchy | unchanged unless drift is discovered | pending review | CLI contract tests |
| Implementation history | `docs/updates/` | pending | Per-slice entries |

### Spec Cleanup Decision

- **Cleanup action:** keep active
- **Reason:** T005-T008 remain pending.
- **Final spec commit:** pending
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** no
- **Closure cleanup commit:** pending
- **Active indexes updated:** no
- **Durable docs linked back to evidence where useful:** yes
- **Residual spec-only content:** remaining requirements, tasks, and validation evidence

## Ship Or Closure Risk

- **Risk level:** medium
- **Breaking change:** no
- **Blast radius checked:** partial — required per remaining task
- **Rollback path:** revert each bounded implementation slice
- **Requires human review:** yes for compatibility removals
- **Release notes needed:** only if user-visible behavior changes
- **Follow-up issue or spec needed:** only for newly discovered out-of-scope defects

### Risk Rationale

The CLI has broad command coverage and compatibility seams. Small slices and
contract tests reduce risk, but hidden consumers and backend-specific resolution
paths remain possible until inventory and full validation complete.

## Residual Risks

- External consumers of `CLIServiceManager` may not be visible in repository searches.
- Repository-resolution behavior may vary across local, S3, and B2 backends.
- Optional monitoring integrations may need validation outside the focused unit suite.

## Readiness Decision

- **Ready for promotion:** no
- **Ready for release:** no
- **Ready for closure:** no
