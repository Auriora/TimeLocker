"""Entrypoint checks for the privileged system-control backend."""

import os
from pathlib import Path
from threading import Event
from typing import cast

import pytest

from TimeLocker.system_control import backend_entry
from TimeLocker.system_control.types import OperationTrigger


class _StubTransport:
    """Minimal transport shim exposing only listener shutdown semantics."""

    def __init__(self, listener: object) -> None:
        self.listener = listener


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
    monkeypatch.setenv("LISTEN_PID", str(os.getpid()))
    monkeypatch.setenv("LISTEN_FDS", "1")
    monkeypatch.setenv("LISTEN_FDNAMES", "control")

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
    assert captured["systemd_descriptor"] == 3
    assert "status_systemd_descriptor" not in captured
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


@pytest.mark.unit
def test_systemd_descriptor_contract_requires_only_control_socket() -> None:
    control = backend_entry._systemd_socket_descriptor(
        {
            "LISTEN_PID": "123",
            "LISTEN_FDS": "1",
            "LISTEN_FDNAMES": "control",
        },
        process_id=123,
    )

    assert control == 3


@pytest.mark.unit
@pytest.mark.parametrize(
    "environment",
    [
        {},
        {
            "LISTEN_PID": "122",
            "LISTEN_FDS": "1",
            "LISTEN_FDNAMES": "control",
        },
        {
            "LISTEN_PID": "123",
            "LISTEN_FDS": "1",
            "LISTEN_FDNAMES": "status-events",
        },
        {
            "LISTEN_PID": "123",
            "LISTEN_FDS": "2",
            "LISTEN_FDNAMES": "control:control",
        },
    ],
)
def test_systemd_descriptor_contract_fails_closed(
    environment: dict[str, str],
) -> None:
    with pytest.raises(RuntimeError, match="systemd socket"):
        backend_entry._systemd_socket_descriptor(environment, process_id=123)


@pytest.mark.unit
def test_main_runs_control_backend_when_event_socket_is_absent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        backend_entry,
        "run_linux_backend",
        lambda **kwargs: captured.update(kwargs),
    )
    monkeypatch.setenv("LISTEN_PID", str(os.getpid()))
    monkeypatch.setenv("LISTEN_FDS", "1")
    monkeypatch.setenv("LISTEN_FDNAMES", "control")

    backend_entry.main(
        [
            "--systemd-socket",
            "--policy",
            str(tmp_path / "policy.json"),
            "--state-root",
            str(tmp_path / "state"),
        ]
    )

    assert captured["systemd_descriptor"] == 3
    assert "status_systemd_descriptor" not in captured
    assert "status_socket_mode" not in captured


@pytest.mark.unit
def test_one_shot_service_serves_one_request_and_stops() -> None:
    control_served = Event()

    class _ControlTransport:
        listener = None

        def serve_once(self, _dispatcher: object) -> None:
            control_served.set()

    service = backend_entry.LinuxBackendService(
        policy=backend_entry.SystemPolicy(),
        store=cast(object, None),
        locks=cast(object, None),
        dispatcher=cast(object, None),
        transport=cast(object, _ControlTransport()),
        audit_sink=cast(object, None),
        stop_event=Event(),
        membership_resolver=cast(object, None),
    )

    service.serve_once()

    assert control_served.is_set()
    assert service.stop_event.is_set()
