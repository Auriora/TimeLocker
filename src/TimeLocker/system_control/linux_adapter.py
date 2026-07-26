"""Linux peer identity, NSS authorization, and Unix-socket transport adapters."""

from __future__ import annotations

import grp
import pwd
import socket
import struct
from threading import Event

from .interfaces import ControlRequestHandler, PeerIdentity
from .validation import require_group_name


class LinuxPeerIdentityProvider:
    """Derive PID and UID from kernel-owned Unix-socket peer credentials."""

    _CREDENTIAL_FORMAT = "3i"

    def peer_identity(self, connection: object) -> PeerIdentity:
        """Read Linux ``SO_PEERCRED``; never consult request content."""
        if not isinstance(connection, socket.socket):
            raise TypeError("connection must be a socket")
        credentials = connection.getsockopt(
            socket.SOL_SOCKET,
            socket.SO_PEERCRED,
            struct.calcsize(self._CREDENTIAL_FORMAT),
        )
        process_id, user_id, _group_id = struct.unpack(
            self._CREDENTIAL_FORMAT,
            credentials,
        )
        if user_id < 0:
            raise OSError("peer user identity is unavailable")
        return PeerIdentity(
            platform_id=f"linux-uid:{user_id}",
            process_id=process_id,
        )


class LinuxNssGroupMembershipResolver:
    """Resolve primary and supplementary membership from current NSS state."""

    _PREFIX = "linux-uid:"

    def is_current_member(self, identity: PeerIdentity, group_name: str) -> bool:
        """Re-read account and group databases for every protected request."""
        if not isinstance(identity, PeerIdentity):
            raise TypeError("identity must be a PeerIdentity")
        group_name = require_group_name(group_name)
        if not identity.platform_id.startswith(self._PREFIX):
            return False
        raw_user_id = identity.platform_id.removeprefix(self._PREFIX)
        if not raw_user_id.isascii() or not raw_user_id.isdecimal():
            return False
        try:
            account = pwd.getpwuid(int(raw_user_id))
            operator_group = grp.getgrnam(group_name)
        except KeyError:
            return False
        return (
            account.pw_gid == operator_group.gr_gid
            or account.pw_name in operator_group.gr_mem
        )


class LinuxUnixSocketTransport:
    """Serve one bounded request per local Unix-socket connection."""

    def __init__(
        self,
        listener: socket.socket,
        *,
        max_request_bytes: int,
        request_timeout_seconds: float = 5.0,
        stop_event: Event | None = None,
    ) -> None:
        if not isinstance(listener, socket.socket):
            raise TypeError("listener must be a socket")
        if listener.family != socket.AF_UNIX:
            raise ValueError("listener must be an AF_UNIX socket")
        if (
            type(max_request_bytes) is not int
            or not 1_024 <= max_request_bytes <= 1_048_576
        ):
            raise ValueError("max_request_bytes is outside the supported bound")
        if (
            isinstance(request_timeout_seconds, bool)
            or not isinstance(request_timeout_seconds, (int, float))
            or not 0.1 <= request_timeout_seconds <= 60.0
        ):
            raise ValueError("request_timeout_seconds is outside the supported bound")
        self.listener = listener
        self.max_request_bytes = max_request_bytes
        self.request_timeout_seconds = float(request_timeout_seconds)
        self.stop_event = stop_event or Event()
        self.identity_provider = LinuxPeerIdentityProvider()

    @classmethod
    def from_systemd(
        cls,
        *,
        max_request_bytes: int,
        descriptor: int = 3,
        request_timeout_seconds: float = 5.0,
        stop_event: Event | None = None,
    ) -> "LinuxUnixSocketTransport":
        """Adopt a systemd-activated listening socket without rebinding paths."""
        if type(descriptor) is not int or descriptor < 3:
            raise ValueError("descriptor must be a systemd-passed descriptor")
        listener = socket.fromfd(descriptor, socket.AF_UNIX, socket.SOCK_STREAM)
        if listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 1:
            listener.close()
            raise OSError("systemd descriptor is not a listening socket")
        return cls(
            listener,
            max_request_bytes=max_request_bytes,
            request_timeout_seconds=request_timeout_seconds,
            stop_event=stop_event,
        )

    def serve(self, handler: ControlRequestHandler) -> None:
        """Serve until stopped, isolating malformed clients to one connection."""
        while not self.stop_event.is_set():
            connection, _address = self.listener.accept()
            with connection:
                try:
                    self.serve_connection(connection, handler)
                except OSError:
                    continue

    def serve_connection(
        self,
        connection: socket.socket,
        handler: ControlRequestHandler,
    ) -> None:
        """Derive the peer, read one bounded frame, and return one response."""
        identity = self.identity_provider.peer_identity(connection)
        if hasattr(connection, "settimeout"):
            connection.settimeout(self.request_timeout_seconds)
        request = _receive_frame(connection, self.max_request_bytes)
        response = handler.handle(request, identity)
        connection.sendall(response)


def _receive_frame(connection: socket.socket, maximum: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while size <= maximum:
        try:
            chunk = connection.recv(min(65_536, maximum + 1 - size))
        except TimeoutError:
            return b""
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
        if b"\n" in chunk:
            break
    payload = b"".join(chunks)
    newline = payload.find(b"\n")
    if newline >= 0:
        payload = payload[:newline]
    return payload
