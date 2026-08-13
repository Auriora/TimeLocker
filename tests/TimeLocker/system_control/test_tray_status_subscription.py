"""Daemonless tray status snapshot observation tests."""

from __future__ import annotations

from threading import Event
from uuid import UUID

from TimeLocker.system_control.models import StatusRevision, StatusSnapshot
from TimeLocker.system_control.status_snapshot import StatusSnapshotUnavailable
from TimeLocker.system_control.tray_client import TrayStatusSubscriptionClient
from TimeLocker.system_control.types import BackendStatus


SESSION_ONE = UUID("526719f9-4c46-42ac-b286-2623079bc335")
SESSION_TWO = UUID("eb53eaf9-42c5-45e2-b772-a3c6d7ace818")


def _snapshot(session_id: UUID, sequence: int) -> StatusSnapshot:
    return StatusSnapshot(
        revision=StatusRevision(session_id, sequence),
        backend_status=BackendStatus.AVAILABLE,
        active_operations=0,
    )


class _Watcher:
    def __init__(self, snapshots: list[StatusSnapshot]) -> None:
        self._snapshots = snapshots

    def snapshots(self, _stop_event: Event):
        yield from self._snapshots


def test_initial_snapshot_and_direct_changes_are_applied() -> None:
    applied: list[StatusSnapshot] = []
    TrayStatusSubscriptionClient(
        watcher=_Watcher(
            [
                _snapshot(SESSION_ONE, 0),
                _snapshot(SESSION_ONE, 1),
                _snapshot(SESSION_TWO, 0),
            ]
        )
    ).serve(Event(), on_snapshot=applied.append)

    assert [snapshot.revision for snapshot in applied] == [
        StatusRevision(SESSION_ONE, 0),
        StatusRevision(SESSION_ONE, 1),
        StatusRevision(SESSION_TWO, 0),
    ]


def test_duplicate_and_older_same_session_snapshots_do_not_regress() -> None:
    applied: list[StatusSnapshot] = []
    TrayStatusSubscriptionClient(
        watcher=_Watcher(
            [
                _snapshot(SESSION_ONE, 2),
                _snapshot(SESSION_ONE, 2),
                _snapshot(SESSION_ONE, 1),
            ]
        )
    ).serve(Event(), on_snapshot=applied.append)

    assert [snapshot.revision.sequence for snapshot in applied] == [2]


def test_untrusted_or_unavailable_status_file_projects_safe_state_once() -> None:
    class _UnavailableWatcher:
        def snapshots(self, _stop_event: Event):
            raise StatusSnapshotUnavailable("secret path")
            yield

    unavailable: list[str] = []
    TrayStatusSubscriptionClient(watcher=_UnavailableWatcher()).serve(
        Event(),
        on_snapshot=lambda _snapshot: None,
        on_unavailable=unavailable.append,
    )

    assert unavailable == ["unavailable"]


def test_pre_stopped_subscription_does_not_apply_snapshot() -> None:
    stop = Event()
    stop.set()
    applied: list[StatusSnapshot] = []
    TrayStatusSubscriptionClient(
        watcher=_Watcher([_snapshot(SESSION_ONE, 0)])
    ).serve(stop, on_snapshot=applied.append)

    assert applied == []
