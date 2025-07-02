"""
Configuration schema definitions for TimeLocker.

This module provides type-safe configuration models using dataclasses,
following the Single Responsibility Principle by focusing solely on
configuration structure definition.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum


class LogLevel(Enum):
    """Supported log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CompressionType(Enum):
    """Supported compression types"""
    AUTO = "auto"
    NONE = "none"
    GZIP = "gzip"
    LZMA = "lzma"
    ZSTD = "zstd"


class ThemeType(Enum):
    """Supported UI themes"""
    AUTO = "auto"
    LIGHT = "light"
    DARK = "dark"


@dataclass
class GeneralConfig:
    """General application configuration"""
    app_name: str = "TimeLocker"
    version: str = "1.0.0"
    log_level: LogLevel = LogLevel.INFO
    data_dir: Optional[str] = None
    temp_dir: Optional[str] = None
    max_concurrent_operations: int = 2
    default_repository: Optional[str] = None


@dataclass
class BackupConfig:
    """Backup operation configuration"""
    compression: CompressionType = CompressionType.AUTO
    exclude_caches: bool = True
    exclude_if_present: List[str] = field(default_factory=lambda: [".nobackup", "CACHEDIR.TAG"])
    one_file_system: bool = False
    verify_after_backup: bool = True
    check_before_backup: bool = False
    dry_run: bool = False
    verbose: bool = False
    progress: bool = True
    stats: bool = True
    cleanup_cache: bool = True
    limit_upload: Optional[int] = None  # KB/s
    limit_download: Optional[int] = None


@dataclass
class RestoreConfig:
    """Restore operation configuration"""
    verify_after_restore: bool = True
    create_target_directory: bool = True
    overwrite_existing: bool = False
    preserve_permissions: bool = True
    preserve_ownership: bool = True
    preserve_timestamps: bool = True
    sparse_files: bool = True
    progress: bool = True
    verbose: bool = False
    conflict_resolution: str = "prompt"  # prompt, skip, overwrite, keep_both


@dataclass
class SecurityConfig:
    """Security and encryption configuration"""
    encryption_enabled: bool = True
    audit_logging: bool = True
    credential_timeout: int = 3600  # seconds
    max_failed_attempts: int = 3
    lockout_duration: int = 300  # seconds
    password_strength_check: bool = True
    require_password_confirmation: bool = True


@dataclass
class UIConfig:
    """User interface configuration"""
    theme: ThemeType = ThemeType.AUTO
    show_advanced_options: bool = False
    auto_refresh_interval: int = 30  # seconds
    max_log_entries: int = 1000
    confirm_destructive_actions: bool = True
    show_hidden_files: bool = False
    default_view: str = "list"  # list, tree, grid
    window_width: int = 1200
    window_height: int = 800


@dataclass
class NotificationConfig:
    """Notification system configuration"""
    enabled: bool = True
    desktop_enabled: bool = True
    email_enabled: bool = False
    notify_on_success: bool = True
    notify_on_error: bool = True
    notify_on_warning: bool = True
    sound_enabled: bool = False
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""
    status_retention_days: int = 30
    metrics_enabled: bool = True
    performance_monitoring: bool = True
    detailed_logging: bool = False
    log_rotation_size: int = 10  # MB
    log_retention_days: int = 7
    export_metrics: bool = False
    metrics_endpoint: Optional[str] = None


@dataclass
class RepositoryConfig:
    """Repository configuration"""
    name: str
    location: Optional[str] = None
    password: Optional[str] = None
    password_file: Optional[str] = None
    password_command: Optional[str] = None
    cache_dir: Optional[str] = None
    compression: Optional[CompressionType] = None
    pack_size: Optional[int] = None  # MB
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    read_only: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        from dataclasses import asdict
        result = asdict(self)

        # Convert enums to their values for JSON serialization
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif hasattr(obj, 'value'):  # Enum
                return obj.value
            else:
                return obj

        return convert_enums(result)


@dataclass
class BackupTargetConfig:
    """Backup target configuration"""
    name: str
    paths: List[str]
    repository: str
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    exclude_files: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    schedule: Optional[str] = None  # cron expression
    retention_policy: Optional[Dict[str, int]] = None
    pre_backup_script: Optional[str] = None
    post_backup_script: Optional[str] = None
    enabled: bool = True
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        from dataclasses import asdict
        result = asdict(self)

        # Convert enums to their values for JSON serialization
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif hasattr(obj, 'value'):  # Enum
                return obj.value
            else:
                return obj

        return convert_enums(result)


@dataclass
class TimeLockerConfig:
    """Complete TimeLocker configuration"""
    general: GeneralConfig = field(default_factory=GeneralConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    restore: RestoreConfig = field(default_factory=RestoreConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    repositories: Dict[str, RepositoryConfig] = field(default_factory=dict)
    backup_targets: Dict[str, BackupTargetConfig] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format"""
        from dataclasses import asdict
        result = asdict(self)

        # Convert enums to their values for JSON serialization
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif hasattr(obj, 'value'):  # Enum
                return obj.value
            else:
                return obj

        return convert_enums(result)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeLockerConfig':
        """Create configuration from dictionary"""
        # Extract main sections
        general = GeneralConfig(**data.get('general', {}))
        backup = BackupConfig(**data.get('backup', {}))
        restore = RestoreConfig(**data.get('restore', {}))
        security = SecurityConfig(**data.get('security', {}))
        ui = UIConfig(**data.get('ui', {}))
        notifications = NotificationConfig(**data.get('notifications', {}))
        monitoring = MonitoringConfig(**data.get('monitoring', {}))

        # Convert repositories
        repositories = {}
        for name, repo_data in data.get('repositories', {}).items():
            # Create a copy to avoid modifying original data
            repo_data_copy = repo_data.copy()
            # Remove 'name' from repo_data to avoid duplicate parameter
            repo_data_copy.pop('name', None)
            repositories[name] = RepositoryConfig(name=name, **repo_data_copy)

        # Convert backup targets
        backup_targets = {}
        for name, target_data in data.get('backup_targets', {}).items():
            # Create a copy to avoid modifying original data
            target_data_copy = target_data.copy()
            # Remove 'name' from target_data to avoid duplicate parameter
            target_data_copy.pop('name', None)
            backup_targets[name] = BackupTargetConfig(name=name, **target_data_copy)

        return cls(
                general=general,
                backup=backup,
                restore=restore,
                security=security,
                ui=ui,
                notifications=notifications,
                monitoring=monitoring,
                repositories=repositories,
                backup_targets=backup_targets
        )

    def merge_with_defaults(self, defaults: 'TimeLockerConfig') -> 'TimeLockerConfig':
        """Merge this configuration with defaults, preserving existing values"""
        # This is a simplified merge - in practice, you'd want more sophisticated merging
        merged_dict = defaults.to_dict()
        current_dict = self.to_dict()

        # Deep merge logic would go here
        # For now, simple update
        merged_dict.update(current_dict)

        return TimeLockerConfig.from_dict(merged_dict)


# Type aliases for convenience
ConfigDict = Dict[str, Any]
ConfigValue = Union[str, int, bool, float, List[Any], Dict[str, Any]]
