#!/usr/bin/env python3
"""Install one built artifact and smoke its public and system entry points."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def executable(environment: Path, name: str) -> Path:
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return scripts / f"{name}{suffix}"


def run(command: list[str], *, expected: str | None = None) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} exited {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if expected is not None and result.stdout.strip() != expected:
        raise RuntimeError(
            f"{' '.join(command)} returned {result.stdout.strip()!r}, "
            f"expected {expected!r}"
        )


def smoke_system_contract(python: Path, expected_version: str) -> None:
    """Verify installed protocols and protected deployment assets."""
    contract = """
import sys
from importlib.resources import files
from TimeLocker.system_control.models import (
    PROTOCOL_VERSION,
    STATUS_EVENT_PROTOCOL_VERSION,
)
from TimeLocker.system_control.release_launcher import ReleaseManifest

assets = files("TimeLocker.system_control").joinpath("assets")
for name in (
    "timelocker-control.service",
    "timelocker-control.socket",
    "timelocker-status-events.socket",
    "timelocker-retention.service",
    "timelocker-retention.timer",
    "timelocker-icon-connecting.png",
    "timelocker-icon-idle.png",
    "timelocker-icon-running.png",
    "timelocker-icon-success.png",
    "timelocker-icon-warning.png",
    "timelocker-icon-error.png",
):
    assert assets.joinpath(name).is_file(), name
manifest = ReleaseManifest.from_mapping(
    {
        "schema_version": 2,
        "release_id": "a" * 40,
        "package_version": sys.argv[1],
        "control_protocol_version": PROTOCOL_VERSION,
        "event_protocol_version": STATUS_EVENT_PROTOCOL_VERSION,
        "entrypoint": "venv/bin/timelocker",
    }
)
assert manifest.control_protocol_version == PROTOCOL_VERSION
assert manifest.event_protocol_version == STATUS_EVENT_PROTOCOL_VERSION
"""
    run([str(python), "-c", contract, expected_version])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    if not artifact.is_file():
        raise SystemExit(f"Artifact does not exist: {artifact}")

    with tempfile.TemporaryDirectory(prefix="timelocker-artifact-") as temporary:
        environment = Path(temporary) / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = executable(environment, "python")
        run([str(python), "-m", "pip", "install", "--disable-pip-version-check", str(artifact)])
        for command_name in ("timelocker", "tl"):
            command = executable(environment, command_name)
            run([str(command), "version", "--short"], expected=args.expected_version)
            run([str(command), "--help"])
        for command_name in ("timelocker-system-control", "timelocker-tray"):
            run([str(executable(environment, command_name)), "--help"])
        smoke_system_contract(python, args.expected_version)
    print(f"Smoke contract passed for {artifact.name} on Python {sys.version.split()[0]}")


if __name__ == "__main__":
    main()
