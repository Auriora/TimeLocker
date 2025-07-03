#!/usr/bin/env python3
"""
TimeLocker Integrated Backup Example

This example demonstrates the integrated security, monitoring, and configuration
features of TimeLocker, showing how all components work together to provide
a comprehensive backup solution.

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

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add the src directory to the path so we can import TimeLocker
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker import (
    IntegrationService,
    CredentialManager
)
from TimeLocker.config import ConfigurationModule
from TimeLocker.restic.Repositories.local import LocalResticRepository

# Configure logging
logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main example function demonstrating integrated TimeLocker functionality"""

    print("TimeLocker Integrated Backup Example")
    print("=" * 50)

    # Setup paths
    config_dir = Path.home() / ".timelocker_example"
    repo_path = config_dir / "example_repository"
    backup_source = Path.home() / "Documents"  # Example backup source

    try:
        # 1. Initialize Integration Service
        print("\n1. Initializing TimeLocker Integration Service...")
        integration_service = IntegrationService(config_dir)

        # 2. Setup Credential Manager
        print("2. Setting up credential management...")
        credential_manager = CredentialManager(config_dir / "credentials")

        # For this example, we'll use a simple password
        master_password = "example_master_password_123"
        if not credential_manager.unlock(master_password):
            print("   Creating new credential store...")
            credential_manager.unlock(master_password)

        # Initialize security service
        integration_service.initialize_security(credential_manager)

        # 3. Configure System Settings
        print("3. Configuring system settings...")

        # Configure backup settings
        integration_service.config_manager.update_section(
                "backup",
                {
                        "compression":         "auto",
                        "exclude_caches":      True,
                        "check_before_backup": True,
                        "verify_after_backup": True
                }
        )

        # Configure notification settings
        integration_service.config_manager.update_section(
                "notifications",
                {
                        "enabled":                True,
                        "desktop_enabled":        True,
                        "email_enabled":          False,  # Disable email for example
                        "notify_on_success":      True,
                        "notify_on_error":        True,
                        "min_operation_duration": 5  # Notify for operations > 5 seconds
                }
        )

        # Configure security settings
        integration_service.config_manager.update_section(
                "security",
                {
                        "encryption_enabled": True,
                        "audit_logging":      True,
                        "credential_timeout": 3600
                }
        )

        print("   Configuration completed successfully")

        # 4. Setup Repository
        print("4. Setting up backup repository...")

        # Create repository directory
        repo_path.mkdir(parents=True, exist_ok=True)

        # Create repository instance
        repository = LocalResticRepository(
                location=str(repo_path),
                credential_manager=credential_manager
        )

        # Repository password for encryption
        repo_password = "example_repo_password_456"

        # Store repository credentials
        credential_manager.store_credential(
                "example_repository",
                {
                        "password": repo_password,
                        "location": str(repo_path),
                        "type":     "local"
                }
        )

        # Initialize repository if not already done
        if not repository.is_repository_initialized():
            print("   Initializing new repository...")
            repository.setup_repository_with_credentials(repo_password)
        else:
            print("   Using existing repository")

        # 5. Verify Security
        print("5. Verifying repository security...")

        # Verify encryption status
        encryption_status = integration_service.security_service.verify_repository_encryption(repository)
        print(f"   Repository encrypted: {encryption_status.is_encrypted}")
        print(f"   Encryption algorithm: {encryption_status.encryption_algorithm}")

        # Validate repository integrity
        integrity_valid = integration_service.security_service.validate_backup_integrity(repository)
        print(f"   Repository integrity: {'VALID' if integrity_valid else 'INVALID'}")

        # 6. Execute Backup Operation
        print("6. Executing backup operation...")

        if not backup_source.exists():
            print(f"   Warning: Backup source {backup_source} does not exist")
            print("   Creating example files for demonstration...")
            backup_source.mkdir(parents=True, exist_ok=True)
            (backup_source / "example_file.txt").write_text("This is an example file for backup.")

        # Create mock backup target for demonstration
        class MockBackupTarget:
            def __init__(self, paths):
                self.paths = paths

        backup_target = MockBackupTarget([str(backup_source)])

        # Execute integrated backup
        print(f"   Starting backup of {backup_source}...")
        backup_result = integration_service.execute_backup(
                repository=repository,
                backup_target=backup_target,
                operation_id=f"example_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        print(f"   Backup completed with status: {backup_result.status.value}")
        print(f"   Message: {backup_result.message}")

        # 7. Display System Status
        print("7. System status summary...")

        system_status = integration_service.get_system_status()

        print(f"   Active components: {len([c for c in system_status['components'].values() if c == 'active'])}")
        print(f"   Current operations: {system_status['current_operations']}")
        print(f"   Total configuration settings: {system_status['configuration_summary']['total_settings']}")

        if 'security_summary' in system_status:
            security_summary = system_status['security_summary']
            print(f"   Security events (last 7 days): {security_summary['total_events']}")

        if 'status_summary' in system_status:
            status_summary = system_status['status_summary']
            print(f"   Operations (last 7 days): {status_summary['total_operations']}")

        # 8. Display Recent Security Events
        print("8. Recent security events...")

        if integration_service.security_service:
            security_summary = integration_service.security_service.get_security_summary(days=1)

            print(f"   Total events today: {security_summary['total_events']}")

            if security_summary['events_by_type']:
                print("   Event types:")
                for event_type, count in security_summary['events_by_type'].items():
                    print(f"     - {event_type}: {count}")

        # 9. Test Notifications (if enabled)
        print("9. Testing notification system...")

        try:
            test_results = integration_service.notification_service.test_notifications()
            for notification_type, success in test_results.items():
                status = "SUCCESS" if success else "FAILED"
                print(f"   {notification_type.title()} notifications: {status}")
        except Exception as e:
            print(f"   Notification test failed: {e}")

        print("\n" + "=" * 50)
        print("TimeLocker integrated backup example completed successfully!")
        print(f"Configuration stored in: {config_dir}")
        print(f"Repository located at: {repo_path}")
        print("\nKey features demonstrated:")
        print("- Integrated security with encryption verification")
        print("- Comprehensive status reporting and monitoring")
        print("- Centralized configuration management")
        print("- Security event logging and audit trails")
        print("- Notification system integration")
        print("- End-to-end operation tracking")

    except Exception as e:
        logger.error(f"Example failed: {e}")
        print(f"\nError: {e}")
        print("Please check the logs for more details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
