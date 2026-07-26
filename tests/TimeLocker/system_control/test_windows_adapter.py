"""Contract tests for the platform-neutral Windows adapter seam."""

from dataclasses import dataclass, field

import pytest

from TimeLocker.system_control.interfaces import PeerIdentity
from TimeLocker.system_control.windows_adapter import (
    WindowsCurrentGroupMembershipResolver,
    WindowsNamedPipeTransport,
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
