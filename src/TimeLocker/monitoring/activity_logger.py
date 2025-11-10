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
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from .status_reporter import OperationStatus, StatusLevel

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels for activity logging"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """Represents a single log entry"""
    timestamp: datetime
    level: LogLevel
    operation_type: str
    operation_id: Optional[str]
    repository_id: Optional[str]
    message: str
    details: Dict[str, Any]
    error_context: Optional[Dict[str, Any]] = None
    troubleshooting_suggestions: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'operation_type': self.operation_type,
            'operation_id': self.operation_id,
            'repository_id': self.repository_id,
            'message': self.message,
            'details': self.details
        }
        if self.error_context:
            result['error_context'] = self.error_context
        if self.troubleshooting_suggestions:
            result['troubleshooting_suggestions'] = self.troubleshooting_suggestions
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['level'] = LogLevel(data['level'])
        return cls(**data)

    def format_user_friendly(self) -> str:
        """Format log entry in a user-friendly way"""
        level_symbols = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.CRITICAL: "🚨"
        }
        
        symbol = level_symbols.get(self.level, "•")
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        lines = [f"{symbol} [{timestamp_str}] {self.level.value.upper()}: {self.message}"]
        
        if self.repository_id:
            lines.append(f"   Repository: {self.repository_id}")
        
        if self.operation_id:
            lines.append(f"   Operation: {self.operation_id}")
        
        if self.details:
            for key, value in self.details.items():
                if key not in ['start_time', 'end_time']:  # Skip internal timestamps
                    lines.append(f"   {key}: {value}")
        
        if self.error_context:
            lines.append("   Error Context:")
            for key, value in self.error_context.items():
                lines.append(f"     {key}: {value}")
        
        if self.troubleshooting_suggestions:
            lines.append("   Troubleshooting Suggestions:")
            for i, suggestion in enumerate(self.troubleshooting_suggestions, 1):
                lines.append(f"     {i}. {suggestion}")
        
        return "\n".join(lines)


class ActivityLogger:
    """
    Manages activity logging with user-friendly formatting and automatic log management.
    
    Responsibilities:
    - Structured logging with readable format
    - Automatic log rotation and cleanup
    - Configurable log levels
    - Error context and troubleshooting information
    - User-friendly log descriptions
    """

    # Maximum log file size (10MB)
    MAX_LOG_SIZE = 10 * 1024 * 1024
    
    # Maximum number of log files to keep
    MAX_LOG_FILES = 5

    def __init__(self, config_dir: Path):
        """
        Initialize activity logger.
        
        Args:
            config_dir: Directory for log files and configuration
        """
        self.log_dir = config_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_log = self.log_dir / "timelocker.log"
        self.user_friendly_log = self.log_dir / "timelocker_readable.log"
        
        self.log_level = LogLevel.INFO
        
        # Load configuration
        self._load_config()
        
        # Perform initial log rotation check
        self._check_and_rotate_logs()

    def set_log_level(self, level: LogLevel) -> None:
        """
        Set logging level.
        
        Args:
            level: New log level
        """
        self.log_level = level
        self._save_config()
        logger.info(f"Activity log level set to {level.value}")

    def log_backup_event(self, event: OperationStatus) -> None:
        """
        Log backup-related events with appropriate detail level.
        
        Args:
            event: Backup operation status to log
        """
        # Determine log level from status
        level_map = {
            StatusLevel.INFO: LogLevel.INFO,
            StatusLevel.SUCCESS: LogLevel.INFO,
            StatusLevel.WARNING: LogLevel.WARNING,
            StatusLevel.ERROR: LogLevel.ERROR,
            StatusLevel.CRITICAL: LogLevel.CRITICAL
        }
        
        level = level_map.get(event.status, LogLevel.INFO)
        
        # Build details
        details = {}
        if event.progress_percentage is not None:
            details['progress'] = f"{event.progress_percentage}%"
        if event.files_processed is not None and event.total_files is not None:
            details['files'] = f"{event.files_processed}/{event.total_files}"
        if event.bytes_processed is not None:
            size_mb = event.bytes_processed / (1024 * 1024)
            details['data_processed'] = f"{size_mb:.2f} MB"
        if event.metadata:
            details.update(event.metadata)
        
        # Add troubleshooting for errors
        troubleshooting = None
        error_context = None
        
        if event.status in [StatusLevel.ERROR, StatusLevel.CRITICAL]:
            troubleshooting = self._get_troubleshooting_suggestions(event)
            error_context = self._extract_error_context(event)
        
        # Create log entry
        entry = LogEntry(
            timestamp=event.timestamp,
            level=level,
            operation_type=event.operation_type,
            operation_id=event.operation_id,
            repository_id=event.repository_id,
            message=event.message,
            details=details,
            error_context=error_context,
            troubleshooting_suggestions=troubleshooting
        )
        
        self._write_log_entry(entry)

    def log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """
        Log errors with context and troubleshooting suggestions.
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
        """
        error_context = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            **context
        }
        
        troubleshooting = self._get_error_troubleshooting(error, context)
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            operation_type=context.get('operation_type', 'unknown'),
            operation_id=context.get('operation_id'),
            repository_id=context.get('repository_id'),
            message=f"Error occurred: {str(error)}",
            details=context,
            error_context=error_context,
            troubleshooting_suggestions=troubleshooting
        )
        
        self._write_log_entry(entry)

    def get_recent_logs(self, hours: int = 24, level: Optional[LogLevel] = None) -> List[LogEntry]:
        """
        Get recent log entries for troubleshooting.
        
        Args:
            hours: Number of hours to look back
            level: Optional filter by log level
            
        Returns:
            List of log entries
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        entries = []
        
        if not self.current_log.exists():
            return entries
        
        try:
            with open(self.current_log, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        entry = LogEntry.from_dict(data)
                        
                        # Apply filters
                        if entry.timestamp < cutoff_time:
                            continue
                        if level and entry.level != level:
                            continue
                        
                        entries.append(entry)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        except Exception as e:
            logger.error(f"Failed to read log entries: {e}")
        
        return sorted(entries, key=lambda x: x.timestamp, reverse=True)

    def _write_log_entry(self, entry: LogEntry) -> None:
        """
        Write log entry to files.
        
        Args:
            entry: Log entry to write
        """
        # Check if we should log based on level
        level_priority = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4
        }
        
        if level_priority[entry.level] < level_priority[self.log_level]:
            return
        
        try:
            # Write structured JSON log
            with open(self.current_log, 'a') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
            
            # Write user-friendly log
            with open(self.user_friendly_log, 'a') as f:
                f.write(entry.format_user_friendly() + '\n\n')
            
            # Check if rotation is needed
            self._check_and_rotate_logs()
            
        except Exception as e:
            logger.error(f"Failed to write log entry: {e}")

    def _check_and_rotate_logs(self) -> None:
        """Check log file size and rotate if necessary"""
        try:
            if self.current_log.exists() and self.current_log.stat().st_size > self.MAX_LOG_SIZE:
                self._rotate_logs()
        except Exception as e:
            logger.error(f"Failed to check/rotate logs: {e}")

    def _rotate_logs(self) -> None:
        """Rotate log files"""
        try:
            # Rotate both structured and user-friendly logs
            for log_file in [self.current_log, self.user_friendly_log]:
                if not log_file.exists():
                    continue
                
                # Shift existing rotated logs
                for i in range(self.MAX_LOG_FILES - 1, 0, -1):
                    old_file = log_file.parent / f"{log_file.stem}.{i}{log_file.suffix}"
                    new_file = log_file.parent / f"{log_file.stem}.{i + 1}{log_file.suffix}"
                    
                    if old_file.exists():
                        if i == self.MAX_LOG_FILES - 1:
                            # Delete oldest log
                            old_file.unlink()
                        else:
                            old_file.rename(new_file)
                
                # Rotate current log to .1
                rotated_file = log_file.parent / f"{log_file.stem}.1{log_file.suffix}"
                log_file.rename(rotated_file)
            
            logger.info("Log files rotated successfully")
            
        except Exception as e:
            logger.error(f"Failed to rotate logs: {e}")

    def _get_troubleshooting_suggestions(self, event: OperationStatus) -> List[str]:
        """
        Get troubleshooting suggestions based on operation status.
        
        Args:
            event: Operation status
            
        Returns:
            List of troubleshooting suggestions
        """
        suggestions = []
        
        # Generic suggestions based on operation type
        if event.operation_type == 'backup':
            if 'permission' in event.message.lower():
                suggestions.extend([
                    "Check file and directory permissions for the backup source",
                    "Ensure TimeLocker has read access to all files being backed up",
                    "Try running the backup with appropriate permissions"
                ])
            elif 'network' in event.message.lower() or 'connection' in event.message.lower():
                suggestions.extend([
                    "Check your network connection",
                    "Verify repository URL and credentials",
                    "Check if the backup destination is accessible"
                ])
            elif 'space' in event.message.lower() or 'disk' in event.message.lower():
                suggestions.extend([
                    "Check available disk space on the backup destination",
                    "Consider cleaning up old backups",
                    "Review retention policies to free up space"
                ])
            else:
                suggestions.extend([
                    "Check the detailed error message above",
                    "Review recent log entries for more context",
                    "Verify backup configuration settings"
                ])
        
        elif event.operation_type == 'restore':
            suggestions.extend([
                "Verify the snapshot exists and is accessible",
                "Check destination path permissions",
                "Ensure sufficient disk space for restore"
            ])
        
        return suggestions

    def _extract_error_context(self, event: OperationStatus) -> Dict[str, Any]:
        """
        Extract error context from operation status.
        
        Args:
            event: Operation status
            
        Returns:
            Error context dictionary
        """
        context = {}
        
        if event.metadata:
            # Extract relevant error information
            if 'error_type' in event.metadata:
                context['error_type'] = event.metadata['error_type']
            if 'error_code' in event.metadata:
                context['error_code'] = event.metadata['error_code']
            if 'stack_trace' in event.metadata:
                context['stack_trace'] = event.metadata['stack_trace']
        
        return context

    def _get_error_troubleshooting(self, error: Exception, context: Dict[str, Any]) -> List[str]:
        """
        Get troubleshooting suggestions for an error.
        
        Args:
            error: Exception that occurred
            context: Error context
            
        Returns:
            List of troubleshooting suggestions
        """
        suggestions = []
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Common error patterns
        if 'permission' in error_msg or 'access' in error_msg:
            suggestions.extend([
                "Check file and directory permissions",
                "Ensure you have the necessary access rights",
                "Try running with appropriate permissions"
            ])
        elif 'connection' in error_msg or 'network' in error_msg:
            suggestions.extend([
                "Check your network connection",
                "Verify server/repository is accessible",
                "Check firewall settings"
            ])
        elif 'not found' in error_msg or 'does not exist' in error_msg:
            suggestions.extend([
                "Verify the file or directory path",
                "Check if the resource has been moved or deleted",
                "Ensure the configuration is correct"
            ])
        elif 'timeout' in error_msg:
            suggestions.extend([
                "Check network connectivity",
                "Increase timeout settings if appropriate",
                "Verify the remote service is responding"
            ])
        else:
            suggestions.extend([
                "Review the error message and context above",
                "Check the application logs for more details",
                "Verify your configuration settings"
            ])
        
        return suggestions

    def _load_config(self) -> None:
        """Load logger configuration"""
        config_file = self.log_dir / "logger_config.json"
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    if 'log_level' in data:
                        self.log_level = LogLevel(data['log_level'])
        except Exception as e:
            logger.warning(f"Failed to load logger config: {e}")

    def _save_config(self) -> None:
        """Save logger configuration"""
        config_file = self.log_dir / "logger_config.json"
        
        try:
            with open(config_file, 'w') as f:
                json.dump({'log_level': self.log_level.value}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save logger config: {e}")
