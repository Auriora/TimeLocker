"""
Repository Configuration Backup Integration for TimeLocker

This module integrates repository configurations with the TimeLocker configuration
backup system, ensuring repository settings are included in backups while
securely excluding credentials.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .configuration_backup_manager import ConfigurationBackupManager, BackupReason
from ..interfaces.repository_management_models import RepositoryConfig, BackupEngine, RepositoryType
from ..interfaces.exceptions import ConfigurationBackupError

logger = logging.getLogger(__name__)


class RepositoryConfigurationBackup:
    """
    Manages backup and restoration of repository configurations.
    
    Ensures repository configurations are included in TimeLocker backups
    while securely excluding all credential information.
    """
    
    def __init__(self, config_dir: Path, backup_manager: Optional[ConfigurationBackupManager] = None):
        """
        Initialize repository configuration backup manager.
        
        Args:
            config_dir: Configuration directory
            backup_manager: Optional ConfigurationBackupManager instance
        """
        self.config_dir = config_dir
        self.repositories_config_file = config_dir / "repositories.json"
        
        # Initialize backup manager if not provided
        if backup_manager is None:
            backup_dir = config_dir / "backups"
            from .configuration_validator import ConfigurationValidator
            validator = ConfigurationValidator()
            self.backup_manager = ConfigurationBackupManager(backup_dir, validator)
        else:
            self.backup_manager = backup_manager
    
    def backup_repository_configurations(self, reason: BackupReason = BackupReason.AUTOMATIC,
                                        tags: Optional[List[str]] = None) -> str:
        """
        Create backup of repository configurations with credential exclusion.
        
        Args:
            reason: Reason for creating the backup
            tags: Optional tags for the backup
            
        Returns:
            Backup identifier
            
        Raises:
            ConfigurationBackupError: If backup creation fails
        """
        try:
            if not self.repositories_config_file.exists():
                logger.info("No repository configuration file to backup")
                return ""
            
            # Load repository configurations
            with open(self.repositories_config_file, 'r') as f:
                repo_configs = json.load(f)
            
            # Create sanitized copy with credentials excluded
            sanitized_configs = self._sanitize_repository_configs(repo_configs)
            
            # Create temporary file with sanitized configurations
            temp_config_file = self.config_dir / "repositories_backup_temp.json"
            try:
                with open(temp_config_file, 'w') as f:
                    json.dump(sanitized_configs, f, indent=2)
                
                # Create backup using backup manager
                backup_tags = tags or []
                backup_tags.append("repository_config")
                
                backup_id = self.backup_manager.create_backup(
                    temp_config_file,
                    reason=reason,
                    tags=backup_tags
                )
                
                logger.info(f"Created repository configuration backup: {backup_id}")
                return backup_id
                
            finally:
                # Clean up temporary file
                if temp_config_file.exists():
                    temp_config_file.unlink()
        
        except Exception as e:
            logger.error(f"Failed to backup repository configurations: {e}")
            raise ConfigurationBackupError(f"Repository configuration backup failed: {e}")
    
    def _sanitize_repository_configs(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove all credential information from repository configurations.
        
        Args:
            configs: Repository configurations dictionary
            
        Returns:
            Sanitized configurations with credentials excluded
        """
        sanitized = {}
        
        # Process repositories section
        if 'repositories' in configs:
            sanitized['repositories'] = {}
            for repo_name, repo_data in configs['repositories'].items():
                sanitized_repo = repo_data.copy()
                
                # Remove credential-related fields
                credential_fields = [
                    'password', 'credentials', 'access_key', 'secret_key',
                    'access_key_id', 'secret_access_key', 'account_id',
                    'account_key', 'api_key', 'token', 'ssh_key'
                ]
                
                for field in credential_fields:
                    sanitized_repo.pop(field, None)
                
                # Remove credentials from metadata
                if 'metadata' in sanitized_repo and isinstance(sanitized_repo['metadata'], dict):
                    for field in credential_fields:
                        sanitized_repo['metadata'].pop(field, None)
                
                # Remove credentials from engine_config
                if 'engine_config' in sanitized_repo and isinstance(sanitized_repo['engine_config'], dict):
                    for field in credential_fields:
                        sanitized_repo['engine_config'].pop(field, None)
                
                # Add marker indicating credentials were excluded
                sanitized_repo['_credentials_excluded'] = True
                sanitized_repo['_backup_timestamp'] = datetime.utcnow().isoformat()
                
                sanitized['repositories'][repo_name] = sanitized_repo
        
        # Copy other sections without modification (they shouldn't contain credentials)
        for key, value in configs.items():
            if key != 'repositories':
                sanitized[key] = value
        
        # Add backup metadata
        sanitized['_backup_metadata'] = {
            'version': '1.0',
            'backup_type': 'repository_configuration',
            'credentials_excluded': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return sanitized
    
    def restore_repository_configurations(self, backup_id: str,
                                         validate_compatibility: bool = True) -> bool:
        """
        Restore repository configurations from backup.
        
        Args:
            backup_id: Backup identifier to restore from
            validate_compatibility: Whether to validate configuration compatibility
            
        Returns:
            True if restoration was successful
            
        Raises:
            ConfigurationBackupError: If restoration fails
        """
        try:
            # Restore backup to temporary file
            temp_restore_file = self.config_dir / "repositories_restore_temp.json"
            
            try:
                # Restore using backup manager
                self.backup_manager.restore_backup(backup_id, temp_restore_file)
                
                # Load restored configurations
                with open(temp_restore_file, 'r') as f:
                    restored_configs = json.load(f)
                
                # Validate compatibility if requested
                if validate_compatibility:
                    validation_result = self._validate_configuration_compatibility(restored_configs)
                    if not validation_result['compatible']:
                        raise ConfigurationBackupError(
                            f"Configuration incompatible: {', '.join(validation_result['issues'])}"
                        )
                
                # Merge with existing configurations (preserving credentials)
                merged_configs = self._merge_configurations(restored_configs)
                
                # Save merged configurations
                with open(self.repositories_config_file, 'w') as f:
                    json.dump(merged_configs, f, indent=2)
                
                logger.info(f"Restored repository configurations from backup: {backup_id}")
                return True
                
            finally:
                # Clean up temporary file
                if temp_restore_file.exists():
                    temp_restore_file.unlink()
        
        except Exception as e:
            logger.error(f"Failed to restore repository configurations: {e}")
            raise ConfigurationBackupError(f"Repository configuration restoration failed: {e}")
    
    def _validate_configuration_compatibility(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that restored configurations are compatible with current system.
        
        Args:
            configs: Restored configurations
            
        Returns:
            Dictionary with compatibility status and issues
        """
        result = {
            'compatible': True,
            'issues': [],
            'warnings': []
        }
        
        # Check backup metadata
        if '_backup_metadata' not in configs:
            result['warnings'].append("Backup metadata missing - may be from older version")
        
        # Validate repository configurations
        if 'repositories' in configs:
            for repo_name, repo_data in configs['repositories'].items():
                # Check required fields
                required_fields = ['name', 'uri', 'engine', 'type']
                missing_fields = [f for f in required_fields if f not in repo_data]
                
                if missing_fields:
                    result['compatible'] = False
                    result['issues'].append(
                        f"Repository '{repo_name}' missing required fields: {', '.join(missing_fields)}"
                    )
                
                # Validate engine type
                if 'engine' in repo_data:
                    try:
                        BackupEngine(repo_data['engine'])
                    except ValueError:
                        result['compatible'] = False
                        result['issues'].append(
                            f"Repository '{repo_name}' has unsupported engine: {repo_data['engine']}"
                        )
                
                # Validate repository type
                if 'type' in repo_data:
                    try:
                        RepositoryType(repo_data['type'])
                    except ValueError:
                        result['compatible'] = False
                        result['issues'].append(
                            f"Repository '{repo_name}' has unsupported type: {repo_data['type']}"
                        )
                
                # Check if credentials were excluded
                if repo_data.get('_credentials_excluded'):
                    result['warnings'].append(
                        f"Repository '{repo_name}' requires credential re-entry"
                    )
        
        return result
    
    def _merge_configurations(self, restored_configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge restored configurations with existing ones, preserving credentials.
        
        Args:
            restored_configs: Restored configurations from backup
            
        Returns:
            Merged configurations
        """
        # Load existing configurations if they exist
        existing_configs = {}
        if self.repositories_config_file.exists():
            try:
                with open(self.repositories_config_file, 'r') as f:
                    existing_configs = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load existing configurations: {e}")
        
        merged = restored_configs.copy()
        
        # Merge repositories, preserving existing credentials
        if 'repositories' in merged and 'repositories' in existing_configs:
            for repo_name, restored_repo in merged['repositories'].items():
                if repo_name in existing_configs['repositories']:
                    existing_repo = existing_configs['repositories'][repo_name]
                    
                    # Preserve credential fields from existing configuration
                    credential_fields = [
                        'password', 'credentials', 'access_key', 'secret_key',
                        'access_key_id', 'secret_access_key', 'account_id',
                        'account_key', 'api_key', 'token', 'ssh_key'
                    ]
                    
                    for field in credential_fields:
                        if field in existing_repo:
                            restored_repo[field] = existing_repo[field]
                    
                    # Remove backup markers
                    restored_repo.pop('_credentials_excluded', None)
                    restored_repo.pop('_backup_timestamp', None)
        
        # Remove backup metadata from final configuration
        merged.pop('_backup_metadata', None)
        
        return merged
    
    def get_credential_requirements(self, backup_id: str) -> List[Dict[str, str]]:
        """
        Get list of repositories that require credential re-entry after restoration.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            List of dictionaries with repository information requiring credentials
        """
        try:
            # Get backup metadata
            backups = self.backup_manager.list_backups()
            backup_info = next((b for b in backups if b['backup_id'] == backup_id), None)
            
            if not backup_info:
                return []
            
            # Load backup file
            backup_file = self.backup_manager.backup_directory / f"{backup_id}.json"
            if not backup_file.exists():
                return []
            
            with open(backup_file, 'r') as f:
                backup_configs = json.load(f)
            
            # Find repositories with excluded credentials
            credential_requirements = []
            
            if 'repositories' in backup_configs:
                for repo_name, repo_data in backup_configs['repositories'].items():
                    if repo_data.get('_credentials_excluded'):
                        credential_requirements.append({
                            'repository_name': repo_name,
                            'repository_uri': repo_data.get('uri', ''),
                            'repository_type': repo_data.get('type', ''),
                            'engine': repo_data.get('engine', ''),
                            'requires_password': True,
                            'requires_backend_credentials': repo_data.get('type') in ['s3', 'b2', 'sftp']
                        })
            
            return credential_requirements
        
        except Exception as e:
            logger.error(f"Failed to get credential requirements: {e}")
            return []
    
    def create_structured_export(self, output_file: Path,
                                 include_metadata: bool = True) -> bool:
        """
        Create structured export of repository configurations for cross-platform compatibility.
        
        Args:
            output_file: Output file path
            include_metadata: Whether to include metadata
            
        Returns:
            True if export was successful
        """
        try:
            if not self.repositories_config_file.exists():
                logger.warning("No repository configuration file to export")
                return False
            
            # Load repository configurations
            with open(self.repositories_config_file, 'r') as f:
                repo_configs = json.load(f)
            
            # Create sanitized export
            export_data = self._sanitize_repository_configs(repo_configs)
            
            # Add export metadata
            if include_metadata:
                export_data['_export_metadata'] = {
                    'version': '1.0',
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'platform': 'cross-platform',
                    'format': 'structured_json',
                    'credentials_excluded': True
                }
            
            # Write export file
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Created structured export: {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create structured export: {e}")
            return False
