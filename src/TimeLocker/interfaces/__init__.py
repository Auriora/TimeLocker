"""
TimeLocker Interfaces Package

This package contains abstract interfaces that define contracts for
TimeLocker components, following the Dependency Inversion Principle.
"""

from .repository_factory import IRepositoryFactory
from .configuration_provider import IConfigurationProvider
from .credential_provider import ICredentialProvider
from .backup_orchestrator import IBackupOrchestrator
from .configuration_store import IConfigurationStore
from .configuration_watcher import IConfigurationWatcher, ConfigurationChangeEvent
from .configuration_lock import IConfigurationLock, ConfigurationLock

# Integration Architecture Interfaces
from .service_interface import ServiceInterface

# Backup Engine Plugin Interface
from .backup_engine_plugin import (
    BackupEnginePlugin,
    BackupEngine,
    RepositoryType,
    ValidationResult,
    EngineCapabilities,
    PluginError,
    EngineNotAvailableError,
    EngineConfigurationError,
    UnsupportedStorageTypeError
)

# Exception classes
from .exceptions import (
    TimeLockerInterfaceError,
    RepositoryFactoryError,
    UnsupportedSchemeError,
    ConfigurationError,
    ConfigurationNotFoundError,
    InvalidConfigurationError,
    RepositoryNotFoundError,
    RepositoryAlreadyExistsError,
    ConfigurationStoreError,
    ConfigurationAtomicUpdateError,
    ConfigurationBackupError,
    ConfigurationLockError,
    ConfigurationLockTimeoutError,
    ConfigurationLockNotHeldError,
    ConfigurationStaleLockError,
    ConfigurationWatchError,
    ConfigurationWatchNotFoundError,
    ConfigurationWatchStartupError,
    ConfigurationValidationError,
    ConfigurationSchemaError,
    ConfigurationConstraintError,
    ConfigurationMigrationError,
    ConfigurationVersionError,
    ConfigurationCorruptionError,
    CredentialError,
    CredentialNotFoundError,
    CredentialAccessError,
    BackupOrchestratorError,
    InvalidBackupConfigurationError,
    BackupExecutionError,
    BackupCancellationError
)

# Integration Architecture Exceptions
from .integration_exceptions import (
    ServiceIntegrationError,
    ServiceInitializationError,
    ServiceShutdownError,
    ServiceContextError,
    ServiceContextValidationError,
    ServiceContextInheritanceError,
    EventSystemError,
    EventValidationError,
    EventCorrelationError,
    ServiceDiscoveryError,
    ServiceRegistrationError,
    DependencyResolutionError
)

# Data models
from .data_models import (
    BackupStatus,
    CredentialType,
    Credential,
    BackupResult,
    RestoreResult,
    SnapshotInfo,
    RepositoryInfo,
    BackupTargetInfo
)

# S3 Configuration Models
from .s3_config_models import (
    S3Config,
    S3ServiceType,
    S3ServiceTemplate,
    S3ConfigValidator,
    S3_SERVICE_TEMPLATES,
    create_s3_config_for_service
)

# Integration Architecture Data Models
from .integration_data_models import (
    ServiceContext,
    Event
)

# Recovery Operations Data Models
from .recovery_models import (
    RecoveryType,
    OperationStatus,
    FileType,
    FailureType,
    ConflictResolution,
    FileEntry,
    PaginationInfo,
    SnapshotListing,
    SizeRange,
    DateRange,
    SelectionCriteria,
    NotificationPreferences,
    RecoveryOptions,
    ProgressStatus,
    ErrorDetails,
    ValidationFailure,
    ValidationWarning,
    ValidationResult,
    RecoveryOperation
)

__all__ = [
        # Interfaces
        'IRepositoryFactory',
        'IConfigurationProvider',
        'ICredentialProvider',
        'IBackupOrchestrator',
        'IConfigurationStore',
        'IConfigurationWatcher',
        'IConfigurationLock',
        
        # Integration Architecture Interfaces
        'ServiceInterface',
        
        # Backup Engine Plugin Interface
        'BackupEnginePlugin',
        'BackupEngine',
        'RepositoryType',
        'ValidationResult',
        'EngineCapabilities',
        'PluginError',
        'EngineNotAvailableError',
        'EngineConfigurationError',
        'UnsupportedStorageTypeError',

        # Configuration Data Models
        'ConfigurationChangeEvent',
        'ConfigurationLock',

        # Exceptions
        'TimeLockerInterfaceError',
        'RepositoryFactoryError',
        'UnsupportedSchemeError',
        'ConfigurationError',
        'ConfigurationNotFoundError',
        'InvalidConfigurationError',
        'RepositoryNotFoundError',
        'RepositoryAlreadyExistsError',
        'ConfigurationStoreError',
        'ConfigurationAtomicUpdateError',
        'ConfigurationBackupError',
        'ConfigurationLockError',
        'ConfigurationLockTimeoutError',
        'ConfigurationLockNotHeldError',
        'ConfigurationStaleLockError',
        'ConfigurationWatchError',
        'ConfigurationWatchNotFoundError',
        'ConfigurationWatchStartupError',
        'ConfigurationValidationError',
        'ConfigurationSchemaError',
        'ConfigurationConstraintError',
        'ConfigurationMigrationError',
        'ConfigurationVersionError',
        'ConfigurationCorruptionError',
        'CredentialError',
        'CredentialNotFoundError',
        'CredentialAccessError',
        'BackupOrchestratorError',
        'InvalidBackupConfigurationError',
        'BackupExecutionError',
        'BackupCancellationError',
        
        # Integration Architecture Exceptions
        'ServiceIntegrationError',
        'ServiceInitializationError',
        'ServiceShutdownError',
        'ServiceContextError',
        'ServiceContextValidationError',
        'ServiceContextInheritanceError',
        'EventSystemError',
        'EventValidationError',
        'EventCorrelationError',
        'ServiceDiscoveryError',
        'ServiceRegistrationError',
        'DependencyResolutionError',

        # Data models
        'BackupStatus',
        'CredentialType',
        'Credential',
        'BackupResult',
        'RestoreResult',
        'SnapshotInfo',
        'RepositoryInfo',
        'BackupTargetInfo',
        
        # S3 Configuration Models
        'S3Config',
        'S3ServiceType',
        'S3ServiceTemplate',
        'S3ConfigValidator',
        'S3_SERVICE_TEMPLATES',
        'create_s3_config_for_service',
        
        # Integration Architecture Data Models
        'ServiceContext',
        'Event',
        
        # Recovery Operations Data Models
        'RecoveryType',
        'OperationStatus',
        'FileType',
        'FailureType',
        'ConflictResolution',
        'FileEntry',
        'PaginationInfo',
        'SnapshotListing',
        'SizeRange',
        'DateRange',
        'SelectionCriteria',
        'NotificationPreferences',
        'RecoveryOptions',
        'ProgressStatus',
        'ErrorDetails',
        'ValidationFailure',
        'ValidationWarning',
        'ValidationResult',
        'RecoveryOperation'
]
