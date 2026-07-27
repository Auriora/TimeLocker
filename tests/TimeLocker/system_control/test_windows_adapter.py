"""Contract tests for the platform-neutral Windows adapter seam."""

from dataclasses import dataclass, field
import json

import pytest

from TimeLocker.system_control.interfaces import PeerIdentity
from TimeLocker.system_control.models import StatusEvent
from TimeLocker.system_control.status_events import BoundedStatusEventBroker
from TimeLocker.system_control.types import StatusEventKind
from TimeLocker.system_control.windows_adapter import (
    WindowsCurrentGroupMembershipResolver,
    WindowsNamedPipeTransport,
    WindowsNamedPipeStatusEventTransport,
    WindowsPeerIdentityProvider,
    WindowsPeerToken,
)


class TokenProvider:
    def peer_token(self, _connection: object) -> WindowsPeerToken:
        return WindowsPeerToken(sid="S-1-5-21-1000", process_id=42)


@dataclass
class GroupProvider:
    allowed: bool
    calls: int = 0

    def is_current_member(self, sid: str, group_name: str) -> bool:
        self.calls += 1
        assert sid == "S-1-5-21-1000"
        assert group_name == "timelocker-operators"
        return self.allowed


@dataclass
class Connection:
    request: bytes
    sent: list[bytes] = field(default_factory=list)
    closed: bool = False

    def receive(self, _maximum: int) -> bytes:
        return self.request

    def send(self, payload: bytes) -> None:
        self.sent.append(payload)

    def close(self) -> None:
        self.closed = True


class Acceptor:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def accept(self) -> Connection:
        return self.connection


@dataclass
class EventConnection:
    sent: list[tuple[bytes, float]] = field(default_factory=list)
    closed: bool = False

    def send_event(self, payload: bytes, timeout_seconds: float) -> None:
        self.sent.append((payload, timeout_seconds))

    def close(self) -> None:
        self.closed = True


class EventAcceptor:
    def __init__(self, connection: EventConnection) -> None:
        self.connection = connection

    def accept(self) -> EventConnection:
        return self.connection


class SequencedGroupProvider:
    def __init__(self, answers: list[bool]) -> None:
        self._answers = iter(answers)
        self.calls = 0

    def is_current_member(self, sid: str, group_name: str) -> bool:
        assert sid == "S-1-5-21-1000"
        assert group_name == "timelocker-operators"
        self.calls += 1
        return next(self._answers, False)


class Handler:
    def handle(self, request: bytes, identity: PeerIdentity) -> bytes:
        assert request == b"request"
        assert identity.platform_id == "windows-sid:S-1-5-21-1000"
        return b"response"


@pytest.mark.unit
def test_identity_comes_from_pipe_token_provider() -> None:
    identity = WindowsPeerIdentityProvider(TokenProvider()).peer_identity(object())

    assert identity == PeerIdentity(
        platform_id="windows-sid:S-1-5-21-1000",
        process_id=42,
    )


@pytest.mark.unit
def test_group_membership_is_rechecked_and_fails_closed() -> None:
    provider = GroupProvider(allowed=True)
    resolver = WindowsCurrentGroupMembershipResolver(provider)
    identity = PeerIdentity(platform_id="windows-sid:S-1-5-21-1000")

    assert resolver.is_current_member(identity, "timelocker-operators")
    provider.allowed = False
    assert not resolver.is_current_member(identity, "timelocker-operators")
    assert provider.calls == 2
    assert not resolver.is_current_member(
        PeerIdentity(platform_id="linux-uid:1000"),
        "timelocker-operators",
    )


@pytest.mark.unit
def test_named_pipe_transport_bounds_request_and_closes_connection() -> None:
    connection = Connection(b"request")
    transport = WindowsNamedPipeTransport(
        Acceptor(connection),
        TokenProvider(),
        max_request_bytes=1024,
    )

    transport.serve_once(Handler())

    assert connection.sent == [b"response"]
    assert connection.closed


@pytest.mark.unit
def test_named_pipe_transport_rejects_oversized_request() -> None:
    connection = Connection(b"x" * 1025)
    transport = WindowsNamedPipeTransport(
        Acceptor(connection),
        TokenProvider(),
        max_request_bytes=1024,
    )

    with pytest.raises(OSError, match="exceeds"):
        transport.serve_once(Handler())

    assert connection.closed


@pytest.mark.unit
def test_windows_event_subscription_uses_token_and_reauthorizes_delivery() -> None:
    connection = EventConnection()
    groups = SequencedGroupProvider([True, True, False])
    transport = WindowsNamedPipeStatusEventTransport(
        EventAcceptor(connection),
        TokenProvider(),
        heartbeat_interval_seconds=0.25,
        max_frame_bytes=1_024,
    )

    transport.serve_once(
        BoundedStatusEventBroker(),
        WindowsCurrentGroupMembershipResolver(groups),
    )

    assert connection.closed
    assert groups.calls == 3
    assert len(connection.sent) == 1
    event = StatusEvent.from_mapping(json.loads(connection.sent[0][0]))
    assert event.kind is StatusEventKind.SNAPSHOT_REQUIRED
    assert connection.sent[0][1] == 2.0


@pytest.mark.unit
def test_windows_event_denial_contains_no_status_payload() -> None:
    connection = EventConnection()
    transport = WindowsNamedPipeStatusEventTransport(
        EventAcceptor(connection),
        TokenProvider(),
        heartbeat_interval_seconds=0.25,
        max_frame_bytes=1_024,
    )

    transport.serve_once(
        BoundedStatusEventBroker(),
        WindowsCurrentGroupMembershipResolver(
            SequencedGroupProvider([False])
        ),
    )

    assert json.loads(connection.sent[0][0]) == {
        "safe_summary": "System access denied.",
        "status": "denied",
    }
    assert connection.closed


@pytest.mark.unit
def test_windows_event_heartbeat_is_bounded_and_reauthorized() -> None:
    connection = EventConnection()
    transport = WindowsNamedPipeStatusEventTransport(
        EventAcceptor(connection),
        TokenProvider(),
        heartbeat_interval_seconds=0.25,
        max_frame_bytes=1_024,
    )

    transport.serve_once(
        BoundedStatusEventBroker(),
        WindowsCurrentGroupMembershipResolver(
            SequencedGroupProvider([True, True, True, False])
        ),
    )

    events = [
        StatusEvent.from_mapping(json.loads(payload))
        for payload, _timeout in connection.sent
    ]
    assert [event.kind for event in events] == [
        StatusEventKind.SNAPSHOT_REQUIRED,
        StatusEventKind.HEARTBEAT,
    ]


@pytest.mark.unit
def test_windows_slow_event_sender_releases_subscription_capacity() -> None:
    class SlowConnection(EventConnection):
        def send_event(self, payload: bytes, timeout_seconds: float) -> None:
            raise TimeoutError

    connection = SlowConnection()
    broker = BoundedStatusEventBroker(max_subscribers=1)
    transport = WindowsNamedPipeStatusEventTransport(
        EventAcceptor(connection),
        TokenProvider(),
        heartbeat_interval_seconds=0.25,
        max_frame_bytes=1_024,
    )

    with pytest.raises(TimeoutError):
        transport.serve_once(
            broker,
            WindowsCurrentGroupMembershipResolver(
                SequencedGroupProvider([True, True])
            ),
        )

    replacement = broker.subscribe()
    replacement.close()
    assert connection.closed
