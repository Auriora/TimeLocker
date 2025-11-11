---
title: "Snapshots vs Restore Command Namespace Analysis"
date: "2025-11-11"
type: [ update, analysis ]
status: [ completed ]
tags: [cli, command-structure, recovery-operations, gap-analysis]
related_specs: [cli-interface, recovery-operations]
---

# Snapshots vs Restore Command Namespace Analysis

## Summary

Analyzed the current CLI command structure against all TimeLocker specifications to determine if the `snapshots` command should be replaced with `restore` or if both should coexist. **Finding: The specifications require BOTH namespaces with distinct purposes.**

## Key Findings

### Critical Gap Identified

The current implementation violates **CLI Interface Requirements - Requirement 13**, which explicitly specifies a `restore` namespace with 8 commands for recovery operations. Currently:

- ❌ NO `restore` namespace exists
- ❌ Recovery operations incorrectly placed in `snapshots` namespace  
- ❌ Missing critical commands: `restore verify`, `restore files`, `restore browse`
- ❌ Parameter signatures don't match requirements (missing explicit repository parameters)

### Specification Requirements

**CLI Interface Requirements (Requirement 13)** specifies:
```
restore/
├── browse <repository> <snapshot-id>
├── files <repository> <snapshot-id> <paths>
├── full <repository> <snapshot-id> <target>
├── mount <repository> <snapshot-id> <mountpoint>
├── find <repository> <query>
├── diff <repository> <snapshot-a> <snapshot-b>
├── list <repository>
└── verify <target>
```

**Current Implementation** has:
```
snapshots/
├── list, show, contents, restore, mount, umount
├── find-in, forget, prune, diff, find
└── (no restore namespace at all)
```

## Recommended Solution: Option 1 - Separate Namespaces

### Proposed Structure

**`snapshots/` - Snapshot Lifecycle Management**
- `list` - List snapshots
- `show` - Show snapshot details
- `forget` - Remove snapshots
- `prune` - Apply retention policies
- `diff` - Compare snapshots
- `find` - Search across snapshots

**`restore/` - Data Recovery Operations**
- `browse` - Explore snapshot contents
- `files` - Selective file restoration
- `full` - Complete snapshot restoration
- `mount` - Mount snapshot as filesystem
- `umount` - Unmount snapshot
- `find` - Search files for recovery
- `diff` - Compare snapshots for recovery
- `list` - List available snapshots
- `verify` - Verify restored data integrity

### Rationale

1. **Specification Compliance**: Only way to meet CLI Interface Requirements Requirement 13
2. **Separation of Concerns**: Matches Recovery Operations architecture design
3. **Clear Intent**: `snapshots` = manage, `restore` = recover data
4. **Extensibility**: Easy to add recovery features without cluttering snapshot management
5. **User Experience**: Better discoverability and intuitive command structure

### Critical Gaps Resolved

| Gap | Current | Required | Resolution |
|-----|---------|----------|------------|
| Verification | None | `restore verify` | ✅ New command |
| Selective restore | Unclear | `restore files <paths>` | ✅ Explicit command |
| Repository scoping | Implicit | Explicit `<repository>` param | ✅ All restore commands |
| Browse capability | `snapshots contents` | `restore browse` | ✅ Proper semantics |

## Implementation Approach

**Since there are no existing users, implement the correct architecture immediately:**

### Phase 1: Implement Restore Namespace (High Priority)
- Create `restore` namespace with all 8 required commands
- Add explicit repository parameters to all commands
- Implement `restore verify` for data integrity validation
- Add Data Selection integration (`--selection` option)
- Implement progress monitoring for all restore operations

### Phase 2: Refactor Snapshots Namespace (High Priority)
- Remove `restore` command from `snapshots` namespace
- Keep only snapshot management commands (list, show, forget, prune, diff, find)
- Ensure clear separation between management and recovery operations
- Update command hierarchy documentation

### Phase 3: Documentation and Testing (High Priority)
- Update all CLI documentation to reflect correct structure
- Update command hierarchy reference
- Create comprehensive examples for both namespaces
- Add integration tests for all restore commands
- Update quickstart guides and tutorials

## Migration Considerations

**Status**: ✅ **NO MIGRATION NEEDED** - Product has not been released yet, no existing users.

This eliminates all backward compatibility concerns and allows clean implementation of the correct architecture from the start.

## Impact Assessment

### Positive Impacts
- ✅ Full specification compliance
- ✅ Clearer command semantics
- ✅ Better user experience
- ✅ Easier to extend recovery features
- ✅ Matches internal architecture
- ✅ **No migration complexity** - clean slate implementation
- ✅ **No backward compatibility burden** - can implement correctly from day one

### Implementation Considerations
- Documentation updates required (normal for pre-release)
- Some command name overlap (list, diff, find) - acceptable with different contexts
- Increased total command count - acceptable for clarity and separation of concerns

### Risk Assessment
- ⚠️ **ZERO migration risk** - no existing users
- ✅ Clean implementation opportunity
- ✅ Can establish correct patterns from the start

## Conclusion

**The `snapshots` command has NOT been replaced by `restore`** - both are required by specifications with distinct purposes:

- **`snapshots`**: Snapshot lifecycle management (list, forget, prune)
- **`restore`**: Data recovery operations (browse, restore, verify)

The current implementation is **non-compliant** with CLI Interface Requirements. 

**RECOMMENDATION: Implement Option 1 immediately** - With no existing users, there is zero migration risk and we can establish the correct architecture from the start. This is the ideal time to fix the non-compliance before release.

## Next Steps

1. ✅ Review and approve gap analysis report
2. Create implementation tasks for `restore` namespace
3. Remove `restore` command from `snapshots` namespace
4. Update command hierarchy documentation
5. Implement all 8 required `restore` commands
6. Add comprehensive tests for recovery operations
7. Update all CLI documentation and examples

## References

- **Detailed Analysis**: `docs/reports/2025-11-11-snapshots-restore-command-gap-analysis.md`
- **CLI Interface Requirements**: `.kiro/specs/cli-interface/requirements.md` (Requirement 13)
- **Recovery Operations Requirements**: `.kiro/specs/recovery-operations/requirements.md`
- **Command Hierarchy**: `docs/reference/timelocker-cli-command-hierarchy.md`

## Rules Consulted

- operational-best-practices.md (Priority 40) - Tool-driven exploration, SRS alignment
- coding-standards.md (Priority 100) - SOLID principles, separation of concerns
- general-preferences.md (Priority 50) - SOLID and DRY principles
- documentation-conventions.md (Priority 20) - Report placement in docs/reports/

## Rules Applied

- Placed detailed analysis in `docs/reports/` per documentation conventions
- Followed SRS alignment requirements from operational best practices
- Applied separation of concerns principle from coding standards
- Used tool-driven exploration to analyze specifications
