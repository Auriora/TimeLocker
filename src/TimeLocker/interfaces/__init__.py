"""
TimeLocker Interfaces Package

This package contains abstract interfaces that define contracts for
TimeLocker components, following the Dependency Inversion Principle.
"""

from .repository_factory import IRepositoryFactory
from .configuration_provider import IConfigurationProvider
from .credential_provider import ICredentialProvider
from .backup_orchestrator import IBackupOrchestrator

# Exception classes
from .exceptions import (
    TimeLockerInterfaceError,
    RepositoryFactoryError,
    UnsupportedSchemeError,
    ConfigurationError,
    ConfigurationNotFoundError,
    InvalidConfigurationError,
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

        # Exceptions
        'TimeLockerInterfaceError',
        'RepositoryFactoryError',
        'UnsupportedSchemeError',
        'ConfigurationError',
        'ConfigurationNotFoundError',
        'InvalidConfigurationError',
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
