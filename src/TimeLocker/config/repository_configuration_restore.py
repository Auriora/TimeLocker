"""
Repository Configuration Restoration for TimeLocker

This module handles restoration of repository configurations from backups,
including compatibility validation, credential re-entry prompts, and
optional exclusion of TimeLocker configuration from backups.
"""

import json
import logging
import getpass
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from .repository_configuration_backup import RepositoryConfigurationBackup
from ..utils.platform_compatibility import PlatformCompatibility, get_platform_compatibility
from ..interfaces.repository_management_models import BackupEngine, RepositoryType
from ..interfaces.exceptions import ConfigurationBackupError, ConfigurationError

logger = logging.getLogger(__name__)


class CredentialPromptHandler:
    """
    Handles interactive credential prompts during configuration restoration.
    """
    
    def __init__(self, interactive: bool = True):
        """
        Initialize credential prompt handler.
        
        Args:
            interactive: Whether to allow interactive prompts
        """
        self.interactive = interactive
        self._credential_cache: Dict[str, Dict[str, str]] = {}
    
    def prompt_for_repository_password(self, repository_name: str, repository_uri: str) -> Optional[str]:
        """
        Prompt user for repository password.
        
        Args:
            repository_name: Repository name
            repository_uri: Repository URI
            
        Returns:
            Password if provided, None otherwise
        """
        if not self.interactive:
            logger.warning(f"Non-interactive mode: cannot prompt for password for {repository_name}")
            return None
        
        try:
            print(f"\nRepository '{repository_name}' requires password")
            print(f"URI: {repository_uri}")
            password = getpass.getpass(f"Enter password for repository '{repository_name}': ")
            
            if password:
                # Cache for potential reuse
                self._credential_cache[repository_name] = {'password': password}
                return password
            
            return None
        
        except (KeyboardInterrupt, EOFError):
            logger.info("Password prompt cancelled by user")
            return None
        except Exception as e:
            logger.error(f"Failed to prompt for password: {e}")
            return None
    
    def prompt_for_backend_credentials(self, repository_name: str, backend_type: str) -> Optional[Dict[str, str]]:
        """
        Prompt user for backend-specific credentials.
        
        Args:
            repository_name: Repository name
            backend_type: Backend type (s3, b2, etc.)
            
        Returns:
            Dictionary of credentials if provided, None otherwise
        """
        if not self.interactive:
            logger.warning(f"Non-interactive mode: cannot prompt for {backend_type} credentials for {repository_name}")
            return None
        
        try:
            print(f"\nRepository '{repository_name}' requires {backend_type.upper()} credentials")
            
            credentials = {}
            
            if backend_type == 's3':
                credentials['access_key_id'] = input("AWS Access Key ID: ").strip()
                credentials['secret_access_key'] = getpass.getpass("AWS Secret Access Key: ")
                region = input("AWS Region (optional, press Enter to skip): ").strip()
                if region:
                    credentials['region'] = region
            
            elif backend_type == 'b2':
                credentials['account_id'] = input("B2 Account ID: ").strip()
                credentials['account_key'] = getpass.getpass("B2 Account Key: ")
            
            elif backend_type == 'sftp':
                credentials['username'] = input("SFTP Username: ").strip()
                password = getpass.getpass("SFTP Password (or press Enter for key-based auth): ")
                if password:
                    credentials['password'] = password
                else:
                    key_path = input("SSH Key Path: ").strip()
                    if key_path:
                        credentials['key_path'] = key_path
            
            # Cache credentials
            if credentials:
                cache_key = f"{repository_name}:{backend_type}"
                self._credential_cache[cache_key] = credentials
            
            return credentials if credentials else None
        
        except (KeyboardInterrupt, EOFError):
            logger.info("Credential prompt cancelled by user")
            return None
        except Exception as e:
            logger.error(f"Failed to prompt for credentials: {e}")
            return None
    
    def get_cached_credentials(self, repository_name: str, credential_type: str = 'password') -> Optional[Any]:
        """
        Get cached credentials if available.
        
        Args:
            repository_name: Repository name
            credential_type: Type of credential
            
        Returns:
            Cached credentials if available, None otherwise
        """
        if credential_type == 'password':
            return self._credential_cache.get(repository_name, {}).get('password')
        else:
            cache_key = f"{repository_name}:{credential_type}"
            return self._credential_cache.get(cache_key)


class RepositoryConfigurationRestore:
    """
    Manages restoration of repository configurations with compatibility validation
    and credential re-entry.
    """
    
    def __init__(self, config_dir: Path, 
                 backup_manager: Optional[RepositoryConfigurationBackup] = None,
                 platform_compat: Optional[PlatformCompatibility] = None):
        """
        Initialize configuration restore manager.
        
        Args:
            config_dir: Configuration directory
            backup_manager: Optional RepositoryConfigurationBackup instance
            platform_compat: Optional PlatformCompatibility instance
        """
        self.config_dir = config_dir
        
        # Initialize backup manager if not provided
        if backup_manager is None:
            self.backup_manager = RepositoryConfigurationBackup(config_dir)
        else:
            self.backup_manager = backup_manager
        
        # Initialize platform compatibility
        if platform_compat is None:
            self.platform_compat = get_platform_compatibility()
        else:
            self.platform_compat = platform_compat
        
        self.credential_handler = CredentialPromptHandler()
    
    def restore_with_credential_prompts(self, backup_id: str,
                                       validate_compatibility: bool = True,
                                       interactive: bool = True) -> Dict[str, Any]:
        """
        Restore repository configurations with interactive credential prompts.
        
        Args:
            backup_id: Backup identifier to restore
            validate_compatibility: Whether to validate compatibility
            interactive: Whether to allow interactive prompts
            
        Returns:
            Dictionary with restoration results
        """
        result = {
            'success': False,
            'repositories_restored': [],
            'credentials_required': [],
            'credentials_entered': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            # Set interactive mode
            self.credential_handler.interactive = interactive
            
            # Get credential requirements
            credential_reqs = self.backup_manager.get_credential_requirements(backup_id)
            result['credentials_required'] = [req['repository_name'] for req in credential_reqs]
            
            # Restore configurations
            self.backup_manager.restore_repository_configurations(
                backup_id,
                validate_compatibility=validate_compatibility
            )
            
            # Prompt for credentials if interactive
            if interactive and credential_reqs:
                print("\n" + "="*60)
                print("CREDENTIAL RE-ENTRY REQUIRED")
                print("="*60)
                print(f"\n{len(credential_reqs)} repository(ies) require credential re-entry")
                print("Credentials were excluded from backup for security.\n")
                
                for req in credential_reqs:
                    repo_name = req['repository_name']
                    
                    # Prompt for repository password
                    if req.get('requires_password'):
                        password = self.credential_handler.prompt_for_repository_password(
                            repo_name,
                            req['repository_uri']
                        )
                        
                        if password:
                            result['credentials_entered'].append({
                                'repository': repo_name,
                                'type': 'password'
                            })
                            # Store password using credential manager
                            # (This would integrate with SecurityService in production)
                            logger.info(f"Password entered for repository: {repo_name}")
                        else:
                            result['warnings'].append(
                                f"No password entered for repository: {repo_name}"
                            )
                    
                    # Prompt for backend credentials if needed
                    if req.get('requires_backend_credentials'):
                        backend_type = req['repository_type']
                        credentials = self.credential_handler.prompt_for_backend_credentials(
                            repo_name,
                            backend_type
                        )
                        
                        if credentials:
                            result['credentials_entered'].append({
                                'repository': repo_name,
                                'type': f'{backend_type}_credentials'
                            })
                            logger.info(f"{backend_type.upper()} credentials entered for repository: {repo_name}")
                        else:
                            result['warnings'].append(
                                f"No {backend_type.upper()} credentials entered for repository: {repo_name}"
                            )
            
            result['success'] = True
            result['repositories_restored'] = [req['repository_name'] for req in credential_reqs]
            
            if result['warnings']:
                print("\n" + "="*60)
                print("WARNINGS")
                print("="*60)
                for warning in result['warnings']:
                    print(f"⚠️  {warning}")
            
            print("\n" + "="*60)
            print("RESTORATION COMPLETE")
            print("="*60)
            print(f"✓ Restored {len(result['repositories_restored'])} repository configuration(s)")
            print(f"✓ Entered credentials for {len(result['credentials_entered'])} repository(ies)")
            
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Configuration restoration failed: {e}")
        
        return result
    
    def validate_platform_compatibility(self, backup_id: str) -> Dict[str, Any]:
        """
        Validate that backup is compatible with current platform.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Dictionary with compatibility validation results
        """
        result = {
            'compatible': True,
            'platform_issues': [],
            'path_conversions_needed': [],
            'warnings': []
        }
        
        try:
            # Load backup file
            backup_file = self.backup_manager.backup_manager.backup_directory / f"{backup_id}.json"
            if not backup_file.exists():
                result['compatible'] = False
                result['platform_issues'].append(f"Backup file not found: {backup_id}")
                return result
            
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Check backup metadata for platform information
            backup_metadata = backup_data.get('_backup_metadata', {})
            source_platform = backup_metadata.get('source_platform', 'unknown')
            
            current_platform = self.platform_compat.current_platform.value
            
            if source_platform != 'unknown' and source_platform != current_platform:
                result['warnings'].append(
                    f"Backup created on {source_platform}, restoring to {current_platform}"
                )
            
            # Check repository URIs for platform-specific paths
            if 'repositories' in backup_data:
                for repo_name, repo_data in backup_data['repositories'].items():
                    uri = repo_data.get('uri', '')
                    
                    # Check if URI needs conversion
                    if self._needs_path_conversion(uri):
                        result['path_conversions_needed'].append({
                            'repository': repo_name,
                            'original_uri': uri,
                            'converted_uri': self.platform_compat.normalize_repository_uri(uri)
                        })
            
            # Check platform capabilities
            capabilities = self.platform_compat.get_platform_capabilities()
            
            if not capabilities['native_credential_store']:
                result['warnings'].append(
                    "Platform does not support native credential store - using encrypted file storage"
                )
        
        except Exception as e:
            result['compatible'] = False
            result['platform_issues'].append(f"Compatibility validation failed: {e}")
        
        return result
    
    def _needs_path_conversion(self, uri: str) -> bool:
        """
        Check if URI needs platform-specific path conversion.
        
        Args:
            uri: Repository URI
            
        Returns:
            True if conversion needed, False otherwise
        """
        # Network URIs don't need conversion
        if uri.startswith(("s3:", "b2:", "sftp:", "rest:", "http:", "https:")):
            return False
        
        # Check for platform-specific path indicators
        current_platform = self.platform_compat.current_platform
        
        # Windows paths on non-Windows platforms
        if current_platform != self.platform_compat.Platform.WINDOWS:
            if uri.find(':\\') != -1 or uri.find('C:') != -1:
                return True
        
        # Unix paths on Windows
        if current_platform == self.platform_compat.Platform.WINDOWS:
            if uri.startswith('/') and not uri.startswith('//'):
                return True
        
        return False
    
    def apply_path_conversions(self, backup_id: str) -> bool:
        """
        Apply platform-specific path conversions to restored configurations.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            True if conversions applied successfully
        """
        try:
            # Get path conversions needed
            compat_result = self.validate_platform_compatibility(backup_id)
            
            if not compat_result['path_conversions_needed']:
                logger.info("No path conversions needed")
                return True
            
            # Load current configurations
            config_file = self.config_dir / "repositories.json"
            if not config_file.exists():
                logger.warning("No configuration file to update")
                return False
            
            with open(config_file, 'r') as f:
                configs = json.load(f)
            
            # Apply conversions
            conversions_applied = 0
            for conversion in compat_result['path_conversions_needed']:
                repo_name = conversion['repository']
                if repo_name in configs.get('repositories', {}):
                    old_uri = configs['repositories'][repo_name]['uri']
                    new_uri = conversion['converted_uri']
                    
                    configs['repositories'][repo_name]['uri'] = new_uri
                    conversions_applied += 1
                    
                    logger.info(f"Converted path for {repo_name}: {old_uri} -> {new_uri}")
            
            # Save updated configurations
            if conversions_applied > 0:
                with open(config_file, 'w') as f:
                    json.dump(configs, f, indent=2)
                
                logger.info(f"Applied {conversions_applied} path conversion(s)")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to apply path conversions: {e}")
            return False
    
    def create_exclusion_filter(self, exclude_timelocker_config: bool = False) -> Dict[str, Any]:
        """
        Create filter for excluding TimeLocker configuration from backups.
        
        Args:
            exclude_timelocker_config: Whether to exclude TimeLocker config
            
        Returns:
            Dictionary with exclusion filter configuration
        """
        filter_config = {
            'exclude_patterns': [],
            'exclude_paths': [],
            'exclude_sections': []
        }
        
        if exclude_timelocker_config:
            # Exclude TimeLocker configuration directory
            config_dir = self.platform_compat.get_platform_specific_config_dir()
            filter_config['exclude_paths'].append(str(config_dir))
            
            # Exclude specific configuration files
            filter_config['exclude_patterns'].extend([
                '*/timelocker/config.json',
                '*/timelocker/repositories.json',
                '*/.timelocker/*',
                '*/TimeLocker/*'
            ])
            
            # Exclude configuration sections
            filter_config['exclude_sections'].extend([
                'timelocker_settings',
                'application_config'
            ])
            
            logger.info("Created exclusion filter for TimeLocker configuration")
        
        return filter_config
    
    def restore_with_exclusions(self, backup_id: str,
                                exclude_timelocker_config: bool = False) -> Dict[str, Any]:
        """
        Restore configuration with optional exclusions.
        
        Args:
            backup_id: Backup identifier
            exclude_timelocker_config: Whether to exclude TimeLocker config
            
        Returns:
            Dictionary with restoration results
        """
        result = {
            'success': False,
            'excluded_items': [],
            'errors': []
        }
        
        try:
            # Create exclusion filter
            exclusion_filter = self.create_exclusion_filter(exclude_timelocker_config)
            
            # Restore with credential prompts
            restore_result = self.restore_with_credential_prompts(
                backup_id,
                validate_compatibility=True,
                interactive=True
            )
            
            # Apply exclusions if needed
            if exclude_timelocker_config:
                # Remove excluded sections from restored configuration
                config_file = self.config_dir / "repositories.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        configs = json.load(f)
                    
                    for section in exclusion_filter['exclude_sections']:
                        if section in configs:
                            del configs[section]
                            result['excluded_items'].append(section)
                    
                    with open(config_file, 'w') as f:
                        json.dump(configs, f, indent=2)
            
            result['success'] = restore_result['success']
            result['restore_details'] = restore_result
            
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Restoration with exclusions failed: {e}")
        
        return result
