"""
Tests for BackupOrchestrator job execution capabilities.

This module tests the enhanced backup orchestrator functionality including
job validation, preparation, and execution with Policy Management and
Data Selection integration.
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from TimeLocker.interfaces.data_models import (
    BackupJobConfig,
    BackupJob,
    ExecutionMode,
    RetryConfig,
    NotificationConfig,
    ValidationResult as JobValidationResult
)
from TimeLocker.interfaces import BackupStatus
from TimeLocker.services.backup_orchestrator import BackupOrchestrator


class TestBackupOrchestratorJobExecution:
    """Test suite for backup orchestrator job execution capabilities"""
    
    @pytest.fixture
    def mock_repository_factory(self):
        """Create mock repository factory"""
        factory = Mock()
        mock_repo = Mock()
        mock_repo.backup_target.return_value = {
            'snapshot_id': 'test-snapshot-123',
            'files_processed': 100,
            'bytes_processed': 1024000
        }
        factory.create_repository.return_value = mock_repo
        return factory
    
    @pytest.fixture
    def mock_configuration_provider(self):
        """Create mock configuration provider"""
        provider = Mock()
        provider.get_repositories.return_value = [
            {
                'name': 'test-repo',
                'id': 'test-repo-id',
                'uri': 'file:///tmp/test-repo'
            }
        ]
        provider.get_backup_targets.return_value = [
            {
                'name': 'test-target',
                'paths': ['/tmp/test-data'],
                'exclude_patterns': ['*.tmp'],
                'include_patterns': []
            }
        ]
        return provider
    
    @pytest.fixture
    def orchestrator(self, mock_repository_factory, mock_configuration_provider):
        """Create backup orchestrator instance"""
        return BackupOrchestrator(
            repository_factory=mock_repository_factory,
            configuration_provider=mock_configuration_provider,
            max_concurrent_backups=2
        )
    
    @pytest.fixture
    def sample_job_config(self):
        """Create sample job configuration"""
        return BackupJobConfig(
            job_id='test-job-001',
            repository_id='test-repo',
            target_names=['test-target'],
            execution_mode=ExecutionMode.ON_DEMAND,
            tool_type='restic',
            tags=['test', 'automated'],
            retry_config=RetryConfig(max_retries=2),
            notification_config=NotificationConfig(enabled=True)
        )
    
    def test_validate_job_configuration_valid(self, orchestrator, sample_job_config):
        """Test validation of valid job configuration"""
        result = orchestrator.validate_job_configuration(sample_job_config)
        
        assert isinstance(result, JobValidationResult)
        assert result.is_valid
        assert len(result.errors) == 0
        assert 'repository_validated' in result.validation_details
    
    def test_validate_job_configuration_invalid_repository(self, orchestrator):
        """Test validation with invalid repository"""
        job_config = BackupJobConfig(
            job_id='test-job-002',
            repository_id='nonexistent-repo',
            target_names=['test-target']
        )
        
        result = orchestrator.validate_job_configuration(job_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any('Repository' in error for error in result.errors)
    
    def test_validate_job_configuration_invalid_target(self, orchestrator):
        """Test validation with invalid target"""
        job_config = BackupJobConfig(
            job_id='test-job-003',
            repository_id='test-repo',
            target_names=['nonexistent-target']
        )
        
        result = orchestrator.validate_job_configuration(job_config)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any('target' in error.lower() for error in result.errors)
    
    def test_prepare_backup_job(self, orchestrator, sample_job_config):
        """Test backup job preparation"""
        backup_job = orchestrator.prepare_backup_job(sample_job_config)
        
        assert isinstance(backup_job, BackupJob)
        assert backup_job.config == sample_job_config
        assert backup_job.tool_configuration is not None
        assert backup_job.execution_context is not None
        assert len(backup_job.source_paths) > 0
        assert backup_job.tool_configuration.tool_type == 'restic'
    
    def test_prepare_backup_job_with_targets(self, orchestrator, sample_job_config):
        """Test job preparation includes target paths"""
        backup_job = orchestrator.prepare_backup_job(sample_job_config)
        
        assert '/tmp/test-data' in backup_job.source_paths
        assert '*.tmp' in backup_job.exclude_patterns
    
    def test_queue_backup_job(self, orchestrator, sample_job_config):
        """Test queueing a backup job"""
        job_id = orchestrator.queue_backup_job(sample_job_config)
        
        assert job_id == sample_job_config.job_id
        
        queued_jobs = orchestrator.get_queued_jobs()
        assert len(queued_jobs) == 1
        assert queued_jobs[0].job_id == sample_job_config.job_id
    
    def test_queue_invalid_job_fails(self, orchestrator):
        """Test queueing invalid job raises error"""
        invalid_config = BackupJobConfig(
            job_id='test-job-004',
            repository_id='nonexistent-repo',
            target_names=['test-target']
        )
        
        with pytest.raises(Exception):
            orchestrator.queue_backup_job(invalid_config)
    
    def test_cancel_queued_job(self, orchestrator, sample_job_config):
        """Test cancelling a queued job"""
        job_id = orchestrator.queue_backup_job(sample_job_config)
        
        result = orchestrator.cancel_queued_job(job_id)
        assert result is True
        
        queued_jobs = orchestrator.get_queued_jobs()
        assert len(queued_jobs) == 0
    
    def test_cancel_nonexistent_job(self, orchestrator):
        """Test cancelling nonexistent job returns False"""
        result = orchestrator.cancel_queued_job('nonexistent-job')
        assert result is False
    
    @patch('TimeLocker.services.backup_orchestrator.Path')
    def test_execute_job_dry_run(self, mock_path, orchestrator, sample_job_config):
        """Test dry run execution"""
        # Setup mock path
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_file.is_file.return_value = True
        mock_file.is_dir.return_value = False
        mock_file.stat.return_value.st_size = 1024
        mock_path.return_value = mock_file
        
        sample_job_config.dry_run = True
        backup_job = orchestrator.prepare_backup_job(sample_job_config)
        
        result = orchestrator._execute_job_dry_run(backup_job)
        
        assert result.status == BackupStatus.COMPLETED
        assert result.snapshot_id is not None
        assert 'dry-run' in result.snapshot_id
        assert result.metadata['dry_run'] is True
    
    def test_execute_backup_job_success(self, orchestrator, sample_job_config):
        """Test successful backup job execution"""
        result = orchestrator.execute_backup_job(sample_job_config)
        
        assert result.status == BackupStatus.COMPLETED
        assert result.snapshot_id == 'test-snapshot-123'
        assert result.files_processed == 100
        assert result.bytes_processed == 1024000
    
    def test_execute_backup_job_with_retry(self, orchestrator, sample_job_config, mock_repository_factory):
        """Test backup job execution with retry on failure"""
        # Make first attempt fail, second succeed
        mock_repo = mock_repository_factory.create_repository.return_value
        mock_repo.backup_target.side_effect = [
            Exception("Temporary failure"),
            {
                'snapshot_id': 'test-snapshot-retry',
                'files_processed': 50,
                'bytes_processed': 512000
            }
        ]
        
        sample_job_config.retry_config = RetryConfig(
            max_retries=2,
            base_delay_seconds=0.1  # Short delay for testing
        )
        
        result = orchestrator.execute_backup_job(sample_job_config)
        
        # Should succeed on retry
        assert result.status == BackupStatus.COMPLETED
        assert result.snapshot_id == 'test-snapshot-retry'
    
    def test_execute_backup_job_validation_failure(self, orchestrator):
        """Test job execution fails with invalid configuration"""
        invalid_config = BackupJobConfig(
            job_id='test-job-005',
            repository_id='nonexistent-repo',
            target_names=['test-target']
        )
        
        with pytest.raises(Exception) as exc_info:
            orchestrator.execute_backup_job(invalid_config)
        
        assert 'validation failed' in str(exc_info.value).lower()
    
    def test_job_config_with_policy_id(self, mock_repository_factory, mock_configuration_provider):
        """Test job configuration with policy ID"""
        # Create orchestrator with mock policy service
        mock_policy_service = Mock()
        orchestrator = BackupOrchestrator(
            repository_factory=mock_repository_factory,
            configuration_provider=mock_configuration_provider,
            policy_integration_service=mock_policy_service
        )
        
        job_config = BackupJobConfig(
            job_id='test-job-006',
            repository_id='test-repo',
            policy_id='test-policy-001',
            execution_mode=ExecutionMode.POLICY_DRIVEN
        )
        
        backup_job = orchestrator.prepare_backup_job(job_config)
        
        assert backup_job.policy_config is not None
        assert backup_job.policy_config['policy_id'] == 'test-policy-001'
    
    def test_job_config_with_data_selection_id(self, orchestrator):
        """Test job configuration with data selection ID"""
        job_config = BackupJobConfig(
            job_id='test-job-007',
            repository_id='test-repo',
            data_selection_id='test-selection-001',
            target_names=['test-target']
        )
        
        backup_job = orchestrator.prepare_backup_job(job_config)
        
        assert backup_job.data_selection_config is not None
        assert backup_job.data_selection_config['selection_id'] == 'test-selection-001'
    
    def test_job_execution_context(self, orchestrator, sample_job_config):
        """Test execution context is properly initialized"""
        backup_job = orchestrator.prepare_backup_job(sample_job_config)
        
        assert backup_job.execution_context is not None
        assert backup_job.execution_context.attempt_number == 1
        assert backup_job.execution_context.start_time > 0
        assert isinstance(backup_job.execution_context.previous_errors, list)
    
    def test_tool_configuration(self, orchestrator, sample_job_config):
        """Test tool configuration is properly set"""
        backup_job = orchestrator.prepare_backup_job(sample_job_config)
        
        assert backup_job.tool_configuration.tool_type == 'restic'
        assert backup_job.tool_configuration.encryption_enabled is True
        assert backup_job.tool_configuration.integrity_check_enabled is True
        assert 'tags' in backup_job.tool_configuration.tool_specific_options

    def test_dry_run_reports_selected_file_counts(self, orchestrator, tmp_path):
        """Ensure dry-run enumerates files from selection-applied source paths."""
        data_dir = tmp_path / "docs"
        data_dir.mkdir()
        sample_file = data_dir / "report.txt"
        sample_file.write_text("content")

        job_config = BackupJobConfig(
            job_id='dry-run-job',
            repository_id='test-repo',
            data_selection_id='selection-123',
            execution_mode=ExecutionMode.ON_DEMAND
        )
        backup_job = BackupJob(
            config=job_config,
            source_paths=[str(data_dir)],
            exclude_patterns=[],
            include_patterns=[]
        )

        result = orchestrator._execute_job_dry_run(backup_job)

        assert result.status == BackupStatus.COMPLETED
        assert result.files_processed == 1
        assert result.bytes_processed == len("content")
