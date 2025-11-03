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

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .security_configuration_manager import SecurityConfigurationManager
from ..interfaces.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class SecurityMigrationError(ConfigurationError):
    """Exception for security-related migration errors"""
    pass


class SecurityConfigurationMigrator:
    """
    Handles secure migration of configuration data with encryption support.
    
    Provides migration capabilities that preserve security properties during
    configuration upgrades and format changes.
    """

    def __init__(self, security_manager: SecurityConfigurationManager):
        """
        Initialize security configuration migrator.
        
        Args:
            security_manager: SecurityConfigurationManager instance
        """
        self.security_manager = security_manager
        self.migration_log: List[Dict[str, Any]] = []

    def migrate_configuration_with_encryption(
        self,
        source_config: Dict[str, Any],
        target_format_version: str = "2.0"
    ) -> Dict[str, Any]:
        """
        Migrate configuration data while applying encryption to sensitive values.
        
        Args:
            source_config: Source configuration data
            target_format_version: Target configuration format version
            
        Returns:
            Dict containing migrated and encrypted configuration
        """
        try:
            self._log_migration_event("migration_start", {
                "source_sections": list(source_config.keys()),
                "target_version": target_format_version
            })
            
            migrated_config = {}
            
            # Process each configuration section
            for section_name, section_data in source_config.items():
                if isinstance(section_data, dict):
                    migrated_section = self._migrate_section_with_encryption(
                        section_name, section_data
                    )
                    migrated_config[section_name] = migrated_section
                else:
                    # Handle non-dict values directly
                    encrypted_value = self.security_manager.encrypt_value(section_data, section_name)
                    migrated_config[section_name] = encrypted_value
            
            # Add migration metadata
            migrated_config["_migration"] = {
                "version": target_format_version,
                "migrated_at": datetime.now().isoformat(),
                "source_version": source_config.get("_migration", {}).get("version", "1.0"),
                "encrypted_keys": self._get_encrypted_keys_list(migrated_config)
            }
            
            # Sign the migrated configuration
            signature = self.security_manager.sign_configuration(migrated_config)
            
            self._log_migration_event("migration_complete", {
                "target_sections": list(migrated_config.keys()),
                "encrypted_values": len(migrated_config["_migration"]["encrypted_keys"]),
                "signature_created": True
            })
            
            return migrated_config
            
        except Exception as e:
            self._log_migration_event("migration_error", {"error": str(e)})
            logger.error(f"Failed to migrate configuration with encryption: {e}")
            raise SecurityMigrationError(f"Migration failed: {e}")

    def _migrate_section_with_encryption(
        self,
        section_name: str,
        section_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Migrate a configuration section while encrypting sensitive values.
        
        Args:
            section_name: Name of the configuration section
            section_data: Section data to migrate
            
        Returns:
            Dict containing migrated section with encrypted values
        """
        migrated_section = {}
        
        for key, value in section_data.items():
            key_path = f"{section_name}.{key}"
            
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                migrated_section[key] = self._migrate_nested_dict(key_path, value)
            elif isinstance(value, list):
                # Process lists that might contain sensitive data
                migrated_section[key] = self._migrate_list(key_path, value)
            else:
                # Process individual values
                encrypted_value = self.security_manager.encrypt_value(value, key_path)
                migrated_section[key] = encrypted_value
        
        return migrated_section

    def _migrate_nested_dict(self, base_path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate nested dictionary with encryption support.
        
        Args:
            base_path: Base key path for encryption detection
            data: Dictionary data to migrate
            
        Returns:
            Dict containing migrated nested data
        """
        migrated_dict = {}
        
        for key, value in data.items():
            key_path = f"{base_path}.{key}"
            
            if isinstance(value, dict):
                migrated_dict[key] = self._migrate_nested_dict(key_path, value)
            elif isinstance(value, list):
                migrated_dict[key] = self._migrate_list(key_path, value)
            else:
                encrypted_value = self.security_manager.encrypt_value(value, key_path)
                migrated_dict[key] = encrypted_value
        
        return migrated_dict

    def _migrate_list(self, key_path: str, data: List[Any]) -> List[Any]:
        """
        Migrate list data with encryption support.
        
        Args:
            key_path: Key path for encryption detection
            data: List data to migrate
            
        Returns:
            List containing migrated data
        """
        migrated_list = []
        
        for i, item in enumerate(data):
            item_path = f"{key_path}[{i}]"
            
            if isinstance(item, dict):
                migrated_list.append(self._migrate_nested_dict(item_path, item))
            elif isinstance(item, list):
                migrated_list.append(self._migrate_list(item_path, item))
            else:
                encrypted_value = self.security_manager.encrypt_value(item, item_path)
                migrated_list.append(encrypted_value)
        
        return migrated_list

    def _get_encrypted_keys_list(self, config: Dict[str, Any]) -> List[str]:
        """
        Get list of encrypted keys in the configuration.
        
        Args:
            config: Configuration data to analyze
            
        Returns:
            List of key paths that are encrypted
        """
        encrypted_keys = []
        
        def find_encrypted_keys(data: Any, path: str = ""):
            if isinstance(data, dict):
                if data.get("encrypted", False):
                    encrypted_keys.append(path)
                else:
                    for key, value in data.items():
                        if key.startswith("_"):  # Skip metadata keys
                            continue
                        new_path = f"{path}.{key}" if path else key
                        find_encrypted_keys(value, new_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    new_path = f"{path}[{i}]"
                    find_encrypted_keys(item, new_path)
        
        find_encrypted_keys(config)
        return encrypted_keys

    def decrypt_migrated_configuration(self, encrypted_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt a migrated configuration for use.
        
        Args:
            encrypted_config: Configuration with encrypted values
            
        Returns:
            Dict containing decrypted configuration
        """
        try:
            self._log_migration_event("decryption_start", {
                "sections": list(encrypted_config.keys())
            })
            
            decrypted_config = {}
            
            for section_name, section_data in encrypted_config.items():
                if section_name.startswith("_"):  # Skip metadata sections
                    decrypted_config[section_name] = section_data
                    continue
                    
                decrypted_section = self._decrypt_section(section_data)
                decrypted_config[section_name] = decrypted_section
            
            self._log_migration_event("decryption_complete", {
                "sections_decrypted": len([k for k in decrypted_config.keys() if not k.startswith("_")])
            })
            
            return decrypted_config
            
        except Exception as e:
            self._log_migration_event("decryption_error", {"error": str(e)})
            logger.error(f"Failed to decrypt migrated configuration: {e}")
            raise SecurityMigrationError(f"Decryption failed: {e}")

    def _decrypt_section(self, section_data: Any) -> Any:
        """
        Recursively decrypt a configuration section.
        
        Args:
            section_data: Section data to decrypt
            
        Returns:
            Decrypted section data
        """
        if isinstance(section_data, dict):
            if section_data.get("encrypted", False):
                # This is an encrypted value
                return self.security_manager.decrypt_value(section_data)
            else:
                # Regular dictionary - process recursively
                decrypted_dict = {}
                for key, value in section_data.items():
                    decrypted_dict[key] = self._decrypt_section(value)
                return decrypted_dict
        elif isinstance(section_data, list):
            # Process list items
            return [self._decrypt_section(item) for item in section_data]
        else:
            # Regular value - return as-is
            return section_data

    def validate_migration_integrity(self, migrated_config: Dict[str, Any]) -> bool:
        """
        Validate the integrity of migrated configuration.
        
        Args:
            migrated_config: Migrated configuration to validate
            
        Returns:
            bool: True if validation passes
        """
        try:
            # Verify configuration signature
            verification_passed = self.security_manager.verify_configuration(migrated_config)
            
            # Check migration metadata
            migration_metadata = migrated_config.get("_migration", {})
            has_valid_metadata = all(
                key in migration_metadata
                for key in ["version", "migrated_at", "encrypted_keys"]
            )
            
            # Validate encrypted keys can be decrypted
            encrypted_keys_valid = True
            try:
                self.decrypt_migrated_configuration(migrated_config)
            except Exception:
                encrypted_keys_valid = False
            
            validation_result = verification_passed and has_valid_metadata and encrypted_keys_valid
            
            self._log_migration_event("validation_complete", {
                "signature_valid": verification_passed,
                "metadata_valid": has_valid_metadata,
                "encryption_valid": encrypted_keys_valid,
                "overall_valid": validation_result
            })
            
            return validation_result
            
        except Exception as e:
            self._log_migration_event("validation_error", {"error": str(e)})
            logger.error(f"Failed to validate migration integrity: {e}")
            return False

    def create_migration_backup(
        self,
        source_config: Dict[str, Any],
        backup_dir: Path
    ) -> Optional[Path]:
        """
        Create encrypted backup of source configuration before migration.
        
        Args:
            source_config: Source configuration to backup
            backup_dir: Directory to store backup
            
        Returns:
            Optional[Path]: Path to backup file if successful
        """
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"pre_migration_backup_{timestamp}.json"
            
            # Create backup with encryption
            encrypted_backup = self.migrate_configuration_with_encryption(
                source_config, "backup"
            )
            
            with open(backup_file, 'w') as f:
                json.dump(encrypted_backup, f, indent=2)
            
            self._log_migration_event("backup_created", {
                "backup_file": str(backup_file),
                "source_sections": len(source_config)
            })
            
            logger.info(f"Created migration backup: {backup_file}")
            return backup_file
            
        except Exception as e:
            self._log_migration_event("backup_error", {"error": str(e)})
            logger.error(f"Failed to create migration backup: {e}")
            return None

    def restore_from_backup(self, backup_file: Path) -> Dict[str, Any]:
        """
        Restore configuration from encrypted backup.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            Dict containing restored configuration
        """
        try:
            if not backup_file.exists():
                raise SecurityMigrationError(f"Backup file not found: {backup_file}")
            
            with open(backup_file, 'r') as f:
                encrypted_backup = json.load(f)
            
            # Decrypt and restore
            restored_config = self.decrypt_migrated_configuration(encrypted_backup)
            
            # Remove backup-specific metadata
            if "_migration" in restored_config:
                migration_meta = restored_config["_migration"]
                if migration_meta.get("version") == "backup":
                    del restored_config["_migration"]
            
            self._log_migration_event("backup_restored", {
                "backup_file": str(backup_file),
                "restored_sections": len(restored_config)
            })
            
            logger.info(f"Restored configuration from backup: {backup_file}")
            return restored_config
            
        except Exception as e:
            self._log_migration_event("restore_error", {"error": str(e)})
            logger.error(f"Failed to restore from backup: {e}")
            raise SecurityMigrationError(f"Backup restoration failed: {e}")

    def get_migration_log(self) -> List[Dict[str, Any]]:
        """
        Get migration operation log.
        
        Returns:
            List of migration log entries
        """
        return self.migration_log.copy()

    def _log_migration_event(self, event_type: str, metadata: Dict[str, Any]) -> None:
        """
        Log migration event for audit trail.
        
        Args:
            event_type: Type of migration event
            metadata: Event metadata
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "metadata": metadata
        }
        
        self.migration_log.append(log_entry)
        
        # Also log to security service if available
        if self.security_manager.security_service:
            from ..security.security_service import SecurityEvent, SecurityLevel
            self.security_manager.security_service.log_security_event(
                SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="configuration_migration",
                    level=SecurityLevel.MEDIUM,
                    description=f"Configuration migration event: {event_type}",
                    metadata=metadata
                )
            )

    def cleanup_migration_artifacts(self, keep_backups: int = 5) -> int:
        """
        Clean up old migration artifacts and backups.
        
        Args:
            keep_backups: Number of recent backups to keep
            
        Returns:
            int: Number of artifacts cleaned up
        """
        try:
            backup_dir = self.security_manager.config_dir / "migration_backups"
            if not backup_dir.exists():
                return 0
            
            # Find backup files
            backup_files = list(backup_dir.glob("pre_migration_backup_*.json"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Remove old backups
            files_to_remove = backup_files[keep_backups:]
            removed_count = 0
            
            for backup_file in files_to_remove:
                try:
                    backup_file.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove backup file {backup_file}: {e}")
            
            if removed_count > 0:
                self._log_migration_event("cleanup_complete", {
                    "removed_backups": removed_count,
                    "remaining_backups": len(backup_files) - removed_count
                })
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup migration artifacts: {e}")
            return 0