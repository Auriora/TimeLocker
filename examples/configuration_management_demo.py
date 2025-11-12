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

Configuration Management Demo

This example demonstrates the configuration management capabilities
of the scheduling system, including:
- Loading and saving configurations
- Platform preference management
- Configuration migration and upgrade
- Configuration validation
- Import/export functionality
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.scheduling import (
    SchedulingConfiguration,
    ConfigurationManager,
    ConfigurationMigrator,
    RetryConfig,
    MonitoringConfig,
    CURRENT_CONFIG_VERSION
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_basic_configuration():
    """Demonstrate basic configuration operations."""
    print_section("Basic Configuration Operations")
    
    # Create default configuration
    config = SchedulingConfiguration()
    
    print("Default Configuration:")
    print(f"  Config Version: {config.config_version}")
    print(f"  Audit Retention Days: {config.audit_retention_days}")
    print(f"  Max Concurrent Executions: {config.max_concurrent_executions}")
    print(f"  Execution Timeout Minutes: {config.execution_timeout_minutes}")
    print(f"  Platform Preferences: {config.platform_preferences}")
    
    # Validate configuration
    validation_result = config.validate()
    print(f"\nValidation Result:")
    print(f"  Is Valid: {validation_result.is_valid}")
    if validation_result.errors:
        print(f"  Errors: {validation_result.errors}")
    if validation_result.warnings:
        print(f"  Warnings: {validation_result.warnings}")


def demo_platform_preferences():
    """Demonstrate platform preference management."""
    print_section("Platform Preference Management")
    
    config = SchedulingConfiguration()
    
    # Set platform preferences
    print("Setting platform preferences...")
    config.set_platform_preference('linux', 'systemd')
    config.set_platform_preference('darwin', 'launchd')
    config.set_platform_preference('windows', 'windows_task_scheduler')
    
    print(f"Platform Preferences: {config.platform_preferences}")
    
    # Get platform preference
    linux_pref = config.get_platform_preference('linux')
    print(f"\nLinux Preference: {linux_pref}")
    
    # Clear platform preference
    config.clear_platform_preference('linux')
    print(f"After clearing Linux preference: {config.platform_preferences}")


def demo_configuration_manager():
    """Demonstrate configuration manager operations."""
    print_section("Configuration Manager Operations")
    
    # Create temporary config directory
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Initialize configuration manager
        config_manager = ConfigurationManager(config_dir=temp_dir)
        
        print(f"Configuration Directory: {config_manager.config_dir}")
        print(f"Configuration Path: {config_manager.config_path}")
        
        # Load configuration (creates default if not exists)
        print("\nLoading configuration...")
        config = config_manager.load_configuration()
        print(f"  Loaded config version: {config.config_version}")
        
        # Modify configuration
        print("\nModifying configuration...")
        config.max_concurrent_executions = 5
        config.execution_timeout_minutes = 90
        config.set_platform_preference('linux', 'systemd')
        
        # Save configuration
        print("Saving configuration...")
        config_manager.save_configuration(config)
        print("  Configuration saved successfully")
        
        # Get configuration info
        print("\nConfiguration Info:")
        info = config_manager.get_configuration_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # Export configuration
        export_path = temp_dir / "exported_config.json"
        print(f"\nExporting configuration to {export_path}...")
        success = config_manager.export_configuration(export_path)
        print(f"  Export successful: {success}")
        
        # Reset to defaults
        print("\nResetting to defaults...")
        default_config = config_manager.reset_to_defaults(create_backup=True)
        print(f"  Reset complete. Max concurrent: {default_config.max_concurrent_executions}")
        
        # Import configuration
        print(f"\nImporting configuration from {export_path}...")
        imported_config = config_manager.import_configuration(export_path)
        print(f"  Import complete. Max concurrent: {imported_config.max_concurrent_executions}")
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_configuration_migration():
    """Demonstrate configuration migration."""
    print_section("Configuration Migration")
    
    import tempfile
    import json
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create an old configuration file (version 0.0.0)
        old_config_path = temp_dir / "old_config.json"
        old_config_data = {
            "config_version": "0.0.0",
            "audit_retention_days": 180,
            "max_concurrent_executions": 2
            # Missing many fields that exist in v1.0.0
        }
        
        with open(old_config_path, 'w') as f:
            json.dump(old_config_data, f, indent=2)
        
        print(f"Created old configuration (v0.0.0) at {old_config_path}")
        
        # Check if migration is needed
        with open(old_config_path, 'r') as f:
            config_data = json.load(f)
        
        needs_migration = ConfigurationMigrator.needs_migration(config_data)
        print(f"\nNeeds Migration: {needs_migration}")
        
        # Migrate configuration
        print("\nMigrating configuration...")
        migrated_config = ConfigurationMigrator.migrate_configuration(old_config_path)
        
        print(f"Migration complete!")
        print(f"  New version: {migrated_config.config_version}")
        print(f"  Audit retention days: {migrated_config.audit_retention_days}")
        print(f"  Max concurrent executions: {migrated_config.max_concurrent_executions}")
        print(f"  Execution timeout minutes: {migrated_config.execution_timeout_minutes}")
        
        # Check for backup
        backup_files = list(temp_dir.glob("*_backup_*.json"))
        if backup_files:
            print(f"\nBackup created: {backup_files[0].name}")
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_configuration_upgrade():
    """Demonstrate configuration upgrade."""
    print_section("Configuration Upgrade")
    
    import tempfile
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create a basic configuration
        config = SchedulingConfiguration()
        config.max_concurrent_executions = 2
        
        config_path = temp_dir / "config.json"
        config.save_to_file(config_path)
        
        print(f"Created configuration at {config_path}")
        print(f"  Max concurrent executions: {config.max_concurrent_executions}")
        print(f"  Platform preferences: {config.platform_preferences}")
        
        # Upgrade configuration
        print("\nUpgrading configuration...")
        upgraded_config = ConfigurationMigrator.upgrade_configuration(config_path)
        
        print(f"Upgrade complete!")
        print(f"  Max concurrent executions: {upgraded_config.max_concurrent_executions}")
        print(f"  Platform preferences: {upgraded_config.platform_preferences}")
        print(f"  (Platform-specific optimizations applied)")
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_custom_configuration():
    """Demonstrate custom configuration creation."""
    print_section("Custom Configuration")
    
    # Create custom retry configuration
    custom_retry = RetryConfig(
        max_attempts=5,
        initial_delay_minutes=10,
        backoff_multiplier=1.5,
        max_delay_minutes=120
    )
    
    # Create custom monitoring configuration
    custom_monitoring = MonitoringConfig(
        webhook_url="https://example.com/webhook",
        health_check_url="https://example.com/health",
        notification_on_success=True,
        notification_on_failure=True,
        notification_on_retry=True
    )
    
    # Create custom configuration
    custom_config = SchedulingConfiguration(
        platform_preferences={
            'linux': 'systemd',
            'darwin': 'launchd',
            'windows': 'windows_task_scheduler'
        },
        default_retry_config=custom_retry,
        default_monitoring_config=custom_monitoring,
        audit_retention_days=730,  # 2 years
        max_concurrent_executions=8,
        execution_timeout_minutes=120,
        credential_store_config={
            'encryption_enabled': True,
            'key_rotation_days': 90
        }
    )
    
    print("Custom Configuration Created:")
    print(f"  Audit Retention: {custom_config.audit_retention_days} days")
    print(f"  Max Concurrent: {custom_config.max_concurrent_executions}")
    print(f"  Execution Timeout: {custom_config.execution_timeout_minutes} minutes")
    print(f"  Retry Max Attempts: {custom_config.default_retry_config.max_attempts}")
    print(f"  Monitoring Webhook: {custom_config.default_monitoring_config.webhook_url}")
    
    # Validate custom configuration
    validation_result = custom_config.validate()
    print(f"\nValidation Result:")
    print(f"  Is Valid: {validation_result.is_valid}")
    if validation_result.warnings:
        print(f"  Warnings:")
        for warning in validation_result.warnings:
            print(f"    - {warning}")


def demo_merge_with_defaults():
    """Demonstrate merging configuration with defaults."""
    print_section("Merge with Defaults")
    
    # Create minimal configuration
    minimal_config = SchedulingConfiguration(
        audit_retention_days=90,
        max_concurrent_executions=4
    )
    
    print("Minimal Configuration:")
    print(f"  Audit Retention: {minimal_config.audit_retention_days}")
    print(f"  Max Concurrent: {minimal_config.max_concurrent_executions}")
    print(f"  Platform Preferences: {minimal_config.platform_preferences}")
    print(f"  Retry Config: {minimal_config.default_retry_config}")
    
    # Merge with defaults
    print("\nMerging with defaults...")
    minimal_config.merge_with_defaults()
    
    print("After Merge:")
    print(f"  Audit Retention: {minimal_config.audit_retention_days}")
    print(f"  Max Concurrent: {minimal_config.max_concurrent_executions}")
    print(f"  Platform Preferences: {minimal_config.platform_preferences}")
    print(f"  Retry Config: {minimal_config.default_retry_config}")


def main():
    """Run all configuration management demos."""
    print("\n" + "=" * 70)
    print("  TimeLocker Scheduling Configuration Management Demo")
    print("=" * 70)
    print(f"\nCurrent Configuration Version: {CURRENT_CONFIG_VERSION}")
    print(f"Demo Time: {datetime.utcnow().isoformat()}")
    
    try:
        # Run demos
        demo_basic_configuration()
        demo_platform_preferences()
        demo_configuration_manager()
        demo_configuration_migration()
        demo_configuration_upgrade()
        demo_custom_configuration()
        demo_merge_with_defaults()
        
        print_section("Demo Complete")
        print("All configuration management features demonstrated successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
