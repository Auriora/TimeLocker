---
title: "Gap Analysis: Snapshots vs Restore Command Namespaces"
type: [ report, analysis ]
status: [ draft ]
created: "2025-11-11"
owner: "CLI Team"
tags: [cli, command-structure, gap-analysis, recovery-operations]
---

# Gap Analysis: Snapshots vs Restore Command Namespaces

## Executive Summary

This analysis reviews Option 1 (separate `snapshots` and `restore` namespaces) against all TimeLocker specifications to identify gaps, inconsistencies, and design considerations. The analysis reveals that **the current implementation has a fundamental mismatch** between the CLI Interface requirements (which specify a `restore` namespace) and the implemented command hierarchy (which consolidates everything under `snapshots`).

## Current State

### Implemented Command Hierarchy (docs/reference/timelocker-cli-command-hierarchy.md)

```
snapshots/
├── list|ls                     # List snapshots from configured repos
├── show <id>                   # Show snapshot details
├── contents <id>               # List contents of snapshot
├── restore <id> <target>       # Restore snapshot
├── mount <id> <path>           # Mount snapshot
├── umount <id>                 # Unmount snapshot
├── find-in <id> <pattern>      # Search within a snapshot
├── forget <id>                 # Remove snapshot
├── prune                       # Retention across repositories
├── diff <id1> <id2>            # Compare snapshots
└── find <pattern>              # Search across repositories
```

### Required Command Structure (CLI Interface Requirements - Requirement 13)

```
restore/
├── browse <repository> <snapshot-id>           # Explore snapshot contents
├── files <repository> <snapshot-id> <paths>    # Selective file restoration
├── full <repository> <snapshot-id> <target>    # Complete snapshot restoration
├── mount <repository> <snapshot-id> <mountpoint> # Mount snapshots as filesystems
├── find <repository> <query>                   # Search files across snapshots
├── diff <repository> <snapshot-a> <snapshot-b> # Compare snapshots
├── list <repository>                           # Display available snapshots
└── verify <target>                             # Validate restored data integrity
```

## Gap Analysis

### Gap 1: Missing `restore` Namespace Entirely

**Severity**: Critical  
**Specification**: 
- **CLI Interface Requirements - Requirement 13** (`.kiro/specs/cli-interface/requirements.md`)
- User Story: "As a backup administrator, I want specific CLI commands for recovery operations..."

**Issue**: The CLI Interface requirements explicitly define a `restore` namespace with 8 specific commands for recovery operations. The current implementation has NO `restore` namespace at all.

**Impact**:
- Direct violation of CLI Interface Requirements Requirement 13
- Users expecting `tl restore browse` will encounter command not found errors
- Documentation inconsistency between requirements and implementation
- Automation scripts based on requirements will fail

**Required Commands Missing**:
- `restore browse` - Not implemented
- `restore files` - Not implemented  
- `restore full` - Not implemented
- `restore verify` - Not implemented (critical for data integrity)

### Gap 2: Parameter Signature Mismatch

**Severity**: High  
**Specification**: 
- **CLI Interface Requirements - Requirement 13** (`.kiro/specs/cli-interface/requirements.md`)
- Acceptance Criteria 1-8: All restore commands specify explicit `<repository>` parameter

**Issue**: Commands that exist have different parameter signatures:

| Requirement | Implementation | Issue |
|------------|----------------|-------|
| `restore browse <repository> <snapshot-id>` | `snapshots contents <id>` | Missing explicit repository parameter |
| `restore files <repository> <snapshot-id> <paths>` | `snapshots restore <id> <target>` | Different semantics - no selective paths |
| `restore full <repository> <snapshot-id> <target>` | `snapshots restore <id> <target>` | Conflated with selective restore |
| `restore list <repository>` | `snapshots list` | Missing explicit repository scoping |

**Impact**:
- Cannot specify repository explicitly in many commands
- Ambiguity between full and selective restoration
- Inconsistent with multi-repository workflows
- Violates principle of explicit over implicit

### Gap 3: Missing Recovery Verification

**Severity**: Critical  
**Specification**: 
- **CLI Interface Requirements - Requirement 13** (`.kiro/specs/cli-interface/requirements.md`)
  - Acceptance Criteria 8: "THE TimeLocker System SHALL provide `timelocker restore verify <target>` command for validating restored data integrity"
- **Recovery Operations Requirements - Requirement 4** (`.kiro/specs/recovery-operations/requirements.md`)
  - User Story: "As a backup administrator, I want to verify restored data integrity..."
  - Acceptance Criteria 1: "THE TimeLocker System SHALL verify restored file integrity by comparing checksums with snapshot metadata"
  - Acceptance Criteria 2: "WHEN restoration completes, THE TimeLocker System SHALL provide a verification report showing successful and failed restorations"

**Issue**: No `restore verify <target>` command exists to validate restored data integrity.

**Impact**:
- Cannot verify restored data matches original backup
- Violates Recovery Operations Requirement 4 acceptance criteria
- No way to detect corruption or incomplete restorations
- Critical for compliance and data integrity assurance

**Recovery Operations Requirement 4 states**:
> "THE TimeLocker System SHALL verify restored file integrity by comparing checksums with snapshot metadata"

### Gap 4: Semantic Confusion Between Management and Recovery

**Severity**: Medium  
**Specification**: 
- **Recovery Operations Design** (`.kiro/specs/recovery-operations/design.md`)
  - Architecture section: Defines separate components for RecoveryOrchestrator, SnapshotBrowser, RecoveryValidator
- **CLI Interface Requirements - Requirement 13** (`.kiro/specs/cli-interface/requirements.md`)
  - Defines separate `restore` namespace for recovery operations

**Issue**: The current `snapshots` namespace conflates two distinct concerns:
1. **Snapshot Management**: List, show, forget, prune (lifecycle operations)
2. **Recovery Operations**: Browse, restore, mount, verify (data recovery)

**Design Principle Violation**:
The Recovery Operations Design document explicitly separates:
- **Snapshot Browser** - exploration capabilities
- **Recovery Orchestrator** - restoration operations  
- **Recovery Validator** - integrity verification

Mixing these in one namespace violates separation of concerns.

**Impact**:
- Unclear command purpose (is `snapshots` about managing or recovering?)
- Difficult to extend recovery features without cluttering snapshot management
- Inconsistent with internal architecture design
- Poor discoverability for users focused on recovery workflows

### Gap 5: Missing Selective File Restoration

**Severity**: High  
**Specification**: 
- **CLI Interface Requirements - Requirement 13** (`.kiro/specs/cli-interface/requirements.md`)
  - Acceptance Criteria 2: "THE TimeLocker System SHALL provide `timelocker restore files <repository> <snapshot-id> <paths>` command for selective file restoration"
- **Recovery Operations Requirements - Requirement 3** (`.kiro/specs/recovery-operations/requirements.md`)
  - User Story: "As a backup administrator, I want to perform selective file restoration..."
  - Acceptance Criteria 1: "THE TimeLocker System SHALL support selective restoration of individual files and directories from snapshots"
  - Acceptance Criteria 2: "WHEN selecting files for restoration, THE TimeLocker System SHALL allow multiple selection using patterns and filters"

**Issue**: No command for selective file restoration with multiple file paths.

**Current**: `snapshots restore <id> <target>` - appears to be full restore only  
**Required**: `restore files <repository> <snapshot-id> <paths>` - selective with multiple paths

**Recovery Operations Requirement 3 states**:
> "THE TimeLocker System SHALL support selective restoration of individual files and directories from snapshots"
> "WHEN selecting files for restoration, THE TimeLocker System SHALL allow multiple selection using patterns and filters"

**Impact**:
- Cannot restore specific files without restoring entire snapshot
- Inefficient for large snapshots when only few files needed
- Violates Recovery Operations Requirement 3 acceptance criteria

### Gap 6: Repository Scoping Inconsistency

**Severity**: Medium  
**Specification**: 
- **CLI Interface Requirements - Requirement 13** (`.kiro/specs/cli-interface/requirements.md`)
  - All 8 acceptance criteria specify explicit `<repository>` as first parameter
  - Example: "THE TimeLocker System SHALL provide `timelocker restore browse <repository> <snapshot-id>` command..."

**Issue**: Requirements specify explicit `<repository>` parameter for all restore commands, but implementation relies on implicit repository resolution.

**Current Behavior** (from command hierarchy docs):
> "Snapshot commands default to **all** repositories; specify `--repository` to scope to one repository."

**Required Behavior**: Explicit repository parameter as first argument for all restore commands.

**Impact**:
- Ambiguity in multi-repository environments
- Difficult to script operations for specific repositories
- Inconsistent with explicit design principle
- May cause unintended operations across wrong repositories

### Gap 7: Missing Data Selection Integration

**Severity**: Medium  
**Specification**: 
- **Recovery Operations Requirements - Requirement 7** (`.kiro/specs/recovery-operations/requirements.md`)
  - User Story: "As a backup administrator, I want to reuse data selection templates during recovery operations..."
  - Acceptance Criteria 1: "THE TimeLocker System SHALL integrate with the Data Selection system to retrieve and apply selection templates during recovery operations"
  - Acceptance Criteria 2: "WHEN performing selective restoration, THE TimeLocker System SHALL allow selection of files using existing selection templates and pattern groups"

**Issue**: No integration with Data Selection system for recovery operations.

**Recovery Operations Requirement 7 states**:
> "THE TimeLocker System SHALL integrate with the Data Selection system to retrieve and apply selection templates during recovery operations"
> "WHEN performing selective restoration, THE TimeLocker System SHALL allow selection of files using existing selection templates and pattern groups"

**Impact**:
- Cannot reuse selection templates for consistent backup/restore criteria
- Manual pattern specification required for each restore
- Violates DRY principle for selection criteria
- Inconsistent with Data Selection integration design

### Gap 8: Missing Recovery Progress and Monitoring

**Severity**: Low  
**Specification**: 
- **Recovery Operations Requirements - Requirement 5** (`.kiro/specs/recovery-operations/requirements.md`)
  - User Story: "As a backup administrator, I want to monitor recovery progress..."
  - Acceptance Criteria 1: "THE TimeLocker System SHALL provide real-time progress information during recovery operations"
  - Acceptance Criteria 2: "WHEN restoration is running, THE TimeLocker System SHALL display files processed, data transferred, and estimated completion time"

**Issue**: No explicit commands or options for recovery progress monitoring.

**Recovery Operations Requirement 5 states**:
> "THE TimeLocker System SHALL provide real-time progress information during recovery operations"
> "WHEN restoration is running, THE TimeLocker System SHALL display files processed, data transferred, and estimated completion time"

**Note**: This may be implemented at the service layer, but CLI interface should expose it.

**Impact**:
- Users cannot track long-running restore operations
- No estimated completion time for large restores
- Difficult to diagnose slow or stalled operations

## Specification Alignment Analysis

### ✅ Aligned Specifications

1. **Repository Management** - No conflicts, repository operations are separate
2. **Backup Operations** - No conflicts, backup namespace is separate
3. **Policy Management** - No conflicts, policy namespace is separate
4. **Data Selection** - No conflicts, selections namespace is separate
5. **Security Services** - No conflicts, credentials namespace is separate

### ❌ Misaligned Specifications

1. **CLI Interface Requirements - Requirement 13** (`.kiro/specs/cli-interface/requirements.md`): Complete mismatch
   - Specifies `restore` namespace with 8 commands
   - Implementation has 0 commands in `restore` namespace
   - All recovery operations incorrectly placed in `snapshots`
   - **Affected Acceptance Criteria**: All 8 (AC1-AC8)

2. **Recovery Operations Requirements** (`.kiro/specs/recovery-operations/requirements.md`): Partial implementation
   - **Requirement 1** (Browsing): Partially met via `snapshots contents` - wrong namespace
   - **Requirement 2** (Full restoration): Unclear if `snapshots restore` is full or selective
   - **Requirement 3** (Selective restoration): Not met - no multi-file selection (AC1, AC2 violated)
   - **Requirement 4** (Verification): Not met - no verify command (AC1, AC2 violated)
   - **Requirement 5** (Progress monitoring): Unknown - needs verification (AC1, AC2 need validation)
   - **Requirement 6** (Repository integration): Partially met - implicit repository resolution
   - **Requirement 7** (Data Selection integration): Not met - no template support (AC1, AC2 violated)
   - **Requirement 8** (Multi-tool support): Unknown - needs verification
   - **Requirement 9** (Error handling): Unknown - needs verification

3. **Recovery Operations Design** (`.kiro/specs/recovery-operations/design.md`): Architectural mismatch
   - Design separates Browser, Orchestrator, Validator components
   - CLI conflates all into single `snapshots` namespace
   - Violates separation of concerns principle

## Option 1 Evaluation: Separate Namespaces

### Proposed Structure

```
snapshots/                          # Snapshot Management
├── list|ls                         # List snapshots
├── show <id>                       # Show snapshot details
├── forget <id>                     # Remove snapshot
├── prune                           # Apply retention policies
├── diff <id1> <id2>                # Compare snapshots
└── find <pattern>                  # Search across snapshots

restore/                            # Recovery Operations
├── browse <repository> <snapshot-id>           # Explore contents
├── files <repository> <snapshot-id> <paths>    # Selective restoration
├── full <repository> <snapshot-id> <target>    # Full restoration
├── mount <repository> <snapshot-id> <mountpoint> # Mount snapshot
├── umount <snapshot-id>                        # Unmount snapshot
├── find <repository> <query>                   # Search files
├── diff <repository> <snapshot-a> <snapshot-b> # Compare for recovery
├── list <repository>                           # List available snapshots
└── verify <target>                             # Verify restored data
```

### Advantages

1. **✅ Full Specification Compliance**
   - Matches CLI Interface Requirements Requirement 13 exactly
   - Aligns with Recovery Operations architecture design
   - Implements all required recovery commands

2. **✅ Clear Separation of Concerns**
   - `snapshots` = lifecycle management (list, forget, prune)
   - `restore` = data recovery operations (browse, restore, verify)
   - Matches internal architecture (Browser, Orchestrator, Validator)

3. **✅ Explicit Repository Scoping**
   - All restore commands take explicit `<repository>` parameter
   - No ambiguity in multi-repository environments
   - Better for scripting and automation

4. **✅ Extensibility**
   - Easy to add recovery-specific features without cluttering snapshot management
   - Clear namespace for recovery monitoring and reporting
   - Supports future recovery workflow enhancements

5. **✅ User Experience**
   - Clear intent: "I want to restore data" → `tl restore`
   - Intuitive command discovery
   - Matches user mental model (manage snapshots vs recover data)

### Disadvantages

1. **⚠️ Command Duplication**
   - `snapshots list` vs `restore list` - different purposes but similar names
   - `snapshots diff` vs `restore diff` - same operation, different contexts
   - `snapshots find` vs `restore find` - overlapping functionality
   - **Mitigation**: Different contexts make this acceptable; help text clarifies usage

2. **~~Migration Complexity~~** ✅ **NOT APPLICABLE**
   - ~~Existing users may have scripts using `snapshots restore`~~
   - **Status**: No existing users, product not yet released
   - **Impact**: Zero migration risk, clean implementation possible

3. **⚠️ Increased Command Count**
   - More commands to learn and document
   - Larger help output and completion lists
   - Potential confusion about which namespace to use
   - **Mitigation**: Clear documentation and help text; separation improves discoverability

### Gaps Resolved by Option 1

| Gap | Resolution |
|-----|-----------|
| Gap 1: Missing restore namespace | ✅ Fully resolved - restore namespace created |
| Gap 2: Parameter mismatch | ✅ Fully resolved - explicit repository parameters |
| Gap 3: Missing verification | ✅ Fully resolved - `restore verify` command |
| Gap 4: Semantic confusion | ✅ Fully resolved - clear separation |
| Gap 5: Selective restoration | ✅ Fully resolved - `restore files` with paths |
| Gap 6: Repository scoping | ✅ Fully resolved - explicit repository parameter |
| Gap 7: Data Selection integration | ⚠️ Partially resolved - needs `--selection` option |
| Gap 8: Progress monitoring | ⚠️ Needs verification - should be in all restore commands |

### Remaining Work for Option 1

1. **Implement Missing Commands**
   - `restore browse` - snapshot content exploration
   - `restore files` - selective multi-file restoration
   - `restore full` - explicit full restoration
   - `restore verify` - post-restoration integrity check

2. **Add Data Selection Integration**
   - `--selection <template>` option for `restore files`
   - Integration with Data Selection system
   - Pattern group support for recovery

3. **Enhance Progress Monitoring**
   - Real-time progress display for all restore commands
   - Estimated completion time
   - Transfer rate and file count tracking

4. **Migration Support**
   - Deprecation warnings for `snapshots restore`
   - Alias support during transition period
   - Updated documentation and migration guide

5. **Command Disambiguation**
   - Clear documentation on when to use `snapshots` vs `restore`
   - Help text explaining the distinction
   - Examples for common workflows

## Recommendations

### Primary Recommendation: Implement Option 1 Immediately

**Status**: ✅ **NO EXISTING USERS** - Product not yet released, zero migration risk

**Rationale**:
1. **Specification Compliance**: Option 1 is the ONLY way to comply with CLI Interface Requirements Requirement 13
2. **Architectural Alignment**: Matches Recovery Operations design separation of concerns
3. **User Experience**: Clearer intent and better discoverability
4. **Extensibility**: Easier to add recovery features without namespace pollution
5. **Clean Implementation**: No backward compatibility burden, can implement correctly from day one

### Implementation Approach

#### Phase 1: Implement Restore Namespace (Immediate - High Priority)
1. Create `restore` namespace with all 8 required commands
2. Add explicit repository parameters to all commands
3. Implement `restore verify` for data integrity validation
4. Add Data Selection integration (`--selection` option)
5. Implement progress monitoring for all restore operations

#### Phase 2: Refactor Snapshots Namespace (Immediate - High Priority)
1. Remove `restore` command from `snapshots` namespace
2. Keep only snapshot management commands (list, show, forget, prune, diff, find)
3. Ensure clear separation between management and recovery operations
4. Update internal routing and command registration

#### Phase 3: Documentation and Testing (Immediate - High Priority)
1. Update command hierarchy documentation
2. Update all CLI documentation and examples
3. Create comprehensive tests for all restore commands
4. Update quickstart guides and tutorials
5. Verify all specification requirements are met

#### Phase 4: Enhanced Features (Post-Implementation - Medium Priority)
1. Add advanced recovery workflows
2. Implement recovery reporting and analytics
3. Add recovery operation scheduling
4. Enhance progress monitoring with detailed metrics

### ~~Alternative: Hybrid Approach~~ NOT NEEDED

~~If migration concerns are significant...~~

**Status**: Migration concerns are NOT applicable - no existing users. Implement the correct architecture directly without compromise.

## Conclusion

The current implementation has **critical gaps** that violate CLI Interface Requirements and Recovery Operations specifications. Option 1 (separate namespaces) is the correct architectural approach that:

1. ✅ Achieves full specification compliance
2. ✅ Aligns with internal architecture design
3. ✅ Provides clear separation of concerns
4. ✅ Improves user experience and discoverability
5. ✅ Enables future extensibility
6. ✅ **Zero migration risk** - no existing users

~~The main challenge is migration~~ **There is NO migration challenge** - the product has not been released yet, so we can implement the correct architecture immediately without any backward compatibility concerns.

**Recommendation**: **Implement Option 1 immediately** - This is the ideal time to fix the non-compliance before release. With no existing users, we have a clean slate to establish the correct command structure that will serve users well for the lifetime of the product.

## References

- CLI Interface Requirements: `.kiro/specs/cli-interface/requirements.md` - Requirement 13
- CLI Interface Design: `.kiro/specs/cli-interface/design.md`
- Recovery Operations Requirements: `.kiro/specs/recovery-operations/requirements.md`
- Recovery Operations Design: `.kiro/specs/recovery-operations/design.md`
- Command Hierarchy: `docs/reference/timelocker-cli-command-hierarchy.md`
- Repository Management Requirements: `.kiro/specs/repository-management/requirements.md`
- Backup Operations Requirements: `.kiro/specs/backup-operations/requirements.md`
