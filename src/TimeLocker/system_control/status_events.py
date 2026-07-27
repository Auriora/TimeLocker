"""Bounded in-memory status revisions, subscriptions, and change sources."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterator
from enum import StrEnum
from threading import Condition, Event, RLock
from typing import Protocol, TypeVar
from uuid import UUID, uuid4

from .models import StatusEvent, StatusRevision
from .types import StatusEventKind
from .validation import MAX_COUNTER_VALUE, require_int, require_uuid


_Snapshot = TypeVar("_Snapshot")


class StatusSubscriptionLimitError(RuntimeError):
    """Raised when the configured subscriber bound has been reached."""


class StatusWatchSignal(StrEnum):
    """Sanitized watcher observations; uncertainty requires full resync."""

    CHANGED = "changed"
    UNCERTAIN = "uncertain"


class ProtectedStateWatcher(Protocol):
    """Injectable platform watcher for protected record or schedule changes."""

    def events(self, stop_event: Event) -> Iterator[StatusWatchSignal]:
        """Yield bounded change signals until shutdown."""


class BoundedStatusSubscription:
    """One subscriber retaining at most the newest pending event."""

    def __init__(self, close_callback: Callable[[], None]) -> None:
        self._condition = Condition()
        self._events: deque[StatusEvent] = deque(maxlen=1)
        self._closed = False
        self._close_callback = close_callback

    def next_event(self, timeout_seconds: float | None = None) -> StatusEvent | None:
        """Return the next event, or None after timeout or closure."""
        if timeout_seconds is not None and (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
            or timeout_seconds > 3_600
        ):
            raise ValueError("timeout_seconds must be between zero and 3600")
        with self._condition:
            if not self._events and not self._closed:
                self._condition.wait(timeout_seconds)
            if self._events:
                return self._events.popleft()
            return None

    def close(self) -> None:
        """Close once and unregister from the owning broker."""
        callback: Callable[[], None] | None = None
        with self._condition:
            if not self._closed:
                self._closed = True
                self._events.clear()
                self._condition.notify_all()
                callback = self._close_callback
        if callback is not None:
            callback()

    def _offer(self, event: StatusEvent) -> None:
        with self._condition:
            if self._closed:
                return
            self._events.append(event)
            self._condition.notify()


class BoundedStatusEventBroker:
    """Thread-safe session revisions with one pending event per subscriber."""

    def __init__(
        self,
        *,
        session_id: UUID | None = None,
        max_subscribers: int = 32,
    ) -> None:
        self._lock = RLock()
        self._session_id = require_uuid(
            session_id or uuid4(),
            field="session_id",
        )
        self._sequence = 0
        self._max_subscribers = require_int(
            max_subscribers,
            field="max_subscribers",
            minimum=1,
            maximum=256,
        )
        self._subscriptions: dict[UUID, BoundedStatusSubscription] = {}

    def current_revision(self) -> StatusRevision:
        """Return the current immutable backend-session revision."""
        with self._lock:
            return StatusRevision(self._session_id, self._sequence)

    def publish_change(
        self,
        kind: StatusEventKind = StatusEventKind.CHANGED,
    ) -> StatusRevision:
        """Advance once and coalesce the newest invalidation per subscriber."""
        if kind not in {
            StatusEventKind.CHANGED,
            StatusEventKind.RESYNC_REQUIRED,
        }:
            raise ValueError("published changes must invalidate or require resync")
        with self._lock:
            if self._sequence >= MAX_COUNTER_VALUE:
                raise RuntimeError("status revision sequence is exhausted")
            self._sequence += 1
            revision = StatusRevision(self._session_id, self._sequence)
            event = StatusEvent(revision=revision, kind=kind)
            for subscription in tuple(self._subscriptions.values()):
                subscription._offer(event)
            return revision

    def subscribe(self) -> BoundedStatusSubscription:
        """Register one bounded subscriber and enqueue its initial refresh."""
        with self._lock:
            if len(self._subscriptions) >= self._max_subscribers:
                raise StatusSubscriptionLimitError(
                    "status subscriber limit has been reached"
                )
            subscription_id = uuid4()
            subscription = BoundedStatusSubscription(
                lambda: self._unsubscribe(subscription_id)
            )
            self._subscriptions[subscription_id] = subscription
            subscription._offer(
                StatusEvent(
                    revision=StatusRevision(self._session_id, self._sequence),
                    kind=StatusEventKind.SNAPSHOT_REQUIRED,
                )
            )
            return subscription

    def _unsubscribe(self, subscription_id: UUID) -> None:
        with self._lock:
            self._subscriptions.pop(subscription_id, None)


class StatusChangeCoordinator:
    """Synchronize snapshot revisions with explicit and watched changes."""

    def __init__(self, broker: BoundedStatusEventBroker) -> None:
        if not isinstance(broker, BoundedStatusEventBroker):
            raise TypeError("broker must be a BoundedStatusEventBroker")
        self.broker = broker
        self._boundary = RLock()

    def snapshot(self, builder: Callable[[StatusRevision], _Snapshot]) -> _Snapshot:
        """Build state and its revision under one publication boundary."""
        if not callable(builder):
            raise TypeError("builder must be callable")
        with self._boundary:
            return builder(self.broker.current_revision())

    def run_changed(self) -> StatusRevision:
        """Publish after a durable run mutation."""
        return self._publish(StatusEventKind.CHANGED)

    def schedule_changed(self) -> StatusRevision:
        """Publish after a TimeLocker-managed schedule mutation."""
        return self._publish(StatusEventKind.CHANGED)

    def watcher_changed(self, *, uncertain: bool = False) -> StatusRevision:
        """Publish a watcher observation, forcing resync after uncertainty."""
        return self._publish(
            StatusEventKind.RESYNC_REQUIRED
            if uncertain
            else StatusEventKind.CHANGED
        )

    def _publish(self, kind: StatusEventKind) -> StatusRevision:
        with self._boundary:
            return self.broker.publish_change(kind)


class ProtectedStateChangeMonitor:
    """Translate injected watcher signals into safe broker invalidations."""

    def __init__(
        self,
        watcher: ProtectedStateWatcher,
        coordinator: StatusChangeCoordinator,
    ) -> None:
        if not hasattr(watcher, "events"):
            raise TypeError("watcher must provide events(stop_event)")
        if not isinstance(coordinator, StatusChangeCoordinator):
            raise TypeError("coordinator must be a StatusChangeCoordinator")
        self.watcher = watcher
        self.coordinator = coordinator

    def run(self, stop_event: Event) -> None:
        """Publish sanitized changes until the watcher or caller stops."""
        if not isinstance(stop_event, Event):
            raise TypeError("stop_event must be a threading.Event")
        try:
            for signal in self.watcher.events(stop_event):
                if stop_event.is_set():
                    return
                if signal is StatusWatchSignal.CHANGED:
                    self.coordinator.watcher_changed()
                elif signal is StatusWatchSignal.UNCERTAIN:
                    self.coordinator.watcher_changed(uncertain=True)
                else:
                    self.coordinator.watcher_changed(uncertain=True)
        except Exception:
            if not stop_event.is_set():
                self.coordinator.watcher_changed(uncertain=True)
