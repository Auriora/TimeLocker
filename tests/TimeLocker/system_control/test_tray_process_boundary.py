"""Import and lifecycle boundaries for the independent tray process."""

import os
from contextlib import nullcontext
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
def test_package_import_defers_backup_and_cloud_dependencies() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = "src"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import TimeLocker; "
                "assert 'TimeLocker.backup_manager' not in sys.modules; "
                "assert 'boto3' not in sys.modules; "
                "assert 'b2sdk' not in sys.modules; "
                "from TimeLocker import BackupManager; "
                "assert BackupManager.__name__ == 'BackupManager'"
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
def test_tray_launcher_import_defers_unrelated_system_services() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = "src"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import TimeLocker.system_control.tray_launcher_entry; "
                "assert 'TimeLocker.system_control.retention' not in sys.modules; "
                "assert 'TimeLocker.system_control.storage' not in sys.modules; "
                "assert 'boto3' not in sys.modules; "
                "assert 'b2sdk' not in sys.modules"
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
    assert "open_ui" not in _tray_menu_actions(None)
    assert "status" not in _tray_menu_actions(None)


@pytest.mark.unit
def test_apply_state_projects_last_backup_time_to_tray() -> None:
    backup_time = datetime(2026, 7, 26, 12, 34, tzinfo=UTC)
    tray = Mock()
    tray.is_available.return_value = True
    state = TrayDisplayState(
        status="success",
        tooltip="TimeLocker\nLast backup: 2026-07-26T12:34:00+00:00",
        health="Healthy",
        activity="Idle",
        active_operations=0,
        backend_available=True,
        last_successful_backup_completed_at=backup_time,
        latest_backup_started_at=backup_time,
        latest_backup_status="Backup completed successfully.",
        latest_retention_started_at=None,
        latest_retention_status=None,
        next_backup_at=None,
        next_retention_at=None,
    )

    _apply_state(tray, state)

    status_info = tray.update_status_info.call_args.args[0]
    assert status_info.last_successful_backup_time == backup_time
    assert status_info.health == "Healthy"
    assert status_info.activity == "Idle"


@pytest.mark.unit
def test_healthy_serve_is_silent_and_applies_event_snapshot(
    monkeypatch,
    capsys,
) -> None:
    arguments = type(
        "Arguments",
        (),
        {
            "action": "serve",
            "once": True,
            "refresh_seconds": 15,
            "target_id": "production",
            "retention_policy_fingerprint": None,
            "dry_run_retention": False,
        },
    )()
    state = TrayDisplayState(
        status="success",
        tooltip="TimeLocker",
        health="Healthy",
        activity="Idle",
        active_operations=0,
        backend_available=True,
        last_successful_backup_completed_at=datetime(
            2026,
            7,
            26,
            12,
            34,
            tzinfo=UTC,
        ),
        latest_backup_started_at=None,
        latest_backup_status="Backup completed successfully.",
        latest_retention_started_at=None,
        latest_retention_status=None,
        next_backup_at=None,
        next_retention_at=None,
    )
    client = Mock()
    client.project_snapshot.return_value = state
    tray = Mock()
    tray.is_available.return_value = True

    class _Subscription:
        def serve(self, _stop_event, *, on_snapshot, on_unavailable) -> None:
            on_snapshot(object())

    monkeypatch.setattr(tray_entry, "_parse_args", lambda: arguments)
    monkeypatch.setattr(tray_entry, "_build_client", lambda **_kwargs: client)
    monkeypatch.setattr(tray_entry, "SystemTrayIntegration", lambda **_kwargs: tray)
    monkeypatch.setattr(
        tray_entry,
        "TrayStatusSubscriptionClient",
        lambda: _Subscription(),
    )
    monkeypatch.setattr(tray_entry, "_single_instance", lambda: nullcontext())
    monkeypatch.setattr(tray_entry.signal, "signal", lambda *_args: None)

    tray_entry.main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert tray.update_status_info.call_count == 1
    client.refresh_status.assert_not_called()


@pytest.mark.unit
def test_connecting_icon_is_processed_before_subscription_starts(
    monkeypatch,
) -> None:
    arguments = type(
        "Arguments",
        (),
        {
            "action": "serve",
            "once": True,
            "refresh_seconds": 15,
            "target_id": "production",
            "retention_policy_fingerprint": None,
            "dry_run_retention": False,
        },
    )()
    events: list[str] = []
    tray = Mock()
    tray.is_available.return_value = True
    tray.process_events.side_effect = lambda: events.append("ui-ready")

    class _Subscription:
        def serve(self, _stop_event, *, on_snapshot, on_unavailable) -> None:
            events.append("subscription-started")
            on_snapshot(object())

    monkeypatch.setattr(tray_entry, "_parse_args", lambda: arguments)
    monkeypatch.setattr(
        tray_entry,
        "_build_client",
        lambda **_kwargs: Mock(),
    )
    monkeypatch.setattr(tray_entry, "SystemTrayIntegration", lambda **_kwargs: tray)
    monkeypatch.setattr(
        tray_entry,
        "TrayStatusSubscriptionClient",
        lambda: _Subscription(),
    )
    monkeypatch.setattr(tray_entry, "_single_instance", lambda: nullcontext())
    monkeypatch.setattr(tray_entry.signal, "signal", lambda *_args: None)

    tray_entry.main()

    assert events[0] == "ui-ready"
    assert "subscription-started" in events


@pytest.mark.unit
def test_explicit_status_action_still_renders_bounded_output(
    monkeypatch,
    capsys,
) -> None:
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
    state = TrayDisplayState(
        status="idle",
        tooltip="TimeLocker",
        health="Healthy",
        activity="Idle",
        active_operations=0,
        backend_available=True,
        last_successful_backup_completed_at=None,
        latest_backup_started_at=None,
        latest_backup_status=None,
        latest_retention_started_at=None,
        latest_retention_status=None,
        next_backup_at=None,
        next_retention_at=None,
    )
    client = Mock()
    client.perform_action.return_value = state
    monkeypatch.setattr(tray_entry, "_parse_args", lambda: arguments)
    monkeypatch.setattr(tray_entry, "_build_client", lambda **_kwargs: client)

    tray_entry.main()

    output = capsys.readouterr().out
    assert "status: idle" in output
    assert "backend_available: True" in output
