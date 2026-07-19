#!/usr/bin/env python3
"""Install one built artifact in a fresh environment and smoke both CLIs."""

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
        raise RuntimeError(f"{' '.join(command)} returned {result.stdout.strip()!r}, expected {expected!r}")


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
    print(f"Smoke contract passed for {artifact.name} on Python {sys.version.split()[0]}")


if __name__ == "__main__":
    main()
