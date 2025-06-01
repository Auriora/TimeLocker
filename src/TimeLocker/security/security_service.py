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

import hashlib
import logging
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .credential_manager import CredentialManager

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Base exception for security-related errors"""
    pass


class SecurityLevel(Enum):
    """Security levels for operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Represents a security event for audit logging"""
    timestamp: datetime
    event_type: str
    level: SecurityLevel
    description: str
    user_id: Optional[str] = None
    repository_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EncryptionStatus:
    """Status of encryption for a repository or operation"""
    is_encrypted: bool
    encryption_algorithm: Optional[str] = None
    key_derivation: Optional[str] = None
    last_verified: Optional[datetime] = None
    verification_hash: Optional[str] = None


class SecurityService:
    """
    Enhanced security service for TimeLocker that leverages Restic's encryption capabilities
    and provides additional security features including audit logging and monitoring.
    """

    def __init__(self, credential_manager: CredentialManager, config_dir: Optional[Path] = None):
        """
        Initialize security service
        
        Args:
            credential_manager: Credential manager instance
            config_dir: Directory for security configuration and logs
        """
        self.credential_manager = credential_manager

        if config_dir is None:
            config_dir = Path.home() / ".timelocker" / "security"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.audit_log_file = self.config_dir / "audit.log"
        self.security_config_file = self.config_dir / "security_config.json"

        # Security event handlers
        self._event_handlers: List[Callable[[SecurityEvent], None]] = []

        # Initialize audit log
        self._initialize_audit_log()

    def _initialize_audit_log(self):
        """Initialize the audit log with proper headers"""
        if not self.audit_log_file.exists():
            with open(self.audit_log_file, 'w') as f:
                f.write("# TimeLocker Security Audit Log\n")
                f.write(f"# Initialized: {datetime.now().isoformat()}\n")
                f.write("# Format: timestamp|event_type|level|description|user_id|repository_id|metadata\n")

    def add_event_handler(self, handler: Callable[[SecurityEvent], None]):
        """Add a security event handler"""
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: Callable[[SecurityEvent], None]):
        """Remove a security event handler"""
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    def log_security_event(self, event: SecurityEvent):
        """
        Log a security event to the audit log and notify handlers
        
        Args:
            event: Security event to log
        """
        try:
            # Create audit log entry
            log_entry = (
                    f"{event.timestamp.isoformat()}|"
                    f"{event.event_type}|"
                    f"{event.level.value}|"
                    f"{event.description}|"
                    f"{event.user_id or ''}|"
                    f"{event.repository_id or ''}|"
                    f"{event.metadata or {} }"
            )

            # Write to audit log
            with open(self.audit_log_file, 'a') as f:
                f.write(log_entry + "\n")

            # Notify event handlers
            for handler in self._event_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in security event handler: {e}")

            logger.info(f"Security event logged: {event.event_type} - {event.description}")

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            raise SecurityError(f"Failed to log security event: {e}")

    def verify_repository_encryption(self, repository) -> EncryptionStatus:
        """
        Verify that a repository is properly encrypted using Restic's encryption
        
        Args:
            repository: Repository instance to verify
            
        Returns:
            EncryptionStatus: Status of repository encryption
        """
        try:
            # Check if repository is initialized and encrypted
            if not repository.is_repository_initialized():
                return EncryptionStatus(is_encrypted=False)

            # Get repository configuration to check encryption
            repo_info = repository.get_repository_info()

            # Restic repositories are encrypted by default when initialized with a password
            is_encrypted = bool(repository._password)

            encryption_status = EncryptionStatus(
                    is_encrypted=is_encrypted,
                    encryption_algorithm="AES-256" if is_encrypted else None,
                    key_derivation="scrypt" if is_encrypted else None,
                    last_verified=datetime.now(),
                    verification_hash=self._calculate_verification_hash(repo_info)
            )

            # Log verification event
            self.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="encryption_verification",
                    level=SecurityLevel.MEDIUM,
                    description=f"Repository encryption verified: {is_encrypted}",
                    repository_id=getattr(repository, 'id', str(repository._location)),
                    metadata={
                            "is_encrypted": is_encrypted,
                            "algorithm":    encryption_status.encryption_algorithm
                    }
            ))

            return encryption_status

        except Exception as e:
            logger.error(f"Failed to verify repository encryption: {e}")
            raise SecurityError(f"Failed to verify repository encryption: {e}")

    def _calculate_verification_hash(self, repo_info: Dict) -> str:
        """Calculate a verification hash for repository configuration"""
        # Create a hash of key repository configuration elements
        hash_data = f"{repo_info.get('id', '')}{repo_info.get('version', '')}"
        return hashlib.sha256(hash_data.encode()).hexdigest()[:16]

    def validate_backup_integrity(self, repository, snapshot_id: Optional[str] = None) -> bool:
        """
        Validate the integrity of backup data
        
        Args:
            repository: Repository to validate
            snapshot_id: Specific snapshot to validate (optional)
            
        Returns:
            bool: True if validation passes
        """
        try:
            # Use Restic's check command to validate repository integrity
            if snapshot_id:
                # Check specific snapshot
                result = repository.check_snapshot(snapshot_id)
            else:
                # Check entire repository
                result = repository.check()

            validation_passed = "error" not in result.lower()

            # Log validation event
            self.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="integrity_validation",
                    level=SecurityLevel.HIGH if validation_passed else SecurityLevel.CRITICAL,
                    description=f"Backup integrity validation: {'PASSED' if validation_passed else 'FAILED'}",
                    repository_id=getattr(repository, 'id', str(repository._location)),
                    metadata={
                            "snapshot_id":       snapshot_id,
                            "validation_result": validation_passed,
                            "details":           result[:200]  # Truncate for logging
                    }
            ))

            return validation_passed

        except Exception as e:
            logger.error(f"Failed to validate backup integrity: {e}")
            self.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="integrity_validation_error",
                    level=SecurityLevel.CRITICAL,
                    description=f"Integrity validation failed with error: {str(e)}",
                    repository_id=getattr(repository, 'id', str(repository._location)),
                    metadata={"error": str(e)}
            ))
            return False

    def audit_credential_access(self, credential_id: str, operation: str, success: bool):
        """
        Audit credential access operations
        
        Args:
            credential_id: ID of the credential accessed
            operation: Type of operation (read, write, delete)
            success: Whether the operation was successful
        """
        self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="credential_access",
                level=SecurityLevel.HIGH,
                description=f"Credential {operation} operation: {'SUCCESS' if success else 'FAILED'}",
                metadata={
                        "credential_id": credential_id,
                        "operation":     operation,
                        "success":       success
                }
        ))

    def get_security_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get a summary of security events for the specified period
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dict containing security summary
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            events_by_type = {}
            events_by_level = {}
            total_events = 0

            if self.audit_log_file.exists():
                with open(self.audit_log_file, 'r') as f:
                    for line in f:
                        if line.startswith('#'):
                            continue

                        try:
                            parts = line.strip().split('|')
                            if len(parts) >= 4:
                                event_time = datetime.fromisoformat(parts[0])
                                if event_time >= cutoff_date:
                                    event_type = parts[1]
                                    event_level = parts[2]

                                    events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                                    events_by_level[event_level] = events_by_level.get(event_level, 0) + 1
                                    total_events += 1
                        except (ValueError, IndexError):
                            continue

            return {
                    "period_days":     days,
                    "total_events":    total_events,
                    "events_by_type":  events_by_type,
                    "events_by_level": events_by_level,
                    "generated_at":    datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate security summary: {e}")
            raise SecurityError(f"Failed to generate security summary: {e}")

    def validate_security_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate security configuration settings

        Args:
            config: Security configuration to validate

        Returns:
            Dict containing validation results with 'valid', 'issues', 'warnings', 'recommendations'
        """
        issues = []
        warnings = []
        recommendations = []

        # Check encryption settings
        if not config.get("encryption_enabled", True):
            issues.append("Encryption is disabled - this is a security risk")

        # Check audit logging
        if not config.get("audit_logging", True):
            issues.append("Audit logging is disabled - this reduces security monitoring")

        # Check credential timeout
        timeout = config.get("credential_timeout", 3600)
        if timeout < 0:  # Negative timeout
            issues.append(f"Credential timeout ({timeout}s) cannot be negative")
        elif timeout < 300:  # Less than 5 minutes
            issues.append(f"Credential timeout ({timeout}s) is too short - minimum 300s recommended")
        elif timeout < 900:  # Less than 15 minutes
            warnings.append(f"Credential timeout ({timeout}s) is quite short - consider increasing")

        # Check max failed attempts
        max_attempts = config.get("max_failed_attempts", 3)
        if max_attempts <= 0:
            issues.append("Max failed attempts must be greater than 0")
        elif max_attempts > 10:
            warnings.append(f"Max failed attempts ({max_attempts}) is quite high - consider reducing")

        # Check lockout duration
        lockout = config.get("lockout_duration", 300)
        if lockout < 60:  # Less than 1 minute
            warnings.append(f"Lockout duration ({lockout}s) is very short")

        # Recommendations
        if config.get("encryption_enabled", True) and not config.get("key_rotation_enabled", False):
            recommendations.append("Consider enabling automatic key rotation for enhanced security")

        if not config.get("two_factor_enabled", False):
            recommendations.append("Consider enabling two-factor authentication")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations
        }

    def audit_backup_operation(self, repository=None, operation_type: str = None, targets: List[str] = None,
                               success: bool = True, metadata: Optional[Dict[str, Any]] = None,
                               operation_id: str = None, repository_id: str = None, status: str = None,
                               file_count: int = None, total_size: int = None):
        """
        Audit backup operations for security monitoring

        Args:
            repository: Repository instance (optional)
            operation_type: Type of backup operation (full, incremental, etc.)
            targets: List of backup targets (optional)
            success: Whether the operation was successful
            metadata: Additional operation metadata
            operation_id: ID of the backup operation
            repository_id: ID of the repository
            status: Status of the operation
            file_count: Number of files in the backup
            total_size: Total size of the backup
        """
        try:
            # Handle both old and new calling conventions
            if operation_id or repository_id or status or file_count or total_size:
                # New calling convention from tests
                audit_metadata = {
                        "operation_id":   operation_id,
                        "operation_type": operation_type,
                        "status":         status,
                        "file_count":     file_count,
                        "total_size":     total_size,
                        "success":        success
                }
                repo_id = repository_id or (getattr(repository, 'id', str(repository._location)) if repository else 'unknown')
            else:
                # Original calling convention
                audit_metadata = {
                        "operation_type":      operation_type,
                        "target_count":        len(targets) if targets else 0,
                        "targets":             targets[:5] if targets else [],  # Limit to first 5 for logging
                        "success":             success,
                        "repository_location": str(getattr(repository, '_location', 'unknown')) if repository else 'unknown'
                }
                repo_id = getattr(repository, 'id', str(repository._location)) if repository else 'unknown'

            if metadata:
                audit_metadata.update(metadata)

            self.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="backup_operation",
                    level=SecurityLevel.MEDIUM if success else SecurityLevel.HIGH,
                    description=f"Backup operation {operation_type or 'unknown'}: {'SUCCESS' if success else 'FAILED'}",
                    repository_id=repo_id,
                    metadata=audit_metadata
            ))

        except Exception as e:
            logger.error(f"Failed to audit backup operation: {e}")

    def audit_restore_operation(self, repository=None, snapshot_id: str = None, target_path: str = None,
                                success: bool = True, metadata: Optional[Dict[str, Any]] = None,
                                operation_id: str = None, repository_id: str = None, status: str = None,
                                files_restored: int = None):
        """
        Audit restore operations for security monitoring

        Args:
            repository: Repository instance (optional)
            snapshot_id: ID of the snapshot being restored
            target_path: Target path for restore
            success: Whether the operation was successful
            metadata: Additional operation metadata
            operation_id: ID of the restore operation
            repository_id: ID of the repository
            status: Status of the operation
            files_restored: Number of files restored
        """
        try:
            # Handle both old and new calling conventions
            if operation_id or repository_id or status or files_restored:
                # New calling convention from tests
                audit_metadata = {
                        "operation_id":    operation_id,
                        "snapshot_id":     snapshot_id,
                        "target_path":     str(target_path) if target_path else None,
                        "status":          status,
                        "files_restored":  files_restored,
                        "success":         success
                }
                repo_id = repository_id or (getattr(repository, 'id', str(repository._location)) if repository else 'unknown')
            else:
                # Original calling convention
                audit_metadata = {
                        "snapshot_id":         snapshot_id,
                        "target_path":         str(target_path) if target_path else None,
                        "success":             success,
                        "repository_location": str(getattr(repository, '_location', 'unknown')) if repository else 'unknown'
                }
                repo_id = getattr(repository, 'id', str(repository._location)) if repository else 'unknown'

            if metadata:
                audit_metadata.update(metadata)

            self.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="restore_operation",
                    level=SecurityLevel.HIGH,  # Restore operations are always high security
                    description=f"Restore operation: {'SUCCESS' if success else 'FAILED'}",
                    repository_id=repo_id,
                    metadata=audit_metadata
            ))

        except Exception as e:
            logger.error(f"Failed to audit restore operation: {e}")



    def emergency_lockdown(self, reason: str, metadata: Optional[Dict[str, Any]] = None, triggered_by: str = None) -> bool:
        """
        Initiate emergency lockdown procedures

        Args:
            reason: Reason for the emergency lockdown
            metadata: Additional metadata about the emergency
            triggered_by: Who or what triggered the lockdown

        Returns:
            bool: True if lockdown was successful
        """
        try:
            lockdown_metadata = {
                    "reason":           reason,
                    "triggered_by":     triggered_by,
                    "initiated_at":     datetime.now().isoformat(),
                    "lockdown_actions": []
            }

            if metadata:
                lockdown_metadata.update(metadata)

            # Lock credential manager
            try:
                self.credential_manager.lock()
                lockdown_metadata["lockdown_actions"].append("credential_manager_locked")
                logger.warning("Emergency lockdown: Credential manager locked")
            except Exception as e:
                logger.error(f"Failed to lock credential manager during emergency: {e}")
                lockdown_metadata["lockdown_actions"].append(f"credential_manager_lock_failed: {str(e)}")

            # Clear any cached credentials or sensitive data
            try:
                # Force garbage collection of sensitive data
                import gc
                gc.collect()
                lockdown_metadata["lockdown_actions"].append("memory_cleared")
            except Exception as e:
                logger.error(f"Failed to clear memory during emergency: {e}")

            # Create emergency lockdown marker file
            try:
                lockdown_file = self.config_dir / "emergency_lockdown.marker"
                with open(lockdown_file, 'w') as f:
                    json.dump(lockdown_metadata, f, indent=2)
                lockdown_metadata["lockdown_actions"].append("lockdown_marker_created")
            except Exception as e:
                logger.error(f"Failed to create lockdown marker: {e}")

            # Log critical security event
            self.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="emergency_lockdown",
                    level=SecurityLevel.CRITICAL,
                    description=f"Emergency lockdown initiated: {reason}",
                    metadata=lockdown_metadata
            ))

            logger.critical(f"Emergency lockdown completed: {reason}")
            return True

        except Exception as e:
            logger.critical(f"Emergency lockdown failed: {e}")
            # Still try to log the failure
            try:
                self.log_security_event(SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="emergency_lockdown_failed",
                        level=SecurityLevel.CRITICAL,
                        description=f"Emergency lockdown failed: {str(e)}",
                        metadata={"reason": reason, "error": str(e)}
                ))
            except:
                pass  # If we can't even log, we're in serious trouble
            return False

    def audit_integrity_check(self, repository=None, check_type: str = None, success: bool = None,
                              results: Optional[Dict[str, Any]] = None, file_path: str = None,
                              expected_hash: str = None, actual_hash: str = None, status: str = None, **kwargs):
        """
        Audit integrity check operations

        Args:
            repository: Repository instance (for original calling convention)
            check_type: Type of integrity check (full, snapshot, metadata, etc.)
            success: Whether the check was successful
            results: Results of the integrity check
            file_path: Path to the file being checked (for simplified calling convention)
            expected_hash: Expected hash value
            actual_hash: Actual hash value
            status: Status of the check (passed/failed)
        """
        try:
            # Determine which calling convention is being used
            if repository is not None and check_type is not None and success is not None:
                # Original calling convention
                audit_metadata = {
                        "check_type":          check_type,
                        "success":             success,
                        "repository_location": str(getattr(repository, '_location', 'unknown')),
                        "check_timestamp":     datetime.now().isoformat()
                }

                if results:
                    # Include key results but limit size for logging
                    audit_metadata["results_summary"] = {
                            "errors_found":   results.get("errors_found", 0),
                            "warnings_found": results.get("warnings_found", 0),
                            "items_checked":  results.get("items_checked", 0),
                            "check_duration": results.get("check_duration", 0)
                    }

                    # Include first few errors/warnings for context
                    if "errors" in results and results["errors"]:
                        audit_metadata["sample_errors"] = results["errors"][:3]
                    if "warnings" in results and results["warnings"]:
                        audit_metadata["sample_warnings"] = results["warnings"][:3]

                # Determine security level based on results
                if not success:
                    level = SecurityLevel.CRITICAL
                elif results and results.get("errors_found", 0) > 0:
                    level = SecurityLevel.HIGH
                elif results and results.get("warnings_found", 0) > 0:
                    level = SecurityLevel.MEDIUM
                else:
                    level = SecurityLevel.LOW

                description = f"Integrity check {check_type}: {'SUCCESS' if success else 'FAILED'}"
                repo_id = getattr(repository, 'id', str(repository._location))
            else:
                # Simplified calling convention
                audit_metadata = {
                        "file_path":      file_path,
                        "expected_hash":  expected_hash,
                        "actual_hash":    actual_hash,
                        "status":         status,
                        "check_timestamp": datetime.now().isoformat()
                }

                # Add any additional kwargs to metadata
                audit_metadata.update(kwargs)

                success = status == "passed" if status else (expected_hash == actual_hash)
                level = SecurityLevel.LOW if success else SecurityLevel.HIGH
                description = f"Integrity check: {status or ('PASSED' if success else 'FAILED')}"
                repo_id = None

            self.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="integrity_check",
                    level=level,
                    description=description,
                    repository_id=repo_id,
                    metadata=audit_metadata
            ))

        except Exception as e:
            logger.error(f"Failed to audit integrity check: {e}")
