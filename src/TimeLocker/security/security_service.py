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
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum

from .credential_manager import CredentialManager
from .repository_protection import RepositoryProtectionManager, RepositoryInfo, RepositoryMode
from .confirmation_dialogs import ConfirmationDialogs
from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext

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


class SecurityService(ServiceInterface):
    """
    Enhanced security service for TimeLocker that leverages Restic's encryption capabilities
    and provides additional security features including audit logging and monitoring.
    """

    def __init__(self, credential_manager: CredentialManager, config_dir: Optional[Path] = None, 
                 security_logger: Optional['SecurityLogger'] = None):
        """
        Initialize security service
        
        Args:
            credential_manager: Credential manager instance
            config_dir: Directory for security configuration and logs
            security_logger: Optional SecurityLogger instance for enhanced logging
        """
        self.credential_manager = credential_manager

        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            base_config_dir = ConfigurationPathResolver.get_config_directory()
            config_dir = base_config_dir / "security"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.audit_log_file = self.config_dir / "audit.log"
        self.security_config_file = self.config_dir / "security_config.json"

        # Security event handlers
        self._event_handlers: List[Callable[[SecurityEvent], None]] = []

        # Enhanced security logger
        self.security_logger = security_logger
        if self.security_logger is None:
            # Import here to avoid circular imports
            from .security_logger import SecurityLogger
            self.security_logger = SecurityLogger(config_dir=config_dir)

        # Repository protection manager
        self.repository_protection = RepositoryProtectionManager(config_dir=config_dir)
        
        # Confirmation dialogs
        self.confirmation_dialogs = ConfirmationDialogs()

        # Data privacy manager
        from .data_privacy_manager import DataPrivacyManager
        self.data_privacy_manager = DataPrivacyManager(
            config_dir=config_dir,
            security_logger=self.security_logger
        )

        # ServiceInterface implementation
        self._context: Optional[ServiceContext] = None
        self._initialized = False

        # Initialize audit log
        self._initialize_audit_log()
        
        # Integrate with existing logs
        self.security_logger.integrate_with_existing_logs()

    # ServiceInterface implementation
    def initialize(self, context: ServiceContext) -> bool:
        """
        Initialize the security service with the provided context.
        
        Args:
            context: ServiceContext containing configuration and runtime information
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            if not self.validate_context(context):
                logger.error("Invalid service context provided to SecurityService")
                return False
            
            self._context = context
            
            # Initialize any context-dependent components
            logger.info("SecurityService initialized successfully")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SecurityService: {e}")
            return False

    def shutdown(self) -> None:
        """
        Shutdown the security service and clean up resources.
        """
        try:
            # Clean up security resources
            if self.credential_manager:
                try:
                    self.credential_manager.lock()
                except Exception as e:
                    logger.warning(f"Failed to lock credential manager during shutdown: {e}")
            
            # Clean up resources
            self._context = None
            self._initialized = False
            logger.info("SecurityService shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during SecurityService shutdown: {e}")

    def health_check(self) -> bool:
        """
        Check the health status of the security service.
        
        Returns:
            bool: True if the service is healthy and operational, False otherwise
        """
        try:
            # Check if service is initialized
            if not self._initialized:
                return False
            
            # Check if credential manager is available
            if not self.credential_manager:
                return False
            
            # Check if security logger is available
            if not self.security_logger:
                return False
            
            # Check if audit log file is accessible
            if not self.audit_log_file.parent.exists():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"SecurityService health check failed: {e}")
            return False

    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities provided by this service.
        
        Returns:
            List[str]: List of capability identifiers
        """
        return [
            'encryption_verification',
            'integrity_validation',
            'credential_audit',
            'security_events',
            'backup_audit',
            'restore_audit',
            'emergency_lockdown',
            'repository_protection',
            'data_privacy'
        ]

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
            # Create audit log entry (maintain backward compatibility)
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

            # Also log to SecurityLogger for enhanced functionality
            if self.security_logger:
                from .security_logger import SecurityLogEntry, SecurityLogLevel, SecurityEventType
                
                # Map SecurityLevel to SecurityLogLevel
                level_mapping = {
                    SecurityLevel.LOW: SecurityLogLevel.LOW,
                    SecurityLevel.MEDIUM: SecurityLogLevel.MEDIUM,
                    SecurityLevel.HIGH: SecurityLogLevel.HIGH,
                    SecurityLevel.CRITICAL: SecurityLogLevel.CRITICAL
                }
                
                # Map event type string to SecurityEventType
                event_type_mapping = {
                    "encryption_verification": SecurityEventType.ENCRYPTION_VERIFICATION,
                    "integrity_validation": SecurityEventType.INTEGRITY_CHECK,
                    "integrity_validation_error": SecurityEventType.INTEGRITY_CHECK,
                    "credential_access": SecurityEventType.CREDENTIAL_ACCESS,
                    "backup_operation": SecurityEventType.BACKUP_OPERATION,
                    "restore_operation": SecurityEventType.RESTORE_OPERATION,
                    "emergency_lockdown": SecurityEventType.EMERGENCY_LOCKDOWN,
                    "emergency_lockdown_failed": SecurityEventType.EMERGENCY_LOCKDOWN,
                    "integrity_check": SecurityEventType.INTEGRITY_CHECK,
                }
                
                security_log_entry = SecurityLogEntry(
                    timestamp=event.timestamp,
                    event_type=event_type_mapping.get(event.event_type, SecurityEventType.SYSTEM_EVENT),
                    level=level_mapping.get(event.level, SecurityLogLevel.MEDIUM),
                    description=event.description,
                    user_id=event.user_id,
                    repository_id=event.repository_id,
                    metadata=event.metadata,
                    source="SecurityService"
                )
                
                self.security_logger.log_event(security_log_entry)

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

    def get_security_logs(self, days: int = 7, event_type: Optional[str] = None, 
                         level: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get security logs with user-friendly filtering
        
        Args:
            days: Number of days to look back (default: 7)
            event_type: Filter by event type (optional)
            level: Filter by security level (optional)
            limit: Maximum number of entries to return (optional)
            
        Returns:
            List of security log entries as dictionaries
        """
        if not self.security_logger:
            return []
        
        try:
            from .security_logger import EventFilter, SecurityEventType, SecurityLogLevel
            
            # Build filter criteria
            filter_criteria = EventFilter(
                start_date=datetime.now() - timedelta(days=days),
                limit=limit
            )
            
            if event_type:
                try:
                    filter_criteria.event_types = [SecurityEventType(event_type)]
                except ValueError:
                    logger.warning(f"Invalid event type: {event_type}")
            
            if level:
                try:
                    filter_criteria.levels = [SecurityLogLevel(level)]
                except ValueError:
                    logger.warning(f"Invalid security level: {level}")
            
            # Get events and convert to dictionaries
            events = self.security_logger.get_events(filter_criteria)
            return [event.to_dict() for event in events]
            
        except Exception as e:
            logger.error(f"Failed to get security logs: {e}")
            return []

    def get_security_audit(self, days: int = 7, repository_id: Optional[str] = None,
                           event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get security audit logs (alias for get_security_logs with repository filtering).

        Args:
            days: Number of days to look back (default: 7)
            repository_id: Filter by repository ID (optional)
            event_type: Filter by event type (optional)

        Returns:
            List of security audit entries as dictionaries
        """
        logs = self.get_security_logs(days=days, event_type=event_type)

        # Filter by repository_id if specified
        if repository_id:
            logs = [log for log in logs if log.get('repository_id') == repository_id]

        return logs

    def get_security_notifications(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent security notifications
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List of security notifications as dictionaries
        """
        if not self.security_logger:
            return []
        
        try:
            notifications = self.security_logger.get_notifications(hours=hours)
            return [notification.to_dict() for notification in notifications]
            
        except Exception as e:
            logger.error(f"Failed to get security notifications: {e}")
            return []

    def cleanup_security_logs(self) -> bool:
        """
        Clean up old security logs based on retention policy
        
        Returns:
            True if cleanup successful, False otherwise
        """
        if not self.security_logger:
            return False
        
        try:
            self.security_logger.cleanup_old_logs()
            logger.info("Security log cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup security logs: {e}")
            return False

    def export_security_logs(self, output_path: str, days: int = 30, 
                           format_type: str = "json") -> bool:
        """
        Export security logs to a file
        
        Args:
            output_path: Path to export file
            days: Number of days to include in export (default: 30)
            format_type: Export format ("json" or "csv")
            
        Returns:
            True if export successful, False otherwise
        """
        if not self.security_logger:
            return False
        
        try:
            from .security_logger import EventFilter
            
            filter_criteria = EventFilter(
                start_date=datetime.now() - timedelta(days=days)
            )
            
            success = self.security_logger.export_logs(
                output_path=Path(output_path),
                filter_criteria=filter_criteria,
                format_type=format_type
            )
            
            if success:
                logger.info(f"Security logs exported to: {output_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to export security logs: {e}")
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

    # Repository Protection Methods

    def lock_repository(self, repository_id: str, operation: str, 
                       locked_by: str = "system", timeout_minutes: Optional[int] = None) -> str:
        """
        Lock repository to prevent accidental modifications
        
        Args:
            repository_id: Repository ID to lock
            operation: Operation that requires the lock
            locked_by: User or process locking the repository
            timeout_minutes: Lock timeout in minutes
            
        Returns:
            str: Lock ID for the created lock
        """
        try:
            lock_id = self.repository_protection.lock_repository(
                repository_id, operation, locked_by, timeout_minutes
            )
            
            # Log security event
            self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="repository_lock",
                level=SecurityLevel.MEDIUM,
                description=f"Repository locked for operation: {operation}",
                repository_id=repository_id,
                metadata={
                    "lock_id": lock_id,
                    "operation": operation,
                    "locked_by": locked_by,
                    "timeout_minutes": timeout_minutes
                }
            ))
            
            return lock_id
            
        except Exception as e:
            logger.error(f"Failed to lock repository {repository_id}: {e}")
            raise SecurityError(f"Failed to lock repository: {e}")

    def unlock_repository(self, repository_id: str, lock_id: Optional[str] = None,
                         unlocked_by: str = "system") -> bool:
        """
        Unlock repository
        
        Args:
            repository_id: Repository ID to unlock
            lock_id: Specific lock ID to remove (optional)
            unlocked_by: User or process unlocking the repository
            
        Returns:
            bool: True if repository was unlocked successfully
        """
        try:
            success = self.repository_protection.unlock_repository(
                repository_id, lock_id, unlocked_by
            )
            
            # Log security event
            self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="repository_unlock",
                level=SecurityLevel.MEDIUM,
                description=f"Repository unlock {'successful' if success else 'failed'}",
                repository_id=repository_id,
                metadata={
                    "lock_id": lock_id,
                    "unlocked_by": unlocked_by,
                    "success": success
                }
            ))
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to unlock repository {repository_id}: {e}")
            return False

    def is_repository_locked(self, repository_id: str) -> bool:
        """
        Check if repository is currently locked
        
        Args:
            repository_id: Repository ID to check
            
        Returns:
            bool: True if repository is locked
        """
        return self.repository_protection.is_repository_locked(repository_id)

    def set_repository_mode(self, repository_id: str, mode: str,
                           changed_by: str = "system") -> bool:
        """
        Set repository access mode
        
        Args:
            repository_id: Repository ID to set mode for
            mode: Repository mode ('read_write', 'read_only', 'locked')
            changed_by: User or process changing the mode
            
        Returns:
            bool: True if mode was set successfully
        """
        try:
            # Convert string to RepositoryMode enum
            if mode == "read_write":
                repo_mode = RepositoryMode.READ_WRITE
            elif mode == "read_only":
                repo_mode = RepositoryMode.READ_ONLY
            elif mode == "locked":
                repo_mode = RepositoryMode.LOCKED
            else:
                raise ValueError(f"Invalid repository mode: {mode}")
            
            success = self.repository_protection.set_repository_mode(
                repository_id, repo_mode, changed_by
            )
            
            # Log security event
            self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="repository_mode_change",
                level=SecurityLevel.MEDIUM,
                description=f"Repository mode changed to {mode}",
                repository_id=repository_id,
                metadata={
                    "new_mode": mode,
                    "changed_by": changed_by,
                    "success": success
                }
            ))
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to set repository mode for {repository_id}: {e}")
            return False

    def get_repository_mode(self, repository_id: str) -> str:
        """
        Get repository access mode
        
        Args:
            repository_id: Repository ID to get mode for
            
        Returns:
            str: Current repository mode
        """
        mode = self.repository_protection.get_repository_mode(repository_id)
        return mode.value

    def is_operation_allowed(self, repository_id: str, operation: str) -> bool:
        """
        Check if operation is allowed on repository
        
        Args:
            repository_id: Repository ID to check
            operation: Operation to check
            
        Returns:
            bool: True if operation is allowed
        """
        return self.repository_protection.is_operation_allowed(repository_id, operation)

    def confirm_destructive_operation(self, operation_type: str, repository_info: Dict[str, Any],
                                    force: bool = False) -> bool:
        """
        Confirm destructive operation with user
        
        Args:
            operation_type: Type of destructive operation
            repository_info: Repository information dictionary
            force: Skip confirmation if True
            
        Returns:
            bool: True if operation is confirmed
        """
        try:
            # Convert dictionary to RepositoryInfo object
            repo_info = RepositoryInfo(
                repository_id=repository_info.get('repository_id', ''),
                name=repository_info.get('name', ''),
                location=repository_info.get('location', ''),
                size_bytes=repository_info.get('size_bytes'),
                snapshot_count=repository_info.get('snapshot_count'),
                last_backup=repository_info.get('last_backup'),
                created_at=repository_info.get('created_at'),
                mode=RepositoryMode(repository_info.get('mode', 'read_write'))
            )
            
            # Create destructive operation info
            operation = self.repository_protection.create_destructive_operation_info(
                operation_type, repo_info
            )
            
            # Get confirmation
            confirmed = self.confirmation_dialogs.confirm_destructive_operation(operation, force)
            
            # Log security event
            self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="destructive_operation_confirmation",
                level=SecurityLevel.HIGH,
                description=f"Destructive operation {operation_type} {'confirmed' if confirmed else 'cancelled'}",
                repository_id=repo_info.repository_id,
                metadata={
                    "operation_type": operation_type,
                    "confirmed": confirmed,
                    "force": force
                }
            ))
            
            return confirmed
            
        except Exception as e:
            logger.error(f"Failed to confirm destructive operation: {e}")
            return False

    def cleanup_repository_protection(self) -> Dict[str, int]:
        """
        Clean up expired repository locks and protection data
        
        Returns:
            Dict: Cleanup statistics
        """
        try:
            expired_locks = self.repository_protection.cleanup_expired_locks()
            
            # Log cleanup event
            self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="repository_protection_cleanup",
                level=SecurityLevel.LOW,
                description=f"Repository protection cleanup completed",
                metadata={
                    "expired_locks_cleaned": expired_locks
                }
            ))
            
            return {
                "expired_locks_cleaned": expired_locks
            }
            
        except Exception as e:
            logger.error(f"Repository protection cleanup failed: {e}")
            return {"expired_locks_cleaned": 0}

    def get_repository_protection_status(self) -> Dict[str, Any]:
        """
        Get repository protection status
        
        Returns:
            Dict: Protection status information
        """
        return self.repository_protection.get_protection_status()

    # Data Privacy Methods

    def get_privacy_info(self) -> Dict[str, Any]:
        """
        Get privacy information for user display
        
        Returns:
            Dict: Privacy information and status
        """
        try:
            privacy_info = self.data_privacy_manager.get_privacy_info()
            return {
                "data_types_processed": privacy_info.data_types_processed,
                "privacy_level": privacy_info.privacy_level.value,
                "retention_period_hours": privacy_info.retention_period.total_seconds() / 3600 if privacy_info.retention_period else None,
                "secure_deletion_enabled": privacy_info.secure_deletion_enabled,
                "encryption_status": privacy_info.encryption_status,
                "last_cleanup": privacy_info.last_cleanup.isoformat() if privacy_info.last_cleanup else None,
                "temporary_files_location": privacy_info.temporary_files_location,
                "privacy_policy_summary": privacy_info.privacy_policy_summary
            }
        except Exception as e:
            logger.error(f"Failed to get privacy info: {e}")
            return {}

    def get_privacy_recommendations(self, file_selection: 'FileSelection') -> List[Dict[str, Any]]:
        """
        Get privacy recommendations for file selection
        
        Args:
            file_selection: FileSelection object to analyze
            
        Returns:
            List of privacy recommendations
        """
        try:
            return self.data_privacy_manager.get_privacy_recommendations(file_selection)
        except Exception as e:
            logger.error(f"Failed to get privacy recommendations: {e}")
            return []

    def apply_privacy_exclusions(self, file_selection: 'FileSelection', 
                                exclude_patterns: List[str]) -> bool:
        """
        Apply privacy-based exclusions to file selection
        
        Args:
            file_selection: FileSelection object to modify
            exclude_patterns: List of patterns to exclude for privacy
            
        Returns:
            bool: True if exclusions were applied successfully
        """
        try:
            self.data_privacy_manager.apply_privacy_exclusions(file_selection, exclude_patterns)
            
            # Log security event
            self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="data_privacy",
                level=SecurityLevel.MEDIUM,
                description=f"Privacy exclusions applied: {len(exclude_patterns)} patterns",
                metadata={
                    "patterns_count": len(exclude_patterns),
                    "patterns": exclude_patterns[:5]  # Log first 5 patterns
                }
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply privacy exclusions: {e}")
            return False

    def cleanup_temporary_files(self, max_age_hours: Optional[int] = None) -> Dict[str, int]:
        """
        Clean up temporary files and cached data
        
        Args:
            max_age_hours: Maximum age of files to keep
            
        Returns:
            Dict: Cleanup statistics
        """
        try:
            stats = self.data_privacy_manager.cleanup_temporary_files(max_age_hours)
            
            # Log security event
            self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="data_privacy",
                level=SecurityLevel.LOW,
                description=f"Temporary file cleanup completed",
                metadata=stats
            ))
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to cleanup temporary files: {e}")
            return {"registered_files_deleted": 0, "old_files_deleted": 0, "errors": 1}

    def secure_delete_file(self, file_path: Union[str, Path]) -> bool:
        """
        Securely delete a file
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            bool: True if deletion successful
        """
        try:
            success = self.data_privacy_manager.secure_delete_file(file_path)
            
            # Log security event
            self.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="data_privacy",
                level=SecurityLevel.MEDIUM,
                description=f"Secure file deletion {'successful' if success else 'failed'}",
                metadata={
                    "file_path": str(file_path),
                    "success": success
                }
            ))
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to securely delete file {file_path}: {e}")
            return False

    def register_temporary_file(self, file_path: Union[str, Path]) -> None:
        """
        Register a temporary file for automatic cleanup
        
        Args:
            file_path: Path to temporary file
        """
        try:
            self.data_privacy_manager.register_temporary_file(file_path)
        except Exception as e:
            logger.error(f"Failed to register temporary file {file_path}: {e}")

    def get_sensitive_file_patterns(self) -> Dict[str, Any]:
        """
        Get sensitive file patterns for privacy protection
        
        Returns:
            Dict: Sensitive file patterns and information
        """
        try:
            patterns = self.data_privacy_manager.get_sensitive_file_patterns()
            return {
                name: {
                    "pattern": pattern.pattern,
                    "description": pattern.description,
                    "privacy_level": pattern.privacy_level.value,
                    "recommended_action": pattern.recommended_action
                }
                for name, pattern in patterns.items()
            }
        except Exception as e:
            logger.error(f"Failed to get sensitive file patterns: {e}")
            return {}

    def check_file_sensitivity(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Check if a file is potentially sensitive
        
        Args:
            file_path: Path to check
            
        Returns:
            Dict with sensitivity information if file is sensitive, None otherwise
        """
        try:
            sensitivity = self.data_privacy_manager.check_file_sensitivity(file_path)
            if sensitivity:
                return {
                    "pattern": sensitivity.pattern,
                    "description": sensitivity.description,
                    "privacy_level": sensitivity.privacy_level.value,
                    "recommended_action": sensitivity.recommended_action
                }
            return None
        except Exception as e:
            logger.error(f"Failed to check file sensitivity for {file_path}: {e}")
            return None

    def get_privacy_cleanup_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get privacy cleanup statistics
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dict: Cleanup statistics
        """
        try:
            return self.data_privacy_manager.get_cleanup_statistics(days)
        except Exception as e:
            logger.error(f"Failed to get cleanup statistics: {e}")
            return {}
