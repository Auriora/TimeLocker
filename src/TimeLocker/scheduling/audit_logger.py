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

Scheduling Audit Logger

This module provides comprehensive audit logging for scheduling operations,
ensuring all scheduling activities are tracked for compliance and troubleshooting.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events for scheduling operations."""
    SCHEDULE_CREATED = "schedule_created"
    SCHEDULE_UPDATED = "schedule_updated"
    SCHEDULE_DELETED = "schedule_deleted"
    SCHEDULE_ENABLED = "schedule_enabled"
    SCHEDULE_DISABLED = "schedule_disabled"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_TIMEOUT = "execution_timeout"
    VALIDATION_FAILED = "validation_failed"
    PLATFORM_ERROR = "platform_error"


@dataclass
class AuditEntry:
    """Represents a single audit log entry."""
    timestamp: datetime
    event_type: AuditEventType
    schedule_id: Optional[str]
    execution_id: Optional[str]
    user: Optional[str]
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'schedule_id': self.schedule_id,
            'execution_id': self.execution_id,
            'user': self.user,
            'details': self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEntry':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['event_type'] = AuditEventType(data['event_type'])
        return cls(**data)


class SchedulingAuditLogger:
    """
    Comprehensive audit logging for scheduling operations.
    
    Responsibilities:
    - Log all scheduling CRUD operations
    - Log execution events and outcomes
    - Maintain audit trail with retention
    - Provide audit query capabilities
    - Ensure compliance with audit requirements
    """
    
    # Default audit log retention period (365 days)
    DEFAULT_RETENTION_DAYS = 365
    
    # Maximum audit log file size (50MB)
    MAX_LOG_SIZE = 50 * 1024 * 1024
    
    def __init__(self, config_dir: Path, retention_days: int = DEFAULT_RETENTION_DAYS):
        """
        Initialize scheduling audit logger.
        
        Args:
            config_dir: Directory for audit logs
            retention_days: Number of days to retain audit logs
        """
        self.audit_dir = config_dir / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        self.audit_log = self.audit_dir / "scheduling_audit.log"
        self.retention_days = retention_days
        
        self.logger = logging.getLogger(f"{__name__}.SchedulingAuditLogger")
        
        # Perform initial cleanup
        self._cleanup_old_logs()
    
    def log_schedule_creation(
        self,
        schedule_id: str,
        schedule_config: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> None:
        """
        Log schedule creation event.
        
        Args:
            schedule_id: Schedule identifier
            schedule_config: Schedule configuration
            created_by: User who created the schedule
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SCHEDULE_CREATED,
            schedule_id=schedule_id,
            execution_id=None,
            user=created_by,
            details={
                'name': schedule_config.get('name'),
                'policy_id': schedule_config.get('policy_id'),
                'schedule_pattern': schedule_config.get('schedule_pattern'),
                'enabled': schedule_config.get('enabled', True)
            }
        )
        
        self._write_audit_entry(entry)
        self.logger.info(f"Audit: Schedule created - {schedule_id}")
    
    def log_schedule_update(
        self,
        schedule_id: str,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> None:
        """
        Log schedule update event.
        
        Args:
            schedule_id: Schedule identifier
            updates: Updates applied
            updated_by: User who updated the schedule
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SCHEDULE_UPDATED,
            schedule_id=schedule_id,
            execution_id=None,
            user=updated_by,
            details={'updates': updates}
        )
        
        self._write_audit_entry(entry)
        self.logger.info(f"Audit: Schedule updated - {schedule_id}")
    
    def log_schedule_deletion(
        self,
        schedule_id: str,
        deleted_by: Optional[str] = None
    ) -> None:
        """
        Log schedule deletion event.
        
        Args:
            schedule_id: Schedule identifier
            deleted_by: User who deleted the schedule
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SCHEDULE_DELETED,
            schedule_id=schedule_id,
            execution_id=None,
            user=deleted_by,
            details={}
        )
        
        self._write_audit_entry(entry)
        self.logger.info(f"Audit: Schedule deleted - {schedule_id}")
    
    def log_schedule_status_change(
        self,
        schedule_id: str,
        enabled: bool,
        changed_by: Optional[str] = None
    ) -> None:
        """
        Log schedule enable/disable event.
        
        Args:
            schedule_id: Schedule identifier
            enabled: New enabled status
            changed_by: User who changed the status
        """
        event_type = AuditEventType.SCHEDULE_ENABLED if enabled else AuditEventType.SCHEDULE_DISABLED
        
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            schedule_id=schedule_id,
            execution_id=None,
            user=changed_by,
            details={'enabled': enabled}
        )
        
        self._write_audit_entry(entry)
        self.logger.info(f"Audit: Schedule {'enabled' if enabled else 'disabled'} - {schedule_id}")
    
    def log_execution_start(
        self,
        schedule_id: str,
        execution_id: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Log backup execution start event.
        
        Args:
            schedule_id: Schedule identifier
            execution_id: Execution identifier
            context: Execution context
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.EXECUTION_STARTED,
            schedule_id=schedule_id,
            execution_id=execution_id,
            user=context.get('user_context'),
            details={
                'triggered_by': context.get('triggered_by'),
                'platform': context.get('platform')
            }
        )
        
        self._write_audit_entry(entry)
        self.logger.info(f"Audit: Execution started - {execution_id} for schedule {schedule_id}")
    
    def log_execution_complete(self, execution_result: Dict[str, Any]) -> None:
        """
        Log backup execution completion event.
        
        Args:
            execution_result: Execution result details
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.EXECUTION_COMPLETED,
            schedule_id=execution_result.get('schedule_id'),
            execution_id=execution_result.get('execution_id'),
            user=None,
            details={
                'status': execution_result.get('status'),
                'execution_time_seconds': execution_result.get('execution_time', {}).get('total_seconds', 0),
                'files_processed': execution_result.get('backup_result', {}).get('files_processed', 0),
                'bytes_transferred': execution_result.get('backup_result', {}).get('bytes_transferred', 0)
            }
        )
        
        self._write_audit_entry(entry)
        self.logger.info(
            f"Audit: Execution completed - {execution_result.get('execution_id')} "
            f"with status {execution_result.get('status')}"
        )
    
    def log_execution_error(
        self,
        execution_result: Dict[str, Any],
        error: Exception
    ) -> None:
        """
        Log backup execution error event.
        
        Args:
            execution_result: Execution result details
            error: Exception that occurred
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.EXECUTION_FAILED,
            schedule_id=execution_result.get('schedule_id'),
            execution_id=execution_result.get('execution_id'),
            user=None,
            details={
                'error_type': type(error).__name__,
                'error_message': str(error),
                'execution_time_seconds': execution_result.get('execution_time', {}).get('total_seconds', 0)
            }
        )
        
        self._write_audit_entry(entry)
        self.logger.error(
            f"Audit: Execution failed - {execution_result.get('execution_id')}: {str(error)}"
        )
    
    def log_validation_failure(
        self,
        schedule_id: str,
        validation_errors: List[str]
    ) -> None:
        """
        Log schedule validation failure event.
        
        Args:
            schedule_id: Schedule identifier
            validation_errors: List of validation errors
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.VALIDATION_FAILED,
            schedule_id=schedule_id,
            execution_id=None,
            user=None,
            details={'validation_errors': validation_errors}
        )
        
        self._write_audit_entry(entry)
        self.logger.warning(f"Audit: Validation failed - {schedule_id}")
    
    def log_platform_error(
        self,
        schedule_id: str,
        platform: str,
        error: Exception
    ) -> None:
        """
        Log platform scheduler error event.
        
        Args:
            schedule_id: Schedule identifier
            platform: Platform name
            error: Exception that occurred
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.PLATFORM_ERROR,
            schedule_id=schedule_id,
            execution_id=None,
            user=None,
            details={
                'platform': platform,
                'error_type': type(error).__name__,
                'error_message': str(error)
            }
        )
        
        self._write_audit_entry(entry)
        self.logger.error(f"Audit: Platform error - {schedule_id} on {platform}: {str(error)}")
    
    def get_audit_trail(
        self,
        schedule_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """
        Query audit trail with filters.
        
        Args:
            schedule_id: Optional filter by schedule ID
            event_type: Optional filter by event type
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries matching filters
        """
        entries = []
        
        if not self.audit_log.exists():
            return entries
        
        try:
            with open(self.audit_log, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        entry = AuditEntry.from_dict(data)
                        
                        # Apply filters
                        if schedule_id and entry.schedule_id != schedule_id:
                            continue
                        if event_type and entry.event_type != event_type:
                            continue
                        if start_date and entry.timestamp < start_date:
                            continue
                        if end_date and entry.timestamp > end_date:
                            continue
                        
                        entries.append(entry)
                        
                        if len(entries) >= limit:
                            break
                            
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        self.logger.warning(f"Failed to parse audit entry: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Failed to read audit trail: {e}")
        
        return sorted(entries, key=lambda x: x.timestamp, reverse=True)
    
    def _write_audit_entry(self, entry: AuditEntry) -> None:
        """
        Write audit entry to log file.
        
        Args:
            entry: Audit entry to write
        """
        try:
            # Check if rotation is needed
            if self.audit_log.exists() and self.audit_log.stat().st_size > self.MAX_LOG_SIZE:
                self._rotate_audit_log()
            
            # Write entry
            with open(self.audit_log, 'a') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to write audit entry: {e}")
    
    def _rotate_audit_log(self) -> None:
        """Rotate audit log file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_file = self.audit_dir / f"scheduling_audit_{timestamp}.log"
            
            self.audit_log.rename(rotated_file)
            self.logger.info(f"Rotated audit log to {rotated_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to rotate audit log: {e}")
    
    def _cleanup_old_logs(self) -> None:
        """Clean up audit logs older than retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for log_file in self.audit_dir.glob("scheduling_audit_*.log"):
                try:
                    # Extract timestamp from filename
                    timestamp_str = log_file.stem.replace("scheduling_audit_", "")
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if file_date < cutoff_date:
                        log_file.unlink()
                        self.logger.info(f"Deleted old audit log: {log_file}")
                        
                except (ValueError, OSError) as e:
                    self.logger.warning(f"Failed to process audit log {log_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old audit logs: {e}")
