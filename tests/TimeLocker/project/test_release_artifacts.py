"""Contracts for non-publishing release artifact validation."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from TimeLocker.cli import app

ROOT = Path(__file__).parents[3]


def load_validator():
    path = ROOT / "scripts/validate_release_artifacts.py"
    spec = importlib.util.spec_from_file_location("validate_release_artifacts", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.config
@pytest.mark.unit
def test_supported_python_and_os_metadata_are_explicit():
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    assert project["requires-python"] == ">=3.12,<3.14"
    assert "Operating System :: OS Independent" not in project["classifiers"]
    for classifier in (
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ):
        assert classifier in project["classifiers"]


@pytest.mark.config
@pytest.mark.unit
def test_version_guard_rejects_a_mismatch(tmp_path):
    validator = load_validator()
    with pytest.raises(AssertionError, match="version guard failed"):
        validator.validate(ROOT, tmp_path, "0.9.0")


@pytest.mark.config
@pytest.mark.unit
def test_smoke_workflow_is_non_publishing_read_only_and_covers_support_matrix():
    workflow = (ROOT / ".github/workflows/artifact-smoke.yml").read_text()
    assert "pull_request:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "contents: read" in workflow
    assert "ubuntu-latest, macos-latest, windows-latest" in workflow
    assert 'python-version: ["3.12", "3.13"]' in workflow
    assert "artifact: [wheel, sdist]" in workflow
    for forbidden in ("gh release", "git tag", "twine upload"):
        assert forbidden not in workflow


@pytest.mark.platform
@pytest.mark.unit
def test_root_help_is_compatible_with_windows_default_encoding():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    result.output.encode("cp1252")


@pytest.mark.config
@pytest.mark.unit
def test_validator_cli_rejects_a_version_mismatch_before_artifact_checks(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_release_artifacts.py"),
            "--expected-version",
            "0.9.0",
            "--dist",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "version guard failed" in result.stderr
