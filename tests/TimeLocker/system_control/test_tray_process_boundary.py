"""Import and lifecycle boundaries for the independent tray process."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from TimeLocker.system_control import tray_entry
from TimeLocker.system_control.tray_entry import _single_instance


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
