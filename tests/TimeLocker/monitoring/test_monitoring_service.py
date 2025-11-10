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

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from TimeLocker.monitoring import (
    MonitoringService,
    HealthStatus,
    BackupEvent,
    RecoveryEvent,
    MonitoringPreferences,
    StatusLevel
)
from TimeLocker.interfaces.integration_data_models import ServiceContext


class TestMonitoringService:
    """Test suite for MonitoringService"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.monitoring_service = MonitoringService(self.temp_dir)
        
        # Create mock components for ServiceContext
        mock_config_manager = Mock()
        mock_event_bus = Mock()
        mock_service_registry = Mock()
        
        # Create a mock service context
        self.mock_context = ServiceContext(
            config_manager=mock_config_manager,
            event_bus=mock_event_bus,
            service_registry=mock_service_registry
        )

    def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self, 'monitoring_service'):
            self.monitoring_service.shutdown()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_initialization(self):
        """Test monitoring service initialization"""
        assert self.monitoring_service.config_dir.exists()
        assert self.monitoring_service.status_reporter is not None
        assert self.monitoring_service.notifier is not None
        assert self.monitoring_service.preferences is not None

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_service_interface_initialization(self):
        """Test ServiceInterface initialization"""
        result = self.monitoring_service.initialize(self.mock_context)
        assert result is True
        assert self.monitoring_service._initialized is True
        assert self.monitoring_service._context == self.mock_context

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_health_check(self):
        """Test health check functionality"""
        # Initialize first
        self.monitoring_service.initialize(self.mock_context)
        
        # Health check should pass
        assert self.monitoring_service.health_check() is True

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_capabilities(self):
        """Test getting service capabilities"""
        capabilities = self.monitoring_service.get_capabilities()
        
        assert 'event_monitoring' in capabilities
        assert 'status_reporting' in capabilities
        assert 'notifications' in capabilities
        assert 'health_monitoring' in capabilities
        assert 'operation_tracking' in capabilities
        assert 'monitoring_preferences' in capabilities

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_handle_backup_event_started(self):
        """Test handling backup started event"""
        event = BackupEvent(
            event_id="backup_001",
            event_type="backup_started",
            timestamp=datetime.now(),
            repository_id="test_repo",
            operation_id="op_001",
            message="Backup started",
            details={"source": "/data"},
            severity=StatusLevel.INFO
        )
        
        self.monitoring_service.handle_backup_event(event)
        
        # Verify operation was started
        current_ops = self.monitoring_service.status_reporter.get_current_operations()
        assert len(current_ops) == 1
        assert current_ops[0].operation_id == "op_001"

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_handle_backup_event_completed(self):
        """Test handling backup completed event"""
        # Start operation first
        start_event = BackupEvent(
            event_id="backup_002",
            event_type="backup_started",
            timestamp=datetime.now(),
            repository_id="test_repo",
            operation_id="op_002",
            message="Backup started",
            details={},
            severity=StatusLevel.INFO
        )
        self.monitoring_service.handle_backup_event(start_event)
        
        # Complete operation
        complete_event = BackupEvent(
            event_id="backup_003",
            event_type="backup_completed",
            timestamp=datetime.now(),
            repository_id="test_repo",
            operation_id="op_002",
            message="Backup completed successfully",
            details={"files_backed_up": 100},
            severity=StatusLevel.SUCCESS
        )
        self.monitoring_service.handle_backup_event(complete_event)
        
        # Verify operation was completed
        current_ops = self.monitoring_service.status_reporter.get_current_operations()
        assert not any(op.operation_id == "op_002" for op in current_ops)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_handle_recovery_event(self):
        """Test handling recovery event"""
        event = RecoveryEvent(
            event_id="recovery_001",
            event_type="recovery_started",
            timestamp=datetime.now(),
            repository_id="test_repo",
            operation_id="rec_001",
            message="Recovery started",
            details={"target": "/restore"},
            severity=StatusLevel.INFO
        )
        
        self.monitoring_service.handle_recovery_event(event)
        
        # Verify operation was started
        current_ops = self.monitoring_service.status_reporter.get_current_operations()
        assert len(current_ops) == 1
        assert current_ops[0].operation_id == "rec_001"

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_system_health_healthy(self):
        """Test getting system health when healthy"""
        # Complete a successful operation
        start_event = BackupEvent(
            event_id="health_001",
            event_type="backup_started",
            timestamp=datetime.now(),
            repository_id="test_repo",
            operation_id="health_op_001",
            message="Backup started",
            details={},
            severity=StatusLevel.INFO
        )
        self.monitoring_service.handle_backup_event(start_event)
        
        complete_event = BackupEvent(
            event_id="health_002",
            event_type="backup_completed",
            timestamp=datetime.now(),
            repository_id="test_repo",
            operation_id="health_op_001",
            message="Backup completed",
            details={},
            severity=StatusLevel.SUCCESS
        )
        self.monitoring_service.handle_backup_event(complete_event)
        
        health = self.monitoring_service.get_system_health()
        assert health == HealthStatus.HEALTHY

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_system_health_error(self):
        """Test getting system health when there are errors"""
        # Complete a failed operation
        start_event = BackupEvent(
            event_id="error_001",
            event_type="backup_started",
            timestamp=datetime.now(),
            repository_id="test_repo",
            operation_id="error_op_001",
            message="Backup started",
            details={},
            severity=StatusLevel.INFO
        )
        self.monitoring_service.handle_backup_event(start_event)
        
        error_event = BackupEvent(
            event_id="error_002",
            event_type="backup_failed",
            timestamp=datetime.now(),
            repository_id="test_repo",
            operation_id="error_op_001",
            message="Backup failed",
            details={},
            severity=StatusLevel.ERROR
        )
        self.monitoring_service.handle_backup_event(error_event)
        
        health = self.monitoring_service.get_system_health()
        assert health == HealthStatus.ERROR

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_get_monitoring_summary(self):
        """Test getting monitoring summary"""
        # Create some operations
        for i in range(3):
            start_event = BackupEvent(
                event_id=f"summary_{i}",
                event_type="backup_started",
                timestamp=datetime.now(),
                repository_id=f"repo_{i}",
                operation_id=f"summary_op_{i}",
                message=f"Backup {i} started",
                details={},
                severity=StatusLevel.INFO
            )
            self.monitoring_service.handle_backup_event(start_event)
            
            complete_event = BackupEvent(
                event_id=f"summary_complete_{i}",
                event_type="backup_completed",
                timestamp=datetime.now(),
                repository_id=f"repo_{i}",
                operation_id=f"summary_op_{i}",
                message=f"Backup {i} completed",
                details={},
                severity=StatusLevel.SUCCESS
            )
            self.monitoring_service.handle_backup_event(complete_event)
        
        summary = self.monitoring_service.get_monitoring_summary()
        
        assert summary is not None
        assert summary.health_status == HealthStatus.HEALTHY
        assert len(summary.recent_operations) >= 3
        assert len(summary.repository_statuses) >= 3
        assert len(summary.last_backup_dates) >= 3
        assert summary.generated_at is not None

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_update_preferences(self):
        """Test updating monitoring preferences"""
        new_preferences = MonitoringPreferences(
            log_level="DEBUG",
            log_retention_days=14,
            enable_desktop_notifications=False,
            notify_on_success=False
        )
        
        self.monitoring_service.update_preferences(new_preferences)
        
        # Verify preferences were updated
        current_prefs = self.monitoring_service.get_preferences()
        assert current_prefs.log_level == "DEBUG"
        assert current_prefs.log_retention_days == 14
        assert current_prefs.enable_desktop_notifications is False
        assert current_prefs.notify_on_success is False

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_preferences_persistence(self):
        """Test preferences persistence across service restarts"""
        # Update preferences
        new_preferences = MonitoringPreferences(
            log_level="WARNING",
            log_retention_days=30
        )
        self.monitoring_service.update_preferences(new_preferences)
        
        # Create new service instance (simulating restart)
        new_service = MonitoringService(self.temp_dir)
        
        # Verify preferences were loaded
        loaded_prefs = new_service.get_preferences()
        assert loaded_prefs.log_level == "WARNING"
        assert loaded_prefs.log_retention_days == 30

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_shutdown(self):
        """Test service shutdown"""
        self.monitoring_service.initialize(self.mock_context)
        self.monitoring_service.shutdown()
        
        assert self.monitoring_service._initialized is False
        assert self.monitoring_service._context is None

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_notification_integration(self):
        """Test integration with notification service"""
        # Mock the notification service to track calls
        with patch.object(self.monitoring_service.notifier, 'send_notification') as mock_notify:
            # Configure to notify on success
            self.monitoring_service.preferences.notify_on_success = True
            self.monitoring_service.preferences.min_operation_duration_seconds = 0
            
            # Update notifier config to match
            self.monitoring_service.notifier.update_config(
                notify_on_success=True,
                min_operation_duration=0
            )
            
            # Complete a successful operation
            start_event = BackupEvent(
                event_id="notify_001",
                event_type="backup_started",
                timestamp=datetime.now(),
                repository_id="test_repo",
                operation_id="notify_op_001",
                message="Backup started",
                details={"start_time": datetime.now().isoformat()},
                severity=StatusLevel.INFO
            )
            self.monitoring_service.handle_backup_event(start_event)
            
            complete_event = BackupEvent(
                event_id="notify_002",
                event_type="backup_completed",
                timestamp=datetime.now(),
                repository_id="test_repo",
                operation_id="notify_op_001",
                message="Backup completed",
                details={},
                severity=StatusLevel.SUCCESS
            )
            self.monitoring_service.handle_backup_event(complete_event)
            
            # Verify notification was sent
            assert mock_notify.called
