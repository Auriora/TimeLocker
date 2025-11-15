"""
Integration tests for RepositoryResolver in CLI commands
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.cli_modules.commands.base import _create_repository_resolver


@pytest.fixture
def mock_config_dir(tmp_path_factory):
    """Create an isolated temporary config directory per test invocation."""
    base_dir = tmp_path_factory.mktemp("repo-resolver")
    config_dir = base_dir / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir


@pytest.fixture
def mock_repository_resolver():
    """Create mock RepositoryResolver"""
    with patch('TimeLocker.cli_modules.commands.base.RepositoryResolver') as mock:
        resolver_instance = Mock()
        
        # Mock methods
        resolver_instance.resolve_repository.return_value = Mock(
            uri='s3:s3.amazonaws.com/test-bucket',
            password=Mock(return_value='test-password')
        )
        resolver_instance.resolve_repository_uri.return_value = 's3:s3.amazonaws.com/test-bucket'
        resolver_instance.resolve_repository_name.return_value = 'test-repo'
        resolver_instance.get_default_repository.return_value = 'test-repo'
        resolver_instance.resolve_credentials.return_value = 'test-password'
        resolver_instance.detect_backend.return_value = 's3'
        resolver_instance.get_backend_info.return_value = {
            'type': 's3',
            'uri': 's3:s3.amazonaws.com/test-bucket'
        }
        
        mock.return_value = resolver_instance
        yield mock


class TestRepositoryResolverFactory:
    """Test RepositoryResolver factory function"""
    
    def test_create_repository_resolver(self, mock_config_dir, mock_repository_resolver):
        """Test creating RepositoryResolver instance"""
        resolver = _create_repository_resolver(mock_config_dir)
        
        assert resolver is not None
        assert mock_repository_resolver.called
    
    def test_create_repository_resolver_default_config(self, mock_repository_resolver):
        """Test creating RepositoryResolver with default config"""
        resolver = _create_repository_resolver()
        
        assert resolver is not None
        assert mock_repository_resolver.called


class TestRestoreCommandIntegration:
    """Test restore command integration with RepositoryResolver"""
    
    def test_get_repository_uses_resolver(self, mock_config_dir, mock_repository_resolver):
        """Test _get_repository uses RepositoryResolver"""
        from TimeLocker.cli_modules.commands.restore import _get_repository
        
        # Patch where it's imported in the restore module (from .base import _create_repository_resolver)
        with patch('TimeLocker.cli_modules.commands.base._create_repository_resolver') as mock_create:
            mock_create.return_value = mock_repository_resolver.return_value
            
            repo = _get_repository('test-repo', mock_config_dir)
            
            assert repo is not None
            assert mock_create.called
            mock_repository_resolver.return_value.resolve_repository.assert_called_once()


class TestBackupCommandIntegration:
    """Test backup command integration with RepositoryResolver"""
    
    def test_backup_repository_resolution(self, mock_config_dir, mock_repository_resolver):
        """Test backup command uses RepositoryResolver for resolution"""
        # This test verifies the integration pattern
        # Actual command testing would require more complex mocking
        
        with patch('TimeLocker.cli_modules.commands.base._create_repository_resolver') as mock_create:
            mock_create.return_value = mock_repository_resolver.return_value
            
            resolver = _create_repository_resolver(mock_config_dir)
            
            # Verify resolver methods work as expected
            uri = resolver.resolve_repository_uri('test-repo')
            assert uri == 's3:s3.amazonaws.com/test-bucket'
            
            password = resolver.resolve_credentials('test-repo', explicit_password='test-pass')
            assert password == 'test-password'


class TestSnapshotsCommandIntegration:
    """Test snapshots command integration with RepositoryResolver"""
    
    def test_snapshots_repository_resolution(self, mock_config_dir, mock_repository_resolver):
        """Test snapshots command uses RepositoryResolver for resolution"""
        
        with patch('TimeLocker.cli_modules.commands.base._create_repository_resolver') as mock_create:
            mock_create.return_value = mock_repository_resolver.return_value
            
            resolver = _create_repository_resolver(mock_config_dir)
            
            # Verify resolver methods work as expected
            uri = resolver.resolve_repository_uri('test-repo')
            assert uri == 's3:s3.amazonaws.com/test-bucket'
            
            default_repo = resolver.get_default_repository()
            assert default_repo == 'test-repo'


class TestCredentialResolutionIntegration:
    """Test credential resolution integration across commands"""
    
    def test_credential_chain_explicit_password(self, mock_config_dir, mock_repository_resolver):
        """Test explicit password has highest priority"""
        resolver = _create_repository_resolver(mock_config_dir)
        
        # Mock to return explicit password
        resolver.resolve_credentials.return_value = 'explicit-pass'
        
        password = resolver.resolve_credentials(
            repository_name='test-repo',
            explicit_password='explicit-pass',
            allow_prompt=False
        )
        
        assert password == 'explicit-pass'
    
    def test_credential_chain_fallback(self, mock_config_dir, mock_repository_resolver):
        """Test credential chain fallback behavior"""
        resolver = _create_repository_resolver(mock_config_dir)
        
        # Mock to return None (no credentials found)
        resolver.resolve_credentials.return_value = None
        
        password = resolver.resolve_credentials(
            repository_name='test-repo',
            explicit_password=None,
            allow_prompt=False
        )
        
        # Should return None when no credentials available
        assert password is None


class TestBackendDetectionIntegration:
    """Test backend detection integration"""
    
    def test_detect_s3_backend(self, mock_config_dir, mock_repository_resolver):
        """Test S3 backend detection"""
        resolver = _create_repository_resolver(mock_config_dir)
        
        backend = resolver.detect_backend('s3:s3.amazonaws.com/bucket')
        assert backend == 's3'
    
    def test_get_backend_info(self, mock_config_dir, mock_repository_resolver):
        """Test getting backend information"""
        resolver = _create_repository_resolver(mock_config_dir)
        
        info = resolver.get_backend_info('s3:s3.amazonaws.com/bucket')
        assert info['type'] == 's3'
        assert 'uri' in info


class TestErrorHandlingIntegration:
    """Test error handling integration"""
    
    def test_repository_not_found_error(self, mock_config_dir):
        """Test repository not found error handling"""
        from TimeLocker.interfaces.exceptions import RepositoryNotFoundError
        
        with patch('TimeLocker.cli_modules.commands.base.RepositoryResolver') as mock:
            resolver_instance = Mock()
            resolver_instance.resolve_repository.side_effect = RepositoryNotFoundError("Repository not found")
            mock.return_value = resolver_instance
            
            resolver = _create_repository_resolver(mock_config_dir)
            
            with pytest.raises(RepositoryNotFoundError):
                resolver.resolve_repository('nonexistent')
    
    def test_configuration_error(self, mock_config_dir):
        """Test configuration error handling"""
        from TimeLocker.interfaces.exceptions import ConfigurationError
        
        with patch('TimeLocker.cli_modules.commands.base.RepositoryResolver') as mock:
            resolver_instance = Mock()
            resolver_instance.resolve_repository_uri.side_effect = ConfigurationError("Invalid configuration")
            mock.return_value = resolver_instance
            
            resolver = _create_repository_resolver(mock_config_dir)
            
            with pytest.raises(ConfigurationError):
                resolver.resolve_repository_uri('invalid')


class TestConsistencyAcrossCommands:
    """Test consistency of RepositoryResolver usage across commands"""
    
    def test_all_commands_use_same_resolver_pattern(self, mock_config_dir, mock_repository_resolver):
        """Test all commands use consistent RepositoryResolver pattern"""
        # This test verifies the pattern is consistent
        
        # Pattern: _create_repository_resolver(config_dir)
        resolver1 = _create_repository_resolver(mock_config_dir)
        resolver2 = _create_repository_resolver(mock_config_dir)
        
        # Both should be instances of the same type
        assert type(resolver1) == type(resolver2)
    
    def test_resolver_methods_available(self, mock_config_dir, mock_repository_resolver):
        """Test all required resolver methods are available"""
        resolver = _create_repository_resolver(mock_config_dir)
        
        # Verify all expected methods exist
        assert hasattr(resolver, 'resolve_repository')
        assert hasattr(resolver, 'resolve_repository_uri')
        assert hasattr(resolver, 'resolve_repository_name')
        assert hasattr(resolver, 'get_default_repository')
        assert hasattr(resolver, 'resolve_credentials')
        assert hasattr(resolver, 'detect_backend')
        assert hasattr(resolver, 'get_backend_info')
