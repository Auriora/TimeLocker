"""Security and resilience tests for Linux status-event delivery."""

from __future__ import annotations

import json
import socket
from threading import Event
from uuid import UUID

import pytest

from TimeLocker.system_control.event_client import (
    StatusEventAccessDenied,
    UnixSocketStatusEventClient,
)
from TimeLocker.system_control.interfaces import PeerIdentity
from TimeLocker.system_control.linux_adapter import LinuxStatusEventTransport
from TimeLocker.system_control.models import StatusEvent
from TimeLocker.system_control.status_events import BoundedStatusEventBroker
from TimeLocker.system_control.types import (
    StatusEventConnectionState,
    StatusEventKind,
)


SESSION_ID = UUID("58d95acd-aa24-4461-96bb-74d3421e8e42")


class _IdentityProvider:
    def peer_identity(self, _connection: object) -> PeerIdentity:
        return PeerIdentity("linux-uid:1000", process_id=123)


class _Membership:
    def __init__(self, answers: list[bool]) -> None:
        self._answers = iter(answers)
        self.calls = 0

    def is_current_member(
        self,
        _identity: PeerIdentity,
        _group_name: str,
    ) -> bool:
        self.calls += 1
        return next(self._answers, False)


def _transport(listener: socket.socket, *, stop_event: Event | None = None):
    return LinuxStatusEventTransport(
        listener,
        heartbeat_interval_seconds=0.25,
        send_timeout_seconds=0.25,
        max_frame_bytes=1_024,
        stop_event=stop_event,
    )


class _MemoryConnection:
    def __init__(self, incoming: list[bytes] | None = None) -> None:
        self.incoming = list(incoming or [])
        self.sent: list[bytes] = []
        self.closed = False

    def settimeout(self, _timeout: float) -> None:
        pass

    def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)

    def recv(self, _maximum: int) -> bytes:
        return self.incoming.pop(0) if self.incoming else b""

    def close(self) -> None:
        self.closed = True


def test_authorized_subscription_receives_allowlisted_initial_event() -> None:
    listener, peer = socket.socketpair()
    broker = BoundedStatusEventBroker(session_id=SESSION_ID)
    membership = _Membership([True, True, False])
    transport = _transport(listener)
    connection = _MemoryConnection()
    try:
        transport.serve_connection(
            connection,  # type: ignore[arg-type]
            broker=broker,
            identity_provider=_IdentityProvider(),
            membership_resolver=membership,
        )
        event = StatusEvent.from_mapping(json.loads(connection.sent[0]))
        assert event.kind is StatusEventKind.SNAPSHOT_REQUIRED
        assert event.revision.session_id == SESSION_ID
        assert membership.calls >= 2
    finally:
        listener.close()
        peer.close()


def test_denied_subscription_receives_only_safe_bounded_denial() -> None:
    listener, peer = socket.socketpair()
    transport = _transport(listener)
    connection = _MemoryConnection()
    try:
        transport.serve_connection(
            connection,  # type: ignore[arg-type]
            broker=BoundedStatusEventBroker(),
            identity_provider=_IdentityProvider(),
            membership_resolver=_Membership([False]),
        )
        assert json.loads(connection.sent[0]) == {
            "safe_summary": "System access denied.",
            "status": "denied",
        }
    finally:
        listener.close()
        peer.close()


def test_membership_revocation_prevents_the_next_event_payload() -> None:
    listener, peer = socket.socketpair()
    broker = BoundedStatusEventBroker(session_id=SESSION_ID)
    membership = _Membership([True, True, False])
    transport = _transport(listener)
    connection = _MemoryConnection()
    try:
        transport.serve_connection(
            connection,  # type: ignore[arg-type]
            broker=broker,
            identity_provider=_IdentityProvider(),
            membership_resolver=membership,
        )
        initial = StatusEvent.from_mapping(json.loads(connection.sent[0]))
        assert initial.kind is StatusEventKind.SNAPSHOT_REQUIRED
        assert len(connection.sent) == 1
        assert membership.calls >= 3
    finally:
        listener.close()
        peer.close()


def test_idle_subscription_receives_reauthorized_heartbeat() -> None:
    listener, peer = socket.socketpair()
    transport = _transport(listener)
    connection = _MemoryConnection()
    try:
        transport.serve_connection(
            connection,  # type: ignore[arg-type]
            broker=BoundedStatusEventBroker(session_id=SESSION_ID),
            identity_provider=_IdentityProvider(),
            membership_resolver=_Membership([True, True, True, False]),
        )
        assert StatusEvent.from_mapping(json.loads(connection.sent[0])).kind is (
            StatusEventKind.SNAPSHOT_REQUIRED
        )
        assert StatusEvent.from_mapping(json.loads(connection.sent[1])).kind is (
            StatusEventKind.HEARTBEAT
        )
    finally:
        listener.close()
        peer.close()


def test_slow_sender_is_disconnected_and_subscription_capacity_is_released() -> None:
    class _SlowConnection:
        def settimeout(self, _timeout: float) -> None:
            pass

        def sendall(self, _payload: bytes) -> None:
            raise TimeoutError

    listener, peer = socket.socketpair()
    broker = BoundedStatusEventBroker(max_subscribers=1)
    transport = _transport(listener)
    try:
        with pytest.raises(TimeoutError):
            transport.serve_connection(
                _SlowConnection(),  # type: ignore[arg-type]
                broker=broker,
                identity_provider=_IdentityProvider(),
                membership_resolver=_Membership([True, True]),
            )
        replacement = broker.subscribe()
        replacement.close()
    finally:
        listener.close()
        peer.close()


def test_status_transport_adopts_the_dedicated_systemd_listener(
    monkeypatch,
) -> None:
    class _ListeningSocket:
        family = socket.AF_UNIX

        def getsockopt(self, _level: int, _option: int) -> int:
            return 1

        def close(self) -> None:
            pass

    listener = _ListeningSocket()
    monkeypatch.setattr(socket, "socket", _ListeningSocket)
    monkeypatch.setattr(socket, "fromfd", lambda *_args: listener)

    transport = LinuxStatusEventTransport.from_systemd(
        descriptor=4,
        heartbeat_interval_seconds=5.0,
    )

    assert transport.listener is listener
    assert transport.max_connections == 32


def test_event_client_reconnects_after_oversized_frame_and_disconnect() -> None:
    first_valid = StatusEvent(
        revision=BoundedStatusEventBroker(session_id=SESSION_ID).current_revision(),
        kind=StatusEventKind.SNAPSHOT_REQUIRED,
    )
    restarted_session = UUID("963f31ad-ff34-458a-a1df-1782c23c27b7")
    second_valid = StatusEvent(
        revision=BoundedStatusEventBroker(
            session_id=restarted_session
        ).current_revision(),
        kind=StatusEventKind.SNAPSHOT_REQUIRED,
    )
    payloads = [
        (b"x" * 1_025) + b"\n",
        (json.dumps(first_valid.to_wire()) + "\n").encode(),
        (json.dumps(second_valid.to_wire()) + "\n").encode(),
    ]

    def connect() -> socket.socket:
        return _MemoryConnection([payloads.pop(0)])  # type: ignore[return-value]

    stop_event = Event()
    event_client = UnixSocketStatusEventClient(
        max_event_bytes=1_024,
        base_retry_delay_seconds=0.001,
        max_retry_delay_seconds=0.002,
        connection_factory=connect,
    )
    events = event_client.events(stop_event)
    assert next(events) == first_valid
    assert next(events) == second_valid
    stop_event.set()


def test_event_client_reconnects_immediately_after_a_healthy_stream_drops() -> None:
    initial = StatusEvent(
        revision=BoundedStatusEventBroker(session_id=SESSION_ID).current_revision(),
        kind=StatusEventKind.SNAPSHOT_REQUIRED,
    )
    restarted = StatusEvent(
        revision=BoundedStatusEventBroker().current_revision(),
        kind=StatusEventKind.SNAPSHOT_REQUIRED,
    )
    payloads = [
        (json.dumps(initial.to_wire()) + "\n").encode(),
        (json.dumps(restarted.to_wire()) + "\n").encode(),
    ]

    def connect() -> socket.socket:
        return _MemoryConnection([payloads.pop(0)])  # type: ignore[return-value]

    stop_event = Event()
    waits: list[float | None] = []
    stop_event.wait = lambda timeout=None: waits.append(timeout) or False  # type: ignore[method-assign]
    event_client = UnixSocketStatusEventClient(connection_factory=connect)
    events = event_client.events(stop_event)

    assert next(events) == initial
    assert next(events) == restarted
    assert waits == []
    stop_event.set()


def test_event_client_rejects_denial_without_status_disclosure() -> None:
    client = _MemoryConnection(
        [b'{"safe_summary":"System access denied.","status":"denied"}\n']
    )
    event_client = UnixSocketStatusEventClient(
        connection_factory=lambda: client  # type: ignore[arg-type,return-value]
    )
    with pytest.raises(StatusEventAccessDenied, match="access denied"):
        next(event_client.events(Event()))


def test_event_client_projects_os_permission_denial_without_retry() -> None:
    calls = 0

    def denied_connect() -> socket.socket:
        nonlocal calls
        calls += 1
        raise PermissionError("private socket path")

    states: list[StatusEventConnectionState] = []
    event_client = UnixSocketStatusEventClient(
        connection_factory=denied_connect,
    )

    with pytest.raises(StatusEventAccessDenied, match="access denied"):
        next(event_client.events(Event(), on_connection_state=states.append))

    assert calls == 1
    assert states == [StatusEventConnectionState.DENIED]


def test_event_client_reports_unavailable_once_while_retrying() -> None:
    stop_event = Event()
    states: list[StatusEventConnectionState] = []
    calls = 0

    def unavailable_connect() -> socket.socket:
        nonlocal calls
        calls += 1
        if calls == 2:
            stop_event.set()
        raise FileNotFoundError("socket missing")

    event_client = UnixSocketStatusEventClient(
        connection_factory=unavailable_connect,
        base_retry_delay_seconds=0.001,
        max_retry_delay_seconds=0.002,
    )

    assert list(
        event_client.events(
            stop_event,
            on_connection_state=states.append,
        )
    ) == []
    assert calls == 2
    assert states == [StatusEventConnectionState.UNAVAILABLE]
