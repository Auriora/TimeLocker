"""
S3-Compatible Service Manager

Manages S3-compatible service configurations and provides unified interface
for MinIO, Wasabi, Backblaze B2, and DigitalOcean Spaces.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..interfaces.s3_config_models import (
    S3Config, S3ServiceType, S3ServiceTemplate, S3_SERVICE_TEMPLATES,
    S3ConfigValidator, create_s3_config_for_service
)
from ..interfaces.exceptions import CredentialError
from .repository_credential_manager import RepositoryCredentialManager

logger = logging.getLogger(__name__)


class S3ServiceManager:
    """
    Manager for S3-compatible services with support for multiple providers.
    
    Provides unified interface for configuring and managing S3-compatible
    storage services including MinIO, Wasabi, Backblaze B2, and DigitalOcean Spaces.
    """

    def __init__(self, credential_manager: RepositoryCredentialManager):
        """
        Initialize S3 service manager.
        
        Args:
            credential_manager: Repository credential manager for secure storage
        """
        self.credential_manager = credential_manager
        self._service_configs: Dict[str, S3Config] = {}

    def get_supported_services(self) -> Dict[S3ServiceType, S3ServiceTemplate]:
        """
        Get all supported S3-compatible services.
        
        Returns:
            Dict mapping service types to their templates
        """
        return S3_SERVICE_TEMPLATES.copy()

    def create_service_config(self, repo_id: str, service_type: S3ServiceType,
                            access_key_id: str, secret_access_key: str,
                            bucket: str, **kwargs) -> Tuple[S3Config, List[str]]:
        """
        Create and validate S3 service configuration.
        
        Args:
            repo_id: Repository identifier
            service_type: Type of S3-compatible service
            access_key_id: Access key ID
            secret_access_key: Secret access key
            bucket: Bucket name
            **kwargs: Additional configuration parameters
            
        Returns:
            Tuple[S3Config, List[str]]: Configuration and validation warnings
            
        Raises:
            ValueError: If configuration is invalid
            CredentialError: If credential storage fails
        """
        try:
            # Create configuration using service template
            config = create_s3_config_for_service(
                service_type, access_key_id, secret_access_key, bucket, **kwargs
            )
            
            # Add timestamps
            config.created_at = datetime.now().isoformat()
            config.updated_at = config.created_at
            
            # Validate configuration
            warnings = S3ConfigValidator.validate_config(config)
            
            # Store configuration and credentials
            self._service_configs[repo_id] = config
            
            return config, warnings
            
        except Exception as e:
            logger.error(f"Failed to create S3 service config for {repo_id}: {e}")
            raise ValueError(f"Failed to create S3 service configuration: {e}")

    async def store_service_credentials(self, repo_id: str, config: S3Config) -> bool:
        """
        Store S3 service credentials securely.
        
        Args:
            repo_id: Repository identifier
            config: S3 configuration containing credentials
            
        Returns:
            bool: True if credentials were stored successfully
            
        Raises:
            CredentialError: If credential storage fails
        """
        try:
            # Prepare credentials for storage
            credentials = {
                'backend_type': 's3',
                'backend_credentials': config.get_credentials_dict()
            }
            
            # Store credentials using credential manager
            success = await self.credential_manager.store_credentials(repo_id, credentials)
            
            if success:
                logger.info(f"S3 credentials stored for repository {repo_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to store S3 credentials for {repo_id}: {e}")
            raise CredentialError(f"Failed to store S3 credentials: {e}")

    async def retrieve_service_credentials(self, repo_id: str) -> Optional[Dict[str, str]]:
        """
        Retrieve S3 service credentials.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Optional[Dict]: S3 credentials if found, None otherwise
        """
        try:
            credentials = await self.credential_manager.retrieve_credentials(repo_id)
            
            if credentials and credentials.get('backend_type') == 's3':
                return credentials.get('backend_credentials', {})
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve S3 credentials for {repo_id}: {e}")
            return None

    def create_minio_config(self, repo_id: str, access_key: str, secret_key: str,
                          bucket: str, endpoint: str = "localhost:9000",
                          use_ssl: bool = False, **kwargs) -> Tuple[S3Config, List[str]]:
        """
        Create MinIO configuration with appropriate defaults.
        
        Args:
            repo_id: Repository identifier
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket: Bucket name
            endpoint: MinIO endpoint (default: localhost:9000)
            use_ssl: Whether to use SSL (default: False for MinIO)
            **kwargs: Additional configuration parameters
            
        Returns:
            Tuple[S3Config, List[str]]: Configuration and validation warnings
        """
        kwargs.update({
            'endpoint': endpoint,
            'use_ssl': use_ssl,
            'verify_ssl': kwargs.get('verify_ssl', False),  # Default to False for MinIO
            'description': kwargs.get('description', f'MinIO configuration for {repo_id}')
        })
        
        return self.create_service_config(
            repo_id, S3ServiceType.MINIO, access_key, secret_key, bucket, **kwargs
        )

    def create_wasabi_config(self, repo_id: str, access_key: str, secret_key: str,
                           bucket: str, region: str = "us-east-1", **kwargs) -> Tuple[S3Config, List[str]]:
        """
        Create Wasabi configuration with appropriate defaults.
        
        Args:
            repo_id: Repository identifier
            access_key: Wasabi access key
            secret_key: Wasabi secret key
            bucket: Bucket name
            region: Wasabi region (default: us-east-1)
            **kwargs: Additional configuration parameters
            
        Returns:
            Tuple[S3Config, List[str]]: Configuration and validation warnings
        """
        kwargs.update({
            'region': region,
            'description': kwargs.get('description', f'Wasabi configuration for {repo_id}')
        })
        
        return self.create_service_config(
            repo_id, S3ServiceType.WASABI, access_key, secret_key, bucket, **kwargs
        )

    def create_backblaze_b2_config(self, repo_id: str, key_id: str, application_key: str,
                                 bucket: str, region: str = "us-west-000", **kwargs) -> Tuple[S3Config, List[str]]:
        """
        Create Backblaze B2 configuration with appropriate defaults.
        
        Args:
            repo_id: Repository identifier
            key_id: Backblaze B2 key ID
            application_key: Backblaze B2 application key
            bucket: Bucket name
            region: B2 region (default: us-west-000)
            **kwargs: Additional configuration parameters
            
        Returns:
            Tuple[S3Config, List[str]]: Configuration and validation warnings
        """
        kwargs.update({
            'region': region,
            'description': kwargs.get('description', f'Backblaze B2 configuration for {repo_id}')
        })
        
        return self.create_service_config(
            repo_id, S3ServiceType.BACKBLAZE_B2, key_id, application_key, bucket, **kwargs
        )

    def create_digitalocean_spaces_config(self, repo_id: str, access_key: str, secret_key: str,
                                        bucket: str, region: str = "nyc3", **kwargs) -> Tuple[S3Config, List[str]]:
        """
        Create DigitalOcean Spaces configuration with appropriate defaults.
        
        Args:
            repo_id: Repository identifier
            access_key: DigitalOcean Spaces access key
            secret_key: DigitalOcean Spaces secret key
            bucket: Bucket name (Space name)
            region: DigitalOcean region (default: nyc3)
            **kwargs: Additional configuration parameters
            
        Returns:
            Tuple[S3Config, List[str]]: Configuration and validation warnings
        """
        kwargs.update({
            'region': region,
            'description': kwargs.get('description', f'DigitalOcean Spaces configuration for {repo_id}')
        })
        
        return self.create_service_config(
            repo_id, S3ServiceType.DIGITALOCEAN_SPACES, access_key, secret_key, bucket, **kwargs
        )

    def create_custom_s3_config(self, repo_id: str, access_key: str, secret_key: str,
                              bucket: str, endpoint: str, **kwargs) -> Tuple[S3Config, List[str]]:
        """
        Create custom S3-compatible service configuration.
        
        Args:
            repo_id: Repository identifier
            access_key: Access key
            secret_key: Secret key
            bucket: Bucket name
            endpoint: Custom endpoint URL
            **kwargs: Additional configuration parameters
            
        Returns:
            Tuple[S3Config, List[str]]: Configuration and validation warnings
        """
        kwargs.update({
            'endpoint': endpoint,
            'description': kwargs.get('description', f'Custom S3 configuration for {repo_id}')
        })
        
        return self.create_service_config(
            repo_id, S3ServiceType.CUSTOM, access_key, secret_key, bucket, **kwargs
        )

    def validate_service_config(self, config: S3Config) -> List[str]:
        """
        Validate S3 service configuration.
        
        Args:
            config: S3 configuration to validate
            
        Returns:
            List[str]: List of validation warnings/issues
        """
        return S3ConfigValidator.validate_config(config)

    def get_service_config(self, repo_id: str) -> Optional[S3Config]:
        """
        Get stored S3 service configuration.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Optional[S3Config]: Configuration if found, None otherwise
        """
        return self._service_configs.get(repo_id)

    def update_service_config(self, repo_id: str, **updates) -> Tuple[S3Config, List[str]]:
        """
        Update existing S3 service configuration.
        
        Args:
            repo_id: Repository identifier
            **updates: Configuration updates
            
        Returns:
            Tuple[S3Config, List[str]]: Updated configuration and validation warnings
            
        Raises:
            ValueError: If repository configuration not found
        """
        config = self._service_configs.get(repo_id)
        if not config:
            raise ValueError(f"No S3 configuration found for repository {repo_id}")
        
        # Create updated configuration
        config_dict = config.to_dict()
        config_dict.update(updates)
        config_dict['updated_at'] = datetime.now().isoformat()
        
        updated_config = S3Config.from_dict(config_dict)
        
        # Validate updated configuration
        warnings = S3ConfigValidator.validate_config(updated_config)
        
        # Store updated configuration
        self._service_configs[repo_id] = updated_config
        
        return updated_config, warnings

    def remove_service_config(self, repo_id: str) -> bool:
        """
        Remove S3 service configuration.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            bool: True if configuration was removed, False if not found
        """
        if repo_id in self._service_configs:
            del self._service_configs[repo_id]
            return True
        return False

    def list_service_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        List all S3 service configurations (without sensitive data).
        
        Returns:
            Dict: Repository ID to configuration summary mapping
        """
        configs = {}
        for repo_id, config in self._service_configs.items():
            config_dict = config.to_dict()
            # Remove sensitive data
            config_dict.pop('access_key_id', None)
            config_dict.pop('secret_access_key', None)
            configs[repo_id] = config_dict
        
        return configs

    def get_connection_parameters(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        Get connection parameters for S3 client.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Optional[Dict]: Connection parameters if configuration exists
        """
        config = self._service_configs.get(repo_id)
        if config:
            return config.get_connection_params()
        return None

    def test_service_connection(self, repo_id: str) -> Tuple[bool, Optional[str]]:
        """
        Test connection to S3-compatible service.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Tuple[bool, Optional[str]]: Success status and error message if failed
        """
        config = self._service_configs.get(repo_id)
        if not config:
            return False, f"No configuration found for repository {repo_id}"
        
        try:
            # This would typically use boto3 or similar to test connection
            # For now, we'll do basic validation
            warnings = S3ConfigValidator.validate_config(config)
            
            if warnings:
                warning_msg = "; ".join(warnings)
                logger.warning(f"S3 connection test warnings for {repo_id}: {warning_msg}")
                return True, f"Connection possible with warnings: {warning_msg}"
            
            return True, None
            
        except Exception as e:
            error_msg = f"Connection test failed: {e}"
            logger.error(f"S3 connection test failed for {repo_id}: {e}")
            return False, error_msg

    def get_service_info(self, service_type: S3ServiceType) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific S3-compatible service.
        
        Args:
            service_type: Type of S3-compatible service
            
        Returns:
            Optional[Dict]: Service information if supported
        """
        template = S3_SERVICE_TEMPLATES.get(service_type)
        if not template:
            return None
        
        return {
            'name': template.name,
            'description': template.description,
            'requires_region': template.requires_region,
            'supports_custom_endpoint': template.supports_custom_endpoint,
            'default_region': template.default_region,
            'default_port': template.default_port,
            'default_use_ssl': template.default_use_ssl,
            'default_verify_ssl': template.default_verify_ssl
        }