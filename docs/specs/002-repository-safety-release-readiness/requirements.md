---
title: Repository safety and release readiness requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

The 2026-07-18 repository review found two critical safety defects and three
readiness/documentation defects. This package governs the accepted remediation
of findings TLR-001 through TLR-005 and temporarily preempts Spec 001.

## Goals

- Prevent restore operations from replacing existing destination files unless
  the operator explicitly requests overwrite behavior.
- Require an operator-supplied secret for non-interactive credential-store
  unlock; never derive encryption keys from predictable host attributes.
- Provide one truthful source-install path and a Python-native release workflow.
- Ensure tests import the installed `TimeLocker` package identity.
- Keep durable architecture documents limited to implemented current state.

## Non-Goals

- Publishing a package to PyPI or configuring external release credentials.
- Redesigning the restore, credential, CLI, or plugin architectures.
- Preserving insecure deterministic-key credential stores as a supported
  compatibility mode.
- Advancing the CLI consolidation tasks in Spec 001.
- Adding future GUI, REST API, or network-backend commitments.

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `CHARTER.md` | Recovery safety, security, one supported path, and current documentation are project priorities. | high | Governing project boundary. |
| `README.md` | Repository front door and installation guidance. | high | Must become truthful for current distribution state. |
| `docs/2-architecture/` | Durable architecture surface. | medium | Contains legacy future-state material to remove. |
| `docs/guides/user/per-repo-credentials.md` | Current credential-store usage guidance. | medium | Must describe explicit non-interactive secrets. |
| `.github/workflows/test.yml` | Current Python CI conventions. | high | Release workflow should follow this project stack. |

## Durable Impact

| Durable area | Action | Target | Notes |
|--------------|--------|--------|-------|
| installation | clarify | `README.md`, `docs/guides/user/installation.md` | Source install is the supported path until a package is published. |
| security/reference | modify | `docs/guides/user/per-repo-credentials.md` | Document explicit environment or protected-file secrets. |
| architecture | supersede | `docs/2-architecture/system-architecture.md`, `component-breakdown.md`, `data-flow.md` | Replace future-state content with current implementation. |
| release operations | modify | `.github/workflows/release.yml`, durable release guidance | Use Python build/test/install-smoke/release steps. |
| testing | clarify | test suite | Enforce one package namespace. |

## Staged Readiness

- **Current stage:** implementation
- **Next stage:** T002 restore safety
- **Ready to design when:** satisfied by the accepted review findings and design.
- **Design-first exception:** no
- **Optional artifacts used:** `change-impact.md`, `verification.md`, `traceability.md`
- **Downstream review needed:** verification and closure risk

## Requirements

### Requirement 1: Non-destructive restore default

**User Story:** As a backup operator, I want restores to preserve existing files
by default, so that recovery does not silently destroy newer destination data.

#### Acceptance Criteria

1. GIVEN a restore without explicit overwrite authorization, WHEN Restic is
   invoked, THEN THE SYSTEM SHALL pass `--overwrite never`.
2. GIVEN explicit overwrite authorization, WHEN Restic is invoked, THEN THE
   SYSTEM SHALL pass `--overwrite always`.
3. GIVEN an interactive destination conflict, WHEN the operator confirms
   overwrite, THEN that confirmation SHALL reach the execution layer.

### Requirement 2: Explicit credential-store secrets

**User Story:** As an operator, I want stored credentials encrypted by a secret
that is not derivable from the host, so that filesystem access alone is
insufficient to decrypt them.

#### Acceptance Criteria

1. THE SYSTEM SHALL NOT derive a credential-store key from machine ID,
   hostname, user ID, usernames, or public constants.
2. WHERE non-interactive unlock is required, THE SYSTEM SHALL accept an
   operator-supplied environment secret or a protected secret file.
3. IF a secret file is missing, empty, non-regular, symbolic, or accessible to
   group/other users on POSIX, THEN THE SYSTEM SHALL refuse it safely.

### Requirement 3: Truthful release and installation path

**User Story:** As a prospective user, I want installation and release guidance
that matches repository capabilities, so that I can install a usable build.

#### Acceptance Criteria

1. WHILE TimeLocker is not published to PyPI, durable guidance SHALL recommend
   source installation and SHALL NOT claim that `pip install timelocker` works.
2. GIVEN a version tag, WHEN the release workflow runs, THEN it SHALL verify the
   version, run required tests, build distributions, install-smoke the wheel,
   and attach artifacts to a GitHub release.
3. THE RELEASE WORKFLOW SHALL NOT depend on unrelated JavaScript/Bun metadata.

### Requirement 4: One Python package identity in tests

**User Story:** As a maintainer, I want tests to import production modules by
their installed name, so that singleton and registry behavior matches runtime.

#### Acceptance Criteria

1. ALL Python tests SHALL import or patch `TimeLocker`, not `src.TimeLocker`.
2. A regression check SHALL fail if the source-layout namespace returns to
   Python tests.

### Requirement 5: Current-state architecture documentation

**User Story:** As a developer or agent, I want architecture docs to describe
implemented behavior only, so that future designs are not mistaken for code.

#### Acceptance Criteria

1. Durable architecture documents SHALL omit unimplemented GUI and REST API
   components and flows.
2. Durable architecture documents SHALL not claim unsupported network backends
   or retain orphaned legacy requirement identifiers.
3. Updated Markdown SHALL pass repository document and internal-link checks.

## Correctness Properties

- **CP-001:** No restore path reaches Restic without an explicit overwrite mode.
- **CP-002:** A fresh process with only host-identifying information cannot
  unlock a credential store.
- **CP-003:** Test imports resolve to the same package identity used by `tl`.
- **CP-004:** Release automation consumes only Python project metadata and
  artifacts present in this repository.

## Technical Context

- **Language/Version:** Python 3.12+
- **Primary Dependencies:** Restic 0.18+, Typer, cryptography, pytest
- **Target Platform:** TimeLocker CLI and GitHub Actions
- **Constraints:** Preserve explicit overwrite behavior; do not publish externally
- **Performance Goals:** No material runtime impact

## Success Criteria

- **SC-001:** Focused restore tests prove both `never` and `always` argv.
- **SC-002:** Credential tests prove host-only auto-unlock is unavailable and
  explicit non-interactive secret sources are validated.
- **SC-003:** No `src.TimeLocker` reference remains under Python tests.
- **SC-004:** Distribution build and wheel install smoke checks pass locally or
  are recorded as an environment-specific release gate.
- **SC-005:** Full configured tests and documentation checks pass.

## Related Artifacts

- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
