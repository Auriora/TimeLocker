"""
S3-Compatible Service Configuration Models

Data models for S3-compatible service configuration including MinIO, Wasabi, 
Backblaze B2, and DigitalOcean Spaces.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class S3ServiceType(Enum):
    """Supported S3-compatible service types"""
    AWS_S3 = "aws_s3"
    MINIO = "minio"
    WASABI = "wasabi"
    BACKBLAZE_B2 = "backblaze_b2"
    DIGITALOCEAN_SPACES = "digitalocean_spaces"
    CUSTOM = "custom"


@dataclass
class S3Config:
    """
    Configuration for S3-compatible services with endpoint, region, and TLS configuration.
    """
    
    # Required fields
    access_key_id: str
    secret_access_key: str
    bucket: str
    
    # Optional fields with defaults
    endpoint: Optional[str] = None
    region: Optional[str] = None
    path_prefix: Optional[str] = None
    use_ssl: bool = True
    verify_ssl: bool = True
    connection_timeout: int = 30
    read_timeout: int = 300
    
    # Service-specific configuration
    service_type: S3ServiceType = S3ServiceType.AWS_S3
    custom_port: Optional[int] = None
    
    # Advanced configuration
    addressing_style: str = "auto"  # "auto", "path", "virtual"
    signature_version: str = "s3v4"
    max_retries: int = 3
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate and normalize configuration after initialization"""
        self._validate_configuration()
        self._normalize_endpoint()
    
    def _validate_configuration(self):
        """Validate S3 configuration parameters"""
        if not self.access_key_id:
            raise ValueError("access_key_id is required")
        
        if not self.secret_access_key:
            raise ValueError("secret_access_key is required")
        
        if not self.bucket:
            raise ValueError("bucket name is required")
        
        # Validate bucket name format
        if not self._is_valid_bucket_name(self.bucket):
            raise ValueError(f"Invalid bucket name: {self.bucket}")
        
        # Validate timeouts
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
        
        if self.read_timeout <= 0:
            raise ValueError("read_timeout must be positive")
        
        # Validate port if specified
        if self.custom_port is not None:
            if not (1 <= self.custom_port <= 65535):
                raise ValueError("custom_port must be between 1 and 65535")
    
    def _normalize_endpoint(self):
        """Normalize endpoint URL based on service type"""
        if self.endpoint:
            # Parse and validate endpoint URL
            parsed = urlparse(self.endpoint if '://' in self.endpoint else f"https://{self.endpoint}")
            
            # Extract port from endpoint if not specified separately
            if parsed.port and self.custom_port is None:
                self.custom_port = parsed.port
            
            # Normalize endpoint format
            scheme = "https" if self.use_ssl else "http"
            hostname = parsed.hostname or parsed.path
            
            if self.custom_port and self.custom_port not in (80, 443):
                self.endpoint = f"{scheme}://{hostname}:{self.custom_port}"
            else:
                self.endpoint = f"{scheme}://{hostname}"
        
        elif self.service_type != S3ServiceType.AWS_S3:
            # Generate endpoint for known services
            self.endpoint = self._generate_service_endpoint()
    
    def _generate_service_endpoint(self) -> Optional[str]:
        """Generate endpoint URL for known S3-compatible services"""
        service_configs = {
            S3ServiceType.MINIO: {
                "default_port": 9000,
                "endpoint_template": "{hostname}:{port}"
            },
            S3ServiceType.WASABI: {
                "endpoint_template": "s3.{region}.wasabisys.com"
            },
            S3ServiceType.BACKBLAZE_B2: {
                "endpoint_template": "s3.{region}.backblazeb2.com"
            },
            S3ServiceType.DIGITALOCEAN_SPACES: {
                "endpoint_template": "{region}.digitaloceanspaces.com"
            }
        }
        
        config = service_configs.get(self.service_type)
        if not config:
            return None
        
        template = config["endpoint_template"]
        
        # For MinIO, we need a hostname
        if self.service_type == S3ServiceType.MINIO:
            hostname = "localhost"  # Default for MinIO
            port = self.custom_port or config.get("default_port", 9000)
            endpoint = template.format(hostname=hostname, port=port)
        else:
            # For cloud services, we need a region
            if not self.region:
                logger.warning(f"Region required for {self.service_type.value} but not provided")
                return None
            endpoint = template.format(region=self.region)
        
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{endpoint}"
    
    def _is_valid_bucket_name(self, bucket_name: str) -> bool:
        """Validate S3 bucket name according to AWS rules"""
        if not bucket_name or len(bucket_name) < 3 or len(bucket_name) > 63:
            return False
        
        # Basic pattern check
        pattern = r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$'
        if not re.match(pattern, bucket_name):
            return False
        
        # Additional rules
        if '..' in bucket_name:  # No consecutive periods
            return False
        
        if '.-' in bucket_name or '-.' in bucket_name:  # No period-dash combinations
            return False
        
        # No IP address format
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if re.match(ip_pattern, bucket_name):
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "access_key_id": self.access_key_id,
            "secret_access_key": self.secret_access_key,
            "bucket": self.bucket,
            "endpoint": self.endpoint,
            "region": self.region,
            "path_prefix": self.path_prefix,
            "use_ssl": self.use_ssl,
            "verify_ssl": self.verify_ssl,
            "connection_timeout": self.connection_timeout,
            "read_timeout": self.read_timeout,
            "service_type": self.service_type.value,
            "custom_port": self.custom_port,
            "addressing_style": self.addressing_style,
            "signature_version": self.signature_version,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'S3Config':
        """Create configuration from dictionary"""
        # Convert service_type string back to enum
        if 'service_type' in data:
            data['service_type'] = S3ServiceType(data['service_type'])
        
        return cls(**data)
    
    def get_credentials_dict(self) -> Dict[str, str]:
        """Get credentials as dictionary for storage"""
        creds = {
            "access_key_id": self.access_key_id,
            "secret_access_key": self.secret_access_key
        }
        
        if self.region:
            creds["region"] = self.region
        
        if not self.verify_ssl:
            creds["insecure_tls"] = "true"
        
        return creds
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for S3 client"""
        params = {
            "aws_access_key_id": self.access_key_id,
            "aws_secret_access_key": self.secret_access_key,
            "use_ssl": self.use_ssl,
            "verify": self.verify_ssl,
            "config": {
                "connect_timeout": self.connection_timeout,
                "read_timeout": self.read_timeout,
                "retries": {"max_attempts": self.max_retries},
                "signature_version": self.signature_version,
                "s3": {"addressing_style": self.addressing_style}
            }
        }
        
        if self.endpoint:
            params["endpoint_url"] = self.endpoint
        
        if self.region:
            params["region_name"] = self.region
        
        return params


@dataclass
class S3ServiceTemplate:
    """Template for S3-compatible service configuration"""
    
    service_type: S3ServiceType
    name: str
    description: str
    endpoint_template: Optional[str] = None
    default_region: Optional[str] = None
    default_port: Optional[int] = None
    requires_region: bool = True
    supports_custom_endpoint: bool = True
    default_use_ssl: bool = True
    default_verify_ssl: bool = True
    
    def create_config(self, access_key_id: str, secret_access_key: str, 
                     bucket: str, **kwargs) -> S3Config:
        """Create S3Config from template with provided credentials"""
        config_data = {
            "access_key_id": access_key_id,
            "secret_access_key": secret_access_key,
            "bucket": bucket,
            "service_type": self.service_type,
            "use_ssl": kwargs.get("use_ssl", self.default_use_ssl),
            "verify_ssl": kwargs.get("verify_ssl", self.default_verify_ssl),
        }
        
        # Add region if provided or use default
        region = kwargs.get("region", self.default_region)
        if region:
            config_data["region"] = region
        
        # Add custom port if provided or use default
        port = kwargs.get("port", self.default_port)
        if port:
            config_data["custom_port"] = port
        
        # Add endpoint if provided
        endpoint = kwargs.get("endpoint")
        if endpoint:
            config_data["endpoint"] = endpoint
        
        # Add other optional parameters
        for key in ["path_prefix", "connection_timeout", "read_timeout", "description"]:
            if key in kwargs:
                config_data[key] = kwargs[key]
        
        return S3Config(**config_data)


# Predefined service templates
S3_SERVICE_TEMPLATES = {
    S3ServiceType.AWS_S3: S3ServiceTemplate(
        service_type=S3ServiceType.AWS_S3,
        name="Amazon S3",
        description="Amazon Simple Storage Service",
        requires_region=True,
        supports_custom_endpoint=False
    ),
    
    S3ServiceType.MINIO: S3ServiceTemplate(
        service_type=S3ServiceType.MINIO,
        name="MinIO",
        description="MinIO Object Storage",
        endpoint_template="http://{hostname}:{port}",
        default_port=9000,
        requires_region=False,
        default_use_ssl=False,
        default_verify_ssl=False
    ),
    
    S3ServiceType.WASABI: S3ServiceTemplate(
        service_type=S3ServiceType.WASABI,
        name="Wasabi Hot Cloud Storage",
        description="Wasabi S3-compatible storage",
        endpoint_template="https://s3.{region}.wasabisys.com",
        default_region="us-east-1",
        requires_region=True
    ),
    
    S3ServiceType.BACKBLAZE_B2: S3ServiceTemplate(
        service_type=S3ServiceType.BACKBLAZE_B2,
        name="Backblaze B2",
        description="Backblaze B2 S3-compatible API",
        endpoint_template="https://s3.{region}.backblazeb2.com",
        default_region="us-west-000",
        requires_region=True
    ),
    
    S3ServiceType.DIGITALOCEAN_SPACES: S3ServiceTemplate(
        service_type=S3ServiceType.DIGITALOCEAN_SPACES,
        name="DigitalOcean Spaces",
        description="DigitalOcean Spaces Object Storage",
        endpoint_template="https://{region}.digitaloceanspaces.com",
        default_region="nyc3",
        requires_region=True
    ),
    
    S3ServiceType.CUSTOM: S3ServiceTemplate(
        service_type=S3ServiceType.CUSTOM,
        name="Custom S3-Compatible Service",
        description="Generic S3-compatible endpoint with custom configuration",
        requires_region=False,
        supports_custom_endpoint=True
    )
}


class S3ConfigValidator:
    """Validator for S3 configuration with protocol validation and TLS warnings"""
    
    @staticmethod
    def validate_config(config: S3Config) -> List[str]:
        """
        Validate S3 configuration and return list of warnings/issues.
        
        Args:
            config: S3Config to validate
            
        Returns:
            List[str]: List of validation warnings/issues
        """
        warnings = []
        
        # TLS verification warnings
        if not config.verify_ssl:
            warnings.append(
                "TLS certificate verification is disabled. This may expose you to "
                "man-in-the-middle attacks. Only disable for trusted private networks."
            )
        
        if not config.use_ssl:
            warnings.append(
                "SSL/TLS is disabled. Credentials and data will be transmitted in plain text. "
                "This is strongly discouraged except for local development."
            )
        
        # Endpoint validation
        if config.endpoint:
            endpoint_warnings = S3ConfigValidator._validate_endpoint(config.endpoint, config.use_ssl)
            warnings.extend(endpoint_warnings)
        
        # Service-specific validation
        service_warnings = S3ConfigValidator._validate_service_specific(config)
        warnings.extend(service_warnings)
        
        return warnings
    
    @staticmethod
    def _validate_endpoint(endpoint: str, use_ssl: bool) -> List[str]:
        """Validate endpoint URL and protocol"""
        warnings = []
        
        try:
            parsed = urlparse(endpoint)
            
            # Protocol validation
            if parsed.scheme == "http" and use_ssl:
                warnings.append(
                    f"Endpoint uses HTTP but SSL is enabled. Consider using HTTPS endpoint."
                )
            elif parsed.scheme == "https" and not use_ssl:
                warnings.append(
                    f"Endpoint uses HTTPS but SSL is disabled. Consider enabling SSL."
                )
            
            # Hostname validation
            if not parsed.hostname:
                warnings.append("Endpoint does not contain a valid hostname")
            
            # Port validation
            if parsed.port:
                if parsed.scheme == "https" and parsed.port == 80:
                    warnings.append("HTTPS endpoint using port 80 (HTTP default)")
                elif parsed.scheme == "http" and parsed.port == 443:
                    warnings.append("HTTP endpoint using port 443 (HTTPS default)")
        
        except Exception as e:
            warnings.append(f"Invalid endpoint URL format: {e}")
        
        return warnings
    
    @staticmethod
    def _validate_service_specific(config: S3Config) -> List[str]:
        """Validate service-specific configuration"""
        warnings = []
        
        template = S3_SERVICE_TEMPLATES.get(config.service_type)
        if not template:
            return warnings
        
        # Region validation
        if template.requires_region and not config.region:
            warnings.append(f"{template.name} requires a region to be specified")
        
        # SSL validation for specific services
        if config.service_type == S3ServiceType.MINIO:
            if config.use_ssl and not config.endpoint:
                warnings.append(
                    "MinIO typically uses HTTP by default. Verify your MinIO server supports HTTPS."
                )
        if config.service_type == S3ServiceType.CUSTOM and not config.endpoint:
            warnings.append("Custom S3-compatible services require an explicit endpoint URL")
        
        return warnings


def create_s3_config_for_service(service_type: S3ServiceType, access_key_id: str, 
                                secret_access_key: str, bucket: str, **kwargs) -> S3Config:
    """
    Create S3Config for a specific service type with appropriate defaults.
    
    Args:
        service_type: Type of S3-compatible service
        access_key_id: Access key ID
        secret_access_key: Secret access key
        bucket: Bucket name
        **kwargs: Additional configuration parameters
        
    Returns:
        S3Config: Configured S3Config instance
        
    Raises:
        ValueError: If service type is not supported
    """
    template = S3_SERVICE_TEMPLATES.get(service_type)
    if not template:
        raise ValueError(f"Unsupported service type: {service_type}")
    
    return template.create_config(access_key_id, secret_access_key, bucket, **kwargs)
