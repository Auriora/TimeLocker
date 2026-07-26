"""Public protected-system command tests."""

from uuid import uuid4

import pytest

from TimeLocker.cli import app
from TimeLocker.cli_modules.commands import system as system_commands
from TimeLocker.system_control.models import ActionReceipt
from tests.TimeLocker.cli.test_utils import combined_output, get_cli_runner


runner = get_cli_runner()


class _Client:
    def __init__(self) -> None:
        self.backup_request = None
        self.retention_request = None

    def request_backup(self, request):
        self.backup_request = request
        return ActionReceipt(uuid4(), True, "queued", uuid4())

    def request_retention(self, request):
        self.retention_request = request
        return ActionReceipt(uuid4(), True, "queued", uuid4())


@pytest.mark.unit
def test_system_help_exposes_protected_actions() -> None:
    result = runner.invoke(app, ["system", "--help"])

    assert result.exit_code == 0
    assert "backup" in combined_output(result)
    assert "retention" in combined_output(result)


@pytest.mark.unit
def test_system_backup_uses_protected_backend(monkeypatch) -> None:
    client = _Client()
    monkeypatch.setattr(
        system_commands,
        "_create_system_control_client",
        lambda: client,
    )

    result = runner.invoke(app, ["system", "backup", "--target", "production"])

    assert result.exit_code == 0
    assert client.backup_request.target_id == "production"


@pytest.mark.unit
def test_system_retention_requires_exact_fingerprint(monkeypatch) -> None:
    client = _Client()
    monkeypatch.setattr(
        system_commands,
        "_create_system_control_client",
        lambda: client,
    )

    result = runner.invoke(
        app,
        [
            "system",
            "retention",
            "--policy-fingerprint",
            "a" * 64,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert client.retention_request.policy_fingerprint == "a" * 64
    assert client.retention_request.dry_run is True
