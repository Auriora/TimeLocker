---
title: "Implementation Plan: Restore Namespace"
type: [ plan ]
status: [ approved ]
priority: high
created: "2025-11-11"
owner: "CLI Team"
tags: [cli, recovery-operations, implementation-plan]
related_specs: [cli-interface, recovery-operations]
---

# Implementation Plan: Restore Namespace

## Executive Summary

Implement the `restore` namespace to achieve CLI Interface Requirements compliance. The current implementation violates Requirement 13 by missing the entire `restore` namespace. With no existing users, we can implement the correct architecture immediately without migration concerns.

## Background

**Current State**: All recovery operations incorrectly placed in `snapshots` namespace  
**Required State**: Separate `restore` namespace with 8 commands per CLI Interface Requirements  
**Migration Risk**: ✅ **ZERO** - Product not yet released, no existing users

## Objectives

1. Achieve full compliance with CLI Interface Requirements Requirement 13
2. Implement proper separation between snapshot management and recovery operations
3. Align CLI structure with Recovery Operations architecture design
4. Establish correct command patterns before product release

## Scope

### In Scope
- Create `restore` namespace with all 8 required commands
- Remove `restore` command from `snapshots` namespace
- Implement explicit repository parameters for all restore commands
- Add `restore verify` for data integrity validation
- Integrate with Data Selection system
- Update all documentation and tests

### Out of Scope
- Migration tooling (not needed - no existing users)
- Backward compatibility aliases (not needed - no existing users)
- Deprecation warnings (not needed - no existing users)

## Implementation Tasks

### Phase 1: Core Restore Namespace (Week 1)

#### Task 1.1: Create Restore Command Module
**Priority**: Critical  
**Effort**: 2 days

- Create `src/TimeLocker/cli_modules/commands/restore.py`
- Set up Typer sub-application for restore namespace
- Register with main CLI application
- Add basic command structure and routing

**Acceptance Criteria**:
- `tl restore --help` displays command list
- All 8 commands registered and accessible
- Basic error handling in place

#### Task 1.2: Implement `restore list`
**Priority**: High  
**Effort**: 0.5 days

```python
@restore_app.command("list")
def restore_list(
    repository: Annotated[str, typer.Argument(help="Repository name or URI")],
    format: Annotated[str, typer.Option("--format", help="Output format")] = "table",
    json_output: bool = False,
) -> None:
    """List available snapshots in repository for restoration."""
```

**Acceptance Criteria**:
- Lists snapshots from specified repository
- Supports JSON output format
- Shows snapshot metadata (ID, date, size, tags)

#### Task 1.3: Implement `restore browse`
**Priority**: High  
**Effort**: 1 day

```python
@restore_app.command("browse")
def restore_browse(
    repository: Annotated[str, typer.Argument(help="Repository name or URI")],
    snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID to browse")],
    path: Annotated[str, typer.Option("--path", help="Path within snapshot")] = "/",
) -> None:
    """Explore snapshot contents interactively."""
```

**Acceptance Criteria**:
- Displays snapshot directory structure
- Supports navigation within snapshot
- Shows file metadata (size, permissions, dates)
- Supports search within snapshot

#### Task 1.4: Implement `restore files`
**Priority**: Critical  
**Effort**: 1.5 days

```python
@restore_app.command("files")
def restore_files(
    repository: Annotated[str, typer.Argument(help="Repository name or URI")],
    snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
    paths: Annotated[List[str], typer.Argument(help="File paths to restore")],
    target: Annotated[str, typer.Option("--target", help="Target directory")] = ".",
    selection: Annotated[Optional[str], typer.Option("--selection", help="Selection template")] = None,
    overwrite: bool = False,
    verify: bool = True,
) -> None:
    """Restore specific files from snapshot."""
```

**Acceptance Criteria**:
- Restores multiple specified files
- Supports selection templates from Data Selection system
- Handles file conflicts (overwrite/skip/rename)
- Preserves file metadata
- Integrates with `restore verify` if requested

#### Task 1.5: Implement `restore full`
**Priority**: Critical  
**Effort**: 1 day

```python
@restore_app.command("full")
def restore_full(
    repository: Annotated[str, typer.Argument(help="Repository name or URI")],
    snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
    target: Annotated[str, typer.Argument(help="Target directory")],
    verify: bool = True,
    overwrite: bool = False,
) -> None:
    """Restore complete snapshot to target location."""
```

**Acceptance Criteria**:
- Restores entire snapshot
- Validates target space availability
- Shows progress with ETA
- Integrates with `restore verify` if requested

#### Task 1.6: Implement `restore verify`
**Priority**: Critical  
**Effort**: 1 day

```python
@restore_app.command("verify")
def restore_verify(
    target: Annotated[str, typer.Argument(help="Directory to verify")],
    repository: Annotated[Optional[str], typer.Option("--repository", help="Repository")] = None,
    snapshot_id: Annotated[Optional[str], typer.Option("--snapshot", help="Snapshot ID")] = None,
) -> None:
    """Verify integrity of restored files."""
```

**Acceptance Criteria**:
- Compares checksums with snapshot metadata
- Reports successful and failed validations
- Detects corruption or incomplete restorations
- Provides detailed verification report

#### Task 1.7: Implement `restore mount` and `restore umount`
**Priority**: Medium  
**Effort**: 1 day

```python
@restore_app.command("mount")
def restore_mount(
    repository: Annotated[str, typer.Argument(help="Repository name or URI")],
    snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
    mountpoint: Annotated[str, typer.Argument(help="Mount point directory")],
) -> None:
    """Mount snapshot as read-only filesystem."""

@restore_app.command("umount")
def restore_umount(
    snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID to unmount")],
) -> None:
    """Unmount previously mounted snapshot."""
```

**Acceptance Criteria**:
- Mounts snapshot as FUSE filesystem
- Validates mount point availability
- Tracks mounted snapshots
- Safely unmounts with cleanup

#### Task 1.8: Implement `restore find` and `restore diff`
**Priority**: Medium  
**Effort**: 1 day

```python
@restore_app.command("find")
def restore_find(
    repository: Annotated[str, typer.Argument(help="Repository name or URI")],
    query: Annotated[str, typer.Argument(help="Search pattern")],
    snapshot_id: Annotated[Optional[str], typer.Option("--snapshot", help="Specific snapshot")] = None,
) -> None:
    """Search for files across snapshots."""

@restore_app.command("diff")
def restore_diff(
    repository: Annotated[str, typer.Argument(help="Repository name or URI")],
    snapshot_a: Annotated[str, typer.Argument(help="First snapshot ID")],
    snapshot_b: Annotated[str, typer.Argument(help="Second snapshot ID")],
) -> None:
    """Compare two snapshots for recovery planning."""
```

**Acceptance Criteria**:
- Searches files across all or specific snapshots
- Compares snapshots showing added/removed/modified files
- Supports pattern matching and filters

### Phase 2: Refactor Snapshots Namespace (Week 2)

#### Task 2.1: Remove `restore` from Snapshots
**Priority**: High  
**Effort**: 0.5 days

- Remove `snapshots restore` command
- Update command registration
- Verify no broken references

**Acceptance Criteria**:
- `tl snapshots restore` returns command not found
- Help text updated
- No broken imports or references

#### Task 2.2: Clean Up Snapshots Commands
**Priority**: Medium  
**Effort**: 0.5 days

- Review remaining snapshots commands
- Ensure clear separation from recovery operations
- Update help text to clarify purpose

**Acceptance Criteria**:
- `snapshots` namespace contains only management commands
- Help text clearly indicates management vs recovery
- No functional overlap with `restore` namespace

### Phase 3: Integration and Testing (Week 2-3)

#### Task 3.1: Data Selection Integration
**Priority**: High  
**Effort**: 1 day

- Add `--selection` option to `restore files`
- Integrate with Data Selection system
- Support pattern groups and templates

**Acceptance Criteria**:
- Can use selection templates for restore operations
- Patterns correctly applied to snapshot contents
- Validation for incompatible patterns

#### Task 3.2: Progress Monitoring
**Priority**: High  
**Effort**: 1 day

- Add progress bars to all restore commands
- Show files processed, bytes transferred, ETA
- Support cancellation (Ctrl+C) with cleanup

**Acceptance Criteria**:
- Real-time progress display
- Accurate ETA calculation
- Graceful cancellation handling

#### Task 3.3: Comprehensive Testing
**Priority**: Critical  
**Effort**: 2 days

- Unit tests for all restore commands
- Integration tests with real repositories
- Error handling and edge case tests
- Performance tests for large restores

**Acceptance Criteria**:
- 90%+ code coverage for restore module
- All commands tested with various scenarios
- Error conditions properly handled

### Phase 4: Documentation (Week 3)

#### Task 4.1: Update Command Hierarchy
**Priority**: High  
**Effort**: 0.5 days

- Update `docs/reference/timelocker-cli-command-hierarchy.md`
- Document all restore commands
- Update migration guide (remove migration section)

#### Task 4.2: Update CLI Documentation
**Priority**: High  
**Effort**: 1 day

- Update user guides with restore examples
- Create recovery operations tutorial
- Update quickstart guides
- Add troubleshooting section

#### Task 4.3: Update Specifications
**Priority**: Medium  
**Effort**: 0.5 days

- Mark CLI Interface Requirement 13 as implemented
- Update CLI design document
- Update recovery operations documentation

## Timeline

**Total Duration**: 3 weeks

| Week | Focus | Deliverables |
|------|-------|--------------|
| Week 1 | Core restore commands | All 8 commands implemented |
| Week 2 | Refactoring & integration | Snapshots cleaned up, integrations complete |
| Week 3 | Testing & documentation | Full test coverage, updated docs |

## Success Criteria

1. ✅ All 8 `restore` commands implemented per requirements
2. ✅ `snapshots` namespace contains only management commands
3. ✅ Full compliance with CLI Interface Requirements Requirement 13
4. ✅ 90%+ test coverage for restore module
5. ✅ All documentation updated
6. ✅ Zero specification violations

## Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Service layer not ready | High | Low | Verify service interfaces exist; implement stubs if needed |
| Data Selection integration complex | Medium | Medium | Start integration early; coordinate with Data Selection team |
| Performance issues with large restores | Medium | Low | Implement streaming and chunking; add performance tests |
| Command overlap confusion | Low | Medium | Clear help text and documentation; examples for each use case |

## Dependencies

- Recovery Operations service layer (RecoveryOrchestrator, SnapshotBrowser, RecoveryValidator)
- Data Selection system integration
- Repository Management service
- Security Services for credential management

## Approval

**Recommended Decision**: ✅ **APPROVE AND IMPLEMENT IMMEDIATELY**

**Rationale**:
- Critical specification compliance issue
- Zero migration risk (no existing users)
- Clean implementation opportunity before release
- Establishes correct patterns for product lifetime

## References

- **Gap Analysis**: `docs/reports/2025-11-11-snapshots-restore-command-gap-analysis.md`
- **Analysis Summary**: `docs/updates/2025-11-11-snapshots-restore-namespace-analysis.md`
- **CLI Interface Requirements**: `.kiro/specs/cli-interface/requirements.md` (Requirement 13)
- **Recovery Operations Requirements**: `.kiro/specs/recovery-operations/requirements.md`
- **Recovery Operations Design**: `.kiro/specs/recovery-operations/design.md`
