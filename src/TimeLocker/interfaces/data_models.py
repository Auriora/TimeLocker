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
