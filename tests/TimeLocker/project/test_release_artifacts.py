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


def load_script(name: str):
    path = ROOT / f"scripts/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
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


@pytest.mark.config
@pytest.mark.unit
def test_artifact_smoke_covers_system_entrypoints_protocols_and_assets():
    smoke = (ROOT / "scripts/smoke_release_artifact.py").read_text()
    for expected in (
        "timelocker-system-control",
        "timelocker-deploy",
        "timelocker-tray",
        '"schema_version": 3',
        "timelocker-retention.timer",
        "timelocker-icon-connecting.png",
        "timelocker-icon-idle.png",
        "timelocker-icon-error.png",
    ):
        assert expected in smoke
    assert 'assert not assets.joinpath("timelocker-status-events.socket").is_file()' in smoke


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


@pytest.mark.config
@pytest.mark.unit
def test_release_intent_accepts_current_version_and_rejects_mismatch():
    validator = load_script("validate_release_intent")
    assert validator.validate(ROOT, "v0.9.1") == "0.9.1"
    with pytest.raises(AssertionError, match="version guard failed"):
        validator.validate(ROOT, "v0.9.0")
    with pytest.raises(AssertionError, match="semantic version tag"):
        validator.validate(ROOT, "0.9.1")


@pytest.mark.config
@pytest.mark.unit
def test_release_notes_are_derived_from_exact_changelog_section():
    extractor = load_script("extract_release_notes")
    changelog = "# Changelog\n\n## [0.9.1] - Prepared\n\nCurrent notes.\n\n## [0.9.0]\n\nOld notes.\n"
    assert extractor.extract(changelog, "0.9.1") == "Current notes.\n"
    with pytest.raises(AssertionError, match="no section"):
        extractor.extract(changelog, "1.0.0")


@pytest.mark.config
@pytest.mark.unit
def test_release_workflows_enforce_read_only_rehearsal_and_isolated_publication(tmp_path):
    validator = load_script("validate_release_workflows")
    rehearsal = ROOT / ".github/workflows/release-validation.yml"
    release = ROOT / ".github/workflows/release.yml"
    validator.validate(rehearsal, release)

    unsafe_rehearsal = tmp_path / "release-validation.yml"
    unsafe_rehearsal.write_text(rehearsal.read_text().replace("contents: read", "contents: write"))
    with pytest.raises(AssertionError, match="read-only"):
        validator.validate(unsafe_rehearsal, release)


@pytest.mark.config
@pytest.mark.unit
def test_release_rehearsal_propagates_missing_prerequisite_failure(tmp_path):
    missing = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/smoke_release_artifact.py"),
            str(tmp_path / "missing.whl"),
            "--expected-version",
            "0.9.1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert missing.returncode != 0
    assert "Artifact does not exist" in missing.stderr
