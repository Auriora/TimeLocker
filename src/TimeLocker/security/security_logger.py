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

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SecurityLogLevel(Enum):
    """Security log levels for filtering and display"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Types of security events that can be logged"""
    AUTHENTICATION = "authentication"
    CREDENTIAL_ACCESS = "credential_access"
    REPOSITORY_ACCESS = "repository_access"
    BACKUP_OPERATION = "backup_operation"
    RESTORE_OPERATION = "restore_operation"
    INTEGRITY_CHECK = "integrity_check"
    ENCRYPTION_VERIFICATION = "encryption_verification"
    EMERGENCY_LOCKDOWN = "emergency_lockdown"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_EVENT = "system_event"


@dataclass
class SecurityLogEntry:
    """Represents a security log entry with user-friendly formatting"""
    timestamp: datetime
    event_type: SecurityEventType
    level: SecurityLogLevel
    description: str
    user_id: Optional[str] = None
    repository_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    source: Optional[str] = None  # Which component logged this event

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "level": self.level.value,
            "description": self.description,
            "user_id": self.user_id,
            "repository_id": self.repository_id,
            "metadata": self.metadata,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityLogEntry':
        """Create log entry from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=SecurityEventType(data["event_type"]),
            level=SecurityLogLevel(data["level"]),
            description=data["description"],
            user_id=data.get("user_id"),
            repository_id=data.get("repository_id"),
            metadata=data.get("metadata"),
            source=data.get("source")
        )


@dataclass
class EventFilter:
    """Filter criteria for security log queries"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_types: Optional[List[SecurityEventType]] = None
    levels: Optional[List[SecurityLogLevel]] = None
    repository_id: Optional[str] = None
    user_id: Optional[str] = None
    limit: Optional[int] = None


class SecurityNotification:
    """Represents a user notification for security events"""
    
    def __init__(self, title: str, message: str, level: SecurityLogLevel, 
                 suggested_actions: Optional[List[str]] = None):
        self.title = title
        self.message = message
        self.level = level
        self.suggested_actions = suggested_actions or []
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary"""
        return {
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "suggested_actions": self.suggested_actions,
            "timestamp": self.timestamp.isoformat()
        }


class SecurityLogger:
    """
    Enhanced security logger with user-friendly interface for TimeLocker.
    
    Provides simple log viewing, filtering capabilities, log retention management,
    and user notification system for security events. Integrates with existing
    audit logging in SecurityService and CredentialManager.
    """

    def __init__(self, config_dir: Optional[Path] = None, retention_days: int = 30):
        """
        Initialize security logger
        
        Args:
            config_dir: Directory for security logs and configuration
            retention_days: Number of days to retain logs (default: 30)
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            base_config_dir = ConfigurationPathResolver.get_config_directory()
            config_dir = base_config_dir / "security"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Log files
        self.security_log_file = self.config_dir / "security_events.jsonl"
        self.notification_log_file = self.config_dir / "notifications.jsonl"
        
        # Configuration
        self.retention_days = retention_days
        
        # Notification handlers
        self._notification_handlers: List[Callable[[SecurityNotification], None]] = []
        
        # Initialize log files
        self._initialize_log_files()

    def _initialize_log_files(self):
        """Initialize log files with proper headers"""
        if not self.security_log_file.exists():
            self.security_log_file.touch()
            logger.info(f"Initialized security log file: {self.security_log_file}")
            
        if not self.notification_log_file.exists():
            self.notification_log_file.touch()
            logger.info(f"Initialized notification log file: {self.notification_log_file}")

    def add_notification_handler(self, handler: Callable[[SecurityNotification], None]):
        """
        Add a notification handler for security events
        
        Args:
            handler: Function to call when notifications are generated
        """
        self._notification_handlers.append(handler)

    def remove_notification_handler(self, handler: Callable[[SecurityNotification], None]):
        """Remove a notification handler"""
        if handler in self._notification_handlers:
            self._notification_handlers.remove(handler)

    def log_event(self, event: SecurityLogEntry):
        """
        Log a security event with user-friendly formatting
        
        Args:
            event: Security event to log
        """
        try:
            # Write to security log file in JSON Lines format
            with open(self.security_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event.to_dict()) + '\n')
            
            # Check if this event should generate a notification
            self._check_for_notification(event)
            
            logger.debug(f"Security event logged: {event.event_type.value} - {event.description}")
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    def _check_for_notification(self, event: SecurityLogEntry):
        """
        Check if a security event should generate a user notification
        
        Args:
            event: Security event to check
        """
        notification = None
        
        # Generate notifications for critical and high-level events
        if event.level == SecurityLogLevel.CRITICAL:
            if event.event_type == SecurityEventType.EMERGENCY_LOCKDOWN:
                notification = SecurityNotification(
                    title="Emergency Lockdown Activated",
                    message=f"TimeLocker has initiated an emergency lockdown: {event.description}",
                    level=event.level,
                    suggested_actions=[
                        "Check system security",
                        "Review recent activities",
                        "Contact administrator if needed"
                    ]
                )
            elif event.event_type == SecurityEventType.INTEGRITY_CHECK:
                notification = SecurityNotification(
                    title="Backup Integrity Issue Detected",
                    message=f"Critical integrity check failure: {event.description}",
                    level=event.level,
                    suggested_actions=[
                        "Run full repository check",
                        "Verify backup data",
                        "Check storage system health"
                    ]
                )
        
        elif event.level == SecurityLogLevel.HIGH:
            if event.event_type == SecurityEventType.AUTHENTICATION:
                if "failed" in event.description.lower():
                    notification = SecurityNotification(
                        title="Authentication Failure",
                        message=f"Authentication attempt failed: {event.description}",
                        level=event.level,
                        suggested_actions=[
                            "Verify credentials",
                            "Check for unauthorized access attempts",
                            "Consider changing passwords"
                        ]
                    )
            elif event.event_type == SecurityEventType.RESTORE_OPERATION:
                if "failed" in event.description.lower():
                    notification = SecurityNotification(
                        title="Restore Operation Failed",
                        message=f"Restore operation encountered issues: {event.description}",
                        level=event.level,
                        suggested_actions=[
                            "Check repository integrity",
                            "Verify restore permissions",
                            "Review error logs"
                        ]
                    )
        
        if notification:
            self._send_notification(notification)

    def _send_notification(self, notification: SecurityNotification):
        """
        Send a security notification to registered handlers
        
        Args:
            notification: Notification to send
        """
        try:
            # Log the notification
            with open(self.notification_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(notification.to_dict()) + '\n')
            
            # Send to notification handlers
            for handler in self._notification_handlers:
                try:
                    handler(notification)
                except Exception as e:
                    logger.error(f"Error in notification handler: {e}")
            
            logger.info(f"Security notification sent: {notification.title}")
            
        except Exception as e:
            logger.error(f"Failed to send security notification: {e}")

    def get_events(self, filter_criteria: Optional[EventFilter] = None) -> List[SecurityLogEntry]:
        """
        Get security events with optional filtering
        
        Args:
            filter_criteria: Filter criteria for events
            
        Returns:
            List of security log entries matching the filter
        """
        events = []
        
        if not self.security_log_file.exists():
            return events
        
        try:
            with open(self.security_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event_data = json.loads(line)
                        event = SecurityLogEntry.from_dict(event_data)
                        
                        # Apply filters
                        if self._matches_filter(event, filter_criteria):
                            events.append(event)
                            
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        logger.warning(f"Failed to parse log entry: {e}")
                        continue
            
            # Sort by timestamp (newest first)
            events.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit if specified
            if filter_criteria and filter_criteria.limit:
                events = events[:filter_criteria.limit]
            
        except Exception as e:
            logger.error(f"Failed to read security events: {e}")
        
        return events

    def _matches_filter(self, event: SecurityLogEntry, filter_criteria: Optional[EventFilter]) -> bool:
        """
        Check if an event matches the filter criteria
        
        Args:
            event: Event to check
            filter_criteria: Filter criteria to apply
            
        Returns:
            True if event matches filter, False otherwise
        """
        if not filter_criteria:
            return True
        
        # Date range filter
        if filter_criteria.start_date and event.timestamp < filter_criteria.start_date:
            return False
        if filter_criteria.end_date and event.timestamp > filter_criteria.end_date:
            return False
        
        # Event type filter
        if filter_criteria.event_types and event.event_type not in filter_criteria.event_types:
            return False
        
        # Level filter
        if filter_criteria.levels and event.level not in filter_criteria.levels:
            return False
        
        # Repository filter
        if filter_criteria.repository_id and event.repository_id != filter_criteria.repository_id:
            return False
        
        # User filter
        if filter_criteria.user_id and event.user_id != filter_criteria.user_id:
            return False
        
        return True

    def get_notifications(self, hours: int = 24) -> List[SecurityNotification]:
        """
        Get recent security notifications
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List of recent notifications
        """
        notifications = []
        
        if not self.notification_log_file.exists():
            return notifications
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(self.notification_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        notification_data = json.loads(line)
                        timestamp = datetime.fromisoformat(notification_data["timestamp"])
                        
                        if timestamp >= cutoff_time:
                            notification = SecurityNotification(
                                title=notification_data["title"],
                                message=notification_data["message"],
                                level=SecurityLogLevel(notification_data["level"]),
                                suggested_actions=notification_data.get("suggested_actions", [])
                            )
                            notification.timestamp = timestamp
                            notifications.append(notification)
                            
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        logger.warning(f"Failed to parse notification entry: {e}")
                        continue
            
            # Sort by timestamp (newest first)
            notifications.sort(key=lambda x: x.timestamp, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to read notifications: {e}")
        
        return notifications

    def cleanup_old_logs(self):
        """
        Clean up old log entries based on retention policy
        
        Removes entries older than retention_days from both security events
        and notifications logs.
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        # Clean up security events
        self._cleanup_log_file(self.security_log_file, cutoff_date, "security events")
        
        # Clean up notifications
        self._cleanup_log_file(self.notification_log_file, cutoff_date, "notifications")

    def _cleanup_log_file(self, log_file: Path, cutoff_date: datetime, log_type: str):
        """
        Clean up a specific log file
        
        Args:
            log_file: Path to log file to clean up
            cutoff_date: Date before which entries should be removed
            log_type: Type of log for logging purposes
        """
        if not log_file.exists():
            return
        
        try:
            temp_file = log_file.with_suffix('.tmp')
            entries_kept = 0
            entries_removed = 0
            
            with open(log_file, 'r', encoding='utf-8') as infile, \
                 open(temp_file, 'w', encoding='utf-8') as outfile:
                
                for line in infile:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        timestamp = datetime.fromisoformat(data["timestamp"])
                        
                        if timestamp >= cutoff_date:
                            outfile.write(line + '\n')
                            entries_kept += 1
                        else:
                            entries_removed += 1
                            
                    except (json.JSONDecodeError, ValueError, KeyError):
                        # Keep malformed entries to avoid data loss
                        outfile.write(line + '\n')
                        entries_kept += 1
            
            # Replace original file with cleaned version
            temp_file.replace(log_file)
            
            logger.info(f"Cleaned up {log_type}: kept {entries_kept}, removed {entries_removed} entries")
            
        except Exception as e:
            logger.error(f"Failed to cleanup {log_type}: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()

    def export_logs(self, output_path: Path, filter_criteria: Optional[EventFilter] = None, 
                   format_type: str = "json") -> bool:
        """
        Export security logs to a file
        
        Args:
            output_path: Path to export file
            filter_criteria: Optional filter criteria
            format_type: Export format ("json" or "csv")
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            events = self.get_events(filter_criteria)
            
            if format_type.lower() == "csv":
                return self._export_to_csv(events, output_path)
            else:
                return self._export_to_json(events, output_path)
                
        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return False

    def _export_to_json(self, events: List[SecurityLogEntry], output_path: Path) -> bool:
        """Export events to JSON format"""
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_events": len(events),
                "events": [event.to_dict() for event in events]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(events)} events to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return False

    def _export_to_csv(self, events: List[SecurityLogEntry], output_path: Path) -> bool:
        """Export events to CSV format"""
        try:
            import csv
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    "Timestamp", "Event Type", "Level", "Description", 
                    "User ID", "Repository ID", "Source", "Metadata"
                ])
                
                # Write events
                for event in events:
                    writer.writerow([
                        event.timestamp.isoformat(),
                        event.event_type.value,
                        event.level.value,
                        event.description,
                        event.user_id or "",
                        event.repository_id or "",
                        event.source or "",
                        json.dumps(event.metadata) if event.metadata else ""
                    ])
            
            logger.info(f"Exported {len(events)} events to CSV: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False

    def get_security_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get a summary of security events for the specified period
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dictionary containing security summary with user-friendly information
        """
        try:
            filter_criteria = EventFilter(
                start_date=datetime.now() - timedelta(days=days),
                limit=None
            )
            
            events = self.get_events(filter_criteria)
            
            # Count events by type and level
            events_by_type = {}
            events_by_level = {}
            
            for event in events:
                event_type = event.event_type.value
                event_level = event.level.value
                
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                events_by_level[event_level] = events_by_level.get(event_level, 0) + 1
            
            # Get recent notifications
            notifications = self.get_notifications(hours=days * 24)
            
            return {
                "period_days": days,
                "total_events": len(events),
                "events_by_type": events_by_type,
                "events_by_level": events_by_level,
                "recent_notifications": len(notifications),
                "critical_events": events_by_level.get("critical", 0),
                "high_events": events_by_level.get("high", 0),
                "generated_at": datetime.now().isoformat(),
                "retention_days": self.retention_days
            }
            
        except Exception as e:
            logger.error(f"Failed to generate security summary: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }

    def integrate_with_existing_logs(self):
        """
        Integrate with existing audit logs from SecurityService and CredentialManager
        
        This method reads existing audit logs and converts them to the new format
        for unified log viewing and management.
        """
        try:
            # Import existing SecurityService logs
            security_service_log = self.config_dir / "audit.log"
            if security_service_log.exists():
                self._import_security_service_logs(security_service_log)
            
            # Import existing CredentialManager logs
            credential_audit_log = self.config_dir / "credential_audit.log"
            if credential_audit_log.exists():
                self._import_credential_manager_logs(credential_audit_log)
            
            logger.info("Successfully integrated with existing audit logs")
            
        except Exception as e:
            logger.error(f"Failed to integrate with existing logs: {e}")

    def _import_security_service_logs(self, log_file: Path):
        """Import logs from SecurityService audit.log format"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    
                    # Parse SecurityService log format: timestamp|event_type|level|description|user_id|repository_id|metadata
                    parts = line.split('|')
                    if len(parts) >= 4:
                        try:
                            timestamp = datetime.fromisoformat(parts[0])
                            event_type_str = parts[1]
                            level_str = parts[2]
                            description = parts[3]
                            user_id = parts[4] if len(parts) > 4 and parts[4] else None
                            repository_id = parts[5] if len(parts) > 5 and parts[5] else None
                            metadata_str = parts[6] if len(parts) > 6 and parts[6] else None
                            
                            # Convert to new format
                            event_type = self._map_event_type(event_type_str)
                            level = self._map_security_level(level_str)
                            
                            metadata = None
                            if metadata_str and metadata_str != "{}":
                                try:
                                    metadata = json.loads(metadata_str.replace("'", '"'))
                                except json.JSONDecodeError:
                                    metadata = {"raw_metadata": metadata_str}
                            
                            event = SecurityLogEntry(
                                timestamp=timestamp,
                                event_type=event_type,
                                level=level,
                                description=description,
                                user_id=user_id,
                                repository_id=repository_id,
                                metadata=metadata,
                                source="SecurityService"
                            )
                            
                            # Only log if not already in new format
                            if not self._event_already_logged(event):
                                self.log_event(event)
                            
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to parse SecurityService log entry: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Failed to import SecurityService logs: {e}")

    def _import_credential_manager_logs(self, log_file: Path):
        """Import logs from CredentialManager audit log format"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    
                    # Parse CredentialManager log format: timestamp|operation|credential_id|success|details
                    parts = line.split('|')
                    if len(parts) >= 4:
                        try:
                            timestamp = datetime.fromisoformat(parts[0])
                            operation = parts[1]
                            credential_id = parts[2]
                            success = parts[3] == "True"
                            details = parts[4] if len(parts) > 4 else ""
                            
                            # Convert to new format
                            description = f"Credential {operation}: {'SUCCESS' if success else 'FAILED'}"
                            if details:
                                description += f" - {details}"
                            
                            level = SecurityLogLevel.MEDIUM if success else SecurityLogLevel.HIGH
                            
                            event = SecurityLogEntry(
                                timestamp=timestamp,
                                event_type=SecurityEventType.CREDENTIAL_ACCESS,
                                level=level,
                                description=description,
                                repository_id=credential_id if credential_id else None,
                                metadata={
                                    "operation": operation,
                                    "success": success,
                                    "details": details
                                },
                                source="CredentialManager"
                            )
                            
                            # Only log if not already in new format
                            if not self._event_already_logged(event):
                                self.log_event(event)
                            
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to parse CredentialManager log entry: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Failed to import CredentialManager logs: {e}")

    def _map_event_type(self, event_type_str: str) -> SecurityEventType:
        """Map string event type to SecurityEventType enum"""
        mapping = {
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
        
        return mapping.get(event_type_str, SecurityEventType.SYSTEM_EVENT)

    def _map_security_level(self, level_str: str) -> SecurityLogLevel:
        """Map string security level to SecurityLogLevel enum"""
        mapping = {
            "low": SecurityLogLevel.LOW,
            "medium": SecurityLogLevel.MEDIUM,
            "high": SecurityLogLevel.HIGH,
            "critical": SecurityLogLevel.CRITICAL
        }
        
        return mapping.get(level_str.lower(), SecurityLogLevel.MEDIUM)

    def _event_already_logged(self, event: SecurityLogEntry) -> bool:
        """
        Check if an event is already logged to avoid duplicates during import
        
        Args:
            event: Event to check
            
        Returns:
            True if event already exists, False otherwise
        """
        # Simple check based on timestamp and description
        # This is a basic implementation to avoid obvious duplicates
        recent_events = self.get_events(EventFilter(
            start_date=event.timestamp - timedelta(seconds=1),
            end_date=event.timestamp + timedelta(seconds=1),
            limit=10
        ))
        
        for existing_event in recent_events:
            if (existing_event.timestamp == event.timestamp and 
                existing_event.description == event.description and
                existing_event.event_type == event.event_type):
                return True
        
        return False