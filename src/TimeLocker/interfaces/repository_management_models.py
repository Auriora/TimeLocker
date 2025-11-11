"""
Repository Management Data Models for TimeLocker

This module provides enhanced data models for repository management operations,
including repository configuration, state management, and validation results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path


class BackupEngine(Enum):
    """Supported backup engines"""
    RESTIC = "restic"
    RSYNC = "rsync"
    RCLONE = "rclone"


class RepositoryType(Enum):
    """Repository storage types"""
    LOCAL = "local"
    S3 = "s3"
    B2 = "b2"
    SFTP = "sftp"
    SMB = "smb"
    NFS = "nfs"


class RepositoryStatus(Enum):
    """Repository operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    VALIDATING = "validating"


class ConnectivityStatus(Enum):
    """Repository connectivity status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    TIMEOUT = "timeout"
    AUTHENTICATION_FAILED = "authentication_failed"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class IntegrityStatus(Enum):
    """Repository integrity status"""
    VALID = "valid"
    CORRUPTED = "corrupted"
    INCOMPLETE = "incomplete"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Result of repository validation operations"""
    success: bool
    timestamp: datetime
    connectivity_status: ConnectivityStatus
    integrity_status: IntegrityStatus
    error_details: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed"""
        return self.success and not self.error_details
    
    def add_error(self, error: str) -> None:
        """Add an error to the validation result"""
        self.error_details.append(error)
        self.success = False
    
    def add_recommendation(self, recommendation: str) -> None:
        """Add a recommendation to improve repository performance or reliability"""
        self.recommendations.append(recommendation)


@dataclass
class ConnectivityResult:
    """Result of repository connectivity testing"""
    success: bool
    status: ConnectivityStatus
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IntegrityResult:
    """Result of repository integrity checking"""
    success: bool
    status: IntegrityStatus
    issues_found: List[str] = field(default_factory=list)
    repair_suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConfigValidationResult:
    """Result of repository configuration validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ExistingRepositoryInfo:
    """Information about an existing repository found at a URI"""
    uri: str
    engine_type: BackupEngine
    requires_credentials: bool
    repository_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_modified: Optional[datetime] = None
    estimated_size: Optional[int] = None
    snapshot_count: Optional[int] = None
    
    def format_size(self) -> str:
        """Format estimated size for display"""
        if not self.estimated_size:
            return "Unknown"
        
        size = self.estimated_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


@dataclass
class RepositoryCreationOptions:
    """Options for repository creation operations"""
    connect_if_exists: bool = False
    reinitialize_if_exists: bool = False
    require_confirmation_for_reinit: bool = True
    backup_existing_config: bool = True
    force_confirmation: bool = False


@dataclass
class UsageStats:
    """Repository usage statistics"""
    total_size: Optional[int] = None
    snapshot_count: Optional[int] = None
    last_backup: Optional[datetime] = None
    last_validation: Optional[datetime] = None
    backup_frequency: Optional[float] = None  # backups per day
    growth_rate: Optional[float] = None  # bytes per day


@dataclass
class RepositoryConfig:
    """Enhanced repository configuration"""
    name: str
    uri: str
    engine: BackupEngine
    type: RepositoryType
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_default: bool = False
    engine_config: Dict[str, Any] = field(default_factory=dict)
    # Status and validation tracking fields
    status: RepositoryStatus = RepositoryStatus.INACTIVE
    last_validated: Optional[datetime] = None
    validation_errors: List[str] = field(default_factory=list)
    performance_warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.name:
            raise ValueError("Repository name cannot be empty")
        if not self.uri:
            raise ValueError("Repository URI cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization"""
        return {
            'name': self.name,
            'uri': self.uri,
            'engine': self.engine.value,
            'type': self.type.value,
            'description': self.description,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_default': self.is_default,
            'engine_config': self.engine_config,
            'status': self.status.value,
            'last_validated': self.last_validated.isoformat() if self.last_validated else None,
            'validation_errors': self.validation_errors,
            'performance_warnings': self.performance_warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepositoryConfig':
        """Create from dictionary format"""
        last_validated = None
        if data.get('last_validated'):
            last_validated = datetime.fromisoformat(data['last_validated'])
            
        return cls(
            name=data['name'],
            uri=data['uri'],
            engine=BackupEngine(data['engine']),
            type=RepositoryType(data['type']),
            description=data.get('description'),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            is_default=data.get('is_default', False),
            engine_config=data.get('engine_config', {}),
            status=RepositoryStatus(data.get('status', 'inactive')),
            last_validated=last_validated,
            validation_errors=data.get('validation_errors', []),
            performance_warnings=data.get('performance_warnings', [])
        )


@dataclass
class Repository:
    """Repository instance with configuration and runtime state"""
    config: RepositoryConfig
    status: RepositoryStatus
    last_validated: Optional[datetime] = None
    validation_result: Optional[ValidationResult] = None
    usage_stats: Optional[UsageStats] = None
    
    @property
    def name(self) -> str:
        """Get repository name"""
        return self.config.name
    
    @property
    def uri(self) -> str:
        """Get repository URI"""
        return self.config.uri
    
    @property
    def is_healthy(self) -> bool:
        """Check if repository is in a healthy state"""
        return (self.status == RepositoryStatus.ACTIVE and 
                self.validation_result is not None and 
                self.validation_result.success)
    
    def update_status(self, new_status: RepositoryStatus) -> None:
        """Update repository status and timestamp"""
        self.status = new_status
        self.config.updated_at = datetime.utcnow()


@dataclass
class RepositoryStateTransition:
    """Record of repository state transition for audit logging"""
    repository_name: str
    from_state: RepositoryStatus
    to_state: RepositoryStatus
    timestamp: datetime
    correlation_id: str
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'repository_name': self.repository_name,
            'from_state': self.from_state.value,
            'to_state': self.to_state.value,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'context': self.context,
            'user_id': self.user_id
        }


# Repository Management Exceptions
class RepositoryError(Exception):
    """Base exception for repository operations"""
    pass


class RepositoryNotFoundError(RepositoryError):
    """Repository does not exist"""
    pass


class RepositoryAlreadyExistsError(RepositoryError):
    """Repository already exists at specified location"""
    def __init__(self, uri: str, existing_info: ExistingRepositoryInfo):
        self.uri = uri
        self.existing_info = existing_info
        super().__init__(f"Repository already exists at {uri}")


class RepositoryValidationError(RepositoryError):
    """Repository validation failed"""
    pass


class CredentialError(RepositoryError):
    """Credential-related errors"""
    pass


class BackendError(RepositoryError):
    """Storage backend errors"""
    pass


class RepositoryLockError(RepositoryError):
    """Repository is locked by another process"""
    pass


class DataLossConfirmationError(RepositoryError):
    """User confirmation required for data loss operation"""
    pass


class RepositoryStateError(RepositoryError):
    """Invalid repository state transition"""
    pass


# Engine-specific configuration classes
@dataclass
class ResticEngineConfig:
    """Configuration for Restic backup engine"""
    compression: str = "auto"
    pack_size: Optional[int] = None
    cache_dir: Optional[str] = None
    exclude_caches: bool = True
    one_file_system: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'compression': self.compression,
            'pack_size': self.pack_size,
            'cache_dir': self.cache_dir,
            'exclude_caches': self.exclude_caches,
            'one_file_system': self.one_file_system
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResticEngineConfig':
        """Create from dictionary"""
        return cls(
            compression=data.get('compression', 'auto'),
            pack_size=data.get('pack_size'),
            cache_dir=data.get('cache_dir'),
            exclude_caches=data.get('exclude_caches', True),
            one_file_system=data.get('one_file_system', False)
        )


@dataclass
class RsyncEngineConfig:
    """Configuration for Rsync backup engine"""
    archive_mode: bool = True
    compress: bool = True
    delete_excluded: bool = False
    preserve_permissions: bool = True
    preserve_times: bool = True
    dry_run: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'archive_mode': self.archive_mode,
            'compress': self.compress,
            'delete_excluded': self.delete_excluded,
            'preserve_permissions': self.preserve_permissions,
            'preserve_times': self.preserve_times,
            'dry_run': self.dry_run
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RsyncEngineConfig':
        """Create from dictionary"""
        return cls(
            archive_mode=data.get('archive_mode', True),
            compress=data.get('compress', True),
            delete_excluded=data.get('delete_excluded', False),
            preserve_permissions=data.get('preserve_permissions', True),
            preserve_times=data.get('preserve_times', True),
            dry_run=data.get('dry_run', False)
        )


@dataclass
class RcloneEngineConfig:
    """Configuration for Rclone backup engine"""
    config_file: Optional[str] = None
    transfers: int = 4
    checkers: int = 8
    buffer_size: str = "16M"
    use_mmap: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'config_file': self.config_file,
            'transfers': self.transfers,
            'checkers': self.checkers,
            'buffer_size': self.buffer_size,
            'use_mmap': self.use_mmap
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RcloneEngineConfig':
        """Create from dictionary"""
        return cls(
            config_file=data.get('config_file'),
            transfers=data.get('transfers', 4),
            checkers=data.get('checkers', 8),
            buffer_size=data.get('buffer_size', '16M'),
            use_mmap=data.get('use_mmap', False)
        )


# Engine configuration mapping
ENGINE_CONFIGURATIONS = {
    BackupEngine.RESTIC: ResticEngineConfig,
    BackupEngine.RSYNC: RsyncEngineConfig,
    BackupEngine.RCLONE: RcloneEngineConfig,
}


@dataclass
class S3Config:
    """Configuration for S3-compatible storage services"""
    endpoint: str
    region: Optional[str] = None
    access_key_id: str = ""
    secret_access_key: str = ""
    bucket: str = ""
    path_prefix: Optional[str] = None
    use_ssl: bool = True
    verify_ssl: bool = True
    connection_timeout: int = 30
    read_timeout: int = 300
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization (excluding sensitive data)"""
        return {
            'endpoint': self.endpoint,
            'region': self.region,
            'bucket': self.bucket,
            'path_prefix': self.path_prefix,
            'use_ssl': self.use_ssl,
            'verify_ssl': self.verify_ssl,
            'connection_timeout': self.connection_timeout,
            'read_timeout': self.read_timeout
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'S3Config':
        """Create from dictionary"""
        return cls(
            endpoint=data['endpoint'],
            region=data.get('region'),
            access_key_id=data.get('access_key_id', ''),
            secret_access_key=data.get('secret_access_key', ''),
            bucket=data.get('bucket', ''),
            path_prefix=data.get('path_prefix'),
            use_ssl=data.get('use_ssl', True),
            verify_ssl=data.get('verify_ssl', True),
            connection_timeout=data.get('connection_timeout', 30),
            read_timeout=data.get('read_timeout', 300)
        )


# S3-compatible service configurations
S3_COMPATIBLE_SERVICES = {
    'minio': {'default_port': 9000, 'supports_regions': False},
    'wasabi': {'endpoint_template': 's3.{region}.wasabisys.com'},
    'backblaze': {'endpoint_template': 's3.{region}.backblazeb2.com'},
    'digitalocean': {'endpoint_template': '{region}.digitaloceanspaces.com'},
}