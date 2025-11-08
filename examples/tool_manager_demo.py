#!/usr/bin/env python3
"""
Tool Manager Demo

This example demonstrates the tool management and capability system for
backup operations, including:
- Tool capability detection
- Tool configuration optimization
- Job compatibility validation
- Performance profiling
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.services import (
    ToolManager,
    Feature,
    ToolCapabilities,
    ToolInfo
)
from TimeLocker.interfaces.data_models import (
    BackupJobConfig,
    BackupJob,
    ExecutionMode,
    ToolConfiguration,
    ExecutionContext
)
import time


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def demo_tool_detection():
    """Demonstrate tool capability detection"""
    print_section("Tool Capability Detection")
    
    tool_manager = ToolManager()
    
    # Get list of supported tools
    print("Supported Backup Tools:")
    print("-" * 80)
    
    tools = tool_manager.get_supported_tools()
    for tool in tools:
        status = "✓ Available" if tool.is_available else "✗ Not Available"
        print(f"\n{tool.tool_name.upper()}")
        print(f"  Status: {status}")
        if tool.is_available:
            print(f"  Version: {tool.version}")
            print(f"  Total Features: {tool.feature_count}")
            print(f"  Native Features: {tool.native_feature_count}")
            print(f"  Wrapper Features: {tool.wrapper_feature_count}")


def demo_capability_details():
    """Demonstrate detailed capability information"""
    print_section("Detailed Capability Information")
    
    tool_manager = ToolManager()
    
    # Get detailed capabilities for Restic
    try:
        capabilities = tool_manager.get_tool_capabilities("restic")
        
        print(f"RESTIC v{capabilities.version}")
        print("-" * 80)
        
        print("\nNative Features:")
        for feature in sorted(capabilities.native_features, key=lambda f: f.value):
            print(f"  ✓ {feature.value}")
        
        print("\nWrapper-Provided Features:")
        for feature in sorted(capabilities.wrapper_features, key=lambda f: f.value):
            print(f"  + {feature.value}")
        
        print("\nLimitations:")
        for limitation in capabilities.limitations:
            print(f"  ! {limitation.description}")
            if limitation.workaround:
                print(f"    Workaround: {limitation.workaround}")
        
        print("\nPerformance Profile:")
        perf = capabilities.performance_characteristics
        print(f"  Throughput: {perf.typical_throughput_mbps} MB/s")
        print(f"  CPU Usage: {perf.cpu_usage}")
        print(f"  Memory Usage: {perf.memory_usage}")
        print(f"  Parallel Efficiency: {perf.parallel_efficiency * 100:.0f}%")
        print(f"  Compression Overhead: {perf.compression_overhead}")
        print(f"  Resume Support: {'Yes' if perf.supports_resume else 'No'}")
        
        print("\nRecommended Use Cases:")
        for use_case in capabilities.recommended_use_cases:
            print(f"  • {use_case}")
        
        print("\nConfiguration Options:")
        for key, value in capabilities.configuration_options.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Could not get Restic capabilities: {e}")


def demo_tool_configuration():
    """Demonstrate tool configuration optimization"""
    print_section("Tool Configuration Optimization")
    
    tool_manager = ToolManager()
    
    # Create a sample backup job
    job_config = BackupJobConfig(
        job_id="demo-job-001",
        repository_id="demo-repo",
        target_names=["documents", "photos"],
        execution_mode=ExecutionMode.ON_DEMAND,
        priority=8,  # High priority
        tags=["demo", "important"]
    )
    
    job = BackupJob(
        config=job_config,
        source_paths=["/home/user/documents", "/home/user/photos"],
        exclude_patterns=["*.tmp", "*.cache"],
        execution_context=ExecutionContext(start_time=time.time())
    )
    
    print("Job Configuration:")
    print(f"  Job ID: {job.config.job_id}")
    print(f"  Priority: {job.config.priority}")
    print(f"  Source Paths: {len(job.source_paths)}")
    print(f"  Exclude Patterns: {len(job.exclude_patterns)}")
    
    # Configure tool for the job
    try:
        print("\nOptimizing configuration for Restic...")
        config = tool_manager.configure_tool_for_job("restic", job)
        
        print("\nOptimized Configuration:")
        print(f"  Tool Type: {config.tool_type}")
        print(f"  Parallel Operations: {config.parallel_operations}")
        print(f"  Compression Level: {config.compression_level}")
        print(f"  Encryption Enabled: {config.encryption_enabled}")
        print(f"  Integrity Check Enabled: {config.integrity_check_enabled}")
        
        if config.bandwidth_limit:
            print(f"  Bandwidth Limit: {config.bandwidth_limit / (1024**2):.2f} MB/s")
        
        print("\nTool-Specific Options:")
        for key, value in config.tool_specific_options.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Configuration failed: {e}")


def demo_compatibility_validation():
    """Demonstrate job compatibility validation"""
    print_section("Job Compatibility Validation")
    
    tool_manager = ToolManager()
    
    # Create jobs with different requirements
    jobs = [
        {
            'name': 'Standard Backup',
            'config': BackupJobConfig(
                job_id="standard-001",
                repository_id="repo-1",
                target_names=["data"],
                priority=5
            ),
            'job': BackupJob(
                config=BackupJobConfig(
                    job_id="standard-001",
                    repository_id="repo-1",
                    target_names=["data"],
                    priority=5
                ),
                source_paths=["/data"],
                execution_context=ExecutionContext(start_time=time.time())
            )
        },
        {
            'name': 'High Priority Encrypted',
            'config': BackupJobConfig(
                job_id="encrypted-001",
                repository_id="repo-2",
                target_names=["sensitive"],
                priority=9
            ),
            'job': BackupJob(
                config=BackupJobConfig(
                    job_id="encrypted-001",
                    repository_id="repo-2",
                    target_names=["sensitive"],
                    priority=9
                ),
                source_paths=["/sensitive"],
                tool_configuration=ToolConfiguration(
                    tool_type="restic",
                    encryption_enabled=True,
                    integrity_check_enabled=True
                ),
                execution_context=ExecutionContext(start_time=time.time())
            )
        }
    ]
    
    for job_info in jobs:
        print(f"\nValidating: {job_info['name']}")
        print("-" * 80)
        
        try:
            result = tool_manager.validate_job_compatibility("restic", job_info['job'])
            
            print(f"Compatible: {'✓ Yes' if result['is_compatible'] else '✗ No'}")
            
            if result['warnings']:
                print("\nWarnings:")
                for warning in result['warnings']:
                    print(f"  ⚠ {warning}")
            
            if result['missing_features']:
                print("\nMissing Features:")
                for feature in result['missing_features']:
                    print(f"  ✗ {feature.value}")
            
            if result['recommendations']:
                print("\nRecommendations:")
                for rec in result['recommendations']:
                    print(f"  → {rec}")
            
        except Exception as e:
            print(f"Validation failed: {e}")


def demo_tool_comparison():
    """Demonstrate comparison between different tools"""
    print_section("Tool Comparison")
    
    tool_manager = ToolManager()
    
    tools_to_compare = ["restic", "borg", "duplicity"]
    
    print("Feature Comparison:")
    print("-" * 80)
    
    # Key features to compare
    key_features = [
        Feature.INCREMENTAL_BACKUP,
        Feature.DATA_DEDUPLICATION,
        Feature.PARALLEL_PROCESSING,
        Feature.ENCRYPTION,
        Feature.INTEGRITY_VERIFICATION,
        Feature.RESUME_SUPPORT
    ]
    
    # Print header
    print(f"{'Feature':<30}", end="")
    for tool in tools_to_compare:
        print(f"{tool.upper():<15}", end="")
    print()
    print("-" * 80)
    
    # Compare features
    for feature in key_features:
        print(f"{feature.value:<30}", end="")
        
        for tool in tools_to_compare:
            try:
                capabilities = tool_manager.get_tool_capabilities(tool)
                if capabilities.is_native_feature(feature):
                    status = "✓ Native"
                elif capabilities.is_wrapper_feature(feature):
                    status = "+ Wrapper"
                else:
                    status = "✗ No"
                print(f"{status:<15}", end="")
            except Exception:
                print(f"{'? Unknown':<15}", end="")
        
        print()
    
    # Performance comparison
    print("\n\nPerformance Comparison:")
    print("-" * 80)
    print(f"{'Metric':<30}", end="")
    for tool in tools_to_compare:
        print(f"{tool.upper():<15}", end="")
    print()
    print("-" * 80)
    
    metrics = [
        ('Throughput (MB/s)', lambda p: f"{p.typical_throughput_mbps or 0:.0f}"),
        ('CPU Usage', lambda p: p.cpu_usage),
        ('Memory Usage', lambda p: p.memory_usage),
        ('Parallel Efficiency', lambda p: f"{p.parallel_efficiency * 100:.0f}%"),
        ('Resume Support', lambda p: "Yes" if p.supports_resume else "No")
    ]
    
    for metric_name, metric_func in metrics:
        print(f"{metric_name:<30}", end="")
        
        for tool in tools_to_compare:
            try:
                capabilities = tool_manager.get_tool_capabilities(tool)
                value = metric_func(capabilities.performance_characteristics)
                print(f"{value:<15}", end="")
            except Exception:
                print(f"{'Unknown':<15}", end="")
        
        print()


def demo_feature_queries():
    """Demonstrate feature availability queries"""
    print_section("Feature Availability Queries")
    
    tool_manager = ToolManager()
    
    # Query specific features
    queries = [
        ("Which tools support parallel processing?", Feature.PARALLEL_PROCESSING),
        ("Which tools support data deduplication?", Feature.DATA_DEDUPLICATION),
        ("Which tools support resume?", Feature.RESUME_SUPPORT),
        ("Which tools support regex patterns?", Feature.REGEX_PATTERNS)
    ]
    
    for question, feature in queries:
        print(f"\n{question}")
        print("-" * 80)
        
        tools = tool_manager.get_supported_tools()
        for tool_info in tools:
            if not tool_info.is_available:
                continue
            
            try:
                capabilities = tool_manager.get_tool_capabilities(tool_info.tool_name)
                
                if capabilities.has_feature(feature):
                    if capabilities.is_native_feature(feature):
                        print(f"  ✓ {tool_info.tool_name.upper()} (native)")
                    else:
                        print(f"  + {tool_info.tool_name.upper()} (via wrapper)")
                else:
                    print(f"  ✗ {tool_info.tool_name.upper()}")
            except Exception:
                pass


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 80)
    print("  TOOL MANAGER DEMONSTRATION")
    print("  TimeLocker Backup Operations - Tool Management System")
    print("=" * 80)
    
    try:
        # Run demonstrations
        demo_tool_detection()
        demo_capability_details()
        demo_tool_configuration()
        demo_compatibility_validation()
        demo_tool_comparison()
        demo_feature_queries()
        
        print_section("Demo Complete")
        print("The tool management system provides:")
        print("  • Automatic capability detection for backup tools")
        print("  • Intelligent configuration optimization")
        print("  • Job compatibility validation")
        print("  • Performance profiling and comparison")
        print("  • Feature availability queries")
        print("\nThis enables TimeLocker to work seamlessly with multiple backup tools")
        print("while providing consistent functionality and optimal performance.")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
