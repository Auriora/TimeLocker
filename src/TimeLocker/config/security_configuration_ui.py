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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from .security_configuration_manager import SecurityConfigurationManager
from .security_configuration_migrator import SecurityConfigurationMigrator

logger = logging.getLogger(__name__)


class SecurityConfigurationUI:
    """
    User interface component for security configuration management.
    
    Provides CLI-friendly methods for managing configuration encryption,
    integrity verification, and security operations.
    """

    def __init__(self, security_manager: SecurityConfigurationManager):
        """
        Initialize security configuration UI.
        
        Args:
            security_manager: SecurityConfigurationManager instance
        """
        self.security_manager = security_manager
        self.migrator = SecurityConfigurationMigrator(security_manager)

    def show_encryption_status(self) -> Dict[str, Any]:
        """
        Display encryption status information.
        
        Returns:
            Dict containing formatted encryption status
        """
        try:
            status = self.security_manager.get_encryption_status()
            
            formatted_status = {
                "encryption_enabled": status["encryption_enabled"],
                "current_key_id": status["current_key_id"] or "None",
                "total_keys": status["total_keys"],
                "signature_exists": status["signature_exists"],
                "sensitive_patterns_count": len(status["sensitive_patterns"]),
                "status": "Enabled" if status["encryption_enabled"] else "Disabled"
            }
            
            return formatted_status
            
        except Exception as e:
            logger.error(f"Failed to get encryption status: {e}")
            return {"error": str(e)}

    def encrypt_configuration_section(
        self,
        section_name: str,
        section_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Encrypt sensitive values in a configuration section.
        
        Args:
            section_name: Name of the configuration section
            section_data: Section data to encrypt
            
        Returns:
            Dict containing encryption results
        """
        try:
            encrypted_values = 0
            processed_section = {}
            
            for key, value in section_data.items():
                key_path = f"{section_name}.{key}"
                encrypted_value = self.security_manager.encrypt_value(value, key_path)
                processed_section[key] = encrypted_value
                
                if encrypted_value.get("encrypted", False):
                    encrypted_values += 1
            
            return {
                "success": True,
                "section": section_name,
                "total_values": len(section_data),
                "encrypted_values": encrypted_values,
                "processed_section": processed_section
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt configuration section: {e}")
            return {
                "success": False,
                "error": str(e),
                "section": section_name
            }

    def verify_configuration_integrity(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify configuration integrity and display results.
        
        Args:
            config_data: Configuration data to verify
            
        Returns:
            Dict containing verification results
        """
        try:
            verification_passed = self.security_manager.verify_configuration(config_data)
            
            # Get signature information
            signature_file = self.security_manager.signature_file
            signature_exists = signature_file.exists()
            signature_age = None
            
            if signature_exists:
                signature_mtime = datetime.fromtimestamp(signature_file.stat().st_mtime)
                signature_age = datetime.now() - signature_mtime
            
            return {
                "verification_passed": verification_passed,
                "signature_exists": signature_exists,
                "signature_age_hours": signature_age.total_seconds() / 3600 if signature_age else None,
                "status": "VALID" if verification_passed else "INVALID",
                "recommendation": self._get_integrity_recommendation(verification_passed, signature_age)
            }
            
        except Exception as e:
            logger.error(f"Failed to verify configuration integrity: {e}")
            return {
                "verification_passed": False,
                "error": str(e),
                "status": "ERROR"
            }

    def _get_integrity_recommendation(
        self,
        verification_passed: bool,
        signature_age: Optional[timedelta]
    ) -> str:
        """
        Get recommendation based on integrity verification results.
        
        Args:
            verification_passed: Whether verification passed
            signature_age: Age of the signature
            
        Returns:
            str: Recommendation message
        """
        if not verification_passed:
            return "Configuration integrity check failed. Consider restoring from backup."
        
        if signature_age and signature_age > timedelta(days=30):
            return "Configuration signature is old. Consider re-signing for freshness."
        
        return "Configuration integrity is valid."

    def rotate_encryption_keys(self) -> Dict[str, Any]:
        """
        Rotate encryption keys and display results.
        
        Returns:
            Dict containing rotation results
        """
        try:
            old_key_id = self.security_manager._current_key_id
            new_key_id = self.security_manager.rotate_encryption_keys()
            
            return {
                "success": True,
                "old_key_id": old_key_id,
                "new_key_id": new_key_id,
                "total_keys": len(self.security_manager._encryption_keys),
                "message": f"Encryption keys rotated successfully: {old_key_id} -> {new_key_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to rotate encryption keys: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Key rotation failed"
            }

    def cleanup_old_keys(self, keep_count: int = 3) -> Dict[str, Any]:
        """
        Clean up old encryption keys and display results.
        
        Args:
            keep_count: Number of recent keys to keep
            
        Returns:
            Dict containing cleanup results
        """
        try:
            removed_count = self.security_manager.cleanup_old_keys(keep_count)
            
            return {
                "success": True,
                "removed_keys": removed_count,
                "remaining_keys": len(self.security_manager._encryption_keys),
                "message": f"Cleaned up {removed_count} old encryption keys"
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old keys: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Key cleanup failed"
            }

    def migrate_configuration_with_encryption(
        self,
        source_config: Dict[str, Any],
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate configuration with encryption support.
        
        Args:
            source_config: Source configuration to migrate
            create_backup: Whether to create backup before migration
            
        Returns:
            Dict containing migration results
        """
        try:
            backup_file = None
            
            if create_backup:
                backup_dir = self.security_manager.config_dir / "migration_backups"
                backup_file = self.migrator.create_migration_backup(source_config, backup_dir)
            
            migrated_config = self.migrator.migrate_configuration_with_encryption(source_config)
            
            # Get migration statistics
            migration_metadata = migrated_config.get("_migration", {})
            encrypted_keys = migration_metadata.get("encrypted_keys", [])
            
            return {
                "success": True,
                "backup_created": backup_file is not None,
                "backup_file": str(backup_file) if backup_file else None,
                "migrated_sections": len([k for k in migrated_config.keys() if not k.startswith("_")]),
                "encrypted_values": len(encrypted_keys),
                "target_version": migration_metadata.get("version"),
                "message": f"Configuration migrated successfully with {len(encrypted_keys)} encrypted values"
            }
            
        except Exception as e:
            logger.error(f"Failed to migrate configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Configuration migration failed"
            }

    def list_sensitive_patterns(self) -> Dict[str, Any]:
        """
        List sensitive configuration patterns.
        
        Returns:
            Dict containing sensitive patterns information
        """
        try:
            patterns = list(self.security_manager.sensitive_patterns)
            
            return {
                "success": True,
                "patterns": sorted(patterns),
                "pattern_count": len(patterns),
                "description": "Configuration keys containing these patterns will be encrypted"
            }
            
        except Exception as e:
            logger.error(f"Failed to list sensitive patterns: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def add_sensitive_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        Add a new sensitive configuration pattern.
        
        Args:
            pattern: Pattern to add to sensitive patterns
            
        Returns:
            Dict containing operation results
        """
        try:
            if pattern in self.security_manager.sensitive_patterns:
                return {
                    "success": False,
                    "message": f"Pattern '{pattern}' already exists",
                    "pattern": pattern
                }
            
            self.security_manager.sensitive_patterns.add(pattern)
            
            return {
                "success": True,
                "pattern": pattern,
                "total_patterns": len(self.security_manager.sensitive_patterns),
                "message": f"Added sensitive pattern: {pattern}"
            }
            
        except Exception as e:
            logger.error(f"Failed to add sensitive pattern: {e}")
            return {
                "success": False,
                "error": str(e),
                "pattern": pattern
            }

    def remove_sensitive_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        Remove a sensitive configuration pattern.
        
        Args:
            pattern: Pattern to remove from sensitive patterns
            
        Returns:
            Dict containing operation results
        """
        try:
            if pattern not in self.security_manager.sensitive_patterns:
                return {
                    "success": False,
                    "message": f"Pattern '{pattern}' not found",
                    "pattern": pattern
                }
            
            self.security_manager.sensitive_patterns.remove(pattern)
            
            return {
                "success": True,
                "pattern": pattern,
                "total_patterns": len(self.security_manager.sensitive_patterns),
                "message": f"Removed sensitive pattern: {pattern}"
            }
            
        except Exception as e:
            logger.error(f"Failed to remove sensitive pattern: {e}")
            return {
                "success": False,
                "error": str(e),
                "pattern": pattern
            }

    def export_security_configuration(self, output_file: Path) -> Dict[str, Any]:
        """
        Export security configuration settings.
        
        Args:
            output_file: Path to export file
            
        Returns:
            Dict containing export results
        """
        try:
            security_config = {
                "encryption_status": self.security_manager.get_encryption_status(),
                "sensitive_patterns": list(self.security_manager.sensitive_patterns),
                "migration_log": self.migrator.get_migration_log(),
                "exported_at": datetime.now().isoformat()
            }
            
            with open(output_file, 'w') as f:
                json.dump(security_config, f, indent=2)
            
            return {
                "success": True,
                "output_file": str(output_file),
                "sections_exported": len(security_config),
                "message": f"Security configuration exported to {output_file}"
            }
            
        except Exception as e:
            logger.error(f"Failed to export security configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "output_file": str(output_file)
            }

    def validate_security_setup(self) -> Dict[str, Any]:
        """
        Validate security configuration setup.
        
        Returns:
            Dict containing validation results and recommendations
        """
        try:
            status = self.security_manager.get_encryption_status()
            issues = []
            warnings = []
            recommendations = []
            
            # Check encryption setup
            if not status["encryption_enabled"]:
                issues.append("Encryption is not enabled - security service not available")
            elif not status["current_key_id"]:
                warnings.append("No encryption keys generated yet")
            
            # Check signature setup
            if not status["signature_exists"]:
                warnings.append("No configuration signature found")
            
            # Check sensitive patterns
            if len(status["sensitive_patterns"]) < 5:
                recommendations.append("Consider adding more sensitive patterns for better coverage")
            
            # Check key management
            if status["total_keys"] > 10:
                recommendations.append("Consider cleaning up old encryption keys")
            
            validation_score = 100
            validation_score -= len(issues) * 30
            validation_score -= len(warnings) * 10
            validation_score = max(0, validation_score)
            
            return {
                "validation_score": validation_score,
                "status": "GOOD" if validation_score >= 80 else "NEEDS_ATTENTION" if validation_score >= 50 else "POOR",
                "issues": issues,
                "warnings": warnings,
                "recommendations": recommendations,
                "encryption_enabled": status["encryption_enabled"],
                "total_keys": status["total_keys"]
            }
            
        except Exception as e:
            logger.error(f"Failed to validate security setup: {e}")
            return {
                "validation_score": 0,
                "status": "ERROR",
                "error": str(e)
            }

    def get_security_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive security configuration summary.
        
        Returns:
            Dict containing security summary
        """
        try:
            status = self.security_manager.get_encryption_status()
            validation = self.validate_security_setup()
            
            return {
                "encryption_status": status,
                "validation_results": validation,
                "sensitive_patterns_count": len(self.security_manager.sensitive_patterns),
                "migration_events": len(self.migrator.get_migration_log()),
                "summary": {
                    "encryption_enabled": status["encryption_enabled"],
                    "keys_available": status["total_keys"] > 0,
                    "signature_exists": status["signature_exists"],
                    "validation_score": validation["validation_score"],
                    "overall_status": validation["status"]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get security summary: {e}")
            return {
                "error": str(e),
                "summary": {
                    "overall_status": "ERROR"
                }
            }