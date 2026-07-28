#!/usr/bin/env python3
"""Safely stage and activate a TimeLocker release for Spec 010 T011.

This operator-facing harness deliberately keeps candidate probes independent of
temporary Python files.  Every identity-sensitive probe runs against the staged
release before the selected-release document or systemd service unit changes.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import subprocess
import sys
from types import FrameType
from typing import TextIO


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
    "timelocker-control.service",
    "timelocker-control.socket",
    "timelocker-status-events.socket",
    "timelocker-npbackup-migration.timer",
    "timelocker-retention.timer",
)
REQUIRED_ENABLED_UNITS = (
    "timelocker-control.socket",
    "timelocker-status-events.socket",
    "timelocker-npbackup-migration.timer",
    "timelocker-retention.timer",
)

AUTHORIZED_EVENT_PROBE = """\
import json
from threading import Event
from TimeLocker.system_control.event_client import UnixSocketStatusEventClient
stop = Event()
events = UnixSocketStatusEventClient().events(stop)
event = next(events)
stop.set()
print(json.dumps({
    "kind": event.kind.value,
    "sequence": event.revision.sequence,
    "session_id": str(event.revision.session_id),
}, sort_keys=True))
"""

DENIED_EVENT_PROBE = """\
from threading import Event
from TimeLocker.system_control.event_client import (
    StatusEventAccessDenied,
    UnixSocketStatusEventClient,
)
try:
    next(UnixSocketStatusEventClient().events(Event()))
except StatusEventAccessDenied:
    print("denied")
else:
    raise SystemExit("unauthorized event subscription unexpectedly succeeded")
"""

BACKEND_IMPORT_PROBE = """\
from TimeLocker.system_control.backend_entry import main
from TimeLocker.system_control.models import (
    PROTOCOL_VERSION,
    STATUS_EVENT_PROTOCOL_VERSION,
)
assert callable(main)
print(f"{PROTOCOL_VERSION}:{STATUS_EVENT_PROTOCOL_VERSION}")
"""

PACKAGED_UNIT_PROBE = """\
from importlib.resources import files
print(files("TimeLocker.system_control.assets") / "timelocker-control.service")
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
    lock_file: Path = Path("/run/lock/timelocker-t011-deploy.lock")


@dataclass(frozen=True, slots=True)
class DeploymentRequest:
    """Validated inputs identifying the exact release artifact to deploy."""

    release_id: str
    expected_current: str
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
    ) -> None:
        self.request = request
        self.paths = paths or DeploymentPaths()
        self.executor = executor or CommandExecutor()
        self.owner_uid = owner_uid
        self.owner_gid = owner_gid
        self.release = self.paths.releases_root / request.release_id
        self.evidence: Path | None = None
        self.staged_wheel: Path | None = None
        self.staged_manifest: Path | None = None
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
        except BaseException:
            self.recover()
            raise
        self.completed = True
        assert self.evidence is not None
        return self.evidence

    def validate_request(self) -> None:
        """Reject unsafe or incoherent inputs before creating host state."""
        for field, value in (
            ("release_id", self.request.release_id),
            ("expected_current", self.request.expected_current),
        ):
            if RELEASE_ID_PATTERN.fullmatch(value) is None:
                raise DeploymentFailure(f"{field} must be a 40-character Git SHA")
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
        try:
            pwd.getpwnam(self.request.operator_user)
        except KeyError as error:
            raise DeploymentFailure("operator_user does not exist") from error
        if self.release.exists():
            raise DeploymentFailure(f"candidate release already exists: {self.release}")
        if _selected_release(self.paths.selector) != self.request.expected_current:
            raise DeploymentFailure("selected release changed before deployment")
        for unit in REQUIRED_ACTIVE_UNITS:
            self._systemctl_gate("is-active", unit)
        for unit in REQUIRED_ENABLED_UNITS:
            self._systemctl_gate("is-enabled", unit)

    def capture_baseline(self) -> None:
        """Create private evidence and immutable rollback inputs."""
        timestamp = subprocess.run(
            ["date", "-u", "+%Y%m%dT%H%M%SZ"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.evidence = (
            self.paths.evidence_root
            / f"t011-hardened-deploy-{timestamp}-{os.getpid()}"
        )
        _mkdir(self.evidence, mode=0o750, uid=self.owner_uid, gid=self.owner_gid)
        _atomic_copy(
            self.paths.selector,
            self.evidence / "selected-release.before.json",
            mode=0o600,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )
        _atomic_copy(
            self.paths.service_unit,
            self.evidence / "timelocker-control.service.before",
            mode=0o600,
            uid=self.owner_uid,
            gid=self.owner_gid,
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
            "schema_version": 2,
            "release_id": self.request.release_id,
            "control_protocol_version": 2,
            "event_protocol_version": 1,
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
        expected_protocol_output = (
            f"{manifest['control_protocol_version']}:"
            f"{manifest['event_protocol_version']}"
        )
        if protocol_output != expected_protocol_output:
            raise DeploymentFailure(
                "staged backend protocol probe failed: "
                f"expected {expected_protocol_output}, got {protocol_output or '<empty>'}"
            )
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
        self.executor.run(
            [
                "timeout",
                "10",
                "runuser",
                "-u",
                self.request.operator_user,
                "--",
                python,
                "-c",
                AUTHORIZED_EVENT_PROBE,
            ],
            timeout=15,
            output=self.evidence / "preflight-authorized-event.json",
        )
        denied = self.executor.run(
            [
                "timeout",
                "10",
                "setpriv",
                "--reuid=65534",
                "--regid=65534",
                "--clear-groups",
                python,
                "-c",
                DENIED_EVENT_PROBE,
            ],
            timeout=15,
            capture=True,
        ).strip()
        if denied != "denied":
            raise DeploymentFailure("staged denied-identity probe did not deny access")
        _write_private_text(self.evidence / "preflight-denied-event.txt", denied + "\n")

        if _selected_release(self.paths.selector) != self.request.expected_current:
            raise DeploymentFailure("selector changed during staged preflight")
        for unit in REQUIRED_ACTIVE_UNITS:
            self._systemctl_gate("is-active", unit)
        for unit in REQUIRED_ENABLED_UNITS:
            self._systemctl_gate("is-enabled", unit)

    def activate(self) -> None:
        """Perform the bounded protected mutation after all preflights pass."""
        assert self.evidence is not None
        if _selected_release(self.paths.selector) != self.request.expected_current:
            raise DeploymentFailure("selector changed immediately before activation")
        python = self.release / "venv/bin/python"
        packaged_unit = Path(
            self.executor.run(
                [python, "-c", PACKAGED_UNIT_PROBE],
                capture=True,
            ).strip()
        )
        self.mutation_started = True
        _atomic_copy(
            packaged_unit,
            self.paths.service_unit,
            mode=0o644,
            uid=self.owner_uid,
            gid=self.owner_gid,
        )
        self.executor.run(["systemctl", "daemon-reload"])
        self.executor.run(
            [
                python,
                "-m",
                "TimeLocker.system_control.release_admin",
                "select",
                self.request.release_id,
                "--expected-current",
                self.request.expected_current,
            ],
            output=self.evidence / "selected-release.txt",
        )
        self.executor.run(["systemctl", "restart", "timelocker-control.service"])

    def verify_activation(self) -> None:
        """Verify the selected release without running backup or retention."""
        assert self.evidence is not None
        if _selected_release(self.paths.selector) != self.request.release_id:
            raise DeploymentFailure("candidate release was not selected")
        for unit in REQUIRED_ACTIVE_UNITS:
            self._systemctl_gate("is-active", unit)
        for unit in REQUIRED_ENABLED_UNITS:
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
        activated_event = self.executor.run(
            [
                "timeout",
                "10",
                "runuser",
                "-u",
                self.request.operator_user,
                "--",
                self.release / "venv/bin/python",
                "-c",
                AUTHORIZED_EVENT_PROBE,
            ],
            timeout=15,
            capture=True,
        )
        try:
            activated_payload = json.loads(activated_event)
        except json.JSONDecodeError as error:
            raise DeploymentFailure(
                "activated event probe returned invalid JSON"
            ) from error
        if not isinstance(activated_payload, dict):
            raise DeploymentFailure("activated event probe returned invalid JSON")
        _write_private_text(
            self.evidence / "activated-authorized-event.json",
            activated_event,
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
                (
                    self.evidence / "timelocker-control.service.before",
                    self.paths.service_unit,
                    0o644,
                ),
            ):
                try:
                    _atomic_copy(
                        source,
                        destination,
                        mode=mode,
                        uid=self.owner_uid,
                        gid=self.owner_gid,
                    )
                except OSError as error:
                    errors.append(f"restore {destination}: {error}")
            for command in (
                ("systemctl", "daemon-reload"),
                ("systemctl", "restart", "timelocker-control.socket"),
                ("systemctl", "restart", "timelocker-status-events.socket"),
                ("systemctl", "restart", "timelocker-control.service"),
            ):
                try:
                    self.executor.run(command, check=False)
                except (DeploymentFailure, OSError) as error:
                    errors.append(f"{' '.join(command)}: {error}")
            try:
                if (
                    _selected_release(self.paths.selector)
                    != self.request.expected_current
                ):
                    errors.append("restored selector does not name prior release")
            except DeploymentFailure as error:
                errors.append(f"validate restored selector: {error}")
            for action, units in (
                ("is-active", REQUIRED_ACTIVE_UNITS),
                ("is-enabled", REQUIRED_ENABLED_UNITS),
            ):
                for unit in units:
                    try:
                        self._systemctl_gate(action, unit)
                    except DeploymentFailure as error:
                        errors.append(f"{action} {unit}: {error}")
        if self.release.exists():
            try:
                shutil.rmtree(self.release)
            except OSError as error:
                errors.append(f"remove candidate release: {error}")
        if errors:
            raise DeploymentFailure(
                "deployment failed and rollback was incomplete: " + "; ".join(errors)
            )

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
            "Wants=timelocker-status-events.socket",
            "Sockets=timelocker-control.socket timelocker-status-events.socket",
        }
        lines = set(text.splitlines())
        missing = required_lines - lines
        if missing:
            raise DeploymentFailure(
                "packaged service unit is missing: " + ", ".join(sorted(missing))
            )
        if (
            "Requires=timelocker-control.socket timelocker-status-events.socket"
            in lines
        ):
            raise DeploymentFailure("packaged service still hard-requires event socket")

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
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    os.chmod(path, 0o600)


@contextmanager
def _deployment_lock(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("w", encoding="utf-8")
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
        description="Stage and activate a T011 TimeLocker Linux release safely."
    )
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--expected-current", required=True)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--operator-user", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if os.geteuid() != 0:
        print("T011 deployment must be run with sudo.", file=sys.stderr)
        return 77
    request = DeploymentRequest(
        release_id=arguments.release_id,
        expected_current=arguments.expected_current,
        wheel=arguments.wheel.resolve(),
        wheel_sha256=arguments.wheel_sha256,
        manifest=arguments.manifest.resolve(),
        operator_user=arguments.operator_user,
    )
    paths = DeploymentPaths()
    prior_handlers = {
        signum: signal.signal(signum, _signal_handler)
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }
    try:
        with _deployment_lock(paths.lock_file):
            evidence = T011LinuxDeployer(request, paths=paths).deploy()
    except (DeploymentFailure, OSError, subprocess.SubprocessError) as error:
        print(f"T011 deployment failed: {error}", file=sys.stderr)
        return 1
    finally:
        for signum, handler in prior_handlers.items():
            signal.signal(signum, handler)
    print(f"release={request.release_id}")
    print(f"evidence_root={evidence}")
    print("preflight_identity_checks=passed")
    print("backup_or_retention_triggered=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
