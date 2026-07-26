"""Import and lifecycle boundaries for the independent tray process."""

import os
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from TimeLocker.system_control import tray_entry
from TimeLocker.system_control.tray_client import TrayDisplayState
from TimeLocker.system_control.tray_entry import (
    _apply_state,
    _single_instance,
    _tray_menu_actions,
)


@pytest.mark.unit
def test_cli_import_does_not_load_platform_tray_module() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = "src"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import TimeLocker.cli; "
                "assert 'TimeLocker.monitoring.system_tray_integration' "
                "not in sys.modules"
            ),
        ],
        cwd=Path(__file__).parents[3],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.unit
def test_tray_single_instance_lock_rejects_second_owner(tmp_path) -> None:
    lock_path = tmp_path / "tray.lock"

    with _single_instance(lock_path):
        with pytest.raises(RuntimeError, match="already running"):
            with _single_instance(lock_path):
                pytest.fail("second tray instance acquired the same lock")

    assert not lock_path.exists()


@pytest.mark.unit
def test_one_shot_action_does_not_construct_desktop_tray(monkeypatch) -> None:
    arguments = type(
        "Arguments",
        (),
        {
            "action": "status",
            "target_id": "production",
            "retention_policy_fingerprint": None,
            "dry_run_retention": False,
        },
    )()

    monkeypatch.setattr(tray_entry, "_parse_args", lambda: arguments)
    monkeypatch.setattr(
        tray_entry,
        "_build_client",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(tray_entry, "_handle_action", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        tray_entry,
        "SystemTrayIntegration",
        lambda **_kwargs: pytest.fail("one-shot action constructed a GUI tray"),
    )

    tray_entry.main()


@pytest.mark.unit
def test_retention_menu_requires_configured_fingerprint() -> None:
    assert "retention_now" not in _tray_menu_actions(None)
    assert "retention_now" in _tray_menu_actions("a" * 64)


@pytest.mark.unit
def test_apply_state_projects_last_backup_time_to_tray() -> None:
    backup_time = datetime(2026, 7, 26, 12, 34, tzinfo=UTC)
    tray = Mock()
    tray.is_available.return_value = True
    state = TrayDisplayState(
        status="success",
        tooltip="TimeLocker\nLast backup: 2026-07-26T12:34:00+00:00",
        active_operations=0,
        backend_available=True,
        last_backup_started_at=backup_time,
        last_backup_status="Backup completed successfully.",
        last_retention_started_at=None,
        last_retention_status=None,
        next_backup_at=None,
        next_retention_at=None,
        repository_count=1,
    )

    _apply_state(tray, state)

    tray.update_last_backup_time.assert_called_once_with(backup_time)
