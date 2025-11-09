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
Unit Tests for Restic Engine Plugin

This module tests the Restic backup engine plugin implementation.

Requirements: 4.1, 4.2, 4.3
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import json

from TimeLocker.services.plugins.restic_plugin import ResticEnginePlugin
from TimeLocker.interfaces.backup_engine_plugin import (
    BackupEngine,
    EngineCapabilities,
    ValidationResult,
    EngineNotAvailableError,
    EngineConfigurationError
)


@pytest.fixture
def restic_plugin():
    """Create Restic plugin instance"""
    return ResticEnginePlugin()


class TestResticPluginProperties:
    """Test Restic plugin basic properties"""
    
    def test_engine_name(self, restic_plugin):
        """Test engine name property"""
        assert restic_plugin.engine_name == "restic"
    
    def test_engine_type(self, restic_plugin):
        """Test engine type property"""
        assert restic_plugin.engine_type == BackupEngine.RESTIC
    
    @patch('subprocess.run')
    def test_engine_version_json(self, mock_run, restic_plugin):
        """Test engine version detection with JSON output"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({'version': '0.18.0'})
        mock_run.return_value = mock_result
        
        version = restic_plugin.engine_version
        assert version == '0.18.0'
    
    @patch('subprocess.run')
    def test_engine_version_text_fallback(self, mock_run, restic_plugin):
        """Test engine version detection with text parsing fallback"""
        # First call (JSON) fails
        mock_json_result = Mock()
        mock_json_result.returncode = 1
        
        # Second call (text) succeeds
        mock_text_result = Mock()
        mock_text_result.returncode = 0
        mock_text_result.stdout = "restic 0.18.0 compiled with go1.23.4"
        
        mock_run.side_effect = [mock_json_result, mock_text_result]
        
        version = restic_plugin.engine_version
        assert version == '0.18.0'
    
    @patch('subprocess.run')
    def test_engine_version_not_found(self, mock_run, restic_plugin):
        """Test engine version when restic not found"""
        mock_run.side_effect = FileNotFoundError()
        
        version = restic_plugin.engine_version
        assert version == "unknown"


class TestResticAvailability:
    """Test Restic availability checking"""
    
    @patch('subprocess.run')
    def test_is_available_true(self, mock_run, restic_plugin):
        """Test availability check when restic is available"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({'version': '0.18.0'})
        mock_run.return_value = mock_result
        
        assert restic_plugin.is_available() is True
    
    @patch('subprocess.run')
    def test_is_available_false_not_found(self, mock_run, restic_plugin):
        """Test availability check when restic not found"""
        mock_run.side_effect = FileNotFoundError()
        
        assert restic_plugin.is_available() is False
    
    @patch('subprocess.run')
    def test_is_available_cached(self, mock_run, restic_plugin):
        """Test that availability check is cached"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({'version': '0.18.0'})
        mock_run.return_value = mock_result
        
        # First call
        result1 = restic_plugin.is_available()
        # Second call should use cached value
        result2 = restic_plugin.is_available()
        
        assert result1 is True
        assert result2 is True
        # Should only call subprocess once
        assert mock_run.call_count == 1


class TestResticCapabilities:
    """Test Restic capabilities"""
    
    def test_get_capabilities(self, restic_plugin):
        """Test getting Restic capabilities"""
        capabilities = restic_plugin.get_capabilities()
        
        assert isinstance(capabilities, EngineCapabilities)
        assert capabilities.supports_encryption is True
        assert capabilities.supports_deduplication is True
        assert capabilities.supports_compression is True
        assert capabilities.supports_snapshots is True
        assert capabilities.supports_incremental is True
        assert capabilities.supports_verification is True
        assert capabilities.supports_retention_policies is True
        assert capabilities.supports_tags is True
        
        # Check storage backends
        assert 'local' in capabilities.storage_backends
        assert 's3' in capabilities.storage_backends
        assert 'b2' in capabilities.storage_backends
        assert 'sftp' in capabilities.storage_backends


class TestResticConfigurationValidation:
    """Test Restic configuration validation"""
    
    def test_validate_valid_configuration(self, restic_plugin):
        """Test validation of valid configuration"""
        config = {
            'compression': 'auto',
            'pack_size': 16 * 1024 * 1024,
            'exclude_caches': True
        }
        
        result = restic_plugin.validate_configuration(config)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_invalid_compression(self, restic_plugin):
        """Test validation with invalid compression value"""
        config = {'compression': 'invalid'}
        
        result = restic_plugin.validate_configuration(config)
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert 'compression' in result.errors[0].lower()
    
    def test_validate_invalid_pack_size(self, restic_plugin):
        """Test validation with invalid pack size"""
        config = {'pack_size': -100}
        
        result = restic_plugin.validate_configuration(config)
        assert result.is_valid is False
        assert 'pack_size' in result.errors[0].lower()
    
    def test_validate_small_pack_size_warning(self, restic_plugin):
        """Test validation with small pack size generates warning"""
        config = {'pack_size': 1024 * 1024}  # 1MB
        
        result = restic_plugin.validate_configuration(config)
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert 'pack_size' in result.warnings[0].lower()
    
    def test_validate_relative_cache_dir_warning(self, restic_plugin):
        """Test validation with relative cache dir generates warning"""
        config = {'cache_dir': 'relative/path'}
        
        result = restic_plugin.validate_configuration(config)
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert 'cache_dir' in result.warnings[0].lower()


class TestResticStorageSupport:
    """Test Restic storage backend support"""
    
    def test_supports_storage_type_local(self, restic_plugin):
        """Test support for local storage"""
        assert restic_plugin.supports_storage_type('local') is True
    
    def test_supports_storage_type_s3(self, restic_plugin):
        """Test support for S3 storage"""
        assert restic_plugin.supports_storage_type('s3') is True
    
    def test_supports_storage_type_unsupported(self, restic_plugin):
        """Test unsupported storage type"""
        assert restic_plugin.supports_storage_type('unsupported') is False
    
    def test_get_supported_storage_backends(self, restic_plugin):
        """Test getting list of supported backends"""
        backends = restic_plugin.get_supported_storage_backends()
        
        assert 'local' in backends
        assert 's3' in backends
        assert 'b2' in backends
        assert 'sftp' in backends
        assert 'rest' in backends


class TestResticURIValidation:
    """Test Restic URI validation"""
    
    def test_validate_local_uri(self, restic_plugin):
        """Test validation of local URI"""
        result = restic_plugin.validate_uri('/path/to/repo')
        assert result.is_valid is True
    
    def test_validate_s3_uri(self, restic_plugin):
        """Test validation of S3 URI"""
        result = restic_plugin.validate_uri('s3://s3.amazonaws.com/bucket/path')
        assert result.is_valid is True
    
    def test_validate_b2_uri(self, restic_plugin):
        """Test validation of B2 URI"""
        result = restic_plugin.validate_uri('b2://bucket-name/path')
        assert result.is_valid is True
    
    def test_validate_sftp_uri(self, restic_plugin):
        """Test validation of SFTP URI"""
        result = restic_plugin.validate_uri('sftp://user@host/path')
        assert result.is_valid is True
    
    def test_validate_empty_uri(self, restic_plugin):
        """Test validation of empty URI"""
        result = restic_plugin.validate_uri('')
        assert result.is_valid is False
        assert 'empty' in result.errors[0].lower()
    
    def test_validate_unsupported_scheme(self, restic_plugin):
        """Test validation of unsupported URI scheme"""
        result = restic_plugin.validate_uri('ftp://host/path')
        assert result.is_valid is False
        assert 'unsupported' in result.errors[0].lower()
    
    def test_validate_s3_without_bucket(self, restic_plugin):
        """Test validation of S3 URI without bucket"""
        result = restic_plugin.validate_uri('s3:')
        assert result.is_valid is False
        assert 'bucket' in result.errors[0].lower()
    
    def test_validate_sftp_without_host(self, restic_plugin):
        """Test validation of SFTP URI without host"""
        result = restic_plugin.validate_uri('sftp://')
        assert result.is_valid is False
        assert 'hostname' in result.errors[0].lower()


class TestResticRepositoryCreation:
    """Test Restic repository creation"""
    
    @patch('subprocess.run')
    @patch('TimeLocker.restic.Repositories.local.LocalResticRepository')
    def test_create_local_repository(self, mock_repo_class, mock_run, restic_plugin):
        """Test creating local repository"""
        # Mock restic availability
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({'version': '0.18.0'})
        mock_run.return_value = mock_result
        
        mock_repo = Mock()
        mock_repo_class.from_parsed_uri.return_value = mock_repo
        
        repo = restic_plugin.create_repository('/path/to/repo', password='test123')
        
        assert repo is not None
        mock_repo_class.from_parsed_uri.assert_called_once()
    
    @patch('subprocess.run')
    def test_create_repository_engine_unavailable(self, mock_run, restic_plugin):
        """Test creating repository when engine unavailable"""
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(EngineNotAvailableError) as exc_info:
            restic_plugin.create_repository('/path/to/repo')
        assert "not available" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_create_repository_invalid_uri(self, mock_run, restic_plugin):
        """Test creating repository with invalid URI"""
        # Mock restic availability
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({'version': '0.18.0'})
        mock_run.return_value = mock_result
        
        with pytest.raises(EngineConfigurationError) as exc_info:
            restic_plugin.create_repository('')
        assert "Invalid repository URI" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_create_repository_unsupported_scheme(self, mock_run, restic_plugin):
        """Test creating repository with unsupported scheme"""
        # Mock restic availability
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({'version': '0.18.0'})
        mock_run.return_value = mock_result
        
        with pytest.raises(EngineConfigurationError) as exc_info:
            restic_plugin.create_repository('ftp://host/path')
        assert "Unsupported URI scheme" in str(exc_info.value)


class TestResticDefaultConfiguration:
    """Test Restic default configuration"""
    
    def test_get_default_configuration(self, restic_plugin):
        """Test getting default configuration"""
        config = restic_plugin.get_default_configuration()
        
        assert 'compression' in config
        assert config['compression'] == 'auto'
        assert config['exclude_caches'] is True
        assert config['one_file_system'] is False
    
    def test_get_configuration_schema(self, restic_plugin):
        """Test getting configuration schema"""
        schema = restic_plugin.get_configuration_schema()
        
        assert 'type' in schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'compression' in schema['properties']
        assert 'pack_size' in schema['properties']
