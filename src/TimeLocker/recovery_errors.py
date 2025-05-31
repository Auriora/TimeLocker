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


class RecoveryError(Exception):
    """Base exception for recovery operations"""
    pass


class SnapshotNotFoundError(RecoveryError):
    """Raised when a requested snapshot cannot be found"""
    pass


class RestoreError(RecoveryError):
    """Base exception for restore operations"""
    pass


class RestoreTargetError(RestoreError):
    """Raised when there are issues with the restore target path"""
    pass


class RestorePermissionError(RestoreError):
    """Raised when there are permission issues during restore"""
    pass


class RestoreVerificationError(RestoreError):
    """Raised when restore verification fails"""
    pass


class RestoreInterruptedError(RestoreError):
    """Raised when a restore operation is interrupted"""
    pass


class FileConflictError(RestoreError):
    """Raised when files already exist at the restore destination"""
    pass


class SnapshotCorruptedError(RecoveryError):
    """Raised when a snapshot is corrupted or incomplete"""
    pass


class InsufficientSpaceError(RestoreError):
    """Raised when there is insufficient disk space for restore"""
    pass
