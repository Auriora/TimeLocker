---
title: CLI consolidation stabilization design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

Continue the existing incremental consolidation. Each slice changes one seam,
adds or updates focused regression tests, records evidence, and only then moves
to the next dependency. Compatibility entry points remain thin delegates until
their callers can safely migrate.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| Requirement 1 | AC1-AC2 | Stable root registration and compatibility boundary | CLI help/registration tests |
| Requirement 2 | AC1-AC2 | RepositoryResolver as command-facing seam | resolver and command tests; import search |
| Requirement 3 | AC1-AC2 | Focused services behind compatibility facade | service/facade tests; dependency search |
| Requirement 4 | AC1-AC2 | Single monitoring integration owner | monitoring command/integration tests |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | Root app composition remains unchanged by remaining slices. | Existing uniqueness/help tests. | Completed registration slice provides guardrail. |
| CP-002 | RepositoryResolver owns normalization and lookup. | Parameterized resolver/command tests. | Use conventional tests unless property-test tooling is adopted. |
| CP-003 | Compatibility methods delegate without alternate fallback logic. | Focused facade and command tests. | Search for duplicate domain logic. |

## High-Level Design

### System Architecture

```text
Typer command
    |-- RepositoryResolver ------> repository/config services
    |-- focused domain service --> domain behavior
    `-- monitoring integration --> monitoring data + presentation

get_cli_service_manager() --> thin compatibility facade --> focused services
```

### Components and Changes

- `src/TimeLocker/cli_modules/commands/`: replace direct repository utilities
  and manager internals with narrow injected or constructed services.
- `src/TimeLocker/cli_modules/services/repository_resolver.py`: retain the
  command-facing repository contract.
- `src/TimeLocker/cli_services.py`: reduce fallback and domain fan-out while
  retaining the public factory seam.
- Monitoring command/integration modules: select one owner for command-facing
  orchestration and leave explicit delegates where compatibility is required.
- Focused tests: prove each migrated caller and the stable CLI contract.

### Data Models

No persistent schema changes. Existing repository configuration, credentials,
and monitoring result models remain authoritative.

### Data Flow

Commands parse inputs, invoke a narrow service, receive domain results, and
format output. Resolution, domain behavior, and monitoring presentation must not
be independently reimplemented in command functions.

## Low-Level Design

### Algorithms and Logic

```text
for each remaining seam:
    inventory callers and focused tests
    add regression coverage for current supported behavior
    migrate one coherent caller group
    remove newly unreachable duplicate logic
    run focused and CLI-contract validation
    update evidence and durable docs
```

### Function Signatures and Interfaces

Retain existing public signatures unless a task explicitly documents a
compatibility migration. Prefer focused service methods already present in
`cli_modules/services/` over expanding `CLIServiceManager`.

### Error Handling

Narrow services own domain and validation errors. Commands translate them into
stable CLI messages and exit behavior. Compatibility delegates must not create
a second fallback/error path.

### Security, Trust, and Access

Repository credentials and secrets remain behind existing credential/config
services. Tests must avoid real credentials, external repositories, or network
access unless an integration test explicitly provisions them.

### Migration and Compatibility

Land Tasks T005-T007 independently. Do not remove `get_cli_service_manager()`
as part of this spec. Any removed wrapper must first have zero supported callers
and focused evidence.

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| CLI help and unique registration tests | Requirement 1, CP-001 | `verification.md` and task evidence | dynamic plugin commands may require separate coverage |
| Resolver unit/command tests and import search | Requirement 2, CP-002 | T005 evidence | unusual backend URI edge cases |
| Facade/service tests and dependency search | Requirement 3, CP-003 | T006 evidence | hidden external consumers of compatibility methods |
| Monitoring focused tests | Requirement 4 | T007 evidence | optional external monitoring integrations |

## Downstream Task Guidance

- Start with T005; T006 and T007 follow after its checkpoint.
- Mark a task `[~]` before implementation and record exact commands/evidence.
- Update `change-impact.md` if the selected boundary differs from this design.
- Promote accepted structure into implementation/reference docs before closure.

## Operational Considerations

No data migration or deployment sequencing is expected. Each slice should be
revertible independently. Run the full repository test suite before closure,
even when focused tests pass during individual slices.

## Open Questions

- Which `CLIServiceManager` methods have consumers outside the repository?
- Which monitoring wrapper should be the retained command-facing owner after
  caller inventory?

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
