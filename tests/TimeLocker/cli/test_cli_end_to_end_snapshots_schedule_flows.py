"""
End-to-end CLI workflows for snapshot inspection and schedule automation.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
        get_cli_runner,
        combined_output,
        maybe_show_cli_output,
)

runner = get_cli_runner()


def _invoke(env_bundle: Dict[str, object], args: List[str], label: str):
    """Invoke CLI command, assert success, and optionally show output."""
    result = runner.invoke(app, args, env=env_bundle["env"])
    assert result.exit_code == 0, combined_output(result)
    maybe_show_cli_output(result, label=label)
    return result


def _invoke_json(env_bundle: Dict[str, object], args: List[str], label: str):
    """Invoke CLI command that emits JSON and return parsed payload."""
    result = _invoke(env_bundle, args, label)
    payload = result.stdout.strip()
    assert payload, "Expected JSON output but received empty response"
    return json.loads(payload)


def _add_repository(env_bundle: Dict[str, object], repo_name: str, *, set_default: bool = False):
    """Add repository to the isolated config."""
    args = [
            "repos", "add", repo_name, env_bundle["repo_uri"],
            "--description", "E2E test repository",
            "--config-dir", str(env_bundle["config_dir"]),
    ]
    if set_default:
        args.append("--set-default")
    _invoke(env_bundle, args, label=f"tl repos add {repo_name}")


@contextmanager
def patched_snapshot_service(snapshot_id: str, source_dir: str):
    """
    Patch snapshot service methods with deterministic responses for CLI flows.
    """
    service = MagicMock()
    snapshot_entry = SimpleNamespace(
            id=snapshot_id,
            time="2025-11-16T12:00:00Z",
            hostname="timelocker-host",
            tags=["daily", "docs"],
    )
    service.list_snapshots.return_value = [snapshot_entry]
    service.get_snapshot.return_value = SimpleNamespace(
            id=snapshot_id,
            time="2025-11-16T12:00:00Z",
            hostname="timelocker-host",
            tags=["daily"],
    )
    search_result = SimpleNamespace(
            name="notes.txt",
            path=f"{source_dir}/notes.txt",
            type=SimpleNamespace(value="file"),
            size=2048,
            modification_time=datetime.now(),
    )
    service.find_snapshots.return_value = [search_result]
    service.delete_snapshot.return_value = SimpleNamespace(success=True)
    service.prune_snapshots.return_value = SimpleNamespace(success=True)

    manager = MagicMock()
    manager.snapshot_service = service

    with patch("TimeLocker.cli_modules.commands.snapshots._get_service_manager_for_command",
               return_value=manager):
        yield service


class TestCLISnapshotEndToEndFlows:
    """Validate snapshot discovery commands end-to-end."""

    pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.snapshots]

    def test_snapshot_list_show_find_flow(self, isolated_cli_environment):
        repo_name = "snapshots-e2e"
        snapshot_id = "a1b2c3d4e5f6a7b8"

        _add_repository(isolated_cli_environment, repo_name, set_default=True)

        with patched_snapshot_service(snapshot_id, isolated_cli_environment["source_dir"]):
            _invoke(
                    isolated_cli_environment,
                    [
                            "snapshots", "list",
                            "--repository", repo_name,
                            "--config-dir", str(isolated_cli_environment["config_dir"]),
                    ],
                    label="tl snapshots list",
            )

            _invoke(
                    isolated_cli_environment,
                    [
                            "snapshots", "show", snapshot_id,
                            "--repository", repo_name,
                            "--config-dir", str(isolated_cli_environment["config_dir"]),
                    ],
                    label="tl snapshots show",
            )

            _invoke(
                    isolated_cli_environment,
                    [
                            "snapshots", "find", "*.txt",
                            "--repository", repo_name,
                            "--limit", "5",
                            "--config-dir", str(isolated_cli_environment["config_dir"]),
                    ],
                    label="tl snapshots find",
            )

    def test_snapshot_forget_and_prune_flow(self, isolated_cli_environment):
        repo_name = "snapshots-prune-e2e"
        snapshot_id = "b1c2d3e4f5a6b7c8"

        _add_repository(isolated_cli_environment, repo_name, set_default=True)

        with patched_snapshot_service(snapshot_id, isolated_cli_environment["source_dir"]) as service:
            _invoke(
                    isolated_cli_environment,
                    [
                            "snapshots", "forget", snapshot_id,
                            "--repository", repo_name,
                            "--config-dir", str(isolated_cli_environment["config_dir"]),
                    ],
                    label="tl snapshots forget",
            )
            service.delete_snapshot.assert_called_once()

            _invoke(
                    isolated_cli_environment,
                    [
                            "snapshots", "prune",
                            "--repository", repo_name,
                            "--config-dir", str(isolated_cli_environment["config_dir"]),
                    ],
                    label="tl snapshots prune",
            )
            service.prune_snapshots.assert_called_once()


class TestCLIScheduleEndToEndFlows:
    """Exercise CLI schedule creation/listing/enabling flows."""

    pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.schedule]

    def test_schedule_create_list_and_toggle_flow(self, isolated_cli_environment):
        schedule_name = "nightly-docs"
        repository_name = "docs-repository"
        scripts_dir = Path(isolated_cli_environment["config_dir"]) / "scripts-out"

        _invoke(
                isolated_cli_environment,
                [
                        "schedule", "create",
                        schedule_name,
                        "--repository", repository_name,
                        "--source", str(Path(isolated_cli_environment["config_dir"])),
                        "--frequency", "daily",
                        "--enabled",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl schedule create",
        )

        schedules = _invoke_json(
                isolated_cli_environment,
                [
                        "schedule", "list",
                        "--json",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl schedule list --json",
        )
        assert schedule_name in schedules
        assert schedules[schedule_name]["repository"] == repository_name
        assert schedules[schedule_name]["sources"] == [str(Path(isolated_cli_environment["config_dir"]).resolve())]

        _invoke(
                isolated_cli_environment,
                [
                        "schedule", "show", schedule_name,
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl schedule show",
        )

        _invoke(
                isolated_cli_environment,
                [
                        "schedule", "disable", schedule_name,
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl schedule disable",
        )

        _invoke(
                isolated_cli_environment,
                [
                        "schedule", "enable", schedule_name,
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl schedule enable",
        )

        final_schedules = _invoke_json(
                isolated_cli_environment,
                [
                        "schedule", "list",
                        "--json",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl schedule list --json (final)",
        )
        assert final_schedules[schedule_name]["enabled"] is True

        scripts_dir.mkdir(parents=True, exist_ok=True)
        _invoke(
                isolated_cli_environment,
                [
                        "schedule", "generate-scripts", schedule_name,
                        "--output", str(scripts_dir),
                        "--platform", "cron",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl schedule generate-scripts",
        )
        generated_script = scripts_dir / f"{schedule_name}_cron.sh"
        assert generated_script.exists(), "Expected cron script to be generated"

        _invoke(
                isolated_cli_environment,
                [
                        "schedule", "test", schedule_name,
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl schedule test",
        )
