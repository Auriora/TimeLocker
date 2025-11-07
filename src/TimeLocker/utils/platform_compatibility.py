"""
Cross-Platform Compatibility Utilities for TimeLocker

This module provides platform-specific path handling, credential store integration,
and consistent repository operations across Windows, macOS, and Linux.
"""

import os
import sys
import platform
import re
import logging
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class PlatformCompatibility:
    """
    Provides cross-platform compatibility for repository operations.
    
    Handles platform-specific path conversions, credential store integration,
    and ensures consistent repository operations across different operating systems.
    """
    
    def __init__(self):
        """Initialize platform compatibility manager"""
        self.current_platform = self._detect_platform()
        logger.info(f"Detected platform: {self.current_platform.value}")
    
    @staticmethod
    def _detect_platform() -> Platform:
        """
        Detect the current operating system platform.
        
        Returns:
            Platform enum value
        """
        system = platform.system().lower()
        
        if system == "windows":
            return Platform.WINDOWS
        elif system == "darwin":
            return Platform.MACOS
        elif system == "linux":
            return Platform.LINUX
        else:
            return Platform.UNKNOWN
    
    def normalize_repository_uri(self, uri: str, target_platform: Optional[Platform] = None) -> str:
        """
        Normalize repository URI for the target platform.
        
        Args:
            uri: Repository URI to normalize
            target_platform: Target platform (defaults to current platform)
            
        Returns:
            Normalized URI for the target platform
        """
        if target_platform is None:
            target_platform = self.current_platform
        
        # Handle different URI schemes
        if uri.startswith(("s3:", "b2:", "sftp:", "rest:", "http:", "https:")):
            # Network URIs don't need platform-specific normalization
            return uri
        
        # Handle local file paths
        if uri.startswith("file://"):
            path = uri[7:]  # Remove file:// prefix
            normalized_path = self._normalize_local_path(path, target_platform)
            return f"file://{normalized_path}"
        
        # Handle bare paths (assume local)
        if self._is_local_path(uri):
            normalized_path = self._normalize_local_path(uri, target_platform)
            return normalized_path
        
        # Return as-is if we can't determine the type
        return uri
    
    def _is_local_path(self, path: str) -> bool:
        """
        Check if a path is a local filesystem path.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is local, False otherwise
        """
        # Check for URI schemes
        if "://" in path and not path.startswith("file://"):
            return False
        
        # Check for Windows drive letters
        if re.match(r'^[A-Za-z]:[/\\]', path):
            return True
        
        # Check for Unix absolute paths
        if path.startswith('/'):
            return True
        
        # Check for relative paths
        if path.startswith(('./', '../', '.\\', '..\\')):
            return True
        
        return False
    
    def _normalize_local_path(self, path: str, target_platform: Platform) -> str:
        """
        Normalize local filesystem path for target platform.
        
        Args:
            path: Local path to normalize
            target_platform: Target platform
            
        Returns:
            Normalized path for target platform
        """
        # Convert to Path object for manipulation
        try:
            if target_platform == Platform.WINDOWS:
                # Convert to Windows path
                if path.startswith('/'):
                    # Unix-style path - convert to Windows
                    # Handle /mnt/c/ style paths (WSL)
                    if path.startswith('/mnt/'):
                        match = re.match(r'/mnt/([a-z])/(.*)', path)
                        if match:
                            drive = match.group(1).upper()
                            rest = match.group(2).replace('/', '\\')
                            return f"{drive}:\\{rest}"
                    
                    # Regular Unix path - use as-is with forward slashes
                    return path.replace('/', '\\')
                else:
                    # Already Windows-style
                    return path.replace('/', '\\')
            
            else:  # macOS or Linux
                # Convert to Unix path
                if re.match(r'^[A-Za-z]:[/\\]', path):
                    # Windows-style path - convert to Unix
                    # C:\path\to\file -> /c/path/to/file
                    drive = path[0].lower()
                    rest = path[3:].replace('\\', '/')
                    return f"/{drive}/{rest}"
                else:
                    # Already Unix-style
                    return path.replace('\\', '/')
        
        except Exception as e:
            logger.warning(f"Failed to normalize path '{path}': {e}")
            return path
    
    def convert_path_for_export(self, path: str) -> str:
        """
        Convert path to platform-independent format for export.
        
        Uses forward slashes and relative paths where possible.
        
        Args:
            path: Path to convert
            
        Returns:
            Platform-independent path representation
        """
        # Remove file:// prefix if present
        if path.startswith("file://"):
            path = path[7:]
        
        # Convert Windows drive letters to /drive/ format
        if re.match(r'^[A-Za-z]:[/\\]', path):
            drive = path[0].lower()
            rest = path[3:].replace('\\', '/')
            return f"/drive/{drive}/{rest}"
        
        # Normalize separators to forward slashes
        return path.replace('\\', '/')
    
    def convert_path_from_export(self, path: str) -> str:
        """
        Convert platform-independent path to current platform format.
        
        Args:
            path: Platform-independent path
            
        Returns:
            Path in current platform format
        """
        # Handle /drive/ format
        if path.startswith("/drive/"):
            match = re.match(r'/drive/([a-z])/(.*)', path)
            if match and self.current_platform == Platform.WINDOWS:
                drive = match.group(1).upper()
                rest = match.group(2)
                return f"{drive}:\\{rest.replace('/', '\\')}"
            elif match:
                # On Unix, keep as-is
                return path
        
        # Normalize for current platform
        return self._normalize_local_path(path, self.current_platform)
    
    def get_credential_store_type(self) -> str:
        """
        Get the appropriate credential store type for the current platform.
        
        Returns:
            Credential store type identifier
        """
        if self.current_platform == Platform.WINDOWS:
            return "windows_credential_manager"
        elif self.current_platform == Platform.MACOS:
            return "macos_keychain"
        elif self.current_platform == Platform.LINUX:
            return "linux_secret_service"
        else:
            return "file_based"
    
    def get_platform_specific_config_dir(self) -> Path:
        """
        Get platform-specific configuration directory.
        
        Returns:
            Path to configuration directory
        """
        if self.current_platform == Platform.WINDOWS:
            # Windows: %APPDATA%\TimeLocker
            appdata = os.getenv('APPDATA')
            if appdata:
                return Path(appdata) / "TimeLocker"
            return Path.home() / "AppData" / "Roaming" / "TimeLocker"
        
        elif self.current_platform == Platform.MACOS:
            # macOS: ~/Library/Application Support/TimeLocker
            return Path.home() / "Library" / "Application Support" / "TimeLocker"
        
        else:  # Linux and others
            # Linux: ~/.config/timelocker (XDG Base Directory)
            xdg_config = os.getenv('XDG_CONFIG_HOME')
            if xdg_config:
                return Path(xdg_config) / "timelocker"
            return Path.home() / ".config" / "timelocker"
    
    def validate_path_permissions(self, path: Path) -> Dict[str, Any]:
        """
        Validate path permissions for the current platform.
        
        Args:
            path: Path to validate
            
        Returns:
            Dictionary with permission validation results
        """
        result = {
            'valid': True,
            'readable': False,
            'writable': False,
            'executable': False,
            'issues': [],
            'warnings': []
        }
        
        try:
            if not path.exists():
                result['valid'] = False
                result['issues'].append(f"Path does not exist: {path}")
                return result
            
            # Check read permission
            result['readable'] = os.access(path, os.R_OK)
            if not result['readable']:
                result['issues'].append("Path is not readable")
            
            # Check write permission
            result['writable'] = os.access(path, os.W_OK)
            if not result['writable']:
                result['warnings'].append("Path is not writable")
            
            # Check execute permission (for directories)
            if path.is_dir():
                result['executable'] = os.access(path, os.X_OK)
                if not result['executable']:
                    result['issues'].append("Directory is not accessible (no execute permission)")
            
            # Platform-specific checks
            if self.current_platform == Platform.WINDOWS:
                # Windows-specific permission checks
                try:
                    import win32security
                    import ntsecuritycon
                    
                    # Get security descriptor
                    sd = win32security.GetFileSecurity(
                        str(path),
                        win32security.DACL_SECURITY_INFORMATION
                    )
                    
                    # Check if we have appropriate access
                    # This is a simplified check
                    result['warnings'].append("Windows ACL validation not fully implemented")
                
                except ImportError:
                    result['warnings'].append("win32security not available for detailed permission checks")
                except Exception as e:
                    result['warnings'].append(f"Windows permission check failed: {e}")
            
            elif self.current_platform in [Platform.LINUX, Platform.MACOS]:
                # Unix-style permission checks
                stat_info = path.stat()
                mode = stat_info.st_mode
                
                # Check if world-readable (potential security issue)
                if mode & 0o004:
                    result['warnings'].append("Path is world-readable")
                
                # Check if world-writable (security issue)
                if mode & 0o002:
                    result['issues'].append("Path is world-writable (security risk)")
                    result['valid'] = False
        
        except Exception as e:
            result['valid'] = False
            result['issues'].append(f"Permission validation failed: {e}")
        
        return result
    
    def get_platform_capabilities(self) -> Dict[str, bool]:
        """
        Get platform-specific capabilities.
        
        Returns:
            Dictionary of capability flags
        """
        capabilities = {
            'native_credential_store': False,
            'file_permissions': True,
            'symbolic_links': True,
            'case_sensitive_paths': True,
            'extended_attributes': False,
            'acl_support': False
        }
        
        if self.current_platform == Platform.WINDOWS:
            capabilities.update({
                'native_credential_store': True,
                'case_sensitive_paths': False,
                'acl_support': True
            })
        
        elif self.current_platform == Platform.MACOS:
            capabilities.update({
                'native_credential_store': True,
                'extended_attributes': True,
                'acl_support': True
            })
        
        elif self.current_platform == Platform.LINUX:
            capabilities.update({
                'native_credential_store': True,  # via Secret Service
                'extended_attributes': True,
                'acl_support': True
            })
        
        return capabilities
    
    def get_fallback_mechanisms(self) -> Dict[str, str]:
        """
        Get fallback mechanisms for platform-specific features.
        
        Returns:
            Dictionary mapping features to fallback implementations
        """
        fallbacks = {}
        
        capabilities = self.get_platform_capabilities()
        
        if not capabilities['native_credential_store']:
            fallbacks['credential_store'] = 'encrypted_file'
        
        if not capabilities['acl_support']:
            fallbacks['access_control'] = 'unix_permissions'
        
        if not capabilities['extended_attributes']:
            fallbacks['metadata_storage'] = 'sidecar_files'
        
        return fallbacks
    
    def create_platform_report(self) -> Dict[str, Any]:
        """
        Create comprehensive platform compatibility report.
        
        Returns:
            Dictionary with platform information and capabilities
        """
        return {
            'platform': self.current_platform.value,
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'python_version': sys.version,
            'capabilities': self.get_platform_capabilities(),
            'fallback_mechanisms': self.get_fallback_mechanisms(),
            'config_directory': str(self.get_platform_specific_config_dir()),
            'credential_store_type': self.get_credential_store_type()
        }


# Global instance for easy access
_platform_compat = None


def get_platform_compatibility() -> PlatformCompatibility:
    """
    Get global PlatformCompatibility instance.
    
    Returns:
        PlatformCompatibility instance
    """
    global _platform_compat
    if _platform_compat is None:
        _platform_compat = PlatformCompatibility()
    return _platform_compat
