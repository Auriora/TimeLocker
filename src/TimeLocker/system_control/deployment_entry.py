#!/usr/bin/env python3
"""Supported protected TimeLocker installation and release administration.

This operator-facing harness deliberately keeps candidate probes independent of
temporary Python files.  Every identity-sensitive probe runs against the staged
release before the selected-release document or systemd service unit changes.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
from packaging.utils import canonicalize_name, parse_wheel_filename
import re
import shutil
import signal
import stat
import subprocess
import time
from types import FrameType
from typing import Callable, TextIO
import zipfile

try:
    import fcntl
    import grp
    import pwd
except ImportError:  # pragma: no cover - reported explicitly on non-POSIX hosts.
    fcntl = None  # type: ignore[assignment]
    grp = None  # type: ignore[assignment]
    pwd = None  # type: ignore[assignment]

from .deployment import (
    AssetTarget,
    SystemReleaseDeployment,
    build_asset_manifest,
    linux_asset_targets,
)
from .models import PROTOCOL_VERSION
from .release_launcher import ImmutableReleaseResolver


RELEASE_ID_PATTERN = re.compile(r"[0-9a-f]{40}")
WHEEL_FILENAME_PATTERN = re.compile(
    r"[A-Za-z0-9_.+!]+(?:-[A-Za-z0-9_.+!]+){4,}\.whl"
)
REQUIRED_ENTRYPOINTS = (
    "timelocker",
    "tl",
    "timelocker-tray",
    "timelocker-system-control",
)
REQUIRED_ACTIVE_UNITS = (
    "timelocker-control.socket",
    "timelocker-npbackup-migration.timer",
    "timelocker-retention.timer",
)
REQUIRED_ENABLED_UNITS = (
    "timelocker-control.socket",
    "timelocker-npbackup-migration.timer",
    "timelocker-retention.timer",
)

BACKEND_IMPORT_PROBE = """\
from TimeLocker.system_control.backend_entry import main
from TimeLocker.system_control.models import PROTOCOL_VERSION
assert callable(main)
print(PROTOCOL_VERSION)
"""

PACKAGED_UNIT_PROBE = """\
from importlib.resources import files
print(files("TimeLocker.system_control.assets") / "timelocker-control.service")
"""

LAUNCHER_COMPATIBILITY_PROBE = """\
import sys
from TimeLocker.system_control.release_launcher import ImmutableReleaseResolver
resolver = ImmutableReleaseResolver()
current = resolver.release_manifest(sys.argv[1])
candidate = resolver.release_manifest(sys.argv[2])
assert current.release_id == sys.argv[1]
assert candidate.release_id == sys.argv[2]
assert candidate.control_protocol_version == int(sys.argv[3])
assert candidate.schema_version == 3
assert candidate.event_protocol_version is None
print("compatible")
"""


class DeploymentFailure(RuntimeError):
    """Raised when a deployment gate fails or rollback cannot complete."""


class DeploymentInterrupted(DeploymentFailure):
    """Raised when SIGINT or SIGTERM interrupts a deployment."""


@dataclass(frozen=True, slots=True)
class DeploymentPaths:
    """Protected paths used by the Linux immutable-release deployment."""

    releases_root: Path = Path("/opt/timelocker/releases")
    selector: Path = Path("/opt/timelocker/selected-release.json")
    service_unit: Path = Path("/etc/systemd/system/timelocker-control.service")
    evidence_root: Path = Path("/var/lib/timelocker/migration-backup")
    lock_file: Path = Path("/run/lock/timelocker/deploy.lock")
    launcher_venv: Path = Path("/opt/timelocker/launcher/venv")
    legacy_event_socket: Path = Path("/run/timelocker/status-events.sock")
    attention_file: Path = Path("/var/lib/timelocker/deployment-attention.json")
    expected_owner_uid: int = 0


@dataclass(frozen=True, slots=True)
class DeploymentRequest:
    """Validated inputs identifying the exact release artifact to deploy."""

    release_id: str
    expected_current: str | None
    wheel: Path
    wheel_sha256: str
    manifest: Path
    operator_user: str


class CommandExecutor:
    """Run bounded commands and optionally retain their redacted output."""

    def run(
        self,
        arguments: Sequence[str | Path],
        *,
        timeout: int = 30,
        output: Path | None = None,
        capture: bool = False,
        check: bool = True,
    ) -> str:
        command = [str(argument) for argument in arguments]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = completed.stdout
        if completed.stderr:
            combined += completed.stderr
        if output is not None:
            _write_private_text(output, combined)
        if check and completed.returncode != 0:
            raise DeploymentFailure(
                f"command failed ({completed.returncode}): {_display_command(command)}"
            )
        return completed.stdout if capture else combined


class T011LinuxDeployer:
    """Preflight-first, rollback-safe Linux deployment transaction."""

    def __init__(
        self,
        request: DeploymentRequest,
        *,
        paths: DeploymentPaths | None = None,
        executor: CommandExecutor | None = None,
        owner_uid: int | None = 0,
        owner_gid: int | None = 0,
        asset_targets: tuple[AssetTarget, ...] | None = None,
    ) -> None:
        self.request = request
        self.paths = paths or DeploymentPaths()
        self.executor = executor or CommandExecutor()
        self.owner_uid = owner_uid
        self.owner_gid = owner_gid
        self.asset_targets = asset_targets or linux_asset_targets()
        self.release = self.paths.releases_root / request.release_id
        self.evidence: Path | None = None
        self.staged_wheel: Path | None = None
        self.staged_manifest: Path | None = None
        self.staged_launcher = self.paths.launcher_venv.with_name(
            f".venv.{request.release_id}.staged"
        )
        self.previous_launcher = self.paths.launcher_venv.with_name(
            f"venv.previous.{request.expected_current or 'initial'}"
        )
        self.launcher_prior_moved = False
        self.launcher_swapped = False
        self.mutation_started = False
        self.completed = False

    def deploy(self) -> Path:
        """Stage, preflight, activate, and verify one exact release."""
        self.validate_request()
        self.capture_baseline()
        try:
            self.stage_release()
            self.preflight_staged_release()
            self.activate()
            self.verify_activation()
            if self.previous_launcher.exists():
                shutil.rmtree(self.previous_launcher)
            self.completed = True
        except BaseException:
            self.recover()
            raise
        assert self.evidence is not None
        return self.evidence

    def validate_request(self) -> None:
        """Reject unsafe or incoherent inputs before creating host state."""
        for field, value in (("release_id", self.request.release_id),):
            if RELEASE_ID_PATTERN.fullmatch(value) is None:
                raise DeploymentFailure(f"{field} must be a 40-character identity")
        if self.request.expected_current is not None and RELEASE_ID_PATTERN.fullmatch(
            self.request.expected_current
        ) is None:
            raise DeploymentFailure(
                "expected_current must be a 40-character identity"
            )
        if (
            len(self.request.wheel_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.request.wheel_sha256
            )
        ):
            raise DeploymentFailure("wheel_sha256 must be a lowercase SHA-256 digest")
        _require_regular_file(self.request.wheel, "wheel")
        _require_regular_file(self.request.manifest, "manifest")
        _validated_wheel_filename(self.request.wheel)
        if pwd is None:
            raise DeploymentFailure("protected deployment is unsupported on this platform")
        try:
            pwd.getpwnam(self.request.operator_user)
        except KeyError as error:
            raise DeploymentFailure("operator_user does not exist") from error
        if self.release.exists():
            raise DeploymentFailure(f"candidate release already exists: {self.release}")
        if self.staged_launcher.exists():
            raise DeploymentFailure(
                f"staged launcher already exists: {self.staged_launcher}"
            )
        if self.previous_launcher.exists():
            raise DeploymentFailure(
                f"launcher rollback path already exists: {self.previous_launcher}"
            )
        _require_trusted_directory(
            self.paths.launcher_venv.parent,
            expected_owner_uid=self.owner_uid,
        )
        if self.request.expected_current is not None:
            _require_trusted_directory(
                self.paths.launcher_venv,
                expected_owner_uid=self.owner_uid,
            )
            _require_trusted_executable(
                self.paths.launcher_venv / "bin/python",
                expected_owner_uid=self.owner_uid,
            )
        if _selected_release_optional(self.paths.selector) != self.request.expected_current:
            raise DeploymentFailure("selected release changed before deployment")
        if self.request.expected_current is not None:
            for unit in REQUIRED_ACTIVE_UNITS:
                self._systemctl_gate("is-active", unit)
            for unit in REQUIRED_ENABLED_UNITS:
                self._systemctl_gate("is-enabled", unit)

    def capture_baseline(self) -> None:
        """Create private evidence and immutable rollback inputs."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.evidence = (
            self.paths.evidence_root
            / f"t011-hardened-deploy-{timestamp}-{os.getpid()}"
        )
        _mkdir(self.evidence, mode=0o750, uid=self.owner_uid, gid=self.owner_gid)
        if self.paths.selector.exists():
            _atomic_copy(
                self.paths.selector,
                self.evidence / "selected-release.before.json",
                mode=0o600,
                uid=self.owner_uid,
                gid=self.owner_gid,
            )
        asset_baseline = self.evidence / "assets-before"
        _mkdir(
            asset_baseline,
            mode=0o700,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )
        existing_assets: list[str] = []
        for target in self.asset_targets:
            if not target.destination.exists():
                continue
            _require_regular_file(target.destination, "installed asset")
            _atomic_copy(
                target.destination,
                asset_baseline / target.source_name,
                mode=0o600,
                uid=self.owner_uid,
                gid=self.owner_gid,
            )
            existing_assets.append(target.source_name)
        _write_private_text(
            self.evidence / "assets-before.json",
            json.dumps(sorted(existing_assets), separators=(",", ":")) + "\n",
        )
        self.staged_wheel = self.evidence / _validated_wheel_filename(
            self.request.wheel
        )
        self.staged_manifest = self.evidence / "candidate-release.json"
        _atomic_copy(
            self.request.wheel,
            self.staged_wheel,
            mode=0o600,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )
        _atomic_copy(
            self.request.manifest,
            self.staged_manifest,
            mode=0o600,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )
        if _sha256(self.staged_wheel) != self.request.wheel_sha256:
            raise DeploymentFailure("copied wheel SHA-256 does not match")
        manifest = _read_json(self.staged_manifest)
        expected_manifest = {
            "schema_version": 3,
            "release_id": self.request.release_id,
            "control_protocol_version": 2,
            "entrypoint": "venv/bin/timelocker",
        }
        for field, expected in expected_manifest.items():
            if manifest.get(field) != expected:
                raise DeploymentFailure(f"manifest {field} is incompatible")

    def stage_release(self) -> None:
        """Install the wheel into an inert, immutable release directory."""
        assert self.evidence is not None
        assert self.staged_wheel is not None
        assert self.staged_manifest is not None
        _mkdir(self.release, mode=0o755, uid=self.owner_uid, gid=self.owner_gid)
        self.executor.run(
            ["python3", "-m", "venv", "--system-site-packages", self.release / "venv"],
            timeout=120,
            output=self.evidence / "venv-create.txt",
        )
        python = self.release / "venv/bin/python"
        self.executor.run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-index",
                self.staged_wheel,
            ],
            timeout=600,
            output=self.evidence / "pip-install.txt",
        )
        _atomic_copy(
            self.staged_manifest,
            self.release / "release.json",
            mode=0o644,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )
        _make_tree_immutable(
            self.release,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )
        self.executor.run(
            [
                "python3",
                "-m",
                "venv",
                "--system-site-packages",
                self.staged_launcher,
            ],
            timeout=120,
            output=self.evidence / "launcher-venv-create.txt",
        )
        self.executor.run(
            [
                self.staged_launcher / "bin/python",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-index",
                "--no-deps",
                self.staged_wheel,
            ],
            timeout=300,
            output=self.evidence / "launcher-pip-install.txt",
        )
        _make_tree_immutable(
            self.staged_launcher,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )

    def preflight_staged_release(self) -> None:
        """Exercise every target identity before protected activation."""
        assert self.evidence is not None
        python = self.release / "venv/bin/python"
        for entrypoint in REQUIRED_ENTRYPOINTS:
            path = self.release / "venv/bin" / entrypoint
            _require_regular_file(path, f"staged entrypoint {entrypoint}")
            expected = f"#!{python}"
            try:
                actual = path.open(encoding="utf-8").readline().rstrip("\n")
            except OSError as error:
                raise DeploymentFailure(
                    f"cannot inspect staged entrypoint: {entrypoint}"
                ) from error
            if actual != expected or not os.access(path, os.X_OK):
                raise DeploymentFailure(
                    f"staged entrypoint is not executable at its final path: {entrypoint}"
                )

        protocol_output = self.executor.run(
            [python, "-c", BACKEND_IMPORT_PROBE],
            output=self.evidence / "preflight-backend-protocol.txt",
            capture=True,
        ).strip()
        assert self.staged_manifest is not None
        manifest = _read_json(self.staged_manifest)
        expected_protocol_output = str(manifest["control_protocol_version"])
        if protocol_output != expected_protocol_output:
            raise DeploymentFailure(
                "staged backend protocol probe failed: "
                f"expected {expected_protocol_output}, got {protocol_output or '<empty>'}"
            )
        if self.request.expected_current is not None:
            launcher_output = self.executor.run(
                [
                    self.staged_launcher / "bin/python",
                    "-c",
                    LAUNCHER_COMPATIBILITY_PROBE,
                    self.request.expected_current,
                    self.request.release_id,
                    str(manifest["control_protocol_version"]),
                ],
                output=self.evidence / "preflight-launcher-compatibility.txt",
                capture=True,
            ).strip()
            if launcher_output != "compatible":
                raise DeploymentFailure("staged launcher compatibility probe failed")
        packaged_unit = Path(
            self.executor.run(
                [python, "-c", PACKAGED_UNIT_PROBE],
                capture=True,
            ).strip()
        )
        self._validate_packaged_unit(packaged_unit)
        self.executor.run(
            ["systemd-analyze", "verify", packaged_unit],
            timeout=30,
            output=self.evidence / "systemd-analyze-preflight.txt",
        )

        candidate_cli = self.release / "venv/bin/timelocker"
        candidate_version = self.executor.run(
            [
                "timeout",
                "10",
                "runuser",
                "-u",
                self.request.operator_user,
                "--",
                candidate_cli,
                "version",
                "--short",
            ],
            timeout=15,
            output=self.evidence / "preflight-cli-version.txt",
            capture=True,
        ).strip()
        expected_package_version = manifest["package_version"]
        if candidate_version != expected_package_version:
            raise DeploymentFailure(
                "staged CLI version probe failed: "
                f"expected {expected_package_version}, "
                f"got {candidate_version or '<empty>'}"
            )
        if _selected_release_optional(self.paths.selector) != self.request.expected_current:
            raise DeploymentFailure("selector changed during staged preflight")
        if self.request.expected_current is not None:
            for unit in REQUIRED_ACTIVE_UNITS:
                self._systemctl_gate("is-active", unit)
            for unit in REQUIRED_ENABLED_UNITS:
                self._systemctl_gate("is-enabled", unit)

    def activate(self) -> None:
        """Perform the bounded protected mutation after all preflights pass."""
        assert self.evidence is not None
        if _selected_release_optional(self.paths.selector) != self.request.expected_current:
            raise DeploymentFailure("selector changed immediately before activation")
        python = self.release / "venv/bin/python"
        packaged_unit = Path(
            self.executor.run(
                [python, "-c", PACKAGED_UNIT_PROBE],
                capture=True,
            ).strip()
        )
        assert self.staged_manifest is not None
        manifest = _read_json(self.staged_manifest)
        self.mutation_started = True
        if self.paths.launcher_venv.exists():
            self.launcher_prior_moved = True
            os.replace(self.paths.launcher_venv, self.previous_launcher)
        os.replace(self.staged_launcher, self.paths.launcher_venv)
        self.launcher_swapped = True
        if self.request.expected_current is not None:
            launcher_output = self.executor.run(
                [
                    self.paths.launcher_venv / "bin/python",
                    "-c",
                    LAUNCHER_COMPATIBILITY_PROBE,
                    self.request.expected_current,
                    self.request.release_id,
                    str(manifest["control_protocol_version"]),
                ],
                output=self.evidence / "activated-launcher-compatibility.txt",
                capture=True,
            ).strip()
            if launcher_output != "compatible":
                raise DeploymentFailure("activated launcher compatibility probe failed")
        asset_root = packaged_unit.parent
        asset_manifest = build_asset_manifest(
            asset_root=asset_root,
            release_id=self.request.release_id,
            package_version=str(manifest["package_version"]),
            asset_names=tuple(target.source_name for target in self.asset_targets),
        )
        SystemReleaseDeployment(
            resolver=ImmutableReleaseResolver(
                releases_root=self.paths.releases_root,
                selector_path=self.paths.selector,
                expected_owner_uid=self.owner_uid or 0,
            ),
            targets=self.asset_targets,
            expected_owner_uid=self.owner_uid or 0,
        ).install_assets(
            asset_root,
            asset_manifest,
        )
        self.executor.run(["systemctl", "daemon-reload"])
        # Remove the rejected resident event channel before selecting the
        # candidate. These commands are idempotent for clean installations.
        self.executor.run(
            ["systemctl", "disable", "--now", "timelocker-status-events.socket"],
            check=False,
        )
        self.executor.run(
            ["systemctl", "stop", "timelocker-control.service"],
            check=False,
        )
        self.paths.legacy_event_socket.unlink(missing_ok=True)
        select_command = [
            python,
            "-m",
            "TimeLocker.system_control.release_admin",
            "select",
            self.request.release_id,
        ]
        if self.request.expected_current is not None:
            select_command.extend(["--expected-current", self.request.expected_current])
        self.executor.run(
            select_command,
            output=self.evidence / "selected-release.txt",
        )
        self.executor.run(["systemctl", "restart", "timelocker-control.socket"])
        self.executor.run(
            [
                "systemctl",
                "enable",
                "--now",
                "timelocker-control.socket",
            ]
        )

    def verify_activation(self) -> None:
        """Verify the selected release without running backup or retention."""
        assert self.evidence is not None
        if _selected_release(self.paths.selector) != self.request.release_id:
            raise DeploymentFailure("candidate release was not selected")
        active_units = (
            REQUIRED_ACTIVE_UNITS
            if self.request.expected_current is not None
            else ("timelocker-control.socket",)
        )
        enabled_units = (
            REQUIRED_ENABLED_UNITS
            if self.request.expected_current is not None
            else ("timelocker-control.socket",)
        )
        for unit in active_units:
            self._systemctl_gate("is-active", unit)
        for unit in enabled_units:
            self._systemctl_gate("is-enabled", unit)
        self.executor.run(
            [
                "timeout",
                "15",
                "runuser",
                "-u",
                self.request.operator_user,
                "--",
                self.release / "venv/bin/timelocker",
                "runs",
                "list",
                "--limit",
                "3",
                "--json",
            ],
            timeout=20,
            output=self.evidence / "activated-authorized-runs.json",
        )
        _atomic_copy(
            self.paths.selector,
            self.evidence / "selected-release.after.json",
            mode=0o600,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )

    def recover(self) -> None:
        """Restore baseline state after any failed or interrupted transaction."""
        if self.completed:
            return
        errors: list[str] = []
        if self.mutation_started and self.evidence is not None:
            for source, destination, mode in (
                (
                    self.evidence / "selected-release.before.json",
                    self.paths.selector,
                    0o644,
                ),
            ):
                try:
                    if source.exists():
                        _atomic_copy(
                            source,
                            destination,
                            mode=mode,
                            uid=self.owner_uid,
                            gid=self.owner_gid,
                        )
                    else:
                        destination.unlink(missing_ok=True)
                except OSError as error:
                    errors.append(f"restore {destination}: {error}")
            try:
                existing_assets = set(
                    json.loads(
                        (self.evidence / "assets-before.json").read_text(
                            encoding="utf-8"
                        )
                    )
                )
                for target in self.asset_targets:
                    if target.source_name in existing_assets:
                        _atomic_copy(
                            self.evidence / "assets-before" / target.source_name,
                            target.destination,
                            mode=target.mode,
                            uid=self.owner_uid,
                            gid=self.owner_gid,
                        )
                    else:
                        target.destination.unlink(missing_ok=True)
            except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
                errors.append(f"restore installed assets: {error}")
            try:
                self._restore_launcher()
            except OSError as error:
                errors.append(f"restore stable launcher: {error}")
            for command in (
                ("systemctl", "daemon-reload"),
                ("systemctl", "restart", "timelocker-control.socket"),
            ):
                try:
                    self.executor.run(command, check=False)
                except (DeploymentFailure, OSError, subprocess.SubprocessError) as error:
                    errors.append(f"{' '.join(command)}: {error}")
            try:
                if (
                    _selected_release_optional(self.paths.selector)
                    != self.request.expected_current
                ):
                    errors.append("restored selector does not name prior release")
            except DeploymentFailure as error:
                errors.append(f"validate restored selector: {error}")
            if self.request.expected_current is not None:
                for action, units in (
                    ("is-active", REQUIRED_ACTIVE_UNITS),
                    ("is-enabled", REQUIRED_ENABLED_UNITS),
                ):
                    for unit in units:
                        try:
                            self._systemctl_gate(action, unit)
                        except (DeploymentFailure, subprocess.SubprocessError) as error:
                            errors.append(f"{action} {unit}: {error}")
        if self.release.exists():
            try:
                shutil.rmtree(self.release)
            except OSError as error:
                errors.append(f"remove candidate release: {error}")
        if self.staged_launcher.exists():
            try:
                shutil.rmtree(self.staged_launcher)
            except OSError as error:
                errors.append(f"remove staged launcher: {error}")
        if errors:
            _write_private_text(
                self.paths.attention_file,
                json.dumps(
                    {
                        "schema_version": 1,
                        "reason": "deployment_recovery_failed",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
            )
            raise DeploymentFailure(
                "deployment failed and rollback was incomplete: " + "; ".join(errors)
            )

    def _restore_launcher(self) -> None:
        """Restore the prior immutable launcher after activation begins."""
        if not self.launcher_prior_moved:
            if self.launcher_swapped and self.paths.launcher_venv.exists():
                os.replace(self.paths.launcher_venv, self.staged_launcher)
                self.launcher_swapped = False
            return
        if not self.previous_launcher.exists():
            self.launcher_prior_moved = False
            return
        if self.paths.launcher_venv.exists():
            os.replace(self.paths.launcher_venv, self.staged_launcher)
            self.launcher_swapped = False
        os.replace(self.previous_launcher, self.paths.launcher_venv)
        self.launcher_prior_moved = False

    def _validate_packaged_unit(self, packaged_unit: Path) -> None:
        _require_regular_file(packaged_unit, "packaged service unit")
        try:
            packaged_unit.resolve().relative_to(self.release.resolve())
        except ValueError as error:
            raise DeploymentFailure(
                "packaged service unit escapes the staged release"
            ) from error
        text = packaged_unit.read_text(encoding="utf-8")
        required_lines = {
            "Requires=timelocker-control.socket",
            "Sockets=timelocker-control.socket",
            "Type=exec",
            "RuntimeDirectoryPreserve=yes",
        }
        lines = set(text.splitlines())
        missing = required_lines - lines
        if missing:
            raise DeploymentFailure(
                "packaged service unit is missing: " + ", ".join(sorted(missing))
            )
        if "status-events" in text:
            raise DeploymentFailure("packaged service still references event socket")

    def _systemctl_gate(self, action: str, unit: str) -> None:
        self.executor.run(
            ["systemctl", action, "--quiet", unit],
            timeout=15,
        )


def _display_command(command: Sequence[str]) -> str:
    safe: list[str] = []
    for argument in command:
        if "\n" in argument or len(argument) > 160:
            safe.append("<inline-probe>")
        else:
            safe.append(argument)
    return " ".join(safe)


def _require_regular_file(path: Path, field: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise DeploymentFailure(f"{field} must be a regular non-symlink file")


def _require_trusted_directory(
    path: Path,
    *,
    expected_owner_uid: int | None,
) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise DeploymentFailure(f"trusted directory is unavailable: {path}") from error
    if not path.is_dir() or path.is_symlink():
        raise DeploymentFailure(f"trusted directory is invalid: {path}")
    if expected_owner_uid is not None and metadata.st_uid != expected_owner_uid:
        raise DeploymentFailure(f"trusted directory has wrong owner: {path}")
    if metadata.st_mode & 0o022:
        raise DeploymentFailure(f"trusted directory is group/world writable: {path}")


def _require_trusted_executable(
    path: Path,
    *,
    expected_owner_uid: int | None,
) -> None:
    _require_trusted_directory(
        path.parent,
        expected_owner_uid=expected_owner_uid,
    )
    try:
        metadata = path.resolve(strict=True).stat()
    except OSError as error:
        raise DeploymentFailure(f"trusted executable is unavailable: {path}") from error
    if not path.resolve().is_file() or not os.access(path, os.X_OK):
        raise DeploymentFailure(f"trusted executable is invalid: {path}")
    if expected_owner_uid is not None and metadata.st_uid != expected_owner_uid:
        raise DeploymentFailure(f"trusted executable has wrong owner: {path}")
    if metadata.st_mode & 0o022:
        raise DeploymentFailure(f"trusted executable is group/world writable: {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validated_wheel_filename(path: Path) -> str:
    """Return a pip-compatible wheel basename without changing its identity."""
    filename = path.name
    if WHEEL_FILENAME_PATTERN.fullmatch(filename) is None:
        raise DeploymentFailure(
            "wheel must use a valid wheel filename, for example "
            "timelocker-0.9.1-py3-none-any.whl"
        )
    return filename


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DeploymentFailure(f"cannot read JSON: {path}") from error
    if not isinstance(value, dict):
        raise DeploymentFailure(f"JSON document must be an object: {path}")
    return value


def _selected_release(selector: Path) -> str:
    value = _read_json(selector).get("selected")
    if not isinstance(value, str) or RELEASE_ID_PATTERN.fullmatch(value) is None:
        raise DeploymentFailure("selected-release document is invalid")
    return value


def _selected_release_optional(selector: Path) -> str | None:
    if not selector.exists():
        return None
    return _selected_release(selector)


def _mkdir(
    path: Path,
    *,
    mode: int,
    uid: int | None,
    gid: int | None,
) -> None:
    path.mkdir(parents=True, exist_ok=False)
    os.chmod(path, mode)
    if uid is not None and gid is not None:
        os.chown(path, uid, gid)


def _atomic_copy(
    source: Path,
    destination: Path,
    *,
    mode: int,
    uid: int | None,
    gid: int | None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.timelocker-{os.getpid()}.tmp"
    )
    try:
        with source.open("rb") as source_stream, temporary.open("xb") as target:
            shutil.copyfileobj(source_stream, target)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, mode)
        if uid is not None and gid is not None:
            os.chown(temporary, uid, gid)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _make_tree_immutable(
    root: Path,
    *,
    uid: int | None,
    gid: int | None,
) -> None:
    for path in (root, *root.rglob("*")):
        if path.is_symlink():
            continue
        mode = path.stat().st_mode & 0o777
        if path.is_dir():
            mode |= 0o555
        else:
            mode |= 0o444
        mode &= ~0o022
        os.chmod(path, mode)
        if uid is not None and gid is not None:
            os.chown(path, uid, gid)


def _write_private_text(path: Path, content: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_mode & 0o022
        ):
            raise DeploymentFailure("private deployment file is not trusted")
        os.fchmod(descriptor, 0o600)
        os.ftruncate(descriptor, 0)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


@contextmanager
def _deployment_lock(path: Path) -> TextIO:
    if fcntl is None:
        raise DeploymentFailure("protected deployment is unsupported on this platform")
    _require_trusted_directory(path.parent, expected_owner_uid=os.geteuid())
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or metadata.st_mode & 0o022
    ):
        os.close(descriptor)
        raise DeploymentFailure("deployment lock is not trusted")
    os.fchmod(descriptor, 0o600)
    stream = os.fdopen(descriptor, "w", encoding="utf-8")
    try:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise DeploymentFailure("another TimeLocker deployment is active") from error
        yield stream
    finally:
        stream.close()


def _signal_handler(signum: int, _frame: FrameType | None) -> None:
    name = signal.Signals(signum).name
    raise DeploymentInterrupted(f"deployment interrupted by {name}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="timelocker-deploy",
        description="Install, inspect, upgrade, or roll back protected TimeLocker.",
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("install", "upgrade"):
        command = commands.add_parser(operation)
        command.add_argument("wheel", type=Path)
        command.add_argument(
            "--operator-user",
            default=os.environ.get("SUDO_USER"),
            help="Account authorized to exercise the installed CLI.",
        )
    commands.add_parser("status")
    commands.add_parser("rollback")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    paths = DeploymentPaths()
    if os.name != "posix":
        print(
            json.dumps(
                {
                    "operation": arguments.operation,
                    "result_code": "platform_unsupported",
                },
                sort_keys=True,
            )
        )
        return 69
    if arguments.operation == "status":
        try:
            payload = _deployment_status(paths)
        except (OSError, RuntimeError, TypeError, ValueError):
            payload = {
                "operation": "status",
                "result_code": "status_unavailable",
                "selected_release": None,
                "previous_release": None,
            }
            print(json.dumps(payload, sort_keys=True))
            return 1
        print(json.dumps(payload, sort_keys=True))
        return 0
    if os.geteuid() != 0:
        print(
            json.dumps(
                {
                    "operation": arguments.operation,
                    "result_code": "elevation_required",
                    "next_action": "run this command with sudo",
                },
                sort_keys=True,
            )
        )
        return 77
    try:
        _prepare_protected_roots(paths)
    except (DeploymentFailure, OSError):
        return _print_failure(arguments.operation, "deployment_roots_unavailable")
    if paths.attention_file.exists():
        return _print_failure(arguments.operation, "attention_required")
    if arguments.operation == "rollback":
        return _run_rollback(paths)
    if not arguments.operator_user:
        print(
            json.dumps(
                {
                    "operation": arguments.operation,
                    "result_code": "operator_user_required",
                    "next_action": "pass --operator-user ACCOUNT",
                },
                sort_keys=True,
            )
        )
        return 2
    resolver = ImmutableReleaseResolver(
        releases_root=paths.releases_root,
        selector_path=paths.selector,
        expected_owner_uid=paths.expected_owner_uid,
    )
    try:
        state = resolver._read_selector_optional()
    except (OSError, RuntimeError, TypeError, ValueError):
        return _print_failure(arguments.operation, "selector_untrusted")
    current = state.selected if state is not None else None
    if arguments.operation == "upgrade" and current is None:
        return _print_failure(arguments.operation, "not_installed")
    prior_handlers = {
        signum: signal.signal(signum, _signal_handler)
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }
    stage = "artifact_validation"
    deployer: T011LinuxDeployer | None = None
    try:
        request = _derive_request(
            arguments.wheel.resolve(),
            expected_current=current,
            operator_user=arguments.operator_user,
            paths=paths,
        )
        with _deployment_lock(paths.lock_file):
            stage = "idempotency_check"
            disposition = _release_request_disposition(
                arguments.operation,
                current=current,
                candidate=request.release_id,
            )
            if disposition == "already_selected":
                resolver.release_manifest(request.release_id)
                result = {
                    "operation": arguments.operation,
                    "result_code": "already_selected",
                    "selected_release": request.release_id,
                    "previous_release": state.previous if state else None,
                    "artifact_sha256": request.wheel_sha256,
                    "mutation_completed": False,
                    "backup_or_retention_triggered": False,
                }
                evidence = _write_operation_evidence(paths, result)
                result["evidence_location"] = str(evidence)
                print(json.dumps(result, sort_keys=True))
                return 0
            if disposition == "already_installed":
                raise DeploymentFailure("a different release is already installed")
            _cleanup_inert_candidate(
                paths,
                request.release_id,
                selected=current,
                previous=state.previous if state else None,
            )
            _ensure_operator_membership(
                request.operator_user,
                executor=CommandExecutor(),
            )
            stage = "deployment_transaction"
            deployer = T011LinuxDeployer(request, paths=paths)
            evidence = deployer.deploy()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as error:
        attention_required = paths.attention_file.exists()
        mutation_started = deployer is not None and deployer.mutation_started
        if attention_required:
            result_code = "recovery_failed"
            next_action = "inspect deployment attention evidence before retrying"
        elif mutation_started:
            result_code = "activation_failed_recovered"
            next_action = "inspect deployment evidence and retry the verified artifact"
        elif isinstance(error, DeploymentInterrupted):
            result_code = "deployment_interrupted"
            next_action = "verify deployment status before retrying"
        else:
            result_code = "validation_failed"
            next_action = "correct the rejected input or host precondition"
        payload: dict[str, object] = {
            "operation": arguments.operation,
            "result_code": result_code,
            "failed_stage": stage,
            "mutation_completed": False,
            "recovery_completed": mutation_started and not attention_required,
            "backup_or_retention_triggered": False,
            "next_action": next_action,
        }
        if deployer is not None and deployer.evidence is not None:
            _write_private_text(
                deployer.evidence / "deployment-result.json",
                json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            )
            evidence_location = deployer.evidence
        else:
            evidence_location = _write_operation_evidence(paths, payload)
        payload["evidence_location"] = str(evidence_location)
        print(json.dumps(payload, sort_keys=True))
        return 1
    finally:
        for signum, handler in prior_handlers.items():
            signal.signal(signum, handler)
        if "request" in locals():
            shutil.rmtree(request.manifest.parent, ignore_errors=True)
    result = {
        "operation": arguments.operation,
        "result_code": "deployed",
        "selected_release": request.release_id,
        "previous_release": request.expected_current,
        "artifact_sha256": request.wheel_sha256,
        "evidence_location": str(evidence),
        "mutation_completed": True,
        "backup_or_retention_triggered": False,
    }
    _write_private_text(
        evidence / "deployment-result.json",
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def _derive_request(
    wheel: Path,
    *,
    expected_current: str | None,
    operator_user: str,
    paths: DeploymentPaths,
) -> DeploymentRequest:
    """Validate one local wheel and derive all identity-sensitive inputs."""
    _require_regular_file(wheel, "wheel")
    filename = _validated_wheel_filename(wheel)
    try:
        wheel_name, wheel_version, _build, _tags = parse_wheel_filename(filename)
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            if len(metadata_names) != 1:
                raise DeploymentFailure("wheel contains ambiguous package metadata")
            metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as error:
        raise DeploymentFailure("wheel metadata is invalid") from error
    package_name = metadata.get("Name")
    package_version = metadata.get("Version")
    if (
        not isinstance(package_name, str)
        or canonicalize_name(package_name) != "timelocker"
        or canonicalize_name(str(wheel_name)) != "timelocker"
        or package_version != str(wheel_version)
    ):
        raise DeploymentFailure("wheel filename and package metadata disagree")
    required_assets = {
        f"TimeLocker/system_control/assets/{target.source_name}"
        for target in linux_asset_targets()
    }
    missing = required_assets - names
    if missing or any(name.endswith("timelocker-status-events.socket") for name in names):
        raise DeploymentFailure("wheel protected asset set is incompatible")
    digest = _sha256(wheel)
    release_id = digest[:40]
    _require_trusted_directory(paths.evidence_root, expected_owner_uid=os.geteuid())
    input_root = paths.evidence_root / f"input-{release_id}-{os.getpid()}"
    _mkdir(
        input_root,
        mode=0o700,
        uid=os.geteuid(),
        gid=os.getegid(),
    )
    manifest = input_root / "release.json"
    _write_private_text(
        manifest,
        json.dumps(
            {
                "schema_version": 3,
                "release_id": release_id,
                "package_version": package_version,
                "control_protocol_version": PROTOCOL_VERSION,
                "entrypoint": "venv/bin/timelocker",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
    )
    return DeploymentRequest(
        release_id=release_id,
        expected_current=expected_current,
        wheel=wheel,
        wheel_sha256=digest,
        manifest=manifest,
        operator_user=operator_user,
    )


def _release_request_disposition(
    operation: str,
    *,
    current: str | None,
    candidate: str,
) -> str | None:
    """Classify a verified artifact retry before protected mutation."""
    if current == candidate:
        return "already_selected"
    if operation == "install" and current is not None:
        return "already_installed"
    return None


def _systemctl_unit_healthy(action: str, unit: str) -> bool:
    try:
        completed = subprocess.run(
            ["systemctl", action, "--quiet", unit],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _deployment_status(
    paths: DeploymentPaths,
    *,
    unit_probe: Callable[[str, str], bool] = _systemctl_unit_healthy,
) -> dict[str, object]:
    resolver = ImmutableReleaseResolver(
        releases_root=paths.releases_root,
        selector_path=paths.selector,
        expected_owner_uid=paths.expected_owner_uid,
    )
    if paths.selector.is_symlink():
        raise DeploymentFailure("selected-release document is not trusted")
    state = resolver._read_selector_optional() if paths.selector.exists() else None
    selected = state.selected if state is not None else None
    previous = state.previous if state is not None else None
    attention_required = paths.attention_file.is_file()
    service_text = ""
    try:
        service_text = paths.service_unit.read_text(encoding="utf-8")
    except OSError:
        pass
    daemonless_unit = all(
        marker in service_text
        for marker in (
            "Type=exec",
            "Sockets=timelocker-control.socket",
            "RuntimeDirectoryPreserve=yes",
        )
    ) and "status-events" not in service_text
    unit_health = {
        "control_socket_active": unit_probe(
            "is-active", "timelocker-control.socket"
        ),
        "control_socket_enabled": unit_probe(
            "is-enabled", "timelocker-control.socket"
        ),
        "backup_timer_active": unit_probe(
            "is-active", "timelocker-npbackup-migration.timer"
        ),
        "backup_timer_enabled": unit_probe(
            "is-enabled", "timelocker-npbackup-migration.timer"
        ),
        "retention_timer_active": unit_probe(
            "is-active", "timelocker-retention.timer"
        ),
        "retention_timer_enabled": unit_probe(
            "is-enabled", "timelocker-retention.timer"
        ),
    }
    return {
        "operation": "status",
        "result_code": (
            "attention_required"
            if attention_required
            else ("installed" if selected is not None else "not_installed")
        ),
        "selected_release": selected,
        "previous_release": previous,
        "one_shot_helper_ready": (
            selected is not None
            and daemonless_unit
            and unit_health["control_socket_active"]
            and unit_health["control_socket_enabled"]
        ),
        "resident_service_required": False,
        "attention_required": attention_required,
        **unit_health,
    }


def _cleanup_inert_candidate(
    paths: DeploymentPaths,
    release_id: str,
    *,
    selected: str | None,
    previous: str | None,
) -> None:
    """Remove only trusted, unselected remnants of this exact artifact."""
    if release_id in {selected, previous}:
        if release_id == previous:
            raise DeploymentFailure("candidate is retained as the rollback release")
        return
    candidates = (
        paths.releases_root / release_id,
        paths.launcher_venv.with_name(f".venv.{release_id}.staged"),
    )
    for candidate in candidates:
        if not candidate.exists():
            continue
        _require_trusted_directory(
            candidate,
            expected_owner_uid=paths.expected_owner_uid,
        )
        shutil.rmtree(candidate)


def _write_operation_evidence(
    paths: DeploymentPaths,
    payload: dict[str, object],
) -> Path:
    """Write one exact redacted operation result into protected evidence."""
    operation = str(payload.get("operation", "deployment"))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = paths.evidence_root / f"{operation}-{timestamp}-{os.getpid()}.json"
    _write_private_text(
        destination,
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
    )
    return destination


def _ensure_operator_membership(
    operator_user: str,
    *,
    executor: CommandExecutor,
) -> None:
    """Create the fixed local authorization group and enroll one operator."""
    if pwd is None or grp is None:
        raise DeploymentFailure("protected deployment is unsupported on this platform")
    try:
        account = pwd.getpwnam(operator_user)
    except KeyError as error:
        raise DeploymentFailure("operator_user does not exist") from error
    try:
        group = grp.getgrnam("timelocker-operators")
    except KeyError:
        executor.run(["groupadd", "--system", "timelocker-operators"])
        group = grp.getgrnam("timelocker-operators")
    if account.pw_gid != group.gr_gid and operator_user not in group.gr_mem:
        executor.run(
            [
                "usermod",
                "--append",
                "--groups",
                "timelocker-operators",
                operator_user,
            ]
        )


def _prepare_protected_roots(paths: DeploymentPaths) -> None:
    """Create only trusted staging roots before candidate preflight."""
    for directory, mode in (
        (paths.releases_root, 0o755),
        (paths.selector.parent, 0o755),
        (paths.launcher_venv.parent, 0o755),
        (paths.evidence_root, 0o750),
        (paths.lock_file.parent, 0o755),
    ):
        _create_directory_tree(directory, leaf_mode=mode)
        _require_trusted_directory(directory, expected_owner_uid=os.geteuid())
    cutoff = time.time() - 86_400
    for candidate in paths.evidence_root.glob("input-*"):
        if not re.fullmatch(r"input-[0-9a-f]{40}-[0-9]+", candidate.name):
            continue
        metadata = candidate.lstat()
        if (
            stat.S_ISDIR(metadata.st_mode)
            and not stat.S_ISLNK(metadata.st_mode)
            and metadata.st_uid == os.geteuid()
            and metadata.st_mtime < cutoff
        ):
            shutil.rmtree(candidate)


def _create_directory_tree(path: Path, *, leaf_mode: int) -> None:
    """Create missing path components without changing existing directories."""
    missing: list[Path] = []
    candidate = path
    while not candidate.exists():
        missing.append(candidate)
        candidate = candidate.parent
    for directory in reversed(missing):
        mode = leaf_mode if directory == path else 0o755
        directory.mkdir(mode=mode)
        directory.chmod(mode)


def _run_rollback(paths: DeploymentPaths) -> int:
    resolver = ImmutableReleaseResolver(
        releases_root=paths.releases_root,
        selector_path=paths.selector,
        expected_owner_uid=paths.expected_owner_uid,
    )
    mutated = False
    try:
        current = resolver._read_selector_optional()
        if current is None or current.previous is None:
            raise DeploymentFailure("no previous release is available")
        if resolver.release_manifest(current.previous).schema_version < 3:
            raise DeploymentFailure("previous release requires a resident service")
        with _deployment_lock(paths.lock_file):
            selected = resolver.rollback()
            mutated = True
            executor = CommandExecutor()
            executor.run(["systemctl", "restart", "timelocker-control.socket"])
            _verify_required_unit_health(executor)
    except (DeploymentFailure, OSError, RuntimeError, subprocess.SubprocessError):
        recovery_failed = False
        if mutated:
            try:
                resolver.rollback()
                executor = CommandExecutor()
                executor.run(["systemctl", "restart", "timelocker-control.socket"])
                _verify_required_unit_health(executor)
            except (OSError, RuntimeError, subprocess.SubprocessError):
                recovery_failed = True
        payload: dict[str, object] = {
            "operation": "rollback",
            "result_code": (
                "rollback_recovery_failed"
                if recovery_failed
                else "rollback_failed"
            ),
            "mutation_completed": mutated,
            "recovery_completed": mutated and not recovery_failed,
            "backup_or_retention_triggered": False,
            "message": "rollback failed safely",
        }
        evidence = _write_operation_evidence(paths, payload)
        payload["evidence_location"] = str(evidence)
        if recovery_failed:
            _write_private_text(
                paths.attention_file,
                json.dumps(
                    {
                        "schema_version": 1,
                        "reason": "rollback_recovery_failed",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
            )
        print(json.dumps(payload, sort_keys=True))
        return 1
    payload = {
        "operation": "rollback",
        "result_code": "rolled_back",
        "selected_release": selected.selected,
        "previous_release": selected.previous,
        "mutation_completed": True,
        "recovery_completed": False,
        "backup_or_retention_triggered": False,
    }
    evidence = _write_operation_evidence(paths, payload)
    payload["evidence_location"] = str(evidence)
    print(json.dumps(payload, sort_keys=True))
    return 0


def _verify_required_unit_health(executor: CommandExecutor) -> None:
    for action, units in (
        ("is-active", REQUIRED_ACTIVE_UNITS),
        ("is-enabled", REQUIRED_ENABLED_UNITS),
    ):
        for unit in units:
            executor.run(["systemctl", action, "--quiet", unit], timeout=15)


def _print_failure(operation: str, result_code: str) -> int:
    print(json.dumps({"operation": operation, "result_code": result_code}, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
