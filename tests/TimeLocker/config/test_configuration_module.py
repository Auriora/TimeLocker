"""
Test suite for ConfigurationModule.

This module tests the new configuration system that replaced the old ConfigurationManager.
"""

import json
import tempfile
from pathlib import Path
import pytest

from TimeLocker.config import ConfigurationModule, ConfigurationDefaults
from TimeLocker.interfaces.exceptions import ConfigurationError


class TestConfigurationModule:
    """Test suite for ConfigurationModule"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_module = ConfigurationModule(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test ConfigurationModule initialization"""
        assert self.config_module.config_file.parent == self.temp_dir
        assert self.config_module.config_file.name == "config.json"

    def test_default_configuration(self):
        """Test default configuration values"""
        # Get complete configuration
        config = self.config_module.get_config()

        # Test general section
        assert config.general.app_name == "TimeLocker"
        assert config.general.version == "1.0.0"
        # Handle both enum and string cases for log_level
        log_level = config.general.log_level
        if hasattr(log_level, 'value'):
            assert log_level.value == "INFO"
        else:
            assert log_level == "INFO"
        assert config.general.max_concurrent_operations == 2

        # Test backup section
        # Handle both enum and string cases for compression
        compression = config.backup.compression
        if hasattr(compression, 'value'):
            assert compression.value == "auto"
        else:
            assert compression == "auto"
        assert config.backup.exclude_caches is True
        assert ".nobackup" in config.backup.exclude_if_present

        # Test security section
        assert config.security.encryption_enabled is True
        assert config.security.audit_logging is True
        assert config.security.credential_timeout == 3600

    def test_get_section(self):
        """Test getting configuration sections"""
        # Get general section
        general = self.config_module.get_section("general")
        assert isinstance(general, dict)
        assert general["app_name"] == "TimeLocker"
        assert general["version"] == "1.0.0"

        # Get backup section
        backup = self.config_module.get_section("backup")
        assert isinstance(backup, dict)
        assert backup["compression"] == "auto"
        assert backup["exclude_caches"] is True

    def test_update_section(self):
        """Test updating configuration sections"""
        # Update general section with valid fields only
        new_general = {
                "app_name": "Updated TimeLocker",
                "version":  "2.0.0"
        }
        self.config_module.update_section("general", new_general)

        # Verify updates
        general = self.config_module.get_section("general")
        assert general["app_name"] == "Updated TimeLocker"
        assert general["version"] == "2.0.0"

    def test_config_value_access(self):
        """Test dot notation configuration access"""
        # Get specific value
        app_name = self.config_module.get_config_value("general.app_name")
        assert app_name == "TimeLocker"

        # Set specific value (using valid field)
        self.config_module.set_config_value("general.version", "test_version")
        value = self.config_module.get_config_value("general.version")
        assert value == "test_version"

        # Get with default
        nonexistent = self.config_module.get_config_value("general.nonexistent", "default")
        assert nonexistent == "default"

    def test_repository_management(self):
        """Test repository configuration management"""
        # Add repository
        repo_config = {
                "name":     "test-repo",
                "location": "file:///tmp/test-repo",
                "password": "test-password"
        }
        self.config_module.add_repository(repo_config)

        # Get repository (returns RepositoryConfig object)
        repo = self.config_module.get_repository("test-repo")
        assert repo.name == "test-repo"
        assert repo.location == "file:///tmp/test-repo"

        # List repositories (returns list of dicts)
        repos = self.config_module.get_repositories()
        assert len(repos) > 0
        assert any(repo["name"] == "test-repo" for repo in repos)

        # Remove repository
        self.config_module.remove_repository("test-repo")
        repos = self.config_module.get_repositories()
        assert not any(repo["name"] == "test-repo" for repo in repos)

    def test_backup_target_management(self):
        """Test backup target configuration management"""
        # Add backup target (using correct field names)
        target_config = {
                "name":             "test-target",
                "paths":            ["/tmp/test-target"],  # paths is a list
                "description":      "Test target",
                "exclude_patterns": ["*.tmp", "*.log"]
        }
        self.config_module.add_backup_target(target_config)

        # Get backup target (returns BackupTargetConfig object)
        target = self.config_module.get_backup_target("test-target")
        assert target.name == "test-target"
        assert "/tmp/test-target" in target.paths

        # List backup targets (returns list of dicts)
        targets = self.config_module.get_backup_targets()
        assert len(targets) > 0
        assert any(target["name"] == "test-target" for target in targets)

        # Remove backup target
        self.config_module.remove_backup_target("test-target")
        targets = self.config_module.get_backup_targets()
        assert not any(target["name"] == "test-target" for target in targets)

    def test_configuration_persistence(self):
        """Test configuration save and load"""
        # Modify configuration (using valid field)
        self.config_module.set_config_value("general.version", "persistent_version")

        # Create new module instance (simulating restart)
        new_module = ConfigurationModule(self.temp_dir)

        # Verify configuration was loaded
        value = new_module.get_config_value("general.version")
        assert value == "persistent_version"

    def test_configuration_export_import(self):
        """Test configuration export and import"""
        # Export configuration
        export_path = self.temp_dir / "exported_config.json"
        self.config_module.export_configuration(export_path)

        # Verify export file exists and has content
        assert export_path.exists()
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        assert "general" in exported_data
        assert exported_data["general"]["app_name"] == "TimeLocker"

        # Modify current configuration
        self.config_module.set_config_value("general.app_name", "Modified")

        # Import configuration
        self.config_module.import_configuration(export_path)

        # Verify imported values
        app_name = self.config_module.get_config_value("general.app_name")
        assert app_name == "TimeLocker"

    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults"""
        # Modify configuration
        self.config_module.set_config_value("general.app_name", "Modified")
        self.config_module.set_config_value("backup.compression", "none")

        # Reset to defaults
        self.config_module.reset_to_defaults()

        # Verify reset
        app_name = self.config_module.get_config_value("general.app_name")
        compression = self.config_module.get_config_value("backup.compression")
        assert app_name == "TimeLocker"
        assert compression == "auto"

    def test_configuration_validation(self):
        """Test configuration validation"""
        # Get validation result
        result = self.config_module.validate_current_configuration()
        assert result.is_valid
        assert len(result.errors) == 0

    def test_configuration_defaults(self):
        """Test configuration defaults"""
        # Test default configuration structure
        default_config = ConfigurationDefaults.get_default_config()

        # Test backup defaults
        backup_config = default_config.backup
        assert backup_config.compression.value == "auto"
        assert backup_config.exclude_caches is True
        assert ".nobackup" in backup_config.exclude_if_present

        # Test restore defaults
        restore_config = default_config.restore
        assert restore_config.verify_after_restore is True
        assert restore_config.conflict_resolution == "prompt"

        # Test security defaults
        security_config = default_config.security
        assert security_config.encryption_enabled is True
        assert security_config.audit_logging is True

        # Test UI defaults
        ui_config = default_config.ui
        assert ui_config.theme.value == "auto"
        assert ui_config.confirm_destructive_actions is True

    def test_error_handling(self):
        """Test error handling for invalid operations"""
        # Test getting non-existent repository
        with pytest.raises(Exception):  # Should raise RepositoryNotFoundError
            self.config_module.get_repository("nonexistent")

        # Test removing non-existent repository
        with pytest.raises(Exception):  # Should raise RepositoryNotFoundError
            self.config_module.remove_repository("nonexistent")

        # Test importing non-existent file
        with pytest.raises(ConfigurationError):
            self.config_module.import_configuration(Path("/nonexistent/file.json"))
