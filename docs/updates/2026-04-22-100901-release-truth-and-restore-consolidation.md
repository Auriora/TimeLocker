---
title: "Update: Release Truth And Restore Consolidation"
id: "update-2026-04-22-100901"
type: [ update ]
status: [ approved ]
owner: "Codex"
last_reviewed: "22-04-2026"
tags: [update, documentation, release, restore, cli]
links:
  tooling: [pytest, basedpyright]
---

# Update: Release Truth And Restore Consolidation

- **Owner**: Codex
- **Created Date**: 22-04-2026
- **Audience**: Developers
- **Related**: Repository review follow-up
- **Scope**: root, `src/TimeLocker/`, `docs/`

## 1. Purpose

Bring top-level release claims closer to the observable implementation state, remove stale service-layer migration commentary, and stop reporting placeholder
restore statistics.

## 2. Summary

- Rebased package/readme maturity claims from stable to beta-oriented wording.
- Corrected the root README installation link and repository-structure summary.
- Rewrote `docs/DOCUMENTATION-STATUS.md` from an unconditional success report into a consolidation checkpoint.
- Removed stale `ConfigurationService` / `BackupOrchestrator` TODO commentary from `cli_services.py` and wired `self._config_service` consistently.
- Replaced placeholder restore statistics with parsed values plus a filesystem fallback during verification.
- Removed a legacy `spec_from_file_location(...)` restore/selections loader from `cli.py` so command modules load through package imports only.
- Added explicit validation/import typing in the late `cli.py` config import/export flow so `migrate validate` and `config import config` no longer rely on mixed inferred dict shapes.
- Reworked the config export path in `cli.py` to serialize dataclasses/config-like objects through a helper and handle optional sections (`data_selections`, `policies`, `schedules`, `security`, `monitoring`) without assuming those attributes exist on every config fixture.
- Replaced the generic validation change-summary iteration in `cli.py` with typed buckets and removed a batch of top-level unused imports flagged by basedpyright.
- Tightened the Typer/CliRunner compatibility patch in `cli.py` to use `setattr(...)` for result monkeypatching and removed the last dead `re`/`urlparse` imports identified by IDE diagnostics.
- Typed `cli_helpers.store_backend_credentials(...)` around explicit credential/config protocols, switched its credential input to a mapping boundary, and replaced the Rich fallback console shim so targeted IDE diagnostics on the source file are clean.
- Updated the two direct helper test files to use typed repository/credential fixtures that match the narrowed helper contract.
- Tightened the top-of-file `cli.py` compatibility helpers further by typing the `CliRunner.invoke` monkeypatch to the real runtime signature, modernizing a bounded set of `Optional[...]` CLI annotations, and narrowing `_serialize_config_value(...)` / Rich input helper surfaces without changing command behavior.
- Tightened the remaining `cli.py` auth/config helper seam by strengthening the local access/session protocols, making the session sort key explicitly comparable, adding a typed `ConfigurationModule` factory protocol, and normalizing repository config serialization to concrete mapping shapes so the IDE-reported blocker slice is now warning-only.
- Tightened the `repos_credentials_set` / `cli_helpers.store_backend_credentials(...)` boundary so the CLI payload typing, repository-config shape, and helper protocol casts match real runtime behavior while preserving boolean `insecure_tls` handling required by the helper tests.
- Tightened `_ensure_manager_unlocked(...)` in `cli.py` around a narrow unlock-capable credential-manager protocol so the lower credential command flow no longer relies on raw `object` attribute access for `is_locked()` / `unlock()`.
- Tightened the `cli.py` logging/output helper seam by annotating the custom log filter and Rich log handler with explicit `logging.LogRecord` types, `@override`, and an annotated `console` attribute, then closed the next credentials-helper blocker by widening the local payload boundary to `dict[str, object]` and making the credential-store cast explicit through `object`.
- Tightened the credential-display table formatting block in `cli.py` by typing the local table payload explicitly and removing the redundant string narrowing so the IDE no longer reports the `append`/`format_table(...)` unknown-shape warnings in that slice.
- Tightened the config export/import optional-section loops in `cli.py` by iterating over explicitly typed `Mapping[object, object]` views for selections, policies, and schedules, which removed the remaining unknown loop-variable warnings in that block.
- Tightened the config export/import `security` and `monitoring` boundaries in `cli.py` by casting the `getattr(...)` results to `object` before serialization, removing the remaining `Any`-to-serializer warnings in that export block.
- Tightened the remaining `cli.py` monitoring/credential/import-summary seams by importing `StatusReporter` / `StatusLevel` through the typed status-reporter module path, annotating the credential-manager factory with a concrete protocol, explicitly marking ignored return values in compatibility/session/credential cleanup paths, and reusing the existing config-map aliases in the later `config import` summary block.
- Tightened the follow-on `cli.py` warning slice by explicitly assigning the remaining intentional `setdefault(...)` / `pop(...)` return values to `_` and replacing the later configuration-import dry-run literal with an explicit message variable.
- Removed the dead `cli.py` security/session helper seam entirely, including the now-unreferenced helper bodies and their orphaned auth/session protocols, instead of suppressing the warnings around them.
- Tightened the last small active `cli.py` source warnings by making the Timeshift warning render boundary explicit, typing the service-method fallback default value, renaming the unused logging config-dir parameter to reflect intent, and passing `config_dir` through the credential-manager factory.
- Fixed follow-on regressions in the parallel `cli_modules` command refactor by restoring credentials-command access to shared logging/service-manager helpers, matching the local unlock helper signature to its call sites, stopping credential commands when unlock fails, and making the shared `cli_modules` logging/credential-manager helpers actually honor `config_dir`.

## 3. Implementation Notes

- Updated `pyproject.toml`, `README.md`, `docs/DOCUMENTATION-STATUS.md`, `src/TimeLocker/cli_services.py`, `src/TimeLocker/restore_manager.py`
- Updated `src/TimeLocker/cli.py` to remove duplicate package-less command loading.
- Updated `src/TimeLocker/cli.py` validation/import structures with typed change buckets and a typed configuration-module factory return.
- Updated `src/TimeLocker/cli.py` export serialization to use a shared serializer helper and tolerate partial/mock config objects in tests.
- Updated `src/TimeLocker/cli.py` change-summary rendering to use explicit typed buckets and removed stale imports that were no longer referenced after command/helper extraction.
- Updated `src/TimeLocker/cli.py` test compatibility monkeypatch to avoid direct property writes that basedpyright flagged on Click/Typer result objects.
- Updated `src/TimeLocker/cli.py` monkeypatch and helper signatures to reduce unknown-parameter/deprecated-typing noise in the IDE-guided `cli.py` slice.
- Updated `src/TimeLocker/cli.py` builtin test-symbol registration and shell completion config handling to use typed fallback objects and a typed shell-config structure, clearing the IDE-reported blocker slice for completion install/verify paths.
- Updated `src/TimeLocker/cli.py` remaining help/completion messaging, import-command result handling, service-helper typing, and auth-helper protocols to close the systematic `cli.py` cleanup plan without leaving active typed blockers in the edited slice.
- Updated `src/TimeLocker/cli.py` auth/session helper protocols, configuration-module factory typing, and repository-config normalization to remove the final blocker-level IDE findings from the current `cli.py` debt slice.
- Updated `src/TimeLocker/cli.py` repository-credentials command to use a typed credentials payload and explicit helper-boundary casts for credential/config manager protocols.
- Updated `src/TimeLocker/cli.py` credential-manager unlock helper to use an explicit unlock-capable protocol instead of object-typed attribute checks.
- Updated `src/TimeLocker/cli.py` logging/output helper classes with typed override signatures and a typed Rich console attribute, and adjusted the later repository-credentials helper call to align the payload/cast boundary with the helper protocol.
- Updated `src/TimeLocker/cli.py` credential-display formatting to build an explicitly typed table payload before passing it to the output formatter.
- Updated `src/TimeLocker/cli.py` config export/import optional-section handling to cast selections, policies, and schedules to explicit mapping boundaries before serialization.
- Updated `src/TimeLocker/cli.py` export-side `security` and `monitoring` handling to pass explicit object-typed values into `_serialize_config_value(...)`.
- Updated `src/TimeLocker/cli.py` to use a typed monitoring import fallback, a protocol-typed credential-manager factory, explicit `_ = ...` markers for intentionally ignored return values, and `_ConfigObjectMap` / `_ConfigSectionMap` in the later configuration-import summary path.
- Updated `src/TimeLocker/cli.py` to make the remaining repository-export cleanup and later import dry-run message explicit so those warning-only sites no longer rely on implicit concatenation or ignored dict-operation results.
- Updated `src/TimeLocker/cli.py` to delete the unused security/session helper functions and remove the unreferenced auth/session protocol types they had been keeping alive.
- Updated `src/TimeLocker/cli.py` to close the remaining small source-warning seams in the Timeshift warning loop, service-method helper, logging setup signature, and credential-manager factory.
- Updated `src/TimeLocker/cli_modules/commands/credentials.py`, `src/TimeLocker/cli_modules/helpers/service_helpers.py`, and `src/TimeLocker/cli_modules/helpers/logging_setup.py` to repair the reviewed runtime regressions in the command-module migration path.
- Updated `src/TimeLocker/restore_manager.py` to modernize core option/result typing and define explicit recovery-validator/progress-monitor protocols, closing the restore recovery seam that the IDE had previously identified as a higher-debt next target.
- Updated `src/TimeLocker/cli_helpers.py` to use protocol boundaries aligned with the real credential/config implementations while keeping the non-conflicting console fallback.
- Updated `tests/TimeLocker/cli/test_cli_helpers.py` and `tests/TimeLocker/cli/test_store_backend_credentials.py` with typed fixture dictionaries aligned to the helper boundary.
- Added restore parsing coverage in `tests/TimeLocker/recovery/test_restore_manager.py`
- Testing performed:
  - `pytest tests/TimeLocker/recovery/test_restore_manager.py -q`
  - `pytest tests/TimeLocker/cli/test_cli_real_service_integration.py -q`
  - `pytest tests/TimeLocker/cli/test_config_export_import.py -q`
  - `pytest tests/TimeLocker/cli/test_config_export_import.py tests/TimeLocker/cli/test_cli_real_service_integration.py -q`
  - `pytest tests/TimeLocker/cli/test_cli_helpers.py tests/TimeLocker/cli/test_store_backend_credentials.py -q`
  - `pytest tests/TimeLocker/cli/test_config_export_import.py tests/TimeLocker/cli/test_cli_real_service_integration.py tests/TimeLocker/cli/test_cli_helpers.py tests/TimeLocker/cli/test_store_backend_credentials.py -q`
  - `pytest tests/TimeLocker/cli/test_config_export_import.py tests/TimeLocker/cli/test_cli_real_service_integration.py -q`
  - `python -m compileall src/TimeLocker`
  - `python -m compileall src/TimeLocker/cli_helpers.py tests/TimeLocker/cli/test_cli_helpers.py tests/TimeLocker/cli/test_store_backend_credentials.py`
  - `python -m compileall src/TimeLocker/cli.py`
  - `python -m compileall src/TimeLocker/cli.py`
  - `python-agent-ide diagnostics_for_files` on `src/TimeLocker/cli_helpers.py`
  - `python-agent-ide diagnostics_for_change` / `diagnostics_for_files` on `src/TimeLocker/cli.py`
  - `python-agent-ide post_edit_feedback` on `src/TimeLocker/cli.py`
  - additional `python-agent-ide diagnostics_for_change` / `post_edit_feedback` passes on `src/TimeLocker/cli.py` during the systematic follow-up slices
  - additional `python-agent-ide diagnostics_for_change` passes on `src/TimeLocker/cli.py` to confirm the auth/config helper slice reached zero blocker-level findings
  - additional `python-agent-ide diagnostics_for_change` passes on `src/TimeLocker/cli.py` and `src/TimeLocker/cli_helpers.py` to confirm the repository-credentials helper slice stayed blocker-free after restoring the expected boolean credential behavior
  - additional `python-agent-ide diagnostics_for_change` pass on `src/TimeLocker/cli.py` to confirm the lower credential-manager unlock seam no longer reports unknown `is_locked` / `unlock` access
  - additional `python-agent-ide diagnostics_for_change` / `test_impact_with_evidence` passes on `src/TimeLocker/cli.py` to clear the logging/output helper warnings and the next repository-credentials blocker without widening the change slice
  - additional `python-agent-ide diagnostics_for_change` / `test_impact_with_evidence` passes on `src/TimeLocker/cli.py` to clear the credential-display table/list unknown-shape warnings
  - additional `python-agent-ide diagnostics_for_change` / `test_impact_with_evidence` passes on `src/TimeLocker/cli.py` to clear the export/import optional-section loop-variable warnings
  - additional `python-agent-ide diagnostics_for_change` / `test_impact_with_evidence` passes on `src/TimeLocker/cli.py` to clear the export-side `security` / `monitoring` Any-boundary warnings
  - additional `python-agent-ide diagnostics_for_change` pass on `src/TimeLocker/cli.py` to target the remaining monitoring import, credential-manager, ignored-return, and late import-summary warning cluster
  - `python-agent-ide diagnostics_for_change` / `post_edit_feedback` on `src/TimeLocker/restore_manager.py`
  - `pytest tests/TimeLocker/recovery/test_restore_manager.py -q`
  - `pytest tests/TimeLocker/cli/test_config_export_import.py tests/TimeLocker/cli/test_cli_real_service_integration.py tests/TimeLocker/cli/test_cli_helpers.py tests/TimeLocker/cli/test_store_backend_credentials.py -q`
  - `python -c "import importlib; importlib.import_module('TimeLocker.cli')"`
- Follow-up tasks:
  - Reassess whether the remaining lower-priority `cli.py` warnings justify another focused slice or whether the next high-value cleanup should move to a different file
  - Continue consolidating release/documentation claims with validated behavior

## 4. Documentation & Links

- Updated top-level project guidance in `README.md`
- Updated status framing in `docs/DOCUMENTATION-STATUS.md`
- Rules consulted: `AGENT-GUIDE-General-Preferences`, `AGENT-RULE-Documentation-Conventions`, `AGENT-RULE-Testing-Conventions`
- Rules applied: documentation update logging in `docs/updates/`, targeted test coverage for changed behavior, IDE-guided narrowed change slices before editing

# References

- `docs/guides/ai-agent/AGENT-GUIDE-General-Preferences.md`
- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md`
- `docs/guides/ai-agent/AGENT-RULE-Testing-Conventions.md`
