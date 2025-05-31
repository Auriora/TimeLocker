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
import os
import hashlib
import subprocess
from abc import abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from packaging import version

from TimeLocker.backup_repository import BackupRepository, RetentionPolicy
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.backup_target import BackupTarget
from TimeLocker.restic.errors import RepositoryError, ResticError
from TimeLocker.restic.logging import logger
from TimeLocker.restic.restic_command_definition import restic_command_def
from TimeLocker.command_builder import CommandBuilder
from TimeLocker.security import CredentialManager

RESTIC_COMMAND = "restic"
RESTIC_VERSION_COMMAND = f"{RESTIC_COMMAND} --json version"
RESTIC_MIN_VERSION = "0.18.0"


class ResticRepository(BackupRepository):
    def __init__(self, location: str, tags: Optional[List[str]] = None, password: Optional[str] = None,
                 min_version: str = RESTIC_MIN_VERSION, credential_manager: Optional[CredentialManager] = None):
        logger.info(f"Initializing repository at location: {location}")
        self._command = CommandBuilder(restic_command_def).param("json")
        self._restic_version = self._verify_restic_executable(min_version)
        logger.info("Detected restic version: %s", self._restic_version)  # from logging import logger
        self._location = location
        self._explicit_password = password
        self._credential_manager = credential_manager
        self._cached_env = None
        self._repository_id = self._generate_repository_id()
        self.validate()
        self._command = self._command.param("repo", self.uri)

    def _verify_restic_executable(self, min_version: str) -> str | None:
        try:
            logger.info("Verifying restic executable...")
            # Build version command - json is a global parameter, so add it first
            version_command = CommandBuilder(restic_command_def)
            version_command.param("json")
            version_command.command("version")
            subprocess_result = version_command.run()
            version_dict = json.loads(subprocess_result)
            restic_version = version_dict.get("version", None)

            if version.parse(restic_version) < version.parse(min_version):
                raise ResticError(f"restic version {restic_version} is below the required minimum version {min_version}.")

            return restic_version
        except Exception as e:
            # If JSON parsing fails, try without JSON flag for basic version check
            logger.warning(f"JSON version check failed: {e}, trying basic version check")
            try:
                basic_command = CommandBuilder(restic_command_def).command("version")
                subprocess_result = basic_command.run()
                # Parse version from text output (format: "restic 0.18.0 compiled with go1.21.5 on linux/amd64")
                lines = subprocess_result.strip().split('\n')
                for line in lines:
                    if line.startswith('restic '):
                        parts = line.split()
                        if len(parts) >= 2:
                            restic_version = parts[1]
                            if version.parse(restic_version) < version.parse(min_version):
                                raise ResticError(f"restic version {restic_version} is below the required minimum version {min_version}.")
                            return restic_version
                raise ResticError("Could not parse restic version from output")
            except FileNotFoundError:
                raise ResticError("restic executable not found. Please ensure it is installed and in the PATH.")
            except Exception as e2:
                raise ResticError(f"Failed to verify restic executable: {e2}")

    def _generate_repository_id(self) -> str:
        """Generate a unique ID for this repository based on its location"""
        return hashlib.sha256(self._location.encode()).hexdigest()[:16]

    def repository_id(self) -> str:
        """Get the unique repository ID"""
        return self._repository_id

    def password(self) -> Optional[str]:
        """Get repository password from explicit setting, credential manager, or environment"""
        # Priority: explicit password > credential manager > environment variable
        if self._explicit_password:
            return self._explicit_password

        if self._credential_manager and not self._credential_manager.is_locked():
            stored_password = self._credential_manager.get_repository_password(self._repository_id)
            if stored_password:
                return stored_password

        return os.getenv("RESTIC_PASSWORD")

    def store_password(self, password: str) -> bool:
        """Store password in credential manager if available"""
        if self._credential_manager and not self._credential_manager.is_locked():
            try:
                self._credential_manager.store_repository_password(self._repository_id, password)
                logger.info(f"Password stored for repository {self._repository_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to store password: {e}")
                return False
        return False

    def to_env(self) -> Dict[str, str]:
        if self._cached_env:
            return self._cached_env

        env = {}
        pwd = self.password()
        if not pwd:
            raise RepositoryError("RESTIC_PASSWORD must be set explicitly or in the environment.")
        env["RESTIC_PASSWORD"] = pwd
        env.update(self.backend_env())
        logger.debug("Constructed environment for restic")
        self._cached_env = env
        return env

    def uri(self) -> str:
        return f"{self._location}"

    def initialize(self) -> bool:
        """Initialize the backup repository"""
        try:
            result = self._command.param("init").run(self.to_env())
            logger.info("Repository initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize repository: {e}")
            return False

    def check(self) -> bool:
        """Check if the backup repository is available"""
        try:
            self._command.param("check").run(self.to_env())
            logger.info("Repository check passed")
            return True
        except Exception as e:
            logger.error(f"Repository check failed: {e}")
            return False

    def backup_target(self, targets: List[BackupTarget], tags: Optional[List[str]] = None) -> Dict:
        """
        Create a new backup from the specified targets

        Args:
            targets: List of BackupTarget objects defining what to backup
            tags: Optional list of tags to add to the backup

        Returns:
            Dict: Backup result information including snapshot ID and statistics

        Raises:
            RepositoryError: If backup operation fails
        """
        if not targets:
            raise RepositoryError("At least one backup target must be specified")

        # Validate all targets
        for target in targets:
            target.validate()

        # Collect all paths to backup and build command arguments
        all_paths = []
        all_tags = set(tags or [])

        for target in targets:
            # Get paths from file selection
            paths = target.selection.get_backup_paths()
            all_paths.extend(paths)
            all_tags.update(target.tags)

        if not all_paths:
            raise RepositoryError("No paths specified for backup")

        # Build backup command using the existing command builder pattern
        backup_command = self._command.command("backup")

        # Add exclude patterns from all targets
        for target in targets:
            for pattern in target.selection.exclude_patterns:
                backup_command.param("exclude", pattern)
            for path in target.selection.excludes:
                backup_command.param("exclude", str(path))

        # Add tags if any
        if all_tags:
            tag_string = ",".join(sorted(all_tags))
            backup_command.param("tag", tag_string)

        try:
            # Build the complete command list manually since restic backup needs paths as positional args
            command_list = backup_command.build()
            command_list.extend(all_paths)  # Add paths at the end

            logger.info(f"Executing backup command: {' '.join(command_list[:3])} ... {len(all_paths)} paths")

            # Execute the command directly
            result = subprocess.run(
                    command_list,
                    capture_output=True,
                    text=True,
                    env=self.to_env(),
                    check=True
            )

            # Parse JSON output to get backup results
            lines = result.stdout.strip().split('\n')
            backup_result = None

            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get("message_type") == "summary":
                            backup_result = data
                            break
                    except json.JSONDecodeError:
                        continue

            if backup_result:
                snapshot_id = backup_result.get("snapshot_id", "unknown")
                files_new = backup_result.get("files_new", 0)
                files_changed = backup_result.get("files_changed", 0)
                files_unmodified = backup_result.get("files_unmodified", 0)
                data_added = backup_result.get("data_added", 0)

                logger.info(f"Backup completed successfully. Snapshot ID: {snapshot_id}")
                logger.info(f"Files: {files_new} new, {files_changed} changed, {files_unmodified} unmodified")
                logger.info(f"Data added: {data_added} bytes")

                return backup_result
            else:
                logger.warning("Backup completed but no summary found in output")
                return {
                        "message_type":     "summary",
                        "snapshot_id":      "unknown",
                        "files_new":        0,
                        "files_changed":    0,
                        "files_unmodified": 0,
                        "data_added":       0
                }

        except subprocess.CalledProcessError as e:
            logger.error(f"Backup command failed with exit code {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            raise RepositoryError(f"Backup failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Backup operation failed: {e}")
            raise RepositoryError(f"Backup failed: {e}")

    def verify_backup(self, snapshot_id: Optional[str] = None) -> bool:
        """
        Verify the integrity of a backup snapshot

        Args:
            snapshot_id: Specific snapshot to verify. If None, verifies the latest snapshot

        Returns:
            bool: True if verification successful, False otherwise
        """
        try:
            # Build check command - need to create new builder without json since check doesn't support it
            check_command = CommandBuilder(restic_command_def)
            check_command = check_command.param("repo", self.uri())
            check_command = check_command.command("check")

            if snapshot_id:
                check_command = check_command.param("read-data-subset", f"{snapshot_id}")

            logger.info(f"Verifying backup integrity{f' for snapshot {snapshot_id}' if snapshot_id else ''}")

            # Execute check command
            command_list = check_command.build()

            result = subprocess.run(
                    command_list,
                    capture_output=True,
                    text=True,
                    env=self.to_env(),
                    check=True
            )

            logger.info("Backup verification completed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Backup verification failed with exit code {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        """List available snapshots"""
        output = self._command.param("snapshots").run(self.to_env())
        snapshots_data = json.loads(output)
        return [BackupSnapshot(repo=self, snapshot_id=s["short_id"], timestamp=s["time"], paths=s["paths"]) for s in snapshots_data]

    def restore(self, snapshot_id: str, target_path: Optional[Path] = None) -> str:
        return self._command.param("restore").param(snapshot_id).param("target", target_path).run(self.to_env())

    def stats(self) -> dict:
        """Get snapshot stats"""
        output = self._command.param("stats").run(self.to_env())
        return json.loads(output)

    def location(self) -> str:
        """Get repository location"""
        return self._location

    def apply_retention_policy(self, policy: RetentionPolicy, prune: bool = False) -> bool:
        """
        Remove snapshots according to retention policy.
        At least one retention period must be specified.

        Args:
            policy: Retention policy specifying which snapshots to keep
            prune: If True, automatically run prune after forgetting snapshots
        """
        cmdline = self._command.param("forget")
        if prune:
            cmdline.param("--prune")
        result = cmdline.run(self.to_env())
        if result.returncode != 0:
            logger.error("Failed to implement Retention Policy: {result.stderr}")
            return False
        return True

    def forget_snapshot(self, snapshotid: str, prune: bool = False) -> bool:
        """
        Remove snapshots according to retention policy.
        At least one retention period must be specified.

        Args:
            snapshotid: ID of the Snapshot to remove
            prune: If True, automatically run prune after forgetting snapshots
        """
        cmdline = self._command.param("forget").param(snapshotid)
        if prune:
            cmdline.param("--prune")
        result = cmdline.run(self.to_env())
        if result.returncode != 0:
            logger.error("Failed to initialize repository: {result.stderr}")
            return False
        return True

    def prune_data(self) -> str:
        """
        Remove unreferenced data from the repository.
        This removes file chunks that are no longer used by any snapshot.
        """
        return self._command.param("prune").run(self.to_env())

    def validate(self) -> str:
        """Validate repository configuration"""
        return self._command.param("validate").run(self.to_env())

    @abstractmethod
    def backend_env(self) -> Dict[str, str]:
        pass

    def _handle_restic_output(self, output: Dict):
        message_type = output.get("message_type")
        if message_type == "summary":
            self._on_backup_summary(output)
        elif message_type == "status":
            self._on_backup_status(output)
        # Handle other message types as needed

    def _on_backup_summary(self, summary: Dict):
        # Placeholder for event handling logic
        print(f"Backup Summary: {summary}")

    def _on_backup_status(self, status: Dict):
        # Placeholder for event handling logic
        print(f"Backup Status: {status}")
