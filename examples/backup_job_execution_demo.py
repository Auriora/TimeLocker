#!/usr/bin/env python3
"""
Demonstration of enhanced backup orchestrator job execution capabilities.

This example shows how to use the new job-based backup execution features
including validation, preparation, queueing, and execution with retry logic.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from TimeLocker.interfaces.data_models import (
    BackupJobConfig,
    ExecutionMode,
    RetryConfig,
    NotificationConfig
)
from TimeLocker.services.backup_orchestrator import BackupOrchestrator
from TimeLocker.services.repository_factory import RepositoryFactory
from TimeLocker.services.configuration_service import ConfigurationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_job_validation():
    """Demonstrate job configuration validation"""
    logger.info("=== Job Validation Demo ===")
    
    # Create services
    config_service = ConfigurationService()
    repo_factory = RepositoryFactory(config_service)
    orchestrator = BackupOrchestrator(repo_factory, config_service)
    
    # Create a job configuration
    job_config = BackupJobConfig(
        job_id='demo-job-001',
        repository_id='local-backup',
        target_names=['documents'],
        execution_mode=ExecutionMode.ON_DEMAND,
        tool_type='restic',
        tags=['demo', 'manual']
    )
    
    # Validate the job
    validation_result = orchestrator.validate_job_configuration(job_config)
    
    logger.info(f"Validation result: valid={validation_result.is_valid}")
    if validation_result.errors:
        logger.error(f"Validation errors: {validation_result.errors}")
    if validation_result.warnings:
        logger.warning(f"Validation warnings: {validation_result.warnings}")
    
    return validation_result.is_valid


def demo_job_preparation():
    """Demonstrate job preparation with policy and data selection integration"""
    logger.info("\n=== Job Preparation Demo ===")
    
    # Create services
    config_service = ConfigurationService()
    repo_factory = RepositoryFactory(config_service)
    orchestrator = BackupOrchestrator(repo_factory, config_service)
    
    # Create a job configuration with policy and data selection
    job_config = BackupJobConfig(
        job_id='demo-job-002',
        repository_id='local-backup',
        target_names=['documents'],
        policy_id='daily-backup-policy',
        data_selection_id='important-files',
        execution_mode=ExecutionMode.POLICY_DRIVEN,
        tool_type='restic',
        tags=['demo', 'policy-driven']
    )
    
    # Prepare the job
    try:
        backup_job = orchestrator.prepare_backup_job(job_config)
        
        logger.info(f"Job prepared successfully:")
        logger.info(f"  - Source paths: {len(backup_job.source_paths)}")
        logger.info(f"  - Exclude patterns: {len(backup_job.exclude_patterns)}")
        logger.info(f"  - Tool type: {backup_job.tool_configuration.tool_type}")
        logger.info(f"  - Policy integrated: {backup_job.policy_config is not None}")
        logger.info(f"  - Data selection integrated: {backup_job.data_selection_config is not None}")
        
        return backup_job
    except Exception as e:
        logger.error(f"Job preparation failed: {e}")
        return None


def demo_job_queueing():
    """Demonstrate job queueing and management"""
    logger.info("\n=== Job Queueing Demo ===")
    
    # Create services
    config_service = ConfigurationService()
    repo_factory = RepositoryFactory(config_service)
    orchestrator = BackupOrchestrator(repo_factory, config_service)
    
    # Create multiple job configurations
    jobs = [
        BackupJobConfig(
            job_id=f'demo-job-queue-{i}',
            repository_id='local-backup',
            target_names=['documents'],
            execution_mode=ExecutionMode.ON_DEMAND,
            tool_type='restic',
            tags=['demo', 'queued']
        )
        for i in range(3)
    ]
    
    # Queue the jobs
    for job_config in jobs:
        try:
            job_id = orchestrator.queue_backup_job(job_config)
            logger.info(f"Queued job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to queue job: {e}")
    
    # List queued jobs
    queued_jobs = orchestrator.get_queued_jobs()
    logger.info(f"\nTotal queued jobs: {len(queued_jobs)}")
    
    # Cancel a job
    if queued_jobs:
        job_to_cancel = queued_jobs[0].job_id
        cancelled = orchestrator.cancel_queued_job(job_to_cancel)
        logger.info(f"Cancelled job {job_to_cancel}: {cancelled}")
        
        # List remaining jobs
        remaining_jobs = orchestrator.get_queued_jobs()
        logger.info(f"Remaining queued jobs: {len(remaining_jobs)}")


def demo_job_execution_with_retry():
    """Demonstrate job execution with retry logic"""
    logger.info("\n=== Job Execution with Retry Demo ===")
    
    # Create services
    config_service = ConfigurationService()
    repo_factory = RepositoryFactory(config_service)
    orchestrator = BackupOrchestrator(repo_factory, config_service)
    
    # Create a job configuration with custom retry settings
    job_config = BackupJobConfig(
        job_id='demo-job-retry',
        repository_id='local-backup',
        target_names=['documents'],
        execution_mode=ExecutionMode.ON_DEMAND,
        tool_type='restic',
        tags=['demo', 'retry'],
        retry_config=RetryConfig(
            max_retries=3,
            base_delay_seconds=2.0,
            backoff_multiplier=2.0,
            max_delay_seconds=30.0
        ),
        notification_config=NotificationConfig(
            enabled=True,
            notify_on_success=True,
            notify_on_failure=True
        )
    )
    
    # Execute the job
    try:
        result = orchestrator.execute_backup_job(job_config)
        
        logger.info(f"Job execution result:")
        logger.info(f"  - Status: {result.status.value}")
        logger.info(f"  - Snapshot ID: {result.snapshot_id}")
        logger.info(f"  - Files processed: {result.files_processed}")
        logger.info(f"  - Bytes processed: {result.bytes_processed}")
        logger.info(f"  - Duration: {result.duration:.2f}s" if result.duration else "  - Duration: N/A")
        
        if result.errors:
            logger.error(f"  - Errors: {result.errors}")
        if result.warnings:
            logger.warning(f"  - Warnings: {result.warnings}")
        
        return result
    except Exception as e:
        logger.error(f"Job execution failed: {e}")
        return None


def demo_dry_run_execution():
    """Demonstrate dry run execution"""
    logger.info("\n=== Dry Run Execution Demo ===")
    
    # Create services
    config_service = ConfigurationService()
    repo_factory = RepositoryFactory(config_service)
    orchestrator = BackupOrchestrator(repo_factory, config_service)
    
    # Create a job configuration with dry_run enabled
    job_config = BackupJobConfig(
        job_id='demo-job-dryrun',
        repository_id='local-backup',
        target_names=['documents'],
        execution_mode=ExecutionMode.ON_DEMAND,
        tool_type='restic',
        tags=['demo', 'dry-run'],
        dry_run=True
    )
    
    # Execute the dry run
    try:
        result = orchestrator.execute_backup_job(job_config)
        
        logger.info(f"Dry run result:")
        logger.info(f"  - Status: {result.status.value}")
        logger.info(f"  - Estimated files: {result.files_processed}")
        logger.info(f"  - Estimated size: {result.bytes_processed / (1024**3):.2f} GB")
        logger.info(f"  - Snapshot ID: {result.snapshot_id}")
        
        return result
    except Exception as e:
        logger.error(f"Dry run failed: {e}")
        return None


def main():
    """Run all demonstrations"""
    logger.info("Starting Backup Job Execution Demonstrations\n")
    
    try:
        # Run demonstrations
        demo_job_validation()
        demo_job_preparation()
        demo_job_queueing()
        demo_dry_run_execution()
        demo_job_execution_with_retry()
        
        logger.info("\n=== All Demonstrations Complete ===")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
