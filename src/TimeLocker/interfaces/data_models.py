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
Data models for TimeLocker interfaces.

These models provide consistent data structures across interface implementations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class BackupStatus(Enum):
    """Enumeration of backup operation statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class CredentialType(Enum):
    """Enumeration of credential types"""
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"


class OperationStatus(Enum):
    """Enumeration of operation statuses"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"


@dataclass
class Credential:
    """
    Represents a credential for authentication.
    """
    key: str
    value: str
    credential_type: CredentialType
    repository_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate credential data after initialization"""
        if not self.key:
            raise ValueError("Credential key cannot be empty")
        if not self.value:
            raise ValueError("Credential value cannot be empty")


@dataclass
class BackupResult:
    """
    Represents the result of a backup operation.
    """
    status: BackupStatus
    repository_name: str
    target_names: List[str]
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    snapshot_id: Optional[str] = None
    files_processed: int = 0
    bytes_processed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Calculate operation duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_successful(self) -> bool:
        """Check if backup was successful"""
        return self.status == BackupStatus.COMPLETED and not self.errors

    @property
    def has_warnings(self) -> bool:
        """Check if backup has warnings"""
        return len(self.warnings) > 0

    def add_error(self, error: str) -> None:
        """Add an error to the result"""
        self.errors.append(error)
        if self.status not in [BackupStatus.FAILED, BackupStatus.CANCELLED]:
            self.status = BackupStatus.FAILED

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result"""
        self.warnings.append(warning)


@dataclass
class RestoreResult:
    """
    Represents the result of a restore operation.
    """
    status: BackupStatus
    repository_name: str
    snapshot_id: str
    target_path: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    files_restored: int = 0
    bytes_restored: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Calculate operation duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_successful(self) -> bool:
        """Check if restore was successful"""
        return self.status == BackupStatus.COMPLETED and not self.errors


@dataclass
class SnapshotInfo:
    """
    Represents information about a backup snapshot.
    """
    id: str
    repository_name: str
    timestamp: float
    hostname: str
    username: str
    paths: List[str]
    tags: List[str] = field(default_factory=list)
    size: Optional[int] = None
    file_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def short_id(self) -> str:
        """Get shortened snapshot ID for display"""
        return self.id[:8] if len(self.id) >= 8 else self.id


@dataclass
class RepositoryInfo:
    """
    Represents information about a backup repository.
    """
    name: str
    uri: str
    repository_type: str
    total_size: Optional[int] = None
    snapshot_count: Optional[int] = None
    last_backup: Optional[float] = None
    is_locked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupTargetInfo:
    """
    Represents information about a backup target.
    """
    name: str
    paths: List[str]
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    last_backup: Optional[float] = None
    estimated_size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapshotResult:
    """Result of a snapshot operation"""
    status: OperationStatus
    snapshot_id: str
    message: str
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class SnapshotSearchResult:
    """Result of searching within a snapshot"""
    path: str
    name: str
    type: str  # 'file' or 'dir'
    size: Optional[int] = None
    modified_time: Optional[datetime] = None
    match_type: str = 'name'  # 'name', 'content', 'path'


@dataclass
class SnapshotDiffResult:
    """Result of snapshot comparison"""
    added_files: List[str]
    removed_files: List[str]
    modified_files: List[str]
    unchanged_files: List[str]
    size_changes: Dict[str, Dict[str, int]] = field(default_factory=dict)  # file -> {'old': size, 'new': size}
    metadata_changes: Dict[str, Any] = field(default_factory=dict)


class ExecutionMode(Enum):
    """Backup execution mode"""
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    MANUAL_RETRY = "manual_retry"
    POLICY_DRIVEN = "policy_driven"


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    base_delay_seconds: float = 2.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 60.0
    retry_on_errors: List[str] = field(default_factory=lambda: [
        "network_timeout",
        "connection_error",
        "temporary_failure"
    ])
    
    def __post_init__(self):
        """Validate retry configuration"""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be non-negative")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")


@dataclass
class NotificationConfig:
    """Configuration for backup notifications"""
    enabled: bool = True
    notify_on_success: bool = True
    notify_on_failure: bool = True
    notify_on_warning: bool = False
    notification_channels: List[str] = field(default_factory=list)
    minimum_duration_for_notification: float = 60.0  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupJobConfig:
    """Configuration for a backup job execution"""
    job_id: str
    repository_id: str
    execution_mode: ExecutionMode = ExecutionMode.ON_DEMAND
    policy_id: Optional[str] = None
    data_selection_id: Optional[str] = None
    target_names: List[str] = field(default_factory=list)
    tool_type: str = "restic"
    tags: List[str] = field(default_factory=list)
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    notification_config: NotificationConfig = field(default_factory=NotificationConfig)
    dry_run: bool = False
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate job configuration"""
        if not self.job_id:
            raise ValueError("job_id cannot be empty")
        if not self.repository_id:
            raise ValueError("repository_id cannot be empty")
        if not self.target_names and not self.data_selection_id and not self.policy_id:
            raise ValueError("Must specify target_names, data_selection_id, or policy_id")


@dataclass
class ExecutionContext:
    """Runtime context for backup job execution"""
    start_time: float
    attempt_number: int = 1
    previous_errors: List[str] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)
    performance_hints: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolConfiguration:
    """Configuration for backup tool execution"""
    tool_type: str
    parallel_operations: int = 1
    compression_level: Optional[int] = None
    encryption_enabled: bool = True
    integrity_check_enabled: bool = True
    bandwidth_limit: Optional[int] = None  # bytes per second
    tool_specific_options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate tool configuration"""
        if self.parallel_operations < 1:
            raise ValueError("parallel_operations must be >= 1")
        if self.compression_level is not None and not (0 <= self.compression_level <= 9):
            raise ValueError("compression_level must be between 0 and 9")


@dataclass
class BackupJob:
    """Runtime representation of a backup job"""
    config: BackupJobConfig
    source_paths: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    tool_configuration: Optional[ToolConfiguration] = None
    execution_context: Optional[ExecutionContext] = None
    data_selection_config: Optional[Dict[str, Any]] = None
    policy_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.tool_configuration is None:
            self.tool_configuration = ToolConfiguration(tool_type=self.config.tool_type)
        if self.execution_context is None:
            import time
            self.execution_context = ExecutionContext(start_time=time.time())


@dataclass
class ValidationResult:
    """Result of job configuration validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_details: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """Add a validation error"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a validation warning"""
        self.warnings.append(warning)
