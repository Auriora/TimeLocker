---
title: Release readiness stabilization verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Verification

## Scope

This record covers Spec 007 requirements R1-R5 and tasks T001-T013. It records
release-preparation evidence only; creating a production tag or release requires
separate explicit approval.

## Quality Gates

| Gate | Required? | Status | Evidence |
|------|-----------|--------|----------|
| Acceptance traceability complete | yes | passed | Lifecycle stage readiness reports zero acceptance, property, context, downstream-review, or blocking gaps after reconciliation. |
| Substantive requirements and design review | yes | passed | Review on 2026-07-18 produced TLR-001 through TLR-006; all six findings were reconciled into the package before implementation. |
| Task evidence complete | yes | pending | T001-T013 pending. |
| Normal and dependency-owning test profiles pass | yes | pending | Current normal run 29653160911 fails on unavailable MinIO. |
| Stress implementation and disposition recorded | yes | pending | T004 and GitHub issue #68. |
| Artifacts and six-combination clean installs validate | yes | pending | T006-T008. |
| Release interface and rehearsal prove no publication side effect | yes | pending | T009-T010. |
| Durable documentation and communications promoted | yes | pending | T011-T012 and promotion table below. |
| Final lifecycle checks and expert review pass | yes | pending | T013; package-creation review does not replace final implementation review. |

## Validation Commands And Methods

| Command Or Method | Purpose | Result | Evidence |
|-------------------|---------|--------|----------|
| `python -m pytest -m "not performance and not stress and not minio"` | Normal correctness and coverage profile | pending | Replaces current failing selector in T001. |
| complete collection compared with normal, `minio`, performance, and stress selections | Prove collection safety and node ownership | pending | T001-T003. |
| `python -m pytest -m minio` with provisioned service | Validate live S3 integration and dependency preflight | pending | T002. |
| `python -m pytest -m "performance or stress" --no-cov` | Extended performance and stress profile | pending | T004 and issue #68; final evidence must explain the coverage exception for this opt-in profile. |
| `python scripts/bump_version.py bump patch --no-commit --no-tag` plus pre/post commit, tag, tag-triggered release-workflow run, and release identity | Prepare `0.9.1` without publication side effects | pending | T006. |
| `python -m build`, version guard, metadata inspection, and SHA-256 generation | Build and prove artifact identity | pending | T006. |
| wheel and sdist smoke installs on Linux, macOS, and Windows for Python 3.12 and 3.13 | Prove CP-003 and all declared support claims | pending | T007 six-combination matrix. |
| safe pre-tag interface tests and non-publishing rehearsal | Prove CP-004, including failure paths and unchanged external state | pending | T009-T010. |
| repository Markdown/link checks and `git diff --check` | Validate specification and durable-doc hygiene | pending | Package reconciliation and T011-T013. |

## Requirement Coverage

| Requirement | Acceptance Criteria Covered | Evidence | Residual Risk |
|-------------|------------------------------|----------|---------------|
| R1 | AC1-AC6 | T001-T003 pending; failing run captured | Marker or collection drift could hide tests. |
| R2 | AC1-AC4 | Spec-owned T004-T005 and issue #68 pending | Host variance. |
| R3 | AC1-AC5 | T006 and T008 pending | Side-effecting defaults must remain disabled. |
| R4 | AC1-AC5 | T007-T008 and T011 pending | Unavailable runner blocks the associated support claim. |
| R5 | AC1-AC6 | T009-T013 pending | Human operator error at first actual tag. |

## Correctness Property Coverage

| Property | Covered By | Evidence | Residual Risk |
|----------|------------|----------|---------------|
| CP-001 | T001-T003, collection partition and workflow runs | pending | Marker drift. |
| CP-002 | T006 version guard and negative test | pending | None expected after automated guard. |
| CP-003 | T007 six-combination artifact matrix | pending | Runner availability is a blocking support gap. |
| CP-004 | T006, T008-T010, and T013 external-state comparisons | pending | Actual tag behavior remains separately controlled. |
| CP-005 | T012-T013 changelog and derived release-body review | pending | Review quality. |

## Agent Readiness Evidence

| Field | Evidence | Residual Risk |
|-------|----------|---------------|
| Scope and out-of-scope files | Requirements goals, non-goals, change impact, and task file lists | Newly discovered release blockers require reconciliation. |
| Must-read and optional context | Full Spec 007 package, `CHARTER.md`, workflows, metadata, version helper/config, install and process docs, issue #68 | GitHub evidence can change. |
| Permissions and approval points | Branch work approved; task commits require explicit commit instruction; tag, GitHub release, and PyPI publication require separate release approval | Do not infer publication authority. |
| Validation commands and expected signals | Validation table plus task-specific commands | Hosted services and runners remain external. |
| Review needs | CI, packaging, security, operations, and documentation review at T013 | Human release decision remains. |
| Durable-doc or closure impact | Promotion table and `change-impact.md` | Package cannot close before promotion. |
| Optional repo-evidence provider caveats | Agent Workbench routing is advisory and has stale deleted-path candidates; direct repository and lifecycle evidence are authoritative | Recheck provider before relying on suggestions. |

## Task Evidence

| Task ID | Status | Evidence | Notes |
|---------|--------|----------|-------|
| T001 | pending | Failing CI root cause captured | Live-versus-mocked classification and collection safety pending. |
| T002 | pending | | Provisioned profile pending. |
| T003 | pending | | CI checkpoint pending. |
| T004 | pending | GitHub issue #68 created and assigned | Spec owns implementation; issue tracks state and evidence. |
| T005 | pending | | Prerequisite checkpoint pending. |
| T006 | pending | Side-effecting helper defaults identified | Safe bump, artifact, and external-state evidence pending. |
| T007 | pending | Six-combination contract defined | Artifact matrix pending. |
| T008 | pending | | Artifact checkpoint pending. |
| T009 | pending | | Safe pre-tag interface pending. |
| T010 | pending | | Non-publishing rehearsal pending. |
| T011 | pending | Existing version process selected as promotion target | Durable updates pending. |
| T012 | pending | `CHANGELOG.md` selected as canonical source | Communications pending. |
| T013 | pending | | Final review and human decision pending. |

## Evidence Log

| Date | Evidence | Result | Notes |
|------|----------|--------|-------|
| 2026-07-18 | GitHub Actions run 29653160911 | failed | Unprovisioned MinIO caused one failure and four setup errors; normal CI is not release-ready. |
| 2026-07-18 | Focused local mocked MinIO contract test | passed | Controlled environment passed, supporting separation of mocked contracts from live-service tests. |
| 2026-07-18 | Open-issue reconciliation | passed | All 27 inherited open issues reviewed; 9 closed, 18 retained with current scope. |
| 2026-07-18 | GitHub milestone `v0.9.1` | created | PyPI and `1.0.0` explicitly deferred. |
| 2026-07-18 | GitHub issue #68 | created and assigned | Tracks selection stress assignment, state, and chronological evidence; Spec 007 owns delivery authority. |
| 2026-07-18 | Substantive Spec 007 review | findings addressed | TLR-001 through TLR-006 reconciled safe versioning, stress authority, support matrix, MinIO ownership, release-task decomposition, and review evidence. |
| 2026-07-18 | Downstream task and verification review | passed | Tasks and verification were rechecked after the final requirements and design reconciliation, including the changelog-derived communications model. |
| 2026-07-18 | Spec Lifecycle Manager package checks | passed | Package lint has zero diagnostics; stage readiness is implementation-ready with zero gaps; sampled T001, T004, T006, T007, T009, and T013 lookups and T001 readiness resolve without gaps. |
| 2026-07-18 | Documentation and patch checks | passed with advisory warnings | No structural Markdown findings, broken links, or whitespace errors; 135 table-readability warnings and 25 pre-existing canonical-link style suggestions remain non-blocking. |

## Manual Or External Verification

GitHub issue and milestone state is externally authoritative for assignment and
chronology. The active spec remains authoritative for approved scope,
sequencing, acceptance, and validation. GitHub Actions runs and eventual
release artifacts must be linked here before release readiness can be approved.

## Residual Risks

- Normal CI is currently red and blocks every downstream release claim.
- MinIO marker or collection changes can reduce coverage unless the complete
  node partition and mocked-contract placement are proved.
- Stress thresholds can remain host-sensitive until T004 evidence is accepted.
- Version tooling commits and tags by default; every preparation run must use
  both disabling flags and prove external state is unchanged.
- All six declared OS/Python combinations are release blockers until validated
  or their support claims are corrected.
- The first actual tag exercises external publication behavior that rehearsal
  cannot reproduce fully; it remains a human-controlled release risk.

## Durable Promotion And Cleanup

| Spec Content | Durable Destination Or Deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| Test profile contract | `docs/4-testing/README.md` | pending | T002-T003. |
| Verified installation matrix | `docs/guides/user/installation.md` | pending | T007 and T011. |
| Version preparation, release procedure, and rollback | `docs/processes/version-management.md`, linked from `docs/processes/README.md` | pending | T011; no duplicate process document. |
| Version contents and release communications | `CHANGELOG.md`; GitHub release body derived from its `v0.9.1` section | pending | T012. |
| Front-door support and version claims | `README.md` if current text requires correction | pending | T011. |
| PyPI and `1.0.0` deferral | GitHub issue #22, milestone description, version process | partial | GitHub scope updated; durable process pending. |
| Follow-up work | GitHub issues outside milestone or an approved successor spec | pending | T013. |

### Spec Cleanup Decision

- **Cleanup action:** keep active
- **Reason:** Implementation and release preparation have not started.
- **Final spec commit:** pending
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** no
- **Closure cleanup commit:** pending
- **Active indexes updated:** yes for package creation
- **Durable docs linked back to evidence where useful:** no
- **Residual spec-only content:** all intended content remains active

## Ship Or Closure Risk

- **Risk level:** high
- **Breaking change:** no
- **Blast radius checked:** partial
- **Rollback path:** existing version process to be corrected and validated in T011
- **Requires human review:** yes
- **Release notes needed:** yes, in `CHANGELOG.md`
- **Follow-up issue or spec needed:** issue #68 already tracks stress evidence

### Risk Rationale

Normal CI currently fails, the tag-triggered release workflow has no repository
release history, and artifact or clean-install evidence for `0.9.1` does not
exist. No release should proceed until the required gates are complete.

## Readiness Decision

- **Ready for promotion:** no
- **Ready for release:** no
- **Ready for closure:** no

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Traceability: `traceability.md`
