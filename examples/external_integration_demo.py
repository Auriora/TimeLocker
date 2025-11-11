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

External Integration Demo
=========================

This example demonstrates the optional external integration capabilities
for power users, including webhook notifications and health check service
integration.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.monitoring import (
    WebhookHandler,
    WebhookConfig,
    PayloadFormat,
    HealthCheckIntegration,
    HealthCheckServiceType,
    HealthCheckHealthStatus,
    StatusReporter,
    OperationStatus,
    StatusLevel
)


def demo_webhook_integration():
    """Demonstrate webhook integration capabilities"""
    print("=" * 70)
    print("Webhook Integration Demo")
    print("=" * 70)
    
    # Initialize webhook handler
    webhook = WebhookHandler()
    print("\n1. Webhook Handler Initialized")
    print(f"   Config directory: {webhook.config_dir}")
    
    # Configure webhook
    print("\n2. Configuring Webhook")
    webhook.update_config(
        enabled=True,
        url="https://example.com/webhook",
        payload_format=PayloadFormat.JSON,
        max_retries=3,
        retry_delay=1.0,
        include_metadata=True,
        include_progress=True
    )
    print(f"   URL: {webhook.config.url}")
    print(f"   Format: {webhook.config.payload_format.value}")
    print(f"   Max retries: {webhook.config.max_retries}")
    
    # Validate configuration
    print("\n3. Validating Webhook Configuration")
    validation = webhook.validate_webhook_config()
    print(f"   Valid: {validation['valid']}")
    if validation['errors']:
        print(f"   Errors: {validation['errors']}")
    if validation['warnings']:
        print(f"   Warnings: {validation['warnings']}")
    
    # Create a test operation status
    print("\n4. Creating Test Operation Status")
    status = OperationStatus(
        operation_id="demo_backup_001",
        operation_type="backup",
        status=StatusLevel.SUCCESS,
        message="Backup completed successfully",
        timestamp=datetime.now(),
        repository_id="demo-repo",
        progress_percentage=100,
        files_processed=1500,
        total_files=1500,
        bytes_processed=1024 * 1024 * 500  # 500 MB
    )
    print(f"   Operation: {status.operation_type}")
    print(f"   Status: {status.status.value}")
    print(f"   Files: {status.files_processed}/{status.total_files}")
    
    # Build payload (without actually sending)
    print("\n5. Building Webhook Payload")
    payload = webhook._build_payload(status)
    print(f"   Payload keys: {list(payload.keys())}")
    print(f"   Event type: {payload['event_type']}")
    print(f"   Status: {payload['status']}")
    print(f"   Progress: {payload.get('progress_percentage', 'N/A')}%")
    
    # Note: Actual sending would require a real webhook endpoint
    print("\n   Note: Actual webhook sending requires a valid endpoint")
    print("   Use webhook.send_webhook(status) to send to configured URL")
    
    # Test webhook (would fail without real endpoint)
    print("\n6. Webhook Test")
    print("   Skipping actual test (requires valid endpoint)")
    print("   Use webhook.test_webhook() to test with real endpoint")
    
    # Cleanup
    webhook.shutdown()
    print("\n✓ Webhook handler shutdown complete")


def demo_health_check_integration():
    """Demonstrate health check service integration"""
    print("\n" + "=" * 70)
    print("Health Check Integration Demo")
    print("=" * 70)
    
    # Initialize health check integration
    health_check = HealthCheckIntegration()
    print("\n1. Health Check Integration Initialized")
    print(f"   Config directory: {health_check.config_dir}")
    
    # Configure healthchecks.io service
    print("\n2. Configuring healthchecks.io Service")
    health_check.configure_healthchecks_io(
        name="primary",
        check_uuid="your-check-uuid-here",
        api_key=None  # Optional
    )
    print("   Service: healthchecks.io")
    print("   Name: primary")
    print("   UUID: your-check-uuid-here")
    
    # Configure custom HTTP health check
    print("\n3. Configuring Custom HTTP Health Check")
    health_check.configure_custom_http(
        name="custom",
        ping_url="https://example.com/health",
        custom_headers={"X-API-Key": "your-api-key"},
        verify_ssl=True
    )
    print("   Service: Custom HTTP")
    print("   Name: custom")
    print("   URL: https://example.com/health")
    
    # List configured services
    print("\n4. Configured Services")
    for name, service in health_check.config.services.items():
        print(f"   - {name}:")
        print(f"     Type: {service.service_type.value}")
        print(f"     URL: {service.ping_url}")
        print(f"     Enabled: {service.enabled}")
    
    # Validate service configurations
    print("\n5. Validating Service Configurations")
    for name, service in health_check.config.services.items():
        validation = health_check.validate_service_config(service)
        print(f"   {name}: {'✓ Valid' if validation['valid'] else '✗ Invalid'}")
        if validation['warnings']:
            for warning in validation['warnings']:
                print(f"     Warning: {warning}")
    
    # Configure periodic pinging
    print("\n6. Configuring Periodic Pinging")
    health_check.config.enabled = True
    health_check.config.ping_interval = 60  # 60 seconds
    health_check.config.ping_on_backup_start = True
    health_check.config.ping_on_backup_success = True
    health_check.config.ping_on_backup_failure = True
    print(f"   Enabled: {health_check.config.enabled}")
    print(f"   Interval: {health_check.config.ping_interval}s")
    print(f"   Ping on backup start: {health_check.config.ping_on_backup_start}")
    print(f"   Ping on backup success: {health_check.config.ping_on_backup_success}")
    print(f"   Ping on backup failure: {health_check.config.ping_on_backup_failure}")
    
    # Note: Actual pinging would require valid endpoints
    print("\n7. Health Check Pinging")
    print("   Note: Actual pinging requires valid endpoints")
    print("   Use health_check.ping_health_check(status) to ping services")
    print("   Use health_check.notify_backup_success(repo_id) for backup events")
    
    # Demonstrate event notifications (without actually sending)
    print("\n8. Event Notification Methods")
    print("   - notify_backup_start(repository_id)")
    print("   - notify_backup_success(repository_id, duration)")
    print("   - notify_backup_failure(repository_id, error)")
    print("   - ping_health_check(status, message, logs)")
    
    # Periodic pinging
    print("\n9. Periodic Pinging")
    print("   Note: Periodic pinging runs in background thread")
    print("   Use health_check.start_periodic_ping() to start")
    print("   Use health_check.stop_periodic_ping() to stop")
    print("   Skipping actual start (requires valid endpoints)")
    
    # Cleanup
    health_check.shutdown()
    print("\n✓ Health check integration shutdown complete")


def demo_integration_with_monitoring():
    """Demonstrate integration with monitoring service"""
    print("\n" + "=" * 70)
    print("Integration with Monitoring Service")
    print("=" * 70)
    
    print("\n1. Integration Points")
    print("   Webhook and health check integrations can be used with:")
    print("   - MonitoringService for centralized event handling")
    print("   - NotificationService for notification delivery")
    print("   - BackupHistory for historical event tracking")
    
    print("\n2. Example Integration Flow")
    print("   a. Backup operation starts")
    print("   b. MonitoringService receives backup event")
    print("   c. WebhookHandler sends webhook notification")
    print("   d. HealthCheckIntegration pings health check services")
    print("   e. NotificationService sends desktop/email notifications")
    
    print("\n3. Configuration Best Practices")
    print("   - Enable webhooks only for critical events")
    print("   - Use health checks for periodic status monitoring")
    print("   - Configure appropriate retry settings for reliability")
    print("   - Use SSL verification for security")
    print("   - Set reasonable timeouts to avoid blocking")
    
    print("\n4. Error Handling")
    print("   - Both integrations handle failures gracefully")
    print("   - Webhook failures don't block backup operations")
    print("   - Health check failures are logged but don't affect backups")
    print("   - Retry logic with exponential backoff for transient failures")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("TimeLocker External Integration Demo")
    print("=" * 70)
    print("\nThis demo showcases optional external integration capabilities")
    print("for power users who want to integrate TimeLocker with external")
    print("monitoring and notification systems.")
    
    try:
        # Run demos
        demo_webhook_integration()
        demo_health_check_integration()
        demo_integration_with_monitoring()
        
        print("\n" + "=" * 70)
        print("Demo Complete!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("1. Webhook integration provides flexible event notifications")
        print("2. Health check integration enables external monitoring")
        print("3. Both integrations are optional and designed for power users")
        print("4. Robust error handling ensures backup operations aren't affected")
        print("5. Configuration is persistent and easily manageable")
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
