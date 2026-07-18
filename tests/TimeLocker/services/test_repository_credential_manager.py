"""
Tests for Repository Credential Manager

This module tests the repository credential management functionality including
Security Services integration, credential resolution order, and rotation.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from TimeLocker.services.repository_credential_manager import RepositoryCredentialManager
from TimeLocker.security import SecurityService, CredentialManager, SecurityEvent, SecurityLevel
from TimeLocker.interfaces.exceptions import CredentialError


class TestRepositoryCredentialManager:
    """Test Repository Credential Manager functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def mock_security_service(self, temp_dir):
        """Create mock security service with credential manager"""
        # Create real credential manager for testing
        credential_manager = CredentialManager(config_dir=temp_dir)
        credential_manager.unlock("test_master_password")
        
        # Create mock security service
        security_service = Mock(spec=SecurityService)
        security_service.credential_manager = credential_manager
        security_service.log_security_event = Mock()
        
        return security_service
    
    @pytest.fixture
    def credential_manager(self, mock_security_service):
        """Create repository credential manager"""
        return RepositoryCredentialManager(mock_security_service)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_repository_password(self, credential_manager):
        """Test storing repository password"""
        repo_id = "test-repo-1"
        credentials = {
            'password': 'test-password-123'
        }
        
        # Store credentials
        result = await credential_manager.store_credentials(repo_id, credentials)
        
        assert result is True
        
        # Verify password was stored
        stored_password = credential_manager.credential_manager.get_repository_password(repo_id)
        assert stored_password == 'test-password-123'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_backend_credentials(self, credential_manager):
        """Test storing backend credentials"""
        repo_id = "test-repo-2"
        credentials = {
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'region': 'us-west-2'
            }
        }
        
        # Store credentials
        result = await credential_manager.store_credentials(repo_id, credentials)
        
        assert result is True
        
        # Verify backend credentials were stored
        stored_creds = credential_manager.credential_manager.get_repository_backend_credentials(
            repo_id, 's3'
        )
        assert stored_creds['access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
        assert stored_creds['secret_access_key'] == 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_combined_credentials(self, credential_manager):
        """Test storing both password and backend credentials"""
        repo_id = "test-repo-3"
        credentials = {
            'password': 'repo-password',
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'test-key',
                'secret_access_key': 'test-secret'
            }
        }
        
        # Store credentials
        result = await credential_manager.store_credentials(repo_id, credentials)
        
        assert result is True
        
        # Verify both were stored
        password = credential_manager.credential_manager.get_repository_password(repo_id)
        assert password == 'repo-password'
        
        backend_creds = credential_manager.credential_manager.get_repository_backend_credentials(
            repo_id, 's3'
        )
        assert backend_creds['access_key_id'] == 'test-key'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retrieve_repository_password(self, credential_manager):
        """Test retrieving repository password"""
        repo_id = "test-repo-4"
        
        # Store password first
        await credential_manager.store_credentials(repo_id, {'password': 'test-pass'})
        
        # Retrieve credentials
        credentials = await credential_manager.retrieve_credentials(repo_id)
        
        assert credentials is not None
        assert 'password' in credentials
        assert credentials['password'] == 'test-pass'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retrieve_backend_credentials(self, credential_manager):
        """Test retrieving backend credentials"""
        repo_id = "test-repo-5"
        
        # Store backend credentials
        await credential_manager.store_credentials(repo_id, {
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'test-key',
                'secret_access_key': 'test-secret'
            }
        })
        
        # Retrieve credentials
        credentials = await credential_manager.retrieve_credentials(repo_id)
        
        assert credentials is not None
        assert 'backend_type' in credentials
        assert credentials['backend_type'] == 's3'
        assert 'backend_credentials' in credentials
        assert credentials['backend_credentials']['access_key_id'] == 'test-key'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retrieve_nonexistent_credentials(self, credential_manager):
        """Test retrieving credentials for non-existent repository"""
        credentials = await credential_manager.retrieve_credentials("nonexistent-repo")
        
        assert credentials is None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rotate_password(self, credential_manager):
        """Test rotating repository password"""
        repo_id = "test-repo-6"
        
        # Store initial password
        await credential_manager.store_credentials(repo_id, {'password': 'old-password'})
        
        # Rotate password
        result = await credential_manager.rotate_password(repo_id, 'new-password')
        
        assert result is True
        
        # Verify new password is stored
        credentials = await credential_manager.retrieve_credentials(repo_id)
        assert credentials['password'] == 'new-password'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rotate_backend_credentials(self, credential_manager):
        """Test rotating backend credentials"""
        repo_id = "test-repo-7"
        
        # Store initial credentials
        await credential_manager.store_credentials(repo_id, {
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'old-key',
                'secret_access_key': 'old-secret'
            }
        })
        
        # Rotate backend credentials
        new_creds = {
            'access_key_id': 'new-key',
            'secret_access_key': 'new-secret'
        }
        result = await credential_manager.rotate_backend_credentials(repo_id, 's3', new_creds)
        
        assert result is True
        
        # Verify new credentials are stored
        credentials = await credential_manager.retrieve_credentials(repo_id)
        assert credentials['backend_credentials']['access_key_id'] == 'new-key'
        assert credentials['backend_credentials']['secret_access_key'] == 'new-secret'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rotate_credentials_full(self, credential_manager):
        """Test rotating all credentials at once"""
        repo_id = "test-repo-8"
        
        # Store initial credentials
        await credential_manager.store_credentials(repo_id, {
            'password': 'old-password',
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'old-key',
                'secret_access_key': 'old-secret'
            }
        })
        
        # Rotate all credentials
        new_credentials = {
            'password': 'new-password',
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'new-key',
                'secret_access_key': 'new-secret'
            }
        }
        result = await credential_manager.rotate_credentials(repo_id, new_credentials)
        
        assert result is True
        
        # Verify all new credentials are stored
        credentials = await credential_manager.retrieve_credentials(repo_id)
        assert credentials['password'] == 'new-password'
        assert credentials['backend_credentials']['access_key_id'] == 'new-key'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_remove_credentials(self, credential_manager):
        """Test removing repository credentials"""
        repo_id = "test-repo-9"
        
        # Store credentials
        await credential_manager.store_credentials(repo_id, {
            'password': 'test-password',
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'test-key',
                'secret_access_key': 'test-secret'
            }
        })
        
        # Remove credentials
        result = await credential_manager.remove_credentials(repo_id)
        
        assert result is True
        
        # Verify credentials are removed
        credentials = await credential_manager.retrieve_credentials(repo_id)
        assert credentials is None
    
    @pytest.mark.unit
    def test_resolve_credentials_from_stored(self, credential_manager):
        """Test credential resolution from stored credentials"""
        repo_id = "test-repo-10"
        
        # Store password
        credential_manager.credential_manager.store_repository_password(repo_id, 'stored-password')
        
        # Resolve credentials
        resolved = credential_manager.resolve_credentials(repo_id, 'password')
        
        assert resolved == 'stored-password'
    
    @pytest.mark.unit
    @patch('getpass.getpass', return_value=None)
    @patch('builtins.input', return_value='')
    def test_resolve_credentials_from_environment(self, mock_input, mock_getpass, credential_manager):
        """Test credential resolution from environment variables"""
        repo_id = "test-repo-11"
        
        # Set environment variable (note: repo_id.upper() doesn't replace hyphens)
        env_var = f"TIMELOCKER_{repo_id.upper()}_PASSWORD"
        os.environ[env_var] = 'env-password'
        
        try:
            # Resolve credentials (should fall back to environment)
            resolved = credential_manager.resolve_credentials(repo_id, 'password')
            
            assert resolved == 'env-password'
        finally:
            # Clean up environment variable
            del os.environ[env_var]
    
    @pytest.mark.unit
    @patch('getpass.getpass', return_value=None)
    @patch('builtins.input', return_value='')
    def test_resolve_credentials_from_generic_environment(self, mock_input, mock_getpass, credential_manager):
        """Test credential resolution from generic environment variable"""
        repo_id = "test-repo-12"
        
        # Set generic environment variable
        os.environ['TIMELOCKER_REPOSITORY_PASSWORD'] = 'generic-password'
        
        try:
            # Resolve credentials
            resolved = credential_manager.resolve_credentials(repo_id, 'password')
            
            assert resolved == 'generic-password'
        finally:
            # Clean up environment variable
            del os.environ['TIMELOCKER_REPOSITORY_PASSWORD']
    
    @pytest.mark.unit
    @patch('getpass.getpass', return_value=None)
    @patch('builtins.input', return_value='')
    def test_resolve_credentials_order(self, mock_input, mock_getpass, credential_manager):
        """Test credential resolution order: stored > environment > interactive"""
        repo_id = "test-repo-13"
        
        # Store password
        credential_manager.credential_manager.store_repository_password(repo_id, 'stored-password')
        
        # Set environment variable (should be ignored since stored exists)
        env_var = f"TIMELOCKER_{repo_id.upper()}_PASSWORD"
        os.environ[env_var] = 'env-password'
        
        try:
            # Resolve credentials (should use stored)
            resolved = credential_manager.resolve_credentials(repo_id, 'password')
            
            assert resolved == 'stored-password'
        finally:
            # Clean up environment variable
            del os.environ[env_var]
    
    @pytest.mark.unit
    def test_list_repository_credentials(self, credential_manager):
        """Test listing repositories with stored credentials"""
        # Store credentials for multiple repositories
        repos = ['repo-a', 'repo-b', 'repo-c']
        for repo in repos:
            credential_manager.credential_manager.store_repository_password(repo, f'password-{repo}')
        
        # List repositories
        stored_repos = credential_manager.list_repository_credentials()
        
        assert set(stored_repos) == set(repos)
    
    @pytest.mark.unit
    def test_has_credentials(self, credential_manager):
        """Test checking if repository has credentials"""
        repo_id = "test-repo-14"
        
        # Initially no credentials
        assert credential_manager.has_credentials(repo_id) is False
        
        # Store password
        credential_manager.credential_manager.store_repository_password(repo_id, 'test-password')
        
        # Now has credentials
        assert credential_manager.has_credentials(repo_id) is True
    
    @pytest.mark.unit
    def test_has_backend_credentials(self, credential_manager):
        """Test checking if repository has backend credentials"""
        repo_id = "test-repo-15"
        
        # Initially no credentials
        assert credential_manager.has_credentials(repo_id) is False
        
        # Store backend credentials
        credential_manager.credential_manager.store_repository_backend_credentials(
            repo_id, 's3', {'access_key_id': 'test-key'}
        )
        
        # Now has credentials
        assert credential_manager.has_credentials(repo_id) is True
    
    @pytest.mark.unit
    def test_get_credential_metadata(self, credential_manager):
        """Test getting credential metadata"""
        repo_id = "test-repo-16"
        
        # Store credentials
        credential_manager.credential_manager.store_repository_password(repo_id, 'test-password')
        credential_manager.credential_manager.store_repository_backend_credentials(
            repo_id, 's3', {'access_key_id': 'test-key'}
        )
        
        # Get metadata
        metadata = credential_manager.get_credential_metadata(repo_id)
        
        assert metadata is not None
        assert 'backend_credentials' in metadata
        assert 's3' in metadata['backend_credentials']
        assert metadata['backend_credentials']['s3'] is True
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_security_event_logging_on_store(self, credential_manager, mock_security_service):
        """Test that security events are logged when storing credentials"""
        repo_id = "test-repo-17"
        
        # Store credentials
        await credential_manager.store_credentials(repo_id, {'password': 'test-password'})
        
        # Verify security event was logged
        mock_security_service.log_security_event.assert_called()
        
        # Check event details
        call_args = mock_security_service.log_security_event.call_args[0][0]
        assert call_args.event_type == "credential_storage"
        assert call_args.repository_id == repo_id
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_security_event_logging_on_retrieve(self, credential_manager, mock_security_service):
        """Test that security events are logged when retrieving credentials"""
        repo_id = "test-repo-18"
        
        # Store credentials first
        await credential_manager.store_credentials(repo_id, {'password': 'test-password'})
        
        # Reset mock
        mock_security_service.log_security_event.reset_mock()
        
        # Retrieve credentials
        await credential_manager.retrieve_credentials(repo_id)
        
        # Verify security event was logged
        mock_security_service.log_security_event.assert_called()
        
        # Check event details
        call_args = mock_security_service.log_security_event.call_args[0][0]
        assert call_args.event_type == "credential_retrieval"
        assert call_args.repository_id == repo_id
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_security_event_logging_on_rotation(self, credential_manager, mock_security_service):
        """Test that security events are logged when rotating credentials"""
        repo_id = "test-repo-19"
        
        # Store initial credentials
        await credential_manager.store_credentials(repo_id, {'password': 'old-password'})
        
        # Reset mock
        mock_security_service.log_security_event.reset_mock()
        
        # Rotate credentials
        await credential_manager.rotate_password(repo_id, 'new-password')
        
        # Verify security event was logged
        mock_security_service.log_security_event.assert_called()
        
        # Check event details
        call_args = mock_security_service.log_security_event.call_args[0][0]
        assert call_args.event_type == "credential_rotation"
        assert call_args.repository_id == repo_id
        assert call_args.level == SecurityLevel.HIGH
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_security_event_logging_on_removal(self, credential_manager, mock_security_service):
        """Test that security events are logged when removing credentials"""
        repo_id = "test-repo-20"
        
        # Store credentials first
        await credential_manager.store_credentials(repo_id, {'password': 'test-password'})
        
        # Reset mock
        mock_security_service.log_security_event.reset_mock()
        
        # Remove credentials
        await credential_manager.remove_credentials(repo_id)
        
        # Verify security event was logged
        mock_security_service.log_security_event.assert_called()
        
        # Check event details
        call_args = mock_security_service.log_security_event.call_args[0][0]
        assert call_args.event_type == "credential_removal"
        assert call_args.repository_id == repo_id
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_credentials_when_locked_raises_error(self, temp_dir, mock_security_service):
        """Test that storing credentials when locked raises error"""
        # Create locked credential manager
        locked_cm = CredentialManager(config_dir=temp_dir)
        # Don't unlock it
        
        # Mock ensure_unlocked to always return False
        locked_cm.ensure_unlocked = Mock(return_value=False)
        
        mock_security_service.credential_manager = locked_cm
        credential_manager = RepositoryCredentialManager(mock_security_service)
        
        # Try to store credentials - should raise error because manager is locked
        with pytest.raises(CredentialError, match="Cannot store credentials: credential manager is locked"):
            await credential_manager.store_credentials("test-repo", {'password': 'test'})
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retrieve_credentials_when_locked_raises_error(self, temp_dir, mock_security_service):
        """Test that retrieving credentials when locked raises error"""
        # Create locked credential manager
        locked_cm = CredentialManager(config_dir=temp_dir)
        # Don't unlock it
        
        # Mock ensure_unlocked to always return False
        locked_cm.ensure_unlocked = Mock(return_value=False)
        
        mock_security_service.credential_manager = locked_cm
        credential_manager = RepositoryCredentialManager(mock_security_service)
        
        # Try to retrieve credentials - should raise error because manager is locked
        with pytest.raises(CredentialError, match="Cannot retrieve credentials: credential manager is locked"):
            await credential_manager.retrieve_credentials("test-repo")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rotate_credentials_when_locked_raises_error(self, temp_dir, mock_security_service):
        """Test that rotating credentials when locked raises error"""
        # Create locked credential manager
        locked_cm = CredentialManager(config_dir=temp_dir)
        # Don't unlock it
        
        mock_security_service.credential_manager = locked_cm
        credential_manager = RepositoryCredentialManager(mock_security_service)
        
        # Try to rotate credentials
        with pytest.raises(CredentialError):
            await credential_manager.rotate_password("test-repo", 'new-password')


class TestRepositoryCredentialManagerMultipleBackends:
    """Test Repository Credential Manager with multiple backend types"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def credential_manager(self, temp_dir):
        """Create repository credential manager"""
        credential_mgr = CredentialManager(config_dir=temp_dir)
        credential_mgr.unlock("test_master_password")
        
        security_service = Mock(spec=SecurityService)
        security_service.credential_manager = credential_mgr
        security_service.log_security_event = Mock()
        
        return RepositoryCredentialManager(security_service)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_s3_credentials(self, credential_manager):
        """Test storing S3 backend credentials"""
        repo_id = "s3-repo"
        credentials = {
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'region': 'us-west-2'
            }
        }
        
        result = await credential_manager.store_credentials(repo_id, credentials)
        assert result is True
        
        # Retrieve and verify
        retrieved = await credential_manager.retrieve_credentials(repo_id)
        assert retrieved['backend_type'] == 's3'
        assert retrieved['backend_credentials']['access_key_id'] == 'AKIAIOSFODNN7EXAMPLE'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_b2_credentials(self, credential_manager):
        """Test storing B2 backend credentials"""
        repo_id = "b2-repo"
        credentials = {
            'backend_type': 'b2',
            'backend_credentials': {
                'account_id': 'test-account-id',
                'application_key': 'test-application-key'
            }
        }
        
        result = await credential_manager.store_credentials(repo_id, credentials)
        assert result is True
        
        # Retrieve and verify
        retrieved = await credential_manager.retrieve_credentials(repo_id)
        assert retrieved['backend_type'] == 'b2'
        assert retrieved['backend_credentials']['account_id'] == 'test-account-id'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_sftp_credentials(self, credential_manager):
        """Test storing SFTP backend credentials"""
        repo_id = "sftp-repo"
        credentials = {
            'backend_type': 'sftp',
            'backend_credentials': {
                'username': 'test-user',
                'password': 'test-password',
                'host': 'sftp.example.com',
                'port': 22
            }
        }
        
        result = await credential_manager.store_credentials(repo_id, credentials)
        assert result is True
        
        # Retrieve and verify
        retrieved = await credential_manager.retrieve_credentials(repo_id)
        assert retrieved['backend_type'] == 'sftp'
        assert retrieved['backend_credentials']['username'] == 'test-user'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retrieve_correct_backend_type(self, credential_manager):
        """Test that retrieval returns correct backend type"""
        # Store credentials for multiple backend types
        await credential_manager.store_credentials("s3-repo", {
            'backend_type': 's3',
            'backend_credentials': {'access_key_id': 's3-key'}
        })
        
        await credential_manager.store_credentials("b2-repo", {
            'backend_type': 'b2',
            'backend_credentials': {'account_id': 'b2-account'}
        })
        
        # Retrieve S3 credentials
        s3_creds = await credential_manager.retrieve_credentials("s3-repo")
        assert s3_creds['backend_type'] == 's3'
        assert 'access_key_id' in s3_creds['backend_credentials']
        
        # Retrieve B2 credentials
        b2_creds = await credential_manager.retrieve_credentials("b2-repo")
        assert b2_creds['backend_type'] == 'b2'
        assert 'account_id' in b2_creds['backend_credentials']
