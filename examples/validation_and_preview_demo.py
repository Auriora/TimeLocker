"""
Demo script for Selection Validation and Preview Services.

This script demonstrates:
1. Validating selection configurations
2. Detecting conflicts in selection rules
3. Generating selection previews
4. Estimating selection sizes
5. Checking path accessibility

Copyright ©  Bruce Cherrington
Licensed under GPL v3.0
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    PrecedenceStrategy,
    SelectionConfig
)
from TimeLocker.selection_validation_service import SelectionValidationService
from TimeLocker.selection_preview_service import SelectionPreviewService, PreviewOptions


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


async def demo_validation():
    """Demonstrate selection validation."""
    print_section("Selection Validation Demo")
    
    # Create validation service
    validation_service = SelectionValidationService()
    
    # Example 1: Valid configuration
    print("Example 1: Valid Configuration")
    print("-" * 70)
    
    valid_config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        exclude_paths=[Path("/home/user/documents/temp")],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.pdf", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("~*", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        precedence_config=PrecedenceConfig(
            default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE
        )
    )
    
    result = await validation_service.validate_selection_config(valid_config)
    
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - [{warning.severity}] {warning.message}")
    
    if result.estimated_performance:
        print(f"\nPerformance Estimate:")
        print(f"  Files/sec: {result.estimated_performance.estimated_files_per_second:.0f}")
        print(f"  Memory: {result.estimated_performance.estimated_memory_mb:.1f} MB")
    
    # Example 2: Invalid configuration (no includes)
    print("\n\nExample 2: Invalid Configuration (No Includes)")
    print("-" * 70)
    
    invalid_config = SelectionConfig(
        include_paths=[],
        exclude_paths=[Path("/home/user/temp")],
        include_patterns=[],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ]
    )
    
    result = await validation_service.validate_selection_config(invalid_config)
    
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {len(result.errors)}")
    
    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error.message}")
            if error.suggested_fix:
                print(f"    Fix: {error.suggested_fix}")
    
    # Example 3: Configuration with conflicts
    print("\n\nExample 3: Configuration with Conflicts")
    print("-" * 70)
    
    conflict_config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        exclude_paths=[],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        exclude_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        precedence_config=PrecedenceConfig(
            default_strategy=PrecedenceStrategy.MOST_SPECIFIC_WINS
        )
    )
    
    result = await validation_service.validate_selection_config(conflict_config)
    
    print(f"Valid: {result.is_valid}")
    print(f"Warnings: {len(result.warnings)}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - [{warning.severity}] {warning.message}")
    
    # Detect conflicts
    conflicts = await validation_service.detect_selection_conflicts(conflict_config)
    
    print(f"\nConflicts Detected: {len(conflicts)}")
    for conflict in conflicts:
        print(f"  - Type: {conflict.conflict_type.value}")
        print(f"    Severity: {conflict.severity.value}")
        print(f"    Resolution: {conflict.suggested_resolution}")


async def demo_pattern_validation():
    """Demonstrate pattern syntax validation."""
    print_section("Pattern Syntax Validation Demo")
    
    validation_service = SelectionValidationService()
    
    # Test various patterns
    test_patterns = [
        PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule(".*\\.log$", PatternSyntax.REGEX, False, PathComponent.FILENAME, 100),
        PatternRule("README.md", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 100),
        PatternRule("**/*.py", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 100),
        PatternRule("", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),  # Invalid
        PatternRule("[invalid", PatternSyntax.REGEX, False, PathComponent.FILENAME, 100),  # Invalid
    ]
    
    result = await validation_service.validate_pattern_syntax(test_patterns)
    
    print(f"Valid: {result.is_valid}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    
    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - Pattern {error.context.get('pattern_index', '?')}: {error.message}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - Pattern {warning.context.get('pattern_index', '?')}: {warning.message}")


async def demo_path_accessibility():
    """Demonstrate path accessibility checking."""
    print_section("Path Accessibility Demo")
    
    validation_service = SelectionValidationService()
    
    # Test various paths
    test_paths = [
        Path("/tmp"),
        Path("/etc"),
        Path("/root"),  # Likely not accessible
        Path("/nonexistent/path"),
        Path.home(),
    ]
    
    print("Checking path accessibility...")
    results = await validation_service.check_path_accessibility(test_paths)
    
    for result in results:
        status = "✓" if result.accessible else "✗"
        print(f"\n{status} {result.path}")
        print(f"  Exists: {result.exists}")
        print(f"  Readable: {result.readable}")
        if result.permissions:
            print(f"  Permissions: {result.permissions}")
        if result.error_message:
            print(f"  Error: {result.error_message}")


async def demo_preview():
    """Demonstrate selection preview generation."""
    print_section("Selection Preview Demo")
    
    preview_service = SelectionPreviewService()
    
    # Create a simple configuration
    config = SelectionConfig(
        include_paths=[Path.home()],
        exclude_paths=[],
        include_patterns=[
            PatternRule("*.py", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("*.md", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        exclude_patterns=[
            PatternRule("__pycache__/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
            PatternRule("*.pyc", PatternSyntax.GLOB, False, PathComponent.FILENAME, 200),
        ],
        precedence_config=PrecedenceConfig(
            default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE
        )
    )
    
    # Generate preview with limited samples
    options = PreviewOptions(
        max_samples=20,
        include_excluded_samples=True,
        max_depth=3,  # Limit depth for demo
        follow_symlinks=False
    )
    
    print("Generating preview (limited to 20 samples, max depth 3)...")
    preview = await preview_service.generate_selection_preview(
        config,
        [Path.home()],
        options
    )
    
    print(f"\nPreview Results:")
    print(f"  Generation time: {preview.preview_generation_time:.2f}s")
    print(f"  Total files seen: {preview.total_estimated_files}")
    print(f"  Included samples: {len(preview.sample_included_files)}")
    print(f"  Excluded samples: {len(preview.sample_excluded_files)}")
    print(f"  Truncated: {preview.truncated}")
    
    if preview.sample_included_files:
        print(f"\nSample Included Files (showing first 5):")
        for path in preview.sample_included_files[:5]:
            print(f"  + {path}")
    
    if preview.sample_excluded_files:
        print(f"\nSample Excluded Files (showing first 5):")
        for path in preview.sample_excluded_files[:5]:
            print(f"  - {path}")


async def demo_size_estimation():
    """Demonstrate size estimation."""
    print_section("Size Estimation Demo")
    
    preview_service = SelectionPreviewService()
    
    # Create a configuration for a specific directory
    test_dir = Path.home() / ".config"
    if not test_dir.exists():
        test_dir = Path.home()
    
    config = SelectionConfig(
        include_paths=[test_dir],
        exclude_paths=[],
        include_patterns=[],
        exclude_patterns=[
            PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.cache", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        precedence_config=PrecedenceConfig(
            default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE
        )
    )
    
    # Progress callback
    def progress_callback(progress):
        if progress.files_processed % 100 == 0:
            print(f"  Progress: {progress.files_processed} files, "
                  f"{progress.bytes_processed / 1024 / 1024:.2f} MB, "
                  f"{progress.elapsed_seconds:.1f}s")
    
    print(f"Estimating size for: {test_dir}")
    print("(This may take a moment...)\n")
    
    estimate = await preview_service.estimate_selection_size(
        config,
        [test_dir],
        progress_callback
    )
    
    print(f"\nSize Estimate Results:")
    print(f"  Total size: {estimate.total_size_bytes / 1024 / 1024:.2f} MB")
    print(f"  File count: {estimate.file_count}")
    print(f"  Directory count: {estimate.directory_count}")
    print(f"  Estimation time: {estimate.estimation_time_seconds:.2f}s")
    print(f"  Accuracy: {estimate.estimation_accuracy * 100:.0f}%")
    
    if estimate.inaccessible_paths:
        print(f"  Inaccessible paths: {len(estimate.inaccessible_paths)}")
        if len(estimate.inaccessible_paths) <= 5:
            for path in estimate.inaccessible_paths:
                print(f"    - {path}")


async def demo_statistics():
    """Demonstrate service statistics."""
    print_section("Service Statistics Demo")
    
    validation_service = SelectionValidationService()
    preview_service = SelectionPreviewService()
    
    # Run some operations
    config = SelectionConfig(
        include_paths=[Path.home()],
        exclude_paths=[],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        exclude_patterns=[]
    )
    
    await validation_service.validate_selection_config(config)
    await validation_service.validate_selection_config(config)
    
    # Get statistics
    val_stats = validation_service.get_statistics()
    prev_stats = preview_service.get_statistics()
    
    print("Validation Service Statistics:")
    for key, value in val_stats.items():
        print(f"  {key}: {value}")
    
    print("\nPreview Service Statistics:")
    for key, value in prev_stats.items():
        print(f"  {key}: {value}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("  Selection Validation and Preview Services Demo")
    print("=" * 70)
    
    try:
        await demo_validation()
        await demo_pattern_validation()
        await demo_path_accessibility()
        await demo_preview()
        await demo_size_estimation()
        await demo_statistics()
        
        print("\n" + "=" * 70)
        print("  Demo Complete!")
        print("=" * 70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
