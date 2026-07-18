---
title: "RFC: CLI Helpers Extraction"
id: "rfc-cli-helpers-extraction"
type: [ plan ]
status: [ completed ]
owner: "CLI Team"
last_reviewed: "18-07-2026"
tags: [ plan, refactor, cli ]
links:
    tooling: [ ]
---

# RFC: CLI Helpers Extraction

- **Owner**: CLI Team
- **Status**: Completed
- **Last Updated**: 18-07-2026
- **Created Date**: 19-12-2024
- **Audience**: Engineering Teams, QA, Reviewers

## 1. Purpose

Refactor the `store_backend_credentials` helper from a nested Typer command into a standalone module to improve testability, reuse, and separation of concerns
within the CLI.

## 2. Problem Statement

The helper lived inside the `repos add` command, forcing tests to exercise the full CLI workflow and making the logic difficult to reuse. Direct testing
required complex CLI invocation, slowing feedback and obscuring failures. Success criteria:

- Helper callable directly without CLI scaffolding.
- Unit tests cover credential storage logic in isolation.
- Integration tests retain coverage of CLI prompts and parameter handling.

## 3. Proposed Solution

### 3.1 Implementation Steps

1. Extract `store_backend_credentials` to `src/TimeLocker/cli_helpers.py` with explicit dependencies passed via parameters.
2. Update `src/TimeLocker/cli.py` to import the helper and call it from the Typer command.
3. Create focused unit tests in `tests/TimeLocker/cli/test_cli_helpers.py` covering success, failure, and edge cases.
4. Retain integration tests in `tests/TimeLocker/cli/test_store_backend_credentials.py`, clarifying their scope and referencing the new unit suite.

### 3.2 Completed Changes

- **Direct Unit Tests**: Eight scenarios validating unlock flows, optional fields, exception handling, backend variants, and prompt suppression.
- **Integration Tests**: Seven scenarios ensuring CLI wiring, prompts, and argument parsing remain correct.
- **Benefits**:
    - Faster test execution (0.11s vs 0.63s for helper logic).
    - Easier debugging with failures isolated to helper functionality.
    - Reusable helper accessible to other commands without duplication.

## 4. Alternatives

1. **Keep helper nested in CLI command**
    - Pros: No refactor required.
    - Cons: Continues to impede testing and reuse. Rejected.
2. **Create a mixin class for CLI helpers**
    - Pros: Groups helper logic.
    - Cons: Adds inheritance without solving direct testability; standalone module deemed simpler.

## 5. Impact

- **Systems**: `src/TimeLocker/cli.py`, `src/TimeLocker/cli_helpers.py`, related test suites.
- **Risks**: Potential divergence between helper API and CLI usage. Mitigated by integration tests and shared typings.
- **Migration**: No breaking CLI changes; user behaviour unchanged.

## 6. Decision Log

- 19-12-2024 – RFC approved; work scheduled for Phase 4 integration refactors.
- 20-12-2024 – Refactor merged; unit and integration tests passing.
- 01-11-2025 – Document reformatted to repository plan template.
- 18-07-2026 – Lifecycle reconciled to completed after implementation and test evidence review.

# References

- Helper implementation: `src/TimeLocker/cli_helpers.py`
- CLI command: `src/TimeLocker/cli.py`
- Tests: `tests/TimeLocker/cli/test_cli_helpers.py`, `tests/TimeLocker/cli/test_store_backend_credentials.py`
