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
import os
import shutil
import copy
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Base exception for configuration-related errors"""
    pass


class RepositoryNotFoundError(ConfigurationError):
    """Raised when a repository name cannot be resolved"""
    pass


class RepositoryAlreadyExistsError(ConfigurationError):
    """Raised when trying to add a repository with an existing name"""
    pass


# ConfigSection enum removed - use string section names directly


# Old dataclasses removed - use ConfigurationDefaults.get_*_defaults() instead


class ConfigurationPathResolver:
    """
    Utility class for resolving configuration directory paths
    Handles XDG Base Directory Specification and system vs user contexts
    """

    @staticmethod
    def is_system_context() -> bool:
        """
        Determine if running in system context (as root for system backups)

        Returns:
            bool: True if running as root or in system context
        """
        return os.geteuid() == 0 if hasattr(os, 'geteuid') else False

    @staticmethod
    def get_xdg_config_home() -> Path:
        """
        Get XDG config home directory

        Returns:
            Path: XDG config home directory
        """
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config_home:
            return Path(xdg_config_home)
        return Path.home() / ".config"

    @staticmethod
    def get_config_directory() -> Path:
        """
        Get appropriate configuration directory based on context

        Returns:
            Path: Configuration directory to use
        """
        if ConfigurationPathResolver.is_system_context():
            # System-wide configuration for root/system backups
            system_config = Path("/etc/timelocker")
            if system_config.exists() or system_config.parent.exists():
                return system_config
            # Fallback to XDG system directory
            return Path("/etc/xdg/timelocker")
        else:
            # User configuration following XDG specification
            return ConfigurationPathResolver.get_xdg_config_home() / "timelocker"

    @staticmethod
    def get_legacy_config_directory() -> Path:
        """
        Get legacy configuration directory for migration

        Returns:
            Path: Legacy configuration directory
        """
        return Path.home() / ".timelocker"

    @staticmethod
    def should_migrate_from_legacy() -> bool:
        """
        Check if migration from legacy config is needed

        Returns:
            bool: True if legacy config exists and new config doesn't
        """
        legacy_dir = ConfigurationPathResolver.get_legacy_config_directory()
        new_dir = ConfigurationPathResolver.get_config_directory()

        legacy_config = legacy_dir / "config.json"
        new_config = new_dir / "config.json"

        return legacy_config.exists() and not new_config.exists()


class ConfigurationMigrationManager:
    """
    Handles migration of configuration files from legacy locations
    """

    @staticmethod
    def calculate_file_checksum(file_path: Path) -> str:
        """
        Calculate SHA256 checksum of a file

        Args:
            file_path: Path to file

        Returns:
            str: Hexadecimal checksum
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""

    @staticmethod
    def create_migration_backup(source_path: Path, backup_dir: Path) -> Optional[Path]:
        """
        Create backup of source file before migration

        Args:
            source_path: Source file to backup
            backup_dir: Directory to store backup

        Returns:
            Optional[Path]: Path to backup file if successful
        """
        if not source_path.exists():
            return None

        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"migration_backup_{timestamp}_{source_path.name}"
            shutil.copy2(source_path, backup_path)
            logger.info(f"Created migration backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create migration backup: {e}")
            return None

    @staticmethod
    def migrate_configuration_directory(legacy_dir: Path, new_dir: Path) -> bool:
        """
        Migrate entire configuration directory from legacy to new location

        Args:
            legacy_dir: Legacy configuration directory
            new_dir: New configuration directory

        Returns:
            bool: True if migration successful
        """
        if not legacy_dir.exists():
            logger.info("No legacy configuration directory found")
            return True

        if new_dir.exists() and (new_dir / "config.json").exists():
            logger.info("New configuration already exists, skipping migration")
            return True

        try:
            logger.info(f"Migrating configuration from {legacy_dir} to {new_dir}")

            # Create new directory
            new_dir.mkdir(parents=True, exist_ok=True)

            # Create backup directory in new location
            backup_dir = new_dir / "migration_backups"
            backup_dir.mkdir(exist_ok=True)

            # Files to migrate
            files_to_migrate = ["config.json"]
            migrated_files = []

            for filename in files_to_migrate:
                legacy_file = legacy_dir / filename
                new_file = new_dir / filename

                if legacy_file.exists():
                    # Create backup
                    backup_path = ConfigurationMigrationManager.create_migration_backup(
                            legacy_file, backup_dir
                    )

                    # Calculate checksum before migration
                    original_checksum = ConfigurationMigrationManager.calculate_file_checksum(legacy_file)

                    # Copy file
                    shutil.copy2(legacy_file, new_file)

                    # Verify checksum after migration
                    new_checksum = ConfigurationMigrationManager.calculate_file_checksum(new_file)

                    if original_checksum and original_checksum == new_checksum:
                        migrated_files.append(filename)
                        logger.info(f"Successfully migrated {filename}")
                    else:
                        logger.error(f"Checksum mismatch for {filename}, migration may have failed")
                        if new_file.exists():
                            new_file.unlink()
                        return False

            if migrated_files:
                logger.info(f"Migration completed successfully. Migrated files: {migrated_files}")

                # Create migration marker file
                migration_marker = new_dir / ".migrated_from_legacy"
                with open(migration_marker, 'w') as f:
                    f.write(f"Migrated from {legacy_dir} on {datetime.now().isoformat()}\n")
                    f.write(f"Migrated files: {', '.join(migrated_files)}\n")

                return True
            else:
                logger.info("No files to migrate")
                return True

        except Exception as e:
            logger.error(f"Failed to migrate configuration directory: {e}")
            return False


class ConfigurationManager:
    """
    Backward-compatibility shim over ConfigurationModule.

    Provides a minimal subset of the legacy API used by tests and existing scripts.
    Internally delegates to ConfigurationModule while adapting method names and
    return shapes.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        # Lazy import to avoid potential circular imports during test discovery
        from . import ConfigurationModule  # type: ignore
        self._module = ConfigurationModule(config_dir)

    # -------------------------------
    # Repository management methods
    # -------------------------------
    def add_repository(self, name: str, uri: str, description: Optional[str] = None) -> None:
        config = self._module.get_config()
        if name in config.repositories:
            raise RepositoryAlreadyExistsError(f"Repository '{name}' already exists")
        repo_dict = {"name": name, "location": uri, "description": description or ""}
        self._module.add_repository(repo_dict)

    def get_repository(self, name: str) -> Dict[str, Any]:
        try:
            repo = self._module.get_repository(name)
        except Exception:
            raise RepositoryNotFoundError(f"Repository '{name}' not found")
        return {
                "name":        name,
                "uri":         repo.location or "",
                "description": repo.description or "",
                "type":        self._detect_type(repo.location or ""),
                "created":     datetime.now().isoformat(),
        }

    def remove_repository(self, name: str) -> None:
        try:
            self._module.remove_repository(name)
        except Exception:
            raise RepositoryNotFoundError(f"Repository '{name}' not found")

    def set_default_repository(self, name: str) -> None:
        # Verify exists
        try:
            _ = self._module.get_repository(name)
        except Exception:
            raise RepositoryNotFoundError(f"Repository '{name}' not found")
        self._module.set_default_repository(name)

    def get_default_repository(self) -> Optional[str]:
        return self._module.get_default_repository()

    # -------------------------------
    # Resolution helpers
    # -------------------------------
    def resolve_repository(self, name_or_uri: Optional[str]) -> str:
        if not name_or_uri:
            default_name = self.get_default_repository()
            if not default_name:
                raise RepositoryNotFoundError("No default repository configured and no input provided")
            repo = self._module.get_repository(default_name)
            return repo.location or ""

        # If exact name exists
        config = self._module.get_config()
        if name_or_uri in config.repositories:
            return config.repositories[name_or_uri].location or ""

        # Passthrough if looks like URI/path
        if self._looks_like_uri_or_path(name_or_uri):
            return name_or_uri

        raise RepositoryNotFoundError(f"Repository '{name_or_uri}' not found")

    # -------------------------------
    # Internal helpers
    # -------------------------------
    @staticmethod
    def _looks_like_uri_or_path(value: str) -> bool:
        return (
                "://" in value
                or value.startswith(("s3:", "sftp:", "rest:", "file://", "/"))
        )

    @staticmethod
    def _detect_type(uri: str) -> str:
        if uri.startswith(("s3://", "s3:")):
            return "s3"
        if uri.startswith(("sftp://", "sftp:")):
            return "sftp"
        if uri.startswith("file://") or uri.startswith("/"):
            return "local"
        # Heuristic: treat unknown without scheme as local
        if "://" not in uri and uri and not uri.split(":")[0]:
            return "local"
        # Default
        return "local"
