"""
Data Selection Integration Demo

This demo shows how the data selection integration service works with
backup operations to translate and apply selection rules to different
backup tools.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from TimeLocker.services.data_selection_integration_service import (
    DataSelectionIntegrationService
)
from TimeLocker.selection_models import (
    SelectionConfig,
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig
)
from TimeLocker.interfaces.data_models import (
    BackupJob,
    BackupJobConfig,
    ExecutionMode,
    RetryConfig,
    ToolConfiguration,
    ExecutionContext
)


def demo_basic_translation():
    """Demonstrate basic pattern translation for different tools"""
    print("=" * 80)
    print("DEMO: Basic Pattern Translation")
    print("=" * 80)
    
    # Create a selection configuration
    selection_config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        exclude_paths=[Path("/home/user/documents/temp")],
        include_patterns=[
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.pdf", syntax=PatternSyntax.GLOB),
            PatternRule(pattern=".*\\.log$", syntax=PatternSyntax.REGEX),  # Regex pattern
        ],
        exclude_patterns=[
            PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*~", syntax=PatternSyntax.GLOB),
            PatternRule(pattern=".*\\.bak$", syntax=PatternSyntax.REGEX),  # Regex pattern
        ]
    )
    
    # Create integration service
    service = DataSelectionIntegrationService()
    
    # Test translation for different tools
    tools = ['restic', 'borg', 'duplicity']
    
    for tool in tools:
        print(f"\n--- Translating for {tool.upper()} ---")
        
        result = service.translate_selection_for_tool(selection_config, tool)
        
        print(f"Include patterns: {result.include_patterns}")
        print(f"Exclude patterns: {result.exclude_patterns}")
        print(f"Include paths: {result.include_paths}")
        print(f"Exclude paths: {result.exclude_paths}")
        print(f"Unsupported patterns: {len(result.unsupported_patterns)}")
        
        if result.warnings:
            print(f"Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        if result.translation_notes:
            print(f"Translation notes:")
            for pattern, note in result.translation_notes.items():
                if pattern != 'summary':
                    print(f"  {pattern}: {note}")


def demo_compatibility_validation():
    """Demonstrate selection compatibility validation"""
    print("\n" + "=" * 80)
    print("DEMO: Selection Compatibility Validation")
    print("=" * 80)
    
    # Create a selection with various pattern types
    selection_config = SelectionConfig(
        include_patterns=[
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern=".*\\.log$", syntax=PatternSyntax.REGEX),
            PatternRule(pattern="README.md", syntax=PatternSyntax.LITERAL),
        ],
        exclude_patterns=[
            PatternRule(
                pattern="test_*.py",
                syntax=PatternSyntax.GLOB,
                applies_to=PathComponent.FILENAME
            ),
        ]
    )
    
    service = DataSelectionIntegrationService()
    
    # Validate for different tools
    tools = ['restic', 'borg']
    
    for tool in tools:
        print(f"\n--- Validating for {tool.upper()} ---")
        
        result = service.validate_selection_compatibility(selection_config, tool)
        
        print(f"Is compatible: {result.is_compatible}")
        print(f"Supported features: {result.supported_features}")
        print(f"Unsupported features: {result.unsupported_features}")
        
        if result.warnings:
            print(f"Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        if result.recommendations:
            print(f"Recommendations:")
            for rec in result.recommendations:
                print(f"  - {rec}")
        
        if result.alternative_approaches:
            print(f"Alternative approaches:")
            for feature, approach in result.alternative_approaches.items():
                print(f"  {feature}: {approach}")


def demo_job_integration():
    """Demonstrate applying selection to a backup job"""
    print("\n" + "=" * 80)
    print("DEMO: Applying Selection to Backup Job")
    print("=" * 80)
    
    # Create a selection configuration
    selection_config = SelectionConfig(
        include_paths=[Path("/home/user/projects")],
        include_patterns=[
            PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.md", syntax=PatternSyntax.GLOB),
        ],
        exclude_patterns=[
            PatternRule(pattern="__pycache__", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.pyc", syntax=PatternSyntax.GLOB),
            PatternRule(pattern=".git", syntax=PatternSyntax.GLOB),
        ]
    )
    
    # Create a backup job
    job_config = BackupJobConfig(
        job_id="demo-job-001",
        policy_id="",
        repository_id="demo-repo",
        data_selection_id="demo-selection",
        tool_type="restic",
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(),
        notification_config={}
    )
    
    backup_job = BackupJob(
        config=job_config,
        tool_configuration=ToolConfiguration(tool_type="restic"),
        execution_context=ExecutionContext(start_time=time.time())
    )
    
    # Apply selection to job
    service = DataSelectionIntegrationService()
    updated_job = service.apply_selection_to_job(backup_job, selection_config)
    
    print(f"Job ID: {updated_job.config.job_id}")
    print(f"Tool type: {updated_job.config.tool_type}")
    print(f"Source paths: {updated_job.source_paths}")
    print(f"Include patterns: {updated_job.include_patterns}")
    print(f"Exclude patterns: {updated_job.exclude_patterns}")
    
    if 'selection_warnings' in updated_job.config.metadata:
        print(f"Selection warnings:")
        for warning in updated_job.config.metadata['selection_warnings']:
            print(f"  - {warning}")
    
    if 'unsupported_selection_patterns' in updated_job.config.metadata:
        print(f"Unsupported patterns:")
        for pattern_info in updated_job.config.metadata['unsupported_selection_patterns']:
            print(f"  - {pattern_info['pattern']} ({pattern_info['syntax']}): {pattern_info['reason']}")


def demo_regex_to_glob_conversion():
    """Demonstrate regex to glob pattern conversion"""
    print("\n" + "=" * 80)
    print("DEMO: Regex to Glob Pattern Conversion")
    print("=" * 80)
    
    # Test various regex patterns
    test_patterns = [
        (".*\\.txt$", "Match .txt files"),
        ("^/home/user/.*", "Match files under /home/user"),
        (".*/logs/.*", "Match files in logs directories"),
        ("filename.*", "Match files starting with 'filename'"),
        (".*complex[0-9]+.*", "Complex regex (may not convert)"),
    ]
    
    service = DataSelectionIntegrationService()
    
    print("\nTesting regex to glob conversions:")
    for regex_pattern, description in test_patterns:
        glob_pattern = service._regex_to_glob(regex_pattern)
        print(f"\n{description}")
        print(f"  Regex: {regex_pattern}")
        print(f"  Glob:  {glob_pattern if glob_pattern else '(no conversion available)'}")


def demo_warning_generation():
    """Demonstrate warning generation for selection configurations"""
    print("\n" + "=" * 80)
    print("DEMO: Selection Warning Generation")
    print("=" * 80)
    
    # Create a job
    job_config = BackupJobConfig(
        job_id="demo-job-002",
        policy_id="",
        repository_id="demo-repo",
        data_selection_id="demo-selection",  # Required field
        tool_type="restic",
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(),
        notification_config={}
    )
    
    backup_job = BackupJob(
        config=job_config,
        tool_configuration=ToolConfiguration(tool_type="restic"),
        execution_context=ExecutionContext(start_time=time.time())
    )
    
    # Test case 1: Empty selection
    print("\n--- Test Case 1: Empty Selection ---")
    empty_selection = SelectionConfig()
    service = DataSelectionIntegrationService()
    warnings = service.generate_selection_warnings(backup_job, empty_selection)
    for warning in warnings:
        print(f"  - {warning}")
    
    # Test case 2: Conflicting patterns
    print("\n--- Test Case 2: Conflicting Patterns ---")
    conflicting_selection = SelectionConfig(
        include_patterns=[
            PatternRule(pattern="*.log", syntax=PatternSyntax.GLOB),
        ],
        exclude_patterns=[
            PatternRule(pattern="*.log", syntax=PatternSyntax.GLOB),
        ]
    )
    warnings = service.generate_selection_warnings(backup_job, conflicting_selection)
    for warning in warnings:
        print(f"  - {warning}")
    
    # Test case 3: Complex patterns
    print("\n--- Test Case 3: Complex Patterns ---")
    complex_selection = SelectionConfig(
        include_patterns=[
            PatternRule(
                pattern="*" * 10 + "very_long_pattern_" * 10,
                syntax=PatternSyntax.GLOB
            ),
        ]
    )
    warnings = service.generate_selection_warnings(backup_job, complex_selection)
    for warning in warnings:
        print(f"  - {warning}")
    
    # Test case 4: Broad exclude patterns
    print("\n--- Test Case 4: Broad Exclude Patterns ---")
    broad_selection = SelectionConfig(
        include_paths=[Path("/home/user")],
        exclude_patterns=[
            PatternRule(pattern="**/*", syntax=PatternSyntax.GLOB),
        ]
    )
    warnings = service.generate_selection_warnings(backup_job, broad_selection)
    for warning in warnings:
        print(f"  - {warning}")


def demo_statistics():
    """Demonstrate service statistics"""
    print("\n" + "=" * 80)
    print("DEMO: Service Statistics")
    print("=" * 80)
    
    service = DataSelectionIntegrationService()
    
    # Perform some operations
    selection_config = SelectionConfig(
        include_patterns=[
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
        ]
    )
    
    # Multiple translations
    for tool in ['restic', 'borg', 'duplicity']:
        service.translate_selection_for_tool(selection_config, tool)
    
    # Multiple validations
    for tool in ['restic', 'borg']:
        service.validate_selection_compatibility(selection_config, tool)
    
    # Get statistics
    stats = service.get_statistics()
    
    print("\nService Statistics:")
    print(f"  Translations performed: {stats['translations_performed']}")
    print(f"  Validations performed: {stats['validations_performed']}")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Cache misses: {stats['cache_misses']}")
    print(f"  Cache size: {stats['cache_size']}")
    print(f"  Cache hit ratio: {stats['cache_hit_ratio']:.2%}")


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("DATA SELECTION INTEGRATION SERVICE DEMO")
    print("=" * 80)
    
    try:
        demo_basic_translation()
        demo_compatibility_validation()
        demo_job_integration()
        demo_regex_to_glob_conversion()
        demo_warning_generation()
        demo_statistics()
        
        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
