import os
import subprocess

from typing import Dict, List

from packaging import version

from backup_target import BackupTarget

from restic.errors import CommandExecutionError

class ResticCommand:
    @staticmethod
    def run(command: List[str], env: Dict[str, str]) -> str:
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                env={**env, **os.environ},
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise CommandExecutionError(f"Command failed: {' '.join(command)}", stderr=e.stderr.strip())

class CommandBuilder:
    def __init__(self, restic_version: str):
        self.restic_version = version.parse(restic_version)

    def build_backup_command(self, target: BackupTarget) -> list:
        cmd = ["restic", "backup", target.selection.paths.join(' '), "--json"]

        # Include tags if available
        for tag in target.tags:
            cmd += ["--tag", tag]

        # Handle excludes based on the restic version
        if self.restic_version >= version.parse("0.9.0"):
            for pattern in target.exclusion.patterns:
                cmd += ["--exclude", pattern]
        else:
            # For older versions, use alternative exclude handling if necessary
            pass  # Implement as needed for older versions

        return cmd

    # Additional methods for other commands can be implemented similarly