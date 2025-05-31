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
                f.write("# Format: timestamp|event_type|level|description|metadata\n")

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
