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

__all__ = [
        # Interfaces
        'IRepositoryFactory',
        'IConfigurationProvider',
        'ICredentialProvider',
        'IBackupOrchestrator',
        'IConfigurationStore',
        'IConfigurationWatcher',
        'IConfigurationLock',

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

        # Data models
        'BackupStatus',
        'CredentialType',
        'Credential',
        'BackupResult',
        'RestoreResult',
        'SnapshotInfo',
        'RepositoryInfo',
        'BackupTargetInfo'
]
