---
title: Release readiness stabilization traceability
doc_type: spec
artifact_type: traceability
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Traceability Matrix

## Task To Context Matrix

| Task ID | Requirements | Acceptance Criteria | Design Sections | Change Impact | Verification | Durable Targets | Open Decisions |
|---------|--------------|---------------------|-----------------|---------------|--------------|-----------------|----------------|
| T001 | Requirement 1 | AC1, AC4, AC5, AC6 | CI Profile Logic | Live MinIO classification and collection safety | normal profile and collection partition | workflow, testing guide | none |
| T002 | Requirement 1 | AC2, AC3, AC6 | CI Profile Logic; Error Handling; Security | Provisioned MinIO profile | MinIO profile and negative preflight | workflow, testing guide | none |
| T003 | Requirement 1 | AC1, AC2, AC3, AC4, AC5, AC6 | Validation Strategy | CI profile readiness | CI quality gate, coverage, partition proof | testing guide | none |
| T004 | Requirement 2 | AC1, AC2, AC3, AC4 | Components; Validation Strategy | Spec-owned stress bug fix | representative timings, tests, issue #68, extended profile | tests, testing guide | none |
| T005 | Requirement 1, Requirement 2 | all | Downstream Task Guidance | CI and stress readiness | prerequisite checkpoint | none | none |
| T006 | Requirement 3 | AC1, AC2, AC3, AC4, AC5 | Version and Artifact Guard; Security | Side-effect-safe version and artifact changes | Git/release-state comparison, build, metadata, version guard | metadata, version process, changelog | none |
| T007 | Requirement 4 | AC1, AC2, AC3, AC4, AC5 | Clean-Install Matrix | Exact support matrix and install validation | six-combination wheel and sdist smoke matrix | metadata, installation guide | none |
| T008 | Requirements 3 and 4 | all | Validation Strategy | Artifact and install readiness | artifact checkpoint and side-effect proof | installation guide | none |
| T009 | Requirement 5 | AC1, AC5 | Release Rehearsal; Security | Safe pre-tag interface | syntax, tests, publication-boundary review | release workflow | none |
| T010 | Requirement 5 | AC1, AC4, AC5 | Release Rehearsal; Error Handling | Non-publishing rehearsal | rehearsal, failure paths, external-state comparison | verification record | none |
| T011 | Requirements 4 and 5 | R4 AC3, AC4, AC5; R5 AC2, AC5 | Operational Considerations; Clean-Install Matrix | Existing process and install guidance | command, Markdown, and link review | version process, process index, install guide, README if needed | none |
| T012 | Requirement 5 | AC3, AC5, AC6 | Validation Strategy | Canonical release communications | claim-to-evidence review and release-body preview | changelog | none |
| T013 | Requirement 1, Requirement 2, Requirement 3, Requirement 4, Requirement 5 | all | Validation Strategy; Downstream Task Guidance | all promotion targets | lifecycle, evidence, security, and expert review | all listed targets | none |
| T014 | Requirement 6, Requirement 7, Requirement 8, Requirement 9 | all | Phase 5 Machine Acceptance Flow; Migration and Compatibility | Linux Mint pilot reconciliation | lifecycle, traceability, and package review | spec package | operator credential, sudo, and cutover remain downstream gates |
| T015 | Requirement 6 | Requirement 6 AC1, Requirement 6 AC2, Requirement 6 AC3, Requirement 6 AC4 | Repository and Credential Boundary; Error Handling | Backup/recovery runtime repair | focused tests and isolated init/dry-run/backup | backup and recovery guidance | credential choice remains operator-owned |
| T016 | Requirement 7 | Requirement 7 AC1, Requirement 7 AC2, Requirement 7 AC3, Requirement 7 AC4 | Snapshot and Restore Boundary; Error Handling | Recoverable snapshot workflow | focused tests and digest-verified TimeLocker restore | backup and recovery guidance | none |
| T017 | Requirement 8 | Requirement 8 AC1, Requirement 8 AC2, Requirement 8 AC3 | Components and Changes; Error Handling | Mint tray compatibility | namespace/fallback tests and Mint smoke | installation/troubleshooting guidance | desktop packaging variance |
| T018 | Requirement 9 | Requirement 9 AC1, Requirement 9 AC2, Requirement 9 AC3, Requirement 9 AC4 | Schedule Rendering Boundary; Migration and Compatibility | Executable staged schedules | parser round trip and staged asset review | scheduling/operator guidance | privileged install remains operator-owned |
| T019 | Requirement 6, Requirement 7, Requirement 8, Requirement 9 | all | Validation Strategy; Downstream Task Guidance | all Phase 5 promotion targets | machine acceptance, lifecycle, tests, and docs review | all Phase 5 targets | NPBackup cutover requires observed runs |

## Requirement To Delivery Matrix

| Requirement | Acceptance Criteria | Design Sections | Tasks | Verification | Durable Targets |
|-------------|---------------------|-----------------|-------|--------------|-----------------|
| Requirement 1 | AC1-AC6 | CI Profile Logic; Error Handling | T001-T003 | normal and MinIO profiles, coverage, complete collection partition | workflow, `docs/4-testing/README.md` |
| Requirement 2 | AC1-AC4 | Components; Validation Strategy | T004-T005 | stress tests, issue #68 evidence, extended profile | tests and testing guide |
| Requirement 3 | AC1-AC5 | Version and Artifact Guard | T006, T008 | side-effect proof, build, metadata, hashes, version guard | metadata, version process, changelog |
| Requirement 4 | AC1-AC5 | Clean-Install Matrix | T007-T008, T011 | six-combination artifact install matrix and support-claim review | metadata, installation guide |
| Requirement 5 | AC1-AC6 | Release Rehearsal; Operational Considerations | T009-T013 | interface tests, rehearsal, docs, communications, expert review | version process, process index, changelog, README if needed |
| Requirement 6 | AC1-AC4 | Repository and Credential Boundary; Error Handling | T014-T015, T019 | focused tests and isolated init/dry-run/backup | backup and recovery guidance |
| Requirement 7 | AC1-AC4 | Snapshot and Restore Boundary; Error Handling | T014, T016, T019 | list/latest/exact restore and digest proof | backup and recovery guidance |
| Requirement 8 | AC1-AC3 | Components and Changes; Error Handling | T014, T017, T019 | Ayatana/legacy/headless tests and Mint smoke | installation/troubleshooting guidance |
| Requirement 9 | AC1-AC4 | Schedule Rendering Boundary; Migration and Compatibility | T014, T018-T019 | parser round trip, redacted asset review, cutover gate review | scheduling/operator guidance |

## Correctness Property Coverage

| Property | Requirements | Design Sections | Tasks | Tests Or Verification | Residual Risk |
|----------|--------------|-----------------|-------|-----------------------|---------------|
| CP-001 | Requirement 1 | CI Profile Logic | T001-T003 | collection partition and both CI profiles | marker drift |
| CP-002 | Requirement 3 | Version and Artifact Guard | T006, T008 | positive and negative version guard | none expected |
| CP-003 | Requirement 4 | Clean-Install Matrix | T007-T008 | wheel and sdist smoke across six combinations | runner availability blocks support claim |
| CP-004 | Requirements 3 and 5 | Version and Artifact Guard; Release Rehearsal | T006, T008-T010, T013 | pre/post commit, tag, and release-state identity | tag-only external behavior |
| CP-005 | Requirement 5 | Validation Strategy | T012-T013 | changelog claim evidence and derived release-body review | human review quality |
| CP-006 | Requirements 6 and 9 | Repository and Credential Boundary; Schedule Rendering Boundary | T014-T015, T018-T019 | credential precedence tests and redacted asset review | operator-managed environment file permissions |
| CP-007 | Requirement 7 | Snapshot and Restore Boundary | T014, T016, T019 | TimeLocker create/list/restore/digest round trip | filesystem metadata variance |
| CP-008 | Requirement 9 | Schedule Rendering Boundary | T014, T018-T019 | generated argv parser contract | CLI evolution requires contract maintenance |
| CP-009 | Requirement 8 | Components and Changes; Error Handling | T014, T017, T019 | namespace/fallback and headless CLI tests | desktop session variance |

## Design To Implementation Matrix

| Design Section | Requirements | Tasks | Interfaces Or Files | Verification |
|----------------|--------------|-------|---------------------|--------------|
| CI Profile Logic | Requirement 1 | T001-T003 | workflow, marker registry, fixtures, live and mocked integration tests | collection partition, normal CI, MinIO CI |
| Version and Artifact Guard | Requirement 3 | T006, T008 | helper, bump config, metadata, package version, build output | external-state identity, guard, build, metadata, hashes |
| Clean-Install Matrix | Requirement 4 | T007-T008, T011 | metadata, workflows, smoke tooling, installation guide | isolated artifact installs on six combinations |
| Release Rehearsal | Requirement 5 | T009-T010, T013 | release workflow, rehearsal evidence | non-publishing interface, rehearsal, external-state identity |
| Operational Considerations | Requirements 4 and 5 | T011-T013 | existing version process, process index, installation guide, changelog | docs, command, link, communications, and expert review |
| Security, Trust, and Access | Requirements 1, 3, and 5 | T002, T006, T009-T010, T013 | workflow permissions, ephemeral MinIO values, version helper | secrets, permissions, and side-effect review |
| Repository and Credential Boundary | Requirement 6 | T014-T015, T019 | repository/backup CLI and credential resolver | focused tests and isolated pilot |
| Snapshot and Restore Boundary | Requirement 7 | T014, T016, T019 | snapshot adapter, restore manager/CLI, progress/status handling | list/restore/digest round trip |
| Schedule Rendering Boundary | Requirement 9 | T014, T018-T019 | schedule model, CLI, cron/systemd renderers | parser round trip and staged asset review |
| Phase 5 Machine Acceptance Flow | Requirements 6-9 | T014-T019 | runtime paths, optional tray, schedule tooling, durable guidance | isolated Linux Mint pilot and final checkpoint |

## Open Decision Impact

There are no unresolved decisions blocking isolated implementation. Repository
credential selection, sudo installation for protected sources, discovery of the
actual NPBackup scheduler, observed scheduled runs, and cutover are explicit
operator gates that block migration, not T015-T018 implementation.

## Maintenance Notes

- Update this matrix whenever acceptance criteria, task IDs, support claims,
  validation profiles, or durable destinations change.
- Requirements and design, including the changelog-derived communications
  decision, were re-reviewed against this matrix after the TLR-001 through
  TLR-006 remediation; all acceptance mappings are explicit.
- Spec 007 owns stress implementation and acceptance; issue #68 is the linked
  assignment, state, and chronological-evidence record.
