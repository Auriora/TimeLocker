"""
Repository Configuration Backup Manager for TimeLocker

This module provides specialized backup management for repository configurations,
extending the base configuration backup functionality with repository-specific
features and safety mechanisms.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..config.configuration_backup_manager import (
    ConfigurationBackupManager, BackupReason, ConfigurationBackupMetadata
)
from ..interfaces.repository_management_models import (
    RepositoryConfig, Repository, RepositoryError
)
from ..interfaces.exceptions import ConfigurationBackupError

logger = logging.getLogger(__name__)


@dataclass
class RepositoryBackupMetadata(ConfigurationBackupMetadata):
    """Extended metadata for repository configuration backups"""
    repository_name: Optional[str] = None
    repository_uri: Optional[str] = None
    engine_type: Optional[str] = None
    operation_type: Optional[str] = None  # create, update, delete, reinitialize
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = super().to_dict()
        data.update({
            'repository_name': self.repository_name,
            'repository_uri': self.repository_uri,
            'engine_type': self.engine_type,
            'operation_type': self.operation_type
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepositoryBackupMetadata':
        """Create from dictionary"""
        base_data = {k: v for k, v in data.items() 
                    if k not in ['repository_name', 'repository_uri', 'engine_type', 'operation_type']}
        base_metadata = ConfigurationBackupMetadata.from_dict(base_data)
        
        return cls(
            backup_id=base_metadata.backup_id,
            created_at=base_metadata.created_at,
            reason=base_metadata.reason,
            size_bytes=base_metadata.size_bytes,
            sections=base_metadata.sections,
            validation_status=base_metadata.validation_status,
            checksum=base_metadata.checksum,
            retention_policy=base_metadata.retention_policy,
            source_file=base_metadata.source_file,
            backup_version=base_metadata.backup_version,
            tags=base_metadata.tags,
            repository_name=data.get('repository_name'),
            repository_uri=data.get('repository_uri'),
            engine_type=data.get('engine_type'),
            operation_type=data.get('operation_type')
        )


class RepositoryConfigurationBackupManager:
    """
    Specialized configuration backup manager for repository configurations.
    
    Provides automatic backups before risky operations, repository-specific
    backup cleanup, and configuration restoration with credential handling.
    """
    
    def __init__(self, backup_directory: Path):
        """
        Initialize the repository configuration backup manager.
        
        Args:
            backup_directory: Directory to store repository configuration backups
        """
        self.backup_directory = backup_directory / "repository_configs"
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        
        # Use the base configuration backup manager
        self._base_manager = ConfigurationBackupManager(self.backup_directory)
        
        # Repository-specific settings
        self.max_backups_per_repository = 5
        self.auto_backup_operations = {
            'reinitialize', 'delete', 'update_credentials', 'migrate'
        }

    def backup_repository_config(self, repo_config: RepositoryConfig, 
                                operation_type: str = "manual",
                                reason: BackupReason = BackupReason.MANUAL) -> str:
        """
        Create a backup of repository configuration before risky operations.
        
        Args:
            repo_config: Repository configuration to backup
            operation_type: Type of operation triggering the backup
            reason: Reason for creating the backup
            
        Returns:
            Backup identifier
            
        Raises:
            ConfigurationBackupError: If backup creation fails
        """
        try:
            # Create a temporary file with the repository configuration
            temp_config_file = self.backup_directory / f"temp_{repo_config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Prepare configuration data (excluding sensitive information)
            config_data = self._prepare_config_for_backup(repo_config)
            
            # Write configuration to temporary file
            with open(temp_config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Create backup using base manager
            tags = [f"repository:{repo_config.name}", f"operation:{operation_type}"]
            if operation_type in self.auto_backup_operations:
                tags.append("auto_backup")
            
            backup_id = self._base_manager.create_backup(temp_config_file, reason, tags)
            
            # Clean up temporary file
            temp_config_file.unlink()
            
            # Update backup metadata with repository-specific information
            self._update_repository_backup_metadata(
                backup_id, repo_config, operation_type
            )
            
            logger.info(f"Created repository configuration backup for '{repo_config.name}': {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to backup repository configuration for '{repo_config.name}': {e}")
            raise ConfigurationBackupError(f"Repository backup failed: {e}")

    def backup_before_risky_operation(self, repo_config: RepositoryConfig, 
                                    operation_type: str) -> str:
        """
        Automatically create backup before risky operations.
        
        Args:
            repo_config: Repository configuration to backup
            operation_type: Type of risky operation
            
        Returns:
            Backup identifier
        """
        if operation_type not in self.auto_backup_operations:
            logger.debug(f"Operation '{operation_type}' does not require automatic backup")
            return ""
        
        reason_map = {
            'reinitialize': BackupReason.PRE_UPDATE,
            'delete': BackupReason.PRE_UPDATE,
            'update_credentials': BackupReason.PRE_UPDATE,
            'migrate': BackupReason.PRE_MIGRATION
        }
        
        reason = reason_map.get(operation_type, BackupReason.AUTOMATIC)
        return self.backup_repository_config(repo_config, operation_type, reason)

    def list_repository_backups(self, repository_name: Optional[str] = None,
                              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List repository configuration backups.
        
        Args:
            repository_name: Filter backups for specific repository
            limit: Maximum number of backups to return
            
        Returns:
            List of repository backup information
        """
        all_backups = self._base_manager.list_backups(limit=None)
        
        # Filter for repository backups
        repo_backups = []
        for backup in all_backups:
            # Check if this is a repository backup
            tags = backup.get('tags', [])
            has_repo_tag = any(tag.startswith('repository:') for tag in tags)
            
            if has_repo_tag:
                if repository_name:
                    # Filter by repository name
                    repo_tag = f"repository:{repository_name}"
                    if repo_tag in tags:
                        repo_backups.append(backup)
                else:
                    repo_backups.append(backup)
        
        if limit:
            repo_backups = repo_backups[:limit]
        
        return repo_backups

    def restore_repository_config(self, backup_id: str, 
                                target_config: Optional[RepositoryConfig] = None) -> Dict[str, Any]:
        """
        Restore repository configuration from backup.
        
        Args:
            backup_id: Backup identifier to restore
            target_config: Optional target configuration to merge with
            
        Returns:
            Restored configuration data (credentials excluded)
            
        Raises:
            ConfigurationBackupError: If restoration fails
        """
        try:
            # Get backup file
            backup_file = self.backup_directory / f"{backup_id}.json"
            
            if not backup_file.exists():
                raise ConfigurationBackupError(f"Repository backup not found: {backup_id}")
            
            # Load backup configuration
            with open(backup_file, 'r') as f:
                backup_config = json.load(f)
            
            # Validate backup
            validation_result = self._base_manager.validate_backup(backup_id)
            if not validation_result.is_valid:
                logger.warning(f"Backup validation issues for {backup_id}: {validation_result.errors}")
            
            logger.info(f"Restored repository configuration from backup: {backup_id}")
            return backup_config
            
        except Exception as e:
            logger.error(f"Failed to restore repository configuration from backup {backup_id}: {e}")
            raise ConfigurationBackupError(f"Repository configuration restoration failed: {e}")

    def cleanup_repository_backups(self, repository_name: Optional[str] = None) -> int:
        """
        Clean up old repository configuration backups.
        
        Args:
            repository_name: Clean backups for specific repository, or all if None
            
        Returns:
            Number of backups cleaned up
        """
        try:
            if repository_name:
                return self._cleanup_repository_specific_backups(repository_name)
            else:
                return self._cleanup_all_repository_backups()
                
        except Exception as e:
            logger.error(f"Failed to cleanup repository backups: {e}")
            return 0

    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a repository backup.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Backup information dictionary or None if not found
        """
        backups = self._base_manager.list_backups()
        for backup in backups:
            if backup['backup_id'] == backup_id:
                return backup
        return None

    def validate_repository_backup(self, backup_id: str) -> bool:
        """
        Validate a repository configuration backup.
        
        Args:
            backup_id: Backup identifier to validate
            
        Returns:
            True if backup is valid
        """
        try:
            validation_result = self._base_manager.validate_backup(backup_id)
            return validation_result.is_valid
        except Exception as e:
            logger.error(f"Failed to validate repository backup {backup_id}: {e}")
            return False

    # Private helper methods

    def _prepare_config_for_backup(self, repo_config: RepositoryConfig) -> Dict[str, Any]:
        """
        Prepare repository configuration for backup, excluding sensitive data.
        
        Args:
            repo_config: Repository configuration
            
        Returns:
            Configuration dictionary safe for backup
        """
        config_dict = repo_config.to_dict()
        
        # Remove sensitive information that should not be backed up
        sensitive_fields = ['password', 'secret_key', 'access_key', 'token', 'credential']
        
        def remove_sensitive_recursive(obj):
            if isinstance(obj, dict):
                return {
                    k: remove_sensitive_recursive(v) 
                    for k, v in obj.items() 
                    if not any(sensitive in k.lower() for sensitive in sensitive_fields)
                }
            elif isinstance(obj, list):
                return [remove_sensitive_recursive(item) for item in obj]
            else:
                return obj
        
        safe_config = remove_sensitive_recursive(config_dict)
        
        # Add backup metadata
        safe_config['_backup_metadata'] = {
            'backed_up_at': datetime.utcnow().isoformat(),
            'backup_version': '1.0',
            'excluded_fields': [f for f in config_dict.keys() if f not in safe_config],
            'requires_credential_reentry': bool(safe_config.get('_backup_metadata', {}).get('excluded_fields'))
        }
        
        return safe_config

    def _update_repository_backup_metadata(self, backup_id: str, 
                                         repo_config: RepositoryConfig,
                                         operation_type: str) -> None:
        """Update backup metadata with repository-specific information"""
        try:
            # This would extend the base metadata with repository information
            # For now, we rely on tags to identify repository backups
            pass
        except Exception as e:
            logger.warning(f"Failed to update repository backup metadata: {e}")

    def _cleanup_repository_specific_backups(self, repository_name: str) -> int:
        """Clean up backups for a specific repository"""
        repo_backups = self.list_repository_backups(repository_name)
        
        if len(repo_backups) <= self.max_backups_per_repository:
            return 0
        
        # Sort by creation time and keep only the most recent ones
        repo_backups.sort(key=lambda x: x['created_at'], reverse=True)
        backups_to_remove = repo_backups[self.max_backups_per_repository:]
        
        cleaned_count = 0
        for backup in backups_to_remove:
            # Don't remove backups with critical tags (but allow removal of 'manual' backups)
            critical_tags = ['critical', 'milestone']
            if not any(tag in backup.get('tags', []) for tag in critical_tags):
                try:
                    # Use the base manager to properly remove the backup
                    if self._base_manager._remove_backup(backup['backup_id']):
                        cleaned_count += 1
                        logger.debug(f"Removed old repository backup: {backup['backup_id']}")
                except Exception as e:
                    logger.warning(f"Failed to remove backup {backup['backup_id']}: {e}")
        
        return cleaned_count

    def _cleanup_all_repository_backups(self) -> int:
        """Clean up backups for all repositories"""
        # Group backups by repository
        all_backups = self.list_repository_backups()
        repo_groups = {}
        
        for backup in all_backups:
            repo_tag = next((tag for tag in backup.get('tags', []) if tag.startswith('repository:')), None)
            if repo_tag:
                repo_name = repo_tag.split(':', 1)[1]
                if repo_name not in repo_groups:
                    repo_groups[repo_name] = []
                repo_groups[repo_name].append(backup)
        
        # Clean up each repository's backups
        total_cleaned = 0
        for repo_name in repo_groups:
            total_cleaned += self._cleanup_repository_specific_backups(repo_name)
        
        return total_cleaned