"""
Tests for RepositoryResolver service
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.cli_modules.services.repository_resolver import RepositoryResolver
from TimeLocker.interfaces.exceptions import ConfigurationError, RepositoryNotFoundError
from TimeLocker.security.credential_manager import CredentialManagerError


@pytest.fixture
def mock_config_module():
    """Create mock configuration module"""
    with patch('TimeLocker.cli_modules.services.repository_resolver.ConfigurationModule') as mock:
        config_instance = Mock()
        config_instance.config_dir = Path("/tmp/test_config")
        
        # Mock get_config
        mock_config = Mock()
        mock_config.repositories = {
            'test-repo': Mock(
                name='test-repo',
                location='s3:s3.amazonaws.com/test-bucket',
                description='Test repository'
            ),
            'local-repo': Mock(
                name='local-repo',
                location='/tmp/local-repo',
                description='Local test repository'
            )
        }
        config_instance.get_config.return_value = mock_config
        
        # Mock get_repository
        def get_repository_side_effect(name):
            if name in mock_config.repositories:
                return mock_config.repositories[name]
            raise RepositoryNotFoundError(f"Repository '{name}' not found")
        
        config_instance.get_repository.side_effect = get_repository_side_effect
        
        mock.return_value = config_instance
        yield mock


@pytest.fixture
def mock_credential_manager():
    """Create mock credential manager"""
    with patch('TimeLocker.cli_modules.services.repository_resolver.CredentialManager') as mock:
        cred_instance = Mock()
        cred_instance.is_locked.return_value = False
        cred_instance.get_repository_password.return_value = "test-password"
        cred_instance.ensure_unlocked.return_value = True
        mock.return_value = cred_instance
        yield mock


@pytest.fixture
def mock_backup_manager():
    """Create mock backup manager"""
    with patch('TimeLocker.cli_modules.services.repository_resolver.BackupManager') as mock:
        manager_instance = Mock()
        mock_repo = Mock()
        mock_repo.uri = 's3:s3.amazonaws.com/test-bucket'
        mock_repo.password.return_value = 'test-password'
        manager_instance.from_uri.return_value = mock_repo
        mock.return_value = manager_instance
        yield mock


@pytest.fixture
def repository_resolver(mock_config_module, mock_credential_manager, mock_backup_manager):
    """Create RepositoryResolver instance with mocked dependencies"""
    with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve_uri, \
         patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_get_info, \
         patch('TimeLocker.cli_modules.services.repository_resolver.get_default_repository') as mock_get_default:
        
        # Setup default mocks
        mock_resolve_uri.return_value = 's3:s3.amazonaws.com/test-bucket'
        mock_get_info.return_value = {
            'uri': 's3:s3.amazonaws.com/test-bucket',
            'name': 'test-repo',
            'description': 'Test repository',
            'type': 's3',
            'is_named': True
        }
        mock_get_default.return_value = 'test-repo'
        
        resolver = RepositoryResolver(config_dir=Path("/tmp/test_config"))
        yield resolver


class TestRepositoryResolverInitialization:
    """Test RepositoryResolver initialization"""
    
    def test_initialization(self, repository_resolver):
        """Test basic initialization"""
        assert repository_resolver is not None
        assert repository_resolver._config_module is not None
        assert repository_resolver._repository_cache == {}
        assert repository_resolver._cache_ttl == 300
    
    def test_credential_manager_initialization(self, repository_resolver):
        """Test credential manager is initialized"""
        assert repository_resolver._credential_manager is not None


class TestRepositoryResolution:
    """Test repository resolution methods"""
    
    def test_resolve_repository_by_name(self, repository_resolver):
        """Test resolving repository by name"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve, \
             patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_info:
            
            mock_resolve.return_value = 's3:s3.amazonaws.com/test-bucket'
            mock_info.return_value = {
                'uri': 's3:s3.amazonaws.com/test-bucket',
                'name': 'test-repo',
                'is_named': True
            }
            
            repo = repository_resolver.resolve_repository('test-repo', password='test-pass')
            
            assert repo is not None
            assert mock_resolve.called
            assert mock_info.called
    
    def test_resolve_repository_by_uri(self, repository_resolver):
        """Test resolving repository by URI"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve, \
             patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_info:
            
            uri = 's3:s3.amazonaws.com/test-bucket'
            mock_resolve.return_value = uri
            mock_info.return_value = {
                'uri': uri,
                'is_named': False
            }
            
            repo = repository_resolver.resolve_repository(uri, password='test-pass')
            
            assert repo is not None
    
    def test_resolve_repository_default(self, repository_resolver):
        """Test resolving default repository"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve, \
             patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_info, \
             patch('TimeLocker.cli_modules.services.repository_resolver.get_default_repository') as mock_default:
            
            mock_default.return_value = 'test-repo'
            mock_resolve.return_value = 's3:s3.amazonaws.com/test-bucket'
            mock_info.return_value = {
                'uri': 's3:s3.amazonaws.com/test-bucket',
                'name': 'test-repo',
                'is_named': True
            }
            
            repo = repository_resolver.resolve_repository(None, password='test-pass')
            
            assert repo is not None
    
    def test_resolve_repository_not_found(self, repository_resolver):
        """Test resolving non-existent repository"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve:
            mock_resolve.side_effect = RepositoryNotFoundError("Repository not found")
            
            with pytest.raises(RepositoryNotFoundError):
                repository_resolver.resolve_repository('nonexistent')
    
    def test_resolve_repository_uri_only(self, repository_resolver):
        """Test resolving repository URI without creating instance"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve:
            mock_resolve.return_value = 's3:s3.amazonaws.com/test-bucket'
            
            uri = repository_resolver.resolve_repository_uri('test-repo')
            
            assert uri == 's3:s3.amazonaws.com/test-bucket'
            assert mock_resolve.called
    
    def test_resolve_repository_name(self, repository_resolver):
        """Test resolving repository name from name or URI"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_info:
            mock_info.return_value = {
                'name': 'test-repo',
                'uri': 's3:s3.amazonaws.com/test-bucket'
            }
            
            name = repository_resolver.resolve_repository_name('test-repo')
            
            assert name == 'test-repo'


class TestCredentialResolution:
    """Test credential resolution chain"""
    
    def test_explicit_password_priority(self, repository_resolver):
        """Test explicit password has highest priority"""
        password = repository_resolver._resolve_credentials(
            repository_name='test-repo',
            repository_uri='s3:s3.amazonaws.com/test-bucket',
            explicit_password='explicit-pass',
            allow_prompt=False
        )
        
        assert password == 'explicit-pass'
    
    def test_credential_manager_password(self, repository_resolver):
        """Test credential manager password resolution"""
        repository_resolver._credential_manager.get_repository_password.return_value = 'stored-pass'
        
        password = repository_resolver._resolve_credentials(
            repository_name='test-repo',
            repository_uri='s3:s3.amazonaws.com/test-bucket',
            explicit_password=None,
            allow_prompt=False
        )
        
        assert password == 'stored-pass'
    
    def test_environment_variable_password(self, repository_resolver):
        """Test environment variable password resolution"""
        repository_resolver._credential_manager.get_repository_password.return_value = None
        
        with patch.dict(os.environ, {'RESTIC_PASSWORD': 'env-pass'}):
            password = repository_resolver._resolve_credentials(
                repository_name='test-repo',
                repository_uri='s3:s3.amazonaws.com/test-bucket',
                explicit_password=None,
                allow_prompt=False
            )
            
            assert password == 'env-pass'
    
    def test_prompt_password(self, repository_resolver):
        """Test interactive password prompt"""
        repository_resolver._credential_manager.get_repository_password.return_value = None
        
        with patch.dict(os.environ, {}, clear=True), \
             patch('rich.prompt.Prompt') as mock_prompt:
            
            mock_prompt.ask.return_value = 'prompted-pass'
            
            password = repository_resolver._resolve_credentials(
                repository_name='test-repo',
                repository_uri='s3:s3.amazonaws.com/test-bucket',
                explicit_password=None,
                allow_prompt=True
            )
            
            assert password == 'prompted-pass'
    
    def test_no_password_found(self, repository_resolver):
        """Test when no password can be resolved"""
        repository_resolver._credential_manager.get_repository_password.return_value = None
        
        with patch.dict(os.environ, {}, clear=True):
            password = repository_resolver._resolve_credentials(
                repository_name='test-repo',
                repository_uri='s3:s3.amazonaws.com/test-bucket',
                explicit_password=None,
                allow_prompt=False
            )
            
            assert password is None
    
    def test_credential_manager_locked(self, repository_resolver):
        """Test credential resolution when credential manager is locked"""
        repository_resolver._credential_manager.is_locked.return_value = True
        
        with patch.dict(os.environ, {'RESTIC_PASSWORD': 'env-pass'}):
            password = repository_resolver._resolve_credentials(
                repository_name='test-repo',
                repository_uri='s3:s3.amazonaws.com/test-bucket',
                explicit_password=None,
                allow_prompt=False
            )
            
            # Should fall back to environment variable
            assert password == 'env-pass'


class TestBackendDetection:
    """Test backend detection methods"""
    
    def test_detect_s3_backend(self, repository_resolver):
        """Test S3 backend detection"""
        assert repository_resolver.detect_backend('s3:s3.amazonaws.com/bucket') == 's3'
        assert repository_resolver.detect_backend('s3://s3.amazonaws.com/bucket') == 's3'
    
    def test_detect_b2_backend(self, repository_resolver):
        """Test B2 backend detection"""
        assert repository_resolver.detect_backend('b2:bucket/path') == 'b2'
        assert repository_resolver.detect_backend('b2://bucket/path') == 'b2'
    
    def test_detect_local_backend(self, repository_resolver):
        """Test local backend detection"""
        assert repository_resolver.detect_backend('/tmp/repo') == 'local'
        assert repository_resolver.detect_backend('file:///tmp/repo') == 'local'
    
    def test_detect_sftp_backend(self, repository_resolver):
        """Test SFTP backend detection"""
        assert repository_resolver.detect_backend('sftp://user@host/path') == 'sftp'
    
    def test_get_backend_info_s3(self, repository_resolver):
        """Test getting S3 backend info"""
        info = repository_resolver.get_backend_info('s3:s3.amazonaws.com/bucket/path')
        
        assert info['type'] == 's3'
        assert info['host'] == 's3.amazonaws.com'
        assert info['path'] == 'bucket/path'
    
    def test_get_backend_info_local(self, repository_resolver):
        """Test getting local backend info"""
        info = repository_resolver.get_backend_info('/tmp/repo')
        
        assert info['type'] == 'local'
        assert info['path'] == '/tmp/repo'


class TestCaching:
    """Test repository caching"""
    
    def test_cache_hit(self, repository_resolver):
        """Test cache hit on second resolution"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve, \
             patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_info:
            
            mock_resolve.return_value = 's3:s3.amazonaws.com/test-bucket'
            mock_info.return_value = {
                'uri': 's3:s3.amazonaws.com/test-bucket',
                'name': 'test-repo',
                'is_named': True
            }
            
            # First resolution - cache miss
            repo1 = repository_resolver.resolve_repository('test-repo', password='test-pass')
            assert repository_resolver._cache_misses == 1
            
            # Second resolution - cache hit
            repo2 = repository_resolver.resolve_repository('test-repo', password='test-pass')
            assert repository_resolver._cache_hits == 1
            assert repo1 is repo2
    
    def test_cache_expiration(self, repository_resolver):
        """Test cache expiration after TTL"""
        import time
        
        repository_resolver.set_cache_ttl(1)  # 1 second TTL
        
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve, \
             patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_info:
            
            mock_resolve.return_value = 's3:s3.amazonaws.com/test-bucket'
            mock_info.return_value = {
                'uri': 's3:s3.amazonaws.com/test-bucket',
                'name': 'test-repo',
                'is_named': True
            }
            
            # First resolution
            repo1 = repository_resolver.resolve_repository('test-repo', password='test-pass')
            
            # Wait for cache to expire
            time.sleep(1.1)
            
            # Second resolution - cache should be expired
            repo2 = repository_resolver.resolve_repository('test-repo', password='test-pass')
            assert repository_resolver._cache_misses == 2
    
    def test_clear_cache(self, repository_resolver):
        """Test clearing cache"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve, \
             patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_info:
            
            mock_resolve.return_value = 's3:s3.amazonaws.com/test-bucket'
            mock_info.return_value = {
                'uri': 's3:s3.amazonaws.com/test-bucket',
                'name': 'test-repo',
                'is_named': True
            }
            
            # Add to cache
            repository_resolver.resolve_repository('test-repo', password='test-pass')
            assert len(repository_resolver._repository_cache) > 0
            
            # Clear cache
            repository_resolver.clear_cache()
            assert len(repository_resolver._repository_cache) == 0


class TestRepositoryConfiguration:
    """Test repository configuration methods"""
    
    def test_get_repository_config(self, repository_resolver):
        """Test getting repository configuration"""
        config = repository_resolver.get_repository_config('test-repo')
        
        assert config is not None
        # Mock object, so just verify it was returned
        assert config is not None
    
    def test_get_repository_config_not_found(self, repository_resolver):
        """Test getting non-existent repository configuration"""
        with pytest.raises(RepositoryNotFoundError):
            repository_resolver.get_repository_config('nonexistent')
    
    def test_list_repositories(self, repository_resolver):
        """Test listing all repositories"""
        repos = repository_resolver.list_repositories()
        
        assert 'test-repo' in repos
        assert 'local-repo' in repos


class TestPerformanceStats:
    """Test performance statistics"""
    
    def test_performance_stats(self, repository_resolver):
        """Test getting performance statistics"""
        stats = repository_resolver.get_performance_stats()
        
        assert 'total_operations' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'cache_hit_rate' in stats
        assert 'cache_size' in stats
    
    def test_cache_hit_rate_calculation(self, repository_resolver):
        """Test cache hit rate calculation"""
        with patch('TimeLocker.cli_modules.services.repository_resolver.resolve_repository_uri') as mock_resolve, \
             patch('TimeLocker.cli_modules.services.repository_resolver.get_repository_info') as mock_info:
            
            mock_resolve.return_value = 's3:s3.amazonaws.com/test-bucket'
            mock_info.return_value = {
                'uri': 's3:s3.amazonaws.com/test-bucket',
                'name': 'test-repo',
                'is_named': True
            }
            
            # First resolution - miss
            repository_resolver.resolve_repository('test-repo', password='test-pass')
            
            # Second resolution - hit
            repository_resolver.resolve_repository('test-repo', password='test-pass')
            
            stats = repository_resolver.get_performance_stats()
            assert stats['cache_hit_rate'] == '50.0%'
