#!/usr/bin/env python3
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

"""
Demonstration of enhanced backup notification and error reporting system.

This example shows:
1. Backup-specific notification templates
2. Error classification and remediation guidance
3. Notification filtering based on duration and significance
4. Integration with status reporting
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.monitoring.notification_service import NotificationService
from TimeLocker.monitoring.status_reporter import StatusReporter, StatusLevel
from TimeLocker.services.backup_error_reporter import (
    BackupErrorReporter,
    ErrorCategory,
    ErrorSeverity
)
from TimeLocker.services.backup_notification_service import (
    BackupNotificationService,
    BackupEventType,
    NotificationFilter
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_error_classification():
    """Demonstrate error classification and remediation guidance"""
    print("\n" + "=" * 80)
    print("DEMO: Error Classification and Remediation")
    print("=" * 80)
    
    error_reporter = BackupErrorReporter()
    
    # Test different error types
    test_errors = [
        (
            Exception("Connection timeout to repository"),
            {'operation_id': 'backup-001', 'repository_id': 'prod-repo', 'tool_name': 'restic'}
        ),
        (
            Exception("Permission denied: /var/backups"),
            {'operation_id': 'backup-002', 'repository_id': 'prod-repo'}
        ),
        (
            Exception("No space left on device"),
            {'operation_id': 'backup-003', 'repository_id': 'prod-repo'}
        ),
        (
            Exception("Checksum verification failed"),
            {'operation_id': 'backup-004', 'repository_id': 'prod-repo'}
        )
    ]
    
    for error, context in test_errors:
        print(f"\n--- Classifying Error: {error} ---")
        
        backup_error = error_reporter.classify_error(error, context)
        
        print(f"Error ID: {backup_error.error_id}")
        print(f"Category: {backup_error.category.value}")
        print(f"Severity: {backup_error.severity.value}")
        print(f"Message: {backup_error.message}")
        
        print("\nRemediation Steps:")
        for i, step in enumerate(backup_error.remediation_steps, 1):
            print(f"  {i}. {step.description}")
            if step.command:
                print(f"     Command: {step.command}")
            if step.automated:
                print(f"     (Automated)")


def demo_warning_creation():
    """Demonstrate warning creation with suggestions"""
    print("\n" + "=" * 80)
    print("DEMO: Warning Creation with Suggestions")
    print("=" * 80)
    
    error_reporter = BackupErrorReporter()
    
    # Test different warnings
    test_warnings = [
        ("Backup performance is slow", {'operation_id': 'backup-005', 'repository_id': 'prod-repo'}),
        ("Some files were skipped due to permissions", {'operation_id': 'backup-006', 'repository_id': 'prod-repo'}),
        ("Using deprecated configuration option", {'operation_id': 'backup-007', 'repository_id': 'prod-repo'})
    ]
    
    for message, context in test_warnings:
        print(f"\n--- Creating Warning: {message} ---")
        
        warning = error_reporter.create_warning(message, context)
        
        print(f"Warning ID: {warning.warning_id}")
        print(f"Severity: {warning.severity.value}")
        print(f"Message: {warning.message}")
        
        if warning.suggestions:
            print("\nSuggestions:")
            for suggestion in warning.suggestions:
                print(f"  • {suggestion}")


def demo_notification_filtering():
    """Demonstrate notification filtering"""
    print("\n" + "=" * 80)
    print("DEMO: Notification Filtering")
    print("=" * 80)
    
    notification_service = NotificationService()
    status_reporter = StatusReporter()
    backup_notification_service = BackupNotificationService(
        notification_service,
        status_reporter
    )
    
    # Configure filter
    print("\nConfiguring notification filter:")
    print("  - Minimum duration: 30 seconds")
    print("  - Progress notifications: Enabled (every 60 seconds)")
    print("  - Warnings: Enabled")
    print("  - Errors: Enabled")
    print("  - Success: Enabled")
    
    backup_notification_service.update_filter(
        min_duration_seconds=30,
        notify_on_progress=True,
        progress_interval_seconds=60,
        notify_on_warnings=True,
        notify_on_errors=True,
        notify_on_success=True,
        min_severity=ErrorSeverity.LOW
    )
    
    # Display current filter config
    filter_config = backup_notification_service.get_filter_config()
    print("\nCurrent Filter Configuration:")
    for key, value in filter_config.items():
        print(f"  {key}: {value}")


def demo_backup_notifications():
    """Demonstrate backup-specific notifications"""
    print("\n" + "=" * 80)
    print("DEMO: Backup-Specific Notifications")
    print("=" * 80)
    
    notification_service = NotificationService()
    status_reporter = StatusReporter()
    backup_notification_service = BackupNotificationService(
        notification_service,
        status_reporter
    )
    error_reporter = BackupErrorReporter()
    
    # Simulate backup lifecycle with notifications
    operation_id = "backup-demo-001"
    repository_id = "demo-repo"
    
    print("\n1. Sending backup started notification...")
    backup_notification_service.notify_backup_event(
        event_type=BackupEventType.BACKUP_STARTED,
        operation_id=operation_id,
        repository_id=repository_id,
        message="Starting backup operation"
    )
    
    print("\n2. Sending backup progress notification...")
    backup_notification_service.notify_backup_progress(
        operation_id=operation_id,
        repository_id=repository_id,
        statistics={
            'files_processed': 150,
            'total_files': 500,
            'bytes_processed': 1024 * 1024 * 100,  # 100 MB
            'progress_percentage': 30
        }
    )
    
    print("\n3. Sending backup warning notification...")
    warning = error_reporter.create_warning(
        "Some files were skipped",
        context={'operation_id': operation_id, 'repository_id': repository_id}
    )
    backup_notification_service.notify_backup_warning(
        operation_id=operation_id,
        warning=warning,
        repository_id=repository_id
    )
    
    print("\n4. Sending backup completed notification...")
    backup_notification_service.notify_backup_event(
        event_type=BackupEventType.BACKUP_COMPLETED,
        operation_id=operation_id,
        repository_id=repository_id,
        message="Backup completed successfully",
        statistics={
            'files_processed': 500,
            'total_files': 500,
            'bytes_processed': 1024 * 1024 * 350,  # 350 MB
            'progress_percentage': 100,
            'duration': timedelta(seconds=120)
        }
    )


def demo_error_notification():
    """Demonstrate error notification with remediation"""
    print("\n" + "=" * 80)
    print("DEMO: Error Notification with Remediation")
    print("=" * 80)
    
    notification_service = NotificationService()
    status_reporter = StatusReporter()
    backup_notification_service = BackupNotificationService(
        notification_service,
        status_reporter
    )
    error_reporter = BackupErrorReporter()
    
    operation_id = "backup-error-001"
    repository_id = "demo-repo"
    
    print("\nSimulating backup failure...")
    
    # Create error with remediation steps
    error = error_reporter.classify_error(
        Exception("Connection timeout to repository"),
        context={
            'operation_id': operation_id,
            'repository_id': repository_id,
            'tool_name': 'restic'
        }
    )
    
    print(f"\nError Details:")
    print(f"  Category: {error.category.value}")
    print(f"  Severity: {error.severity.value}")
    print(f"  Message: {error.message}")
    
    print(f"\nRemediation Steps:")
    for i, step in enumerate(error.remediation_steps, 1):
        print(f"  {i}. {step.description}")
        if step.command:
            print(f"     Command: {step.command}")
    
    print("\nSending error notification with remediation...")
    backup_notification_service.notify_backup_error(
        operation_id=operation_id,
        error=error,
        repository_id=repository_id
    )


def demo_notification_templates():
    """Demonstrate notification templates"""
    print("\n" + "=" * 80)
    print("DEMO: Notification Templates")
    print("=" * 80)
    
    notification_service = NotificationService()
    status_reporter = StatusReporter()
    backup_notification_service = BackupNotificationService(
        notification_service,
        status_reporter
    )
    
    print("\nAvailable Notification Templates:")
    for event_type in BackupEventType:
        template = backup_notification_service.templates.get(event_type)
        if template:
            print(f"\n{event_type.value}:")
            print(f"  Title: {template.title_template}")
            print(f"  Message: {template.message_template}")
            print(f"  Include Remediation: {template.include_remediation}")
            print(f"  Include Statistics: {template.include_statistics}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 80)
    print("BACKUP NOTIFICATION AND ERROR REPORTING DEMONSTRATION")
    print("=" * 80)
    
    try:
        demo_error_classification()
        demo_warning_creation()
        demo_notification_filtering()
        demo_backup_notifications()
        demo_error_notification()
        demo_notification_templates()
        
        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
