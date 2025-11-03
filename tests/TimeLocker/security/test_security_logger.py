"""
Tests for SecurityLogger functionality.

This module tests the SecurityLogger class which provides user-friendly
security event logging, filtering, retention management, and notifications.
"""

import json
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from TimeLocker.security.security_logger import (
    SecurityLogger, SecurityLogEntry, SecurityLogLevel, SecurityEventType,
    EventFilter, SecurityNotification
)


@pytest.mark.security
class TestSecurityLogger:
    """Test SecurityLogger functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.security_logger = SecurityLogger(config_dir=self.temp_dir, retention_days=30)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.unit
    def test_security_logger_initialization(self):
        """Test SecurityLogger initialization"""
        assert self.security_logger.config_dir == self.temp_dir
        assert self.security_logger.retention_days == 30
        assert self.security_logger.security_log_file.exists()
        assert self.security_logger.notification_log_file.exists()

    @pytest.mark.unit
    def test_log_event_basic(self):
        """Test basic event logging functionality"""
        event = SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.AUTHENTICATION,
            level=SecurityLogLevel.MEDIUM,
            description="User authentication successful",
            user_id="test_user",
            repository_id="test_repo",
            metadata={"method": "password"},
            source="TestSource"
        )

        self.security_logger.log_event(event)

        # Verify event was logged
        events = self.security_logger.get_events()
        assert len(events) == 1
        assert events[0].description == "User authentication successful"
        assert events[0].event_type == SecurityEventType.AUTHENTICATION
        assert events[0].level == SecurityLogLevel.MEDIUM

    @pytest.mark.unit
    def test_event_filtering(self):
        """Test event filtering functionality"""
        # Create test events
        events_data = [
            (SecurityEventType.AUTHENTICATION, SecurityLogLevel.HIGH, "Auth failed"),
            (SecurityEventType.BACKUP_OPERATION, SecurityLogLevel.LOW, "Backup success"),
            (SecurityEventType.CREDENTIAL_ACCESS, SecurityLogLevel.MEDIUM, "Credential read"),
            (SecurityEventType.INTEGRITY_CHECK, SecurityLogLevel.CRITICAL, "Integrity failure")
        ]

        for event_type, level, description in events_data:
            event = SecurityLogEntry(
                timestamp=datetime.now(),
                event_type=event_type,
                level=level,
                description=description,
                source="TestSource"
            )
            self.security_logger.log_event(event)

        # Test filtering by event type
        filter_criteria = EventFilter(event_types=[SecurityEventType.AUTHENTICATION])
        filtered_events = self.security_logger.get_events(filter_criteria)
        assert len(filtered_events) == 1
        assert filtered_events[0].event_type == SecurityEventType.AUTHENTICATION

        # Test filtering by level
        filter_criteria = EventFilter(levels=[SecurityLogLevel.CRITICAL])
        filtered_events = self.security_logger.get_events(filter_criteria)
        assert len(filtered_events) == 1
        assert filtered_events[0].level == SecurityLogLevel.CRITICAL

        # Test filtering by date range
        yesterday = datetime.now() - timedelta(days=1)
        tomorrow = datetime.now() + timedelta(days=1)
        filter_criteria = EventFilter(start_date=yesterday, end_date=tomorrow)
        filtered_events = self.security_logger.get_events(filter_criteria)
        assert len(filtered_events) == 4  # All events should be within range

    @pytest.mark.unit
    def test_notification_generation(self):
        """Test security notification generation"""
        notification_handler = Mock()
        self.security_logger.add_notification_handler(notification_handler)

        # Create critical event that should generate notification
        critical_event = SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.EMERGENCY_LOCKDOWN,
            level=SecurityLogLevel.CRITICAL,
            description="Emergency lockdown activated due to security breach",
            source="TestSource"
        )

        self.security_logger.log_event(critical_event)

        # Verify notification handler was called
        assert notification_handler.call_count == 1
        notification = notification_handler.call_args[0][0]
        assert isinstance(notification, SecurityNotification)
        assert notification.level == SecurityLogLevel.CRITICAL
        assert "Emergency Lockdown Activated" in notification.title

    @pytest.mark.unit
    def test_log_retention_cleanup(self):
        """Test log retention and cleanup functionality"""
        # Create events with different timestamps
        old_event = SecurityLogEntry(
            timestamp=datetime.now() - timedelta(days=35),  # Older than retention
            event_type=SecurityEventType.AUTHENTICATION,
            level=SecurityLogLevel.LOW,
            description="Old authentication event",
            source="TestSource"
        )

        recent_event = SecurityLogEntry(
            timestamp=datetime.now() - timedelta(days=5),  # Within retention
            event_type=SecurityEventType.BACKUP_OPERATION,
            level=SecurityLogLevel.LOW,
            description="Recent backup event",
            source="TestSource"
        )

        # Manually write events to log file to simulate old entries
        with open(self.security_logger.security_log_file, 'w') as f:
            f.write(json.dumps(old_event.to_dict()) + '\n')
            f.write(json.dumps(recent_event.to_dict()) + '\n')

        # Run cleanup
        self.security_logger.cleanup_old_logs()

        # Verify only recent event remains
        events = self.security_logger.get_events()
        assert len(events) == 1
        assert events[0].description == "Recent backup event"

    @pytest.mark.unit
    def test_export_logs_json(self):
        """Test exporting logs to JSON format"""
        # Create test event
        event = SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.BACKUP_OPERATION,
            level=SecurityLogLevel.MEDIUM,
            description="Test backup operation",
            source="TestSource"
        )
        self.security_logger.log_event(event)

        # Export to JSON
        export_path = self.temp_dir / "export.json"
        success = self.security_logger.export_logs(export_path, format_type="json")
        assert success
        assert export_path.exists()

        # Verify export content
        with open(export_path, 'r') as f:
            export_data = json.load(f)
        
        assert export_data["total_events"] == 1
        assert len(export_data["events"]) == 1
        assert export_data["events"][0]["description"] == "Test backup operation"

    @pytest.mark.unit
    def test_export_logs_csv(self):
        """Test exporting logs to CSV format"""
        # Create test event
        event = SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.CREDENTIAL_ACCESS,
            level=SecurityLogLevel.HIGH,
            description="Test credential access",
            source="TestSource"
        )
        self.security_logger.log_event(event)

        # Export to CSV
        export_path = self.temp_dir / "export.csv"
        success = self.security_logger.export_logs(export_path, format_type="csv")
        assert success
        assert export_path.exists()

        # Verify CSV content
        with open(export_path, 'r') as f:
            content = f.read()
        
        assert "Timestamp,Event Type,Level,Description" in content
        assert "Test credential access" in content
        assert "credential_access" in content

    @pytest.mark.unit
    def test_security_summary(self):
        """Test security summary generation"""
        # Create various test events
        events_data = [
            (SecurityEventType.AUTHENTICATION, SecurityLogLevel.HIGH),
            (SecurityEventType.AUTHENTICATION, SecurityLogLevel.HIGH),
            (SecurityEventType.BACKUP_OPERATION, SecurityLogLevel.LOW),
            (SecurityEventType.INTEGRITY_CHECK, SecurityLogLevel.CRITICAL)
        ]

        for event_type, level in events_data:
            event = SecurityLogEntry(
                timestamp=datetime.now(),
                event_type=event_type,
                level=level,
                description=f"Test {event_type.value} event",
                source="TestSource"
            )
            self.security_logger.log_event(event)

        # Get security summary
        summary = self.security_logger.get_security_summary(days=7)

        assert summary["total_events"] == 4
        assert summary["events_by_type"]["authentication"] == 2
        assert summary["events_by_type"]["backup_operation"] == 1
        assert summary["events_by_level"]["high"] == 2
        assert summary["events_by_level"]["critical"] == 1
        assert summary["critical_events"] == 1
        assert summary["high_events"] == 2

    @pytest.mark.unit
    def test_notification_management(self):
        """Test notification storage and retrieval"""
        # Create notification
        notification = SecurityNotification(
            title="Test Security Alert",
            message="This is a test security notification",
            level=SecurityLogLevel.HIGH,
            suggested_actions=["Check logs", "Verify system"]
        )

        # Send notification
        self.security_logger._send_notification(notification)

        # Retrieve notifications
        notifications = self.security_logger.get_notifications(hours=24)
        assert len(notifications) == 1
        assert notifications[0].title == "Test Security Alert"
        assert notifications[0].level == SecurityLogLevel.HIGH
        assert len(notifications[0].suggested_actions) == 2

    @pytest.mark.unit
    def test_integration_with_existing_logs(self):
        """Test integration with existing SecurityService and CredentialManager logs"""
        # Create mock SecurityService audit log
        security_audit_log = self.temp_dir / "audit.log"
        with open(security_audit_log, 'w') as f:
            f.write("# TimeLocker Security Audit Log\n")
            f.write(f"{datetime.now().isoformat()}|backup_operation|medium|Test backup|user1|repo1|{{}}\n")

        # Create mock CredentialManager audit log
        credential_audit_log = self.temp_dir / "credential_audit.log"
        with open(credential_audit_log, 'w') as f:
            f.write("# TimeLocker Credential Manager Audit Log\n")
            f.write(f"{datetime.now().isoformat()}|store_repository_password|repo1|True|Password stored\n")

        # Run integration
        self.security_logger.integrate_with_existing_logs()

        # Verify events were imported
        events = self.security_logger.get_events()
        assert len(events) >= 2  # At least the two events we created

        # Check for backup operation event
        backup_events = [e for e in events if e.event_type == SecurityEventType.BACKUP_OPERATION]
        assert len(backup_events) >= 1

        # Check for credential access event
        credential_events = [e for e in events if e.event_type == SecurityEventType.CREDENTIAL_ACCESS]
        assert len(credential_events) >= 1

    @pytest.mark.unit
    def test_event_serialization(self):
        """Test SecurityLogEntry serialization and deserialization"""
        original_event = SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.RESTORE_OPERATION,
            level=SecurityLogLevel.MEDIUM,
            description="Test restore operation",
            user_id="test_user",
            repository_id="test_repo",
            metadata={"files_restored": 100, "duration": 30},
            source="TestSource"
        )

        # Convert to dict and back
        event_dict = original_event.to_dict()
        restored_event = SecurityLogEntry.from_dict(event_dict)

        # Verify all fields match
        assert restored_event.timestamp == original_event.timestamp
        assert restored_event.event_type == original_event.event_type
        assert restored_event.level == original_event.level
        assert restored_event.description == original_event.description
        assert restored_event.user_id == original_event.user_id
        assert restored_event.repository_id == original_event.repository_id
        assert restored_event.metadata == original_event.metadata
        assert restored_event.source == original_event.source

    @pytest.mark.unit
    def test_notification_handler_management(self):
        """Test adding and removing notification handlers"""
        handler1 = Mock()
        handler2 = Mock()

        # Add handlers
        self.security_logger.add_notification_handler(handler1)
        self.security_logger.add_notification_handler(handler2)

        # Create event that triggers notification
        critical_event = SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.INTEGRITY_CHECK,
            level=SecurityLogLevel.CRITICAL,
            description="Critical integrity check failure",
            source="TestSource"
        )

        self.security_logger.log_event(critical_event)

        # Both handlers should be called
        assert handler1.call_count == 1
        assert handler2.call_count == 1

        # Remove one handler
        self.security_logger.remove_notification_handler(handler1)

        # Create another critical event
        critical_event2 = SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.EMERGENCY_LOCKDOWN,
            level=SecurityLogLevel.CRITICAL,
            description="Emergency lockdown test",
            source="TestSource"
        )

        self.security_logger.log_event(critical_event2)

        # Only handler2 should be called again
        assert handler1.call_count == 1  # Still 1
        assert handler2.call_count == 2  # Now 2

    @pytest.mark.unit
    def test_malformed_log_entry_handling(self):
        """Test handling of malformed log entries during import"""
        # Create log file with malformed entries
        with open(self.security_logger.security_log_file, 'w') as f:
            # Valid entry
            valid_event = SecurityLogEntry(
                timestamp=datetime.now(),
                event_type=SecurityEventType.AUTHENTICATION,
                level=SecurityLogLevel.LOW,
                description="Valid event",
                source="TestSource"
            )
            f.write(json.dumps(valid_event.to_dict()) + '\n')
            
            # Malformed JSON
            f.write('{"invalid": json}\n')
            
            # Missing required fields
            f.write('{"timestamp": "2023-01-01T00:00:00"}\n')

        # Should handle malformed entries gracefully
        events = self.security_logger.get_events()
        assert len(events) == 1  # Only the valid event should be returned
        assert events[0].description == "Valid event"

    @pytest.mark.integration
    def test_performance_with_large_log_files(self):
        """Test performance with large numbers of log entries"""
        # Create many log entries
        num_events = 1000
        for i in range(num_events):
            event = SecurityLogEntry(
                timestamp=datetime.now() - timedelta(seconds=i),
                event_type=SecurityEventType.BACKUP_OPERATION,
                level=SecurityLogLevel.LOW,
                description=f"Backup operation {i}",
                source="TestSource"
            )
            self.security_logger.log_event(event)

        # Test retrieval with limit
        events = self.security_logger.get_events(EventFilter(limit=100))
        assert len(events) == 100

        # Test filtering performance
        filter_criteria = EventFilter(
            event_types=[SecurityEventType.BACKUP_OPERATION],
            levels=[SecurityLogLevel.LOW],
            limit=50
        )
        filtered_events = self.security_logger.get_events(filter_criteria)
        assert len(filtered_events) == 50

        # Test cleanup performance
        self.security_logger.cleanup_old_logs()
        
        # Verify cleanup worked
        remaining_events = self.security_logger.get_events()
        assert len(remaining_events) <= num_events  # Some may have been cleaned up