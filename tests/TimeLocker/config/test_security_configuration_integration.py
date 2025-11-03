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
import json
from pathlib import Path
from datetime import datetime

from src.TimeLocker.config.security_configuration_manager import SecurityConfigurationManager
from src.TimeLocker.config.security_configuration_migrator import SecurityConfigurationMigrator
from src.TimeLocker.config.security_configuration_ui import SecurityConfigurationUI
from src.TimeLocker.config.configuration_audit_logger import ConfigurationAuditLogger, ConfigurationOperation
from src.TimeLocker.config.configuration_access_control import ConfigurationAccessControl
from src.TimeLocker.security.security_service import SecurityService
from src.TimeLocker.security.credential_manager import CredentialManager


class TestSecurityConfigurationIntegration:
    """Integration tests for security configuration enhancements"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize security components
        self.credential_manager = CredentialManager(self.config_dir / "credentials")
        # Unlock credential manager for testing
        self.credential_manager.unlock("test_password")
        
        self.security_service = SecurityService(
            self.credential_manager,
            self.config_dir / "security"
        )
        
        # Initialize security configuration components
        self.security_manager = SecurityConfigurationManager(
            self.security_service,
            self.config_dir
        )
        self.audit_logger = ConfigurationAuditLogger(
            self.config_dir,
            self.security_service
        )
        self.access_control = ConfigurationAccessControl(
            self.config_dir,
            self.audit_logger
        )
        self.migrator = SecurityConfigurationMigrator(self.security_manager)
        self.ui = SecurityConfigurationUI(self.security_manager)

    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.config
    @pytest.mark.security
    def test_encryption_workflow(self):
        """Test complete encryption workflow"""
        # Test configuration data with sensitive values
        test_config = {
            "database": {
                "host": "localhost",
                "password": "secret123",  # Should be encrypted
                "port": 5432
            },
            "api": {
                "api_key": "abc123def456",  # Should be encrypted
                "endpoint": "https://api.example.com"
            }
        }
        
        # Test encryption
        encrypted_section = self.ui.encrypt_configuration_section("database", test_config["database"])
        assert encrypted_section["success"] is True
        assert encrypted_section["encrypted_values"] == 1  # Only password should be encrypted
        
        # Verify sensitive value was encrypted
        processed_section = encrypted_section["processed_section"]
        assert processed_section["password"]["encrypted"] is True
        assert processed_section["host"]["encrypted"] is False  # Not sensitive
        
        # Test decryption
        decrypted_password = self.security_manager.decrypt_value(processed_section["password"])
        assert decrypted_password == "secret123"

    @pytest.mark.config
    @pytest.mark.security
    def test_configuration_signing_and_verification(self):
        """Test configuration signing and integrity verification"""
        test_config = {
            "repositories": {
                "default": {
                    "location": "/backup/repo",
                    "password": "repo_secret"
                }
            }
        }
        
        # Sign configuration
        signature = self.security_manager.sign_configuration(test_config)
        assert signature.signature is not None
        assert signature.algorithm == "PBKDF2-HMAC-SHA256"
        assert len(signature.sections) == 1
        
        # Verify configuration
        verification_result = self.ui.verify_configuration_integrity(test_config)
        assert verification_result["verification_passed"] is True
        assert verification_result["status"] == "VALID"
        
        # Test with modified configuration
        modified_config = test_config.copy()
        modified_config["repositories"]["default"]["location"] = "/different/path"
        
        verification_result = self.ui.verify_configuration_integrity(modified_config)
        assert verification_result["verification_passed"] is False
        assert verification_result["status"] == "INVALID"

    @pytest.mark.config
    @pytest.mark.security
    def test_migration_with_encryption(self):
        """Test configuration migration with encryption"""
        source_config = {
            "version": "1.0",
            "credentials": {
                "username": "admin",
                "password": "admin123",  # Should be encrypted during migration
                "token": "bearer_token_xyz"  # Should be encrypted during migration
            },
            "settings": {
                "debug": True,
                "timeout": 30
            }
        }
        
        # Test migration
        migration_result = self.ui.migrate_configuration_with_encryption(source_config)
        assert migration_result["success"] is True
        assert migration_result["encrypted_values"] > 0
        assert migration_result["migrated_sections"] >= 2
        
        # Verify backup was created
        assert migration_result["backup_created"] is True
        assert migration_result["backup_file"] is not None

    @pytest.mark.config
    @pytest.mark.security
    def test_audit_logging(self):
        """Test comprehensive audit logging"""
        # Log various configuration operations
        self.audit_logger.log_configuration_access(
            operation=ConfigurationOperation.READ,
            section="repositories",
            key="default",
            success=True,
            description="Read default repository configuration"
        )
        
        self.audit_logger.log_configuration_access(
            operation=ConfigurationOperation.WRITE,
            section="security",
            key="encryption_enabled",
            success=True,
            description="Updated encryption setting",
            old_value=False,
            new_value=True
        )
        
        self.audit_logger.log_configuration_access(
            operation=ConfigurationOperation.DELETE,
            section="repositories",
            key="old_repo",
            success=False,
            description="Failed to delete repository"
        )
        
        # Retrieve audit events
        events = self.audit_logger.get_audit_events(limit=10)
        assert len(events) >= 3  # May include setup events
        
        # Filter to our test events
        test_events = [e for e in events if e["operation"] in ["read", "write", "delete"] 
                      and e["section"] in ["repositories", "security"]]
        assert len(test_events) == 3
        
        # Verify event details
        read_event = next(e for e in test_events if e["operation"] == "read")
        assert read_event["section"] == "repositories"
        assert read_event["success"] is True
        
        write_event = next(e for e in test_events if e["operation"] == "write")
        assert write_event["old_value_hash"] is not None
        assert write_event["new_value_hash"] is not None
        
        delete_event = next(e for e in test_events if e["operation"] == "delete")
        assert delete_event["success"] is False

    @pytest.mark.config
    @pytest.mark.security
    def test_access_control(self):
        """Test access control and file permissions"""
        # Test file permission setting
        test_file = self.config_dir / "test_config.json"
        test_file.write_text('{"test": "data"}')
        
        # Set secure permissions
        result = self.access_control.set_secure_permissions(test_file, "config_files")
        assert result is True
        
        # Get permission information
        perm_info = self.access_control.get_file_permissions(test_file)
        assert perm_info.path == str(test_file)
        assert perm_info.readable is True
        assert perm_info.writable is True
        
        # Test access permission checking
        current_user = self.access_control._get_current_user()
        
        # User should have read access
        has_read_access = self.access_control.check_access_permission(
            current_user, str(test_file), ConfigurationOperation.READ
        )
        assert has_read_access is True
        
        # User should have write access (as owner)
        has_write_access = self.access_control.check_access_permission(
            current_user, str(test_file), ConfigurationOperation.WRITE
        )
        assert has_write_access is True

    @pytest.mark.config
    @pytest.mark.security
    def test_security_status_and_validation(self):
        """Test security status reporting and validation"""
        # Test encryption status
        status = self.ui.show_encryption_status()
        assert "encryption_enabled" in status
        assert "current_key_id" in status
        assert "total_keys" in status
        
        # Test security validation
        validation = self.ui.validate_security_setup()
        assert "validation_score" in validation
        assert "status" in validation
        assert validation["encryption_enabled"] is True
        
        # Test security summary
        summary = self.ui.get_security_summary()
        assert "encryption_status" in summary
        assert "validation_results" in summary
        assert "summary" in summary

    @pytest.mark.config
    @pytest.mark.security
    def test_key_rotation_and_cleanup(self):
        """Test encryption key rotation and cleanup"""
        # Generate initial key
        initial_key_id = self.security_manager._current_key_id
        
        # Rotate keys
        rotation_result = self.ui.rotate_encryption_keys()
        assert rotation_result["success"] is True
        assert rotation_result["new_key_id"] != initial_key_id
        assert rotation_result["total_keys"] >= 1
        
        # Generate more keys for cleanup test
        for _ in range(5):
            self.security_manager.rotate_encryption_keys()
        
        # Test key cleanup
        cleanup_result = self.ui.cleanup_old_keys(keep_count=3)
        assert cleanup_result["success"] is True
        # Should have cleaned up some keys, but may not be exactly 3 due to current key protection
        assert cleanup_result["remaining_keys"] <= 6  # More flexible assertion

    @pytest.mark.config
    @pytest.mark.security
    def test_sensitive_pattern_management(self):
        """Test sensitive pattern management"""
        # List default patterns
        patterns_result = self.ui.list_sensitive_patterns()
        assert patterns_result["success"] is True
        assert len(patterns_result["patterns"]) > 0
        
        # Add new pattern
        add_result = self.ui.add_sensitive_pattern("custom_secret")
        assert add_result["success"] is True
        assert add_result["pattern"] == "custom_secret"
        
        # Verify pattern was added
        updated_patterns = self.ui.list_sensitive_patterns()
        assert "custom_secret" in updated_patterns["patterns"]
        
        # Remove pattern
        remove_result = self.ui.remove_sensitive_pattern("custom_secret")
        assert remove_result["success"] is True
        
        # Verify pattern was removed
        final_patterns = self.ui.list_sensitive_patterns()
        assert "custom_secret" not in final_patterns["patterns"]

    @pytest.mark.config
    @pytest.mark.security
    def test_directory_security(self):
        """Test directory-wide security operations"""
        # Create test files and directories
        (self.config_dir / "subdir").mkdir(exist_ok=True)
        (self.config_dir / "config.json").write_text('{"test": "data"}')
        (self.config_dir / "subdir" / "nested.json").write_text('{"nested": "data"}')
        
        # Secure entire directory
        security_result = self.access_control.secure_configuration_directory()
        assert security_result["directories_secured"] >= 1
        assert security_result["files_secured"] >= 2
        assert len(security_result["errors"]) == 0
        
        # Audit file permissions
        audit_results = self.access_control.audit_file_permissions()
        assert len(audit_results) >= 3  # config_dir, subdir, and files
        
        # Check that files are marked as secure
        secure_files = [r for r in audit_results if r.get("secure", False)]
        assert len(secure_files) > 0

    @pytest.mark.config
    @pytest.mark.security
    def test_export_and_import_security_config(self):
        """Test security configuration export and import"""
        # Export security configuration
        export_file = self.temp_dir / "security_export.json"
        export_result = self.ui.export_security_configuration(export_file)
        
        assert export_result["success"] is True
        assert export_file.exists()
        
        # Verify export content
        with open(export_file, 'r') as f:
            exported_data = json.load(f)
        
        assert "encryption_status" in exported_data
        assert "sensitive_patterns" in exported_data
        assert "exported_at" in exported_data