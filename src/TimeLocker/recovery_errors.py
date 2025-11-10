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


class ValidationError(RecoveryError):
    """Raised when validation operations fail"""
    pass


class NetworkInterruptionError(RecoveryError):
    """Raised when network connectivity is lost during recovery"""
    pass


class NetworkTimeoutError(NetworkInterruptionError):
    """Raised when network operations timeout during recovery"""
    pass


class RepositoryConnectionError(NetworkInterruptionError):
    """Raised when connection to repository is lost"""
    pass


class FileSystemError(RestoreError):
    """Base exception for file system related errors during recovery"""
    pass


class FileSystemFullError(FileSystemError):
    """Raised when the target file system is full"""
    pass


class FileSystemReadOnlyError(FileSystemError):
    """Raised when attempting to write to a read-only file system"""
    pass


class FileSystemCorruptionError(FileSystemError):
    """Raised when file system corruption is detected"""
    pass


class PathTooLongError(FileSystemError):
    """Raised when a file path exceeds system limits"""
    pass


class SymlinkError(FileSystemError):
    """Raised when there are issues with symbolic links"""
    pass


class RecoveryStateError(RecoveryError):
    """Raised when recovery operation state is invalid or corrupted"""
    pass


class RecoveryCancelledError(RecoveryError):
    """Raised when a recovery operation is cancelled by user"""
    pass


class RecoveryTimeoutError(RecoveryError):
    """Raised when a recovery operation exceeds time limits"""
    pass


class PartialRecoveryError(RecoveryError):
    """Raised when recovery completes but with some failures"""
    
    def __init__(self, message: str, successful_files: int = 0, failed_files: int = 0):
        """
        Initialize PartialRecoveryError with success/failure counts.
        
        Args:
            message: Error message
            successful_files: Number of successfully recovered files
            failed_files: Number of files that failed to recover
        """
        super().__init__(message)
        self.successful_files = successful_files
        self.failed_files = failed_files


class ChecksumMismatchError(ValidationError):
    """Raised when file checksums don't match after recovery"""
    
    def __init__(self, file_path: str, expected: str, actual: str):
        """
        Initialize ChecksumMismatchError with checksum details.
        
        Args:
            file_path: Path to the file with mismatched checksum
            expected: Expected checksum value
            actual: Actual checksum value
        """
        message = f"Checksum mismatch for {file_path}: expected {expected}, got {actual}"
        super().__init__(message)
        self.file_path = file_path
        self.expected_checksum = expected
        self.actual_checksum = actual


class MetadataError(RecoveryError):
    """Raised when there are issues with file metadata during recovery"""
    pass


class RepositoryAccessError(RecoveryError):
    """Raised when repository cannot be accessed for recovery operations"""
    pass


class SelectionValidationError(RecoveryError):
    """Raised when selection criteria validation fails during recovery"""
    pass


class EncryptionKeyError(RecoveryError):
    """Raised when encryption key is missing or invalid for encrypted snapshots"""
    pass
