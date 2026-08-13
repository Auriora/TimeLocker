"""
Global pytest fixtures and configuration helpers.

This module loads environment settings from `.env` / `.env.test` prior to test
collection so integration suites can rely on the same configuration a developer
uses locally. Values already present in ``os.environ`` take precedence, allowing
CI pipelines to inject secrets without modifying the files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

# Ensure global fixtures and environment isolation helpers are loaded
pytest_plugins = [
    "tests.TimeLocker.test_fixtures",
]


def _parse_env_value(raw: str) -> str:
    """Strip optional wrapping quotes from an environment value."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        return raw[1:-1]
    return raw


def _load_env_file(path: Path, *, override: bool = False) -> None:
    """Load KEY=VALUE pairs from a dotenv-style file into os.environ."""
    if not path.is_file():
        return

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if "=" not in stripped:
            continue

        key_part, value_part = stripped.split("=", 1)
        key = key_part.strip().removeprefix("export ").strip()
        if not key:
            continue

        if not override and key in os.environ:
            continue

        os.environ[key] = _parse_env_value(value_part)


def _load_project_env(project_root: Path) -> None:
    """Load project test files while preserving explicit process values."""
    env_files: Iterable[Path] = (
        project_root / ".env",
        project_root / ".env.test",
    )
    for env_path in env_files:
        _load_env_file(env_path, override=False)


def pytest_configure() -> None:  # noqa: D401 - hook invoked by pytest
    """Load environment configuration before tests start."""
    _load_project_env(Path(__file__).resolve().parents[1])
