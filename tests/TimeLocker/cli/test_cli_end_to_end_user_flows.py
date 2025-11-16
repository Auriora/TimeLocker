"""
End-to-end CLI workflow tests covering repository setup, selection creation, and backups.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List
from unittest.mock import patch

import pytest

from src.TimeLocker.cli import app
from TimeLocker.interfaces.data_models import BackupResult, BackupStatus
from tests.TimeLocker.cli.test_utils import get_cli_runner, combined_output

runner = get_cli_runner()


class StubBackupOrchestrator:
    """Minimal orchestrator that records job configs and returns successful results."""

    def __init__(self) -> None:
        self.job_configs: List[object] = []

    def execute_backup_job(self, job_config):
        self.job_configs.append(job_config)
        return BackupResult(
                status=BackupStatus.COMPLETED,
                repository_name=job_config.repository_id,
                target_names=[job_config.data_selection_id],
                snapshot_id="stub-snapshot-001",
                files_processed=128,
                bytes_processed=1024 * 1024,
                start_time=0,
                end_time=2,
                warnings=[]
        )


class StubServiceManager:
    """Service manager stub exposing only the orchestrator attribute used by the CLI."""

    def __init__(self, orchestrator: StubBackupOrchestrator) -> None:
        self._backup_orchestrator = orchestrator


@contextmanager
def stubbed_backup_services() -> Iterator[StubBackupOrchestrator]:
    """
    Patch backup command dependencies with lightweight stubs.

    Yields:
        StubBackupOrchestrator used during the patched window.
    """
    orchestrator = StubBackupOrchestrator()
    stub_manager = StubServiceManager(orchestrator)
    with (
            patch("src.TimeLocker.cli_modules.commands.backup._get_service_manager_for_command",
                  return_value=stub_manager),
            patch("src.TimeLocker.cli_modules.commands.backup.get_cli_service_manager",
                  return_value=stub_manager),
    ):
        yield orchestrator


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

    for directory in (config_dir, template_dir, home_dir, repo_dir, source_dir):
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
    }


def _add_repository(repo_name: str, config_dir: Path, repo_uri: str, env: Dict[str, str], *, set_default: bool = False):
    """Helper to add repositories via CLI and assert success."""
    args = [
            "repos", "add", repo_name, repo_uri,
            "--description", "End-to-end test repository",
            "--config-dir", str(config_dir),
    ]
    if set_default:
        args.append("--set-default")

    result = runner.invoke(app, args, env=env)
    assert result.exit_code == 0, combined_output(result)


def _create_selection(selection_name: str, include_path: Path, env: Dict[str, str]):
    """Create a reusable selection template rooted at include_path."""
    result = runner.invoke(
            app,
            [
                    "selections", "create", selection_name,
                    "--include-path", str(include_path),
                    "--description", "Integration selection",
                    "--tag", "e2e",
            ],
            env=env,
    )
    assert result.exit_code == 0, combined_output(result)


class TestCLIEndToEndWorkflows:
    """Exercise CLI flows that mimic real user interactions."""

    @pytest.mark.integration
    def test_selection_driven_backup_flow(self, isolated_cli_environment):
        """End-to-end flow: add repo -> create selection -> run selection-based backup."""
        env = isolated_cli_environment["env"]
        config_dir = isolated_cli_environment["config_dir"]
        repo_name = "docs-repo"
        selection_name = "documents-e2e"

        _add_repository(repo_name, config_dir, isolated_cli_environment["repo_uri"], env)
        _create_selection(selection_name, isolated_cli_environment["source_dir"], env)

        with stubbed_backup_services() as orchestrator:
            result = runner.invoke(
                    app,
                    [
                            "backup", "create",
                            "--selection", selection_name,
                            "--repository", repo_name,
                            "--dry-run",
                            "--config-dir", str(config_dir),
                    ],
                    env=env,
            )

        assert result.exit_code == 0, combined_output(result)
        output = combined_output(result)
        assert "Backup Completed" in output
        assert orchestrator.job_configs, "backup orchestrator was not invoked"
        job_config = orchestrator.job_configs[-1]
        assert job_config.data_selection_id == selection_name
        assert job_config.repository_id == repo_name
        assert job_config.metadata.get("cli_invoked") is True

    @pytest.mark.integration
    def test_selection_backup_uses_default_repository(self, isolated_cli_environment):
        """Verify backup create falls back to default repository when none is supplied."""
        env = isolated_cli_environment["env"]
        config_dir = isolated_cli_environment["config_dir"]
        repo_name = "primary-default"
        selection_name = "photos-e2e"

        _add_repository(repo_name, config_dir, isolated_cli_environment["repo_uri"], env, set_default=True)
        _create_selection(selection_name, isolated_cli_environment["source_dir"], env)

        with stubbed_backup_services() as orchestrator:
            result = runner.invoke(
                    app,
                    [
                            "backup", "create",
                            "--selection", selection_name,
                            "--dry-run",
                            "--config-dir", str(config_dir),
                    ],
                    env=env,
            )

        assert result.exit_code == 0, combined_output(result)
        assert orchestrator.job_configs, "backup orchestrator was not invoked"
        job_config = orchestrator.job_configs[-1]
        assert job_config.repository_id == repo_name
        assert job_config.data_selection_id == selection_name
