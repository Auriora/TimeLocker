"""Event-driven tray snapshot refresh tests."""

from __future__ import annotations

from threading import Event
from uuid import UUID

from TimeLocker.system_control.client import SystemControlClientError
from TimeLocker.system_control.event_client import StatusEventAccessDenied
from TimeLocker.system_control.models import (
    StatusEvent,
    StatusRevision,
    StatusSnapshot,
)
from TimeLocker.system_control.tray_client import TrayStatusSubscriptionClient
from TimeLocker.system_control.types import (
    BackendStatus,
    ProtocolErrorCode,
    ResponseStatus,
    StatusEventKind,
)


SESSION_ONE = UUID("526719f9-4c46-42ac-b286-2623079bc335")
SESSION_TWO = UUID("eb53eaf9-42c5-45e2-b772-a3c6d7ace818")


def _snapshot(session_id: UUID, sequence: int) -> StatusSnapshot:
    return StatusSnapshot(
        revision=StatusRevision(session_id, sequence),
        backend_status=BackendStatus.AVAILABLE,
        active_operations=0,
    )


class _ControlClient:
    def __init__(self, snapshots: list[StatusSnapshot]) -> None:
        self.snapshots = iter(snapshots)
        self.calls = 0

    def get_status_snapshot(self) -> StatusSnapshot:
        self.calls += 1
        return next(self.snapshots)


class _EventClient:
    def __init__(self, events: list[StatusEvent]) -> None:
        self._events = events

    def events(self, _stop_event: Event):
        yield from self._events


def test_initial_gap_and_backend_restart_each_fetch_a_fresh_snapshot() -> None:
    events = [
        StatusEvent(
            StatusRevision(SESSION_ONE, 0),
            StatusEventKind.SNAPSHOT_REQUIRED,
        ),
        StatusEvent(StatusRevision(SESSION_ONE, 0), StatusEventKind.CHANGED),
        StatusEvent(StatusRevision(SESSION_ONE, 2), StatusEventKind.CHANGED),
        StatusEvent(StatusRevision(SESSION_ONE, 1), StatusEventKind.CHANGED),
        StatusEvent(StatusRevision(SESSION_ONE, 2), StatusEventKind.HEARTBEAT),
        StatusEvent(
            StatusRevision(SESSION_TWO, 0),
            StatusEventKind.SNAPSHOT_REQUIRED,
        ),
    ]
    control = _ControlClient(
        [
            _snapshot(SESSION_ONE, 0),
            _snapshot(SESSION_ONE, 2),
            _snapshot(SESSION_TWO, 0),
        ]
    )
    applied: list[StatusSnapshot] = []
    TrayStatusSubscriptionClient(
        control_client=control,
        event_client=_EventClient(events),
    ).serve(Event(), on_snapshot=applied.append)

    assert control.calls == 3
    assert [snapshot.revision for snapshot in applied] == [
        StatusRevision(SESSION_ONE, 0),
        StatusRevision(SESSION_ONE, 2),
        StatusRevision(SESSION_TWO, 0),
    ]


def test_older_snapshot_never_regresses_presentation() -> None:
    control = _ControlClient(
        [
            _snapshot(SESSION_ONE, 2),
            _snapshot(SESSION_ONE, 1),
        ]
    )
    applied: list[StatusSnapshot] = []
    TrayStatusSubscriptionClient(
        control_client=control,
        event_client=_EventClient(
            [
                StatusEvent(
                    StatusRevision(SESSION_ONE, 2),
                    StatusEventKind.SNAPSHOT_REQUIRED,
                ),
                StatusEvent(
                    StatusRevision(SESSION_ONE, 3),
                    StatusEventKind.CHANGED,
                ),
            ]
        ),
    ).serve(Event(), on_snapshot=applied.append)

    assert [snapshot.revision.sequence for snapshot in applied] == [2]


def test_denied_subscription_projects_only_safe_unavailable_state() -> None:
    class _DeniedClient:
        def events(self, _stop_event: Event):
            raise StatusEventAccessDenied("secret backend detail")
            yield

    unavailable: list[str] = []
    TrayStatusSubscriptionClient(
        control_client=_ControlClient([]),
        event_client=_DeniedClient(),
    ).serve(
        Event(),
        on_snapshot=lambda _snapshot: None,
        on_unavailable=unavailable.append,
    )
    assert unavailable == ["denied"]


def test_heartbeat_retries_initial_snapshot_only_while_not_current() -> None:
    class _RecoveringControl:
        def __init__(self) -> None:
            self.calls = 0

        def get_status_snapshot(self) -> StatusSnapshot:
            self.calls += 1
            if self.calls == 1:
                raise SystemControlClientError(
                    ProtocolErrorCode.SYSTEM_BACKEND_UNAVAILABLE,
                    "unavailable",
                    status=ResponseStatus.UNAVAILABLE,
                )
            return _snapshot(SESSION_ONE, 0)

    control = _RecoveringControl()
    applied: list[StatusSnapshot] = []
    unavailable: list[str] = []
    TrayStatusSubscriptionClient(
        control_client=control,
        event_client=_EventClient(
            [
                StatusEvent(
                    StatusRevision(SESSION_ONE, 0),
                    StatusEventKind.SNAPSHOT_REQUIRED,
                ),
                StatusEvent(
                    StatusRevision(SESSION_ONE, 0),
                    StatusEventKind.HEARTBEAT,
                ),
                StatusEvent(
                    StatusRevision(SESSION_ONE, 0),
                    StatusEventKind.HEARTBEAT,
                ),
            ]
        ),
    ).serve(
        Event(),
        on_snapshot=applied.append,
        on_unavailable=unavailable.append,
    )

    assert unavailable == ["unavailable"]
    assert control.calls == 2
    assert applied == [_snapshot(SESSION_ONE, 0)]
