# Requirements and Design Updates for Backup CLI Selection Integration

**Date**: 2025-11-12  
**Type**: Requirements & Design Review  
**Status**: Proposed Changes  
**Related**: Task 14, Backup CLI Async Template Lookup Issue

## Executive Summary

The implementation of Task 14 (Update backup CLI commands to use data selections) revealed design inconsistencies between the CLI layer and the SelectionManager service layer. This document proposes updates to requirements and design to address these issues.

## Issues Identified

### 1. Async/Sync Boundary Not Defined

**Current State:**
- SelectionManager uses async methods
- CLI commands are synchronous (Typer limitation)
- No clear pattern for bridging async/sync boundary

**Impact:**
- Runtime warnings about unawaited coroutines
- Backup commands fail to execute
- Unclear responsibility for async handling

### 2. Template Lookup API Mismatch

**Current State:**
- Users provide template **names** in CLI
- SelectionManager only supports lookup by template **ID**
- No documented mapping between names and IDs

**Impact:**
- Template lookups fail even when template exists
- Error messages reference IDs instead of names (confusing for users)
- CLI must implement its own name-to-ID resolution

### 3. Validation Method Signatures

**Current State:**
- BackupCLIHandler methods are synchronous
- They call async SelectionManager methods
- No await statements (causes runtime errors)

**Impact:**
- Validation always fails
- Templates appear to not exist even when they do
- Backup operations cannot proceed

## Proposed Requirements Updates

### Update to Requirement 10.2

**Current:**
> 10.2: The CLI shall retrieve data selection templates from the Selection Manager using template names provided by users.

**Proposed:**
> 10.2: The CLI shall retrieve data selection templates from the Selection Manager using template names provided by users. The Selection Manager shall support template lookup by both ID and name, with name-based lookup being the primary interface for CLI operations.

**Rationale:** Clarifies that SelectionManager must support name-based lookup, not just ID-based.

### Update to Requirement 10.4

**Current:**
> 10.4: When a specified template is not found, the CLI shall display a clear error message listing available templates.

**Proposed:**
> 10.4: When a specified template is not found, the CLI shall display a clear error message that:
> - References the template by the name provided by the user (not internal ID)
> - Lists available template names
> - Suggests the command to create a new template
> - Provides examples of correct usage

**Rationale:** Specifies that error messages must use user-facing names, not internal IDs.

### New Requirement 10.6

**Proposed:**
> 10.6: The BackupCLIHandler shall provide synchronous wrapper methods for async SelectionManager operations to simplify CLI integration while properly handling async/await semantics internally.

**Rationale:** Defines responsibility for async/sync boundary handling.

### New Requirement 10.7

**Proposed:**
> 10.7: Template validation shall occur before initiating backup operations, with validation failures providing immediate feedback to users without attempting to connect to repositories or process data.

**Rationale:** Ensures fast-fail behavior for better UX.

## Proposed Design Updates

### Design Update 1: SelectionTemplateManager API Enhancement

**Add method to support name-based lookup:**

```python
class SelectionTemplateManager:
    async def get_template_by_name(self, name: str) -> Optional[SelectionTemplate]:
        """
        Get a template by name.
        
        Args:
            name: The name of the template to retrieve
            
        Returns:
            SelectionTemplate if found, None otherwise
            
        Note:
            This method searches through all templates to find a match by name.
            For better performance with large template collections, consider
            maintaining a name-to-ID index.
        """
        for template in self.templates_cache.values():
            if template.name == name:
                # Increment usage count
                template.usage_count += 1
                template.updated_at = datetime.utcnow()
                self._save_template_to_file(template)
                return template
        return None
    
    async def get_template(self, identifier: str, by_name: bool = False) -> SelectionTemplate:
        """
        Get a template by ID or name.
        
        Args:
            identifier: Template ID or name
            by_name: If True, treat identifier as name; if False, treat as ID
            
        Returns:
            SelectionTemplate: The requested template
            
        Raises:
            TemplateNotFoundError: If the template is not found
        """
        if by_name:
            template = await self.get_template_by_name(identifier)
            if template is None:
                raise TemplateNotFoundError(f"Template with name '{identifier}' not found")
            return template
        else:
            # Existing ID-based lookup
            if identifier not in self.templates_cache:
                raise TemplateNotFoundError(f"Template with ID '{identifier}' not found")
            template = self.templates_cache[identifier]
            template.usage_count += 1
            template.updated_at = datetime.utcnow()
            self._save_template_to_file(template)
            return template
```

**Rationale:**
- Provides flexible lookup API
- Maintains backward compatibility
- Clear parameter naming prevents ambiguity

### Design Update 2: BackupCLIHandler Sync/Async Pattern

**Add synchronous wrapper methods:**

```python
class BackupCLIHandler:
    """
    Handles CLI commands for backup operations with data selection integration.
    
    This handler provides synchronous methods for CLI integration while
    properly handling async SelectionManager operations internally.
    """
    
    def validate_selection_exists(self, selection_name: str) -> bool:
        """
        Check if a selection template exists (synchronous wrapper).
        
        Args:
            selection_name: Name of the selection template
            
        Returns:
            True if the template exists, False otherwise
        """
        try:
            return asyncio.run(self._validate_selection_exists_async(selection_name))
        except Exception as e:
            logger.debug(f"Error validating selection: {e}")
            return False
    
    async def _validate_selection_exists_async(self, selection_name: str) -> bool:
        """
        Check if a selection template exists (async implementation).
        
        Args:
            selection_name: Name of the selection template
            
        Returns:
            True if the template exists, False otherwise
        """
        try:
            template = await self.selection_manager.template_manager.get_template(
                selection_name, by_name=True
            )
            return template is not None
        except TemplateNotFoundError:
            return False
        except Exception as e:
            logger.debug(f"Error checking template existence: {e}")
            return False
    
    def get_selection_summary(self, selection_name: str) -> str:
        """
        Get human-readable summary of selection template (synchronous wrapper).
        
        Args:
            selection_name: Name of the selection template
            
        Returns:
            Human-readable summary string
            
        Raises:
            SelectionTemplateNotFoundError: If template doesn't exist
        """
        return asyncio.run(self._get_selection_summary_async(selection_name))
    
    async def _get_selection_summary_async(self, selection_name: str) -> str:
        """
        Get human-readable summary of selection template (async implementation).
        """
        try:
            template = await self.selection_manager.template_manager.get_template(
                selection_name, by_name=True
            )
            
            # Build summary from template configuration
            config = template.config
            summary_parts = [f"Selection: {selection_name}"]
            
            if config.include_paths:
                summary_parts.append(f"  Include paths: {len(config.include_paths)}")
            if config.exclude_paths:
                summary_parts.append(f"  Exclude paths: {len(config.exclude_paths)}")
            if config.include_patterns:
                summary_parts.append(f"  Include patterns: {len(config.include_patterns)}")
            if config.exclude_patterns:
                summary_parts.append(f"  Exclude patterns: {len(config.exclude_patterns)}")
            
            return "\n".join(summary_parts)
            
        except TemplateNotFoundError as e:
            raise SelectionTemplateNotFoundError(
                f"Failed to get template '{selection_name}': {e}"
            ) from e
```

**Rationale:**
- Clear separation of sync/async boundaries
- Synchronous methods for CLI convenience
- Async methods for internal use and testing
- Proper error handling at each layer

### Design Update 3: Error Message Improvements

**Update error messages to use names:**

```python
# In BackupCLIHandler
def suggest_template_creation(self, selection_name: str) -> str:
    """
    Generate a helpful message suggesting how to create a template.
    
    Args:
        selection_name: Name of the missing template
        
    Returns:
        Helpful suggestion message with template name (not ID)
    """
    available_templates = self.get_available_templates()
    
    message = f"Selection template '{selection_name}' not found.\n\n"
    
    if available_templates:
        message += "Available templates:\n"
        for template_name in available_templates[:5]:
            message += f"  - {template_name}\n"
        if len(available_templates) > 5:
            message += f"  ... and {len(available_templates) - 5} more\n"
        message += "\n"
    
    message += "To create a new selection template:\n"
    message += f"  tl selections create {selection_name} --paths /path/to/backup\n\n"
    message += "For more information:\n"
    message += "  tl selections --help"
    
    return message
```

**Rationale:**
- Uses template names throughout (user-facing)
- Never exposes internal IDs to users
- Provides actionable guidance

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Layer (Sync)                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │  backup_create() command                            │    │
│  │  - Collects user input (template name)             │    │
│  │  - Calls BackupCLIHandler (sync methods)           │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              BackupCLIHandler (Sync/Async Bridge)           │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Synchronous Methods (CLI Interface)                │    │
│  │  - validate_selection_exists(name) → bool          │    │
│  │  - get_selection_summary(name) → str               │    │
│  │  - Uses asyncio.run() internally                    │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Async Methods (Internal Implementation)            │    │
│  │  - _validate_selection_exists_async(name)          │    │
│  │  - _get_selection_summary_async(name)              │    │
│  │  - execute_backup_with_selection(name) [async]     │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                SelectionManager (Async)                     │
│  ┌────────────────────────────────────────────────────┐    │
│  │  SelectionTemplateManager                           │    │
│  │  - get_template(id, by_name=False) [async]         │    │
│  │  - get_template_by_name(name) [async]              │    │
│  │  - list_templates() [async]                         │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: SelectionTemplateManager Updates (High Priority)
1. Add `get_template_by_name()` method
2. Update `get_template()` to support `by_name` parameter
3. Add unit tests for name-based lookup
4. Update error messages to use names

### Phase 2: BackupCLIHandler Updates (High Priority)
1. Add async implementation methods (_*_async)
2. Convert existing methods to synchronous wrappers
3. Update all template lookups to use by_name=True
4. Add comprehensive error handling
5. Update unit tests

### Phase 3: CLI Command Updates (Medium Priority)
1. Update backup_create to use new BackupCLIHandler API
2. Ensure proper error message display
3. Add integration tests
4. Update documentation

### Phase 4: Documentation Updates (Medium Priority)
1. Update requirements.md with new requirements
2. Update design.md with architecture changes
3. Update API documentation
4. Add troubleshooting guide

## Testing Strategy

### Unit Tests
- [ ] Test `get_template_by_name()` with existing templates
- [ ] Test `get_template_by_name()` with non-existent templates
- [ ] Test synchronous wrapper methods
- [ ] Test async implementation methods
- [ ] Test error handling at each layer

### Integration Tests
- [ ] Test full backup flow with selection by name
- [ ] Test error messages shown to users
- [ ] Test validation before backup execution
- [ ] Test completion still works

### Manual Testing
- [ ] Create selection template
- [ ] Run backup with selection by name
- [ ] Verify error messages for missing templates
- [ ] Test tab completion

## Backward Compatibility

### Breaking Changes
- None (all changes are additive)

### Deprecations
- None

### Migration Path
- Existing code using `get_template(id)` continues to work
- New code can use `get_template(name, by_name=True)` or `get_template_by_name(name)`

## Performance Considerations

### Name-Based Lookup Performance
- **Current**: O(1) lookup by ID (dictionary)
- **Proposed**: O(n) lookup by name (linear search)
- **Impact**: Negligible for typical template counts (< 100)
- **Future Optimization**: Add name-to-ID index if needed

### Multiple Event Loops
- **Current**: One asyncio.run() per operation
- **Impact**: Small overhead for CLI operations
- **Acceptable**: CLI operations are not performance-critical
- **Future Optimization**: Batch operations if needed

## Security Considerations

- Template names are user-provided input (validate/sanitize)
- No new security risks introduced
- Existing security measures remain in place

## Conclusion

The proposed updates address the identified issues while maintaining backward compatibility and providing a clear path forward. The changes align with user expectations (using template names) and provide proper async/sync boundary handling.

**Recommendation**: Approve and implement these changes as part of fixing the backup CLI selection integration.

---

**Reviewers**: Please review and provide feedback on:
1. Proposed requirement updates
2. Design approach (sync wrappers vs full async)
3. API naming and signatures
4. Error message improvements
5. Implementation priority

**Next Steps After Approval**:
1. Update requirements.md and design.md
2. Implement SelectionTemplateManager changes
3. Implement BackupCLIHandler changes
4. Update CLI commands
5. Add comprehensive tests
6. Update documentation
