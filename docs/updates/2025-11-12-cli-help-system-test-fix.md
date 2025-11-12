# CLI Targets to Selections Migration - Test Updates

**Date**: 2025-11-12  
**Type**: Test Fix & Code Update  
**Component**: CLI Tests & Commands  
**Status**: Complete

## Overview

Completed migration from 'targets' to 'selections' terminology across all tests and CLI commands. The 'targets' functionality has been fully replaced with 'selections' (data selection system), removing all backward compatibility references as requested.

## Changes Made

### Test Updates

1. **tests/TimeLocker/cli/test_cli_help_system.py**:
   - **test_main_help_output_quality**: Changed expected command group from 'targets' to 'selections'
   - **test_command_group_help_completeness**: Updated command groups list to use 'selections' instead of 'targets'
   - **test_command_discovery**: Updated command groups list to use 'selections' instead of 'targets'
   - **test_error_message_helpfulness**: Changed error scenario from `["targets", "show"]` to `["selections", "show"]`

2. **tests/TimeLocker/cli/test_cli_error_handling.py**:
   - **test_invalid_subcommand_error**: Changed 'targets' to 'selections'
   - **test_missing_required_arguments**: Updated from `["targets", "show"]` and `["targets", "remove"]` to `["selections", "show"]` and `["selections", "delete"]`
   - **test_empty_input_handling**: Changed `["targets", "add", "", "--path", "/tmp"]` to `["selections", "create", "", "--paths", "/tmp"]`
   - **test_very_long_input_handling**: Changed `["targets", "add", ...]` to `["selections", "create", ...]`

3. **tests/TimeLocker/cli/test_config_export_import.py**:
   - **test_config_export_config_help**: Updated assertion from `--targets` to `--selections`

4. **tests/TimeLocker/cli_modules/testing/test_testing_utilities.py**:
   - **test_create_test_config**: Updated assertion from `'targets'` to `'selections'`

### Code Updates

1. **src/TimeLocker/cli.py** - `config_export_config` command:
   - Changed parameter from `include_targets` to `include_selections`
   - Updated option from `--targets/--no-targets` to `--selections/--no-selections`
   - Updated help text from "backup target configurations" to "data selection configurations"
   - Changed internal logic from `config.backup_targets` to `config.data_selections`
   - Updated export data key from `"backup_targets"` to `"data_selections"`
   - Updated summary output from "targets" to "selections"
   - Updated docstring examples from `--no-targets` to `--no-selections`

2. **src/TimeLocker/cli_modules/testing/fixtures.py** - `create_test_config` function:
   - Changed parameter from `targets` to `selections`
   - Updated docstring from "backup target configurations" to "data selection configurations"
   - Changed config dictionary key from `'targets'` to `'selections'`

### Tests Already Properly Handled

- **tests/TimeLocker/cli/test_cli_integration.py**: Two tests already marked as skipped with clear reasons:
  - `test_backup_target_management_workflow`: Skipped with reason "Targets deprecated - replaced by selections"
  - `test_first_time_user_workflow`: Skipped with reason "Targets deprecated - replaced by selections"

## Test Results

All updated tests now pass:
- **test_cli_help_system.py**: 18 passed, 1 skipped
- **test_cli_error_handling.py**: 15 passed, 1 skipped
- **test_config_export_import.py**: All export help tests pass
- **test_testing_utilities.py**: All fixture tests pass

## Related

- The 'targets' command group was removed as part of the data selection refactoring
- The new 'selections' command group provides enhanced data selection capabilities
- No backward compatibility with 'targets' is maintained per user request
- See `docs/updates/2025-11-12-selections-cli-implementation.md` for details on the selections implementation

## Rules Consulted

- `coding-standards.md` (Priority 100): Comprehensive testing requirements
- `operational-best-practices.md` (Priority 40): Test alignment with current implementation
- `testing-conventions.md` (Priority 25): Test organization and best practices
