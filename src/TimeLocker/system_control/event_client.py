"""Reconnectable client for the dedicated local status-event socket."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import json
from pathlib import Path
import socket
from threading import Event

from .models import StatusEvent


DEFAULT_STATUS_EVENT_SOCKET_PATH = Path("/run/timelocker/status-events.sock")
DEFAULT_MAX_EVENT_BYTES = 1_048_576


class StatusEventAccessDenied(RuntimeError):
    """Raised when the protected backend denies an event subscription."""


class UnixSocketStatusEventClient:
    """Consume allowlisted events with bounded reconnect and frame handling."""

    def __init__(
        self,
        *,
        socket_path: Path = DEFAULT_STATUS_EVENT_SOCKET_PATH,
        heartbeat_timeout_seconds: float = 15.0,
        max_event_bytes: int = DEFAULT_MAX_EVENT_BYTES,
        base_retry_delay_seconds: float = 0.5,
        max_retry_delay_seconds: float = 30.0,
        connection_factory: Callable[[], socket.socket] | None = None,
    ) -> None:
        if (
            isinstance(heartbeat_timeout_seconds, bool)
            or not isinstance(heartbeat_timeout_seconds, (int, float))
            or not 0.25 <= heartbeat_timeout_seconds <= 600.0
        ):
            raise ValueError("heartbeat_timeout_seconds is outside the supported bound")
        if (
            type(max_event_bytes) is not int
            or not 1_024 <= max_event_bytes <= 16_777_216
        ):
            raise ValueError("max_event_bytes is outside the supported bound")
        if (
            isinstance(base_retry_delay_seconds, bool)
            or not isinstance(base_retry_delay_seconds, (int, float))
            or base_retry_delay_seconds <= 0
            or max_retry_delay_seconds < base_retry_delay_seconds
            or max_retry_delay_seconds > 300.0
        ):
            raise ValueError("retry delays are outside the supported bound")
        self.socket_path = socket_path
        self.heartbeat_timeout_seconds = float(heartbeat_timeout_seconds)
        self.max_event_bytes = max_event_bytes
        self.base_retry_delay_seconds = float(base_retry_delay_seconds)
        self.max_retry_delay_seconds = float(max_retry_delay_seconds)
        self._connection_factory = connection_factory

    def events(self, stop_event: Event) -> Iterator[StatusEvent]:
        """Yield events, reconnecting until shutdown without steady polling."""
        if not isinstance(stop_event, Event):
            raise TypeError("stop_event must be a threading.Event")
        retry_delay = self.base_retry_delay_seconds
        immediate_retry_available = False
        while not stop_event.is_set():
            connection: socket.socket | None = None
            try:
                connection = self._connect()
                for event in self._connected_events(connection, stop_event):
                    retry_delay = self.base_retry_delay_seconds
                    immediate_retry_available = True
                    yield event
                if stop_event.is_set():
                    return
            except StatusEventAccessDenied:
                raise
            except (OSError, TimeoutError, UnicodeDecodeError, ValueError):
                pass
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except OSError:
                        pass
            if immediate_retry_available:
                immediate_retry_available = False
                continue
            if stop_event.wait(retry_delay):
                return
            retry_delay = min(retry_delay * 2.0, self.max_retry_delay_seconds)

    def _connect(self) -> socket.socket:
        if self._connection_factory is not None:
            connection = self._connection_factory()
        else:
            if not hasattr(socket, "AF_UNIX"):
                raise OSError("Unix sockets are unavailable")
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            connection.connect(str(self.socket_path))
        connection.settimeout(self.heartbeat_timeout_seconds)
        return connection

    def _connected_events(
        self,
        connection: socket.socket,
        stop_event: Event,
    ) -> Iterator[StatusEvent]:
        buffer = b""
        while not stop_event.is_set():
            frame, buffer = self._receive_frame(connection, buffer)
            decoded = json.loads(frame.decode("utf-8"))
            if isinstance(decoded, dict) and decoded.get("status") == "denied":
                if set(decoded) != {"status", "safe_summary"}:
                    raise ValueError("invalid denial frame")
                raise StatusEventAccessDenied("System event access denied.")
            yield StatusEvent.from_mapping(decoded)

    def _receive_frame(
        self,
        connection: socket.socket,
        buffer: bytes,
    ) -> tuple[bytes, bytes]:
        while b"\n" not in buffer:
            remaining = self.max_event_bytes + 1 - len(buffer)
            if remaining <= 0:
                raise ValueError("event frame exceeds configured bound")
            chunk = connection.recv(min(65_536, remaining))
            if not chunk:
                raise OSError("status event connection closed")
            buffer += chunk
        frame, remainder = buffer.split(b"\n", 1)
        if not frame or len(frame) > self.max_event_bytes:
            raise ValueError("invalid event frame")
        return frame, remainder
