#!/usr/bin/env python3
"""
Demo script showing the enhanced SecurityService functionality
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from TimeLocker.security import SecurityService, CredentialManager


def main():
    """Demonstrate the enhanced SecurityService methods"""
    print("=== TimeLocker SecurityService Enhanced Methods Demo ===\n")

    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Initialize credential manager and security service
        credential_manager = Mock(spec=CredentialManager)
        credential_manager.lock.return_value = True

        security_service = SecurityService(
                credential_manager=credential_manager,
                config_dir=temp_path / "security"
        )

        print("1. Testing audit_backup_operation()")
        print("-" * 40)

        # Mock repository for demo
        mock_repository = Mock()
        mock_repository._location = "/backup/repo"
        mock_repository.id = "demo_repo"

        # Audit a backup operation
        security_service.audit_backup_operation(
                repository=mock_repository,
                operation_type="full",
                targets=["/home/user/documents", "/home/user/photos"],
                success=True,
                metadata={"duration": 120, "size": "2.5GB", "files_backed_up": 1500}
        )
        print("✓ Backup operation audited successfully")

        print("\n2. Testing audit_restore_operation()")
        print("-" * 40)

        # Audit a restore operation
        security_service.audit_restore_operation(
                repository=mock_repository,
                snapshot_id="snapshot_abc123",
                target_path="/restore/location",
                success=True,
                metadata={"files_restored": 1200, "duration": 85}
        )
        print("✓ Restore operation audited successfully")

        print("\n3. Testing validate_security_config()")
        print("-" * 40)

        # Test with valid configuration
        valid_config = {
                "encryption_enabled":  True,
                "audit_logging":       True,
                "credential_timeout":  3600,
                "max_failed_attempts": 3,
                "lockout_duration":    300
        }

        result = security_service.validate_security_config(valid_config)
        print(f"✓ Valid config validation: {result['valid']}")
        print(f"  Issues: {len(result['issues'])}")
        print(f"  Warnings: {len(result['warnings'])}")
        print(f"  Recommendations: {len(result['recommendations'])}")

        # Test with invalid configuration
        invalid_config = {
                "encryption_enabled":  False,
                "credential_timeout":  30,  # Too short
                "max_failed_attempts": 0  # Invalid
        }

        result = security_service.validate_security_config(invalid_config)
        print(f"✓ Invalid config validation: {result['valid']}")
        print(f"  Issues found: {result['issues']}")

        print("\n4. Testing emergency_lockdown()")
        print("-" * 40)

        # Trigger emergency lockdown
        lockdown_result = security_service.emergency_lockdown(
                reason="Suspicious activity detected",
                metadata={"source": "intrusion_detection", "severity": "high"}
        )
        print(f"✓ Emergency lockdown executed: {lockdown_result}")

        # Check if lockdown marker file was created
        lockdown_file = security_service.config_dir / "emergency_lockdown.marker"
        print(f"✓ Lockdown marker file created: {lockdown_file.exists()}")

        print("\n5. Testing audit_integrity_check()")
        print("-" * 40)

        # Audit an integrity check with successful results
        check_results = {
                "errors_found":   0,
                "warnings_found": 2,
                "items_checked":  5000,
                "check_duration": 45.5,
                "warnings":       ["Minor timestamp inconsistency", "Metadata cache outdated"]
        }

        security_service.audit_integrity_check(
                repository=mock_repository,
                check_type="full",
                success=True,
                results=check_results
        )
        print("✓ Successful integrity check audited")

        # Audit an integrity check with errors
        error_results = {
                "errors_found":   3,
                "warnings_found": 1,
                "items_checked":  2500,
                "check_duration": 30.2,
                "errors":         ["Corrupted block detected", "Missing metadata", "Invalid checksum"]
        }

        security_service.audit_integrity_check(
                repository=mock_repository,
                check_type="snapshot",
                success=False,
                results=error_results
        )
        print("✓ Failed integrity check audited")

        print("\n6. Viewing Security Summary")
        print("-" * 40)

        # Get security summary
        summary = security_service.get_security_summary(days=1)
        print(f"✓ Security events in last day: {summary['total_events']}")
        print(f"✓ Event types: {list(summary['events_by_type'].keys())}")
        print(f"✓ Security levels: {list(summary['events_by_level'].keys())}")

        print("\n7. Viewing Audit Log")
        print("-" * 40)

        # Show recent audit log entries
        if security_service.audit_log_file.exists():
            with open(security_service.audit_log_file, 'r') as f:
                lines = f.readlines()
                print(f"✓ Total audit log entries: {len([l for l in lines if not l.startswith('#')])}")
                print("✓ Recent entries:")
                for line in lines[-5:]:  # Show last 5 entries
                    if not line.startswith('#') and line.strip():
                        parts = line.strip().split('|')
                        if len(parts) >= 3:
                            print(f"  - {parts[1]} ({parts[2]}): {parts[3][:50]}...")

        print(f"\n=== Demo completed successfully! ===")
        print(f"Security configuration directory: {security_service.config_dir}")
        print(f"Audit log file: {security_service.audit_log_file}")


if __name__ == "__main__":
    main()
