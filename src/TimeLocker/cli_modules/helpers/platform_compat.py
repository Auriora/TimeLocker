"""
Cross-Platform Compatibility Utilities

This module provides cross-platform compatibility utilities for the TimeLocker CLI.
It handles platform-specific differences in paths, credentials, error messages, and
help information to ensure consistent behavior across Windows, macOS, and Linux.

Requirements: 21.1, 21.2, 21.3, 21.4
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class PlatformInfo:
    """
    Platform information and detection.
    
    Provides utilities for detecting the current platform and its capabilities.
    """
    
    @staticmethod
    def get_platform() -> Platform:
        """
        Detect the current platform.
        
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
    
    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return PlatformInfo.get_platform() == Platform.WINDOWS
    
    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS."""
        return PlatformInfo.get_platform() == Platform.MACOS
    
    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux."""
        return PlatformInfo.get_platform() == Platform.LINUX
    
    @staticmethod
    def get_platform_name() -> str:
        """
        Get a user-friendly platform name.
        
        Returns:
            Platform name string
        """
        platform_map = {
            Platform.WINDOWS: "Windows",
            Platform.MACOS: "macOS",
            Platform.LINUX: "Linux",
            Platform.UNKNOWN: "Unknown"
        }
        return platform_map[PlatformInfo.get_platform()]
    
    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """
        Get detailed system information.
        
        Returns:
            Dictionary with system information
        """
        return {
            "platform": PlatformInfo.get_platform_name(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }


class PathHandler:
    """
    Cross-platform path handling utilities.
    
    Handles platform-specific path operations and conversions.
    """
    
    @staticmethod
    def normalize_path(path: str) -> Path:
        """
        Normalize a path for the current platform.
        
        Args:
            path: Path string to normalize
            
        Returns:
            Normalized Path object
        """
        # Expand user home directory
        path = os.path.expanduser(path)
        
        # Expand environment variables
        path = os.path.expandvars(path)
        
        # Convert to Path and resolve
        return Path(path).resolve()
    
    @staticmethod
    def to_platform_path(path: str) -> str:
        """
        Convert a path to platform-specific format.
        
        Args:
            path: Path string
            
        Returns:
            Platform-specific path string
        """
        normalized = PathHandler.normalize_path(path)
        
        if PlatformInfo.is_windows():
            # Use backslashes on Windows
            return str(normalized).replace('/', '\\')
        else:
            # Use forward slashes on Unix-like systems
            return str(normalized).replace('\\', '/')
    
    @staticmethod
    def get_config_dir() -> Path:
        """
        Get the platform-appropriate configuration directory.
        
        Returns:
            Path to configuration directory
        """
        if PlatformInfo.is_windows():
            # Windows: %APPDATA%\TimeLocker
            base = os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming')
            return Path(base) / 'TimeLocker'
        elif PlatformInfo.is_macos():
            # macOS: ~/Library/Application Support/TimeLocker
            return Path.home() / 'Library' / 'Application Support' / 'TimeLocker'
        else:
            # Linux: ~/.config/timelocker
            xdg_config = os.getenv('XDG_CONFIG_HOME', Path.home() / '.config')
            return Path(xdg_config) / 'timelocker'
    
    @staticmethod
    def get_cache_dir() -> Path:
        """
        Get the platform-appropriate cache directory.
        
        Returns:
            Path to cache directory
        """
        if PlatformInfo.is_windows():
            # Windows: %LOCALAPPDATA%\TimeLocker\Cache
            base = os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
            return Path(base) / 'TimeLocker' / 'Cache'
        elif PlatformInfo.is_macos():
            # macOS: ~/Library/Caches/TimeLocker
            return Path.home() / 'Library' / 'Caches' / 'TimeLocker'
        else:
            # Linux: ~/.cache/timelocker
            xdg_cache = os.getenv('XDG_CACHE_HOME', Path.home() / '.cache')
            return Path(xdg_cache) / 'timelocker'
    
    @staticmethod
    def get_data_dir() -> Path:
        """
        Get the platform-appropriate data directory.
        
        Returns:
            Path to data directory
        """
        if PlatformInfo.is_windows():
            # Windows: %LOCALAPPDATA%\TimeLocker
            base = os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
            return Path(base) / 'TimeLocker'
        elif PlatformInfo.is_macos():
            # macOS: ~/Library/Application Support/TimeLocker
            return Path.home() / 'Library' / 'Application Support' / 'TimeLocker'
        else:
            # Linux: ~/.local/share/timelocker
            xdg_data = os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share')
            return Path(xdg_data) / 'timelocker'
    
    @staticmethod
    def is_absolute_path(path: str) -> bool:
        """
        Check if a path is absolute (platform-aware).
        
        Args:
            path: Path string to check
            
        Returns:
            True if path is absolute
        """
        return Path(path).is_absolute()
    
    @staticmethod
    def join_paths(*parts: str) -> str:
        """
        Join path components in a platform-appropriate way.
        
        Args:
            *parts: Path components to join
            
        Returns:
            Joined path string
        """
        return str(Path(*parts))


class CredentialHandler:
    """
    Cross-platform credential storage handling.
    
    Provides platform-specific credential storage recommendations and capabilities.
    """
    
    @staticmethod
    def get_credential_backend() -> str:
        """
        Get the recommended credential backend for the current platform.
        
        Returns:
            Credential backend name
        """
        if PlatformInfo.is_windows():
            return "Windows Credential Manager"
        elif PlatformInfo.is_macos():
            return "macOS Keychain"
        else:
            return "Secret Service (libsecret)"
    
    @staticmethod
    def is_credential_backend_available() -> bool:
        """
        Check if the platform credential backend is available.
        
        Returns:
            True if credential backend is available
        """
        try:
            if PlatformInfo.is_windows():
                # Check for Windows Credential Manager
                import keyring
                return keyring.get_keyring().name != "fail Keyring"
            elif PlatformInfo.is_macos():
                # Check for macOS Keychain
                import keyring
                return "Keychain" in keyring.get_keyring().name
            else:
                # Check for Secret Service on Linux
                import keyring
                return "SecretService" in keyring.get_keyring().name or "kwallet" in keyring.get_keyring().name.lower()
        except Exception as e:
            logger.debug(f"Credential backend check failed: {e}")
            return False
    
    @staticmethod
    def get_credential_storage_info() -> Dict[str, Any]:
        """
        Get information about credential storage on this platform.
        
        Returns:
            Dictionary with credential storage information
        """
        return {
            "backend": CredentialHandler.get_credential_backend(),
            "available": CredentialHandler.is_credential_backend_available(),
            "platform": PlatformInfo.get_platform_name(),
        }


class ErrorMessageFormatter:
    """
    Platform-appropriate error message formatting.
    
    Provides platform-specific error messages and help information.
    """
    
    @staticmethod
    def format_path_error(path: str, error: str) -> str:
        """
        Format a path-related error message for the current platform.
        
        Args:
            path: The problematic path
            error: Error description
            
        Returns:
            Formatted error message
        """
        platform_path = PathHandler.to_platform_path(path)
        
        if PlatformInfo.is_windows():
            return (
                f"{error}\n"
                f"Path: {platform_path}\n\n"
                f"Note: On Windows, use backslashes (\\) or forward slashes (/) in paths.\n"
                f"Example: C:\\backup\\repo or C:/backup/repo"
            )
        else:
            return (
                f"{error}\n"
                f"Path: {platform_path}\n\n"
                f"Note: Use absolute paths starting with / or relative paths.\n"
                f"Example: /backup/repo or ~/backup/repo"
            )
    
    @staticmethod
    def format_permission_error(path: str, operation: str) -> str:
        """
        Format a permission error message for the current platform.
        
        Args:
            path: The path with permission issues
            operation: The operation that failed
            
        Returns:
            Formatted error message
        """
        platform_path = PathHandler.to_platform_path(path)
        
        if PlatformInfo.is_windows():
            return (
                f"Permission denied: Cannot {operation}\n"
                f"Path: {platform_path}\n\n"
                f"Possible solutions:\n"
                f"• Run the command as Administrator\n"
                f"• Check file/folder permissions in Properties\n"
                f"• Ensure the path is not in use by another program"
            )
        else:
            return (
                f"Permission denied: Cannot {operation}\n"
                f"Path: {platform_path}\n\n"
                f"Possible solutions:\n"
                f"• Check file permissions: ls -la {platform_path}\n"
                f"• Change permissions: chmod +rw {platform_path}\n"
                f"• Run with appropriate user privileges"
            )
    
    @staticmethod
    def format_command_not_found(command: str) -> str:
        """
        Format a command not found error for the current platform.
        
        Args:
            command: The command that was not found
            
        Returns:
            Formatted error message
        """
        if PlatformInfo.is_windows():
            return (
                f"Command not found: {command}\n\n"
                f"The command '{command}' is not recognized.\n"
                f"Make sure it is installed and available in your PATH.\n\n"
                f"To check your PATH:\n"
                f"  echo %PATH%\n\n"
                f"To add to PATH:\n"
                f"  setx PATH \"%PATH%;C:\\path\\to\\{command}\""
            )
        else:
            return (
                f"Command not found: {command}\n\n"
                f"The command '{command}' is not installed or not in your PATH.\n\n"
                f"To check your PATH:\n"
                f"  echo $PATH\n\n"
                f"To install (example):\n"
                f"  # On Ubuntu/Debian:\n"
                f"  sudo apt-get install {command}\n"
                f"  # On macOS with Homebrew:\n"
                f"  brew install {command}"
            )


class PlatformCapabilities:
    """
    Platform capability detection and reporting.
    
    Detects and reports platform-specific capabilities and limitations.
    """
    
    @staticmethod
    def get_capabilities() -> Dict[str, bool]:
        """
        Get platform capabilities.
        
        Returns:
            Dictionary of capability names to availability
        """
        capabilities = {
            "credential_storage": CredentialHandler.is_credential_backend_available(),
            "symbolic_links": PlatformCapabilities._check_symlink_support(),
            "case_sensitive_fs": PlatformCapabilities._check_case_sensitivity(),
            "posix_permissions": not PlatformInfo.is_windows(),
            "long_paths": PlatformCapabilities._check_long_path_support(),
        }
        
        return capabilities
    
    @staticmethod
    def _check_symlink_support() -> bool:
        """Check if symbolic links are supported."""
        try:
            # Try to create a symlink in temp directory
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                src = Path(tmpdir) / "test_src"
                dst = Path(tmpdir) / "test_dst"
                src.touch()
                dst.symlink_to(src)
                return True
        except (OSError, NotImplementedError):
            return False
    
    @staticmethod
    def _check_case_sensitivity() -> bool:
        """Check if filesystem is case-sensitive."""
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = Path(tmpdir) / "TEST"
                test_file.touch()
                return not (Path(tmpdir) / "test").exists()
        except Exception:
            # Default assumptions
            return not (PlatformInfo.is_windows() or PlatformInfo.is_macos())
    
    @staticmethod
    def _check_long_path_support() -> bool:
        """Check if long paths are supported."""
        if PlatformInfo.is_windows():
            # Windows 10 version 1607+ supports long paths if enabled
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\FileSystem"
                )
                value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
                return value == 1
            except Exception:
                return False
        else:
            # Unix-like systems generally support long paths
            return True
    
    @staticmethod
    def get_capability_report() -> str:
        """
        Get a formatted capability report.
        
        Returns:
            Formatted capability report string
        """
        capabilities = PlatformCapabilities.get_capabilities()
        platform_name = PlatformInfo.get_platform_name()
        
        report = f"Platform: {platform_name}\n\n"
        report += "Capabilities:\n"
        
        for capability, available in capabilities.items():
            status = "✓ Available" if available else "✗ Not available"
            capability_name = capability.replace('_', ' ').title()
            report += f"  {capability_name}: {status}\n"
        
        return report
    
    @staticmethod
    def check_platform_limitations() -> List[str]:
        """
        Check for platform-specific limitations.
        
        Returns:
            List of limitation warnings
        """
        limitations = []
        
        if PlatformInfo.is_windows():
            if not PlatformCapabilities._check_long_path_support():
                limitations.append(
                    "Long path support is not enabled. Paths longer than 260 characters may fail. "
                    "Enable long paths in Windows settings or Group Policy."
                )
            
            if not PlatformCapabilities._check_symlink_support():
                limitations.append(
                    "Symbolic link support requires Administrator privileges or Developer Mode. "
                    "Some backup operations may be affected."
                )
        
        if not CredentialHandler.is_credential_backend_available():
            limitations.append(
                f"Platform credential storage ({CredentialHandler.get_credential_backend()}) "
                "is not available. Credentials will be stored in configuration files."
            )
        
        return limitations


# Convenience functions for common operations

def get_platform_name() -> str:
    """Get the current platform name."""
    return PlatformInfo.get_platform_name()


def normalize_path(path: str) -> Path:
    """Normalize a path for the current platform."""
    return PathHandler.normalize_path(path)


def format_error_message(error_type: str, **kwargs) -> str:
    """
    Format an error message for the current platform.
    
    Args:
        error_type: Type of error ('path', 'permission', 'command_not_found')
        **kwargs: Error-specific parameters
        
    Returns:
        Formatted error message
    """
    formatter = ErrorMessageFormatter()
    
    if error_type == "path":
        return formatter.format_path_error(kwargs.get("path", ""), kwargs.get("error", ""))
    elif error_type == "permission":
        return formatter.format_permission_error(kwargs.get("path", ""), kwargs.get("operation", ""))
    elif error_type == "command_not_found":
        return formatter.format_command_not_found(kwargs.get("command", ""))
    else:
        return f"Unknown error type: {error_type}"


def get_platform_capabilities() -> Dict[str, bool]:
    """Get platform capabilities."""
    return PlatformCapabilities.get_capabilities()


def check_platform_compatibility() -> tuple[bool, List[str]]:
    """
    Check platform compatibility and return any warnings.
    
    Returns:
        Tuple of (is_compatible, list_of_warnings)
    """
    limitations = PlatformCapabilities.check_platform_limitations()
    is_compatible = PlatformInfo.get_platform() != Platform.UNKNOWN
    
    return is_compatible, limitations
