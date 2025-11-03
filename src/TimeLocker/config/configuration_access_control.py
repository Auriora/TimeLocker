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

import os
import stat
import pwd
import grp
import logging
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum

from .configuration_audit_logger import ConfigurationAuditLogger, ConfigurationOperation
from ..interfaces.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """Access levels for configuration resources"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class PermissionScope(Enum):
    """Scope of permission application"""
    USER = "user"
    GROUP = "group"
    SYSTEM = "system"
    PUBLIC = "public"


@dataclass
class AccessControlRule:
    """Represents an access control rule"""
    user_id: Optional[str]
    group_id: Optional[str]
    access_level: AccessLevel
    scope: PermissionScope
    resource_pattern: str
    description: str
    created_at: str
    expires_at: Optional[str] = None


@dataclass
class FilePermissionInfo:
    """Information about file permissions"""
    path: str
    owner: str
    group: str
    permissions: str
    octal_permissions: str
    readable: bool
    writable: bool
    executable: bool
    secure: bool


class ConfigurationAccessControl:
    """
    Manages access control and file permissions for configuration resources.
    
    Provides platform-specific file permission management and access monitoring
    for configuration files and directories.
    """

    def __init__(self, config_dir: Optional[Path] = None,
                 audit_logger: Optional[ConfigurationAuditLogger] = None):
        """
        Initialize configuration access control.
        
        Args:
            config_dir: Configuration directory to protect
            audit_logger: Audit logger for access monitoring
        """
        if config_dir is None:
            from .configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory()
        
        self.config_dir = Path(config_dir)
        self.audit_logger = audit_logger
        
        # Platform detection
        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        self.is_unix = self.platform in ["linux", "darwin"]
        
        # Access control rules
        self.access_rules: List[AccessControlRule] = []
        
        # Security settings
        self.secure_permissions = {
            "config_files": 0o600,  # rw-------
            "config_dirs": 0o700,   # rwx------
            "backup_files": 0o600,  # rw-------
            "log_files": 0o640,     # rw-r-----
            "temp_files": 0o600     # rw-------
        }
        
        # Initialize access control
        self._initialize_access_control()

    def _initialize_access_control(self) -> None:
        """Initialize access control system"""
        try:
            # Ensure config directory exists with proper permissions
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.set_secure_permissions(self.config_dir, "config_dirs")
            
            # Create default access rules
            self._create_default_access_rules()
            
            logger.info("Configuration access control initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize access control: {e}")

    def _create_default_access_rules(self) -> None:
        """Create default access control rules"""
        try:
            current_user = self._get_current_user()
            
            # User has admin access to their own config
            self.access_rules.append(AccessControlRule(
                user_id=current_user,
                group_id=None,
                access_level=AccessLevel.ADMIN,
                scope=PermissionScope.USER,
                resource_pattern="*",
                description="Owner has full access to configuration",
                created_at=self._get_current_timestamp()
            ))
            
            # System administrators have admin access
            if not self.is_windows:
                admin_groups = ["sudo", "wheel", "admin"]
                user_groups = self._get_user_groups(current_user)
                
                for group in admin_groups:
                    if group in user_groups:
                        self.access_rules.append(AccessControlRule(
                            user_id=None,
                            group_id=group,
                            access_level=AccessLevel.ADMIN,
                            scope=PermissionScope.GROUP,
                            resource_pattern="*",
                            description=f"System administrators ({group}) have full access",
                            created_at=self._get_current_timestamp()
                        ))
                        break
            
        except Exception as e:
            logger.warning(f"Failed to create default access rules: {e}")

    def set_secure_permissions(self, path: Path, resource_type: str) -> bool:
        """
        Set secure permissions on a file or directory.
        
        Args:
            path: Path to secure
            resource_type: Type of resource (config_files, config_dirs, etc.)
            
        Returns:
            bool: True if permissions were set successfully
        """
        try:
            if self.is_windows:
                return self._set_windows_permissions(path, resource_type)
            else:
                return self._set_unix_permissions(path, resource_type)
                
        except Exception as e:
            logger.error(f"Failed to set secure permissions on {path}: {e}")
            if self.audit_logger:
                self.audit_logger.log_configuration_access(
                    operation=ConfigurationOperation.UPDATE,
                    description=f"Failed to set permissions on {path}",
                    success=False,
                    metadata={"path": str(path), "resource_type": resource_type, "error": str(e)}
                )
            return False

    def _set_unix_permissions(self, path: Path, resource_type: str) -> bool:
        """Set Unix-style permissions"""
        try:
            permissions = self.secure_permissions.get(resource_type, 0o600)
            
            # Set permissions
            os.chmod(path, permissions)
            
            # Verify permissions were set correctly
            actual_permissions = oct(path.stat().st_mode)[-3:]
            expected_permissions = oct(permissions)[-3:]
            
            if actual_permissions != expected_permissions:
                logger.warning(f"Permission mismatch on {path}: expected {expected_permissions}, got {actual_permissions}")
                return False
            
            if self.audit_logger:
                self.audit_logger.log_configuration_access(
                    operation=ConfigurationOperation.UPDATE,
                    description=f"Set secure permissions on {path}",
                    success=True,
                    metadata={
                        "path": str(path),
                        "resource_type": resource_type,
                        "permissions": expected_permissions
                    }
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Unix permissions on {path}: {e}")
            return False

    def _set_windows_permissions(self, path: Path, resource_type: str) -> bool:
        """Set Windows-style permissions using icacls"""
        try:
            import subprocess
            
            # Remove inherited permissions and grant full control to current user only
            current_user = os.getenv('USERNAME', 'unknown')
            
            # Reset permissions
            subprocess.run([
                'icacls', str(path), '/reset'
            ], check=True, capture_output=True)
            
            # Remove inheritance
            subprocess.run([
                'icacls', str(path), '/inheritance:r'
            ], check=True, capture_output=True)
            
            # Grant full control to current user
            subprocess.run([
                'icacls', str(path), f'/grant:r', f'{current_user}:F'
            ], check=True, capture_output=True)
            
            # For directories, apply to subdirectories and files
            if path.is_dir():
                subprocess.run([
                    'icacls', str(path), f'/grant:r', f'{current_user}:(OI)(CI)F'
                ], check=True, capture_output=True)
            
            if self.audit_logger:
                self.audit_logger.log_configuration_access(
                    operation=ConfigurationOperation.UPDATE,
                    description=f"Set secure Windows permissions on {path}",
                    success=True,
                    metadata={
                        "path": str(path),
                        "resource_type": resource_type,
                        "user": current_user
                    }
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Windows permissions on {path}: {e}")
            return False

    def get_file_permissions(self, path: Path) -> FilePermissionInfo:
        """
        Get detailed file permission information.
        
        Args:
            path: Path to analyze
            
        Returns:
            FilePermissionInfo: Detailed permission information
        """
        try:
            if not path.exists():
                raise ConfigurationError(f"Path does not exist: {path}")
            
            stat_info = path.stat()
            
            if self.is_windows:
                return self._get_windows_permissions(path, stat_info)
            else:
                return self._get_unix_permissions(path, stat_info)
                
        except Exception as e:
            logger.error(f"Failed to get file permissions for {path}: {e}")
            raise ConfigurationError(f"Failed to get permissions: {e}")

    def _get_unix_permissions(self, path: Path, stat_info) -> FilePermissionInfo:
        """Get Unix-style permission information"""
        try:
            # Get owner and group names
            try:
                owner = pwd.getpwuid(stat_info.st_uid).pw_name
            except KeyError:
                owner = str(stat_info.st_uid)
            
            try:
                group = grp.getgrgid(stat_info.st_gid).gr_name
            except KeyError:
                group = str(stat_info.st_gid)
            
            # Get permission bits
            mode = stat_info.st_mode
            permissions = stat.filemode(mode)
            octal_permissions = oct(mode)[-3:]
            
            # Check access for current user
            readable = os.access(path, os.R_OK)
            writable = os.access(path, os.W_OK)
            executable = os.access(path, os.X_OK)
            
            # Determine if permissions are secure
            secure = self._is_secure_unix_permissions(mode, path.is_dir())
            
            return FilePermissionInfo(
                path=str(path),
                owner=owner,
                group=group,
                permissions=permissions,
                octal_permissions=octal_permissions,
                readable=readable,
                writable=writable,
                executable=executable,
                secure=secure
            )
            
        except Exception as e:
            logger.error(f"Failed to get Unix permissions: {e}")
            raise

    def _get_windows_permissions(self, path: Path, stat_info) -> FilePermissionInfo:
        """Get Windows-style permission information"""
        try:
            # Windows permission analysis is more complex
            # For now, provide basic information
            owner = "unknown"
            group = "unknown"
            
            # Check basic access
            readable = os.access(path, os.R_OK)
            writable = os.access(path, os.W_OK)
            executable = os.access(path, os.X_OK)
            
            # Simple permission representation
            permissions = ""
            permissions += "r" if readable else "-"
            permissions += "w" if writable else "-"
            permissions += "x" if executable else "-"
            
            # For Windows, consider secure if only current user has access
            secure = self._is_secure_windows_permissions(path)
            
            return FilePermissionInfo(
                path=str(path),
                owner=owner,
                group=group,
                permissions=permissions,
                octal_permissions="N/A",
                readable=readable,
                writable=writable,
                executable=executable,
                secure=secure
            )
            
        except Exception as e:
            logger.error(f"Failed to get Windows permissions: {e}")
            raise

    def _is_secure_unix_permissions(self, mode: int, is_directory: bool) -> bool:
        """Check if Unix permissions are secure"""
        # Extract permission bits
        owner_perms = (mode & 0o700) >> 6
        group_perms = (mode & 0o070) >> 3
        other_perms = mode & 0o007
        
        # For configuration files/directories, others should have no access
        if other_perms != 0:
            return False
        
        # Group should have minimal access
        if group_perms > 0o4:  # More than read access
            return False
        
        # Owner should have appropriate access
        if is_directory:
            return owner_perms == 0o7  # rwx for directories
        else:
            return owner_perms in [0o6, 0o4]  # rw- or r-- for files

    def _is_secure_windows_permissions(self, path: Path) -> bool:
        """Check if Windows permissions are secure (simplified)"""
        try:
            # This is a simplified check
            # In a full implementation, we would use Windows APIs to check ACLs
            return os.access(path, os.R_OK) and os.access(path, os.W_OK)
        except Exception:
            return False

    def check_access_permission(
        self,
        user_id: str,
        resource_path: str,
        operation: ConfigurationOperation
    ) -> bool:
        """
        Check if user has permission for operation on resource.
        
        Args:
            user_id: User requesting access
            resource_path: Path to resource
            operation: Operation being attempted
            
        Returns:
            bool: True if access is permitted
        """
        try:
            # Check access rules
            required_level = self._get_required_access_level(operation)
            user_level = self._get_user_access_level(user_id, resource_path)
            
            access_granted = self._compare_access_levels(user_level, required_level)
            
            # Log access check
            if self.audit_logger:
                self.audit_logger.log_configuration_access(
                    operation=operation,
                    description=f"Access check for {resource_path}",
                    success=access_granted,
                    user_id=user_id,
                    metadata={
                        "resource_path": resource_path,
                        "required_level": required_level.value,
                        "user_level": user_level.value,
                        "access_granted": access_granted
                    }
                )
            
            return access_granted
            
        except Exception as e:
            logger.error(f"Failed to check access permission: {e}")
            return False

    def _get_required_access_level(self, operation: ConfigurationOperation) -> AccessLevel:
        """Get required access level for operation"""
        read_operations = {
            ConfigurationOperation.READ,
            ConfigurationOperation.VERIFY
        }
        
        write_operations = {
            ConfigurationOperation.WRITE,
            ConfigurationOperation.UPDATE,
            ConfigurationOperation.CREATE,
            ConfigurationOperation.ENCRYPT,
            ConfigurationOperation.DECRYPT,
            ConfigurationOperation.BACKUP
        }
        
        admin_operations = {
            ConfigurationOperation.DELETE,
            ConfigurationOperation.MIGRATE,
            ConfigurationOperation.RESTORE,
            ConfigurationOperation.SIGN
        }
        
        if operation in read_operations:
            return AccessLevel.READ
        elif operation in write_operations:
            return AccessLevel.WRITE
        elif operation in admin_operations:
            return AccessLevel.ADMIN
        else:
            return AccessLevel.WRITE  # Default to write for unknown operations

    def _get_user_access_level(self, user_id: str, resource_path: str) -> AccessLevel:
        """Get user's access level for resource"""
        max_level = AccessLevel.NONE
        
        for rule in self.access_rules:
            if self._rule_matches_user_and_resource(rule, user_id, resource_path):
                if self._compare_access_levels(rule.access_level, max_level):
                    max_level = rule.access_level
        
        return max_level

    def _rule_matches_user_and_resource(
        self,
        rule: AccessControlRule,
        user_id: str,
        resource_path: str
    ) -> bool:
        """Check if access rule matches user and resource"""
        # Check user match
        if rule.user_id and rule.user_id != user_id:
            return False
        
        # Check group match
        if rule.group_id:
            user_groups = self._get_user_groups(user_id)
            if rule.group_id not in user_groups:
                return False
        
        # Check resource pattern match
        import fnmatch
        if not fnmatch.fnmatch(resource_path, rule.resource_pattern):
            return False
        
        # Check expiration
        if rule.expires_at:
            from datetime import datetime
            try:
                expires = datetime.fromisoformat(rule.expires_at)
                if datetime.now() > expires:
                    return False
            except ValueError:
                pass
        
        return True

    def _compare_access_levels(self, level1: AccessLevel, level2: AccessLevel) -> bool:
        """Compare if level1 >= level2"""
        level_order = {
            AccessLevel.NONE: 0,
            AccessLevel.READ: 1,
            AccessLevel.WRITE: 2,
            AccessLevel.ADMIN: 3
        }
        
        return level_order.get(level1, 0) >= level_order.get(level2, 0)

    def _get_current_user(self) -> str:
        """Get current user identifier"""
        try:
            if self.is_windows:
                return os.getenv('USERNAME', 'unknown')
            else:
                return os.getenv('USER', 'unknown')
        except Exception:
            return 'unknown'

    def _get_user_groups(self, user_id: str) -> List[str]:
        """Get groups for user"""
        try:
            if self.is_windows:
                # Windows group checking would require more complex implementation
                return []
            else:
                import grp
                groups = []
                for group in grp.getgrall():
                    if user_id in group.gr_mem:
                        groups.append(group.gr_name)
                return groups
        except Exception:
            return []

    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()

    def secure_configuration_directory(self) -> Dict[str, Any]:
        """
        Secure the entire configuration directory and its contents.
        
        Returns:
            Dict containing security operation results
        """
        try:
            results = {
                "directories_secured": 0,
                "files_secured": 0,
                "errors": []
            }
            
            # Secure main config directory
            if self.set_secure_permissions(self.config_dir, "config_dirs"):
                results["directories_secured"] += 1
            else:
                results["errors"].append(f"Failed to secure {self.config_dir}")
            
            # Secure all subdirectories and files
            for item in self.config_dir.rglob("*"):
                try:
                    if item.is_dir():
                        resource_type = "config_dirs"
                        if self.set_secure_permissions(item, resource_type):
                            results["directories_secured"] += 1
                        else:
                            results["errors"].append(f"Failed to secure directory {item}")
                    else:
                        # Determine file type
                        if item.suffix in ['.log']:
                            resource_type = "log_files"
                        elif 'backup' in item.name:
                            resource_type = "backup_files"
                        elif item.suffix in ['.tmp', '.temp']:
                            resource_type = "temp_files"
                        else:
                            resource_type = "config_files"
                        
                        if self.set_secure_permissions(item, resource_type):
                            results["files_secured"] += 1
                        else:
                            results["errors"].append(f"Failed to secure file {item}")
                            
                except Exception as e:
                    results["errors"].append(f"Error processing {item}: {e}")
            
            # Log security operation
            if self.audit_logger:
                self.audit_logger.log_configuration_access(
                    operation=ConfigurationOperation.UPDATE,
                    description="Secured configuration directory",
                    success=len(results["errors"]) == 0,
                    metadata=results
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to secure configuration directory: {e}")
            return {
                "directories_secured": 0,
                "files_secured": 0,
                "errors": [str(e)]
            }

    def audit_file_permissions(self) -> List[Dict[str, Any]]:
        """
        Audit file permissions in configuration directory.
        
        Returns:
            List of permission audit results
        """
        try:
            audit_results = []
            
            for item in self.config_dir.rglob("*"):
                try:
                    if item.is_file() or item.is_dir():
                        perm_info = self.get_file_permissions(item)
                        
                        audit_result = {
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "owner": perm_info.owner,
                            "group": perm_info.group,
                            "permissions": perm_info.permissions,
                            "octal_permissions": perm_info.octal_permissions,
                            "secure": perm_info.secure,
                            "readable": perm_info.readable,
                            "writable": perm_info.writable,
                            "executable": perm_info.executable
                        }
                        
                        audit_results.append(audit_result)
                        
                except Exception as e:
                    audit_results.append({
                        "path": str(item),
                        "error": str(e),
                        "secure": False
                    })
            
            # Log audit operation
            if self.audit_logger:
                insecure_count = sum(1 for result in audit_results if not result.get("secure", False))
                self.audit_logger.log_configuration_access(
                    operation=ConfigurationOperation.READ,
                    description="Audited file permissions",
                    success=True,
                    metadata={
                        "total_items": len(audit_results),
                        "insecure_items": insecure_count
                    }
                )
            
            return audit_results
            
        except Exception as e:
            logger.error(f"Failed to audit file permissions: {e}")
            return []