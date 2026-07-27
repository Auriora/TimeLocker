"""Entrypoint checks for the privileged system-control backend."""

import os
import socket
from pathlib import Path
from threading import Event
from typing import cast

import pytest

from TimeLocker.system_control import backend_entry
from TimeLocker.system_control.status_events import (
    BoundedStatusEventBroker,
    StatusChangeCoordinator,
)
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
    monkeypatch.setenv("LISTEN_FDS", "2")
    monkeypatch.setenv("LISTEN_FDNAMES", "control:status-events")

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
    assert captured["status_systemd_descriptor"] == 4
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
def test_systemd_descriptor_names_remove_order_dependency() -> None:
    control, status = backend_entry._systemd_socket_descriptors(
        {
            "LISTEN_PID": "123",
            "LISTEN_FDS": "2",
            "LISTEN_FDNAMES": "status-events:control",
        },
        process_id=123,
    )

    assert control == 4
    assert status == 3


@pytest.mark.unit
def test_systemd_descriptor_contract_allows_control_without_event_socket() -> None:
    control, status = backend_entry._systemd_socket_descriptors(
        {
            "LISTEN_PID": "123",
            "LISTEN_FDS": "1",
            "LISTEN_FDNAMES": "control",
        },
        process_id=123,
    )

    assert control == 3
    assert status is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "environment",
    [
        {},
        {
            "LISTEN_PID": "122",
            "LISTEN_FDS": "2",
            "LISTEN_FDNAMES": "control:status-events",
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
        backend_entry._systemd_socket_descriptors(environment, process_id=123)


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
    assert captured["status_systemd_descriptor"] is None
    assert captured["status_socket_mode"] == "disabled"


@pytest.mark.unit
def test_build_linux_backend_rejects_status_listener_without_listener_mode(
    tmp_path: Path,
) -> None:
    paths = backend_entry.LinuxBackendPaths.from_state_root(
        policy_path=tmp_path / "policy.json",
        state_root=tmp_path / "state-root",
        expected_owner=os.getuid(),
    )

    with pytest.raises(
        ValueError,
        match="status socket listener can only be provided in listener mode",
    ):
        backend_entry.build_linux_backend(
            paths=paths,
            status_socket_mode="systemd",
            status_listener=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM),
        )


@pytest.mark.unit
def test_build_linux_backend_rejects_listener_status_mode_without_status_listener() -> None:
    paths = backend_entry.LinuxBackendPaths.from_state_root(
        policy_path=Path("/tmp/never-read"),
        state_root=Path("/tmp/never-read-state"),
        expected_owner=os.getuid(),
    )

    with pytest.raises(
        ValueError,
        match="status socket listener is required for listener mode",
    ):
        backend_entry.build_linux_backend(paths=paths, status_socket_mode="listener")


@pytest.mark.unit
def test_build_linux_backend_listener_status_mode_uses_supplied_listener(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    control_listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    status_listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    paths = backend_entry.LinuxBackendPaths.from_state_root(
        policy_path=tmp_path / "policy.json",
        state_root=tmp_path / "state-root",
        expected_owner=os.getuid(),
    )

    monkeypatch.setattr(
        backend_entry,
        "load_system_policy",
        lambda *_args, **_kwargs: backend_entry.SystemPolicy(),
    )
    monkeypatch.setattr(
        backend_entry,
        "_build_transport",
        lambda **_kwargs: _StubTransport(control_listener),
    )
    monkeypatch.setattr(
        backend_entry,
        "_build_status_transport",
        lambda **kwargs: (
            captured.__setitem__("status_listener", kwargs["listener"])
            or _StubTransport(status_listener)
        ),
    )
    monkeypatch.setattr(
        backend_entry,
        "_build_handlers",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(
        backend_entry,
        "reconcile_abandoned_runs",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        backend_entry,
        "_emit_startup_diagnostics",
        lambda *_, **__: None,
    )

    service = backend_entry.build_linux_backend(
        paths=paths,
        status_socket_mode="listener",
        status_listener=status_listener,
    )

    assert captured["status_listener"] is status_listener
    assert service.status_event_transport is not None
    service.stop()
    assert control_listener.fileno() == -1
    assert status_listener.fileno() == -1


@pytest.mark.unit
def test_event_transport_failure_does_not_block_control_requests() -> None:
    control_served = Event()
    event_started = Event()

    class _ControlTransport:
        listener = None
        identity_provider = object()

        def serve(self, _dispatcher: object) -> None:
            control_served.set()

    class _FailingEventTransport:
        listener = None

        def serve(self, *_args: object) -> None:
            event_started.set()
            raise OSError("event socket unavailable")

    broker = BoundedStatusEventBroker()
    service = backend_entry.LinuxBackendService(
        policy=backend_entry.SystemPolicy(),
        store=cast(object, None),
        locks=cast(object, None),
        dispatcher=cast(object, None),
        transport=cast(object, _ControlTransport()),
        status_event_transport=cast(object, _FailingEventTransport()),
        audit_sink=cast(object, None),
        stop_event=Event(),
        status_event_broker=broker,
        status_change_coordinator=StatusChangeCoordinator(broker),
        membership_resolver=cast(object, None),
    )

    service.serve_forever(install_signal_handlers=False)

    assert event_started.is_set()
    assert control_served.is_set()
