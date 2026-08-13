"""Authorized backend snapshot action tests for Spec 010 T002."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from TimeLocker.system_control import (
    LocalControlDispatcher,
    PeerIdentity,
    RequestEnvelope,
    RunRecord,
    ScheduleSummary,
    StatusSnapshot,
    SystemAction,
    SystemPolicy,
)
from TimeLocker.system_control.backend_entry import (
    FailClosedBackupMutationAdapter,
    FailClosedRetentionAdapter,
    FailClosedRetentionPlanProvider,
    StaticScheduleSummaryProvider,
    _build_handlers,
)
from TimeLocker.system_control.storage import AtomicRecordStore, RepositoryMutationLock
from TimeLocker.system_control.types import (
    OperationTrigger,
    OperationType,
    ResultCode,
    RunState,
)


NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)


class Membership:
    """Explicit current-membership test double."""

    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed

    def is_current_member(
        self,
        _identity: PeerIdentity,
        _group_name: str,
    ) -> bool:
        return self.allowed


class AuditSink:
    """Discard safe audit records in focused dispatcher tests."""

    def record(self, _event: object) -> None:
        return None


def _run(
    run_id: str,
    *,
    state: RunState,
    started_at: datetime,
    completed_at: datetime | None,
    result_code: ResultCode,
) -> RunRecord:
    return RunRecord(
        run_id=UUID(run_id),
        operation=OperationType.BACKUP,
        trigger=OperationTrigger.SCHEDULED,
        target_id="production",
        started_at=started_at,
        completed_at=completed_at,
        state=state,
        result_code=result_code,
    )


def _handlers(tmp_path: Path):
    store = AtomicRecordStore(tmp_path / "records")
    store.create_run(
        _run(
            "11111111-1111-4111-8111-111111111111",
            state=RunState.SUCCEEDED,
            started_at=NOW - timedelta(hours=2),
            completed_at=NOW - timedelta(hours=1, minutes=50),
            result_code=ResultCode.BACKUP_SUCCEEDED,
        )
    )
    store.create_run(
        _run(
            "22222222-2222-4222-8222-222222222222",
            state=RunState.RUNNING,
            started_at=NOW - timedelta(minutes=5),
            completed_at=None,
            result_code=ResultCode.OPERATION_RUNNING,
        )
    )
    handlers = _build_handlers(
        policy=SystemPolicy(),
        store=store,
        locks=RepositoryMutationLock(tmp_path / "locks"),
        backup_adapter=FailClosedBackupMutationAdapter(),
        retention_adapter=FailClosedRetentionAdapter(),
        retention_plan_provider=FailClosedRetentionPlanProvider(),
        schedule_summary_provider=StaticScheduleSummaryProvider(
            ScheduleSummary(
                next_backup_at=NOW + timedelta(hours=1),
                next_retention_at=None,
            )
        ),
        trigger_root=tmp_path / "triggers",
        clock=lambda: NOW,
    )
    return handlers


@pytest.mark.unit
def test_backend_snapshot_is_coherent_safe_and_preserves_last_success(
    tmp_path: Path,
) -> None:
    handlers = _handlers(tmp_path)
    request = RequestEnvelope(
        request_id=UUID("33333333-3333-4333-8333-333333333333"),
        action=SystemAction.STATUS_SNAPSHOT,
        parameters={},
    )

    first = StatusSnapshot.from_mapping(
        handlers[SystemAction.STATUS_SNAPSHOT](request)
    )
    second = StatusSnapshot.from_mapping(
        handlers[SystemAction.STATUS_SNAPSHOT](request)
    )

    assert first.revision == second.revision
    assert first.active_operations == 1
    assert first.latest_backup is not None
    assert first.latest_backup.state is RunState.RUNNING
    assert first.last_successful_backup_completed_at == NOW - timedelta(
        hours=1,
        minutes=50,
    )
    assert first.next_backup_at == NOW + timedelta(hours=1)


@pytest.mark.unit
@pytest.mark.security
def test_unauthorized_snapshot_receives_only_safe_denial(tmp_path: Path) -> None:
    dispatcher = LocalControlDispatcher(
        policy=SystemPolicy(),
        membership_resolver=Membership(False),
        handlers=_handlers(tmp_path),
        audit_sink=AuditSink(),
    )
    request = {
        "protocol_version": 2,
        "request_id": "44444444-4444-4444-8444-444444444444",
        "action": "status.snapshot",
        "parameters": {},
    }

    response = json.loads(
        dispatcher.handle(
            json.dumps(request).encode("utf-8"),
            PeerIdentity("linux-uid:1000"),
        )
    )

    assert response["status"] == "denied"
    assert response["error_code"] == "system_access_denied"
    assert response["result"] is None
    assert "revision" not in response
    assert "latest_backup" not in response
