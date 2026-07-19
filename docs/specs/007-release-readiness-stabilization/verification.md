---
title: Release readiness stabilization verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
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
| Task evidence complete | yes | pending | T001-T008 passed; T009-T013 pending. |
| Normal and dependency-owning test profiles pass | yes | passed | GitHub Actions run `29676747955` passed normal, MinIO, coverage quality-gate, and notification jobs. |
| Stress implementation and disposition recorded | yes | passed | T004 implementation and repeat evidence are recorded in GitHub issue #68. |
| Artifacts and six-combination clean installs validate | yes | passed | Run `29679083454` passed one build and all 12 artifact/OS/Python jobs. |
| Release interface and rehearsal prove no publication side effect | yes | pending | T009-T010. |
| Durable documentation and communications promoted | yes | pending | T011-T012 and promotion table below. |
| Final lifecycle checks and expert review pass | yes | pending | T013; package-creation review does not replace final implementation review. |

## Validation Commands And Methods

| Command Or Method | Purpose | Result | Evidence |
|-------------------|---------|--------|----------|
| `python -m pytest -m "not performance and not stress and not minio"` | Normal correctness and coverage profile | passed | Hosted run `29676747955`: 2,759 passed, one skipped, 57 deselected; 52.15% coverage. |
| complete collection compared with normal, `minio`, performance, and stress selections | Prove collection safety and node ownership | passed | 2,817 total nodes partition into 2,760 normal, 53 performance/stress, and four live MinIO nodes. |
| `python -m pytest -m minio` with provisioned service | Validate live S3 integration and dependency preflight | passed | Four local live nodes passed in 20.39 seconds; the provisioned job also passed in run `29676747955`. |
| `python -m pytest -m "performance or stress" --no-cov` | Extended performance and stress profile | passed | 53 passed, 2,770 deselected in 45.60 seconds; issue #68 records three repeated targeted medians and the no-coverage rationale. |
| `python scripts/bump_version.py bump patch --no-commit --no-tag` plus pre/post commit, tag, tag-triggered release-workflow run, and release identity | Prepare `0.9.1` without publication side effects | passed | Helper changed only `.bumpversion.cfg`, `pyproject.toml`, and `src/TimeLocker/__init__.py`; zero tags/releases and 11 historical release runs remained. |
| `python -m build`, version guard, metadata inspection, and SHA-256 generation | Build and prove artifact identity | passed | Final run `29679083454` validated one wheel, one sdist, metadata, entry points, nine data files, and hashes; wrong-version guard failed as intended. |
| wheel and sdist smoke installs on Linux, macOS, and Windows for Python 3.12 and 3.13 | Prove CP-003 and all declared support claims | passed | Run `29679083454`: all 12 wheel/sdist jobs passed both CLI entry points. |
| safe pre-tag interface tests and non-publishing rehearsal | Prove CP-004, including failure paths and unchanged external state | pending | T009-T010. |
| repository Markdown/link checks and `git diff --check` | Validate specification and durable-doc hygiene | pending | Package reconciliation and T011-T013. |

## Requirement Coverage

| Requirement | Acceptance Criteria Covered | Evidence | Residual Risk |
|-------------|------------------------------|----------|---------------|
| R1 | AC1-AC6 | T001-T003 passed; GitHub Actions run `29676747955` | Marker and workflow contract tests guard future profile drift. |
| R2 | AC1-AC4 | T004-T005 passed; issue #68 records environment, baseline, tolerance, and repeat evidence | Post-change hosted evidence follows the explicitly requested commit. |
| R3 | AC1-AC5 | T006 and T008 passed; run `29679083454` | Preparation must continue to use both disabling flags. |
| R4 | AC1-AC5 | T007-T008 passed; installation guide updated | T011 will reconcile the broader durable release procedure. |
| R5 | AC1-AC6 | T009-T013 pending | Human operator error at first actual tag. |

## Correctness Property Coverage

| Property | Covered By | Evidence | Residual Risk |
|----------|------------|----------|---------------|
| CP-001 | T001-T003, collection partition and workflow run `29676747955` | passed | Contract tests guard marker, selector, service, and artifact-transfer drift. |
| CP-002 | T006 version guard and negative test | passed | Automated guard covers source and artifact identity. |
| CP-003 | T007 six-combination artifact matrix | passed | Final shared-artifact run passed all 12 jobs. |
| CP-004 | T006, T008-T010, and T013 external-state comparisons | partial | T006/T008 passed; rehearsal and final review remain. |
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
| T001 | passed | Exact node partition, focused contract tests, and normal-profile run passed | Four live nodes are `minio`; mocked/configuration tests remain normal. |
| T002 | passed | Pinned disposable MinIO, readiness preflight, negative dependency contract, and four live nodes passed | Hosted execution belongs to T003. |
| T003 | passed | Actions run `29676747955`: normal, MinIO, quality-gate, and notification jobs passed | Phase 1 checkpoint complete. |
| T004 | passed | Correctness/timing split, 1.0-second baseline, 2.0x tolerance, three repeat runs, and 53-test extended profile | Issue #68 contains the environment and chronological evidence. |
| T005 | passed | T003 hosted run plus T004 local normal/extended profiles and issue evidence | Phase 2 checkpoint complete. |
| T006 | passed | Safe helper invocation, identity guard, one shared build, metadata/data/hash inspection, and unchanged external release state | No tag or release created. |
| T007 | passed | Run `29679083454` passed wheel and sdist on all six OS/Python combinations | Windows encoding defect found in the first run and fixed by `4a2d998`. |
| T008 | passed | CP-002, CP-003, and Phase 3 CP-004 evidence reviewed | Phase 3 checkpoint complete. |
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
| 2026-07-18 | T001 focused MinIO profile tests | passed | Nine normal-profile contract/configuration tests passed and four live nodes were deselected without using repository MinIO configuration. |
| 2026-07-18 | T001 collection partition | passed | All 2,812 nodes accounted for: 2,755 normal, 53 performance/stress, and four live MinIO. |
| 2026-07-18 | T001 exact normal profile | passed | 2,754 passed, one skipped, 57 deselected, 19 warnings, and 52.13% coverage in 783.96 seconds. |
| 2026-07-18 | T002 workflow and environment contracts | passed | Action syntax, pinned-service provisioning, actionable preflight failure, URI-scheme preservation, and process-environment precedence passed focused tests. |
| 2026-07-18 | T002 provisioned MinIO profile | passed | Disposable loopback MinIO served all four live nodes; 2,812 nodes were deselected and cleanup succeeded. |
| 2026-07-18 | Phase 1 exact normal profile | passed | 2,758 passed, one skipped, 57 deselected, 19 warnings, and 52.13% coverage in 571.62 seconds. |
| 2026-07-19 | Hosted Phase 1 checkpoint, run `29676747955` | passed | Commit `8a7e1c1`; 2,759 normal tests passed, one skipped, 57 deselected, 52.15% coverage, four live MinIO tests passed, and the quality gate and notification completed successfully. |
| 2026-07-19 | Legacy selection stress baseline | passed but unstable contract | The fixed 60-second gate completed 209 iterations on Linux/Python 3.12.6; historical observations of 57 and 70 demonstrated host sensitivity. |
| 2026-07-19 | Repeated calibrated selection stress contract | passed | Three `--no-cov` runs reported 0.160, 0.176, and 0.173 second medians against a 1.0-second baseline and 2.0x tolerance. |
| 2026-07-19 | Phase 2 extended profile | passed | 53 passed and 2,770 deselected in 45.60 seconds without coverage instrumentation. |
| 2026-07-19 | Phase 2 normal profile | passed | 2,765 passed, one skipped, 57 deselected, and 52.14% coverage in 726.60 seconds. |
| 2026-07-19 | Non-publishing version preparation | passed | From `9348c584`, the helper changed only the three configured version files; tag, release-workflow, and GitHub-release identity did not change. |
| 2026-07-19 | Local artifact inspection and negative guard | passed | Version, Python range, both entry points, nine package-data files, and hashes passed; expected version `0.9.0` failed before artifact checks. |
| 2026-07-19 | Hosted artifact run `29678906850` | failed as designed gate | Linux/macOS passed; all Windows jobs exposed `cp1252`-unsafe help glyphs. |
| 2026-07-19 | Windows help portability fix `4a2d998` | passed | ASCII metavar/epilog plus a `cp1252` regression contract removed the installation blocker. |
| 2026-07-19 | Hosted artifact run `29679083454` | passed | One shared build and all 12 wheel/sdist matrix jobs passed across Linux, macOS, Windows, Python 3.12, and Python 3.13. |

## Manual Or External Verification

GitHub issue and milestone state is externally authoritative for assignment and
chronology. The active spec remains authoritative for approved scope,
sequencing, acceptance, and validation. GitHub Actions runs and eventual
release artifacts must be linked here before release readiness can be approved.

## Residual Risks

- GitHub Actions currently emits a non-blocking Node.js 20 deprecation warning
  for upstream action versions that the runner forces onto Node.js 24.
- Future marker drift could change profile ownership; the T001 contract test
  guards the intended four live nodes and mocked-test placement.
- Stress thresholds can remain host-sensitive until T004 evidence is accepted.
- Version tooling commits and tags by default; every preparation run must use
  both disabling flags and prove external state is unchanged.
- The verified matrix depends on hosted runner availability; future unavailable
  combinations block readiness until rerun or the support claim is reviewed.
- The first actual tag exercises external publication behavior that rehearsal
  cannot reproduce fully; it remains a human-controlled release risk.

## Durable Promotion And Cleanup

| Spec Content | Durable Destination Or Deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| Test profile contract | `docs/4-testing/README.md` | pending | T002-T003. |
| Verified installation matrix | `docs/guides/user/installation.md` | partial | T007 matrix and prerequisites promoted; T011 owns final procedure reconciliation. |
| Version preparation, release procedure, and rollback | `docs/processes/version-management.md`, linked from `docs/processes/README.md` | pending | T011; no duplicate process document. |
| Version contents and release communications | `CHANGELOG.md`; GitHub release body derived from its `v0.9.1` section | pending | T012. |
| Front-door support and version claims | `README.md` if current text requires correction | pending | T011. |
| PyPI and `1.0.0` deferral | GitHub issue #22, milestone description, version process | partial | GitHub scope updated; durable process pending. |
| Follow-up work | GitHub issues outside milestone or an approved successor spec | pending | T013. |

### Spec Cleanup Decision

- **Cleanup action:** keep active
- **Reason:** Implementation is active; T001-T008 are complete and T009-T013 remain.
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

Normal, provisioned MinIO, extended, artifact, and cross-platform install gates
now pass. The tag-triggered release workflow still has no successful repository
release history, and Phase 4 rehearsal, durable procedure reconciliation,
communications, and final expert review remain. No release should proceed until
those gates are complete.

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
