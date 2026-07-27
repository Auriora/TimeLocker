"""Focused contract tests for event-driven tray status models."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from itertools import permutations
from typing import cast
from uuid import UUID, uuid4

import pytest

from TimeLocker.system_control import (
    BackendStatus,
    OperationTrigger,
    OperationType,
    ResultCode,
    RunRecord,
    RunRecordView,
    RunState,
    StatusEvent,
    StatusEventBroker,
    StatusEventClient,
    StatusEventKind,
    StatusEventTransport,
    StatusRevision,
    StatusSnapshot,
    StatusSnapshotProvider,
)


BASE_TIME = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)
SESSION_ID = UUID("11111111-1111-4111-8111-111111111111")


def _run_view(
    *,
    operation: OperationType,
    state: RunState,
    started_at: datetime,
    completed_at: datetime | None,
    result_code: ResultCode,
    run_id: UUID | None = None,
) -> RunRecordView:
    return RunRecordView.from_record(
        RunRecord(
            run_id=run_id or uuid4(),
            operation=operation,
            trigger=OperationTrigger.SCHEDULED,
            target_id="production",
            started_at=started_at,
            completed_at=completed_at,
            state=state,
            result_code=result_code,
        )
    )


@pytest.mark.unit
def test_status_revision_round_trip_and_immutability() -> None:
    revision = StatusRevision.from_mapping(
        {"session_id": str(SESSION_ID), "sequence": 7}
    )

    assert revision.to_wire() == {"session_id": str(SESSION_ID), "sequence": 7}
    with pytest.raises(FrozenInstanceError):
        revision.sequence = 8  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"session_id": str(SESSION_ID)},
        {"session_id": str(SESSION_ID), "sequence": True},
        {"session_id": str(SESSION_ID), "sequence": 1, "extra": "field"},
    ],
)
def test_status_revision_rejects_missing_unknown_and_bool_sequence(
    payload: dict[str, object]
) -> None:
    with pytest.raises((TypeError, ValueError)):
        StatusRevision.from_mapping(payload)


@pytest.mark.unit
def test_status_event_round_trips_and_rejects_unsupported_versions() -> None:
    event = StatusEvent.from_mapping(
        {
            "schema_version": 1,
            "protocol_version": 1,
            "revision": {"session_id": str(SESSION_ID), "sequence": 3},
            "kind": "changed",
        }
    )

    assert event.to_wire()["kind"] == "changed"
    assert event.revision.is_strictly_newer_than(
        StatusRevision(SESSION_ID, 2)
    ) is True

    for invalid in (
        {
            "schema_version": 2,
            "protocol_version": 1,
            "revision": {"session_id": str(SESSION_ID), "sequence": 3},
            "kind": "changed",
        },
        {
            "schema_version": 1,
            "protocol_version": 2,
            "revision": {"session_id": str(SESSION_ID), "sequence": 3},
            "kind": "changed",
        },
        {
            "schema_version": 1,
            "protocol_version": 1,
            "revision": {"session_id": str(SESSION_ID), "sequence": 3},
            "kind": "changed",
            "secret": "nope",
        },
    ):
        with pytest.raises((TypeError, ValueError)):
            StatusEvent.from_mapping(invalid)


@pytest.mark.unit
def test_status_snapshot_round_trip_and_rejects_mismatched_run_operations() -> None:
    latest_backup = _run_view(
        operation=OperationType.BACKUP,
        state=RunState.FAILED,
        started_at=BASE_TIME,
        completed_at=BASE_TIME + timedelta(minutes=5),
        result_code=ResultCode.OPERATION_FAILED,
        run_id=UUID("22222222-2222-4222-8222-222222222222"),
    )
    snapshot = StatusSnapshot.from_mapping(
        {
            "revision": {"session_id": str(SESSION_ID), "sequence": 4},
            "backend_status": "available",
            "active_operations": 1,
            "latest_backup": latest_backup.to_wire(),
            "last_successful_backup_completed_at": None,
            "latest_retention": None,
            "next_backup_at": (BASE_TIME + timedelta(hours=1)).isoformat(),
            "next_retention_at": None,
        }
    )

    assert snapshot.to_wire()["backend_status"] == "available"
    assert snapshot.latest_backup == latest_backup

    invalid_snapshot = snapshot.to_wire()
    invalid_snapshot["latest_backup"] = _run_view(
        operation=OperationType.RETENTION,
        state=RunState.SUCCEEDED,
        started_at=BASE_TIME,
        completed_at=BASE_TIME + timedelta(minutes=5),
        result_code=ResultCode.RETENTION_SUCCEEDED,
    ).to_wire()
    with pytest.raises(ValueError, match="latest_backup"):
        StatusSnapshot.from_mapping(invalid_snapshot)


@pytest.mark.unit
def test_status_snapshot_rejects_unknown_fields_and_bool_as_active_operations() -> None:
    payload = {
        "revision": {"session_id": str(SESSION_ID), "sequence": 1},
        "backend_status": "available",
        "active_operations": True,
        "latest_backup": None,
        "last_successful_backup_completed_at": None,
        "latest_retention": None,
        "next_backup_at": None,
        "next_retention_at": None,
    }
    with pytest.raises((TypeError, ValueError)):
        StatusSnapshot.from_mapping(payload)

    payload["active_operations"] = 0
    payload["raw_output"] = "secret"
    with pytest.raises(ValueError, match="unknown fields"):
        StatusSnapshot.from_mapping(payload)


@pytest.mark.unit
def test_status_snapshot_builder_selects_latest_attempts_and_max_success_across_permutations() -> None:
    successful_backup = _run_view(
        operation=OperationType.BACKUP,
        state=RunState.SUCCEEDED,
        started_at=BASE_TIME - timedelta(hours=3),
        completed_at=BASE_TIME - timedelta(hours=2, minutes=55),
        result_code=ResultCode.BACKUP_SUCCEEDED,
        run_id=UUID("33333333-3333-4333-8333-333333333333"),
    )
    newer_failed_backup = _run_view(
        operation=OperationType.BACKUP,
        state=RunState.FAILED,
        started_at=BASE_TIME - timedelta(minutes=20),
        completed_at=BASE_TIME - timedelta(minutes=15),
        result_code=ResultCode.OPERATION_FAILED,
        run_id=UUID("44444444-4444-4444-8444-444444444444"),
    )
    newer_successful_backup = _run_view(
        operation=OperationType.BACKUP,
        state=RunState.SUCCEEDED,
        started_at=BASE_TIME - timedelta(hours=1),
        completed_at=BASE_TIME - timedelta(minutes=30),
        result_code=ResultCode.BACKUP_SUCCEEDED,
        run_id=UUID("55555555-5555-4555-8555-555555555555"),
    )
    latest_retention = _run_view(
        operation=OperationType.RETENTION,
        state=RunState.SUCCEEDED,
        started_at=BASE_TIME - timedelta(minutes=10),
        completed_at=BASE_TIME - timedelta(minutes=5),
        result_code=ResultCode.RETENTION_SUCCEEDED,
        run_id=UUID("66666666-6666-4666-8666-666666666666"),
    )

    for history in permutations(
        (
            successful_backup,
            newer_failed_backup,
            newer_successful_backup,
            latest_retention,
        )
    ):
        snapshot = StatusSnapshot.from_run_history(
            revision=StatusRevision(SESSION_ID, 9),
            backend_status=BackendStatus.AVAILABLE,
            active_operations=1,
            runs=history,
            next_backup_at=BASE_TIME + timedelta(hours=2),
            next_retention_at=BASE_TIME + timedelta(hours=3),
        )
        assert snapshot.latest_backup == newer_failed_backup
        assert snapshot.latest_retention == latest_retention
        assert (
            snapshot.last_successful_backup_completed_at
            == newer_successful_backup.completed_at
        )


@pytest.mark.unit
def test_status_snapshot_builder_returns_none_when_no_successful_backup_exists() -> None:
    snapshot = StatusSnapshot.from_run_history(
        revision=StatusRevision(SESSION_ID, 2),
        backend_status=BackendStatus.UNAVAILABLE,
        active_operations=0,
        runs=(
            _run_view(
                operation=OperationType.BACKUP,
                state=RunState.FAILED,
                started_at=BASE_TIME,
                completed_at=BASE_TIME + timedelta(minutes=1),
                result_code=ResultCode.OPERATION_FAILED,
            ),
            _run_view(
                operation=OperationType.RETENTION,
                state=RunState.SUCCEEDED,
                started_at=BASE_TIME - timedelta(minutes=5),
                completed_at=BASE_TIME - timedelta(minutes=1),
                result_code=ResultCode.RETENTION_SUCCEEDED,
            ),
        ),
    )

    assert snapshot.last_successful_backup_completed_at is None
    assert snapshot.latest_backup is not None


@pytest.mark.unit
def test_status_revision_ordering_is_strict_within_a_session() -> None:
    applied = StatusRevision(SESSION_ID, 5)
    duplicate = StatusRevision(SESSION_ID, 5)
    newer = StatusRevision(SESSION_ID, 6)
    older = StatusRevision(SESSION_ID, 4)
    other_session = StatusRevision(
        UUID("77777777-7777-4777-8777-777777777777"),
        1,
    )

    assert duplicate.is_strictly_newer_than(applied) is False
    assert older.is_strictly_newer_than(applied) is False
    assert newer.is_strictly_newer_than(applied) is True
    assert other_session.is_strictly_newer_than(applied) is False


@pytest.mark.unit
def test_status_protocol_interfaces_remain_platform_neutral_contracts() -> None:
    snapshot = StatusSnapshot.from_run_history(
        revision=StatusRevision(SESSION_ID, 1),
        backend_status=BackendStatus.AVAILABLE,
        active_operations=0,
        runs=(),
    )
    event = StatusEvent(
        revision=StatusRevision(SESSION_ID, 1),
        kind=StatusEventKind.SNAPSHOT_REQUIRED,
    )

    class FakeProvider:
        def snapshot(self) -> StatusSnapshot:
            return snapshot

    class FakeBroker:
        def current_revision(self) -> StatusRevision:
            return snapshot.revision

        def publish_change(self, kind: StatusEventKind) -> StatusRevision:
            assert kind is StatusEventKind.CHANGED
            return StatusRevision(SESSION_ID, 2)

        def subscribe(self):
            return FakeSubscription()

    class FakeSubscription:
        def next_event(self, timeout_seconds: float | None = None):
            del timeout_seconds
            return event

        def close(self) -> None:
            return None

    class FakeTransport:
        def serve(self, broker, identity_provider, membership_resolver) -> None:
            assert broker.current_revision() == snapshot.revision

    class FakeClient:
        def events(self, stop_event: object):
            del stop_event
            yield event

    provider = cast(StatusSnapshotProvider, FakeProvider())
    broker = cast(StatusEventBroker, FakeBroker())
    transport = cast(StatusEventTransport, FakeTransport())
    client = cast(StatusEventClient, FakeClient())

    assert provider.snapshot() == snapshot
    assert broker.publish_change(StatusEventKind.CHANGED).sequence == 2
    assert broker.subscribe().next_event() == event
    transport.serve(broker, object(), object())
    assert list(client.events(object())) == [event]
