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

Scheduling Exception Classes

This module defines exception classes for the scheduling system,
providing clear error categorization and recovery guidance.
"""


class SchedulingError(Exception):
    """Base exception for all scheduling operations."""
    
    def __init__(self, message: str, details: dict[str, object] | None = None):
        """
        Initialize scheduling error.
        
        Args:
            message: Error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message: str = message
        self.details: dict[str, object] = details or {}


class PlatformSchedulerError(SchedulingError):
    """Platform scheduler operation failed."""
    pass


class PolicyValidationError(SchedulingError):
    """Backup policy validation failed."""
    pass


class DataSelectionValidationError(SchedulingError):
    """Data selection validation failed."""
    pass


class RepositoryValidationError(SchedulingError):
    """Repository access validation failed."""
    pass


class CredentialAccessError(SchedulingError):
    """Credential access failed."""
    pass


class ExecutionTimeoutError(SchedulingError):
    """Backup execution timed out."""
    pass


class ScheduleConflictError(SchedulingError):
    """Schedule conflict detected."""
    pass


class UnsupportedPlatformError(SchedulingError):
    """Platform or scheduler not supported."""
    pass
