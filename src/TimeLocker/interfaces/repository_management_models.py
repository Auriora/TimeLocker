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
            'engine_config': self.engine_config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepositoryConfig':
        """Create from dictionary format"""
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
            engine_config=data.get('engine_config', {})
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