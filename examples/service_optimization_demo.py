#!/usr/bin/env python3
"""
Service Communication Optimization Demo

This script demonstrates the service communication optimization features
including connection pooling, asynchronous operations, performance monitoring,
and optimization recommendations.
"""

import time
import logging
from pathlib import Path
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.interfaces.service_interface import ServiceInterface
from TimeLocker.interfaces.integration_data_models import ServiceContext
from TimeLocker.integration.service_manager import ServiceManager
from TimeLocker.integration.optimized_service_context import optimized_service, create_async_operation
from TimeLocker.config.configuration_manager import ConfigurationManager


class DemoService(ServiceInterface):
    """Demo service for testing optimization features."""
    
    def __init__(self):
        self.initialized = False
        self.operation_count = 0
    
    def initialize(self, context: ServiceContext) -> bool:
        """Initialize the demo service."""
        logger.info(f"Initializing DemoService {id(self)}")
        time.sleep(0.1)  # Simulate initialization time
        self.initialized = True
        return True
    
    def shutdown(self) -> None:
        """Shutdown the demo service."""
        logger.info(f"Shutting down DemoService {id(self)}")
        self.initialized = False
    
    def health_check(self) -> bool:
        """Check service health."""
        return self.initialized
    
    def get_capabilities(self) -> List[str]:
        """Get service capabilities."""
        return ["demo", "testing"]
    
    def perform_operation(self, duration: float = 0.5) -> str:
        """Perform a demo operation."""
        if not self.initialized:
            raise RuntimeError("Service not initialized")
        
        self.operation_count += 1
        logger.info(f"DemoService {id(self)} performing operation {self.operation_count}")
        
        # Simulate work
        time.sleep(duration)
        
        return f"Operation {self.operation_count} completed"
    
    def long_running_operation(self, duration: float = 5.0) -> str:
        """Perform a long-running operation."""
        logger.info(f"DemoService {id(self)} starting long-running operation")
        
        # Simulate long work with progress
        steps = 10
        step_duration = duration / steps
        
        for i in range(steps):
            time.sleep(step_duration)
            progress = (i + 1) / steps * 100
            logger.info(f"Long operation progress: {progress:.1f}%")
        
        return f"Long operation completed after {duration}s"


def demo_connection_pooling(service_manager: ServiceManager):
    """Demonstrate connection pooling optimization."""
    logger.info("=== Connection Pooling Demo ===")
    
    # Create connection pool for DemoService
    service_manager.create_service_connection_pool(
        service_type=DemoService,
        min_connections=2,
        max_connections=5,
        max_idle_time_seconds=30
    )
    
    # Perform multiple operations using pooled connections
    for i in range(10):
        with optimized_service(service_manager, DemoService, f"operation_{i}") as demo_service:
            result = demo_service.perform_operation(0.2)
            logger.info(f"Operation {i}: {result}")
    
    # Show pool statistics
    stats = service_manager.get_optimization_statistics()
    pool_stats = stats['connection_pools'].get('DemoService', {})
    logger.info(f"Pool statistics: {pool_stats}")


def demo_async_operations(service_manager: ServiceManager):
    """Demonstrate asynchronous operations."""
    logger.info("=== Async Operations Demo ===")
    
    # Submit multiple async operations
    async_ops = []
    
    for i in range(3):
        operation_id = f"async_op_{i}"
        async_op = create_async_operation(service_manager, operation_id, f"Long Operation {i}")
        
        # Define operation function
        def long_operation(duration: float):
            with optimized_service(service_manager, DemoService, f"async_{operation_id}") as demo_service:
                return demo_service.long_running_operation(duration)
        
        # Submit operation
        async_op.submit(
            long_operation,
            2.0 + i,  # Different durations
            completion_callback=lambda op_id, result: logger.info(f"Async operation {op_id} completed: {result}"),
            error_callback=lambda op_id, error: logger.error(f"Async operation {op_id} failed: {error}")
        )
        
        async_ops.append(async_op)
    
    # Monitor operations
    logger.info("Monitoring async operations...")
    while True:
        active_ops = service_manager._optimization_manager._async_manager.get_active_operations()
        if not active_ops:
            break
        
        logger.info(f"Active operations: {len(active_ops)}")
        for async_op in async_ops:
            status = async_op.get_status()
            logger.info(f"Operation {async_op.operation_id}: {status['status']}")
        
        time.sleep(1)
    
    logger.info("All async operations completed")


def demo_performance_monitoring(service_manager: ServiceManager):
    """Demonstrate performance monitoring and alerts."""
    logger.info("=== Performance Monitoring Demo ===")
    
    # Set performance thresholds
    service_manager.set_performance_threshold(
        service_name="DemoService",
        operation_type="perform_operation",
        max_duration_ms=300,  # 300ms threshold
        max_error_rate=0.1,
        alert_after_violations=2
    )
    
    # Perform operations with varying performance
    operations = [
        ("fast", 0.1),
        ("normal", 0.2),
        ("slow", 0.4),  # This should trigger threshold violation
        ("very_slow", 0.6),  # This should trigger alert
        ("fast", 0.1),
    ]
    
    for op_name, duration in operations:
        try:
            with optimized_service(service_manager, DemoService, "performance_test") as demo_service:
                result = demo_service.perform_operation(duration)
                logger.info(f"{op_name} operation: {result}")
        except Exception as e:
            logger.error(f"{op_name} operation failed: {e}")
        
        time.sleep(0.5)  # Brief pause between operations
    
    # Show performance statistics
    stats = service_manager.get_optimization_statistics()
    performance_summary = stats.get('performance_summary', {})
    logger.info(f"Performance summary: {performance_summary}")
    
    # Show bottlenecks and recommendations
    bottlenecks = service_manager.get_service_bottlenecks()
    recommendations = service_manager.get_performance_recommendations()
    
    logger.info(f"Identified bottlenecks: {bottlenecks}")
    logger.info(f"Optimization recommendations: {recommendations}")


def main():
    """Main demo function."""
    logger.info("Starting Service Communication Optimization Demo")
    
    try:
        # Create configuration manager (minimal setup for demo)
        config_manager = ConfigurationManager()
        
        # Create service manager with minimal context
        # The ServiceManager will create its own registry and event bus
        from TimeLocker.integration.service_manager import ServiceRegistry
        
        # Create a temporary registry for context creation
        temp_registry = ServiceRegistry()
        
        # Create service context
        context = ServiceContext(
            config_manager=config_manager,
            event_bus=None,  # Will be created by ServiceManager
            service_registry=temp_registry
        )
        
        # Create service manager
        service_manager = ServiceManager(context)
        
        # Register demo service
        demo_service = DemoService()
        service_manager.register_service(DemoService, demo_service)
        
        # Initialize services
        service_manager.initialize_services()
        
        # Run demos
        demo_connection_pooling(service_manager)
        demo_async_operations(service_manager)
        demo_performance_monitoring(service_manager)
        
        # Show final optimization statistics
        logger.info("=== Final Optimization Statistics ===")
        final_stats = service_manager.get_optimization_statistics()
        
        logger.info("Connection Pools:")
        for service_name, pool_stats in final_stats.get('connection_pools', {}).items():
            logger.info(f"  {service_name}: {pool_stats['total_operations']} ops, "
                       f"{pool_stats['average_operation_time_ms']:.1f}ms avg")
        
        logger.info("Performance Summary:")
        perf_summary = final_stats.get('performance_summary', {})
        for service_name, service_stats in perf_summary.get('services', {}).items():
            logger.info(f"  {service_name}: {service_stats['total_operations']} ops, "
                       f"{service_stats['average_time_ms']:.1f}ms avg, "
                       f"{service_stats['error_rate']:.1%} error rate")
        
        # Cleanup
        service_manager.shutdown_services()
        
        logger.info("Demo completed successfully")
    
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())