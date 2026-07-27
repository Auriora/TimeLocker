"""Windows system-control adapter contracts with injectable OS providers.

The concrete service and named-pipe implementation remain platform follow-up
work. These adapters keep identity and authorization derived from the pipe
token, never from request data, and are testable on non-Windows hosts.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from threading import Event
from typing import Protocol

from .interfaces import (
    ControlRequestHandler,
    GroupMembershipResolver,
    PeerIdentity,
    StatusEventBroker,
)
from .models import StatusEvent
from .status_events import StatusSubscriptionLimitError
from .types import StatusEventKind
from .validation import require_group_name, require_int, require_safe_identifier


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


class NamedPipeEventConnection(Protocol):
    """Injectable bounded send seam for a Windows event subscription."""

    def send_event(self, payload: bytes, timeout_seconds: float) -> None:
        """Send one event within the platform binding's timeout."""

    def close(self) -> None:
        """Close the event connection."""


class NamedPipeEventAcceptor(Protocol):
    """Accept local event subscribers from a protected named pipe."""

    def accept(self) -> NamedPipeEventConnection:
        """Return the next local event connection."""


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


class WindowsNamedPipeStatusEventTransport:
    """Testable Windows event contract; no live service implementation claim."""

    def __init__(
        self,
        acceptor: NamedPipeEventAcceptor,
        token_provider: WindowsTokenProvider,
        *,
        operator_group: str = "timelocker-operators",
        heartbeat_interval_seconds: float = 5.0,
        send_timeout_seconds: float = 2.0,
        max_frame_bytes: int = 1_048_576,
    ) -> None:
        if (
            isinstance(heartbeat_interval_seconds, bool)
            or not isinstance(heartbeat_interval_seconds, (int, float))
            or not 0.25 <= heartbeat_interval_seconds <= 300.0
        ):
            raise ValueError("heartbeat_interval_seconds is outside the supported bound")
        if (
            isinstance(send_timeout_seconds, bool)
            or not isinstance(send_timeout_seconds, (int, float))
            or not 0.1 <= send_timeout_seconds <= 60.0
        ):
            raise ValueError("send_timeout_seconds is outside the supported bound")
        self._acceptor = acceptor
        self._identity_provider = WindowsPeerIdentityProvider(token_provider)
        self.operator_group = require_group_name(operator_group)
        self.heartbeat_interval_seconds = float(heartbeat_interval_seconds)
        self.send_timeout_seconds = float(send_timeout_seconds)
        self.max_frame_bytes = require_int(
            max_frame_bytes,
            field="max_frame_bytes",
            minimum=1_024,
            maximum=16_777_216,
        )

    def serve_once(
        self,
        broker: StatusEventBroker,
        membership_resolver: GroupMembershipResolver,
        *,
        stop_event: Event | None = None,
    ) -> None:
        """Serve one injected connection with per-delivery authorization."""
        stop_event = stop_event or Event()
        connection = self._acceptor.accept()
        subscription = None
        try:
            try:
                identity = self._identity_provider.peer_identity(connection)
            except (OSError, RuntimeError, TypeError, ValueError):
                return
            if not self._authorized(identity, membership_resolver):
                self._send(
                    connection,
                    {
                        "status": "denied",
                        "safe_summary": "System access denied.",
                    },
                )
                return
            try:
                subscription = broker.subscribe()
            except StatusSubscriptionLimitError:
                return
            while not stop_event.is_set():
                event = subscription.next_event(self.heartbeat_interval_seconds)
                if not self._authorized(identity, membership_resolver):
                    return
                if event is None:
                    event = StatusEvent(
                        revision=broker.current_revision(),
                        kind=StatusEventKind.HEARTBEAT,
                    )
                self._send(connection, event.to_wire())
        finally:
            if subscription is not None:
                subscription.close()
            connection.close()

    def _send(
        self,
        connection: NamedPipeEventConnection,
        payload: dict[str, object],
    ) -> None:
        frame = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        if len(frame) > self.max_frame_bytes:
            raise OSError("named-pipe event exceeds configured bound")
        connection.send_event(frame, self.send_timeout_seconds)

    def _authorized(
        self,
        identity: PeerIdentity,
        membership_resolver: GroupMembershipResolver,
    ) -> bool:
        try:
            return membership_resolver.is_current_member(
                identity,
                self.operator_group,
            ) is True
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            return False
