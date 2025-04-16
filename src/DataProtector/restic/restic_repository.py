import json
import os

from abc import abstractmethod
from pathlib import Path
from typing import Optional, Dict, List
from packaging import version

from backup_repository import BackupRepository, RetentionPolicy
from backup_snapshot import BackupSnapshot
from backup_target import BackupTarget

from utils.command_builder import CommandBuilder

from restic.errors import RepositoryError, ResticError
from restic.logging import logger
from restic.restic_command_definition import restic_command_def

RESTIC_COMMAND = "restic"
RESTIC_VERSION_COMMAND = f"{RESTIC_COMMAND} --json version"
RESTIC_MIN_VERSION = "0.18.0"


class ResticRepository(BackupRepository):
    def __init__(self, location: str, tags: Optional[List[str]] = None, password: Optional[str] = None, min_version: str = RESTIC_MIN_VERSION):
        logger.info(f"Initializing repository at location: {location}")
        self._command = CommandBuilder(restic_command_def).param("json")
        self._restic_version = self._verify_restic_executable(min_version)
        logger.info("Detected restic version: %s", self._restic_version)  # from logging import logger
        self._location = location
        self._explicit_password = password
        self._cached_env = None
        self.validate()
        self._command = self._command.param("repo", self.uri)

    def _verify_restic_executable(self, min_version: str) -> str | None:
        try:
            logger.info("Verifying restic executable...")
            subprocess_result = self._command.param("version").run()
            version_dict = json.loads(subprocess_result)
            restic_version = version_dict.get("version", None)

            if version.parse(restic_version) < version.parse(min_version):
                raise ResticError(f"restic version {restic_version} is below the required minimum version {min_version}.")

            return restic_version
        except FileNotFoundError:
            raise ResticError("restic executable not found. Please ensure it is installed and in the PATH.")

    def password(self) -> Optional[str]:
        return self._explicit_password or os.getenv("RESTIC_PASSWORD")

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
        result = self._command.param("init").run(self.to_env())
        if result.returncode != 0:
            logger.error("Failed to initialize repository: {result.stderr}")
            return False
        return True

    def check(self) -> str:
        """Check if the backup repository is available"""
        return self._command.param("check").run(self.to_env())

    def backup_target(self, targets: List[BackupTarget], tags: Optional[List[str]] = None) -> str:
        """Create a new backup"""
        return self._command.param("backup").run(self.to_env())

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

