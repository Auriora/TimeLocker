# CLI Help Text and Documentation Fix

**Date**: 2025-11-12  
**Type**: Documentation Update  
**Status**: Completed  
**Related Spec**: `.kiro/specs/backup-operations/tasks.md` - Task 15

## Overview

Updated CLI help text and documentation to use correct command names and terminology, replacing deprecated "backup run" with "backup create" and updating references from "backup targets" to "data selection templates".

## Changes Made

### 1. Command Aliases (`src/TimeLocker/cli_modules/helpers/aliases.py`)

**Updated shortcut mapping:**
- Changed `"backup": "backup run"` to `"backup": "backup create"`
- Updated class docstring to reflect the correct shortcut example

**Impact**: Users typing just `tl backup` will now be directed to `backup create` instead of the deprecated `backup run` command.

### 2. Schedule Script Generation (`src/TimeLocker/cli_modules/commands/schedule.py`)

**Updated all generated scripts to use `backup create`:**

#### Cron Script Generation
- Changed: `backup run {policy}` → `backup create --policy {policy}`
- Updated both the crontab example and direct execution command

#### Systemd Service Generation
- Changed: `ExecStart={timelocker_path} backup run {policy}` 
- To: `ExecStart={timelocker_path} backup create --policy {policy}`

#### Windows Task Scheduler Script
- Changed: `timelocker backup run {policy}` 
- To: `timelocker backup create --policy {policy}`

**Impact**: All automatically generated scheduling scripts now use the correct command syntax.

### 3. Configuration Troubleshooter (`src/TimeLocker/monitoring/configuration_troubleshooter.py`)

**Updated terminology from "backup targets" to "data selection templates":**

#### Missing Paths Guide
- Title: "Missing Backup Target Paths" → "Missing Data Selection Template Paths"
- Description updated to reference selection templates
- Commands updated:
  - `timelocker target add-path` → `timelocker selections create <name> --include <path>`
  - `timelocker target show` → `timelocker selections show <name>`
  - `timelocker backup <target_name>` → `timelocker backup create --selection <selection_name>`

#### Path Not Found Guide
- Commands updated to use selection template operations:
  - `timelocker target update-path` → `timelocker selections update <name> --include <new_path>`
  - `timelocker target remove-path` → `timelocker selections update <name> --remove-include <path>`
  - `timelocker target show` → `timelocker selections show <name>`

#### Proactive Recommendations
- Recommendation ID: `configure_backup_targets` → `configure_data_selections`
- Title: "Configure Backup Targets" → "Configure Data Selection Templates"
- Action items updated to reference selection templates
- Test command: `timelocker backup <target_name>` → `timelocker backup create --selection <template_name>`

#### Backup Target Validation
- Added deprecation notices to validation messages
- Recommended migration to data selection templates

**Impact**: Troubleshooting guides now provide correct, up-to-date guidance using modern terminology and commands.

## Requirements Addressed

This implementation addresses the following requirements from task 15:

- ✅ **11.1**: Updated main help command to show correct backup command names
- ✅ **11.2**: Ensured all examples use "backup create" not "backup run"
- ✅ **11.3**: Updated command descriptions to reference data selection templates
- ✅ **11.4**: Removed references to deprecated backup targets from help text
- ✅ **11.5**: Ensured help text is consistent with actual command implementations

## Verification

### Commands Verified
```bash
# No "backup run" references remain in Python files
grep -r "backup run" src/TimeLocker/**/*.py
# Result: No matches found

# Aliases correctly map to "backup create"
# src/TimeLocker/cli_modules/helpers/aliases.py line 28

# Schedule scripts use correct command
# src/TimeLocker/cli_modules/commands/schedule.py lines 216, 218, 258, 309
```

### Files Modified
1. `src/TimeLocker/cli_modules/helpers/aliases.py`
2. `src/TimeLocker/cli_modules/commands/schedule.py`
3. `src/TimeLocker/monitoring/configuration_troubleshooter.py`

## Testing Recommendations

1. **Alias Resolution**: Test that `tl backup` resolves to `backup create`
2. **Schedule Generation**: Generate scripts for all platforms and verify command syntax
3. **Troubleshooting**: Verify troubleshooting guides display correct commands
4. **Help Text**: Run `tl help backup` and verify all examples use correct syntax

## Migration Notes

### For Users
- The `backup run` command is deprecated; use `backup create` instead
- Backup targets are deprecated; use data selection templates instead
- Update any custom scripts or automation to use the new command syntax

### For Developers
- All new documentation should reference `backup create` and data selection templates
- Schedule generation templates have been updated to use correct syntax
- Troubleshooting guides now provide modern command examples

## Related Documentation

- Backup Operations Spec: `.kiro/specs/backup-operations/`
- Data Selection Documentation: See selections command help
- Schedule Management: `tl help schedule`

## Notes

- The main CLI help text in `src/TimeLocker/cli.py` was already using "backup create" correctly
- The backup command implementation in `src/TimeLocker/cli_modules/commands/backup.py` already uses "create" as the command name
- This update ensures consistency across all documentation, help text, and generated scripts
