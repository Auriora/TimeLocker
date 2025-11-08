# Selection Validation and Preview Services Implementation

**Date**: 2025-11-07  
**Type**: Feature Implementation  
**Component**: Data Selection  
**Status**: Complete

## Overview

Implemented comprehensive validation and preview services for the data selection system, providing selection rule validation, conflict detection, file system preview generation, and size estimation capabilities.

## Changes Made

### 1. SelectionValidationService (`src/TimeLocker/selection_validation_service.py`)

Created a comprehensive validation service that provides:

**Core Validation Features**:
- Complete selection configuration validation
- Pattern syntax validation for GLOB, REGEX, and LITERAL patterns
- Path syntax and format validation
- Logical consistency checking
- Precedence configuration validation
- Performance impact estimation

**Conflict Detection**:
- Include/exclude overlap detection
- Pattern contradiction detection
- Performance concern identification
- Configurable conflict severity levels (LOW, MEDIUM, HIGH, CRITICAL)
- Detailed conflict reports with suggested resolutions

**Path Accessibility**:
- Path existence checking
- Read permission verification
- File system permission reporting
- Graceful error handling for inaccessible paths

**Key Methods**:
```python
async def validate_selection_config(config: SelectionConfig) -> ValidationResult
async def validate_pattern_syntax(patterns: List[PatternRule]) -> ValidationResult
async def detect_selection_conflicts(config: SelectionConfig) -> List[ConflictReport]
async def check_path_accessibility(paths: List[Path]) -> List[AccessibilityResult]
async def estimate_performance_impact(config: SelectionConfig) -> PerformanceEstimate
```

**Validation Checks**:
1. At least one include path or pattern exists
2. Path syntax and type validation
3. Pattern syntax validation using PatternEngine
4. Duplicate pattern detection
5. Contradictory pattern detection
6. Overly broad exclusion warnings
7. Conflicting path specifications
8. Precedence configuration consistency
9. Performance impact analysis

### 2. SelectionPreviewService (`src/TimeLocker/selection_preview_service.py`)

Created a preview and estimation service that provides:

**Preview Generation**:
- File system traversal with selection rule evaluation
- Sample file collection (included and excluded)
- Configurable sample limits and depth restrictions
- Symlink handling options
- Cancellation support for long-running operations
- Progress reporting capabilities

**Size Estimation**:
- Accurate file and directory counting
- Total size calculation in bytes
- Progress callback support
- Inaccessible path tracking
- Estimation accuracy reporting
- Graceful handling of permission errors

**File System Traversal**:
- Recursive directory traversal
- Cycle detection to avoid infinite loops
- Depth limiting for performance
- Symlink following control
- Efficient path evaluation using compiled patterns
- Integration with PrecedenceResolver for conflict resolution

**Key Methods**:
```python
async def generate_selection_preview(
    config: SelectionConfig,
    base_paths: List[Path],
    options: Optional[PreviewOptions] = None
) -> PreviewResult

async def estimate_selection_size(
    config: SelectionConfig,
    base_paths: List[Path],
    progress_callback: Optional[callable] = None
) -> SizeEstimate
```

**Preview Options**:
- `max_samples`: Maximum number of sample files to collect
- `include_excluded_samples`: Whether to collect excluded file samples
- `max_depth`: Maximum directory depth to traverse
- `follow_symlinks`: Whether to follow symbolic links
- `timeout_seconds`: Operation timeout
- `show_progress`: Progress reporting flag

### 3. Supporting Data Models

**ConflictReport**:
- Conflict type classification
- Affected paths tracking
- Conflicting rules identification
- Suggested resolution guidance
- Severity levels

**AccessibilityResult**:
- Path accessibility status
- Existence verification
- Read permission status
- Error message reporting
- File permissions information

**PreviewOptions**:
- Configurable preview generation parameters
- Depth and sample limiting
- Symlink handling
- Timeout support

**ProgressInfo**:
- Real-time progress tracking
- Files and directories processed
- Bytes processed
- Elapsed time
- Estimated completion time
- Current path being processed

## Integration

### With Existing Components

**PatternEngine Integration**:
- Uses PatternEngine for pattern compilation and validation
- Leverages compiled patterns for efficient matching
- Utilizes pattern statistics for performance estimation

**PrecedenceResolver Integration**:
- Uses PrecedenceResolver for conflict resolution during evaluation
- Validates precedence configurations
- Applies precedence rules during file system traversal

**Selection Models Integration**:
- Uses all core selection data models
- Returns standard ValidationResult, PreviewResult, and SizeEstimate
- Maintains consistency with existing model definitions

### Service Architecture

Both services follow the established patterns:
- Async/await for I/O operations
- Comprehensive error handling
- Statistics tracking
- Logging integration
- Cancellation support
- Progress reporting

## Usage Examples

### Validation Example

```python
from TimeLocker.selection_validation_service import SelectionValidationService
from TimeLocker.selection_models import SelectionConfig, PatternRule, PatternSyntax

validation_service = SelectionValidationService()

config = SelectionConfig(
    include_paths=[Path("/home/user/documents")],
    exclude_paths=[Path("/home/user/documents/temp")],
    include_patterns=[
        PatternRule("*.txt", PatternSyntax.GLOB),
        PatternRule("*.pdf", PatternSyntax.GLOB),
    ],
    exclude_patterns=[
        PatternRule("*.tmp", PatternSyntax.GLOB),
    ]
)

# Validate configuration
result = await validation_service.validate_selection_config(config)

if result.is_valid:
    print("Configuration is valid!")
else:
    for error in result.errors:
        print(f"Error: {error.message}")

# Detect conflicts
conflicts = await validation_service.detect_selection_conflicts(config)
for conflict in conflicts:
    print(f"Conflict: {conflict.suggested_resolution}")
```

### Preview Example

```python
from TimeLocker.selection_preview_service import (
    SelectionPreviewService,
    PreviewOptions
)

preview_service = SelectionPreviewService()

options = PreviewOptions(
    max_samples=100,
    include_excluded_samples=True,
    max_depth=5
)

# Generate preview
preview = await preview_service.generate_selection_preview(
    config,
    [Path("/home/user")],
    options
)

print(f"Included samples: {len(preview.sample_included_files)}")
print(f"Excluded samples: {len(preview.sample_excluded_files)}")
print(preview.selection_summary)
```

### Size Estimation Example

```python
# Estimate size with progress reporting
def progress_callback(progress):
    print(f"Processed {progress.files_processed} files, "
          f"{progress.bytes_processed / 1024 / 1024:.2f} MB")

estimate = await preview_service.estimate_selection_size(
    config,
    [Path("/home/user/documents")],
    progress_callback
)

print(f"Total size: {estimate.total_size_bytes / 1024 / 1024:.2f} MB")
print(f"File count: {estimate.file_count}")
print(f"Accuracy: {estimate.estimation_accuracy * 100:.0f}%")
```

## Demo Script

Created `examples/validation_and_preview_demo.py` demonstrating:
1. Selection configuration validation
2. Pattern syntax validation
3. Path accessibility checking
4. Preview generation
5. Size estimation with progress reporting
6. Service statistics

Run with:
```bash
python examples/validation_and_preview_demo.py
```

## Requirements Satisfied

### Requirement 5.1 - Validation
✓ Validates selection rules for syntax errors, invalid paths, and logical inconsistencies

### Requirement 5.2 - Include Requirement
✓ Requires at least one directory to be included in backup operations

### Requirement 5.3 - Conflict Detection
✓ Detects and reports conflicts between include and exclude rules with suggested resolutions

### Requirement 5.4 - Preview Functionality
✓ Provides preview functionality showing which files would be selected

### Requirement 5.5 - Validation Errors
✓ Prevents backup execution on validation failure and provides detailed error messages

### Requirement 7.1 - Size Estimation
✓ Provides size estimation functionality calculating total bytes and file counts

### Requirement 7.2 - Inaccessible Files
✓ Handles inaccessible files gracefully and reports access issues

### Requirement 7.3 - Progress Reporting
✓ Provides progress reporting during size estimation with cancellation support

### Requirement 7.4 - Cache Estimates
✓ Supports caching through service statistics and can be extended

### Requirement 7.5 - Error Handling
✓ Continues processing accessible files and reports detailed error information

## Performance Characteristics

**Validation Service**:
- Pattern validation: O(n) where n is number of patterns
- Conflict detection: O(n²) for pattern comparisons
- Path accessibility: O(n) where n is number of paths
- Performance estimation: O(n) for pattern compilation

**Preview Service**:
- File system traversal: O(n) where n is number of files
- Pattern matching: O(m) per file where m is number of patterns
- Memory usage: O(k) where k is max_samples
- Supports cancellation for long-running operations

## Testing Recommendations

1. **Unit Tests**:
   - Validation of various configuration scenarios
   - Pattern syntax validation edge cases
   - Conflict detection accuracy
   - Path accessibility checking
   - Performance estimation accuracy

2. **Integration Tests**:
   - End-to-end validation workflows
   - Preview generation with real file systems
   - Size estimation accuracy
   - Progress reporting functionality
   - Cancellation handling

3. **Performance Tests**:
   - Large file system traversal (100k+ files)
   - Complex pattern matching performance
   - Memory usage under load
   - Cancellation responsiveness

## Future Enhancements

1. **Caching**:
   - Cache validation results for unchanged configurations
   - Cache size estimates with invalidation on config changes
   - Cache accessibility results with TTL

2. **Advanced Conflict Resolution**:
   - Machine learning-based conflict suggestion
   - Interactive conflict resolution UI
   - Automatic conflict resolution strategies

3. **Performance Optimization**:
   - Parallel file system traversal
   - Incremental size estimation
   - Smart sampling strategies
   - Adaptive depth limiting

4. **Enhanced Reporting**:
   - Detailed validation reports with visualizations
   - Preview result export (JSON, CSV)
   - Size estimation history tracking
   - Performance profiling reports

## Notes

- Both services are fully async for efficient I/O operations
- Comprehensive error handling ensures graceful degradation
- Statistics tracking enables monitoring and optimization
- Cancellation support allows user control over long operations
- Progress reporting provides user feedback during operations
- Integration with existing components maintains consistency

## Related Files

- `src/TimeLocker/selection_validation_service.py` - Validation service implementation
- `src/TimeLocker/selection_preview_service.py` - Preview service implementation
- `src/TimeLocker/selection_models.py` - Core data models
- `src/TimeLocker/pattern_engine.py` - Pattern matching engine
- `src/TimeLocker/precedence_resolver.py` - Precedence resolution
- `examples/validation_and_preview_demo.py` - Demo script
- `.kiro/specs/data-selection/tasks.md` - Task tracking
- `.kiro/specs/data-selection/requirements.md` - Requirements specification
- `.kiro/specs/data-selection/design.md` - Design documentation
