#!/usr/bin/env python3
"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

"""
Selection Manager Demo

This example demonstrates the comprehensive capabilities of the SelectionManager,
which serves as the central orchestrator for all data selection operations in TimeLocker.

Features demonstrated:
1. Creating selections from configurations
2. Evaluating selections against file systems
3. Size estimation and preview generation
4. Template integration
5. Performance optimization
6. Validation and conflict detection
7. Pattern testing
8. Integration with backup operations
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.selection_manager import SelectionManager
from TimeLocker.selection_service_interface import SelectionServiceInterface
from TimeLocker.selection_models import (
    SelectionConfig,
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    PrecedenceStrategy,
    ConflictResolution,
    SelectionTemplate
)
from TimeLocker.backup_target import BackupTarget


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


async def demo_basic_selection():
    """Demonstrate basic selection creation and evaluation"""
    print_section("1. Basic Selection Creation and Evaluation")
    
    # Create a selection manager
    manager = SelectionManager()
    
    # Create a simple selection configuration
    config = SelectionConfig(
        include_paths=[Path.home() / "Documents"],
        exclude_paths=[Path.home() / "Documents" / "temp"],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME),
            PatternRule("*.pdf", PatternSyntax.GLOB, False, PathComponent.FILENAME)
        ],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME),
            PatternRule("~*", PatternSyntax.GLOB, False, PathComponent.FILENAME)
        ]
    )
    
    print("Creating selection from configuration...")
    selection = await manager.create_selection(config)
    
    print(f"✓ Selection created successfully")
    print(f"  - Pattern count: {selection.metadata['pattern_count']}")
    print(f"  - Creation time: {selection.metadata['creation_time_ms']:.2f}ms")
    print(f"  - Warnings: {selection.metadata['validation_warnings']}")
    
    # Validate the selection
    print("\nValidating selection...")
    validation = await manager.validate_selection(selection)
    
    print(f"✓ Validation {'PASSED' if validation.is_valid else 'FAILED'}")
    print(f"  - Errors: {len(validation.errors)}")
    print(f"  - Warnings: {len(validation.warnings)}")
    
    if validation.warnings:
        print("\n  Warnings:")
        for warning in validation.warnings[:3]:  # Show first 3
            print(f"    - {warning.message}")
    
    return manager, selection


async def demo_template_integration():
    """Demonstrate template creation and usage"""
    print_section("2. Template Integration")
    
    manager = SelectionManager()
    
    # Create a template
    template_config = SelectionConfig(
        include_paths=[Path.home()],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME),
            PatternRule("*.cache", PatternSyntax.GLOB, False, PathComponent.FILENAME),
            PatternRule("__pycache__/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH),
            PatternRule("node_modules/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH)
        ],
        pattern_groups=["temporary_files"]
    )
    
    template = SelectionTemplate(
        id="demo_home_backup",
        name="Home Directory Backup",
        description="Standard home directory backup excluding temporary files",
        selection_config=template_config,
        tags=["home", "standard", "demo"]
    )
    
    print("Creating template...")
    template_id = await manager.template_manager.create_template(template)
    print(f"✓ Template created: {template_id}")
    print(f"  - Name: {template.name}")
    print(f"  - Description: {template.description}")
    print(f"  - Tags: {', '.join(template.tags)}")
    
    # List templates
    print("\nListing available templates...")
    templates = await manager.template_manager.list_templates()
    print(f"✓ Found {len(templates)} template(s)")
    for tmpl in templates[:3]:  # Show first 3
        print(f"  - {tmpl.name} ({tmpl.id})")
    
    # Use template with service interface
    print("\nUsing template with service interface...")
    service = SelectionServiceInterface(manager)
    
    selection = await service.create_selection_from_template(
        template_id,
        overrides={
            'exclude_patterns': [
                PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME)
            ]
        }
    )
    
    print(f"✓ Selection created from template")
    print(f"  - Template: {selection.metadata['template_name']}")
    print(f"  - Overrides applied: {selection.metadata['overrides_applied']}")
    
    return manager, service


async def demo_performance_optimization():
    """Demonstrate performance optimization"""
    print_section("3. Performance Optimization")
    
    manager = SelectionManager()
    
    # Create a selection with many patterns
    config = SelectionConfig(
        include_paths=[Path.home()],
        include_patterns=[
            PatternRule(f"*.{ext}", PatternSyntax.GLOB, False, PathComponent.FILENAME)
            for ext in ["txt", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"]
        ],
        exclude_patterns=[
            PatternRule(f"*.{ext}", PatternSyntax.GLOB, False, PathComponent.FILENAME)
            for ext in ["tmp", "cache", "bak", "swp", "log"]
        ]
    )
    
    selection = await manager.create_selection(config)
    
    print("Optimizing selection for different dataset sizes...")
    
    # Small dataset
    print("\n  Small dataset (1,000 files):")
    optimized_small = await manager.optimize_selection_for_performance(selection, 1000)
    print(f"    - Cache strategy: {optimized_small.cache_strategy}")
    print(f"    - Streaming recommended: {optimized_small.streaming_recommended}")
    print(f"    - Batch size: {optimized_small.batch_size}")
    print(f"    - Estimated gain: {optimized_small.estimated_performance_gain:.1f}x")
    
    # Large dataset
    print("\n  Large dataset (100,000 files):")
    optimized_large = await manager.optimize_selection_for_performance(selection, 100000)
    print(f"    - Cache strategy: {optimized_large.cache_strategy}")
    print(f"    - Streaming recommended: {optimized_large.streaming_recommended}")
    print(f"    - Batch size: {optimized_large.batch_size}")
    print(f"    - Estimated gain: {optimized_large.estimated_performance_gain:.1f}x")
    
    # Very large dataset
    print("\n  Very large dataset (1,000,000 files):")
    optimized_huge = await manager.optimize_selection_for_performance(selection, 1000000)
    print(f"    - Cache strategy: {optimized_huge.cache_strategy}")
    print(f"    - Streaming recommended: {optimized_huge.streaming_recommended}")
    print(f"    - Batch size: {optimized_huge.batch_size}")
    print(f"    - Estimated gain: {optimized_huge.estimated_performance_gain:.1f}x")
    
    # Get optimization recommendations
    print("\n  Optimization recommendations:")
    hints = manager.performance_optimizer.get_optimization_recommendations(config, 100000)
    for hint in hints[:3]:  # Show first 3
        print(f"    - [{hint.impact.upper()}] {hint.message}")
        print(f"      → {hint.implementation}")


async def demo_pattern_testing():
    """Demonstrate pattern testing"""
    print_section("4. Pattern Testing")
    
    manager = SelectionManager()
    
    # Test patterns against sample paths
    test_paths = [
        "/home/user/documents/report.pdf",
        "/home/user/documents/notes.txt",
        "/home/user/documents/temp.tmp",
        "/home/user/downloads/file.zip",
        "/home/user/.cache/data.cache"
    ]
    
    patterns_to_test = [
        "*.pdf",
        "*.txt",
        "*.tmp",
        "/home/user/documents/*"
    ]
    
    print("Testing patterns against sample paths...")
    print(f"\nTest paths ({len(test_paths)}):")
    for path in test_paths:
        print(f"  - {path}")
    
    for pattern in patterns_to_test:
        print(f"\nPattern: '{pattern}'")
        result = await manager.test_pattern_match(pattern, test_paths)
        
        if result['success']:
            print(f"  ✓ Matched {result['matched_count']}/{result['total_paths']} paths")
            if result['matches']:
                print(f"  Matches:")
                for match in result['matches']:
                    print(f"    - {match}")
        else:
            print(f"  ✗ Error: {result['error']}")


async def demo_backup_integration():
    """Demonstrate integration with backup operations"""
    print_section("5. Backup Integration")
    
    # Create a backup target with template
    print("Creating backup target with template...")
    
    # First create a template
    manager = SelectionManager()
    
    template_config = SelectionConfig(
        include_paths=[Path.home() / "Documents"],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME)
        ]
    )
    
    template = SelectionTemplate(
        id="backup_demo_template",
        name="Backup Demo Template",
        description="Demo template for backup integration",
        selection_config=template_config
    )
    
    await manager.template_manager.create_template(template)
    
    # Create backup target with template
    backup_target = BackupTarget(
        name="My Documents Backup",
        template_id="backup_demo_template",
        template_overrides={
            'exclude_patterns': [
                PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME)
            ]
        },
        tags=["documents", "important"]
    )
    
    print(f"✓ Backup target created: {backup_target.name}")
    
    # Get selection info
    info = backup_target.get_selection_info()
    print(f"\nBackup target information:")
    print(f"  - Name: {info['name']}")
    print(f"  - Tags: {', '.join(info['tags'])}")
    print(f"  - Has template: {info['has_template']}")
    print(f"  - Template ID: {info.get('template_id', 'N/A')}")
    print(f"  - Has overrides: {info.get('has_overrides', False)}")
    
    # Resolve selection
    print("\nResolving selection from template...")
    data_selection = await backup_target.resolve_selection()
    
    if data_selection:
        print(f"✓ Selection resolved successfully")
        print(f"  - Template: {data_selection.metadata.get('template_name', 'N/A')}")
        print(f"  - Overrides applied: {data_selection.metadata.get('overrides_applied', False)}")
    
    # Use service interface for backup operations
    print("\nUsing selection service for backup operations...")
    service = SelectionServiceInterface(manager)
    
    # List available templates
    templates = await service.list_available_templates()
    print(f"✓ Available templates: {len(templates)}")
    
    # Get template info
    template_info = await service.get_template_info("backup_demo_template")
    print(f"\nTemplate details:")
    print(f"  - Name: {template_info['name']}")
    print(f"  - Description: {template_info['description']}")
    print(f"  - Include paths: {len(template_info['include_paths'])}")
    print(f"  - Exclude patterns: {template_info['exclude_pattern_count']}")


async def demo_statistics():
    """Demonstrate statistics collection"""
    print_section("6. Statistics and Monitoring")
    
    manager = SelectionManager()
    
    # Perform some operations
    config = SelectionConfig(
        include_paths=[Path.home()],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME)
        ]
    )
    
    # Create multiple selections
    for i in range(3):
        await manager.create_selection(config)
    
    # Get statistics
    stats = manager.get_statistics()
    
    print("Selection Manager Statistics:")
    print(f"  - Selections created: {stats['selections_created']}")
    print(f"  - Evaluations performed: {stats['evaluations_performed']}")
    print(f"  - Validations performed: {stats['validations_performed']}")
    print(f"  - Optimizations applied: {stats['optimizations_applied']}")
    print(f"  - Total files evaluated: {stats['total_files_evaluated']}")
    print(f"  - Template count: {stats['template_count']}")
    
    # Pattern engine statistics
    print("\nPattern Engine Statistics:")
    pe_stats = stats['pattern_engine_stats']
    print(f"  - Cache size: {pe_stats['cache_size']}/{pe_stats['cache_capacity']}")
    print(f"  - Cache hits: {pe_stats['cache_hits']}")
    print(f"  - Cache misses: {pe_stats['cache_misses']}")
    print(f"  - Hit ratio: {pe_stats['hit_ratio']:.1%}")
    print(f"  - Total compilations: {pe_stats['total_compilations']}")
    print(f"  - Total matches: {pe_stats['total_matches']}")


async def main():
    """Run all demonstrations"""
    print("\n" + "=" * 80)
    print("  SelectionManager Comprehensive Demo")
    print("  TimeLocker Data Selection Management System")
    print("=" * 80)
    
    try:
        # Run demonstrations
        await demo_basic_selection()
        await demo_template_integration()
        await demo_performance_optimization()
        await demo_pattern_testing()
        await demo_backup_integration()
        await demo_statistics()
        
        print_section("Demo Complete")
        print("✓ All demonstrations completed successfully!")
        print("\nThe SelectionManager provides a comprehensive interface for:")
        print("  • Creating and validating selections")
        print("  • Managing templates and presets")
        print("  • Optimizing performance for different dataset sizes")
        print("  • Testing patterns and debugging selections")
        print("  • Integrating with backup operations")
        print("  • Monitoring and statistics collection")
        
    except Exception as e:
        print(f"\n✗ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
