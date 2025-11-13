"""
Configuration backup manager for TimeLocker.

This module provides enhanced backup management with metadata, validation,
and comparison capabilities, following the Single Responsibility Principle
by focusing solely on backup operations.
"""

import json
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from .configuration_validator import ConfigurationValidator, ValidationResult
from ..interfaces.exceptions import ConfigurationBackupError, ConfigurationError

logger = logging.getLogger(__name__)


class BackupReason(Enum):
    """Reasons for creating configuration backups"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    PRE_UPDATE = "pre_update"
    PRE_MIGRATION = "pre_migration"
    SCHEDULED = "scheduled"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class ConfigurationBackupMetadata:
    """Metadata for configuration backups"""
    backup_id: str
    created_at: datetime
    reason: BackupReason
    size_bytes: int
    sections: List[str]
    validation_status: str
    checksum: str
    retention_policy: str
    source_file: str
    backup_version: str = "1.0"
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['reason'] = self.reason.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigurationBackupMetadata':
        """Create from dictionary"""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['reason'] = BackupReason(data['reason'])
        return cls(**data)


PROTECTED_BACKUP_TAGS: Set[str] = {"critical", "milestone", "manual"}
PROTECTED_RETENTION_POLICIES: Set[str] = {"keep_forever", "pinned", "retain", "archive"}


class ConfigurationBackupManager:
    """
    Enhanced configuration backup manager.
    
    Provides backup creation, restoration, comparison, and metadata management
    with intelligent cleanup and validation capabilities.
    """

    def __init__(self, backup_directory: Path, validator: Optional[ConfigurationValidator] = None):
        """
        Initialize the backup manager.
        
        Args:
            backup_directory: Directory to store backups
            validator: Configuration validator for backup validation
        """
        self.backup_directory = backup_directory
        self.backup_directory.mkdir(parents=True, exist_ok=True)

        self._validator = validator or ConfigurationValidator()
        self._metadata_file = self.backup_directory / "backup_metadata.json"
        self._metadata_cache: Optional[Dict[str, ConfigurationBackupMetadata]] = None

    def create_backup(self, config_file: Path, reason: BackupReason = BackupReason.MANUAL,
                      tags: Optional[List[str]] = None) -> str:
        """
        Create a backup of the configuration file.
        
        Args:
            config_file: Configuration file to backup
            reason: Reason for creating the backup
            tags: Optional tags for the backup
            
        Returns:
            Backup identifier
            
        Raises:
            ConfigurationBackupError: If backup creation fails
        """
        try:
            if not config_file.exists():
                raise ConfigurationBackupError(f"Configuration file does not exist: {config_file}")

            # Generate backup ID with microsecond precision for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_id = f"backup_{timestamp}_{reason.value}"

            # Create backup file path
            backup_file = self.backup_directory / f"{backup_id}.json"

            # Copy configuration file
            shutil.copy2(config_file, backup_file)

            # Calculate checksum
            checksum = self._calculate_checksum(backup_file)

            # Get file size
            size_bytes = backup_file.stat().st_size

            # Validate backup
            validation_status = self._validate_backup_file(backup_file)

            # Extract sections from configuration
            sections = self._extract_sections(backup_file)

            # Create metadata
            metadata = ConfigurationBackupMetadata(
                    backup_id=backup_id,
                    created_at=datetime.now(),
                    reason=reason,
                    size_bytes=size_bytes,
                    sections=sections,
                    validation_status=validation_status,
                    checksum=checksum,
                    retention_policy="default",
                    source_file=str(config_file),
                    tags=tags or []
            )

            # Save metadata
            self._save_backup_metadata(metadata)

            logger.info(f"Created configuration backup: {backup_id}")
            return backup_id

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise ConfigurationBackupError(f"Backup creation failed: {e}")

    def list_backups(self, limit: Optional[int] = None,
                     reason_filter: Optional[BackupReason] = None) -> List[Dict[str, Any]]:
        """
        List available configuration backups.
        
        Args:
            limit: Maximum number of backups to return
            reason_filter: Filter backups by reason
            
        Returns:
            List of backup information dictionaries
        """
        try:
            metadata_dict = self._load_backup_metadata()
            backups = []

            for backup_id, metadata in metadata_dict.items():
                if reason_filter and metadata.reason != reason_filter:
                    continue

                backup_info = metadata.to_dict()
                backup_info['backup_id'] = backup_id

                # Add file existence check
                backup_file = self.backup_directory / f"{backup_id}.json"
                backup_info['file_exists'] = backup_file.exists()

                backups.append(backup_info)

            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created_at'], reverse=True)

            if limit:
                backups = backups[:limit]

            return backups

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

    def restore_backup(self, backup_id: str, target_file: Optional[Path] = None) -> bool:
        """
        Restore configuration from a backup.
        
        Args:
            backup_id: Backup identifier to restore
            target_file: Target file to restore to (defaults to metadata source file)
            
        Returns:
            True if restore was successful
            
        Raises:
            ConfigurationBackupError: If backup restoration fails
        """
        try:
            backup_file = self.backup_directory / f"{backup_id}.json"

            if not backup_file.exists():
                raise ConfigurationBackupError(f"Backup file not found: {backup_id}")

            # Validate backup before restoration
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                raise ConfigurationBackupError(f"Backup metadata not found: {backup_id}")

            resolved_target = self._resolve_restore_target(target_file, metadata)

            # Verify checksum
            current_checksum = self._calculate_checksum(backup_file)
            if current_checksum != metadata.checksum:
                raise ConfigurationBackupError(f"Backup checksum mismatch: {backup_id}")

            # Ensure target directory exists
            resolved_target.parent.mkdir(parents=True, exist_ok=True)

            # Create backup of current file before restoration
            if resolved_target.exists():
                self.create_backup(resolved_target, BackupReason.PRE_UPDATE, ["pre_restore"])

            # Load backup data (ensures valid JSON and respects metadata sections)
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            missing_sections = [
                    section for section in metadata.sections
                    if section not in backup_data
            ]
            if missing_sections:
                raise ConfigurationBackupError(
                        f"Backup '{backup_id}' is missing section(s): "
                        f"{', '.join(missing_sections)}"
                )

            # Restore the validated configuration
            with open(resolved_target, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2)

            # Re-validate restored configuration
            validation_result = self._validator.validate_config(backup_data)
            if not validation_result.is_valid:
                logger.warning(
                        "Restored configuration reported validation issues: %s",
                        "; ".join(validation_result.errors)
                )

            logger.info(f"Restored configuration from backup: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            raise ConfigurationBackupError(f"Backup restoration failed: {e}")

    def compare_backups(self, backup_id1: str, backup_id2: str) -> Dict[str, Any]:
        """
        Compare two configuration backups.
        
        Args:
            backup_id1: First backup to compare
            backup_id2: Second backup to compare
            
        Returns:
            Comparison result with differences
            
        Raises:
            ConfigurationBackupError: If comparison fails
        """
        try:
            backup_file1 = self.backup_directory / f"{backup_id1}.json"
            backup_file2 = self.backup_directory / f"{backup_id2}.json"

            if not backup_file1.exists():
                raise ConfigurationBackupError(f"Backup not found: {backup_id1}")
            if not backup_file2.exists():
                raise ConfigurationBackupError(f"Backup not found: {backup_id2}")

            # Load configurations
            with open(backup_file1, 'r') as f:
                config1 = json.load(f)
            with open(backup_file2, 'r') as f:
                config2 = json.load(f)

            # Compare configurations
            differences = self._compare_configurations(config1, config2)

            # Get metadata for both backups
            metadata1 = self._get_backup_metadata(backup_id1)
            metadata2 = self._get_backup_metadata(backup_id2)

            return {
                    'backup1':     {
                            'id':         backup_id1,
                            'created_at': metadata1.created_at.isoformat() if metadata1 else None,
                            'reason':     metadata1.reason.value if metadata1 else None
                    },
                    'backup2':     {
                            'id':         backup_id2,
                            'created_at': metadata2.created_at.isoformat() if metadata2 else None,
                            'reason':     metadata2.reason.value if metadata2 else None
                    },
                    'differences': differences,
                    'identical':   len(differences) == 0
            }

        except Exception as e:
            logger.error(f"Failed to compare backups: {e}")
            raise ConfigurationBackupError(f"Backup comparison failed: {e}")

    def restore_section(self, backup_id: str, section: str, target_file: Path) -> bool:
        """
        Restore a specific section from a backup.
        
        Args:
            backup_id: Backup identifier
            section: Section name to restore
            target_file: Target configuration file
            
        Returns:
            True if section restore was successful
            
        Raises:
            ConfigurationBackupError: If section restoration fails
        """
        try:
            backup_file = self.backup_directory / f"{backup_id}.json"

            if not backup_file.exists():
                raise ConfigurationBackupError(f"Backup file not found: {backup_id}")

            # Load backup configuration
            with open(backup_file, 'r') as f:
                backup_config = json.load(f)

            if section not in backup_config:
                raise ConfigurationBackupError(f"Section '{section}' not found in backup")

            # Load current configuration
            current_config = {}
            if target_file.exists():
                with open(target_file, 'r') as f:
                    current_config = json.load(f)

            # Create backup of current file
            if target_file.exists():
                self.create_backup(target_file, BackupReason.PRE_UPDATE, [f"pre_section_restore_{section}"])

            # Restore the section
            current_config[section] = backup_config[section]

            # Save updated configuration
            with open(target_file, 'w') as f:
                json.dump(current_config, f, indent=2)

            logger.info(f"Restored section '{section}' from backup: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore section '{section}' from backup {backup_id}: {e}")
            raise ConfigurationBackupError(f"Section restoration failed: {e}")

    def cleanup_old_backups(self, keep_count: int = 5, max_age_days: Optional[int] = None) -> int:
        """
        Clean up old backups based on retention policy.
        
        Args:
            keep_count: Number of recent backups to keep
            max_age_days: Maximum age in days for backups
            
        Returns:
            Number of backups cleaned up
        """
        try:
            metadata_dict = self._load_backup_metadata()
            backups_to_remove: Set[str] = set()
            cleaned_count = 0

            # Remove metadata entries whose files no longer exist
            available_backups = []
            for backup_id, metadata in metadata_dict.items():
                backup_file = self.backup_directory / f"{backup_id}.json"
                if backup_file.exists():
                    available_backups.append((backup_id, metadata))
                else:
                    if self._remove_backup(backup_id):
                        cleaned_count += 1
                        logger.debug(f"Removed stale metadata for backup {backup_id}")

            # Sort backups by creation time (newest first)
            sorted_backups = sorted(
                    available_backups,
                    key=lambda x: x[1].created_at,
                    reverse=True
            )

            keep_limit = max(keep_count, 0)
            retained_total = 0
            for backup_id, metadata in sorted_backups:
                if retained_total < keep_limit:
                    retained_total += 1
                    continue

                if not self._is_protected_backup(metadata):
                    backups_to_remove.add(backup_id)

            # Apply max_age policy
            if max_age_days:
                cutoff_date = datetime.now() - timedelta(days=max_age_days)
                for backup_id, metadata in available_backups:
                    if metadata.created_at < cutoff_date and not self._is_protected_backup(metadata):
                        backups_to_remove.add(backup_id)

            # Remove selected backups
            for backup_id in backups_to_remove:
                if self._remove_backup(backup_id):
                    cleaned_count += 1

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old configuration backups")

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0

    def validate_backup(self, backup_id: str) -> ValidationResult:
        """
        Validate a configuration backup.
        
        Args:
            backup_id: Backup identifier to validate
            
        Returns:
            Validation result
        """
        result = ValidationResult()

        try:
            backup_file = self.backup_directory / f"{backup_id}.json"

            if not backup_file.exists():
                result.add_error(f"Backup file not found: {backup_id}")
                return result

            # Validate file format
            try:
                with open(backup_file, 'r') as f:
                    config_data = json.load(f)
            except json.JSONDecodeError as e:
                result.add_error(f"Invalid JSON in backup file: {e}")
                return result

            # Validate configuration structure
            validation_result = self._validator.validate_config(config_data)
            result.errors.extend(validation_result.errors)
            result.warnings.extend(validation_result.warnings)
            result.is_valid = validation_result.is_valid

            # Validate metadata
            metadata = self._get_backup_metadata(backup_id)
            if metadata:
                # Verify checksum
                current_checksum = self._calculate_checksum(backup_file)
                if current_checksum != metadata.checksum:
                    result.add_error("Backup checksum mismatch - file may be corrupted")
            else:
                result.add_warning("Backup metadata not found")

        except Exception as e:
            result.add_error(f"Backup validation failed: {e}")

        return result

    # Private helper methods

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""

    def _validate_backup_file(self, backup_file: Path) -> str:
        """Validate a backup file and return status"""
        try:
            with open(backup_file, 'r') as f:
                config_data = json.load(f)

            validation_result = self._validator.validate_config(config_data)
            if validation_result.is_valid:
                return "valid"
            else:
                return f"invalid: {'; '.join(validation_result.errors[:3])}"
        except Exception as e:
            return f"error: {str(e)[:100]}"

    def _extract_sections(self, config_file: Path) -> List[str]:
        """Extract section names from configuration file"""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            return list(config_data.keys())
        except Exception:
            return []

    def _load_backup_metadata(self) -> Dict[str, ConfigurationBackupMetadata]:
        """Load backup metadata from file"""
        if self._metadata_cache is not None:
            return self._metadata_cache

        try:
            if self._metadata_file.exists():
                with open(self._metadata_file, 'r') as f:
                    data = json.load(f)

                metadata_dict = {}
                for backup_id, metadata_data in data.items():
                    try:
                        metadata_dict[backup_id] = ConfigurationBackupMetadata.from_dict(metadata_data)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for backup {backup_id}: {e}")

                self._metadata_cache = metadata_dict
                return metadata_dict
            else:
                self._metadata_cache = {}
                return {}
        except Exception as e:
            logger.error(f"Failed to load backup metadata: {e}")
            return {}

    def _save_backup_metadata(self, metadata: ConfigurationBackupMetadata) -> None:
        """Save backup metadata to file"""
        try:
            metadata_dict = self._load_backup_metadata()
            metadata_dict[metadata.backup_id] = metadata

            # Convert to serializable format
            serializable_data = {}
            for backup_id, meta in metadata_dict.items():
                serializable_data[backup_id] = meta.to_dict()

            # Save to file
            with open(self._metadata_file, 'w') as f:
                json.dump(serializable_data, f, indent=2)

            # Update cache
            self._metadata_cache = metadata_dict

        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")

    def _get_backup_metadata(self, backup_id: str) -> Optional[ConfigurationBackupMetadata]:
        """Get metadata for a specific backup"""
        metadata_dict = self._load_backup_metadata()
        return metadata_dict.get(backup_id)

    def _remove_backup(self, backup_id: str) -> bool:
        """Remove a backup and its metadata"""
        try:
            # Remove backup file
            backup_file = self.backup_directory / f"{backup_id}.json"
            if backup_file.exists():
                backup_file.unlink()

            # Remove from metadata
            metadata_dict = self._load_backup_metadata()
            if backup_id in metadata_dict:
                del metadata_dict[backup_id]

                # Save updated metadata
                serializable_data = {}
                for bid, meta in metadata_dict.items():
                    serializable_data[bid] = meta.to_dict()

                with open(self._metadata_file, 'w') as f:
                    json.dump(serializable_data, f, indent=2)

                # Update cache
                self._metadata_cache = metadata_dict

            return True

        except Exception as e:
            logger.error(f"Failed to remove backup {backup_id}: {e}")
            return False

    def _resolve_restore_target(
            self,
            target_file: Optional[Path],
            metadata: ConfigurationBackupMetadata
    ) -> Path:
        """Resolve the restore target using metadata when necessary."""
        if target_file:
            return target_file

        if metadata.source_file:
            return Path(metadata.source_file)

        raise ConfigurationBackupError(
                "Backup metadata does not include the original source file and no target was provided."
        )

    def _is_protected_backup(self, metadata: ConfigurationBackupMetadata) -> bool:
        """Return True if the backup should be excluded from automated cleanup."""
        tag_set = {tag.lower() for tag in (metadata.tags or [])}
        if tag_set & PROTECTED_BACKUP_TAGS:
            return True

        policy = (metadata.retention_policy or "").lower()
        return policy in PROTECTED_RETENTION_POLICIES

    def _compare_configurations(self, config1: Dict[str, Any], config2: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare two configuration dictionaries and return differences"""
        differences = []

        def compare_recursive(obj1, obj2, path=""):
            if type(obj1) != type(obj2):
                differences.append({
                        'path':      path,
                        'type':      'type_change',
                        'old_value': obj1,
                        'new_value': obj2,
                        'old_type':  type(obj1).__name__,
                        'new_type':  type(obj2).__name__
                })
                return

            if isinstance(obj1, dict):
                all_keys = set(obj1.keys()) | set(obj2.keys())
                for key in all_keys:
                    key_path = f"{path}.{key}" if path else key

                    if key not in obj1:
                        differences.append({
                                'path':      key_path,
                                'type':      'added',
                                'new_value': obj2[key]
                        })
                    elif key not in obj2:
                        differences.append({
                                'path':      key_path,
                                'type':      'removed',
                                'old_value': obj1[key]
                        })
                    else:
                        compare_recursive(obj1[key], obj2[key], key_path)

            elif isinstance(obj1, list):
                if len(obj1) != len(obj2):
                    differences.append({
                            'path':       path,
                            'type':       'list_length_change',
                            'old_length': len(obj1),
                            'new_length': len(obj2),
                            'old_value':  obj1,
                            'new_value':  obj2
                    })
                else:
                    for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                        compare_recursive(item1, item2, f"{path}[{i}]")

            else:
                if obj1 != obj2:
                    differences.append({
                            'path':      path,
                            'type':      'value_change',
                            'old_value': obj1,
                            'new_value': obj2
                    })

        compare_recursive(config1, config2)
        return differences
