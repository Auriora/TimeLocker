"""
Tests for Repository Error Handling and Recovery

This module tests error handling and recovery scenarios for repository management
including network failures, credential errors, and configuration corruption.
"""

import pytest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.TimeLocker.interfaces.repository_management_models import (
    Repository, RepositoryConfig, RepositoryStatus, BackupEngine, RepositoryType,
    ValidationResult, ConnectivityStatus, IntegrityStatus, RepositoryCreationOptions
)
from src.TimeLocker.services.repository_manager import RepositoryManager
from src.TimeLocker.services.validation_service import ValidationService
from src.TimeLocker.services.repository_credential_manager import RepositoryCredentialManager
from src.TimeLocker.interfaces.repository_management_models import (
    RepositoryError, RepositoryValidationError, BackendError
)
from src.TimeLocker.interfaces.exceptions import CredentialError


class TestNetworkFailureScenarios:
    """Test network failure scenarios and timeout handling"""
    
    @pytest.fixture
    def validation_service(self):
        """Create validation service"""
        return ValidationService()
    
    @pytest.fixture
    def repository_config(self):
        """Create network repository configuration"""
        return RepositoryConfig(
            name="network-repo",
            uri="s3://test-bucket/path",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3
        )
    
    @pytest.mark.asyncio
    async def test_network_timeout_during_validation(self, validation_service, repository_config):
        """Test handling of network timeout during repository validation"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock network timeout
        with patch.object(validation_service, '_test_repository_connectivity', 
                         side_effect=asyncio.TimeoutError("Connection timeout")):
            result = await validation_service.validate_connectivity(repo)
            
            # Should handle timeout gracefully
            assert result.success is False
            assert result.status == ConnectivityStatus.TIMEOUT
            assert "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_network_connection_refused(self, validation_service, repository_config):
        """Test handling of connection refused errors"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock connection refused
        with patch.object(validation_service, '_test_repository_connectivity',
                         side_effect=ConnectionRefusedError("Connection refused")):
            result = await validation_service.validate_connectivity(repo)
            
            assert result.success is False
            assert result.status == ConnectivityStatus.UNREACHABLE
            assert "refused" in result.error_message.lower() or "unreachable" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_network_dns_resolution_failure(self, validation_service, repository_config):
        """Test handling of DNS resolution failures"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock DNS failure
        with patch.object(validation_service, '_test_repository_connectivity',
                         side_effect=OSError("Name or service not known")):
            result = await validation_service.validate_connectivity(repo)
            
            assert result.success is False
            assert result.status == ConnectivityStatus.UNREACHABLE
    
    @pytest.mark.asyncio
    async def test_network_intermittent_failure_retry(self, validation_service, repository_config):
        """Test retry logic for intermittent network failures"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock intermittent failure (fails twice, succeeds third time)
        call_count = 0
        async def mock_connectivity():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary network error")
            return True
        
        with patch.object(validation_service, '_test_repository_connectivity', side_effect=mock_connectivity):
            # Enable retry logic
            validation_service.enable_retry = True
            validation_service.max_retries = 3
            
            result = await validation_service.validate_connectivity(repo)
            
            # Should eventually succeed after retries
            assert call_count == 3
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_network_timeout_with_custom_threshold(self, validation_service, repository_config):
        """Test network timeout with custom threshold"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Set custom timeout threshold
        original_threshold = validation_service.NETWORK_VALIDATION_THRESHOLD
        validation_service.NETWORK_VALIDATION_THRESHOLD = 5.0  # 5 seconds
        
        try:
            # Mock slow response
            async def slow_connectivity():
                await asyncio.sleep(6.0)  # Exceeds threshold
                return True
            
            with patch.object(validation_service, '_test_repository_connectivity', side_effect=slow_connectivity):
                # Should timeout before completion
                with pytest.raises(asyncio.TimeoutError):
                    await asyncio.wait_for(
                        validation_service.validate_connectivity(repo),
                        timeout=validation_service.NETWORK_VALIDATION_THRESHOLD
                    )
        finally:
            validation_service.NETWORK_VALIDATION_THRESHOLD = original_threshold
    
    @pytest.mark.asyncio
    async def test_network_ssl_certificate_error(self, validation_service, repository_config):
        """Test handling of SSL certificate errors"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock SSL certificate error
        import ssl
        with patch.object(validation_service, '_test_repository_connectivity',
                         side_effect=ssl.SSLError("Certificate verification failed")):
            result = await validation_service.validate_connectivity(repo)
            
            assert result.success is False
            assert "certificate" in result.error_message.lower() or "ssl" in result.error_message.lower()
            # Should provide suggestions for SSL issues
            assert len(result.recommendations) > 0


class TestCredentialErrorRecovery:
    """Test credential error recovery and fallback mechanisms"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def credential_manager(self, temp_dir):
        """Create credential manager"""
        from src.TimeLocker.security import SecurityService, CredentialManager
        
        cred_mgr = CredentialManager(config_dir=temp_dir)
        cred_mgr.unlock("test_master_password")
        
        security_service = Mock(spec=SecurityService)
        security_service.credential_manager = cred_mgr
        security_service.log_security_event = Mock()
        
        return RepositoryCredentialManager(security_service)
    
    @pytest.mark.asyncio
    async def test_credential_not_found_fallback_to_environment(self, credential_manager):
        """Test fallback to environment variables when credentials not found"""
        repo_id = "test-repo"
        
        # Set environment variable
        import os
        env_var = f"TIMELOCKER_{repo_id.upper().replace('-', '_')}_PASSWORD"
        os.environ[env_var] = "env-password"
        
        try:
            # Resolve credentials (should fall back to environment)
            with patch('getpass.getpass', return_value=None):
                with patch('builtins.input', return_value=''):
                    resolved = credential_manager.resolve_credentials(repo_id, 'password')
            
            assert resolved == "env-password"
        finally:
            del os.environ[env_var]
    
    @pytest.mark.asyncio
    async def test_credential_retrieval_when_locked(self, temp_dir):
        """Test credential retrieval when credential manager is locked"""
        from src.TimeLocker.security import SecurityService, CredentialManager
        
        # Create locked credential manager
        cred_mgr = CredentialManager(config_dir=temp_dir)
        # Don't unlock it
        
        security_service = Mock(spec=SecurityService)
        security_service.credential_manager = cred_mgr
        security_service.log_security_event = Mock()
        
        credential_manager = RepositoryCredentialManager(security_service)
        
        # Try to retrieve credentials - should raise error
        with pytest.raises(CredentialError, match="credential manager is locked"):
            await credential_manager.retrieve_credentials("test-repo")
    
    @pytest.mark.asyncio
    async def test_credential_corruption_detection(self, credential_manager):
        """Test detection of corrupted credentials"""
        repo_id = "test-repo"
        
        # Store valid credentials
        await credential_manager.store_credentials(repo_id, {'password': 'test-password'})
        
        # Corrupt the stored credentials by directly modifying the file
        # This simulates file system corruption
        cred_file = credential_manager.credential_manager.config_dir / "credentials.json"
        if cred_file.exists():
            with open(cred_file, 'w') as f:
                f.write("corrupted data {{{")
        
        # Try to retrieve - should handle corruption gracefully
        try:
            credentials = await credential_manager.retrieve_credentials(repo_id)
            # Should return None or raise appropriate error
            assert credentials is None or isinstance(credentials, dict)
        except (CredentialError, json.JSONDecodeError):
            # Expected behavior for corrupted data
            pass
    
    @pytest.mark.asyncio
    async def test_credential_rotation_failure_rollback(self, credential_manager):
        """Test rollback when credential rotation fails"""
        repo_id = "test-repo"
        
        # Store initial credentials
        await credential_manager.store_credentials(repo_id, {'password': 'old-password'})
        
        # Verify initial credentials
        initial_creds = await credential_manager.retrieve_credentials(repo_id)
        assert initial_creds['password'] == 'old-password'
        
        # Mock rotation failure
        with patch.object(credential_manager.credential_manager, 'store_repository_password',
                         side_effect=Exception("Storage failure")):
            # Try to rotate - should fail
            with pytest.raises(Exception):
                await credential_manager.rotate_password(repo_id, 'new-password')
        
        # Verify credentials are unchanged (rollback)
        current_creds = await credential_manager.retrieve_credentials(repo_id)
        assert current_creds['password'] == 'old-password'
    
    @pytest.mark.asyncio
    @patch('getpass.getpass', return_value='interactive-password')
    async def test_credential_interactive_prompt_fallback(self, mock_getpass, credential_manager):
        """Test fallback to interactive prompt when other methods fail"""
        repo_id = "test-repo"
        
        # No stored credentials, no environment variables
        # Should fall back to interactive prompt
        resolved = credential_manager.resolve_credentials(repo_id, 'password')
        
        assert resolved == 'interactive-password'
        mock_getpass.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_credential_invalid_format_handling(self, credential_manager):
        """Test handling of invalid credential format"""
        repo_id = "test-repo"
        
        # Try to store invalid credentials
        invalid_credentials = {
            'password': None,  # Invalid: None password
            'backend_type': 'invalid_backend'
        }
        
        # Should handle gracefully or raise appropriate error
        try:
            result = await credential_manager.store_credentials(repo_id, invalid_credentials)
            # If it succeeds, verify it handled None appropriately
            if result:
                retrieved = await credential_manager.retrieve_credentials(repo_id)
                # Should not have stored None password
                assert retrieved is None or retrieved.get('password') != None
        except (ValueError, CredentialError):
            # Expected behavior for invalid credentials
            pass


class TestConfigurationCorruptionRecovery:
    """Test configuration corruption detection and recovery"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def repository_manager(self, temp_dir):
        """Create repository manager with temp config directory"""
        manager = RepositoryManager()
        manager.config_dir = temp_dir
        manager._repositories = {}
        return manager
    
    def test_detect_corrupted_configuration_file(self, repository_manager, temp_dir):
        """Test detection of corrupted configuration file"""
        # Create corrupted config file
        config_file = temp_dir / "repositories.json"
        with open(config_file, 'w') as f:
            f.write("corrupted json {{{")
        
        # Try to load - should detect corruption
        with pytest.raises((json.JSONDecodeError, RepositoryError)):
            repository_manager._load_repositories_from_file(config_file)
    
    def test_recover_from_backup_configuration(self, repository_manager, temp_dir):
        """Test recovery from backup configuration"""
        # Create valid backup
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()
        
        backup_config = {
            "test-repo": {
                "name": "test-repo",
                "uri": "file:///tmp/test",
                "engine": "restic",
                "type": "local"
            }
        }
        
        backup_file = backup_dir / "repositories_backup_20240101.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_config, f)
        
        # Corrupt main config
        config_file = temp_dir / "repositories.json"
        with open(config_file, 'w') as f:
            f.write("corrupted")
        
        # Try to recover from backup
        repository_manager.backup_dir = backup_dir
        recovered = repository_manager._recover_from_backup()
        
        assert recovered is True
        assert len(repository_manager._repositories) > 0
    
    def test_configuration_validation_before_save(self, repository_manager):
        """Test configuration validation before saving"""
        # Create invalid repository config
        invalid_config = RepositoryConfig(
            name="test-repo",
            uri="",  # Invalid: empty URI
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        repo = Repository(config=invalid_config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["test-repo"] = repo
        
        # Try to save - should validate and fail
        with pytest.raises((ValueError, RepositoryValidationError)):
            repository_manager._validate_before_save()
    
    def test_atomic_configuration_save(self, repository_manager, temp_dir):
        """Test atomic configuration save to prevent partial writes"""
        # Add valid repository
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["test-repo"] = repo
        
        config_file = temp_dir / "repositories.json"
        
        # Mock write failure midway
        original_write = json.dump
        def failing_write(*args, **kwargs):
            raise IOError("Disk full")
        
        with patch('json.dump', side_effect=failing_write):
            # Try to save - should fail
            with pytest.raises(IOError):
                repository_manager._save_repositories_to_file(config_file)
        
        # Original file should not be corrupted (atomic write)
        # Either it doesn't exist or contains valid data
        if config_file.exists():
            with open(config_file, 'r') as f:
                data = json.load(f)  # Should not raise JSONDecodeError
    
    def test_configuration_backup_before_risky_operation(self, repository_manager, temp_dir):
        """Test automatic backup before risky operations"""
        # Add repository
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["test-repo"] = repo
        
        # Save initial state
        config_file = temp_dir / "repositories.json"
        repository_manager._save_repositories_to_file(config_file)
        
        # Perform risky operation (should create backup first)
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()
        repository_manager.backup_dir = backup_dir
        
        backup_id = repository_manager._backup_configuration("test-repo")
        
        # Verify backup was created
        assert backup_id is not None
        backup_files = list(backup_dir.glob("test-repo_*.json"))
        assert len(backup_files) > 0
    
    def test_configuration_backup_cleanup(self, repository_manager, temp_dir):
        """Test cleanup of old configuration backups"""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()
        repository_manager.backup_dir = backup_dir
        
        # Create multiple backups (more than max)
        for i in range(10):
            backup_file = backup_dir / f"test-repo_backup_{i}.json"
            with open(backup_file, 'w') as f:
                json.dump({"backup": i}, f)
        
        # Cleanup should keep only last 5
        repository_manager._cleanup_old_backups("test-repo", keep_count=5)
        
        remaining_backups = list(backup_dir.glob("test-repo_*.json"))
        assert len(remaining_backups) == 5
    
    def test_detect_schema_version_mismatch(self, repository_manager, temp_dir):
        """Test detection of schema version mismatch"""
        # Create config with old schema version
        old_config = {
            "schema_version": "1.0",  # Old version
            "repositories": {
                "test-repo": {
                    "name": "test-repo",
                    "path": "/tmp/test"  # Old field name
                }
            }
        }
        
        config_file = temp_dir / "repositories.json"
        with open(config_file, 'w') as f:
            json.dump(old_config, f)
        
        # Try to load - should detect version mismatch
        with pytest.raises((RepositoryError, ValueError)):
            repository_manager._load_repositories_from_file(config_file)


class TestRepositoryManagerErrorRecovery:
    """Test repository manager error recovery scenarios"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with mocked dependencies"""
        manager = RepositoryManager()
        manager._repositories = {}
        return manager
    
    @pytest.mark.asyncio
    async def test_repository_creation_rollback_on_failure(self, repository_manager):
        """Test rollback when repository creation fails"""
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        # Mock validation to succeed
        repository_manager._validate_configuration = AsyncMock(
            return_value=Mock(is_valid=True, errors=[])
        )
        
        # Mock repository factory to fail
        repository_manager._repository_factory = Mock()
        repository_manager._repository_factory.create_repository.side_effect = Exception("Creation failed")
        
        # Try to create - should fail and rollback
        with pytest.raises(Exception):
            await repository_manager.create_repository(config, RepositoryCreationOptions())
        
        # Verify repository was not added
        assert "test-repo" not in repository_manager._repositories
    
    @pytest.mark.asyncio
    async def test_repository_update_rollback_on_validation_failure(self, repository_manager):
        """Test rollback when repository update validation fails"""
        # Add initial repository
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Original description"
        )
        repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["test-repo"] = repo
        
        # Mock validation to fail
        repository_manager._validate_configuration = AsyncMock(
            return_value=Mock(is_valid=False, errors=["Invalid configuration"])
        )
        
        # Try to update - should fail
        with pytest.raises(RepositoryValidationError):
            await repository_manager.update_repository("test-repo", {'description': 'New description'})
        
        # Verify original configuration is unchanged
        assert repository_manager._repositories["test-repo"].config.description == "Original description"
    
    @pytest.mark.asyncio
    async def test_concurrent_modification_detection(self, repository_manager):
        """Test detection of concurrent modifications"""
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["test-repo"] = repo
        
        # Mock lock acquisition
        repository_manager._acquire_lock = AsyncMock()
        repository_manager._release_lock = AsyncMock()
        
        # Simulate concurrent modification
        async def modify_concurrently():
            await asyncio.sleep(0.1)
            repository_manager._repositories["test-repo"].config.description = "Concurrent change"
        
        # Start concurrent modification
        concurrent_task = asyncio.create_task(modify_concurrently())
        
        # Try to update
        repository_manager._validate_configuration = AsyncMock(
            return_value=Mock(is_valid=True, errors=[])
        )
        repository_manager._save_repositories = Mock()
        
        await repository_manager.update_repository("test-repo", {'description': 'My change'})
        
        # Wait for concurrent task
        await concurrent_task
        
        # One of the changes should win (last write wins)
        assert repository_manager._repositories["test-repo"].config.description in ["My change", "Concurrent change"]
    
    @pytest.mark.asyncio
    async def test_validation_failure_recovery(self, repository_manager):
        """Test recovery from validation failures"""
        config = RepositoryConfig(
            name="test-repo",
            uri="s3://test-bucket/path",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3
        )
        repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["test-repo"] = repo
        
        # Mock validation to fail
        repository_manager.validate_repository = AsyncMock(
            return_value=ValidationResult(
                success=False,
                timestamp=datetime.utcnow(),
                connectivity_status=ConnectivityStatus.UNREACHABLE,
                integrity_status=IntegrityStatus.UNKNOWN,
                error_details=["Network unreachable"]
            )
        )
        
        # Validate repository
        result = await repository_manager.validate_repository(repo)
        
        # Should record failure but not crash
        assert result.success is False
        assert repo.last_validated is not None
        assert repo.validation_result is not None
        assert repo.validation_result.success is False


class TestBatchOperationErrorHandling:
    """Test error handling in batch operations"""
    
    @pytest.fixture
    def validation_service(self):
        """Create validation service"""
        return ValidationService()
    
    @pytest.mark.asyncio
    async def test_batch_validate_partial_failures(self, validation_service):
        """Test batch validation with some repositories failing"""
        # Create multiple repositories
        repos = []
        for i in range(5):
            config = RepositoryConfig(
                name=f"repo-{i}",
                uri=f"file:///tmp/repo-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repos.append(Repository(config=config, status=RepositoryStatus.ACTIVE))
        
        # Mock validation to fail for some repositories
        call_count = 0
        async def mock_validate(repo):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                # Fail every other repository
                raise ConnectionError("Network error")
            return ValidationResult(
                success=True,
                timestamp=datetime.utcnow(),
                connectivity_status=ConnectivityStatus.CONNECTED,
                integrity_status=IntegrityStatus.VALID
            )
        
        with patch.object(validation_service, 'validate_repository', side_effect=mock_validate):
            results = await validation_service.batch_validate(repos)
        
        # Should have results for all repositories
        assert len(results) == 5
        
        # Some should succeed, some should fail
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        
        assert len(successes) > 0
        assert len(failures) > 0
    
    @pytest.mark.asyncio
    async def test_batch_validate_continues_on_error(self, validation_service):
        """Test that batch validation continues even if some validations fail"""
        repos = []
        for i in range(3):
            config = RepositoryConfig(
                name=f"repo-{i}",
                uri=f"file:///tmp/repo-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repos.append(Repository(config=config, status=RepositoryStatus.ACTIVE))
        
        # Mock first validation to raise exception
        call_count = 0
        async def mock_validate(repo):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Unexpected error")
            return ValidationResult(
                success=True,
                timestamp=datetime.utcnow(),
                connectivity_status=ConnectivityStatus.CONNECTED,
                integrity_status=IntegrityStatus.VALID
            )
        
        with patch.object(validation_service, 'validate_repository', side_effect=mock_validate):
            results = await validation_service.batch_validate(repos)
        
        # Should have attempted all validations
        assert call_count == 3
        assert len(results) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
