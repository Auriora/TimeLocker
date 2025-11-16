"""
Shared CLI test fixtures.

Provides an isolated CLI environment so tests can run without touching user data.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pytest


@pytest.fixture()
def isolated_cli_environment(tmp_path: Path) -> Dict[str, object]:
    """
    Provision isolated HOME/config/data directories so commands do not touch user files.
    """
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "xdg-data"
    template_dir = data_dir / "timelocker" / "templates"
    home_dir = tmp_path / "home"
    repo_dir = tmp_path / "repository"
    source_dir = tmp_path / "source" / "documents"
    restore_dir = tmp_path / "restore-target"

    for directory in (config_dir, template_dir, home_dir, repo_dir, source_dir, restore_dir):
        directory.mkdir(parents=True, exist_ok=True)

    (source_dir / "notes.txt").write_text("sample document")
    env = os.environ.copy()
    env.update({
            "HOME":                str(home_dir),
            "TIMELOCKER_TEST_MODE": "1",
            "TIMELOCKER_CONFIG_DIR": str(config_dir),
            "XDG_CONFIG_HOME":      str(config_dir),
            "XDG_DATA_HOME":        str(data_dir),
            "COLUMNS":              "200",
    })

    return {
            "env":        env,
            "config_dir": config_dir,
            "repo_uri":   repo_dir.resolve().as_uri(),
            "source_dir": source_dir,
            "restore_dir": restore_dir,
    }
