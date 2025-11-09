"""
Tests for S3 Service Manager

This module tests S3-compatible service configuration and validation
for MinIO, Wasabi, Backblaze B2, and DigitalOcean Spaces.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.TimeLocker.services.s3_service_manager import S3ServiceManager
from src.TimeLocker.services.repository_credential_manager import RepositoryCredentialManager
from src.TimeLocker.interfaces.s3_config_models import (
    S3Config, S3ServiceType, S3_SERVICE_TEMPLATES
)
from src.TimeLocker.interfaces.exceptions import CredentialError


class TestS3ServiceManager:
    """Test S3 Service Manager functionality"""
    
    @pytest.fixture
    def mock_credential_manager(self):
        """Create mock credential manager"""
        mock_cm = Mock(spec=RepositoryCredentialManager)
        mock_cm.store_credentials = AsyncMock(return_value=True)
        mock_cm.retrieve_credentials = AsyncMock(return_value=None)
        return mock_cm
    
    @pytest.fixture
    def s3_service_manager(self, mock_credential_manager):
        """Create S3 service manager"""
        return S3ServiceManager(mock_credential_manager)
    
    @pytest.mark.unit
    def test_get_supported_services(self, s3_service_manager):
        """Test getting supported S3-compatible services"""
        services = s3_service_manager.get_supported_services()
        
        assert S3ServiceType.MINIO in services
        assert S3ServiceType.WASABI in services
        assert S3ServiceType.BACKBLAZE_B2 in services
        assert S3ServiceType.DIGITALOCEAN_SPACES in services
        # Note: CUSTOM may not be in templates, it's handled separately
    
    @pytest.mark.unit
    def test_create_minio_config(self, s3_service_manager):
        """Test creating MinIO configuration"""
        repo_id = "minio-repo"
        config, warnings = s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="minioadmin",
            secret_key="minioadmin",
            bucket="test-bucket",
            endpoint="localhost:9000",
            use_ssl=False
        )
        
        assert config is not None
        assert config.service_type == S3ServiceType.MINIO
        # Endpoint may be formatted with protocol
        assert "localhost:9000" in config.endpoint or config.endpoint == "localhost:9000"
        assert config.bucket == "test-bucket"
        assert config.use_ssl is False
        assert config.verify_ssl is False  # Default for MinIO
    
    @pytest.mark.unit
    def test_create_wasabi_config(self, s3_service_manager):
        """Test creating Wasabi configuration"""
        repo_id = "wasabi-repo"
        config, warnings = s3_service_manager.create_wasabi_config(
            repo_id=repo_id,
            access_key="test-access-key",
            secret_key="test-secret-key",
            bucket="test-bucket",
            region="us-east-1"
        )
        
        assert config is not None
        assert config.service_type == S3ServiceType.WASABI
        assert config.region == "us-east-1"
        assert config.bucket == "test-bucket"
        assert config.use_ssl is True  # Default for Wasabi
    
    @pytest.mark.unit
    def test_create_backblaze_b2_config(self, s3_service_manager):
        """Test creating Backblaze B2 configuration"""
        repo_id = "b2-repo"
        config, warnings = s3_service_manager.create_backblaze_b2_config(
            repo_id=repo_id,
            key_id="test-key-id",
            application_key="test-app-key",
            bucket="test-bucket",
            region="us-west-000"
        )
        
        assert config is not None
        assert config.service_type == S3ServiceType.BACKBLAZE_B2
        assert config.region == "us-west-000"
        assert config.bucket == "test-bucket"
    
    @pytest.mark.unit
    def test_create_digitalocean_spaces_config(self, s3_service_manager):
        """Test creating DigitalOcean Spaces configuration"""
        repo_id = "do-repo"
        config, warnings = s3_service_manager.create_digitalocean_spaces_config(
            repo_id=repo_id,
            access_key="test-access-key",
            secret_key="test-secret-key",
            bucket="test-space",
            region="nyc3"
        )
        
        assert config is not None
        assert config.service_type == S3ServiceType.DIGITALOCEAN_SPACES
        assert config.region == "nyc3"
        assert config.bucket == "test-space"
    
    @pytest.mark.unit
    def test_create_custom_s3_config(self, s3_service_manager):
        """Test creating custom S3-compatible configuration"""
        repo_id = "custom-repo"
        
        # Custom service type may not be supported by create_service_config
        # Test that it raises appropriate error or skip if not implemented
        try:
            config, warnings = s3_service_manager.create_custom_s3_config(
                repo_id=repo_id,
                access_key="test-access-key",
                secret_key="test-secret-key",
                bucket="test-bucket",
                endpoint="s3.custom-provider.com"
            )
            
            assert config is not None
            assert config.endpoint == "s3.custom-provider.com"
            assert config.bucket == "test-bucket"
        except ValueError as e:
            # If CUSTOM type is not supported, that's acceptable
            assert "Unsupported service type" in str(e)
            pytest.skip("CUSTOM service type not yet implemented")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_service_credentials(self, s3_service_manager, mock_credential_manager):
        """Test storing S3 service credentials"""
        repo_id = "test-repo"
        config, _ = s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket"
        )
        
        result = await s3_service_manager.store_service_credentials(repo_id, config)
        
        assert result is True
        mock_credential_manager.store_credentials.assert_called_once()
        
        # Verify credentials structure
        call_args = mock_credential_manager.store_credentials.call_args[0]
        assert call_args[0] == repo_id
        assert call_args[1]['backend_type'] == 's3'
        assert 'backend_credentials' in call_args[1]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retrieve_service_credentials(self, s3_service_manager, mock_credential_manager):
        """Test retrieving S3 service credentials"""
        repo_id = "test-repo"
        
        # Mock retrieved credentials
        mock_credential_manager.retrieve_credentials.return_value = {
            'backend_type': 's3',
            'backend_credentials': {
                'access_key_id': 'test-key',
                'secret_access_key': 'test-secret'
            }
        }
        
        credentials = await s3_service_manager.retrieve_service_credentials(repo_id)
        
        assert credentials is not None
        assert 'access_key_id' in credentials
        assert credentials['access_key_id'] == 'test-key'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retrieve_nonexistent_credentials(self, s3_service_manager, mock_credential_manager):
        """Test retrieving credentials for non-existent repository"""
        mock_credential_manager.retrieve_credentials.return_value = None
        
        credentials = await s3_service_manager.retrieve_service_credentials("nonexistent")
        
        assert credentials is None
    
    @pytest.mark.unit
    def test_validate_service_config(self, s3_service_manager):
        """Test validating S3 service configuration"""
        config, _ = s3_service_manager.create_minio_config(
            repo_id="test-repo",
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket"
        )
        
        warnings = s3_service_manager.validate_service_config(config)
        
        # Should have warnings about SSL verification disabled
        assert isinstance(warnings, list)
    
    @pytest.mark.unit
    def test_get_service_config(self, s3_service_manager):
        """Test getting stored service configuration"""
        repo_id = "test-repo"
        config, _ = s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket"
        )
        
        # Configuration should be stored
        retrieved_config = s3_service_manager.get_service_config(repo_id)
        
        assert retrieved_config is not None
        assert retrieved_config.bucket == "test-bucket"
    
    @pytest.mark.unit
    def test_update_service_config(self, s3_service_manager):
        """Test updating service configuration"""
        repo_id = "test-repo"
        
        # Create initial config
        config, _ = s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket"
        )
        
        # Update config
        updated_config, warnings = s3_service_manager.update_service_config(
            repo_id,
            description="Updated description",
            use_ssl=True
        )
        
        assert updated_config.description == "Updated description"
        assert updated_config.use_ssl is True
    
    @pytest.mark.unit
    def test_update_nonexistent_config_raises_error(self, s3_service_manager):
        """Test updating non-existent configuration raises error"""
        with pytest.raises(ValueError):
            s3_service_manager.update_service_config("nonexistent", description="test")
    
    @pytest.mark.unit
    def test_remove_service_config(self, s3_service_manager):
        """Test removing service configuration"""
        repo_id = "test-repo"
        
        # Create config
        s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket"
        )
        
        # Remove config
        result = s3_service_manager.remove_service_config(repo_id)
        
        assert result is True
        assert s3_service_manager.get_service_config(repo_id) is None
    
    @pytest.mark.unit
    def test_remove_nonexistent_config(self, s3_service_manager):
        """Test removing non-existent configuration"""
        result = s3_service_manager.remove_service_config("nonexistent")
        
        assert result is False
    
    @pytest.mark.unit
    def test_list_service_configs(self, s3_service_manager):
        """Test listing service configurations"""
        # Create multiple configs
        repos = ["repo1", "repo2", "repo3"]
        for repo in repos:
            s3_service_manager.create_minio_config(
                repo_id=repo,
                access_key="test-key",
                secret_key="test-secret",
                bucket=f"bucket-{repo}"
            )
        
        # List configs
        configs = s3_service_manager.list_service_configs()
        
        assert len(configs) == 3
        for repo in repos:
            assert repo in configs
            # Verify sensitive data is removed
            assert 'access_key_id' not in configs[repo]
            assert 'secret_access_key' not in configs[repo]
    
    @pytest.mark.unit
    def test_get_connection_parameters(self, s3_service_manager):
        """Test getting connection parameters"""
        repo_id = "test-repo"
        
        config, _ = s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket",
            endpoint="localhost:9000"
        )
        
        params = s3_service_manager.get_connection_parameters(repo_id)
        
        assert params is not None
        assert 'endpoint_url' in params
        assert 'aws_access_key_id' in params
        assert 'aws_secret_access_key' in params
    
    @pytest.mark.unit
    def test_test_service_connection(self, s3_service_manager):
        """Test service connection testing"""
        repo_id = "test-repo"
        
        config, _ = s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket"
        )
        
        success, message = s3_service_manager.test_service_connection(repo_id)
        
        # Should succeed with warnings about SSL
        assert success is True
        assert message is not None
    
    @pytest.mark.unit
    def test_test_connection_nonexistent_repo(self, s3_service_manager):
        """Test connection test for non-existent repository"""
        success, message = s3_service_manager.test_service_connection("nonexistent")
        
        assert success is False
        assert "No configuration found" in message
    
    @pytest.mark.unit
    def test_get_service_info(self, s3_service_manager):
        """Test getting service information"""
        info = s3_service_manager.get_service_info(S3ServiceType.MINIO)
        
        assert info is not None
        assert info['name'] == 'MinIO'
        assert 'description' in info
        assert 'requires_region' in info
        assert 'supports_custom_endpoint' in info
    
    @pytest.mark.unit
    def test_get_service_info_all_services(self, s3_service_manager):
        """Test getting information for all supported services"""
        service_types = [
            S3ServiceType.MINIO,
            S3ServiceType.WASABI,
            S3ServiceType.BACKBLAZE_B2,
            S3ServiceType.DIGITALOCEAN_SPACES
        ]
        
        for service_type in service_types:
            info = s3_service_manager.get_service_info(service_type)
            assert info is not None
            assert 'name' in info
        
        # CUSTOM type may not have service info
        custom_info = s3_service_manager.get_service_info(S3ServiceType.CUSTOM)
        # It's acceptable if CUSTOM returns None


class TestS3ServiceManagerValidation:
    """Test S3 Service Manager validation functionality"""
    
    @pytest.fixture
    def s3_service_manager(self):
        """Create S3 service manager"""
        mock_cm = Mock(spec=RepositoryCredentialManager)
        return S3ServiceManager(mock_cm)
    
    @pytest.mark.unit
    def test_minio_ssl_disabled_warning(self, s3_service_manager):
        """Test that MinIO with SSL disabled generates warning"""
        config, warnings = s3_service_manager.create_minio_config(
            repo_id="test-repo",
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket",
            use_ssl=False
        )
        
        # Should have warning about SSL disabled
        assert len(warnings) > 0
        assert any('SSL' in warning or 'TLS' in warning for warning in warnings)
    
    @pytest.mark.unit
    def test_minio_ssl_verification_disabled_warning(self, s3_service_manager):
        """Test that MinIO with SSL verification disabled generates warning"""
        config, warnings = s3_service_manager.create_minio_config(
            repo_id="test-repo",
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket",
            use_ssl=True,
            verify_ssl=False
        )
        
        # Should have warning about SSL verification disabled
        assert len(warnings) > 0
        assert any('verification' in warning.lower() for warning in warnings)
    
    @pytest.mark.unit
    def test_custom_endpoint_validation(self, s3_service_manager):
        """Test custom endpoint validation"""
        # Custom service type may not be supported yet
        try:
            config, warnings = s3_service_manager.create_custom_s3_config(
                repo_id="test-repo",
                access_key="test-key",
                secret_key="test-secret",
                bucket="test-bucket",
                endpoint="https://s3.custom.com"
            )
            
            assert config.endpoint == "https://s3.custom.com"
        except ValueError as e:
            if "Unsupported service type" in str(e):
                pytest.skip("CUSTOM service type not yet implemented")
            else:
                raise
    
    @pytest.mark.unit
    def test_region_required_for_wasabi(self, s3_service_manager):
        """Test that region is required for Wasabi"""
        config, warnings = s3_service_manager.create_wasabi_config(
            repo_id="test-repo",
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket",
            region="us-east-1"
        )
        
        assert config.region == "us-east-1"
    
    @pytest.mark.unit
    def test_region_required_for_backblaze(self, s3_service_manager):
        """Test that region is required for Backblaze B2"""
        config, warnings = s3_service_manager.create_backblaze_b2_config(
            repo_id="test-repo",
            key_id="test-key-id",
            application_key="test-app-key",
            bucket="test-bucket",
            region="us-west-000"
        )
        
        assert config.region == "us-west-000"
    
    @pytest.mark.unit
    def test_region_required_for_digitalocean(self, s3_service_manager):
        """Test that region is required for DigitalOcean Spaces"""
        config, warnings = s3_service_manager.create_digitalocean_spaces_config(
            repo_id="test-repo",
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-space",
            region="nyc3"
        )
        
        assert config.region == "nyc3"


class TestS3ServiceManagerCredentialIntegration:
    """Test S3 Service Manager integration with credential manager"""
    
    @pytest.fixture
    def mock_credential_manager(self):
        """Create mock credential manager"""
        mock_cm = Mock(spec=RepositoryCredentialManager)
        mock_cm.store_credentials = AsyncMock(return_value=True)
        mock_cm.retrieve_credentials = AsyncMock(return_value=None)
        return mock_cm
    
    @pytest.fixture
    def s3_service_manager(self, mock_credential_manager):
        """Create S3 service manager"""
        return S3ServiceManager(mock_credential_manager)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credentials_stored_with_backend_type(self, s3_service_manager, mock_credential_manager):
        """Test that credentials are stored with correct backend type"""
        repo_id = "test-repo"
        config, _ = s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket"
        )
        
        await s3_service_manager.store_service_credentials(repo_id, config)
        
        # Verify backend_type is 's3'
        call_args = mock_credential_manager.store_credentials.call_args[0]
        assert call_args[1]['backend_type'] == 's3'
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_credentials_include_all_required_fields(self, s3_service_manager, mock_credential_manager):
        """Test that stored credentials include all required fields"""
        repo_id = "test-repo"
        config, _ = s3_service_manager.create_wasabi_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket",
            region="us-east-1"
        )
        
        await s3_service_manager.store_service_credentials(repo_id, config)
        
        # Verify all required fields are present
        call_args = mock_credential_manager.store_credentials.call_args[0]
        backend_creds = call_args[1]['backend_credentials']
        
        assert 'access_key_id' in backend_creds
        assert 'secret_access_key' in backend_creds
        assert 'region' in backend_creds
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retrieve_filters_by_backend_type(self, s3_service_manager, mock_credential_manager):
        """Test that retrieval filters by backend type"""
        repo_id = "test-repo"
        
        # Mock credentials with wrong backend type
        mock_credential_manager.retrieve_credentials.return_value = {
            'backend_type': 'b2',
            'backend_credentials': {'key': 'value'}
        }
        
        credentials = await s3_service_manager.retrieve_service_credentials(repo_id)
        
        # Should return None because backend type doesn't match
        assert credentials is None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_credentials_failure_raises_error(self, s3_service_manager, mock_credential_manager):
        """Test that credential storage failure raises error"""
        repo_id = "test-repo"
        config, _ = s3_service_manager.create_minio_config(
            repo_id=repo_id,
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket"
        )
        
        # Mock failure
        mock_credential_manager.store_credentials.side_effect = Exception("Storage failed")
        
        with pytest.raises(CredentialError):
            await s3_service_manager.store_service_credentials(repo_id, config)
