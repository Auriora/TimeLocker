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

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from ..security import SecurityService, SecurityEvent, SecurityLevel
from ..monitoring import StatusReporter, NotificationService, OperationStatus, StatusLevel
from ..config import ConfigurationModule

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Base exception for integration-related errors"""
    pass


class IntegrationService:
    """
    Integration service that coordinates all TimeLocker components
    Provides a unified interface for backup/restore operations with integrated
    security, monitoring, and notification features
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize integration service
        
        Args:
            config_dir: Directory for configuration and data
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory()

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize core components
        self.config_manager = ConfigurationModule(config_dir)
        self.status_reporter = StatusReporter(config_dir / "status")
        self.notification_service = NotificationService(config_dir / "notifications")

        # Security service will be initialized when credential manager is available
        self.security_service: Optional[SecurityService] = None

        # Setup integration
        self._setup_integration()

    def initialize_security(self, credential_manager):
        """
        Initialize security service with credential manager
        
        Args:
            credential_manager: Credential manager instance
        """
        self.security_service = SecurityService(
                credential_manager,
                self.config_dir / "security"
        )

        # Connect security events to notifications
        self.security_service.add_event_handler(self._handle_security_event)

        logger.info("Security service initialized")

    def _setup_integration(self):
        """Setup integration between components"""
        # Connect status updates to notifications
        self.status_reporter.add_status_handler(self._handle_status_update)

        # Load notification configuration from config manager
        notification_config = self.config_manager.get_section("notifications")
        if notification_config:
            self.notification_service.update_config(**notification_config)

    def _handle_status_update(self, status: OperationStatus):
        """Handle status updates from operations"""
        try:
            # Send notifications for completed operations
            if status.status in [StatusLevel.SUCCESS, StatusLevel.ERROR, StatusLevel.CRITICAL]:
                self.notification_service.send_notification(status)

            # Log security events for critical operations
            if self.security_service and status.status == StatusLevel.CRITICAL:
                self.security_service.log_security_event(SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="operation_critical_failure",
                        level=SecurityLevel.CRITICAL,
                        description=f"Critical failure in {status.operation_type}: {status.message}",
                        repository_id=status.repository_id,
                        metadata={"operation_id": status.operation_id}
                ))

        except Exception as e:
            logger.error(f"Error handling status update: {e}")

    def _handle_security_event(self, event: SecurityEvent):
        """Handle security events"""
        try:
            # Create status for critical security events
            if event.level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                status = OperationStatus(
                        operation_id=f"security_{uuid.uuid4().hex[:8]}",
                        operation_type="security",
                        status=StatusLevel.CRITICAL if event.level == SecurityLevel.CRITICAL else StatusLevel.WARNING,
                        message=f"Security Event: {event.description}",
                        timestamp=event.timestamp,
                        repository_id=event.repository_id,
                        metadata=event.metadata
                )

                # Send notification for security events
                self.notification_service.send_notification(status)

        except Exception as e:
            logger.error(f"Error handling security event: {e}")

    def execute_backup(self, repository, backup_target, operation_id: Optional[str] = None) -> OperationStatus:
        """
        Execute backup operation with full integration
        
        Args:
            repository: Repository to backup to
            backup_target: Backup target configuration
            operation_id: Optional operation ID
            
        Returns:
            OperationStatus: Final operation status
        """
        if operation_id is None:
            operation_id = f"backup_{uuid.uuid4().hex[:8]}"

        # Start operation tracking
        status = self.status_reporter.start_operation(
                operation_id=operation_id,
                operation_type="backup",
                repository_id=getattr(repository, 'id', str(repository._location)),
                metadata={
                        "start_time":   datetime.now().isoformat(),
                        "target_paths": getattr(backup_target, 'paths', [])
                }
        )

        try:
            # Security checks
            if self.security_service:
                # Verify repository encryption
                encryption_status = self.security_service.verify_repository_encryption(repository)
                if not encryption_status.is_encrypted:
                    self.security_service.log_security_event(SecurityEvent(
                            timestamp=datetime.now(),
                            event_type="unencrypted_backup_attempt",
                            level=SecurityLevel.HIGH,
                            description="Attempted backup to unencrypted repository",
                            repository_id=getattr(repository, 'id', str(repository._location))
                    ))

                # Log backup start
                self.security_service.log_security_event(SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="backup_started",
                        level=SecurityLevel.MEDIUM,
                        description=f"Backup operation started",
                        repository_id=getattr(repository, 'id', str(repository._location)),
                        metadata={"operation_id": operation_id}
                ))

            # Update status
            self.status_reporter.update_operation(
                    operation_id=operation_id,
                    status=StatusLevel.INFO,
                    message="Starting backup operation"
            )

            # Execute backup (this would integrate with existing backup logic)
            backup_result = self._execute_backup_operation(repository, backup_target, operation_id)

            # Determine final status
            if backup_result.get("success", False):
                final_status = StatusLevel.SUCCESS
                final_message = f"Backup completed successfully. {backup_result.get('files_new', 0)} files backed up."
            else:
                final_status = StatusLevel.ERROR
                final_message = f"Backup failed: {backup_result.get('error', 'Unknown error')}"

            # Complete operation
            final_operation_status = self.status_reporter.complete_operation(
                    operation_id=operation_id,
                    status=final_status,
                    message=final_message,
                    metadata=backup_result
            )

            # Security logging
            if self.security_service:
                self.security_service.log_security_event(SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="backup_completed",
                        level=SecurityLevel.MEDIUM if final_status == StatusLevel.SUCCESS else SecurityLevel.HIGH,
                        description=f"Backup operation completed with status: {final_status.value}",
                        repository_id=getattr(repository, 'id', str(repository._location)),
                        metadata={"operation_id": operation_id, "success": final_status == StatusLevel.SUCCESS}
                ))

            return final_operation_status

        except Exception as e:
            logger.error(f"Backup operation failed: {e}")

            # Complete operation with error
            final_operation_status = self.status_reporter.complete_operation(
                    operation_id=operation_id,
                    status=StatusLevel.CRITICAL,
                    message=f"Backup operation failed: {str(e)}",
                    metadata={"error": str(e)}
            )

            # Security logging
            if self.security_service:
                self.security_service.log_security_event(SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="backup_failed",
                        level=SecurityLevel.CRITICAL,
                        description=f"Backup operation failed with error: {str(e)}",
                        repository_id=getattr(repository, 'id', str(repository._location)),
                        metadata={"operation_id": operation_id, "error": str(e)}
                ))

            return final_operation_status

    def execute_restore(self, repository, snapshot_id: str, restore_options,
                        operation_id: Optional[str] = None) -> OperationStatus:
        """
        Execute restore operation with full integration
        
        Args:
            repository: Repository to restore from
            snapshot_id: Snapshot to restore
            restore_options: Restore configuration
            operation_id: Optional operation ID
            
        Returns:
            OperationStatus: Final operation status
        """
        if operation_id is None:
            operation_id = f"restore_{uuid.uuid4().hex[:8]}"

        # Start operation tracking
        status = self.status_reporter.start_operation(
                operation_id=operation_id,
                operation_type="restore",
                repository_id=getattr(repository, 'id', str(repository._location)),
                metadata={
                        "start_time":  datetime.now().isoformat(),
                        "snapshot_id": snapshot_id,
                        "target_path": str(getattr(restore_options, 'target_path', ''))
                }
        )

        try:
            # Security checks
            if self.security_service:
                # Verify repository integrity before restore
                integrity_valid = self.security_service.validate_backup_integrity(repository, snapshot_id)
                if not integrity_valid:
                    raise IntegrationError("Repository integrity validation failed")

                # Log restore start
                self.security_service.log_security_event(SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="restore_started",
                        level=SecurityLevel.MEDIUM,
                        description=f"Restore operation started for snapshot {snapshot_id}",
                        repository_id=getattr(repository, 'id', str(repository._location)),
                        metadata={"operation_id": operation_id, "snapshot_id": snapshot_id}
                ))

            # Update status
            self.status_reporter.update_operation(
                    operation_id=operation_id,
                    status=StatusLevel.INFO,
                    message=f"Starting restore of snapshot {snapshot_id}"
            )

            # Execute restore (this would integrate with existing restore logic)
            restore_result = self._execute_restore_operation(repository, snapshot_id, restore_options, operation_id)

            # Determine final status
            if restore_result.get("success", False):
                final_status = StatusLevel.SUCCESS
                final_message = f"Restore completed successfully. {restore_result.get('files_restored', 0)} files restored."
            else:
                final_status = StatusLevel.ERROR
                final_message = f"Restore failed: {restore_result.get('error', 'Unknown error')}"

            # Complete operation
            final_operation_status = self.status_reporter.complete_operation(
                    operation_id=operation_id,
                    status=final_status,
                    message=final_message,
                    metadata=restore_result
            )

            # Security logging
            if self.security_service:
                self.security_service.log_security_event(SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="restore_completed",
                        level=SecurityLevel.MEDIUM if final_status == StatusLevel.SUCCESS else SecurityLevel.HIGH,
                        description=f"Restore operation completed with status: {final_status.value}",
                        repository_id=getattr(repository, 'id', str(repository._location)),
                        metadata={"operation_id": operation_id, "snapshot_id": snapshot_id, "success": final_status == StatusLevel.SUCCESS}
                ))

            return final_operation_status

        except Exception as e:
            logger.error(f"Restore operation failed: {e}")

            # Complete operation with error
            final_operation_status = self.status_reporter.complete_operation(
                    operation_id=operation_id,
                    status=StatusLevel.CRITICAL,
                    message=f"Restore operation failed: {str(e)}",
                    metadata={"error": str(e)}
            )

            # Security logging
            if self.security_service:
                self.security_service.log_security_event(SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="restore_failed",
                        level=SecurityLevel.CRITICAL,
                        description=f"Restore operation failed with error: {str(e)}",
                        repository_id=getattr(repository, 'id', str(repository._location)),
                        metadata={"operation_id": operation_id, "snapshot_id": snapshot_id, "error": str(e)}
                ))

            return final_operation_status

    def _execute_backup_operation(self, repository, backup_target, operation_id: str) -> Dict[str, Any]:
        """Execute the actual backup operation (placeholder for integration with existing backup logic)"""
        # This would integrate with the existing backup manager and repository classes
        # For now, return a mock result
        return {
                "success":          True,
                "files_new":        150,
                "files_changed":    25,
                "files_unmodified": 1000,
                "data_added":       1024 * 1024 * 100  # 100MB
        }

    def _execute_restore_operation(self, repository, snapshot_id: str, restore_options, operation_id: str) -> Dict[str, Any]:
        """Execute the actual restore operation (placeholder for integration with existing restore logic)"""
        # This would integrate with the existing restore manager and repository classes
        # For now, return a mock result
        return {
                "success":        True,
                "files_restored": 175,
                "bytes_restored": 1024 * 1024 * 95  # 95MB
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
                "timestamp":             datetime.now().isoformat(),
                "components":            {
                        "configuration":    "active",
                        "status_reporting": "active",
                        "notifications":    "active",
                        "security":         "active" if self.security_service else "inactive"
                },
                "current_operations":    len(self.status_reporter.get_current_operations()),
                "configuration_summary": self.config_manager.get_config_summary()
        }

        # Add security summary if available
        if self.security_service:
            status["security_summary"] = self.security_service.get_security_summary()

        # Add status summary
        status["status_summary"] = self.status_reporter.get_status_summary()

        return status
