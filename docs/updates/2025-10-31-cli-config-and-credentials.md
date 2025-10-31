# 2025-10-31-cli-config-and-credentials

## Summary

- Expanded CLI config import commands to invoke service manager APIs, added non-interactive safeguards, and exposed shorthand helpers required by UX tests.
- Restored repository credential prompts inside `repos add`, sharing the backend helper and improving feedback.
- Added legacy compatibility shims (combined output helper, built-in aliases, `main`) for tests expecting the historical `TimeLocker` package layout.

## Details

- Updated `config_show`, `config_setup`, and config import subcommands to respect service manager fallbacks, validation panels, and new options such as
  `--config-file` and `--dry-run`.
- Reintroduced interactive credential capture during `repos add` using `store_backend_credentials_helper`, including S3 prompts, unlock handling, and
  warning/success messaging.
- Normalised CLI exports by aliasing to `TimeLocker.cli`, created `_combined_output` helper, and provided `StatusReporter`/`StatusLevel` fallbacks plus legacy
  `main()` entry point for user-experience tests.
- Added README/template/index scaffolding for `docs/updates` and documented the rule and tests consulted (`AGENT-GUIDE-Coding-Standards`,
  `AGENT-RULE-Documentation-Conventions`).

## Validation

- `pytest tests/TimeLocker/cli/test_store_backend_credentials.py`
- `pytest tests/TimeLocker/cli/test_snapshots_commands.py`
- `pytest tests/TimeLocker/cli/test_targets_commands.py`
- `pytest tests/TimeLocker/backup/test_manager.py::test_from_uri_supported_scheme`
- `pytest tests/TimeLocker/cli/test_cli_error_handling.py::TestCLIErrorHandling::test_missing_required_arguments`
- Full suite execution was attempted but blocked by sandbox `Permission denied`; results noted in the task summary.
