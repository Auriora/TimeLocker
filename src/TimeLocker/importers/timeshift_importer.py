"""
Timeshift Configuration Importer

This module provides functionality to import Timeshift backup tool configurations
into TimeLocker's configuration system.

Timeshift is a system backup tool for Linux that creates filesystem snapshots.
This importer converts Timeshift's JSON configuration format to TimeLocker's
repository and backup target configurations.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TimeshiftImportResult:
    """Result of Timeshift configuration import"""
    success: bool
    repository_config: Optional[Dict[str, Any]] = None
    backup_target_config: Optional[Dict[str, Any]] = None
    warnings: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []


class TimeshiftConfigParser:
    """Parser for Timeshift configuration files"""

    # Standard Timeshift configuration file locations
    CONFIG_LOCATIONS = [
            Path("/etc/timeshift/timeshift.json"),
            Path("/etc/timeshift.json"),
    ]

    def __init__(self):
        self.config_data: Optional[Dict[str, Any]] = None
        self.config_file: Optional[Path] = None

    def find_config_file(self) -> Optional[Path]:
        """Find Timeshift configuration file"""
        for config_path in self.CONFIG_LOCATIONS:
            if config_path.exists() and config_path.is_file():
                try:
                    # Check if file is readable
                    with open(config_path, 'r') as f:
                        f.read(1)  # Try to read first character
                    return config_path
                except (PermissionError, OSError) as e:
                    logger.warning(f"Cannot read Timeshift config at {config_path}: {e}")
                    continue
        return None

    def parse_config(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Parse Timeshift configuration file
        
        Args:
            config_path: Optional specific path to config file
            
        Returns:
            Parsed configuration dictionary
            
        Raises:
            FileNotFoundError: If no config file found
            PermissionError: If config file not readable
            json.JSONDecodeError: If config file contains invalid JSON
        """
        if config_path:
            if not config_path.exists():
                raise FileNotFoundError(f"Timeshift config file not found: {config_path}")
            self.config_file = config_path
        else:
            self.config_file = self.find_config_file()
            if not self.config_file:
                raise FileNotFoundError(
                        "No Timeshift configuration file found. "
                        f"Checked locations: {', '.join(str(p) for p in self.CONFIG_LOCATIONS)}"
                )

        try:
            with open(self.config_file, 'r') as f:
                self.config_data = json.load(f)

            logger.info(f"Successfully parsed Timeshift config from {self.config_file}")
            return self.config_data

        except PermissionError as e:
            raise PermissionError(f"Permission denied reading {self.config_file}: {e}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                    f"Invalid JSON in Timeshift config {self.config_file}: {e.msg}",
                    e.doc, e.pos
            )
        except Exception as e:
            raise RuntimeError(f"Failed to parse Timeshift config {self.config_file}: {e}")

    def get_backup_device_uuid(self) -> Optional[str]:
        """Get backup device UUID from config"""
        if not self.config_data:
            return None
        return self.config_data.get("backup_device_uuid", "").strip() or None

    def get_exclude_patterns(self) -> List[str]:
        """Get exclude patterns from config"""
        if not self.config_data:
            return []

        excludes = []

        # Get exclude patterns
        exclude_list = self.config_data.get("exclude", [])
        if isinstance(exclude_list, list):
            excludes.extend(exclude_list)

        # Get exclude-apps patterns (application-specific excludes)
        exclude_apps = self.config_data.get("exclude-apps", [])
        if isinstance(exclude_apps, list):
            excludes.extend(exclude_apps)

        return [pattern for pattern in excludes if pattern.strip()]

    def get_schedule_info(self) -> Dict[str, Any]:
        """Get schedule information from config"""
        if not self.config_data:
            return {}

        schedule_info = {}

        # Schedule flags
        for schedule_type in ["hourly", "daily", "weekly", "monthly", "boot"]:
            key = f"schedule_{schedule_type}"
            if key in self.config_data:
                schedule_info[schedule_type] = self.config_data[key] == "true"

        # Retention counts
        for schedule_type in ["hourly", "daily", "weekly", "monthly", "boot"]:
            key = f"count_{schedule_type}"
            if key in self.config_data:
                try:
                    schedule_info[f"{schedule_type}_count"] = int(self.config_data[key])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid count value for {key}: {self.config_data[key]}")

        return schedule_info

    def is_btrfs_mode(self) -> bool:
        """Check if Timeshift is configured for BTRFS mode"""
        if not self.config_data:
            return False
        return self.config_data.get("btrfs_mode", "false") == "true"

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of parsed configuration"""
        if not self.config_data:
            return {}

        return {
                "config_file":        str(self.config_file) if self.config_file else None,
                "backup_device_uuid": self.get_backup_device_uuid(),
                "btrfs_mode":         self.is_btrfs_mode(),
                "exclude_patterns":   self.get_exclude_patterns(),
                "schedule_info":      self.get_schedule_info(),
                "raw_config_keys":    list(self.config_data.keys()) if self.config_data else []
        }


class TimeshiftToTimeLockerMapper:
    """Maps Timeshift configuration to TimeLocker format"""

    def __init__(self):
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def resolve_device_uuid_to_path(self, uuid: str) -> Optional[str]:
        """
        Resolve device UUID to mount path
        
        Args:
            uuid: Device UUID from Timeshift config
            
        Returns:
            Mount path if found, None otherwise
        """
        if not uuid or uuid.strip() == "":
            return None

        try:
            # Try to find device by UUID using blkid
            result = subprocess.run(
                    ["blkid", "-U", uuid],
                    capture_output=True,
                    text=True,
                    timeout=10
            )

            if result.returncode == 0:
                device_path = result.stdout.strip()
                if device_path:
                    # Try to find mount point for this device
                    mount_result = subprocess.run(
                            ["findmnt", "-n", "-o", "TARGET", device_path],
                            capture_output=True,
                            text=True,
                            timeout=10
                    )

                    if mount_result.returncode == 0:
                        mount_point = mount_result.stdout.strip()
                        if mount_point:
                            # Timeshift typically stores backups in /timeshift on the device
                            timeshift_path = Path(mount_point) / "timeshift"
                            return str(timeshift_path)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Failed to resolve UUID {uuid}: {e}")

        return None

    def map_exclude_patterns(self, timeshift_excludes: List[str]) -> List[str]:
        """
        Map Timeshift exclude patterns to TimeLocker format
        
        Args:
            timeshift_excludes: List of Timeshift exclude patterns
            
        Returns:
            List of TimeLocker-compatible exclude patterns
        """
        mapped_patterns = []

        for pattern in timeshift_excludes:
            if not pattern.strip():
                continue

            # Timeshift patterns are typically absolute paths
            # Convert to patterns suitable for file-level backup
            pattern = pattern.strip()

            # If it's an absolute path, convert to relative pattern
            if pattern.startswith('/'):
                # Remove leading slash and add ** prefix for recursive matching
                relative_pattern = pattern[1:]
                mapped_patterns.append(f"**/{relative_pattern}")
                mapped_patterns.append(f"**/{relative_pattern}/**")
            else:
                # Keep as-is if it's already a pattern
                mapped_patterns.append(pattern)

        return mapped_patterns

    def create_repository_config(self,
                                 timeshift_config: Dict[str, Any],
                                 repository_name: str = "timeshift_imported",
                                 manual_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Create TimeLocker repository configuration from Timeshift config
        
        Args:
            timeshift_config: Parsed Timeshift configuration
            repository_name: Name for the imported repository
            manual_path: Manual repository path if UUID resolution fails
            
        Returns:
            TimeLocker repository configuration
        """
        self.warnings.clear()
        self.errors.clear()

        # Get backup device UUID
        backup_uuid = timeshift_config.get("backup_device_uuid", "").strip()

        # Try to resolve UUID to path
        repository_path = None
        if backup_uuid:
            repository_path = self.resolve_device_uuid_to_path(backup_uuid)
            if not repository_path:
                self.warnings.append(
                        f"Could not resolve backup device UUID '{backup_uuid}' to a path. "
                        "You may need to specify the repository path manually."
                )

        # Use manual path if provided or UUID resolution failed
        if manual_path:
            repository_path = manual_path
        elif not repository_path:
            # Default fallback - this will likely need user correction
            repository_path = "/timeshift"
            self.warnings.append(
                    "Using default path '/timeshift'. Please verify this is correct for your setup."
            )

        # Ensure path uses file:// prefix for local repositories
        if not repository_path.startswith(("file://", "s3://", "b2://", "sftp://")):
            repository_path = f"file://{repository_path}"

        repo_config = {
                "name":                   repository_name,
                "location":               repository_path,
                "description":            f"Imported from Timeshift (UUID: {backup_uuid or 'unknown'})",
                "enabled":                True,
                # Display-only fields (not passed to RepositoryConfig constructor)
                "_display_type":          "local",
                "_display_original_uuid": backup_uuid
        }

        return repo_config

    def create_backup_target_config(self,
                                    timeshift_config: Dict[str, Any],
                                    target_name: str = "timeshift_system",
                                    repository_name: str = "timeshift_imported",
                                    backup_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create TimeLocker backup target configuration from Timeshift config

        Args:
            timeshift_config: Parsed Timeshift configuration
            target_name: Name for the backup target
            repository_name: Name of the repository to use
            backup_paths: Paths to backup (defaults to root filesystem like Timeshift)

        Returns:
            TimeLocker backup target configuration
        """
        # Timeshift backs up the entire root filesystem by default
        if not backup_paths:
            backup_paths = ["/"]
            self.warnings.append(
                    "Imported Timeshift configuration with full system backup (root filesystem '/') "
                    "and exclusion patterns. This matches Timeshift's default behavior of backing up "
                    "everything and excluding specific directories."
            )

        # Get exclude patterns from Timeshift
        timeshift_excludes = timeshift_config.get("exclude", [])
        exclude_patterns = self.map_exclude_patterns(timeshift_excludes)

        # Add common system excludes that Timeshift typically handles
        default_excludes = [
                "**/proc/**",
                "**/sys/**",
                "**/dev/**",
                "**/tmp/**",
                "**/run/**",
                "**/mnt/**",
                "**/media/**",
                "**/.cache/**",
                "**/lost+found/**"
        ]
        exclude_patterns.extend(default_excludes)

        # Remove duplicates while preserving order
        seen = set()
        unique_excludes = []
        for pattern in exclude_patterns:
            if pattern not in seen:
                seen.add(pattern)
                unique_excludes.append(pattern)

        target_config = {
                "name":                target_name,
                "paths":               backup_paths,
                "exclude_patterns":    unique_excludes,
                "description":         "Imported from Timeshift - full system backup with exclusions",
                "enabled":             True,
                # Display-only fields (not passed to BackupTargetConfig constructor)
                "_display_repository": repository_name
        }

        # Add schedule information if available
        schedule_info = timeshift_config.get("schedule_info", {})
        if any(schedule_info.get(f"schedule_{t}", False) for t in ["hourly", "daily", "weekly", "monthly"]):
            self.warnings.append(
                    "Timeshift scheduling information found but not imported. "
                    "TimeLocker uses different scheduling mechanisms. "
                    "Please configure backup scheduling separately."
            )

        return target_config

    def import_configuration(self,
                             timeshift_config: Dict[str, Any],
                             repository_name: str = "timeshift_imported",
                             target_name: str = "timeshift_system",
                             manual_repository_path: Optional[str] = None,
                             backup_paths: Optional[List[str]] = None) -> TimeshiftImportResult:
        """
        Import complete Timeshift configuration to TimeLocker format
        
        Args:
            timeshift_config: Parsed Timeshift configuration
            repository_name: Name for imported repository
            target_name: Name for imported backup target
            manual_repository_path: Manual repository path if UUID resolution fails
            backup_paths: Custom backup paths
            
        Returns:
            Import result with configurations and any warnings/errors
        """
        try:
            # Create repository configuration
            repo_config = self.create_repository_config(
                    timeshift_config, repository_name, manual_repository_path
            )

            # Create backup target configuration
            target_config = self.create_backup_target_config(
                    timeshift_config, target_name, repository_name, backup_paths
            )

            # Check for BTRFS mode warning
            if timeshift_config.get("btrfs_mode", "false") == "true":
                self.warnings.append(
                        "Timeshift was configured for BTRFS snapshots. "
                        "TimeLocker uses restic for file-level backups, which works differently. "
                        "Consider the differences in backup approach."
                )

            return TimeshiftImportResult(
                    success=True,
                    repository_config=repo_config,
                    backup_target_config=target_config,
                    warnings=self.warnings.copy(),
                    errors=self.errors.copy()
            )

        except Exception as e:
            self.errors.append(f"Failed to import configuration: {e}")
            return TimeshiftImportResult(
                    success=False,
                    warnings=self.warnings.copy(),
                    errors=self.errors.copy()
            )
