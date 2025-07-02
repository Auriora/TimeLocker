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
Exception classes for TimeLocker interfaces.

These exceptions provide clear error handling contracts for interface implementations.
"""


class TimeLockerInterfaceError(Exception):
    """Base exception for all TimeLocker interface errors"""
    pass


# Repository Factory Exceptions
class RepositoryFactoryError(TimeLockerInterfaceError):
    """Base exception for repository factory errors"""
    pass


class UnsupportedSchemeError(RepositoryFactoryError):
    """Raised when a URI scheme is not supported by the factory"""
    pass


# Configuration Provider Exceptions
class ConfigurationError(TimeLockerInterfaceError):
    """Base exception for configuration-related errors"""
    pass


class ConfigurationNotFoundError(ConfigurationError):
    """Raised when configuration cannot be found"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid or malformed"""
    pass


# Credential Provider Exceptions
class CredentialError(TimeLockerInterfaceError):
    """Base exception for credential-related errors"""
    pass


class CredentialNotFoundError(CredentialError):
    """Raised when a credential cannot be found"""
    pass


class CredentialAccessError(CredentialError):
    """Raised when credential access fails"""
    pass


# Backup Orchestrator Exceptions
class BackupOrchestratorError(TimeLockerInterfaceError):
    """Base exception for backup orchestrator errors"""
    pass


class InvalidBackupConfigurationError(BackupOrchestratorError):
    """Raised when backup configuration is invalid"""
    pass


class BackupExecutionError(BackupOrchestratorError):
    """Raised when backup execution fails"""
    pass


class BackupCancellationError(BackupOrchestratorError):
    """Raised when backup cancellation fails"""
    pass
