"""
Configuration path resolution for TimeLocker.

This module provides centralized path resolution following the Single Responsibility
Principle by focusing solely on determining configuration file locations.
"""

import os
import logging
import tempfile
import uuid

from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class ConfigurationPathResolver:
    """
    Configuration path resolver following Single Responsibility Principle.

    This class focuses solely on resolving configuration file paths according
    to XDG Base Directory Specification and system context.
    """

    @staticmethod
    def get_config_directory() -> Path:
        """
        Get appropriate configuration directory based on context.

        Returns:
            Path: Configuration directory to use
        """
        if ConfigurationPathResolver.is_system_context():
            return ConfigurationPathResolver.get_system_config_directory()
        else:
            return ConfigurationPathResolver.get_user_config_directory()

    @staticmethod
    def get_user_config_directory() -> Path:
        """
        Get user configuration directory following XDG specification.

        Returns:
            Path: User configuration directory
        """
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config_home:
            return Path(xdg_config_home) / "timelocker"
        else:
            return Path.home() / ".config" / "timelocker"

    @staticmethod
    def get_project_config_directory() -> Path:
        """
        Get project-level configuration directory (per working directory).

        Returns:
            Path: Project configuration directory (./.timelocker)
        """
        return Path.cwd() / ".timelocker"

    @staticmethod
    def get_project_config_file_path() -> Path:
        """
        Get project-level configuration file path.

        Returns:
            Path: Project configuration file path (./.timelocker/config.json)
        """
        return ConfigurationPathResolver.get_project_config_directory() / "config.json"

    @staticmethod
    def get_system_config_directory() -> Path:
        """
        Get system-wide configuration directory.

        Returns:
            Path: System configuration directory
        """
        # Windows system directory under ProgramData
        if os.name == "nt":
            program_data = os.environ.get('PROGRAMDATA', r'C:\\ProgramData')
            return Path(program_data) / "timelocker"

        # Prefer /etc/timelocker if it exists or can be created
        system_config = Path("/etc/timelocker")
        if system_config.exists() or system_config.parent.exists():
            return system_config

        # Fallback to XDG system directory
        return Path("/etc/xdg/timelocker")

    @staticmethod
    def get_legacy_config_directory() -> Path:
        """
        Get legacy configuration directory location.

        Returns:
            Path: Legacy configuration directory
        """
        return Path.home() / ".timelocker"

    @staticmethod
    def get_config_file_path(config_dir: Optional[Path] = None) -> Path:
        """
        Get configuration file path.

        Args:
            config_dir: Optional specific configuration directory

        Returns:
            Path: Configuration file path
        """
        if config_dir is None:
            config_dir = ConfigurationPathResolver.get_config_directory()

        return config_dir / "config.json"

    @staticmethod
    def get_backup_directory(config_dir: Optional[Path] = None) -> Path:
        """
        Get configuration backup directory.

        Args:
            config_dir: Optional specific configuration directory

        Returns:
            Path: Configuration backup directory
        """
        if config_dir is None:
            config_dir = ConfigurationPathResolver.get_config_directory()

        return config_dir / "config_backups"

    @staticmethod
    def get_data_directory(config_dir: Optional[Path] = None) -> Path:
        """
        Get data directory path.

        Args:
            config_dir: Optional specific configuration directory

        Returns:
            Path: Data directory path
        """
        if config_dir is None:
            config_dir = ConfigurationPathResolver.get_config_directory()

        return config_dir / "data"

    @staticmethod
    def get_temp_directory(config_dir: Optional[Path] = None) -> Path:
        """
        Get temporary directory path.

        Args:
            config_dir: Optional specific configuration directory

        Returns:
            Path: Temporary directory path
        """
        if config_dir is None:
            config_dir = ConfigurationPathResolver.get_config_directory()

        return config_dir / "temp"

    @staticmethod
    def get_cache_directory() -> Path:
        """
        Get cache directory following XDG specification.

        Returns:
            Path: Cache directory
        """
        if ConfigurationPathResolver.is_system_context():
            if os.name == "nt":
                program_data = os.environ.get('PROGRAMDATA', r'C:\\ProgramData')
                return Path(program_data) / "timelocker" / "cache"
            else:
                return Path("/var/cache/timelocker")
        else:
            xdg_cache_home = os.environ.get('XDG_CACHE_HOME')
            if xdg_cache_home:
                return Path(xdg_cache_home) / "timelocker"
            else:
                return Path.home() / ".cache" / "timelocker"

    @staticmethod
    def get_runtime_directory() -> Path:
        """
        Get runtime directory following XDG specification.

        Returns:
            Path: Runtime directory
        """
        if ConfigurationPathResolver.is_system_context():
            if os.name == "nt":
                program_data = os.environ.get('PROGRAMDATA', r'C:\\ProgramData')
                return Path(program_data) / "timelocker" / "runtime"
            else:
                return Path("/run/timelocker")
        else:
            xdg_runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
            if xdg_runtime_dir:
                return Path(xdg_runtime_dir) / "timelocker"
            # Cross-platform fallback to a temp directory
            try:
                if hasattr(os, "getuid"):
                    uid_or_pid = os.getuid()
                elif hasattr(os, "getpid"):
                    pid = os.getpid()
                    uid_or_pid = f"pid-{pid}-{uuid.uuid4().hex[:8]}"
                else:
                    logger.debug("Neither os.getuid nor os.getpid available; using default UID 1000")
                    uid_or_pid = "uid-1000"
            except (AttributeError, OSError) as e:
                logger.debug(f"Failed to get UID/PID, using default: {e}")
                uid_or_pid = f"pid-{os.getpid()}-{uuid.uuid4().hex[:8]}" if hasattr(os, "getpid") else "uid-1000"
            return Path(tempfile.gettempdir()) / f"timelocker-{uid_or_pid}"

    @staticmethod
    def is_system_context() -> bool:
        """
        Check if running in system context (as root/system/admin) in a cross-platform way.

        Returns:
            bool: True if running with elevated privileges
        """
        # POSIX: root has euid 0
        if hasattr(os, "geteuid"):
            try:
                return os.geteuid() == 0
            except OSError as e:
                logger.debug(f"geteuid check failed: {e}")
                return False
        # Windows: use Shell API when available
        if os.name == "nt":
            try:
                import ctypes  # type: ignore
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception as e:  # Windows can raise various OS-specific errors
                logger.debug(f"Windows admin check failed: {e}")
                return False
        # Other platforms: conservative default
        return False

    @staticmethod
    def should_migrate_from_legacy() -> bool:
        """
        Check if migration from legacy configuration is needed.

        Returns:
            bool: True if legacy configuration exists and should be migrated
        """
        if ConfigurationPathResolver.is_system_context():
            # No legacy migration for system context
            return False

        legacy_dir = ConfigurationPathResolver.get_legacy_config_directory()
        current_dir = ConfigurationPathResolver.get_config_directory()

        # Check if legacy config exists and current doesn't
        legacy_config = legacy_dir / "config.json"
        current_config = current_dir / "config.json"
        migration_marker = current_dir / ".migrated_from_legacy"

        return (
                legacy_config.exists() and
                not current_config.exists() and
                not migration_marker.exists()
        )

    @staticmethod
    def get_all_possible_config_paths() -> List[Path]:
        """
        Get all possible configuration file paths in order of preference.

        Returns:
            List[Path]: List of possible configuration file paths
        """
        paths = []

        # Project-level configuration (highest precedence)
        try:
            project_cfg = ConfigurationPathResolver.get_project_config_file_path()
            paths.append(project_cfg)
        except Exception:
            pass

        # Current context configuration (user/system XDG)
        paths.append(ConfigurationPathResolver.get_config_file_path())

        # Legacy configuration (if not system context)
        if not ConfigurationPathResolver.is_system_context():
            legacy_dir = ConfigurationPathResolver.get_legacy_config_directory()
            paths.append(legacy_dir / "config.json")

        # Alternative system paths (if system context)
        if ConfigurationPathResolver.is_system_context():
            paths.extend([
                    Path("/etc/xdg/timelocker/config.json"),
                    Path("/usr/local/etc/timelocker/config.json")
            ])

        return paths

    @staticmethod
    def ensure_directories_exist(config_dir: Optional[Path] = None) -> None:
        """
        Ensure all necessary directories exist.

        Args:
            config_dir: Optional specific configuration directory
        """
        if config_dir is None:
            config_dir = ConfigurationPathResolver.get_config_directory()

        # Create main directories
        directories = [
                config_dir,
                ConfigurationPathResolver.get_backup_directory(config_dir),
                ConfigurationPathResolver.get_data_directory(config_dir),
                ConfigurationPathResolver.get_temp_directory(config_dir),
                ConfigurationPathResolver.get_cache_directory(),
        ]

        # Only create runtime directory if not system context
        if not ConfigurationPathResolver.is_system_context():
            directories.append(ConfigurationPathResolver.get_runtime_directory())

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {directory}")
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not create directory {directory}: {e}")

    @staticmethod
    def get_path_info() -> dict:
        """
        Get comprehensive path information for debugging.

        Returns:
            dict: Path information
        """
        config_dir = ConfigurationPathResolver.get_config_directory()
        legacy_dir = ConfigurationPathResolver.get_legacy_config_directory()

        return {
                "is_system_context":    ConfigurationPathResolver.is_system_context(),
                "config_directory":     str(config_dir),
                "config_file":          str(ConfigurationPathResolver.get_config_file_path()),
                "legacy_directory":     str(legacy_dir),
                "legacy_config_exists": (legacy_dir / "config.json").exists(),
                "should_migrate":       ConfigurationPathResolver.should_migrate_from_legacy(),
                "cache_directory":      str(ConfigurationPathResolver.get_cache_directory()),
                "runtime_directory":    str(ConfigurationPathResolver.get_runtime_directory()),
                "xdg_config_home":      os.environ.get('XDG_CONFIG_HOME', 'not set'),
                "xdg_cache_home":       os.environ.get('XDG_CACHE_HOME', 'not set'),
                "xdg_runtime_dir":      os.environ.get('XDG_RUNTIME_DIR', 'not set'),
                "all_possible_paths":   [str(p) for p in ConfigurationPathResolver.get_all_possible_config_paths()]
        }
