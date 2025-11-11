"""
Integration tests for configuration management end-to-end workflows.

Tests complete configuration update workflows with locking and backup,
migration scenarios, and concurrent access scenarios.
"""

import json
import time
import tempfile
import threading
import multiprocessing
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pytest

from src.TimeLocker.config.configuration_module import ConfigurationModule
from src.TimeLocker.config.configuration_lock_manager import ConfigurationLockManager
from src.TimeLocker.config.configuration_backup_manager import ConfigurationBackupManager, BackupReason
from src.TimeLocker.config.configuration_watcher import ConfigurationWatcher
from src.TimeLocker.config.configuration_validator import ConfigurationValidator
from src.TimeLocker.config.configuration_migrator import ConfigurationMigrator
from src.TimeLocker.interfaces.exceptions import (
    ConfigurationError,
    ConfigurationLockError,
    ConfigurationBackupError
)


class TestConfigurationIntegrationWorkflows:
    """Integration tests for configuration management workflows"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.config_module = ConfigurationModule(self.config_dir)
        self.lock_manager = ConfigurationLockManager(self.config_dir / "locks")
        self.backup_manager = ConfigurationBackupManager(
            self.config_dir / "backups",
            ConfigurationValidator()
        )
        self.watcher = ConfigurationWatcher(
            self.config_module.config_file,
            polling_interval=0.1
        )
        
        # Test configuration data
        self.test_config = {
            "general": {
                "app_name": "TimeLocker",
                "version": "1.0.0",
                "log_level": "INFO"
            },
            "backup": {
                "compression": "auto",
                "exclude_caches": True
            },
            "repositories": {
                "default": {
                    "location": "/backup/repo",
                    "password": "secret123"
                }
            }
        }

    def teardown_method(self):
        """Cleanup test environment"""
        if self.watcher.is_watching():
            self.watcher.stop_watching()
        
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.config
    @pytest.mark.integration
    def test_complete_configuration_update_workflow(self):
        """Test complete configuration update workflow with locking and backup"""
        # Step 1: Initialize configuration
        for section, data in self.test_config.items():
            self.config_module.update_section(section, data)
        
        # Step 2: Acquire lock for update
        config_resource = Path("configuration_update")
        lock_acquired = self.lock_manager.acquire_lock(config_resource, timeout=10)
        assert lock_acquired is True
        
        try:
            # Step 3: Create backup before update
            backup_id = self.backup_manager.create_backup(
                self.config_module.config_file,
                BackupReason.PRE_UPDATE,
                tags=["integration_test", "pre_update"]
            )
            assert backup_id is not None
            
            # Step 4: Perform configuration updates
            updates = {
                "general": {
                    "version": "2.0.0",
                    "log_level": "DEBUG",
                    "new_feature": True
                },
                "backup": {
                    "compression": "gzip",
                    "exclude_caches": False,
                    "max_backup_size": "10GB"
                }
            }
            
            for section, data in updates.items():
                self.config_module.update_section(section, data)
            
            # Step 5: Validate updated configuration
            validation_result = self.config_module.validate_current_configuration()
            assert validation_result.is_valid
            
            # Step 6: Verify changes were applied
            updated_general = self.config_module.get_section("general")
            assert updated_general["version"] == "2.0.0"
            assert updated_general["log_level"] == "DEBUG"
            # Note: new_feature is filtered out as it's not a valid GeneralConfig field
            
            updated_backup = self.config_module.get_section("backup")
            assert updated_backup["compression"] == "gzip"
            assert updated_backup["exclude_caches"] is False
            
            # Step 7: Create post-update backup
            post_backup_id = self.backup_manager.create_backup(
                self.config_module.config_file,
                BackupReason.MANUAL,
                tags=["integration_test", "post_update"]
            )
            
            # Step 8: Compare backups to verify changes
            comparison = self.backup_manager.compare_backups(backup_id, post_backup_id)
            assert not comparison['identical']
            assert len(comparison['differences']) > 0
            
        finally:
            # Step 9: Release lock
            self.lock_manager.release_lock(config_resource)
        
        # Verify lock was released
        assert not self.lock_manager.is_locked(config_resource)

    @pytest.mark.config
    @pytest.mark.integration
    def test_configuration_migration_workflow(self):
        """Test configuration migration with enhanced backup and validation"""
        # Step 1: Create legacy configuration format
        legacy_config = {
            "version": "0.9.0",
            "settings": {
                "app_name": "TimeLocker",
                "debug": True,
                "backup_compression": "auto"
            },
            "repos": [
                {
                    "name": "default",
                    "path": "/old/backup/path",
                    "password": "old_password"
                }
            ]
        }
        
        legacy_file = self.config_dir / "legacy_config.json"
        with open(legacy_file, 'w') as f:
            json.dump(legacy_config, f, indent=2)
        
        # Step 2: Create backup before migration
        pre_migration_backup = self.backup_manager.create_backup(
            legacy_file,
            BackupReason.PRE_MIGRATION,
            tags=["migration", "legacy_backup"]
        )
        
        # Step 3: Initialize migrator and perform migration
        migrator = ConfigurationMigrator(self.config_dir)
        
        # Mock migration rules for testing
        migration_rules = {
            "0.9.0_to_1.0.0": {
                "version_mapping": {
                    "settings.app_name": "general.app_name",
                    "settings.debug": "general.log_level",
                    "settings.backup_compression": "backup.compression"
                },
                "transformations": {
                    "general.log_level": lambda x: "DEBUG" if x else "INFO",
                    "general.version": lambda x: "1.0.0"
                },
                "repository_migration": {
                    "repos": "repositories",
                    "path": "location"
                }
            }
        }
        
        with patch.object(migrator, '_get_migration_rules', return_value=migration_rules):
            # Perform migration
            migration_result = migrator.migrate_configuration(legacy_file, self.config_module.config_file)
            assert migration_result is True
        
        # Step 4: Validate migrated configuration
        migrated_config = self.config_module.get_config()
        
        # Verify structure migration
        assert hasattr(migrated_config, 'general')
        assert hasattr(migrated_config, 'backup')
        
        # Verify data migration
        assert migrated_config.general.app_name == "TimeLocker"
        assert migrated_config.general.version == "1.0.0"
        assert migrated_config.backup.compression == "auto"
        
        # Step 5: Create post-migration backup
        post_migration_backup = self.backup_manager.create_backup(
            self.config_module.config_file,
            BackupReason.MANUAL,
            tags=["migration", "post_migration"]
        )
        
        # Step 6: Verify migration by comparing backups
        comparison = self.backup_manager.compare_backups(
            pre_migration_backup,
            post_migration_backup
        )
        assert not comparison['identical']
        
        # Step 7: Test rollback capability
        rollback_result = self.backup_manager.restore_backup(
            pre_migration_backup,
            legacy_file
        )
        assert rollback_result is True

    @pytest.mark.config
    @pytest.mark.integration
    def test_concurrent_access_workflow(self):
        """Test concurrent access scenarios with multiple processes"""
        # Initialize shared configuration
        for section, data in self.test_config.items():
            self.config_module.update_section(section, data)
        
        results = []
        errors = []
        
        def concurrent_update_worker(worker_id, update_data):
            """Worker function for concurrent updates"""
            try:
                # Create separate instances for each worker
                worker_config = ConfigurationModule(self.config_dir)
                worker_lock_manager = ConfigurationLockManager(self.config_dir / "locks")
                worker_backup_manager = ConfigurationBackupManager(
                    self.config_dir / "backups",
                    ConfigurationValidator()
                )
                
                # Attempt to acquire lock
                config_resource = Path("concurrent_test")
                lock_acquired = worker_lock_manager.acquire_lock(config_resource, timeout=5)
                
                if lock_acquired:
                    try:
                        # Create backup
                        backup_id = worker_backup_manager.create_backup(
                            worker_config.config_file,
                            BackupReason.AUTOMATIC,
                            tags=[f"worker_{worker_id}"]
                        )
                        
                        # Perform update
                        worker_config.update_section("general", update_data)
                        
                        # Simulate some work
                        time.sleep(0.1)
                        
                        # Validate configuration
                        validation_result = worker_config.validate_current_configuration()
                        
                        results.append({
                            'worker_id': worker_id,
                            'success': True,
                            'backup_id': backup_id,
                            'validation_valid': validation_result.is_valid
                        })
                        
                    finally:
                        worker_lock_manager.release_lock(config_resource)
                else:
                    results.append({
                        'worker_id': worker_id,
                        'success': False,
                        'reason': 'lock_timeout'
                    })
                    
            except Exception as e:
                errors.append({
                    'worker_id': worker_id,
                    'error': str(e)
                })
        
        # Start multiple concurrent workers
        threads = []
        for i in range(5):
            update_data = {
                "app_name": f"TimeLocker_Worker_{i}",
                "version": f"1.{i}.0",
                "worker_id": i
            }
            
            thread = threading.Thread(
                target=concurrent_update_worker,
                args=(i, update_data)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all workers to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        successful_updates = [r for r in results if r.get('success', False)]
        failed_updates = [r for r in results if not r.get('success', False)]
        
        # Only one worker should succeed due to locking
        assert len(successful_updates) == 1
        assert len(failed_updates) == 4
        
        # All failures should be due to lock timeout
        for failure in failed_updates:
            assert failure['reason'] == 'lock_timeout'
        
        # No errors should occur
        assert len(errors) == 0
        
        # Verify final configuration state
        final_config = self.config_module.get_section("general")
        successful_worker = successful_updates[0]
        expected_worker_id = successful_worker['worker_id']
        assert final_config["app_name"] == f"TimeLocker_Worker_{expected_worker_id}"

    @pytest.mark.config
    @pytest.mark.integration
    def test_configuration_watching_integration(self):
        """Test configuration watching integration with updates"""
        # Setup change tracking
        change_events = []
        
        def track_changes(event):
            change_events.append({
                'section': event.section,
                'key': event.key,
                'old_value': event.old_value,
                'new_value': event.new_value,
                'timestamp': event.timestamp
            })
        
        # Subscribe to configuration changes
        watch_id = self.watcher.watch_section("general", track_changes)
        
        # Start watching
        self.watcher.start_watching()
        time.sleep(0.1)  # Allow watcher to initialize
        
        try:
            # Perform configuration updates
            self.config_module.update_section("general", {
                "app_name": "TimeLocker",
                "version": "1.0.0"
            })
            
            # Wait for change detection
            time.sleep(0.3)
            
            # Update again
            self.config_module.update_section("general", {
                "app_name": "TimeLocker Updated",
                "version": "2.0.0",
                "new_feature": True
            })
            
            # Wait for change detection
            time.sleep(0.3)
            
            # Verify changes were detected
            assert len(change_events) > 0
            
            # Check for specific changes
            version_changes = [
                e for e in change_events 
                if e.get('key') and 'version' in e['key']
            ]
            assert len(version_changes) > 0
            
        finally:
            self.watcher.unwatch(watch_id)

    @pytest.mark.config
    @pytest.mark.integration
    def test_error_recovery_workflow(self):
        """Test error recovery workflow with backup restoration"""
        # Step 1: Create initial valid configuration
        for section, data in self.test_config.items():
            self.config_module.update_section(section, data)
        
        # Step 2: Create backup of valid configuration
        good_backup_id = self.backup_manager.create_backup(
            self.config_module.config_file,
            BackupReason.MANUAL,
            tags=["good_state", "recovery_test"]
        )
        
        # Step 3: Simulate configuration corruption
        corrupted_config = {
            "invalid_structure": True,
            "missing_required_fields": "yes",
            "general": "this should be an object, not a string"
        }
        
        with open(self.config_module.config_file, 'w') as f:
            json.dump(corrupted_config, f)
        
        # Step 4: Detect corruption through validation
        try:
            validation_result = self.config_module.validate_current_configuration()
            assert not validation_result.is_valid
        except Exception:
            # Configuration is so corrupted it can't even be loaded
            pass
        
        # Step 5: Perform recovery by restoring from backup
        recovery_successful = self.backup_manager.restore_backup(
            good_backup_id,
            self.config_module.config_file
        )
        assert recovery_successful is True
        
        # Step 6: Verify recovery
        # Reload configuration module to pick up restored file
        recovered_config_module = ConfigurationModule(self.config_dir)
        validation_result = recovered_config_module.validate_current_configuration()
        assert validation_result.is_valid
        
        # Verify data integrity
        recovered_general = recovered_config_module.get_section("general")
        assert recovered_general["app_name"] == "TimeLocker"
        assert recovered_general["version"] == "1.0.0"

    @pytest.mark.config
    @pytest.mark.integration
    def test_atomic_update_workflow(self):
        """Test atomic update workflow with rollback on failure"""
        # Initialize configuration
        for section, data in self.test_config.items():
            self.config_module.update_section(section, data)
        
        # Create backup before atomic update
        pre_update_backup = self.backup_manager.create_backup(
            self.config_module.config_file,
            BackupReason.PRE_UPDATE,
            tags=["atomic_test"]
        )
        
        # Prepare atomic updates (mix of valid and invalid)
        atomic_updates = {
            "general": {
                "version": "2.0.0",
                "log_level": "DEBUG"
            },
            "backup": {
                "compression": "gzip",
                "invalid_field": "this_should_cause_validation_error"
            },
            "new_section": {
                "new_key": "new_value"
            }
        }
        
        # Mock validation to fail for testing rollback
        original_validate = self.config_module.validate_current_configuration
        
        def mock_validate():
            result = original_validate()
            if "invalid_field" in str(self.config_module.config_file.read_text()):
                result.is_valid = False
                result.errors.append("Invalid field detected")
            return result
        
        with patch.object(self.config_module, 'validate_current_configuration', mock_validate):
            # Attempt atomic update (should fail and rollback)
            try:
                # Simulate atomic update process
                temp_config = self.config_module.config_file.with_suffix('.tmp')
                
                # Load current config
                current_config = {}
                if self.config_module.config_file.exists():
                    with open(self.config_module.config_file, 'r') as f:
                        current_config = json.load(f)
                
                # Apply updates
                for section, updates in atomic_updates.items():
                    if section in current_config:
                        current_config[section].update(updates)
                    else:
                        current_config[section] = updates
                
                # Write to temporary file
                with open(temp_config, 'w') as f:
                    json.dump(current_config, f, indent=2)
                
                # Validate temporary config
                temp_module = ConfigurationModule(temp_config.parent)
                temp_module.config_file = temp_config
                validation_result = temp_module.validate_current_configuration()
                
                if validation_result.is_valid:
                    # Move temp to actual (atomic operation)
                    temp_config.replace(self.config_module.config_file)
                else:
                    # Rollback: remove temp file and restore from backup
                    temp_config.unlink()
                    self.backup_manager.restore_backup(
                        pre_update_backup,
                        self.config_module.config_file
                    )
                    raise ConfigurationError("Atomic update failed validation")
                    
            except ConfigurationError:
                # Expected failure due to validation error
                pass
        
        # Verify rollback occurred
        final_config = self.config_module.get_section("general")
        assert final_config["version"] == "1.0.0"  # Should be original value
        
        # Verify configuration is still valid
        validation_result = self.config_module.validate_current_configuration()
        assert validation_result.is_valid

    @pytest.mark.config
    @pytest.mark.integration
    def test_backup_cleanup_integration(self):
        """Test backup cleanup integration with retention policies"""
        # Create multiple backups over time
        backup_ids = []
        
        for i in range(10):
            # Create backup with different reasons and tags
            reason = BackupReason.AUTOMATIC if i % 2 == 0 else BackupReason.MANUAL
            tags = ["cleanup_test"]
            
            if i < 3:
                tags.append("critical")  # Protected backups
            
            backup_id = self.backup_manager.create_backup(
                self.config_module.config_file,
                reason,
                tags=tags
            )
            backup_ids.append(backup_id)
            
            # Artificially age some backups
            if i < 5:
                metadata = self.backup_manager._get_backup_metadata(backup_id)
                metadata.created_at = datetime.now() - timedelta(days=i + 1)
                self.backup_manager._save_backup_metadata(metadata)
        
        # Verify all backups exist
        all_backups = self.backup_manager.list_backups()
        assert len(all_backups) == 10
        
        # Run cleanup with retention policy
        cleaned_count = self.backup_manager.cleanup_old_backups(
            keep_count=5,
            max_age_days=3
        )
        
        # Verify cleanup results
        remaining_backups = self.backup_manager.list_backups()
        
        # Should have cleaned up some backups
        assert cleaned_count > 0
        assert len(remaining_backups) < 10
        
        # Critical backups should be preserved
        critical_backups = [
            b for b in remaining_backups 
            if "critical" in b.get('tags', [])
        ]
        assert len(critical_backups) == 3  # All critical backups preserved

    @pytest.mark.config
    @pytest.mark.integration
    def test_cross_component_integration(self):
        """Test integration across all configuration components"""
        change_events = []
        
        def change_tracker(event):
            change_events.append(event)
        
        # Setup integrated workflow
        self.watcher.watch_section("general", change_tracker)
        self.watcher.start_watching()
        
        try:
            # Step 1: Acquire lock for coordinated update
            resource = Path("integration_test")
            self.lock_manager.acquire_lock(resource, timeout=10)
            
            try:
                # Step 2: Create pre-update backup
                backup_id = self.backup_manager.create_backup(
                    self.config_module.config_file,
                    BackupReason.PRE_UPDATE,
                    tags=["integration", "coordinated_update"]
                )
                
                # Step 3: Perform configuration update
                self.config_module.update_section("general", {
                    "app_name": "TimeLocker Integrated",
                    "version": "2.0.0",
                    "integration_test": True
                })
                
                # Step 4: Wait for change detection
                time.sleep(0.3)
                
                # Step 5: Validate update
                validation_result = self.config_module.validate_current_configuration()
                assert validation_result.is_valid
                
                # Step 6: Create post-update backup
                post_backup_id = self.backup_manager.create_backup(
                    self.config_module.config_file,
                    BackupReason.MANUAL,
                    tags=["integration", "post_update"]
                )
                
                # Step 7: Verify all components worked together
                
                # Lock manager: verify lock is held
                assert self.lock_manager.is_locked(resource)
                
                # Backup manager: verify backups exist and differ
                comparison = self.backup_manager.compare_backups(backup_id, post_backup_id)
                assert not comparison['identical']
                
                # Configuration module: verify changes applied
                updated_config = self.config_module.get_section("general")
                assert updated_config["app_name"] == "TimeLocker Integrated"
                # Note: integration_test is filtered out as it's not a valid GeneralConfig field
                
                # Watcher: verify changes detected
                assert len(change_events) > 0
                
            finally:
                # Step 8: Release lock
                self.lock_manager.release_lock(resource)
            
            # Verify lock released
            assert not self.lock_manager.is_locked(resource)
            
        finally:
            self.watcher.stop_watching()