"""Windows system-control adapter contracts with injectable OS providers.

The concrete service and named-pipe implementation remain platform follow-up
work. These adapters keep identity and authorization derived from the pipe
token, never from request data, and are testable on non-Windows hosts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .interfaces import ControlRequestHandler, PeerIdentity
from .validation import require_group_name, require_safe_identifier


@dataclass(frozen=True, slots=True)
class WindowsPeerToken:
    """Bounded identity projected from a connected named-pipe client token."""

    sid: str
    process_id: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "sid",
            require_safe_identifier(self.sid, field="sid", maximum=128),
        )
        if type(self.process_id) is not int or not 1 <= self.process_id < 2**31:
            raise ValueError("process_id is outside the supported bound")


class WindowsTokenProvider(Protocol):
    """Read the caller token from a connected named pipe."""

    def peer_token(self, connection: object) -> WindowsPeerToken:
        """Return a kernel-derived caller token."""


class WindowsGroupProvider(Protocol):
    """Resolve current Windows group membership by SID."""

    def is_current_member(self, sid: str, group_name: str) -> bool:
        """Re-read current local/domain membership for one caller SID."""


class NamedPipeConnection(Protocol):
    """Minimal connection seam implemented by a Windows named-pipe binding."""

    def receive(self, maximum: int) -> bytes:
        """Receive at most ``maximum`` bytes."""

    def send(self, payload: bytes) -> None:
        """Send one encoded response."""

    def close(self) -> None:
        """Close the connection."""


class NamedPipeAcceptor(Protocol):
    """Accept local clients from a protected named pipe."""

    def accept(self) -> NamedPipeConnection:
        """Return the next local connection."""


class WindowsPeerIdentityProvider:
    """Project peer identity exclusively from an injected token provider."""

    def __init__(self, token_provider: WindowsTokenProvider) -> None:
        self._token_provider = token_provider

    def peer_identity(self, connection: object) -> PeerIdentity:
        token = self._token_provider.peer_token(connection)
        if not isinstance(token, WindowsPeerToken):
            raise TypeError("token provider returned an invalid peer token")
        return PeerIdentity(
            platform_id=f"windows-sid:{token.sid}",
            process_id=token.process_id,
        )


class WindowsCurrentGroupMembershipResolver:
    """Fail closed and re-check the caller's current groups per request."""

    _PREFIX = "windows-sid:"

    def __init__(self, group_provider: WindowsGroupProvider) -> None:
        self._group_provider = group_provider

    def is_current_member(self, identity: PeerIdentity, group_name: str) -> bool:
        if not isinstance(identity, PeerIdentity):
            raise TypeError("identity must be a PeerIdentity")
        group_name = require_group_name(group_name)
        if not identity.platform_id.startswith(self._PREFIX):
            return False
        sid = identity.platform_id.removeprefix(self._PREFIX)
        try:
            return self._group_provider.is_current_member(sid, group_name) is True
        except (OSError, RuntimeError):
            return False


class WindowsNamedPipeTransport:
    """Serve bounded requests over an injected protected named-pipe acceptor."""

    def __init__(
        self,
        acceptor: NamedPipeAcceptor,
        token_provider: WindowsTokenProvider,
        *,
        max_request_bytes: int,
    ) -> None:
        if (
            type(max_request_bytes) is not int
            or not 1_024 <= max_request_bytes <= 1_048_576
        ):
            raise ValueError("max_request_bytes is outside the supported bound")
        self._acceptor = acceptor
        self._identity_provider = WindowsPeerIdentityProvider(token_provider)
        self.max_request_bytes = max_request_bytes

    def serve_once(self, handler: ControlRequestHandler) -> None:
        connection = self._acceptor.accept()
        try:
            identity = self._identity_provider.peer_identity(connection)
            request = connection.receive(self.max_request_bytes + 1)
            if len(request) > self.max_request_bytes:
                raise OSError("named-pipe request exceeds configured bound")
            connection.send(handler.handle(request, identity))
        finally:
            connection.close()
