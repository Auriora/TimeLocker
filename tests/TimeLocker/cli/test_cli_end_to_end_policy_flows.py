"""
End-to-end CLI workflow tests covering policy creation, assignment, and status.
"""

from __future__ import annotations

import json
from typing import Dict, List

import pytest

from TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
        get_cli_runner,
        combined_output,
        maybe_show_cli_output,
)

runner = get_cli_runner()


def _invoke(env_bundle: Dict[str, object], args: List[str], label: str):
    """Run CLI command and assert success, returning the result."""
    result = runner.invoke(app, args, env=env_bundle["env"])
    assert result.exit_code == 0, combined_output(result)
    maybe_show_cli_output(result, label=label)
    return result


def _invoke_json(env_bundle: Dict[str, object], args: List[str], label: str):
    """Invoke CLI command that emits JSON and parse the response."""
    result = _invoke(env_bundle, args, label)
    output = result.stdout.strip()
    assert output, "Expected JSON output but got empty response"
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Failed to parse JSON output: {output}") from exc


def _add_repository(env_bundle: Dict[str, object], repo_name: str):
    """Add a repository via CLI to simulate user setup."""
    _invoke(
            env_bundle,
            [
                    "repos", "add", repo_name, env_bundle["repo_uri"],
                    "--description", "Policy E2E repository",
                    "--config-dir", str(env_bundle["config_dir"]),
                    "--set-default",
            ],
            label=f"tl repos add {repo_name}",
    )


def _create_selection(env_bundle: Dict[str, object], selection_name: str):
    """Create a selection template for policy usage."""
    _invoke(
            env_bundle,
            [
                    "selections", "create", selection_name,
                    "--include-path", str(env_bundle["source_dir"]),
                    "--description", "Policy E2E selection",
            ],
            label=f"tl selections create {selection_name}",
    )


class TestCLIPolicyEndToEndFlows:
    """Exercise CLI policy workflows that mirror operator behavior."""

    pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.policy]

    def test_policy_lifecycle_flow(self, isolated_cli_environment):
        """
        Full flow: create retention + backup policy, assign it, and verify status.
        """
        repo_name = "docs-policy-repo"
        retention_name = "retention-daily"
        backup_name = "nightly-backup-policy"
        selection_name = "policy-selection"

        _add_repository(isolated_cli_environment, repo_name)
        _create_selection(isolated_cli_environment, selection_name)

        _invoke(
                isolated_cli_environment,
                [
                        "policy", "retention", "create", retention_name,
                        "--daily", "7",
                        "--weekly", "4",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl policy retention create",
        )

        retention_policies = _invoke_json(
                isolated_cli_environment,
                [
                        "policy", "retention", "list",
                        "--json",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl policy retention list --json",
        )
        retention_policy = next(
                (policy for policy in retention_policies if policy["name"] == retention_name),
                None
        )
        assert retention_policy is not None, "Retention policy not found in list output"

        _invoke(
                isolated_cli_environment,
                [
                        "policy", "backup", "create", backup_name,
                        "--repository", repo_name,
                        "--retention", retention_policy["id"],
                        "--selection", selection_name,
                        "--description", "Nightly backups for documents",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl policy backup create",
        )

        backup_policies = _invoke_json(
                isolated_cli_environment,
                [
                        "policy", "backup", "list",
                        "--json",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl policy backup list --json",
        )
        backup_policy = next(
                (policy for policy in backup_policies if policy["name"] == backup_name),
                None
        )
        assert backup_policy is not None, "Backup policy not found in list output"

        backup_details = _invoke_json(
                isolated_cli_environment,
                [
                        "policy", "backup", "show", backup_policy["id"],
                        "--json",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl policy backup show --json",
        )
        assert backup_details["name"] == backup_name
        assert backup_details["retention_policy_id"] == retention_policy["id"]

        _invoke(
                isolated_cli_environment,
                [
                        "policy", "assignment", "create",
                        backup_policy["id"],
                        repo_name,
                        "--priority", "75",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl policy assignment create",
        )

        assignments = _invoke_json(
                isolated_cli_environment,
                [
                        "policy", "assignment", "list",
                        "--json",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl policy assignment list --json",
        )
        assert assignments, "Expected at least one assignment"
        assignment = assignments[0]
        assert assignment["policy_id"] == backup_policy["id"]
        assert assignment["target_id"] == repo_name

        status = _invoke_json(
                isolated_cli_environment,
                [
                        "policy", "status",
                        "--repository", repo_name,
                        "--json",
                        "--config-dir", str(isolated_cli_environment["config_dir"]),
                ],
                label="tl policy status --repository --json",
        )
        assert status["repository"] == repo_name
        assert status["active_policies"] == 1
        assert status["total_assignments"] == 1
