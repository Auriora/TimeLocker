"""Bounded broker, change-source, and watcher tests for Spec 010 T003."""

from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from uuid import UUID

import pytest

from TimeLocker.system_control import (
    BoundedStatusEventBroker,
    ProtectedStateChangeMonitor,
    StatusChangeCoordinator,
    StatusEventKind,
    StatusSubscriptionLimitError,
    StatusWatchSignal,
)
from TimeLocker.system_control.models import RunRecord, RunTransition
from TimeLocker.system_control.storage import AtomicRecordStore
from TimeLocker.system_control.types import (
    OperationTrigger,
    OperationType,
    ResultCode,
    RunState,
)


SESSION_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
NOW = datetime(2026, 7, 27, 14, 0, tzinfo=UTC)


@pytest.mark.unit
def test_broker_revisions_are_monotonic_and_pending_changes_coalesce() -> None:
    broker = BoundedStatusEventBroker(session_id=SESSION_ID)
    subscription = broker.subscribe()

    initial = subscription.next_event(0.1)
    assert initial is not None
    assert initial.kind is StatusEventKind.SNAPSHOT_REQUIRED
    assert initial.revision.sequence == 0

    for expected in range(1, 11):
        assert broker.publish_change().sequence == expected

    newest = subscription.next_event(0.1)
    assert newest is not None
    assert newest.kind is StatusEventKind.CHANGED
    assert newest.revision.sequence == 10
    assert subscription.next_event(0.01) is None


@pytest.mark.unit
def test_broker_bounds_subscribers_and_close_releases_capacity() -> None:
    broker = BoundedStatusEventBroker(max_subscribers=1)
    first = broker.subscribe()

    with pytest.raises(StatusSubscriptionLimitError):
        broker.subscribe()

    first.close()
    replacement = broker.subscribe()
    assert replacement.next_event(0.1) is not None


@pytest.mark.unit
def test_new_broker_session_forces_snapshot_required() -> None:
    first = BoundedStatusEventBroker(
        session_id=UUID("11111111-1111-4111-8111-111111111111")
    ).subscribe()
    second = BoundedStatusEventBroker(
        session_id=UUID("22222222-2222-4222-8222-222222222222")
    ).subscribe()

    first_event = first.next_event(0.1)
    second_event = second.next_event(0.1)
    assert first_event is not None
    assert second_event is not None
    assert first_event.revision.session_id != second_event.revision.session_id
    assert second_event.kind is StatusEventKind.SNAPSHOT_REQUIRED


@pytest.mark.unit
def test_snapshot_boundary_prevents_newer_revision_with_older_state() -> None:
    broker = BoundedStatusEventBroker(session_id=SESSION_ID)
    coordinator = StatusChangeCoordinator(broker)
    builder_entered = Event()
    allow_builder_to_finish = Event()
    published = Event()
    snapshot_revision = []

    def build(revision):
        snapshot_revision.append(revision)
        builder_entered.set()
        assert allow_builder_to_finish.wait(1)
        return revision

    snapshot_thread = Thread(target=lambda: coordinator.snapshot(build))
    publish_thread = Thread(
        target=lambda: (
            coordinator.run_changed(),
            published.set(),
        )
    )
    snapshot_thread.start()
    assert builder_entered.wait(1)
    publish_thread.start()

    assert published.wait(0.05) is False
    allow_builder_to_finish.set()
    snapshot_thread.join(1)
    publish_thread.join(1)

    assert snapshot_revision[0].sequence == 0
    assert broker.current_revision().sequence == 1
    assert published.is_set()


@pytest.mark.unit
def test_watcher_uncertainty_forces_resynchronization() -> None:
    class Watcher:
        def events(self, _stop_event: Event):
            yield StatusWatchSignal.CHANGED
            yield StatusWatchSignal.UNCERTAIN

    broker = BoundedStatusEventBroker(session_id=SESSION_ID)
    subscription = broker.subscribe()
    subscription.next_event(0.1)
    monitor = ProtectedStateChangeMonitor(
        Watcher(),
        StatusChangeCoordinator(broker),
    )

    monitor.run(Event())

    event = subscription.next_event(0.1)
    assert event is not None
    assert event.kind is StatusEventKind.RESYNC_REQUIRED
    assert event.revision.sequence == 2


@pytest.mark.unit
def test_watcher_failure_forces_resynchronization() -> None:
    class FailingWatcher:
        def events(self, _stop_event: Event):
            yield StatusWatchSignal.CHANGED
            raise OSError("watch overflow")

    broker = BoundedStatusEventBroker(session_id=SESSION_ID)
    subscription = broker.subscribe()
    subscription.next_event(0.1)

    ProtectedStateChangeMonitor(
        FailingWatcher(),
        StatusChangeCoordinator(broker),
    ).run(Event())

    event = subscription.next_event(0.1)
    assert event is not None
    assert event.kind is StatusEventKind.RESYNC_REQUIRED
    assert event.revision.sequence == 2


@pytest.mark.unit
def test_durable_run_mutations_publish_without_becoming_failure_dependencies(
    tmp_path: Path,
) -> None:
    broker = BoundedStatusEventBroker(session_id=SESSION_ID)
    coordinator = StatusChangeCoordinator(broker)
    store = AtomicRecordStore(
        tmp_path / "records",
        status_change_callback=coordinator.run_changed,
    )
    record = RunRecord(
        run_id=UUID("33333333-3333-4333-8333-333333333333"),
        operation=OperationType.BACKUP,
        trigger=OperationTrigger.SCHEDULED,
        target_id="production",
        started_at=NOW,
        state=RunState.RUNNING,
        result_code=ResultCode.OPERATION_RUNNING,
    )

    store.create_run(record)
    store.transition(
        record.run_id,
        RunTransition(
            expected_states=frozenset({RunState.RUNNING}),
            new_state=RunState.SUCCEEDED,
            result_code=ResultCode.BACKUP_SUCCEEDED,
            completed_at=NOW,
        ),
    )
    assert broker.current_revision().sequence == 2

    failing_store = AtomicRecordStore(
        tmp_path / "failing-records",
        status_change_callback=lambda: (_ for _ in ()).throw(RuntimeError("down")),
    )
    failing_store.create_run(
        RunRecord(
            run_id=UUID("44444444-4444-4444-8444-444444444444"),
            operation=OperationType.RETENTION,
            trigger=OperationTrigger.SCHEDULED,
            target_id="production",
            started_at=NOW,
            state=RunState.RUNNING,
            result_code=ResultCode.OPERATION_RUNNING,
        )
    )
    assert len(failing_store.list_status_runs()) == 1


@pytest.mark.unit
def test_schedule_change_seam_advances_the_same_revision() -> None:
    broker = BoundedStatusEventBroker(session_id=SESSION_ID)
    coordinator = StatusChangeCoordinator(broker)

    assert coordinator.schedule_changed().sequence == 1
