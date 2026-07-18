"""
End-to-end CLI workflow tests covering repository setup, selection creation, and backups.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Iterator, List, Optional
from unittest.mock import patch

import pytest

from TimeLocker.cli import app
from TimeLocker.interfaces.data_models import BackupResult, BackupStatus
from TimeLocker.selection_manager import SelectionManager
from TimeLocker.selection_template_manager import SelectionTemplateManager
from TimeLocker.cli_modules.helpers.backup_cli_handler import BackupCLIHandler
from tests.TimeLocker.cli.test_utils import (
        get_cli_runner,
        combined_output,
        patch_restore_commands,
        maybe_show_cli_output,
)

runner = get_cli_runner()
SNAPSHOT_ID = "stub-snapshot-001"


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
                snapshot_id=SNAPSHOT_ID,
                files_processed=128,
                bytes_processed=1024 * 1024,
                start_time=0,
                end_time=2,
                warnings=[]
        )


class StubServiceManager:
    """Service manager stub that proxies selection operations to the real handler."""
    
    def __init__(self, orchestrator: StubBackupOrchestrator) -> None:
        self._backup_orchestrator = orchestrator
    
    @staticmethod
    def _run(coro):
        return asyncio.run(coro)
    
    def _create_handler(self) -> BackupCLIHandler:
        return BackupCLIHandler(
            selection_manager=SelectionManager(),
            backup_orchestrator=self._backup_orchestrator
        )
    
    def selection_template_exists(self, selection_name: str) -> bool:
        handler = self._create_handler()
        async def _check():
            return await handler.validate_selection_exists(selection_name)
        return self._run(_check())
    
    def get_selection_summary(self, selection_name: str) -> str:
        handler = self._create_handler()
        async def _summary():
            return await handler.get_selection_summary(selection_name)
        return self._run(_summary())
    
    def suggest_selection_creation(self, selection_name: str) -> str:
        handler = self._create_handler()
        return handler.suggest_template_creation(selection_name)
    
    def run_selection_backup(
        self,
        selection_name: str,
        repository: str,
        tags=None,
        dry_run: bool = False,
        execution_mode=None,
        cli_options=None
    ):
        handler = self._create_handler()
        async def _execute():
            return await handler.execute_backup_with_selection(
                selection_name=selection_name,
                repository=repository,
                tags=tags,
                dry_run=dry_run,
                execution_mode=execution_mode,
                **(cli_options or {})
            )
        return self._run(_execute())


@contextmanager
def stubbed_backup_services() -> Iterator[StubBackupOrchestrator]:
    """
    Patch backup command dependencies with lightweight stubs.

    Yields:
        StubBackupOrchestrator used during the patched window.
    """
    orchestrator = StubBackupOrchestrator()
    stub_manager = StubServiceManager(orchestrator)
    with patch("TimeLocker.cli_modules.commands.backup._get_service_manager_for_command",
               return_value=stub_manager):
        yield orchestrator


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
    maybe_show_cli_output(result, label=f"tl repos add {repo_name}")


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
    maybe_show_cli_output(result, label=f"tl selections create {selection_name}")


def _execute_selection_backup(env_bundle: Dict[str, object], selection_name: str, repository: Optional[str]) -> tuple[StubBackupOrchestrator, object]:
    """
    Run tl backup create with optional repository override using the stub orchestrator.
    """
    env = env_bundle["env"]
    config_dir = env_bundle["config_dir"]
    args = [
            "backup", "create",
            "--selection", selection_name,
            "--dry-run",
            "--config-dir", str(config_dir),
    ]
    if repository:
        args.extend(["--repository", repository])

    with stubbed_backup_services() as orchestrator:
        result = runner.invoke(app, args, env=env)

    assert result.exit_code == 0, combined_output(result)
    maybe_show_cli_output(result, label=f"tl backup create (selection={selection_name})")
    return orchestrator, result


@contextmanager
def configured_restore_patches(source_dir: Path) -> Iterator[dict]:
    """
    Configure restore command patches with realistic snapshot metadata for CLI flows.
    """
    with patch_restore_commands() as patched:
        now = datetime.now()
        snapshot_entry = SimpleNamespace(
                id=SNAPSHOT_ID,
                time=now,
                hostname="timelocker-e2e",
                username="cli-user",
                tags=["e2e", "documents"],
                paths=[str(source_dir)],
        )
        patched["snapshot_manager"].list_snapshots.return_value = [snapshot_entry]

        listing_entry = SimpleNamespace(
                name="notes.txt",
                path="/documents/notes.txt",
                type=SimpleNamespace(value="file"),
                size=1024,
                modification_time=now,
                permissions="rw-r--r--",
        )
        patched["snapshot_browser"].list_snapshot_contents.return_value = SimpleNamespace(
                entries=[listing_entry],
                total_entries=1,
                path="/documents",
        )
        yield patched


class TestCLIEndToEndWorkflows:
    """Exercise CLI flows that mimic real user interactions."""
    pytestmark = [pytest.mark.integration, pytest.mark.e2e]

    @pytest.mark.backup
    def test_selection_driven_backup_flow(self, isolated_cli_environment):
        """End-to-end flow: add repo -> create selection -> run selection-based backup."""
        env = isolated_cli_environment["env"]
        config_dir = isolated_cli_environment["config_dir"]
        repo_name = "docs-repo"
        selection_name = "documents-e2e"

        _add_repository(repo_name, config_dir, isolated_cli_environment["repo_uri"], env)
        _create_selection(selection_name, isolated_cli_environment["source_dir"], env)

        orchestrator, result = _execute_selection_backup(isolated_cli_environment, selection_name, repo_name)

        assert result.exit_code == 0, combined_output(result)
        output = combined_output(result)
        assert "Backup Completed" in output
        assert orchestrator.job_configs, "backup orchestrator was not invoked"
        job_config = orchestrator.job_configs[-1]
        template_storage = Path(isolated_cli_environment["env"]["XDG_DATA_HOME"]) / "timelocker" / "templates"
        template_manager = SelectionTemplateManager(storage_dir=template_storage)
        template = template_manager.get_template(selection_name, by_name=True)
        assert job_config.data_selection_id == template.id
        assert job_config.repository_id == repo_name
        assert job_config.metadata.get("cli_invoked") is True

    @pytest.mark.backup
    def test_selection_backup_uses_default_repository(self, isolated_cli_environment):
        """Verify backup create falls back to default repository when none is supplied."""
        env = isolated_cli_environment["env"]
        config_dir = isolated_cli_environment["config_dir"]
        repo_name = "primary-default"
        selection_name = "photos-e2e"

        _add_repository(repo_name, config_dir, isolated_cli_environment["repo_uri"], env, set_default=True)
        _create_selection(selection_name, isolated_cli_environment["source_dir"], env)

        orchestrator, result = _execute_selection_backup(isolated_cli_environment, selection_name, repository=None)

        assert result.exit_code == 0, combined_output(result)
        assert orchestrator.job_configs, "backup orchestrator was not invoked"
        job_config = orchestrator.job_configs[-1]
        assert job_config.repository_id == repo_name
        template_storage = Path(isolated_cli_environment["env"]["XDG_DATA_HOME"]) / "timelocker" / "templates"
        template_manager = SelectionTemplateManager(storage_dir=template_storage)
        template = template_manager.get_template(selection_name, by_name=True)
        assert job_config.data_selection_id == template.id

    @pytest.mark.backup
    @pytest.mark.restore
    def test_backup_to_restore_listing_flow(self, isolated_cli_environment):
        """
        Validate a user journey that runs a selection backup then inspects snapshots via restore commands.
        """
        env = isolated_cli_environment["env"]
        config_dir = isolated_cli_environment["config_dir"]
        repo_name = "history-repo"
        selection_name = "history-documents"

        _add_repository(repo_name, config_dir, isolated_cli_environment["repo_uri"], env, set_default=True)
        _create_selection(selection_name, isolated_cli_environment["source_dir"], env)
        _execute_selection_backup(isolated_cli_environment, selection_name, repo_name)

        with configured_restore_patches(isolated_cli_environment["source_dir"]) as patched_restore:
            list_result = runner.invoke(
                    app,
                    [
                            "restore", "list", repo_name,
                            "--limit", "5",
                            "--config-dir", str(config_dir),
                    ],
                    env=env,
            )
            list_output = combined_output(list_result)
            assert list_result.exit_code == 0, list_output
            assert SNAPSHOT_ID[:12] in list_output
            maybe_show_cli_output(list_result, label="tl restore list")

            browse_result = runner.invoke(
                    app,
                    [
                            "restore", "browse", repo_name, SNAPSHOT_ID,
                            "--path", "/documents",
                            "--config-dir", str(config_dir),
                    ],
                    env=env,
            )
            browse_output = combined_output(browse_result)
            assert browse_result.exit_code == 0, browse_output
            assert "notes.txt" in browse_output
            patched_restore["snapshot_browser"].list_snapshot_contents.assert_called_with(SNAPSHOT_ID, "/documents")
            maybe_show_cli_output(browse_result, label="tl restore browse")

    @pytest.mark.backup
    @pytest.mark.restore
    def test_restore_files_flow(self, isolated_cli_environment):
        """End-to-end flow: run selection backup then restore a file to a target directory."""
        env = isolated_cli_environment["env"]
        config_dir = isolated_cli_environment["config_dir"]
        repo_name = "restore-repo"
        selection_name = "restore-selection"
        target_dir = isolated_cli_environment["restore_dir"]

        _add_repository(repo_name, config_dir, isolated_cli_environment["repo_uri"], env, set_default=True)
        _create_selection(selection_name, isolated_cli_environment["source_dir"], env)
        _execute_selection_backup(isolated_cli_environment, selection_name, repo_name)

        with configured_restore_patches(isolated_cli_environment["source_dir"]) as patched_restore:
            files_result = runner.invoke(
                    app,
                    [
                            "restore", "files", repo_name, SNAPSHOT_ID,
                            "/documents/notes.txt",
                            "--target", str(target_dir),
                            "--selection", selection_name,
                            "--config-dir", str(config_dir),
                    ],
                    env=env,
            )
            files_output = combined_output(files_result)
            assert files_result.exit_code == 0, files_output
            assert "Files Restored" in files_output
            maybe_show_cli_output(files_result, label="tl restore files")

            recovery_call = patched_restore["recovery_orchestrator"].initiate_selective_recovery.call_args
            assert recovery_call is not None
            assert recovery_call.kwargs["snapshot_id"] == SNAPSHOT_ID
            assert recovery_call.kwargs["target_path"] == str(target_dir)

    @pytest.mark.backup
    @pytest.mark.restore
    def test_restore_diff_flow(self, isolated_cli_environment):
        """End-to-end flow: compare snapshots after performing a backup."""
        env = isolated_cli_environment["env"]
        config_dir = isolated_cli_environment["config_dir"]
        repo_name = "diff-repo"
        selection_name = "diff-selection"

        _add_repository(repo_name, config_dir, isolated_cli_environment["repo_uri"], env, set_default=True)
        _create_selection(selection_name, isolated_cli_environment["source_dir"], env)
        _execute_selection_backup(isolated_cli_environment, selection_name, repo_name)

        with configured_restore_patches(isolated_cli_environment["source_dir"]):
            diff_result = runner.invoke(
                    app,
                    [
                            "restore", "diff",
                            repo_name,
                            SNAPSHOT_ID,
                            "previous-snapshot-id",
                            "--path", "/documents",
                            "--config-dir", str(config_dir),
                    ],
                    env=env,
            )
            diff_output = combined_output(diff_result)
            assert diff_result.exit_code == 0, diff_output
            assert "Comparison" in diff_output
            maybe_show_cli_output(diff_result, label="tl restore diff")

    @pytest.mark.restore
    def test_restore_verify_flow(self, isolated_cli_environment):
        """End-to-end flow: backup then run restore verify against snapshot."""
        env = isolated_cli_environment["env"]
        config_dir = isolated_cli_environment["config_dir"]
        repo_name = "verify-repo"
        selection_name = "verify-selection"
        target_dir = isolated_cli_environment["restore_dir"]

        _add_repository(repo_name, config_dir, isolated_cli_environment["repo_uri"], env, set_default=True)
        _create_selection(selection_name, isolated_cli_environment["source_dir"], env)
        _execute_selection_backup(isolated_cli_environment, selection_name, repo_name)

        with configured_restore_patches(isolated_cli_environment["source_dir"]) as patched_restore:
            verify_result = runner.invoke(
                    app,
                    [
                            "restore", "verify", str(target_dir),
                            "--repository", repo_name,
                            "--snapshot", SNAPSHOT_ID,
                            "--config-dir", str(config_dir),
                    ],
                    env=env,
            )
            verify_output = combined_output(verify_result)
            assert verify_result.exit_code == 0, verify_output
            assert "Verification Complete" in verify_output
            patched_restore["recovery_validator"].validate_pre_recovery.assert_called_once()
            maybe_show_cli_output(verify_result, label="tl restore verify")
