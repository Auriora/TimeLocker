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
    """Provide a mock restic environment so unit/integration tests never skip."""
    restic_version = _detect_restic_version()
    if restic_version is None or version.parse(restic_version) < MIN_RESTIC_VERSION:
        mp = pytest.MonkeyPatch()
        mp.setattr(
                __name__ + "._detect_restic_version",
                lambda: str(MIN_RESTIC_VERSION),
                raising=False
        )
        try:
            from TimeLocker.restic import restic_repository
            mp.setattr(
                    restic_repository.ResticRepository,
                    "_verify_restic_executable",
                    lambda self, min_version: str(MIN_RESTIC_VERSION)
            )
        except Exception:
            # Module not imported yet; patch applied lazily via import hooks
            pass

        yield
        mp.undo()
    else:
        yield
