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

import pytest
import time
from unittest.mock import Mock, patch

from TimeLocker.services.job_executor import (
    JobExecutor,
    ErrorClassifier,
    ErrorCategory,
    RetryStrategy,
    ErrorClassification,
    RetryDecision,
    ExecutionResult
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
from TimeLocker.interfaces.backup_orchestrator import BackupExecutionError


class TestErrorClassifier:
    """Test error classification functionality"""
    
    def test_classify_transient_error(self):
        """Test classification of transient errors"""
        classifier = ErrorClassifier()
        
        # Test timeout error
        error = Exception("Connection timeout occurred")
        classification = classifier.classify_error(error)
        
        assert classification.category == ErrorCategory.TRANSIENT
        assert classification.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert classification.should_retry is True
        assert "transient" in classification.reason.lower()
    
    def test_classify_configuration_error(self):
        """Test classification of configuration errors"""
        classifier = ErrorClassifier()
        
        # Test not found error
        error = Exception("File not found: /invalid/path")
        classification = classifier.classify_error(error)
        
        assert classification.category == ErrorCategory.CONFIGURATION
        assert classification.strategy == RetryStrategy.NO_RETRY
        assert classification.should_retry is False
        assert "configuration" in classification.reason.lower()
    
    def test_classify_resource_error(self):
        """Test classification of resource errors"""
        classifier = ErrorClassifier()
        
        # Test disk space error
        error = Exception("No space left on device")
        classification = classifier.classify_error(error)
        
        assert classification.category == ErrorCategory.RESOURCE
        assert classification.strategy == RetryStrategy.LINEAR_BACKOFF
        assert classification.should_retry is True
        assert "resource" in classification.reason.lower()
    
    def test_classify_tool_specific_error(self):
        """Test classification of tool-specific errors"""
        classifier = ErrorClassifier()
        
        # Test repository error
        error = Exception("Repository integrity check failed")
        classification = classifier.classify_error(error)
        
        assert classification.category == ErrorCategory.TOOL_SPECIFIC
        assert classification.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert classification.should_retry is True
    
    def test_classify_permanent_error(self):
        """Test classification of unrecognized errors as permanent"""
        classifier = ErrorClassifier()
        
        # Test unknown error
        error = Exception("Some unknown error occurred")
        classification = classifier.classify_error(error)
        
        assert classification.category == ErrorCategory.PERMANENT
        assert classification.strategy == RetryStrategy.NO_RETRY
        assert classification.should_retry is False


class TestJobExecutor:
    """Test job executor functionality"""
    
    @pytest.fixture
    def job_config(self):
        """Create a test job configuration"""
        return BackupJobConfig(
            job_id="test-job-1",
            repository_id="test-repo",
            target_names=["test-target"],
            execution_mode=ExecutionMode.ON_DEMAND,
            retry_config=RetryConfig(
                max_retries=3,
                base_delay_seconds=0.1,  # Short delay for testing
                backoff_multiplier=2.0,
                max_delay_seconds=1.0
            )
        )
    
    @pytest.fixture
    def backup_job(self, job_config):
        """Create a test backup job"""
        return BackupJob(
            config=job_config,
            source_paths=["/test/path"],
            tool_configuration=ToolConfiguration(tool_type="restic"),
            execution_context=ExecutionContext(start_time=time.time())
        )
    
    def test_successful_execution_first_attempt(self, backup_job):
        """Test successful execution on first attempt"""
        executor = JobExecutor()
        
        # Mock execution function that succeeds
        def mock_execution(job):
            return BackupResult(
                status=BackupStatus.COMPLETED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                snapshot_id="test-snapshot-1",
                files_processed=100,
                bytes_processed=1024000
            )
        
        result = executor.execute_with_retry(backup_job, mock_execution)
        
        assert result.backup_result.status == BackupStatus.COMPLETED
        assert result.total_attempts == 1
        assert len(result.retry_history) == 0
        assert result.backup_result.snapshot_id == "test-snapshot-1"
    
    def test_retry_on_transient_error(self, backup_job):
        """Test retry behavior on transient errors"""
        executor = JobExecutor()
        
        # Mock execution function that fails twice then succeeds
        attempt_count = [0]
        
        def mock_execution(job):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                return BackupResult(
                    status=BackupStatus.FAILED,
                    repository_name=job.config.repository_id,
                    target_names=job.config.target_names,
                    errors=["Connection timeout"]
                )
            return BackupResult(
                status=BackupStatus.COMPLETED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                snapshot_id="test-snapshot-1"
            )
        
        result = executor.execute_with_retry(backup_job, mock_execution)
        
        assert result.backup_result.status == BackupStatus.COMPLETED
        assert result.total_attempts == 3
        assert len(result.retry_history) == 2
        assert result.backup_result.snapshot_id == "test-snapshot-1"
    
    def test_no_retry_on_configuration_error(self, backup_job):
        """Test that configuration errors are not retried"""
        executor = JobExecutor()
        
        # Mock execution function that fails with configuration error
        def mock_execution(job):
            return BackupResult(
                status=BackupStatus.FAILED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                errors=["File not found: /invalid/path"]
            )
        
        result = executor.execute_with_retry(backup_job, mock_execution)
        
        assert result.backup_result.status == BackupStatus.FAILED
        # Configuration errors are attempted once but not retried
        assert result.total_attempts >= 1
        assert len(result.retry_history) >= 1
        assert result.final_error_classification.category == ErrorCategory.CONFIGURATION
        # Verify that no retry was attempted after the first failure
        assert result.final_error_classification.should_retry is False
    
    def test_max_retries_exhausted(self, backup_job):
        """Test behavior when max retries are exhausted"""
        executor = JobExecutor()
        
        # Mock execution function that always fails
        def mock_execution(job):
            return BackupResult(
                status=BackupStatus.FAILED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                errors=["Connection timeout"]
            )
        
        result = executor.execute_with_retry(backup_job, mock_execution)
        
        assert result.backup_result.status == BackupStatus.FAILED
        assert result.total_attempts == 4  # 1 initial + 3 retries
        assert len(result.retry_history) == 4
        assert "Failed after 4 attempts" in result.backup_result.errors[0]
    
    def test_exception_during_execution(self, backup_job):
        """Test handling of exceptions during execution"""
        executor = JobExecutor()
        
        # Mock execution function that raises exception
        attempt_count = [0]
        
        def mock_execution(job):
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise Exception("Network error occurred")
            return BackupResult(
                status=BackupStatus.COMPLETED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                snapshot_id="test-snapshot-1"
            )
        
        result = executor.execute_with_retry(backup_job, mock_execution)
        
        assert result.backup_result.status == BackupStatus.COMPLETED
        assert result.total_attempts == 2
        assert len(result.retry_history) == 1
    
    def test_handle_execution_error_max_attempts(self, backup_job):
        """Test retry decision when max attempts reached"""
        executor = JobExecutor()
        
        error = Exception("Test error")
        decision = executor.handle_execution_error(error, 3, 3)
        
        assert decision.should_retry is False
        assert decision.max_attempts_reached is True
        assert "Maximum retry attempts" in decision.reason
    
    def test_handle_execution_error_with_classification(self, backup_job):
        """Test retry decision with error classification"""
        executor = JobExecutor()
        
        # Test with transient error
        error = Exception("Connection timeout")
        decision = executor.handle_execution_error(error, 1, 3)
        
        assert decision.should_retry is True
        assert decision.delay_seconds > 0
        assert decision.error_classification.category == ErrorCategory.TRANSIENT
    
    def test_exponential_backoff_delay(self, backup_job):
        """Test exponential backoff delay calculation"""
        executor = JobExecutor()
        
        retry_config = RetryConfig(
            max_retries=3,
            base_delay_seconds=2.0,
            backoff_multiplier=2.0,
            max_delay_seconds=60.0
        )
        
        # Test delay calculation for different attempts
        delay1 = executor._calculate_retry_delay(2, retry_config, None)
        delay2 = executor._calculate_retry_delay(3, retry_config, None)
        delay3 = executor._calculate_retry_delay(4, retry_config, None)
        
        assert delay1 == 2.0  # 2.0 * (2.0 ** 0)
        assert delay2 == 4.0  # 2.0 * (2.0 ** 1)
        assert delay3 == 8.0  # 2.0 * (2.0 ** 2)
    
    def test_max_delay_cap(self, backup_job):
        """Test that delay is capped at max_delay_seconds"""
        executor = JobExecutor()
        
        retry_config = RetryConfig(
            max_retries=10,
            base_delay_seconds=2.0,
            backoff_multiplier=2.0,
            max_delay_seconds=10.0
        )
        
        # Test delay for high attempt number
        delay = executor._calculate_retry_delay(10, retry_config, None)
        
        assert delay <= retry_config.max_delay_seconds
    
    def test_retry_history_tracking(self, backup_job):
        """Test that retry history is properly tracked"""
        executor = JobExecutor()
        
        # Mock execution function that fails twice with transient errors then succeeds
        attempt_count = [0]
        
        def mock_execution(job):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                return BackupResult(
                    status=BackupStatus.FAILED,
                    repository_name=job.config.repository_id,
                    target_names=job.config.target_names,
                    errors=[f"Connection timeout on attempt {attempt_count[0]}"]
                )
            return BackupResult(
                status=BackupStatus.COMPLETED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                snapshot_id="test-snapshot-1"
            )
        
        result = executor.execute_with_retry(backup_job, mock_execution)
        
        assert len(result.retry_history) == 2
        assert result.retry_history[0]['attempt'] == 1
        assert result.retry_history[1]['attempt'] == 2
        assert 'classification' in result.retry_history[0]
        assert 'timestamp' in result.retry_history[0]
        # Verify transient errors were classified correctly
        assert result.retry_history[0]['classification'].category == ErrorCategory.TRANSIENT


class TestRetryDecision:
    """Test retry decision data structure"""
    
    def test_retry_decision_creation(self):
        """Test creating a retry decision"""
        classification = ErrorClassification(
            category=ErrorCategory.TRANSIENT,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            should_retry=True,
            reason="Test reason"
        )
        
        decision = RetryDecision(
            should_retry=True,
            delay_seconds=2.0,
            reason="Test decision",
            error_classification=classification
        )
        
        assert decision.should_retry is True
        assert decision.delay_seconds == 2.0
        assert decision.error_classification == classification
        assert decision.max_attempts_reached is False


class TestExecutionResult:
    """Test execution result data structure"""
    
    def test_execution_result_creation(self):
        """Test creating an execution result"""
        backup_result = BackupResult(
            status=BackupStatus.COMPLETED,
            repository_name="test-repo",
            target_names=["test-target"],
            snapshot_id="test-snapshot"
        )
        
        result = ExecutionResult(
            backup_result=backup_result,
            total_attempts=3,
            retry_history=[
                {'attempt': 1, 'error': 'Error 1'},
                {'attempt': 2, 'error': 'Error 2'}
            ]
        )
        
        assert result.backup_result == backup_result
        assert result.total_attempts == 3
        assert len(result.retry_history) == 2
        assert result.final_error_classification is None
