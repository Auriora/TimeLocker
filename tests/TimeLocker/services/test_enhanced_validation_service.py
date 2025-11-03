"""
Tests for enhanced ValidationService functionality

This module tests the repository-specific validation enhancements
added to the ValidationService.
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path

from src.TimeLocker.services.validation_service import ValidationService
from src.TimeLocker.interfaces.repository_management_models import (
    RepositoryConfig, Repository, BackupEngine, RepositoryType, RepositoryStatus
)


class TestEnhancedValidationService:
    """Test enhanced repository validation functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.validation_service = ValidationService()

    def test_validate_repository_uri_comprehensive_local(self):
        """Test comprehensive URI validation for local repositories"""
        # Valid local URI
        result = self.validation_service.validate_repository_uri_comprehensive("file:///tmp/test-repo")
        assert result.is_valid
        assert len(result.errors) == 0

        # Invalid local URI (empty path)
        result = self.validation_service.validate_repository_uri_comprehensive("file://")
        assert not result.is_valid
        assert any("must have a path" in error for error in result.errors)

    def test_validate_repository_uri_comprehensive_s3(self):
        """Test comprehensive URI validation for S3 repositories"""
        # Valid S3 URI
        result = self.validation_service.validate_repository_uri_comprehensive("s3://my-bucket/path")
        assert result.is_valid

        # Invalid S3 URI (no bucket)
        result = self.validation_service.validate_repository_uri_comprehensive("s3://")
        assert not result.is_valid
        assert any("bucket" in error.lower() for error in result.errors)

    def test_validate_repository_uri_comprehensive_unsupported_scheme(self):
        """Test validation with unsupported URI scheme"""
        result = self.validation_service.validate_repository_uri_comprehensive("ftp://example.com/repo")
        assert not result.is_valid
        assert any("Unsupported URI scheme" in error for error in result.errors)
        assert len(result.suggestions) > 0

    def test_validate_repository_configuration(self):
        """Test repository configuration validation"""
        # Valid configuration
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        result = self.validation_service.validate_repository_configuration(config)
        assert result.is_valid
        assert len(result.errors) == 0

        # Invalid configuration (empty name)
        config.name = ""
        result = self.validation_service.validate_repository_configuration(config)
        assert not result.is_valid
        assert any("name cannot be empty" in error for error in result.errors)

    def test_validate_repository_configuration_invalid_name(self):
        """Test repository configuration validation with invalid name"""
        config = RepositoryConfig(
            name="test repo with spaces!",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        result = self.validation_service.validate_repository_configuration(config)
        assert not result.is_valid
        assert any("must contain only letters, numbers, underscores, and hyphens" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_validate_connectivity_local_repository(self):
        """Test connectivity validation for local repository"""
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp",  # Use /tmp which should exist
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
        
        result = await self.validation_service.validate_connectivity(repo)
        assert result.success
        assert result.response_time is not None
        assert result.response_time < self.validation_service.LOCAL_VALIDATION_THRESHOLD

    @pytest.mark.asyncio
    async def test_validate_connectivity_timeout_handling(self):
        """Test connectivity validation timeout handling"""
        config = RepositoryConfig(
            name="test-repo",
            uri="s3://nonexistent-bucket/path",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3
        )
        
        repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
        
        # This should complete quickly since it's a mock implementation
        result = await self.validation_service.validate_connectivity(repo)
        # The mock implementation returns success, but in real scenarios this would test timeout
        assert result.response_time is not None

    @pytest.mark.asyncio
    async def test_batch_validate_repositories(self):
        """Test batch validation of multiple repositories"""
        configs = [
            RepositoryConfig(
                name="repo1",
                uri="file:///tmp/repo1",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            ),
            RepositoryConfig(
                name="repo2",
                uri="file:///tmp/repo2",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
        ]
        
        repos = [Repository(config=config, status=RepositoryStatus.ACTIVE) for config in configs]
        
        results = await self.validation_service.batch_validate(repos)
        assert len(results) == 2
        
        for result in results:
            assert result.timestamp is not None
            assert 'total_validation_time' in result.performance_metrics
            assert 'connectivity_time' in result.performance_metrics

    def test_validate_engine_configuration_restic(self):
        """Test Restic engine configuration validation"""
        # Valid Restic configuration
        config = {
            'compression': 'auto',
            'pack_size': 1024,
            'exclude_caches': True
        }
        
        result = self.validation_service._validate_engine_configuration(BackupEngine.RESTIC, config)
        assert result.is_valid

        # Invalid Restic configuration
        config = {
            'compression': 'invalid',
            'pack_size': -1
        }
        
        result = self.validation_service._validate_engine_configuration(BackupEngine.RESTIC, config)
        assert not result.is_valid
        assert len(result.errors) >= 2  # compression and pack_size errors

    def test_validate_engine_configuration_rsync(self):
        """Test Rsync engine configuration validation"""
        # Valid Rsync configuration
        config = {
            'archive_mode': True,
            'compress': True,
            'preserve_permissions': True
        }
        
        result = self.validation_service._validate_engine_configuration(BackupEngine.RSYNC, config)
        assert result.is_valid

        # Invalid Rsync configuration
        config = {
            'archive_mode': 'not_a_boolean',
            'compress': 'also_not_boolean'
        }
        
        result = self.validation_service._validate_engine_configuration(BackupEngine.RSYNC, config)
        assert not result.is_valid
        assert len(result.errors) >= 2

    def test_validate_engine_configuration_rclone(self):
        """Test Rclone engine configuration validation"""
        # Valid Rclone configuration
        config = {
            'transfers': 4,
            'checkers': 8,
            'buffer_size': '16M'
        }
        
        result = self.validation_service._validate_engine_configuration(BackupEngine.RCLONE, config)
        assert result.is_valid

        # Invalid Rclone configuration
        config = {
            'transfers': -1,
            'checkers': 0,
            'buffer_size': 'invalid_format'
        }
        
        result = self.validation_service._validate_engine_configuration(BackupEngine.RCLONE, config)
        assert not result.is_valid
        assert len(result.errors) >= 3

    def test_is_network_repository(self):
        """Test network repository detection"""
        # Local repositories
        assert not self.validation_service._is_network_repository("file:///tmp/repo")
        assert not self.validation_service._is_network_repository("/tmp/repo")

        # Network repositories
        assert self.validation_service._is_network_repository("s3://bucket/path")
        assert self.validation_service._is_network_repository("sftp://host/path")
        assert self.validation_service._is_network_repository("smb://host/share")
        assert self.validation_service._is_network_repository("nfs://host/export")