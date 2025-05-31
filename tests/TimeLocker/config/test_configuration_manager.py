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
import json
from pathlib import Path

from TimeLocker.config import ConfigurationManager, ConfigSection, ConfigurationError


class TestConfigurationManager:
    """Test suite for ConfigurationManager"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_manager = ConfigurationManager(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test configuration manager initialization"""
        assert self.config_manager.config_dir.exists()
        assert self.config_manager.config_file.exists()
        assert self.config_manager.backup_dir.exists()

    def test_default_configuration(self):
        """Test default configuration values"""
        # Test general section
        general = self.config_manager.get(ConfigSection.GENERAL)
        assert general["app_name"] == "TimeLocker"
        assert general["version"] == "1.0.0"
        assert general["log_level"] == "INFO"
        assert general["max_concurrent_operations"] == 2

        # Test backup section
        backup = self.config_manager.get(ConfigSection.BACKUP)
        assert backup["compression"] == "auto"
        assert backup["exclude_caches"] is True
        assert backup["retention_keep_last"] == 10

        # Test security section
        security = self.config_manager.get(ConfigSection.SECURITY)
        assert security["encryption_enabled"] is True
        assert security["audit_logging"] is True
        assert security["credential_timeout"] == 3600

    def test_get_configuration(self):
        """Test getting configuration values"""
        # Get entire section
        general = self.config_manager.get(ConfigSection.GENERAL)
        assert isinstance(general, dict)
        assert "app_name" in general

        # Get specific key
        app_name = self.config_manager.get(ConfigSection.GENERAL, "app_name")
        assert app_name == "TimeLocker"

        # Get with default value
        nonexistent = self.config_manager.get(ConfigSection.GENERAL, "nonexistent", "default")
        assert nonexistent == "default"

        # Get from nonexistent section
        result = self.config_manager.get("nonexistent_section", "key", "default")
        assert result == "default"

    def test_set_configuration(self):
        """Test setting configuration values"""
        # Set new value
        self.config_manager.set(ConfigSection.GENERAL, "test_key", "test_value")

        # Verify value was set
        value = self.config_manager.get(ConfigSection.GENERAL, "test_key")
        assert value == "test_value"

        # Set in new section
        self.config_manager.set("new_section", "new_key", "new_value")
        value = self.config_manager.get("new_section", "new_key")
        assert value == "new_value"

    def test_update_section(self):
        """Test updating entire configuration section"""
        new_data = {
                "new_key1": "value1",
                "new_key2": "value2",
                "app_name": "Updated TimeLocker"  # Override existing
        }

        self.config_manager.update_section(ConfigSection.GENERAL, new_data)

        # Verify updates
        assert self.config_manager.get(ConfigSection.GENERAL, "new_key1") == "value1"
        assert self.config_manager.get(ConfigSection.GENERAL, "new_key2") == "value2"
        assert self.config_manager.get(ConfigSection.GENERAL, "app_name") == "Updated TimeLocker"

        # Verify existing keys are preserved
        assert self.config_manager.get(ConfigSection.GENERAL, "version") == "1.0.0"

    def test_delete_configuration(self):
        """Test deleting configuration keys"""
        # Set a test value
        self.config_manager.set(ConfigSection.GENERAL, "temp_key", "temp_value")
        assert self.config_manager.get(ConfigSection.GENERAL, "temp_key") == "temp_value"

        # Delete the value
        self.config_manager.delete(ConfigSection.GENERAL, "temp_key")
        assert self.config_manager.get(ConfigSection.GENERAL, "temp_key") is None

    def test_reset_section(self):
        """Test resetting section to defaults"""
        # Modify general section
        self.config_manager.set(ConfigSection.GENERAL, "app_name", "Modified")
        self.config_manager.set(ConfigSection.GENERAL, "custom_key", "custom_value")

        # Reset section
        self.config_manager.reset_section(ConfigSection.GENERAL)

        # Verify reset to defaults
        assert self.config_manager.get(ConfigSection.GENERAL, "app_name") == "TimeLocker"
        assert self.config_manager.get(ConfigSection.GENERAL, "custom_key") is None

    def test_reset_all(self):
        """Test resetting all configuration to defaults"""
        # Modify multiple sections
        self.config_manager.set(ConfigSection.GENERAL, "app_name", "Modified")
        self.config_manager.set(ConfigSection.BACKUP, "compression", "none")

        # Reset all
        self.config_manager.reset_all()

        # Verify reset to defaults
        assert self.config_manager.get(ConfigSection.GENERAL, "app_name") == "TimeLocker"
        assert self.config_manager.get(ConfigSection.BACKUP, "compression") == "auto"

    def test_save_and_load_configuration(self):
        """Test configuration persistence"""
        # Modify configuration
        self.config_manager.set(ConfigSection.GENERAL, "test_persistence", "persistent_value")
        self.config_manager.save_config()

        # Create new manager (simulating restart)
        new_manager = ConfigurationManager(self.temp_dir)

        # Verify configuration was loaded
        value = new_manager.get(ConfigSection.GENERAL, "test_persistence")
        assert value == "persistent_value"

    def test_export_configuration(self):
        """Test configuration export"""
        export_path = self.temp_dir / "exported_config.json"

        # Export configuration
        result = self.config_manager.export_config(export_path)
        assert result is True
        assert export_path.exists()

        # Verify exported content
        with open(export_path, 'r') as f:
            exported_data = json.load(f)

        assert ConfigSection.GENERAL.value in exported_data
        assert exported_data[ConfigSection.GENERAL.value]["app_name"] == "TimeLocker"

    def test_import_configuration(self):
        """Test configuration import"""
        # Create test configuration file
        test_config = {
                ConfigSection.GENERAL.value: {
                        "app_name":       "Imported TimeLocker",
                        "custom_setting": "imported_value"
                },
                ConfigSection.BACKUP.value:  {
                        "compression": "gzip"
                }
        }

        import_path = self.temp_dir / "import_config.json"
        with open(import_path, 'w') as f:
            json.dump(test_config, f)

        # Import configuration
        result = self.config_manager.import_config(import_path)
        assert result is True

        # Verify imported values
        assert self.config_manager.get(ConfigSection.GENERAL, "app_name") == "Imported TimeLocker"
        assert self.config_manager.get(ConfigSection.GENERAL, "custom_setting") == "imported_value"
        assert self.config_manager.get(ConfigSection.BACKUP, "compression") == "gzip"

        # Verify defaults are preserved for non-imported values
        assert self.config_manager.get(ConfigSection.GENERAL, "version") == "1.0.0"

    def test_configuration_validation(self):
        """Test configuration validation"""
        # Set invalid values
        self.config_manager.set(ConfigSection.GENERAL, "max_concurrent_operations", 0)
        self.config_manager.set(ConfigSection.BACKUP, "retention_keep_last", -1)
        self.config_manager.set(ConfigSection.SECURITY, "credential_timeout", 30)

        # Trigger validation
        self.config_manager._validate_config()

        # Verify values were corrected
        assert self.config_manager.get(ConfigSection.GENERAL, "max_concurrent_operations") == 1
        assert self.config_manager.get(ConfigSection.BACKUP, "retention_keep_last") == 1
        assert self.config_manager.get(ConfigSection.SECURITY, "credential_timeout") == 60

    def test_configuration_backup(self):
        """Test configuration backup functionality"""
        # Modify and save configuration
        self.config_manager.set(ConfigSection.GENERAL, "test_backup", "backup_test")
        self.config_manager.save_config()

        # Modify again to trigger backup
        self.config_manager.set(ConfigSection.GENERAL, "test_backup", "backup_test_2")
        self.config_manager.save_config()

        # Verify backup was created
        backups = list(self.config_manager.backup_dir.glob("config_*.json"))
        assert len(backups) >= 1

        # Verify backup content
        with open(backups[0], 'r') as f:
            backup_data = json.load(f)

        assert ConfigSection.GENERAL.value in backup_data

    def test_get_config_summary(self):
        """Test configuration summary generation"""
        summary = self.config_manager.get_config_summary()

        # Verify summary structure
        assert "config_file" in summary
        assert "last_modified" in summary
        assert "sections" in summary
        assert "total_settings" in summary

        # Verify summary content
        assert str(self.config_manager.config_file) in summary["config_file"]
        assert ConfigSection.GENERAL.value in summary["sections"]
        assert summary["total_settings"] > 0

    def test_config_section_enum(self):
        """Test ConfigSection enum usage"""
        # Test enum values
        assert ConfigSection.GENERAL.value == "general"
        assert ConfigSection.BACKUP.value == "backup"
        assert ConfigSection.SECURITY.value == "security"

        # Test using enum with configuration manager
        self.config_manager.set(ConfigSection.GENERAL, "enum_test", "enum_value")
        value = self.config_manager.get(ConfigSection.GENERAL, "enum_test")
        assert value == "enum_value"

    def test_configuration_dataclasses(self):
        """Test configuration dataclasses"""
        from TimeLocker.config.configuration_manager import BackupDefaults, RestoreDefaults, SecurityDefaults, UIDefaults

        # Test BackupDefaults
        backup_defaults = BackupDefaults()
        assert backup_defaults.compression == "auto"
        assert backup_defaults.exclude_caches is True
        assert backup_defaults.retention_keep_last == 10
        assert ".nobackup" in backup_defaults.exclude_if_present

        # Test RestoreDefaults
        restore_defaults = RestoreDefaults()
        assert restore_defaults.verify_after_restore is True
        assert restore_defaults.conflict_resolution == "prompt"

        # Test SecurityDefaults
        security_defaults = SecurityDefaults()
        assert security_defaults.encryption_enabled is True
        assert security_defaults.credential_timeout == 3600

        # Test UIDefaults
        ui_defaults = UIDefaults()
        assert ui_defaults.theme == "auto"
        assert ui_defaults.confirm_destructive_actions is True

    def test_error_handling(self):
        """Test error handling in configuration operations"""
        # Test import with invalid file
        invalid_path = self.temp_dir / "nonexistent.json"
        result = self.config_manager.import_config(invalid_path)
        assert result is False

        # Test export to invalid path
        invalid_export_path = Path("/invalid/path/config.json")
        result = self.config_manager.export_config(invalid_export_path)
        assert result is False

    def test_configuration_merging(self):
        """Test configuration merging with defaults"""
        # Test partial configuration import
        partial_config = {
                ConfigSection.GENERAL.value: {
                        "app_name": "Partial Import"
                        # Missing other general settings
                }
                # Missing other sections
        }

        import_path = self.temp_dir / "partial_config.json"
        with open(import_path, 'w') as f:
            json.dump(partial_config, f)

        # Import partial configuration
        self.config_manager.import_config(import_path)

        # Verify imported value
        assert self.config_manager.get(ConfigSection.GENERAL, "app_name") == "Partial Import"

        # Verify defaults are preserved
        assert self.config_manager.get(ConfigSection.GENERAL, "version") == "1.0.0"
        assert self.config_manager.get(ConfigSection.BACKUP, "compression") == "auto"
