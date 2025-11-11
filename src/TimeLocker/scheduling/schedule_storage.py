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

Schedule Storage

This module provides persistent storage for schedule configurations
using JSON files with atomic write operations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import tempfile
import shutil

from .scheduling_models import ScheduleConfig, SchedulePattern, SchedulePatternType
from .scheduling_exceptions import SchedulingError

logger = logging.getLogger(__name__)


class ScheduleStorage:
    """
    Persistent storage for schedule configurations.
    
    Responsibilities:
    - Save and load schedule configurations
    - Atomic write operations
    - Data integrity validation
    - Backup and recovery
    """
    
    def __init__(self, storage_dir: Path):
        """
        Initialize schedule storage.
        
        Args:
            storage_dir: Directory for schedule storage
        """
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.schedules_file = self.storage_dir / "schedules.json"
        self.backup_dir = self.storage_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.ScheduleStorage")
        
        # Initialize storage file if it doesn't exist
        if not self.schedules_file.exists():
            self._write_schedules({})
    
    def save_schedule(self, schedule: ScheduleConfig) -> None:
        """
        Save a schedule configuration.
        
        Args:
            schedule: Schedule configuration to save
            
        Raises:
            SchedulingError: If save operation fails
        """
        try:
            schedules = self._read_schedules()
            schedules[schedule.schedule_id] = self._schedule_to_dict(schedule)
            self._write_schedules(schedules)
            
            self.logger.debug(f"Saved schedule: {schedule.schedule_id}")
            
        except Exception as e:
            error_msg = f"Failed to save schedule {schedule.schedule_id}: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    def load_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """
        Load a schedule configuration by ID.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            ScheduleConfig or None if not found
        """
        try:
            schedules = self._read_schedules()
            schedule_data = schedules.get(schedule_id)
            
            if schedule_data is None:
                return None
            
            schedule = self._dict_to_schedule(schedule_data)
            self.logger.debug(f"Loaded schedule: {schedule_id}")
            return schedule
            
        except Exception as e:
            self.logger.error(f"Failed to load schedule {schedule_id}: {e}")
            return None
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule configuration.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SchedulingError: If delete operation fails
        """
        try:
            schedules = self._read_schedules()
            
            if schedule_id not in schedules:
                return False
            
            del schedules[schedule_id]
            self._write_schedules(schedules)
            
            self.logger.debug(f"Deleted schedule: {schedule_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to delete schedule {schedule_id}: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    def list_schedules(self) -> List[ScheduleConfig]:
        """
        List all stored schedules.
        
        Returns:
            List of schedule configurations
        """
        try:
            schedules = self._read_schedules()
            schedule_list = []
            
            for schedule_data in schedules.values():
                try:
                    schedule = self._dict_to_schedule(schedule_data)
                    schedule_list.append(schedule)
                except Exception as e:
                    self.logger.warning(f"Failed to parse schedule: {e}")
                    continue
            
            return schedule_list
            
        except Exception as e:
            self.logger.error(f"Failed to list schedules: {e}")
            return []
    
    def backup_schedules(self) -> Path:
        """
        Create a backup of all schedules.
        
        Returns:
            Path to backup file
            
        Raises:
            SchedulingError: If backup operation fails
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"schedules_backup_{timestamp}.json"
            
            shutil.copy2(self.schedules_file, backup_file)
            
            self.logger.info(f"Created schedule backup: {backup_file}")
            return backup_file
            
        except Exception as e:
            error_msg = f"Failed to backup schedules: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    def restore_from_backup(self, backup_file: Path) -> None:
        """
        Restore schedules from a backup file.
        
        Args:
            backup_file: Path to backup file
            
        Raises:
            SchedulingError: If restore operation fails
        """
        try:
            if not backup_file.exists():
                raise SchedulingError(f"Backup file not found: {backup_file}")
            
            # Validate backup file
            with open(backup_file, 'r') as f:
                json.load(f)  # Validate JSON
            
            # Create backup of current state before restoring
            self.backup_schedules()
            
            # Restore from backup
            shutil.copy2(backup_file, self.schedules_file)
            
            self.logger.info(f"Restored schedules from backup: {backup_file}")
            
        except Exception as e:
            error_msg = f"Failed to restore from backup: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    def _read_schedules(self) -> Dict[str, Dict]:
        """
        Read schedules from storage file.
        
        Returns:
            Dictionary of schedule data
        """
        try:
            with open(self.schedules_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse schedules file: {e}")
            # Try to recover from backup
            return self._recover_from_backup()
        except Exception as e:
            self.logger.error(f"Failed to read schedules: {e}")
            return {}
    
    def _write_schedules(self, schedules: Dict[str, Dict]) -> None:
        """
        Write schedules to storage file atomically.
        
        Args:
            schedules: Dictionary of schedule data
        """
        # Write to temporary file first
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.storage_dir,
            prefix=".schedules_",
            suffix=".json.tmp"
        )
        
        try:
            with open(temp_fd, 'w') as f:
                json.dump(schedules, f, indent=2, default=str)
            
            # Atomic rename
            shutil.move(temp_path, self.schedules_file)
            
        except Exception as e:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink()
            except:
                pass
            raise e
    
    def _recover_from_backup(self) -> Dict[str, Dict]:
        """
        Attempt to recover schedules from most recent backup.
        
        Returns:
            Dictionary of schedule data or empty dict if recovery fails
        """
        try:
            # Find most recent backup
            backups = sorted(self.backup_dir.glob("schedules_backup_*.json"), reverse=True)
            
            if not backups:
                self.logger.warning("No backups available for recovery")
                return {}
            
            backup_file = backups[0]
            self.logger.info(f"Attempting recovery from backup: {backup_file}")
            
            with open(backup_file, 'r') as f:
                schedules = json.load(f)
            
            # Write recovered data
            self._write_schedules(schedules)
            
            self.logger.info("Successfully recovered schedules from backup")
            return schedules
            
        except Exception as e:
            self.logger.error(f"Failed to recover from backup: {e}")
            return {}
    
    def _schedule_to_dict(self, schedule: ScheduleConfig) -> Dict:
        """
        Convert ScheduleConfig to dictionary for storage.
        
        Args:
            schedule: Schedule configuration
            
        Returns:
            Dictionary representation
        """
        return {
            'schedule_id': schedule.schedule_id,
            'name': schedule.name,
            'description': schedule.description,
            'policy_id': schedule.policy_id,
            'schedule_pattern': {
                'pattern_type': schedule.schedule_pattern.pattern_type.value,
                'cron_expression': schedule.schedule_pattern.cron_expression,
                'interval_minutes': schedule.schedule_pattern.interval_minutes,
                'calendar_config': self._calendar_config_to_dict(schedule.schedule_pattern.calendar_config),
                'randomize_delay_minutes': schedule.schedule_pattern.randomize_delay_minutes,
                'backup_window': self._backup_window_to_dict(schedule.schedule_pattern.backup_window)
            },
            'enabled': schedule.enabled,
            'execution_timeout': schedule.execution_timeout,
            'retry_config': self._retry_config_to_dict(schedule.retry_config),
            'monitoring_config': self._monitoring_config_to_dict(schedule.monitoring_config),
            'platform_specific_config': schedule.platform_specific_config,
            'created_at': schedule.created_at.isoformat(),
            'updated_at': schedule.updated_at.isoformat(),
            'created_by': schedule.created_by
        }
    
    def _dict_to_schedule(self, data: Dict) -> ScheduleConfig:
        """
        Convert dictionary to ScheduleConfig.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ScheduleConfig instance
        """
        from .scheduling_models import (
            ScheduleConfig, SchedulePattern, RetryConfig, MonitoringConfig
        )
        
        pattern_data = data['schedule_pattern']
        schedule_pattern = SchedulePattern(
            pattern_type=SchedulePatternType(pattern_data['pattern_type']),
            cron_expression=pattern_data.get('cron_expression'),
            interval_minutes=pattern_data.get('interval_minutes'),
            calendar_config=self._dict_to_calendar_config(pattern_data.get('calendar_config')),
            randomize_delay_minutes=pattern_data.get('randomize_delay_minutes', 0),
            backup_window=self._dict_to_backup_window(pattern_data.get('backup_window'))
        )
        
        return ScheduleConfig(
            schedule_id=data['schedule_id'],
            name=data['name'],
            description=data.get('description'),
            policy_id=data['policy_id'],
            schedule_pattern=schedule_pattern,
            enabled=data.get('enabled', True),
            execution_timeout=data.get('execution_timeout'),
            retry_config=self._dict_to_retry_config(data.get('retry_config')),
            monitoring_config=self._dict_to_monitoring_config(data.get('monitoring_config')),
            platform_specific_config=data.get('platform_specific_config', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            created_by=data.get('created_by', '')
        )
    
    def _calendar_config_to_dict(self, config) -> Optional[Dict]:
        """Convert CalendarConfig to dict."""
        if config is None:
            return None
        return {
            'days_of_week': config.days_of_week,
            'time_of_day': config.time_of_day.isoformat(),
            'weeks_of_month': config.weeks_of_month,
            'months_of_year': config.months_of_year
        }
    
    def _dict_to_calendar_config(self, data: Optional[Dict]):
        """Convert dict to CalendarConfig."""
        if data is None:
            return None
        from datetime import time
        from .scheduling_models import CalendarConfig
        return CalendarConfig(
            days_of_week=data['days_of_week'],
            time_of_day=time.fromisoformat(data['time_of_day']),
            weeks_of_month=data.get('weeks_of_month'),
            months_of_year=data.get('months_of_year')
        )
    
    def _backup_window_to_dict(self, window) -> Optional[Dict]:
        """Convert BackupWindow to dict."""
        if window is None:
            return None
        return {
            'start_time': window.start_time.isoformat(),
            'end_time': window.end_time.isoformat(),
            'excluded_dates': [d.isoformat() for d in window.excluded_dates],
            'timezone': window.timezone
        }
    
    def _dict_to_backup_window(self, data: Optional[Dict]):
        """Convert dict to BackupWindow."""
        if data is None:
            return None
        from datetime import time, date
        from .scheduling_models import BackupWindow
        return BackupWindow(
            start_time=time.fromisoformat(data['start_time']),
            end_time=time.fromisoformat(data['end_time']),
            excluded_dates=[date.fromisoformat(d) for d in data.get('excluded_dates', [])],
            timezone=data.get('timezone', 'UTC')
        )
    
    def _retry_config_to_dict(self, config) -> Optional[Dict]:
        """Convert RetryConfig to dict."""
        if config is None:
            return None
        return {
            'max_attempts': config.max_attempts,
            'initial_delay_minutes': config.initial_delay_minutes,
            'backoff_multiplier': config.backoff_multiplier,
            'max_delay_minutes': config.max_delay_minutes
        }
    
    def _dict_to_retry_config(self, data: Optional[Dict]):
        """Convert dict to RetryConfig."""
        if data is None:
            return None
        from .scheduling_models import RetryConfig
        return RetryConfig(**data)
    
    def _monitoring_config_to_dict(self, config) -> Optional[Dict]:
        """Convert MonitoringConfig to dict."""
        if config is None:
            return None
        return {
            'webhook_url': config.webhook_url,
            'health_check_url': config.health_check_url,
            'notification_on_success': config.notification_on_success,
            'notification_on_failure': config.notification_on_failure,
            'notification_on_retry': config.notification_on_retry
        }
    
    def _dict_to_monitoring_config(self, data: Optional[Dict]):
        """Convert dict to MonitoringConfig."""
        if data is None:
            return None
        from .scheduling_models import MonitoringConfig
        return MonitoringConfig(**data)
