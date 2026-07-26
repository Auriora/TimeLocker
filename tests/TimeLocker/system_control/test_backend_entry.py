"""Entrypoint checks for the privileged system-control backend."""

from pathlib import Path

import pytest

from TimeLocker.system_control import backend_entry
from TimeLocker.system_control.types import OperationTrigger


@pytest.mark.unit
def test_main_requires_systemd_socket_mode() -> None:
    with pytest.raises(SystemExit) as caught:
        backend_entry.main([])

    assert caught.value.code == 2


@pytest.mark.unit
def test_scheduled_retention_fails_closed_without_live_adapter(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        backend_entry,
        "run_scheduled_retention",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("protected URI")),
    )

    with pytest.raises(SystemExit) as caught:
        backend_entry.main(["--scheduled-retention"])

    assert caught.value.code == 78
    assert "protected URI" not in capsys.readouterr().err


@pytest.mark.unit
def test_main_maps_backup_success_retention_trigger(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        backend_entry,
        "run_scheduled_retention",
        lambda **kwargs: captured.update(kwargs),
    )

    backend_entry.main(
        [
            "--scheduled-retention",
            "--retention-trigger",
            "backup-success",
            "--policy",
            str(tmp_path / "policy.json"),
            "--state-root",
            str(tmp_path / "state"),
            "--production-target",
            str(tmp_path / "target.json"),
        ]
    )

    assert captured["trigger"] is OperationTrigger.BACKUP_SUCCESS


@pytest.mark.unit
def test_main_maps_systemd_exit_status_for_backup_finish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def finish(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(backend_entry, "run_backup_record_finish", finish)
    monkeypatch.setenv("EXIT_STATUS", "75")

    backend_entry.main(["--backup-run-finish", "--backup-result", "exit-code"])

    assert captured["result"] == "exit-code"
    assert captured["exit_status"] == 75


@pytest.mark.unit
def test_main_ignores_non_numeric_systemd_exit_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def finish(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(backend_entry, "run_backup_record_finish", finish)
    monkeypatch.setenv("EXIT_STATUS", "KILL")

    backend_entry.main(["--backup-run-finish", "--backup-result", "signal"])

    assert captured["result"] == "signal"
    assert captured["exit_status"] is None


@pytest.mark.unit
def test_main_composes_only_explicit_system_paths(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    policy = tmp_path / "policy.json"
    state = tmp_path / "state"
    monkeypatch.setattr(
        backend_entry,
        "run_linux_backend",
        lambda **kwargs: captured.update(kwargs),
    )

    backend_entry.main(
        [
            "--systemd-socket",
            "--policy",
            str(policy),
            "--state-root",
            str(state),
        ]
    )

    paths = captured["paths"]
    assert isinstance(paths, backend_entry.LinuxBackendPaths)
    assert paths.policy_path == policy
    assert paths.record_root == state / "records"
    assert captured["socket_mode"] == "systemd"
    assert (
        captured["production_target_path"]
        == backend_entry.DEFAULT_PRODUCTION_TARGET_PATH
    )


@pytest.mark.unit
def test_main_redacts_initialization_failures(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        backend_entry,
        "run_linux_backend",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("s3://secret.example/private")
        ),
    )

    with pytest.raises(SystemExit) as caught:
        backend_entry.main(["--systemd-socket"])

    assert caught.value.code == 78
    output = capsys.readouterr().err
    assert "failed to initialize safely" in output
    assert "secret.example" not in output
