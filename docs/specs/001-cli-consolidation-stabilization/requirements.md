---
title: CLI consolidation stabilization requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

TimeLocker's CLI still mixes repository-resolution, service-manager, and
monitoring integration paths. Earlier registration and configuration slices are
complete; this package governs the remaining consolidation without changing the
observable command hierarchy.

## Goals

- Standardize command modules on the `RepositoryResolver` service seam.
- Reduce `CLIServiceManager` to a narrow compatibility boundary.
- Converge monitoring commands on one command-facing integration path.
- Preserve CLI help, command discovery, and runtime behavior throughout.

## Non-Goals

- A one-pass CLI rewrite or a new command hierarchy.
- Removal of compatibility entry points before callers are migrated and tested.
- Unrelated feature delivery or broad static-analysis cleanup.
- Reopening completed registration and configuration slices without evidence of regression.

## Glossary

| Term | Definition |
|------|------------|
| RepositoryResolver | CLI service wrapper that resolves named repositories and repository URIs. |
| CLIServiceManager | Existing compatibility/facade object used by CLI command code. |
| Monitoring path | Command, formatter, and integration seams used to display monitoring information. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `docs/reference/timelocker-cli-command-hierarchy.md` | Current public CLI organization. | high | Must remain stable. |
| `docs/3-implementation/service-layer-integration.md` | Current service-layer boundaries and compatibility seams. | medium | Promote changes after each accepted slice. |
| `docs/reference/repo-orientation-and-change-map.md` | Navigation and ownership map for CLI modules. | high | Refresh if files move or responsibilities change. |
| Commit `d8600cc5ee9b06774e1d73f69a392179015e4bff` | Registration consolidation evidence. | high | Migrated as completed work. |
| Commit `519dc81cbc77147fa64b12041c608b1ae7cd978e` | ConfigService migration evidence. | high | Migrated as completed work. |

## Durable Impact

| Durable area | Action | Target | Notes |
|--------------|--------|--------|-------|
| implementation | modify | `docs/3-implementation/service-layer-integration.md` | Reflect final resolver, facade, and monitoring seams. |
| reference | clarify | `docs/reference/repo-orientation-and-change-map.md` | Update code navigation and responsibility boundaries. |
| CLI contract | unchanged | `docs/reference/timelocker-cli-command-hierarchy.md` | Help and discovery remain stable. |

## Staged Readiness

- **Current stage:** implementation
- **Next stage:** T005 repository-resolution cleanup
- **Ready to design when:** satisfied by the migrated design and existing evidence.
- **Design-first exception:** no
- **Optional artifacts recommended:** `change-impact.md`, `verification.md`, `traceability.md`
- **Downstream review needed:** verification after each remaining slice

## Requirements

### Requirement 1: Preserve the CLI contract

**User Story:** As a TimeLocker user, I want consolidation to preserve command
discovery and help output, so that maintenance work does not break automation or
documented usage.

#### Acceptance Criteria

1. WHILE internal CLI seams are consolidated, THE SYSTEM SHALL preserve unique
   top-level command registration and documented command names.
2. IF a compatibility entry point remains, THEN THE SYSTEM SHALL keep its
   observable contract stable until all callers have migrated.

### Requirement 2: Use one repository-resolution seam

**User Story:** As a command author, I want repository resolution behind one
service, so that validation and error behavior do not drift between commands.

#### Acceptance Criteria

1. GIVEN CLI command code that resolves a repository, WHEN it is updated, THEN
   it SHALL use `cli_modules.services.RepositoryResolver` or an explicitly
   documented compatibility adapter.
2. WHERE direct resolver utility imports remain, THE SYSTEM SHALL identify the
   compatibility reason and test the boundary.

### Requirement 3: Narrow the service manager

**User Story:** As a maintainer, I want commands to use narrow services, so that
`CLIServiceManager` no longer concentrates domain logic and fallback behavior.

#### Acceptance Criteria

1. WHEN a command needs a domain capability, THEN it SHALL prefer a focused
   service or facade over `CLIServiceManager` internals.
2. WHILE `get_cli_service_manager()` remains public, THE SYSTEM SHALL preserve
   its compatibility behavior and cover migrated callers with focused tests.

### Requirement 4: Consolidate monitoring integration

**User Story:** As a maintainer, I want one command-facing monitoring path, so
that formatting, data access, and error handling have a clear owner.

#### Acceptance Criteria

1. GIVEN overlapping monitoring command and integration paths, WHEN the slice
   completes, THEN one documented command-facing integration path SHALL remain.
2. IF compatibility wrappers remain, THEN THE SYSTEM SHALL make their delegation
   explicit and test the supported behavior.

## Correctness Properties

- **CP-001**: Top-level command names remain unique after every slice.
- **CP-002**: Equivalent repository inputs resolve to equivalent repository
  identities regardless of the migrated command caller.
- **CP-003**: Compatibility entry points delegate to the same narrow service
  behavior as migrated direct callers.

## Technical Context

- **Language/Version:** Python 3.11+
- **Primary Dependencies:** Typer, Restic integration, pytest
- **Target Platform:** TimeLocker CLI
- **Constraints:** Small reviewable slices; preserve public behavior
- **Performance Goals:** No material CLI startup or command-execution regression

## Success Criteria

- **SC-001**: Focused CLI help and command-registration tests pass after every slice.
- **SC-002**: Direct repository-resolution utility imports in command modules are eliminated or explicitly justified.
- **SC-003**: `CLIServiceManager` fan-out decreases and focused tests cover retained compatibility.
- **SC-004**: One documented monitoring command-facing path remains and T008-T010 capture final validation, promotion, and closure readiness.

## Related Artifacts

- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
