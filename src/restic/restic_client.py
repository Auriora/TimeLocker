import shlex
import subprocess
import json
from typing import Dict, List
from packaging import version

from restic.logging import logger
from restic.errors import ResticError
from restic.restic_command_definition import restic_command
from utils.command_builder import CommandBuilder
from utils.execute_command import ExecuteCommand
from restic.restic_repository import ResticRepository
from backup_target import BackupTarget
from backup_snapshot import BackupSnapshot

RESTIC_COMMAND = "restic"
RESTIC_VERSION_COMMAND = f"{RESTIC_COMMAND} version --json"
RESTIC_MIN_VERSION = "0.18.0"

def _verify_restic_executable(min_version: str) -> str | None:
    try:
        logger.info("Verifying restic executable...")

        restic_executable = shlex.split(RESTIC_VERSION_COMMAND)
        subprocess_result = subprocess.run(
            restic_executable,
            check=True,
            capture_output=True,
            text=True
        )
        restic_version = subprocess_result.stdout

        if version.parse(restic_version) < version.parse(min_version):
            raise ResticError(f"restic version {restic_version} is below the required minimum version {min_version}.")

        return restic_version
    except FileNotFoundError:
        raise ResticError("restic executable not found. Please ensure it is installed and in the PATH.")

class Restic:
    def __init__(self, repo: ResticRepository, min_version: str = RESTIC_MIN_VERSION):
        logger.info("Initializing ResticClient...")
        self.command_builder = CommandBuilder(restic_command)
        self.restic_version = _verify_restic_executable(min_version)
        self.repo = repo
        self.repo.validate()
        logger.info(f"Detected restic version: {self.restic_version}")

    def _base_command(self):
        return ["restic", "-r", self.repo.location]

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

    def backup(self, target: BackupTarget):
        cmd = self.command_builder.build_backup_command(target)
        return ExecuteCommand.run(cmd, self.repo.to_env())

    def restore(self, snapshot_id: str, target_path: str) -> str:
        cmd = self._base_command() + ["restore", snapshot_id, "--target", target_path]
        return ExecuteCommand.run(cmd, self.repo.to_env())

    def snapshots(self) -> List[BackupSnapshot]:
        cmd = self._base_command() + ["snapshots", "--json"]
        output = ExecuteCommand.run(cmd, self.repo.to_env())
        snapshots_data = json.loads(output)
        return [
            BackupSnapshot(repo=self.repo, snapshot_id=s["short_id"], timestamp=s["time"], paths=s["paths"])
            for s in snapshots_data
        ]

    def forget(self, snapshot_id: str, prune: bool = False) -> str:
        cmd = self._base_command() + ["forget", snapshot_id]
        if prune:
            cmd.append("--prune")
        return ExecuteCommand.run(cmd, self.repo.to_env())

    def init_repository(self) -> str:
        cmd = self._base_command() + ["init"]
        return ExecuteCommand.run(cmd, self.repo.to_env())