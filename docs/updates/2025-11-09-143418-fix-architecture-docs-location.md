---
title: "Fix Architecture Documentation Location"
date: "2025-11-09"
type: "documentation"
status: "completed"
tags: ["documentation", "architecture", "steering", "cleanup"]
---

# Fix Architecture Documentation Location

**Date**: 2025-11-09  
**Type**: Documentation Cleanup  
**Status**: Completed

## Summary

Corrected the placement of documentation files that were incorrectly created in non-standard folders:
- Architecture docs in `docs/architecture/` → moved to `docs/2-architecture/`
- Task/prompt files in `docs/tasks/` → moved to `docs/0-project-management/`

Updated steering documentation to prevent this from happening again.

## Problem

Documentation files were created in non-standard folders:

1. **Architecture docs in `docs/architecture/`:**
   - `file-locations-review.md`
   - `SUMMARY-path-review.md`
   - `test-isolation-strategy.md`

2. **Task/prompt files in `docs/tasks/`:**
   - 7 task and prompt files for test fixes

This violated the established documentation structure which uses:
- `docs/2-architecture/` for architecture documentation
- `docs/0-project-management/` for task and project tracking

## Changes Made

### 1. Moved and Reformatted Files

Moved all three files to `docs/2-architecture/` and reformatted them according to the ADR template:

- `docs/architecture/file-locations-review.md` → `docs/2-architecture/file-locations-review.md`
- `docs/architecture/SUMMARY-path-review.md` → `docs/2-architecture/path-review-summary.md`
- `docs/architecture/test-isolation-strategy.md` → `docs/2-architecture/test-isolation-strategy.md`

Each file now includes:
- Proper YAML frontmatter with ADR metadata
- Structured sections following the template
- Cross-references to related documents
- Proper tags and ownership information

### 2. Updated Steering Documentation

Updated `.kiro/steering/documentation-conventions.md` to be more explicit:

**Added explicit warnings:**
```markdown
- Do NOT create ad-hoc directories like `docs/progress/`, `docs/architecture/`, 
  or any other non-standard folders - use the established structure.
- **IMPORTANT**: Architecture documentation MUST go in `docs/2-architecture/`, 
  NOT `docs/architecture/`.
```

**Updated content guidelines:**
```markdown
- Architecture/service design changes → `docs/2-architecture/` (NOT `docs/architecture/`)
```

### 3. Updated AI Agent Documentation

Fixed references in `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md`:
- Changed `docs/architecture/implementation.md` references to `docs/2-architecture/`
- Added explicit note: `(NOT docs/architecture/)`

### 4. Cleanup

- Deleted the incorrect `docs/architecture/` folder
- Verified no remaining references to the old path

## Files Modified

- `.kiro/steering/documentation-conventions.md` - Added explicit warnings about `docs/architecture/` and `docs/tasks/`
- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` - Fixed references
- `docs/2-architecture/file-locations-review.md` - Created with proper structure
- `docs/2-architecture/path-review-summary.md` - Created with proper structure
- `docs/2-architecture/test-isolation-strategy.md` - Created with proper structure

## Files Moved

Moved task/prompt files from `docs/tasks/` to `docs/0-project-management/`:
- `PROMPT-fix-targets-selections.md` → `task-fix-targets-selections.md`
- `PROMPT-fix-cli-integration-tests.md` → `task-fix-cli-integration-tests.md`
- `fix-targets-to-selections-tests.md` → `task-fix-targets-to-selections-tests.md`
- `PROMPT-fix-configuration-tests.md` → `task-fix-configuration-tests.md`
- `README-test-fixes.md` → `test-fixes-index.md`
- `PROMPT-fix-store-credentials-tests.md` → `task-fix-store-credentials-tests.md`
- `PROMPT-fix-integration-backend-tests.md` → `task-fix-integration-backend-tests.md`

Moved developer guide from `docs/guides/` to `docs/guides/developer/`:
- `test-isolation-quick-reference.md` → `developer/test-isolation-quick-reference.md`

## Files Deleted

- `docs/architecture/file-locations-review.md`
- `docs/architecture/SUMMARY-path-review.md`
- `docs/architecture/test-isolation-strategy.md`
- `docs/architecture/` (directory)
- `docs/tasks/` (directory - files moved to `docs/0-project-management/`)

## Verification

- ✅ All architecture docs now in `docs/2-architecture/`
- ✅ All task/prompt files now in `docs/0-project-management/`
- ✅ Developer guides now in `docs/guides/developer/`
- ✅ All architecture files follow ADR template structure
- ✅ No references to `docs/architecture/` remain
- ✅ Steering documentation updated with explicit guidance
- ✅ All incorrect folders removed (`docs/architecture/` and `docs/tasks/`)
- ✅ All files in correct subdirectories

## Prevention

The steering documentation now includes:
1. Explicit prohibition of `docs/architecture/` and `docs/tasks/` folders
2. Clear guidance to use `docs/2-architecture/` for architecture docs
3. Clear guidance to use `docs/0-project-management/` for task tracking
4. Examples in multiple sections
5. Updated PR checklist

This should prevent AI agents from creating incorrect folder structures in the future.

## Related Documents

- [Documentation Conventions](../../.kiro/steering/documentation-conventions.md)
- [File Locations Review](../2-architecture/file-locations-review.md)
- [Path Review Summary](../2-architecture/path-review-summary.md)
- [Test Isolation Strategy](../2-architecture/test-isolation-strategy.md)

## Rules Applied

- **documentation-conventions.md** (Priority 20): Enforced standard documentation structure
- **operational-best-practices.md** (Priority 40): Documentation consistency requirement
- **general-preferences.md** (Priority 50): Single source of truth principle


## Link Fixes

Fixed 24 broken documentation links (from 57 to 33 remaining):

**Fixed Links:**
- Updated all references from `docs/architecture/` to `docs/2-architecture/`
- Updated all references from `docs/tasks/` to `docs/0-project-management/`
- Fixed CLI refactoring phase 1 links to use correct filename `2025-11-07-093135-cli-refactoring-phase1.md`
- Fixed CLI refactoring plan links to point to `docs/archive/cli-refactoring/`
- Fixed steering documentation links to use correct relative paths (`../../../.kiro/steering/`)
- Made update file references canonical with `./` prefix

**Remaining Broken Links (33):**
Most remaining broken links are in archived documentation and reference files that don't exist:
- Test documentation files in `docs/4-testing/` and `docs/archive/` (11 links)
- Missing implementation documentation files (3 links)
- Source code README files (2 links)
- Other archived/historical references (17 links)

These remaining links should be addressed when/if the referenced files are created or the documentation is updated.
