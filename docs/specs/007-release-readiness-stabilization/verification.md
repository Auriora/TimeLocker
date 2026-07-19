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
| Task evidence complete | yes | passed | T001-T013 contain concrete implementation or validation evidence. |
| Normal and dependency-owning test profiles pass | yes | passed | GitHub Actions run `29676747955` passed normal, MinIO, coverage quality-gate, and notification jobs. |
| Stress implementation and disposition recorded | yes | passed | T004 implementation and repeat evidence are recorded in GitHub issue #68. |
| Artifacts and six-combination clean installs validate | yes | passed | Run `29679083454` passed one build and all 12 artifact/OS/Python jobs. |
| Release interface and rehearsal prove no publication side effect | yes | passed | T009-T010: reusable read-only validation, local rehearsal, three negative paths, and unchanged external state. |
| Durable documentation and communications promoted | yes | passed | T011-T012; Markdown/link check found zero issues in the five durable targets. |
| Final lifecycle checks and expert review pass | yes | passed | T013 lifecycle checks have zero blocking gaps; bounded expert review has no remaining actionable findings. |

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
| `actionlint`, nine focused release-contract tests, build/inspect, two clean-install smokes, and negative mismatch/missing/permission paths | Prove the reusable pre-tag interface and CP-004 rehearsal | passed | T009-T010; HEAD `1dcf910`, zero tags/releases, and 11 historical release runs were unchanged. |
| `python scripts/extract_release_notes.py --version 0.9.1` | Derive the eventual GitHub body from the canonical changelog section | passed | T012 preview contains the complete evidence-backed section and limitations. |
| Agent Workbench Markdown/link set check and `git diff --check` | Validate durable-doc hygiene | passed | Five durable documents had zero findings; whitespace check passed before final review. |

## Requirement Coverage

| Requirement | Acceptance Criteria Covered | Evidence | Residual Risk |
|-------------|------------------------------|----------|---------------|
| Requirement 1 | AC1-AC6 | T001-T003 passed; GitHub Actions run `29676747955` | Marker and workflow contract tests guard future profile drift. |
| Requirement 2 | AC1-AC4 | T004-T005 passed; issue #68 records environment, baseline, tolerance, and repeat evidence | Post-change hosted evidence follows the explicitly requested commit. |
| Requirement 3 | AC1-AC5 | T006 and T008 passed; run `29679083454` | Preparation must continue to use both disabling flags. |
| Requirement 4 | AC1-AC5 | T007-T008 passed; installation guide and release procedure updated by T011 | Future support changes require the same matrix. |
| Requirement 5 | AC1-AC6 | T009-T013 passed | Human operator error at first actual tag remains explicitly owned. |

## Correctness Property Coverage

| Property | Covered By | Evidence | Residual Risk |
|----------|------------|----------|---------------|
| CP-001 | T001-T003, collection partition and workflow run `29676747955` | passed | Contract tests guard marker, selector, service, and artifact-transfer drift. |
| CP-002 | T006 version guard and negative test | passed | Automated guard covers source and artifact identity. |
| CP-003 | T007 six-combination artifact matrix | passed | Final shared-artifact run passed all 12 jobs. |
| CP-004 | T006, T008-T010, and T013 external-state comparisons | partial | Preparation and rehearsal passed; final comparison remains in T013. |
| CP-005 | T012-T013 changelog and derived release-body review | partial | Derivation passed; final expert review remains. |

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
| T009 | passed | Reusable read-only workflow, isolated publish job, workflow syntax, and nine focused tests | Only the dependent publish job has write permission. |
| T010 | passed | Local build/inspect, wheel/sdist smokes, three negative paths, and unchanged commit/tag/release/run state | No external publication occurred. |
| T011 | passed | Existing process corrected and indexed; README and installation claims aligned; Markdown/link set clean | PyPI and 1.0 remain deferred. |
| T012 | passed | Canonical changelog section and successful derived release-body preview | Four limitations are explicit. |
| T013 | passed | Final normal profile, lifecycle/hygiene checks, external-state comparison, and bounded TimeLocker expert-panel review | Human release approval and lifecycle closure remain separate. |

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
| 2026-07-19 | T009 release interface contracts | passed | `actionlint`, the workflow-boundary validator, and nine focused tests proved read-only rehearsal, isolated publication, and negative failure propagation. |
| 2026-07-19 | T010 local non-publishing rehearsal | passed | Intent, build, metadata/data/hashes, wheel and sdist clean-install smokes, and release inputs passed; version mismatch, missing artifact, and unsafe permission failed. |
| 2026-07-19 | T010 external-state comparison | unchanged | HEAD remained `1dcf910`; zero tags, zero GitHub releases, and 11 historical release runs remained. |
| 2026-07-19 | T011 durable documentation check | passed | Agent Workbench found zero Markdown or link issues across README, installation, process index, version process, and changelog. |
| 2026-07-19 | T012 release-body derivation | passed | The preview was extracted from the exact `0.9.1` changelog section; no second durable release-note file was created. |
| 2026-07-19 | Initial T013 normal-profile run | corrective finding | 2,773 passed, one skipped, 57 deselected, and 52.14% coverage; one test sampled live 100% CPU while asserting unconstrained parallelism. |
| 2026-07-19 | Resource-dependent test isolation | passed | The high-priority tool-manager test now supplies explicit low-load resources; all 22 tool-manager tests passed. |
| 2026-07-19 | Final T013 normal-profile run | passed | 2,774 passed, one skipped, 57 deselected, 19 warnings, and 52.14% coverage in 1,439.49 seconds. |
| 2026-07-19 | T013 TimeLocker expert-panel review | passed | Bounded Phase 4 diff review applied stewardship, Python CLI, security, reliability, operations, and documentation/lifecycle lenses; Restic behavior was unchanged. No actionable findings remained after test isolation. |
| 2026-07-19 | T013 lifecycle and hygiene checks | passed with advisory | Lifecycle lint had no errors and only the reviewed optional canonical-context advisory; traceability had zero acceptance gaps; `actionlint`, Markdown/link checks, workflow boundary validation, and `git diff --check` passed. |

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
- Stress thresholds remain host-sensitive by nature; T004's calibrated contract
  and issue #68 own the accepted tolerance evidence.
- Version tooling commits and tags by default; every preparation run must use
  both disabling flags and prove external state is unchanged.
- The verified matrix depends on hosted runner availability; future unavailable
  combinations block readiness until rerun or the support claim is reviewed.
- The first actual tag exercises external publication behavior that rehearsal
  cannot reproduce fully; it remains a human-controlled release risk.

## Durable Promotion And Cleanup

| Spec Content | Durable Destination Or Deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| Test profile contract | `docs/4-testing/README.md` | complete | T002-T004 promoted profile ownership, prerequisites, commands, and stress disposition. |
| Verified installation matrix | `docs/guides/user/installation.md` | complete | T007 matrix and prerequisites reconciled by T011. |
| Version preparation, release procedure, and rollback | `docs/processes/version-management.md`, linked from `docs/processes/README.md` | complete | T011 corrected the existing procedure; no duplicate was created. |
| Version contents and release communications | `CHANGELOG.md`; GitHub release body derived from its `v0.9.1` section | complete | T012 preview passed. |
| Front-door support and version claims | `README.md` | complete | T011 aligned version and Python support. |
| PyPI and `1.0.0` deferral | GitHub issue #22, milestone description, version process | complete | External and durable boundaries agree. |
| Follow-up work | GitHub issues outside milestone or an approved successor spec | complete | Existing issue #68 retains stress history; no new Phase 4 finding requires routing. |

### Spec Cleanup Decision

- **Cleanup action:** keep active
- **Reason:** All implementation tasks are complete; the package remains active
  only for the separately authorized lifecycle closure and its final commits.
- **Final spec commit:** pending
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** no
- **Closure cleanup commit:** pending
- **Active indexes updated:** yes for package creation
- **Durable docs linked back to evidence where useful:** yes
- **Residual spec-only content:** task-level implementation and validation evidence only

## Ship Or Closure Risk

- **Risk level:** high
- **Breaking change:** no
- **Blast radius checked:** complete for the Phase 4 workflow, scripts, tests, and docs diff
- **Rollback path:** corrected and validated in `docs/processes/version-management.md`
- **Requires human review:** yes
- **Release notes needed:** yes, in `CHANGELOG.md`
- **Follow-up issue or spec needed:** issue #68 already tracks stress evidence

### Risk Rationale

Normal, provisioned MinIO, extended, artifact, cross-platform install, rehearsal,
documentation, and expert-review gates pass. The tag-triggered release workflow
still has no successful repository release history, so the first tag remains a
high, human-controlled publication risk rather than an implementation blocker.

## Readiness Decision

- **Ready for promotion:** yes
- **Ready for release:** yes, for a separate release-maintainer decision
- **Ready for closure:** yes, through the separate lifecycle closure workflow

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Traceability: `traceability.md`
