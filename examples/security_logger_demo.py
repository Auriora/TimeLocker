#!/usr/bin/env python3
"""
SecurityLogger Demo Script

This script demonstrates the SecurityLogger functionality including:
- Event logging with different types and levels
- Log filtering and retrieval
- Notification system
- Log cleanup and retention
- Export functionality
- Integration with SecurityService and CredentialManager
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, 'src')

from TimeLocker.security.security_logger import (
    SecurityLogger, SecurityLogEntry, SecurityLogLevel, SecurityEventType,
    EventFilter, SecurityNotification
)
from TimeLocker.security.security_service import SecurityService, SecurityEvent, SecurityLevel
from TimeLocker.security.credential_manager import CredentialManager


def demo_basic_logging():
    """Demonstrate basic logging functionality"""
    print("\n=== Basic Logging Demo ===")
    
    temp_dir = Path(tempfile.mkdtemp())
    logger = SecurityLogger(config_dir=temp_dir)
    
    # Create various types of events
    events = [
        SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.AUTHENTICATION,
            level=SecurityLogLevel.MEDIUM,
            description="User login successful",
            user_id="demo_user",
            metadata={"method": "password", "ip": "192.168.1.100"},
            source="AuthSystem"
        ),
        SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.BACKUP_OPERATION,
            level=SecurityLogLevel.LOW,
            description="Backup completed successfully",
            repository_id="home_backup",
            metadata={"files_backed_up": 1250, "size_mb": 2048, "duration_seconds": 45},
            source="BackupManager"
        ),
        SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.CREDENTIAL_ACCESS,
            level=SecurityLogLevel.HIGH,
            description="Repository password retrieved",
            repository_id="cloud_backup",
            metadata={"operation": "get_password", "success": True},
            source="CredentialManager"
        ),
        SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.INTEGRITY_CHECK,
            level=SecurityLogLevel.CRITICAL,
            description="Backup integrity check failed",
            repository_id="cloud_backup",
            metadata={"errors_found": 3, "corrupted_files": ["file1.txt", "file2.doc"]},
            source="IntegrityChecker"
        )
    ]
    
    # Log all events
    for event in events:
        logger.log_event(event)
        print(f"Logged: {event.event_type.value} - {event.level.value} - {event.description}")
    
    print(f"Total events logged: {len(events)}")
    return logger


def demo_filtering():
    """Demonstrate log filtering capabilities"""
    print("\n=== Log Filtering Demo ===")
    
    logger = demo_basic_logging()
    
    # Filter by event type
    print("\n--- Authentication Events ---")
    auth_filter = EventFilter(event_types=[SecurityEventType.AUTHENTICATION])
    auth_events = logger.get_events(auth_filter)
    for event in auth_events:
        print(f"  {event.timestamp.strftime('%H:%M:%S')} - {event.description}")
    
    # Filter by security level
    print("\n--- High/Critical Events ---")
    high_level_filter = EventFilter(levels=[SecurityLogLevel.HIGH, SecurityLogLevel.CRITICAL])
    high_events = logger.get_events(high_level_filter)
    for event in high_events:
        print(f"  {event.level.value.upper()} - {event.description}")
    
    # Filter by repository
    print("\n--- Cloud Backup Repository Events ---")
    repo_filter = EventFilter(repository_id="cloud_backup")
    repo_events = logger.get_events(repo_filter)
    for event in repo_events:
        print(f"  {event.event_type.value} - {event.description}")
    
    return logger


def demo_notifications():
    """Demonstrate notification system"""
    print("\n=== Notification System Demo ===")
    
    temp_dir = Path(tempfile.mkdtemp())
    logger = SecurityLogger(config_dir=temp_dir)
    
    # Set up notification handler
    notifications_received = []
    def notification_handler(notification):
        notifications_received.append(notification)
        print(f"🚨 NOTIFICATION: {notification.title}")
        print(f"   Level: {notification.level.value}")
        print(f"   Message: {notification.message}")
        if notification.suggested_actions:
            print("   Suggested Actions:")
            for action in notification.suggested_actions:
                print(f"     • {action}")
        print()
    
    logger.add_notification_handler(notification_handler)
    
    # Create events that trigger notifications
    critical_events = [
        SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.EMERGENCY_LOCKDOWN,
            level=SecurityLogLevel.CRITICAL,
            description="Emergency lockdown activated due to multiple failed authentication attempts",
            source="SecuritySystem"
        ),
        SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.INTEGRITY_CHECK,
            level=SecurityLogLevel.CRITICAL,
            description="Critical backup integrity failure detected",
            repository_id="important_data",
            source="IntegrityChecker"
        ),
        SecurityLogEntry(
            timestamp=datetime.now(),
            event_type=SecurityEventType.AUTHENTICATION,
            level=SecurityLogLevel.HIGH,
            description="Authentication failed - invalid credentials",
            user_id="unknown_user",
            metadata={"attempts": 5, "ip": "192.168.1.200"},
            source="AuthSystem"
        )
    ]
    
    for event in critical_events:
        logger.log_event(event)
    
    print(f"Generated {len(notifications_received)} notifications")
    return logger


def demo_security_summary():
    """Demonstrate security summary generation"""
    print("\n=== Security Summary Demo ===")
    
    logger = demo_basic_logging()
    
    # Generate summary
    summary = logger.get_security_summary(days=1)
    
    print(f"Security Summary (Last {summary['period_days']} days):")
    print(f"  Total Events: {summary['total_events']}")
    print(f"  Critical Events: {summary['critical_events']}")
    print(f"  High Priority Events: {summary['high_events']}")
    
    print("\n  Events by Type:")
    for event_type, count in summary['events_by_type'].items():
        print(f"    {event_type}: {count}")
    
    print("\n  Events by Level:")
    for level, count in summary['events_by_level'].items():
        print(f"    {level}: {count}")
    
    return logger


def demo_export():
    """Demonstrate log export functionality"""
    print("\n=== Log Export Demo ===")
    
    logger = demo_basic_logging()
    temp_dir = logger.config_dir
    
    # Export to JSON
    json_export = temp_dir / "security_logs.json"
    success = logger.export_logs(json_export, format_type="json")
    print(f"JSON Export: {'SUCCESS' if success else 'FAILED'}")
    if success:
        print(f"  Exported to: {json_export}")
        print(f"  File size: {json_export.stat().st_size} bytes")
    
    # Export to CSV
    csv_export = temp_dir / "security_logs.csv"
    success = logger.export_logs(csv_export, format_type="csv")
    print(f"CSV Export: {'SUCCESS' if success else 'FAILED'}")
    if success:
        print(f"  Exported to: {csv_export}")
        print(f"  File size: {csv_export.stat().st_size} bytes")
    
    return logger


def demo_integration():
    """Demonstrate integration with SecurityService and CredentialManager"""
    print("\n=== Integration Demo ===")
    
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create credential manager
    credential_manager = CredentialManager(config_dir=temp_dir / "credentials")
    credential_manager.unlock("demo_master_password")
    print("CredentialManager initialized and unlocked")
    
    # Create security service with integrated SecurityLogger
    security_service = SecurityService(
        credential_manager=credential_manager,
        config_dir=temp_dir / "security"
    )
    print("SecurityService initialized with SecurityLogger integration")
    
    # Perform some operations that generate security events
    
    # 1. Store repository credentials (generates credential access event)
    credential_manager.store_repository_password("demo_repo", "secure_password_123")
    print("Stored repository credentials")
    
    # 2. Log backup operation
    security_service.audit_backup_operation(
        operation_type="incremental",
        success=True,
        repository_id="demo_repo",
        status="completed",
        file_count=500,
        total_size=1024*1024*100  # 100MB
    )
    print("Logged backup operation")
    
    # 3. Log restore operation
    security_service.audit_restore_operation(
        snapshot_id="snapshot_123",
        success=True,
        repository_id="demo_repo",
        status="completed",
        files_restored=250
    )
    print("Logged restore operation")
    
    # Get security logs through SecurityService interface
    logs = security_service.get_security_logs(days=1)
    print(f"\nRetrieved {len(logs)} security events through SecurityService:")
    for log in logs:
        print(f"  {log['event_type']} - {log['level']} - {log['description']}")
    
    # Get security summary
    summary = security_service.security_logger.get_security_summary(days=1)
    print(f"\nSecurity Summary: {summary['total_events']} total events")
    
    return security_service


def demo_cleanup():
    """Demonstrate log cleanup functionality"""
    print("\n=== Log Cleanup Demo ===")
    
    temp_dir = Path(tempfile.mkdtemp())
    logger = SecurityLogger(config_dir=temp_dir, retention_days=7)
    
    # Create events with different ages
    import json
    
    old_event = SecurityLogEntry(
        timestamp=datetime.now() - timedelta(days=10),
        event_type=SecurityEventType.AUTHENTICATION,
        level=SecurityLogLevel.LOW,
        description="Old authentication event (should be cleaned up)",
        source="TestSource"
    )
    
    recent_event = SecurityLogEntry(
        timestamp=datetime.now() - timedelta(days=2),
        event_type=SecurityEventType.BACKUP_OPERATION,
        level=SecurityLogLevel.LOW,
        description="Recent backup event (should be kept)",
        source="TestSource"
    )
    
    # Manually create log file with old and new events
    with open(logger.security_log_file, 'w') as f:
        f.write(json.dumps(old_event.to_dict()) + '\n')
        f.write(json.dumps(recent_event.to_dict()) + '\n')
    
    print("Created log file with old and recent events")
    
    # Check events before cleanup
    events_before = logger.get_events()
    print(f"Events before cleanup: {len(events_before)}")
    for event in events_before:
        age_days = (datetime.now() - event.timestamp).days
        print(f"  {event.description} (age: {age_days} days)")
    
    # Run cleanup
    logger.cleanup_old_logs()
    print("\nLog cleanup completed")
    
    # Check events after cleanup
    events_after = logger.get_events()
    print(f"Events after cleanup: {len(events_after)}")
    for event in events_after:
        age_days = (datetime.now() - event.timestamp).days
        print(f"  {event.description} (age: {age_days} days)")
    
    return logger


def main():
    """Run all SecurityLogger demos"""
    print("SecurityLogger Demonstration")
    print("=" * 50)
    
    try:
        # Run all demos
        demo_basic_logging()
        demo_filtering()
        demo_notifications()
        demo_security_summary()
        demo_export()
        demo_integration()
        demo_cleanup()
        
        print("\n" + "=" * 50)
        print("All SecurityLogger demos completed successfully! ✅")
        print("\nKey Features Demonstrated:")
        print("• Event logging with different types and security levels")
        print("• Flexible filtering by type, level, date, repository, and user")
        print("• Real-time notification system for critical events")
        print("• Security summaries and analytics")
        print("• Log export to JSON and CSV formats")
        print("• Integration with SecurityService and CredentialManager")
        print("• Automatic log cleanup and retention management")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())