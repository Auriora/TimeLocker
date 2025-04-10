import os
from subprocess import run, Popen, PIPE, STDOUT, SubprocessError, CalledProcessError  # from subprocess import run, CompletedProcess

from typing import Callable, Dict, List
from packaging import version

from backup_target import BackupTarget
from restic.errors import CommandExecutionError


class ResticCommand:
    @staticmethod
    def run(command: List[str], env: Dict[str, str]) -> str:
        try:
            result = run(
                command,
                check=True,
                capture_output=True,
                env={**env, **os.environ},
                text=True
            )
            return result.stdout.strip()
        except CalledProcessError as e:
            raise CommandExecutionError(f"Command failed: {' '.join(command)}", stderr=e.stderr.strip())

    @staticmethod
    def run_with_callback(
        command: List[str],
        env: Dict[str, str],
        callback: Callable[[str], None]
    ) -> str:
        process = Popen(
            command,
            env={**env, **os.environ},
            stdout=PIPE,
            stderr=STDOUT,
            text=True,
            bufsize=1
        )

        output = []
        for line in process.stdout:
            output.append(line)
            callback(line.strip())

        process.communicate()
        return_code = process.returncode
        if return_code != 0:
            raise CommandExecutionError(
                f"Command failed with return code {return_code}: {' '.join(command)}",
                stderr=''.join(output)
            )

        return ''.join(output)

    @staticmethod
    def run_iter(command: List[str], env: Dict[str, str]):
        try:
            process = Popen(
                command,
                env={**env, **os.environ},
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                bufsize=1
            )
        except SubprocessError as e:
            raise CommandExecutionError(f"Failed to start command: {' '.join(command)}", stderr=str(e))

        while True:
            try:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    yield line.strip()
            except IOError as e:
                raise CommandExecutionError(f"Error reading command output: {' '.join(command)}", stderr=str(e))

        if process.returncode != 0:
            raise CommandExecutionError(
                f"Command failed: {' '.join(command)}",
                stderr="Process failed with non-zero exit code"
            )


class CommandBuilder:
    def __init__(self, restic_version: str):
        self.restic_version = version.parse(restic_version)

    def build_backup_command(self, target: BackupTarget) -> list:
        if not isinstance(target.selection.paths, list):
            raise TypeError("target.selection.paths must be a list")
        cmd = ["restic", "backup"] + target.selection.paths + ["--json"]

        # Include tags if available
        for tag in target.tags:
            cmd += ["--tag", tag]

        # Handle excludes based on the restic version
        if self.restic_version >= version.parse("0.9.0"):
            for pattern in target.exclusion.patterns:
                cmd += ["--exclude", pattern]
        else:
            # TODO: Implement alternative exclude handling for older restic versions
            # For versions < 0.9.0, consider using --exclude-file option or other appropriate methods
            pass

        return cmd

    # Additional methods for other commands can be implemented similarly