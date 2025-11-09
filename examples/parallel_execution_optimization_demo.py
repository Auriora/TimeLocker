"""
Parallel Execution Optimization Demo

This example demonstrates the parallel execution optimization capabilities
for backup operations, including:
- Resource-aware parallelization configuration
- Dynamic adjustment based on system constraints
- Graceful degradation when resources are limited
- Performance monitoring and bottleneck identification
"""

import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_parallel_execution_optimization():
    """Demonstrate parallel execution optimization features"""
    
    print("=" * 80)
    print("Parallel Execution Optimization Demo")
    print("=" * 80)
    print()
    
    # Import required modules
    from TimeLocker.services.parallel_execution_optimizer import (
        ParallelExecutionOptimizer,
        SystemResources,
        ResourceConstraintLevel
    )
    from TimeLocker.services.tool_manager import ToolManager, Feature
    from TimeLocker.interfaces.data_models import (
        BackupJobConfig,
        BackupJob,
        ExecutionMode,
        ExecutionContext,
        ToolConfiguration,
        RetryConfig
    )
    
    # 1. Create parallel execution optimizer
    print("1. Creating Parallel Execution Optimizer")
    print("-" * 80)
    
    optimizer = ParallelExecutionOptimizer(
        enable_dynamic_adjustment=True,
        min_parallel_operations=1,
        max_parallel_operations=16
    )
    
    print(f"✓ Optimizer created with dynamic adjustment enabled")
    print(f"  Min parallel operations: 1")
    print(f"  Max parallel operations: 16")
    print()
    
    # 2. Get current system resources
    print("2. Analyzing System Resources")
    print("-" * 80)
    
    system_resources = optimizer.get_system_resources()
    
    print(f"System Resources:")
    print(f"  CPU Cores: {system_resources.cpu_count}")
    print(f"  CPU Usage: {system_resources.cpu_usage_percent:.1f}%")
    print(f"  Total Memory: {system_resources.memory_total_gb:.2f} GB")
    print(f"  Available Memory: {system_resources.memory_available_gb:.2f} GB")
    print(f"  Memory Usage: {system_resources.memory_usage_percent:.1f}%")
    print(f"  Disk I/O Busy: {system_resources.disk_io_busy_percent:.1f}%")
    print(f"  Constraint Level: {system_resources.get_constraint_level().value}")
    print()
    
    # 3. Create tool manager with parallel optimizer
    print("3. Creating Tool Manager with Parallel Optimization")
    print("-" * 80)
    
    tool_manager = ToolManager(parallel_optimizer=optimizer)
    
    print(f"✓ Tool manager created with integrated parallel optimizer")
    print()
    
    # 4. Get tool capabilities
    print("4. Detecting Tool Capabilities")
    print("-" * 80)
    
    try:
        capabilities = tool_manager.get_tool_capabilities('restic')
        
        print(f"Tool: {capabilities.tool_name} v{capabilities.version}")
        print(f"Parallel Processing Support: {capabilities.has_feature(Feature.PARALLEL_PROCESSING)}")
        print(f"Parallel Efficiency: {capabilities.performance_characteristics.parallel_efficiency:.2f}")
        print(f"Max Parallel Files: {capabilities.configuration_options.get('max_parallel_files', 'N/A')}")
        print()
    except Exception as e:
        print(f"⚠ Could not detect Restic: {e}")
        print("  Using simulated capabilities for demo")
        print()
    
    # 5. Create a backup job
    print("5. Creating Backup Job Configuration")
    print("-" * 80)
    
    job_config = BackupJobConfig(
        job_id="demo-parallel-job-001",
        repository_id="demo-repo",
        target_names=["demo-target"],
        tool_type="restic",
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(
            max_retries=3,
            base_delay_seconds=2.0,
            max_delay_seconds=60.0,
            backoff_multiplier=2.0
        ),
        priority=5,
        tags=["demo", "parallel-optimization"]
    )
    
    backup_job = BackupJob(
        config=job_config,
        tool_configuration=ToolConfiguration(
            tool_type="restic",
            parallel_operations=1,
            encryption_enabled=True,
            integrity_check_enabled=True
        ),
        execution_context=ExecutionContext(
            start_time=time.time(),
            attempt_number=1
        )
    )
    
    backup_job.source_paths = ["/tmp/demo-backup"]
    
    print(f"Job ID: {job_config.job_id}")
    print(f"Repository: {job_config.repository_id}")
    print(f"Tool: {job_config.tool_type}")
    print(f"Priority: {job_config.priority}")
    print()
    
    # 6. Calculate optimal parallelism
    print("6. Calculating Optimal Parallelism")
    print("-" * 80)
    
    try:
        capabilities = tool_manager.get_tool_capabilities('restic')
        
        parallel_config = optimizer.calculate_optimal_parallelism(
            capabilities=capabilities,
            job=backup_job,
            system_resources=system_resources
        )
        
        print(f"Optimization Results:")
        print(f"  Parallel Operations: {parallel_config.parallel_operations}")
        print(f"  Max Parallel Operations: {parallel_config.max_parallel_operations}")
        print(f"  Resource Constraint: {parallel_config.resource_constraint_level.value}")
        print(f"  Degradation Applied: {parallel_config.degradation_applied}")
        print()
        print(f"Optimization Reason:")
        print(f"  {parallel_config.optimization_reason}")
        print()
        
        if parallel_config.recommendations:
            print(f"Recommendations:")
            for i, rec in enumerate(parallel_config.recommendations, 1):
                print(f"  {i}. {rec}")
            print()
        
        # Update job configuration with optimized parallelism
        backup_job.tool_configuration.parallel_operations = parallel_config.parallel_operations
        
    except Exception as e:
        print(f"⚠ Could not calculate optimal parallelism: {e}")
        print()
    
    # 7. Configure tool for job
    print("7. Configuring Tool for Optimal Execution")
    print("-" * 80)
    
    try:
        tool_config = tool_manager.configure_tool_for_job('restic', backup_job)
        
        print(f"Tool Configuration:")
        print(f"  Parallel Operations: {tool_config.parallel_operations}")
        print(f"  Compression Level: {tool_config.compression_level}")
        print(f"  Encryption Enabled: {tool_config.encryption_enabled}")
        print(f"  Integrity Check Enabled: {tool_config.integrity_check_enabled}")
        print()
        
        if 'parallel_optimization' in tool_config.tool_specific_options:
            opt_details = tool_config.tool_specific_options['parallel_optimization']
            print(f"Parallel Optimization Details:")
            print(f"  Configured Parallelism: {opt_details['configured_parallelism']}")
            print(f"  Max Parallelism: {opt_details['max_parallelism']}")
            print(f"  Resource Constraint: {opt_details['resource_constraint']}")
            print(f"  Degradation Applied: {opt_details['degradation_applied']}")
            print()
        
    except Exception as e:
        print(f"⚠ Could not configure tool: {e}")
        print()
    
    # 8. Simulate parallel execution monitoring
    print("8. Simulating Parallel Execution Monitoring")
    print("-" * 80)
    
    operation_id = backup_job.config.job_id
    configured_parallelism = backup_job.tool_configuration.parallel_operations
    
    # Start monitoring
    tool_manager.monitor_parallel_execution(
        operation_id=operation_id,
        tool_type='restic',
        configured_parallelism=configured_parallelism
    )
    
    print(f"✓ Started monitoring for operation {operation_id}")
    print(f"  Configured parallelism: {configured_parallelism}")
    print()
    
    # Simulate execution with metrics updates
    print("Simulating execution progress...")
    
    # Update 1: Initial execution
    time.sleep(0.5)
    actual_parallelism = min(configured_parallelism, 6)  # Simulated actual parallelism
    tool_manager.update_parallel_execution_metrics(
        operation_id=operation_id,
        actual_parallelism=actual_parallelism,
        resource_usage={
            'cpu_usage_percent': 65.0,
            'memory_usage_percent': 55.0
        }
    )
    print(f"  Update 1: Actual parallelism={actual_parallelism}, CPU=65%, Memory=55%")
    
    # Update 2: Detect bottleneck
    time.sleep(0.5)
    tool_manager.update_parallel_execution_metrics(
        operation_id=operation_id,
        bottleneck="disk_io_saturation"
    )
    print(f"  Update 2: Bottleneck detected - disk I/O saturation")
    
    # Update 3: Resource constraint
    time.sleep(0.5)
    tool_manager.update_parallel_execution_metrics(
        operation_id=operation_id,
        resource_usage={
            'cpu_usage_percent': 85.0,
            'memory_usage_percent': 78.0
        }
    )
    print(f"  Update 3: Resource usage increased - CPU=85%, Memory=78%")
    print()
    
    # 9. Get execution report
    print("9. Parallel Execution Report")
    print("-" * 80)
    
    report = tool_manager.get_parallel_execution_report(operation_id)
    
    if report:
        print(f"Execution Metrics:")
        print(f"  Operation ID: {report['operation_id']}")
        print(f"  Configured Parallelism: {report['configured_parallelism']}")
        print(f"  Actual Parallelism: {report['actual_parallelism']}")
        print(f"  Parallel Efficiency: {report['parallel_efficiency']:.2f}")
        print(f"  Efficiency Rating: {report['efficiency_rating']}")
        print(f"  Degradation Events: {report['degradation_events']}")
        print()
        
        if report['resource_usage']:
            print(f"Resource Usage:")
            for resource, value in report['resource_usage'].items():
                print(f"  {resource}: {value:.1f}")
            print()
        
        if report['bottlenecks']:
            print(f"Bottlenecks Identified:")
            for i, bottleneck in enumerate(report['bottlenecks'], 1):
                print(f"  {i}. {bottleneck}")
            print()
    
    # 10. Demonstrate graceful degradation
    print("10. Demonstrating Graceful Degradation")
    print("-" * 80)
    
    print(f"Current parallelism: {configured_parallelism}")
    
    # Simulate failure requiring degradation
    new_parallelism = tool_manager.handle_parallel_execution_failure(
        operation_id=operation_id,
        current_parallelism=configured_parallelism,
        failure_reason="High resource contention detected"
    )
    
    print(f"After degradation: {new_parallelism}")
    print(f"Reduction: {configured_parallelism - new_parallelism} operations")
    print()
    
    # Get updated report
    updated_report = tool_manager.get_parallel_execution_report(operation_id)
    if updated_report:
        print(f"Updated Metrics:")
        print(f"  Degradation Events: {updated_report['degradation_events']}")
        print(f"  Latest Bottleneck: {updated_report['bottlenecks'][-1] if updated_report['bottlenecks'] else 'None'}")
        print()
    
    # 11. Test with different resource scenarios
    print("11. Testing Different Resource Scenarios")
    print("-" * 80)
    
    scenarios = [
        ("Low constraint", SystemResources(
            cpu_count=8, cpu_usage_percent=30.0,
            memory_total_gb=16.0, memory_available_gb=12.0,
            memory_usage_percent=25.0, disk_io_busy_percent=20.0
        )),
        ("Medium constraint", SystemResources(
            cpu_count=8, cpu_usage_percent=60.0,
            memory_total_gb=16.0, memory_available_gb=6.0,
            memory_usage_percent=62.0, disk_io_busy_percent=55.0
        )),
        ("High constraint", SystemResources(
            cpu_count=8, cpu_usage_percent=80.0,
            memory_total_gb=16.0, memory_available_gb=2.0,
            memory_usage_percent=87.0, disk_io_busy_percent=78.0
        )),
        ("Critical constraint", SystemResources(
            cpu_count=8, cpu_usage_percent=95.0,
            memory_total_gb=16.0, memory_available_gb=0.5,
            memory_usage_percent=96.0, disk_io_busy_percent=92.0
        ))
    ]
    
    try:
        capabilities = tool_manager.get_tool_capabilities('restic')
        
        for scenario_name, resources in scenarios:
            config = optimizer.calculate_optimal_parallelism(
                capabilities=capabilities,
                job=backup_job,
                system_resources=resources
            )
            
            print(f"{scenario_name}:")
            print(f"  Constraint Level: {resources.get_constraint_level().value}")
            print(f"  CPU: {resources.cpu_usage_percent:.0f}%, Memory: {resources.memory_usage_percent:.0f}%")
            print(f"  Optimal Parallelism: {config.parallel_operations}")
            print(f"  Degradation: {'Yes' if config.degradation_applied else 'No'}")
            print()
    
    except Exception as e:
        print(f"⚠ Could not test scenarios: {e}")
        print()
    
    print("=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        demo_parallel_execution_optimization()
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")
