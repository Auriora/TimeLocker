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
Job Executor Demo

This example demonstrates the advanced retry logic capabilities of the JobExecutor
for backup operations, including error classification and exponential backoff.
"""

import time
from TimeLocker.services.job_executor import (
    JobExecutor,
    ErrorClassifier,
    ErrorCategory,
    RetryStrategy
)
from TimeLocker.interfaces.data_models import (
    BackupJob,
    BackupJobConfig,
    BackupResult,
    BackupStatus,
    RetryConfig,
    ExecutionMode,
    ExecutionContext,
    ToolConfiguration
)


def demo_error_classification():
    """Demonstrate error classification capabilities"""
    print("=" * 80)
    print("Error Classification Demo")
    print("=" * 80)
    
    classifier = ErrorClassifier()
    
    # Test different error types
    test_errors = [
        ("Connection timeout", "Transient network error"),
        ("File not found: /invalid/path", "Configuration error"),
        ("No space left on device", "Resource constraint"),
        ("Repository integrity check failed", "Tool-specific error"),
        ("Unknown error occurred", "Unclassified error")
    ]
    
    for error_msg, description in test_errors:
        error = Exception(error_msg)
        classification = classifier.classify_error(error)
        
        print(f"\n{description}:")
        print(f"  Error: {error_msg}")
        print(f"  Category: {classification.category.value}")
        print(f"  Strategy: {classification.strategy.value}")
        print(f"  Should Retry: {classification.should_retry}")
        print(f"  Reason: {classification.reason}")
        if classification.suggested_action:
            print(f"  Suggested Action: {classification.suggested_action}")


def demo_successful_execution():
    """Demonstrate successful job execution on first attempt"""
    print("\n" + "=" * 80)
    print("Successful Execution Demo")
    print("=" * 80)
    
    # Create job configuration
    job_config = BackupJobConfig(
        job_id="demo-job-1",
        repository_id="demo-repo",
        target_names=["demo-target"],
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(
            max_retries=3,
            base_delay_seconds=1.0,
            backoff_multiplier=2.0
        )
    )
    
    # Create backup job
    backup_job = BackupJob(
        config=job_config,
        source_paths=["/demo/path"],
        tool_configuration=ToolConfiguration(tool_type="restic"),
        execution_context=ExecutionContext(start_time=time.time())
    )
    
    # Mock execution function that succeeds
    def mock_successful_execution(job):
        print(f"\n  Executing backup for job: {job.config.job_id}")
        return BackupResult(
            status=BackupStatus.COMPLETED,
            repository_name=job.config.repository_id,
            target_names=job.config.target_names,
            snapshot_id="demo-snapshot-123",
            files_processed=1000,
            bytes_processed=10485760  # 10 MB
        )
    
    # Execute with JobExecutor
    executor = JobExecutor()
    result = executor.execute_with_retry(backup_job, mock_successful_execution)
    
    print(f"\nExecution Result:")
    print(f"  Status: {result.backup_result.status.value}")
    print(f"  Total Attempts: {result.total_attempts}")
    print(f"  Snapshot ID: {result.backup_result.snapshot_id}")
    print(f"  Files Processed: {result.backup_result.files_processed}")
    print(f"  Bytes Processed: {result.backup_result.bytes_processed}")


def demo_retry_on_transient_error():
    """Demonstrate retry behavior on transient errors"""
    print("\n" + "=" * 80)
    print("Retry on Transient Error Demo")
    print("=" * 80)
    
    # Create job configuration with short delays for demo
    job_config = BackupJobConfig(
        job_id="demo-job-2",
        repository_id="demo-repo",
        target_names=["demo-target"],
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(
            max_retries=3,
            base_delay_seconds=0.5,
            backoff_multiplier=2.0
        )
    )
    
    backup_job = BackupJob(
        config=job_config,
        source_paths=["/demo/path"],
        tool_configuration=ToolConfiguration(tool_type="restic"),
        execution_context=ExecutionContext(start_time=time.time())
    )
    
    # Mock execution function that fails twice then succeeds
    attempt_count = [0]
    
    def mock_retry_execution(job):
        attempt_count[0] += 1
        print(f"\n  Attempt {attempt_count[0]}: Executing backup for job: {job.config.job_id}")
        
        if attempt_count[0] < 3:
            print(f"  Attempt {attempt_count[0]}: Failed with transient error")
            return BackupResult(
                status=BackupStatus.FAILED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                errors=[f"Connection timeout on attempt {attempt_count[0]}"]
            )
        
        print(f"  Attempt {attempt_count[0]}: Success!")
        return BackupResult(
            status=BackupStatus.COMPLETED,
            repository_name=job.config.repository_id,
            target_names=job.config.target_names,
            snapshot_id="demo-snapshot-retry",
            files_processed=500,
            bytes_processed=5242880  # 5 MB
        )
    
    # Execute with JobExecutor
    executor = JobExecutor()
    result = executor.execute_with_retry(backup_job, mock_retry_execution)
    
    print(f"\nExecution Result:")
    print(f"  Status: {result.backup_result.status.value}")
    print(f"  Total Attempts: {result.total_attempts}")
    print(f"  Retry History: {len(result.retry_history)} retries")
    
    for i, retry in enumerate(result.retry_history, 1):
        print(f"\n  Retry {i}:")
        print(f"    Attempt: {retry['attempt']}")
        print(f"    Error: {retry['error']}")
        print(f"    Category: {retry['classification'].category.value}")


def demo_no_retry_on_configuration_error():
    """Demonstrate that configuration errors are not retried"""
    print("\n" + "=" * 80)
    print("No Retry on Configuration Error Demo")
    print("=" * 80)
    
    job_config = BackupJobConfig(
        job_id="demo-job-3",
        repository_id="demo-repo",
        target_names=["demo-target"],
        execution_mode=ExecutionMode.ON_DEMAND,
        retry_config=RetryConfig(max_retries=3)
    )
    
    backup_job = BackupJob(
        config=job_config,
        source_paths=["/demo/path"],
        tool_configuration=ToolConfiguration(tool_type="restic"),
        execution_context=ExecutionContext(start_time=time.time())
    )
    
    # Mock execution function that fails with configuration error
    def mock_config_error_execution(job):
        print(f"\n  Executing backup for job: {job.config.job_id}")
        print(f"  Failed with configuration error")
        return BackupResult(
            status=BackupStatus.FAILED,
            repository_name=job.config.repository_id,
            target_names=job.config.target_names,
            errors=["File not found: /invalid/path"]
        )
    
    # Execute with JobExecutor
    executor = JobExecutor()
    result = executor.execute_with_retry(backup_job, mock_config_error_execution)
    
    print(f"\nExecution Result:")
    print(f"  Status: {result.backup_result.status.value}")
    print(f"  Total Attempts: {result.total_attempts}")
    print(f"  Error Category: {result.final_error_classification.category.value}")
    print(f"  Should Retry: {result.final_error_classification.should_retry}")
    print(f"  Suggested Action: {result.final_error_classification.suggested_action}")


def demo_exponential_backoff():
    """Demonstrate exponential backoff delay calculation"""
    print("\n" + "=" * 80)
    print("Exponential Backoff Demo")
    print("=" * 80)
    
    retry_config = RetryConfig(
        max_retries=5,
        base_delay_seconds=1.0,
        backoff_multiplier=2.0,
        max_delay_seconds=30.0
    )
    
    executor = JobExecutor()
    
    print(f"\nRetry Configuration:")
    print(f"  Base Delay: {retry_config.base_delay_seconds}s")
    print(f"  Backoff Multiplier: {retry_config.backoff_multiplier}x")
    print(f"  Max Delay: {retry_config.max_delay_seconds}s")
    
    print(f"\nCalculated Delays:")
    for attempt in range(2, 7):
        delay = executor._calculate_retry_delay(attempt, retry_config, None)
        print(f"  Attempt {attempt}: {delay:.2f}s delay")


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("JobExecutor Advanced Retry Logic Demo")
    print("=" * 80)
    
    try:
        demo_error_classification()
        demo_successful_execution()
        demo_retry_on_transient_error()
        demo_no_retry_on_configuration_error()
        demo_exponential_backoff()
        
        print("\n" + "=" * 80)
        print("Demo completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
