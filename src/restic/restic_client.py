import shlex
import subprocess
import json
from typing import Dict, List
from packaging import version

from restic.logging import logger
from restic.errors import ResticError, CommandExecutionError
from restic.command import ResticCommand, CommandBuilder
from restic.repository import Repository
from target import Target
from snapshot import BackupSnapshot

RESTIC_COMMAND = "restic"
RESTIC_VERSION_COMMAND = f"{RESTIC_COMMAND} version --json"
RESTIC_MIN_VERSION = "0.18.0"

def _verify_restic_executable(min_version: str) -> str | None:
    try:
        logger.info("Verifying restic executable...")

        restic_command = shlex.split(RESTIC_VERSION_COMMAND)
        subprocess_result = subprocess.run(
            restic_command,
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
    def __init__(self, repo: Repository, min_version: str = RESTIC_MIN_VERSION):
        logger.info("Initializing ResticClient...")
        self.command_builder = CommandBuilder(min_version)
        self.restic_version = _verify_restic_executable(min_version)
        self.repo = repo
        self.repo.validate()
        logger.info(f"Detected restic version: {self.restic_version}")

    def _base_command(self):
        return ["restic", "-r", self.repo.location]

    def _run_restic_command(self, command: List[str]) -> Dict:
        supported = {"backup", "snapshots", "forget", "restore", "prune", "init", "check"}
        json_producing_commands = {"backup", "snapshots", "forget", "restore"}
        if command[0] in supported and command[0] in json_producing_commands:
            command.append("--json")
        full_command = ["restic"] + command
        logger.info(f"Executing command: {' '.join(full_command)}")
        try:
            result = subprocess.run(
                full_command,
                check=True,
                capture_output=True,
                text=True,
                env=self.repo.to_env()
            )
            logger.debug("Command output: %s", result.stdout)
            return json.loads(result.stdout) if command[0] in json_producing_commands else {"output": result.stdout}
        except subprocess.CalledProcessError as e:
            logger.error("Command error output: %s", e.stderr)
            raise CommandExecutionError(f"Command failed: {' '.join(command)}", stderr=e.stderr.strip())

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

    def backup(self, target: Target):
        cmd = self.command_builder.build_backup_command(target)
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=self.repo.to_env()
            )
            output = json.loads(result.stdout)
            self._handle_restic_output(output)
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip()
            try:
                error_json = json.loads(error_output)
                error_message = error_json.get("message", error_output)
                error_code = error_json.get("code", e.returncode)
            except json.JSONDecodeError:
                error_message = error_output
                error_code = e.returncode
            raise RuntimeError(f"restic command failed with exit code {error_code}: {error_message}")

    def restore(self, snapshot_id: str, target_path: str) -> str:
        cmd = self._base_command() + ["restore", snapshot_id, "--target", target_path]
        return ResticCommand.run(cmd, self.repo.to_env())

    def snapshots(self) -> List[BackupSnapshot]:
        cmd = self._base_command() + ["snapshots", "--json"]
        output = ResticCommand.run(cmd, self.repo.to_env())
        snapshots_data = json.loads(output)
        return [
            BackupSnapshot(snapshot_id=s["short_id"], timestamp=s["time"], paths=s["paths"])
            for s in snapshots_data
        ]

    def forget(self, snapshot_id: str, prune: bool = False) -> str:
        cmd = self._base_command() + ["forget", snapshot_id]
        if prune:
            cmd.append("--prune")
        return ResticCommand.run(cmd, self.repo.to_env())

    def init_repository(self) -> str:
        cmd = self._base_command() + ["init"]
        return ResticCommand.run(cmd, self.repo.to_env())