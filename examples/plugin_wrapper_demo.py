#!/usr/bin/env python3
"""
Plugin Wrapper System Demo

This script demonstrates the plugin wrapper system for backup tools,
showing how wrappers provide standardized interfaces and capability
gap filling for different backup engines.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from TimeLocker.services import (
    get_wrapper_registry,
    initialize_wrappers,
    ResticPluginWrapper,
    BackupConfig,
    Feature
)
from TimeLocker.interfaces.data_models import ToolConfiguration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def demo_wrapper_registration():
    """Demonstrate wrapper registration and discovery"""
    print_section("Wrapper Registration and Discovery")
    
    # Initialize wrappers
    initialize_wrappers()
    
    # Get registry
    registry = get_wrapper_registry()
    
    # List supported tools
    supported_tools = registry.get_supported_tools()
    print(f"\nSupported tools: {', '.join(supported_tools)}")
    
    # Get wrapper info for each tool
    for tool_name in supported_tools:
        print(f"\n{tool_name.upper()} Wrapper:")
        info = registry.get_wrapper_info(tool_name)
        print(f"  Native features: {len(info['native_features'])}")
        print(f"  Wrapper features: {len(info['wrapper_features'])}")
        print(f"  Total features: {info['total_features']}")


def demo_capability_detection():
    """Demonstrate capability detection and querying"""
    print_section("Capability Detection")
    
    registry = get_wrapper_registry()
    
    # Get Restic wrapper
    restic_wrapper = registry.get_wrapper('restic')
    
    print("\nRestic Native Capabilities:")
    native_caps = restic_wrapper.get_native_capabilities()
    for cap in sorted(native_caps, key=lambda x: x.value):
        print(f"  ✓ {cap.value}")
    
    print("\nRestic Wrapper-Provided Capabilities:")
    wrapper_caps = restic_wrapper.get_wrapper_capabilities()
    for cap in sorted(wrapper_caps, key=lambda x: x.value):
        print(f"  + {cap.value}")
    
    # Check specific capabilities
    print("\nCapability Checks:")
    features_to_check = [
        Feature.ENCRYPTION,
        Feature.PARALLEL_PROCESSING,
        Feature.REGEX_PATTERNS,
        Feature.MULTI_REPOSITORY
    ]
    
    for feature in features_to_check:
        has_cap = restic_wrapper.has_capability(feature)
        is_native = restic_wrapper.is_native_capability(feature)
        is_wrapper = restic_wrapper.is_wrapper_capability(feature)
        
        status = "Native" if is_native else "Wrapper" if is_wrapper else "Not supported"
        symbol = "✓" if has_cap else "✗"
        print(f"  {symbol} {feature.value}: {status}")


def demo_pattern_translation():
    """Demonstrate pattern translation from regex to tool-specific format"""
    print_section("Pattern Translation")
    
    registry = get_wrapper_registry()
    restic_wrapper = registry.get_wrapper('restic')
    
    # Test patterns
    include_patterns = [
        "*.py",  # Glob pattern (no translation needed)
        ".*\\.log$",  # Regex pattern (needs translation)
        "**/test_*.py",  # Glob pattern
        ".*/temp/.*"  # Regex pattern
    ]
    
    exclude_patterns = [
        "__pycache__",
        ".*\\.pyc$",
        "*/node_modules/*",
        "^\\.git/.*"
    ]
    
    print("\nTranslating patterns:")
    print("\nInclude patterns:")
    for pattern in include_patterns:
        print(f"  Original: {pattern}")
    
    print("\nExclude patterns:")
    for pattern in exclude_patterns:
        print(f"  Original: {pattern}")
    
    # Translate patterns
    result = restic_wrapper.translate_selection_rules(
        include_patterns,
        exclude_patterns
    )
    
    print("\nTranslation results:")
    print(f"\nTranslated include patterns ({len(result['include'])}):")
    for pattern in result['include']:
        print(f"  → {pattern}")
    
    print(f"\nTranslated exclude patterns ({len(result['exclude'])}):")
    for pattern in result['exclude']:
        print(f"  → {pattern}")
    
    if result['unsupported']:
        print(f"\nUnsupported patterns ({len(result['unsupported'])}):")
        for pattern in result['unsupported']:
            print(f"  ✗ {pattern}")


def demo_configuration_validation():
    """Demonstrate configuration validation"""
    print_section("Configuration Validation")
    
    registry = get_wrapper_registry()
    restic_wrapper = registry.get_wrapper('restic')
    
    # Test valid configuration
    print("\nValidating valid configuration:")
    valid_config = BackupConfig(
        source_paths=[Path.cwd()],
        repository_uri="/tmp/test-repo",
        exclude_patterns=["*.tmp", "__pycache__"],
        tags=["demo", "test"],
        tool_configuration=ToolConfiguration(
            tool_type="restic",
            parallel_operations=4,
            compression_level=6,
            encryption_enabled=True
        )
    )
    
    validation = restic_wrapper.validate_configuration(valid_config)
    print(f"  Valid: {validation['is_valid']}")
    if validation['warnings']:
        print(f"  Warnings: {len(validation['warnings'])}")
        for warning in validation['warnings']:
            print(f"    ⚠ {warning}")
    
    # Test invalid configuration
    print("\nValidating invalid configuration:")
    try:
        invalid_config = BackupConfig(
            source_paths=[],  # Empty paths
            repository_uri="",  # Empty URI
            tool_configuration=ToolConfiguration(
                tool_type="restic",
                parallel_operations=1,  # Valid but config has other issues
                compression_level=15  # Invalid
            )
        )
    except ValueError as e:
        # If ToolConfiguration validation fails, create simpler invalid config
        invalid_config = BackupConfig(
            source_paths=[],  # Empty paths
            repository_uri=""  # Empty URI
        )
    
    validation = restic_wrapper.validate_configuration(invalid_config)
    print(f"  Valid: {validation['is_valid']}")
    if validation['errors']:
        print(f"  Errors: {len(validation['errors'])}")
        for error in validation['errors']:
            print(f"    ✗ {error}")


def demo_capability_comparison():
    """Demonstrate capability comparison across wrappers"""
    print_section("Capability Comparison")
    
    registry = get_wrapper_registry()
    
    # Find wrappers with specific capabilities
    print("\nWrappers with encryption support:")
    encryption_tools = registry.find_wrappers_with_capability(Feature.ENCRYPTION)
    for tool in encryption_tools:
        print(f"  ✓ {tool}")
    
    print("\nWrappers with native parallel processing:")
    parallel_tools = registry.find_wrappers_with_native_capability(
        Feature.PARALLEL_PROCESSING
    )
    for tool in parallel_tools:
        print(f"  ✓ {tool}")
    
    print("\nWrappers with regex pattern support:")
    regex_tools = registry.find_wrappers_with_capability(Feature.REGEX_PATTERNS)
    for tool in regex_tools:
        wrapper = registry.get_wrapper(tool)
        is_native = wrapper.is_native_capability(Feature.REGEX_PATTERNS)
        support_type = "native" if is_native else "wrapper-provided"
        print(f"  ✓ {tool} ({support_type})")


def demo_required_capabilities():
    """Demonstrate checking required capabilities"""
    print_section("Required Capability Checking")
    
    registry = get_wrapper_registry()
    restic_wrapper = registry.get_wrapper('restic')
    
    # Define required capabilities for a job
    required_features = {
        Feature.ENCRYPTION,
        Feature.PARALLEL_PROCESSING,
        Feature.INTEGRITY_VERIFICATION,
        Feature.REGEX_PATTERNS
    }
    
    print("\nRequired capabilities for job:")
    for feature in required_features:
        print(f"  • {feature.value}")
    
    # Check if Restic supports all required features
    check_result = restic_wrapper.check_required_capabilities(required_features)
    
    print(f"\nAll supported: {check_result['all_supported']}")
    
    if check_result['native_features']:
        print(f"\nNatively supported ({len(check_result['native_features'])}):")
        for feature in check_result['native_features']:
            print(f"  ✓ {feature.value}")
    
    if check_result['wrapper_features']:
        print(f"\nWrapper-provided ({len(check_result['wrapper_features'])}):")
        for feature in check_result['wrapper_features']:
            print(f"  + {feature.value}")
    
    if check_result['missing_features']:
        print(f"\nMissing features ({len(check_result['missing_features'])}):")
        for feature in check_result['missing_features']:
            print(f"  ✗ {feature.value}")


def demo_wrapper_info():
    """Demonstrate getting comprehensive wrapper information"""
    print_section("Comprehensive Wrapper Information")
    
    registry = get_wrapper_registry()
    
    # Get all wrapper info
    all_info = registry.get_all_wrapper_info()
    
    for tool_name, info in all_info.items():
        print(f"\n{tool_name.upper()}:")
        
        if 'error' in info:
            print(f"  Error: {info['error']}")
            continue
        
        print(f"  Native features: {info['native_count']}")
        print(f"  Wrapper features: {info['wrapper_count']}")
        print(f"  Total features: {info['total_features']}")
        
        # Show sample of native features
        if info['native_features']:
            print(f"\n  Sample native features:")
            for feature in info['native_features'][:5]:
                print(f"    ✓ {feature}")
            if len(info['native_features']) > 5:
                print(f"    ... and {len(info['native_features']) - 5} more")
        
        # Show all wrapper features
        if info['wrapper_features']:
            print(f"\n  Wrapper-provided features:")
            for feature in info['wrapper_features']:
                print(f"    + {feature}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 70)
    print("  Plugin Wrapper System Demonstration")
    print("=" * 70)
    
    try:
        demo_wrapper_registration()
        demo_capability_detection()
        demo_pattern_translation()
        demo_configuration_validation()
        demo_capability_comparison()
        demo_required_capabilities()
        demo_wrapper_info()
        
        print("\n" + "=" * 70)
        print("  Demo completed successfully!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
