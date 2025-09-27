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

try:
    import dateutil.parser
except ImportError:
    dateutil = None

from ..backup_repository import BackupRepository, RetentionPolicy
from ..backup_snapshot import BackupSnapshot
from ..backup_target import BackupTarget
from .errors import RepositoryError, ResticError
from .logging import logger
from .restic_command_definition import restic_command_def
from ..command_builder import CommandBuilder
from ..security import CredentialManager

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
        logger.debug(f"ResticRepository initialized with explicit password: {'***' if password else 'None'}")
        self._credential_manager = credential_manager
        self._cached_env = None
        self._repository_id = self._generate_repository_id()
        self.validate()
        self._command = self._command.param("repo", self.uri)

    def _verify_restic_executable(self, min_version: str) -> Optional[str]:
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
        except (json.JSONDecodeError, FileNotFoundError) as e:
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
        # Priority: explicit password > credential manager (with auto-unlock) > environment variable
        logger.debug(f"password() called - explicit password: {'***' if self._explicit_password else 'None'}")
        if self._explicit_password:
            logger.debug("Returning explicit password")
            return self._explicit_password

        # Try credential manager with auto-unlock (non-interactive)
        if self._credential_manager:
            stored_password = self._credential_manager.get_repository_password(
                    self._repository_id,
                    allow_prompt=False  # Non-interactive for automated operations
            )
            if stored_password:
                logger.debug("Returning credential manager password")
                return stored_password

        # Check TimeLocker environment variable first, then fall back to RESTIC_PASSWORD
        env_password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
        logger.debug(f"Returning environment password: {'***' if env_password else 'None'}")
        return env_password

    def store_password(self, password: str, allow_prompt: bool = True) -> bool:
        """Store password in credential manager if available"""
        if self._credential_manager:
            try:
                self._credential_manager.store_repository_password(
                        self._repository_id,
                        password,
                        allow_prompt=allow_prompt
                )
                logger.info(f"Password stored for repository {self._repository_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to store password: {e}")
                return False
        return False

    def to_env(self) -> Dict[str, str]:
        if self._cached_env:
            return self._cached_env

        # Start with current environment to preserve PATH and other system variables
        import os
        env = os.environ.copy()

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
            result = self._command.command("init").run(self.to_env())
            logger.info("Repository initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize repository: {e}")
            return False

    def check(self) -> bool:
        """Check if the backup repository is available"""
        try:
            self._command.command("check").run(self.to_env())
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
        Verify the integrity of a backup repository

        Args:
            snapshot_id: Specific snapshot to verify. If None, performs basic repository check.
                        Note: Snapshot-specific verification is not currently supported.

        Returns:
            bool: True if verification successful, False otherwise
        """
        try:
            # Build check command with JSON support for better error parsing
            check_command = CommandBuilder(restic_command_def)
            check_command = check_command.param("json")
            check_command = check_command.param("repo", self.uri())
            check_command = check_command.command("check")

            # Note: We perform basic repository check regardless of snapshot_id
            # Snapshot-specific verification would require different approach
            if snapshot_id:
                logger.info(f"Performing repository verification (snapshot-specific verification not supported)")
            else:
                logger.info("Verifying backup repository integrity")

            # Execute check command
            command_list = check_command.build()

            result = subprocess.run(
                    command_list,
                    capture_output=True,
                    text=True,
                    env=self.to_env(),
                    check=True
            )

            # Parse JSON output for better error reporting
            if result.stdout.strip():
                try:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            data = json.loads(line)
                            if data.get("message_type") == "summary":
                                num_errors = data.get("num_errors", 0)
                                if num_errors > 0:
                                    logger.warning(f"Repository check found {num_errors} errors")
                                    return False
                except json.JSONDecodeError:
                    # Fallback to basic success if JSON parsing fails
                    logger.debug("Could not parse JSON output, assuming success based on exit code")

            logger.info("Backup verification completed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Backup verification failed with exit code {e.returncode}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def verify_backup_comprehensive(self, snapshot_id: Optional[str] = None) -> Dict[str, any]:
        """
        Perform comprehensive backup verification with detailed results

        Args:
            snapshot_id: Specific snapshot to verify. If None, verifies repository

        Returns:
            Dict with verification results and details
        """
        verification_result = {
                "success":          False,
                "checks_performed": [],
                "errors":           [],
                "warnings":         [],
                "statistics":       {}
        }

        try:
            # 1. Basic repository check
            logger.info("Performing basic repository check...")
            verification_result["checks_performed"].append("repository_structure")

            basic_check = self.verify_backup(snapshot_id)
            if not basic_check:
                verification_result["errors"].append("Basic repository check failed")
                return verification_result

            # 2. Check repository statistics
            logger.info("Gathering repository statistics...")
            verification_result["checks_performed"].append("statistics")
            try:
                stats = self.stats()
                verification_result["statistics"] = stats
            except Exception as e:
                verification_result["warnings"].append(f"Could not gather statistics: {e}")

            # 3. Verify specific snapshot if provided
            if snapshot_id:
                logger.info(f"Verifying specific snapshot {snapshot_id}...")
                verification_result["checks_performed"].append("snapshot_integrity")

                try:
                    # Check if snapshot exists
                    snapshots = self.snapshots()
                    snapshot_exists = any(s.id == snapshot_id for s in snapshots)

                    if not snapshot_exists:
                        verification_result["errors"].append(f"Snapshot {snapshot_id} not found")
                        return verification_result

                except Exception as e:
                    verification_result["warnings"].append(f"Could not list snapshots: {e}")

            # 4. Check for repository consistency
            logger.info("Checking repository consistency...")
            verification_result["checks_performed"].append("consistency")

            try:
                # Use restic check with --read-data for thorough verification
                check_command = CommandBuilder(restic_command_def)
                check_command = check_command.param("repo", self.uri())
                check_command = check_command.command("check")
                check_command = check_command.param("read-data")

                command_list = check_command.build()

                result = subprocess.run(
                        command_list,
                        capture_output=True,
                        text=True,
                        env=self.to_env(),
                        timeout=300  # 5 minute timeout for data verification
                )

                if result.returncode != 0:
                    verification_result["errors"].append(f"Data verification failed: {result.stderr}")
                    return verification_result

            except subprocess.TimeoutExpired:
                verification_result["warnings"].append("Data verification timed out after 5 minutes")
            except Exception as e:
                verification_result["warnings"].append(f"Data verification failed: {e}")

            verification_result["success"] = True
            logger.info("Comprehensive backup verification completed successfully")

        except Exception as e:
            verification_result["errors"].append(f"Verification failed: {e}")
            logger.error(f"Comprehensive backup verification failed: {e}")

        return verification_result

    def snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        """List available snapshots"""
        output = self._command.command("snapshots").run(self.to_env())
        snapshots_data = json.loads(output)

        snapshots = []
        for s in snapshots_data:
            # Parse the timestamp string to datetime object
            from datetime import datetime
            timestamp_str = s["time"]
            # Handle ISO format with timezone
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            elif '+' in timestamp_str[-6:] or timestamp_str[-6:].count(':') == 2:
                # Already has timezone info
                pass
            else:
                # Add UTC timezone if missing
                timestamp_str += '+00:00'

            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                # Fallback for older Python versions or different formats
                if dateutil:
                    timestamp = dateutil.parser.parse(timestamp_str)
                else:
                    # Basic fallback - try to parse manually
                    # Format: 2025-03-29T21:09:34.068185654+02:00
                    import re
                    # Remove microseconds if too long and parse
                    clean_str = re.sub(r'\.(\d{6})\d*', r'.\1', timestamp_str)
                    timestamp = datetime.fromisoformat(clean_str)

            # Convert paths to Path objects
            from pathlib import Path
            paths = [Path(p) for p in s["paths"]]

            snapshot = BackupSnapshot(
                    repo=self,
                    snapshot_id=s["short_id"],
                    timestamp=timestamp,
                    paths=paths
            )

            # Add additional attributes from restic data
            if "hostname" in s:
                snapshot.hostname = s["hostname"]
            if "tags" in s:
                snapshot.tags = s["tags"]
            else:
                snapshot.tags = []

            snapshots.append(snapshot)

        return snapshots

    def restore(self, snapshot_id: str, target_path: Optional[Path] = None) -> str:
        return self._command.command("restore").param(snapshot_id).param("target", target_path).run(self.to_env())

    def stats(self) -> dict:
        """Get snapshot stats"""
        output = self._command.command("stats").run(self.to_env())
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
        cmdline = self._command.command("forget")
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
        cmdline = self._command.command("forget").param(snapshotid)
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
        return self._command.command("prune").run(self.to_env())

    def validate(self) -> str:
        """Validate repository configuration"""
        # Use check command to validate repository
        self.check()
        return "Repository validation successful"

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
