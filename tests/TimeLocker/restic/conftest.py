import json
import subprocess
from functools import lru_cache

import pytest
from packaging import version

MIN_RESTIC_VERSION = version.parse("0.18.0")


@lru_cache(maxsize=1)
def _detect_restic_version() -> str | None:
    """Return the installed restic version or None if detection fails."""
    commands = [
            ["restic", "--json", "version"],
            ["restic", "version"],
    ]
    for cmd in commands:
        try:
            completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
            output = completed.stdout.strip()
            if "--json" in cmd:
                data = json.loads(output)
                return data.get("version")
            if output.startswith("restic "):
                parts = output.split()
                if len(parts) >= 2:
                    return parts[1]
        except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
            continue
    return None


@pytest.fixture(scope="session", autouse=True)
def _ensure_supported_restic():
    """Skip restic-dependent suites when the binary is missing or too old."""
    restic_version = _detect_restic_version()
    if restic_version is None:
        pytest.skip("restic binary not available in PATH; skipping restic-dependent tests.")
    if version.parse(restic_version) < MIN_RESTIC_VERSION:
        pytest.skip(
                f"restic {restic_version} detected, but tests require >= {MIN_RESTIC_VERSION}. "
                "Upgrade restic to run this suite."
        )
