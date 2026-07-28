"""Focused tests for the stand-alone tray service client."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pytest import mark
import pytest

from TimeLocker.system_control.client import (
    ProtocolErrorCode,
    ResponseStatus,
    SystemControlClientError,
)
from TimeLocker.system_control.models import (
    BackupActionRequest,
    RunQuery,
    RunRecord,
    RunRecordView,
    RetentionActionRequest,
    ScheduleSummary,
    StatusRevision,
    StatusSnapshot,
)
from TimeLocker.system_control.models import OperationTrigger
from TimeLocker.system_control.types import (
    BackendStatus,
    BackupScheduleHealth,
    OperationType as BackendOperationType,
    ResultCode,
    RunState,
)
from TimeLocker.system_control.tray_client import TrayControlClient


class FakeBackend:
    def __init__(
        self, runs, summary, status_error=None, backup_error=None, retention_error=None
    ):
        self.runs = runs
        self.summary = summary
        self.status_error = status_error
        self.backup_error = backup_error
        self.retention_error = retention_error
        self.requests = []

    def list_runs(self, query: RunQuery):
        self.requests.append(("list_runs", query))
        if self.status_error:
            raise self.status_error
        return self.runs

    def list_diagnostics(self, query):
        raise AssertionError("not expected")

    def get_run(self, run_id):
        raise AssertionError("not expected")

    def get_schedule_summary(self):
        self.requests.append(("get_schedule_summary", None))
        if self.status_error:
            raise self.status_error
        return self.summary

    def get_status_snapshot(self):
        self.requests.append(("get_status_snapshot", None))
        if self.status_error:
            raise self.status_error
        return StatusSnapshot.from_run_history(
            revision=StatusRevision(
                UUID("244e6660-95ae-4cb0-b159-704356ab6700"),
                1,
            ),
            backend_status=BackendStatus.AVAILABLE,
            active_operations=sum(
                run.state in {RunState.QUEUED, RunState.RUNNING}
                for run in self.runs
            ),
            runs=self.runs,
            next_backup_at=self.summary.next_backup_at,
            next_retention_at=self.summary.next_retention_at,
        )

    def request_backup(self, request: BackupActionRequest):
        self.requests.append(("request_backup", request))
        if self.backup_error:
            raise self.backup_error
        return None

    def request_retention(self, request: RetentionActionRequest):
        self.requests.append(("request_retention", request))
        if self.retention_error:
            raise self.retention_error
        return None


@mark.unit
@pytest.mark.parametrize(
    ("schedule_health", "expected_health", "expected_status"),
    (
        (BackupScheduleHealth.HEALTHY, "Healthy", "warning"),
        (BackupScheduleHealth.MISSED, "Backup missed", "error"),
        (BackupScheduleHealth.DISABLED, "Schedule disabled", "warning"),
        (BackupScheduleHealth.UNAVAILABLE, "Schedule unavailable", "warning"),
    ),
)
def test_schedule_health_is_kept_separate_from_activity(
    schedule_health: BackupScheduleHealth,
    expected_health: str,
    expected_status: str,
) -> None:
    snapshot = StatusSnapshot.from_run_history(
        revision=StatusRevision(uuid4(), 1),
        backend_status=BackendStatus.AVAILABLE,
        backup_schedule_health=schedule_health,
        active_operations=0,
        runs=(),
    )

    state = TrayControlClient.project_snapshot(snapshot)

    assert state.health == expected_health
    assert state.activity == "Idle"
    assert state.status == expected_status


@mark.unit
def test_refresh_status_orders_runs_by_newest_and_projects_summary() -> None:
    base_time = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    runs = [
        RunRecordView.from_record(
            RunRecord(
                run_id=uuid4(),
                operation=BackendOperationType.BACKUP,
                started_at=base_time - timedelta(minutes=60),
                completed_at=base_time - timedelta(minutes=55),
                state=RunState.SUCCEEDED,
                target_id="prod",
                trigger=OperationTrigger.EXPLICIT,
                result_code=ResultCode.BACKUP_SUCCEEDED,
                policy_fingerprint=None,
                counters={},
                schema_version=1,
            )
        ),
        RunRecordView.from_record(
            RunRecord(
                run_id=uuid4(),
                operation=BackendOperationType.RETENTION,
                started_at=base_time - timedelta(minutes=10),
                completed_at=base_time - timedelta(minutes=5),
                state=RunState.FAILED,
                target_id="prod",
                trigger=OperationTrigger.EXPLICIT,
                result_code=ResultCode.OPERATION_FAILED,
                policy_fingerprint="a" * 64,
                counters={},
                schema_version=1,
            )
        ),
    ]

    summary = ScheduleSummary(
        next_backup_at=base_time + timedelta(hours=1),
        next_retention_at=base_time + timedelta(hours=2),
    )
    client = TrayControlClient(
        client_factory=lambda: FakeBackend(runs, summary),
    )

    state = client.refresh_status()

    assert state.status == "success"
    assert state.health == "Healthy"
    assert state.activity == "Idle"
    assert "Next backup" not in state.tooltip
    assert state.latest_retention_status == "Operation failed."
    assert state.latest_backup_status == "Backup completed successfully."
    assert state.last_successful_backup_completed_at == (
        base_time - timedelta(minutes=55)
    )
    assert state.next_backup_at == base_time + timedelta(hours=1)


@mark.unit
def test_queued_backup_is_active_and_overrides_stale_interruption() -> None:
    base_time = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    runs = [
        RunRecordView.from_record(
            RunRecord(
                run_id=uuid4(),
                operation=BackendOperationType.BACKUP,
                started_at=base_time,
                state=RunState.QUEUED,
                target_id="prod",
                trigger=OperationTrigger.EXPLICIT,
                result_code=ResultCode.OPERATION_QUEUED,
            )
        ),
        RunRecordView.from_record(
            RunRecord(
                run_id=uuid4(),
                operation=BackendOperationType.BACKUP,
                started_at=base_time - timedelta(hours=1),
                completed_at=base_time - timedelta(minutes=55),
                state=RunState.INTERRUPTED,
                target_id="prod",
                trigger=OperationTrigger.SCHEDULED,
                result_code=ResultCode.OPERATION_INTERRUPTED,
            )
        ),
    ]
    client = TrayControlClient(
        client_factory=lambda: FakeBackend(
            runs,
            ScheduleSummary(None, None),
        ),
    )

    state = client.refresh_status()

    assert state.status == "running"
    assert state.health == "Healthy"
    assert state.activity == "Backup running"
    assert state.active_operations == 1


@mark.unit
def test_new_success_supersedes_stale_interruption() -> None:
    base_time = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    runs = [
        RunRecordView.from_record(
            RunRecord(
                run_id=uuid4(),
                operation=BackendOperationType.BACKUP,
                started_at=base_time,
                completed_at=base_time + timedelta(minutes=5),
                state=RunState.SUCCEEDED,
                target_id="prod",
                trigger=OperationTrigger.EXPLICIT,
                result_code=ResultCode.BACKUP_SUCCEEDED,
            )
        ),
        RunRecordView.from_record(
            RunRecord(
                run_id=uuid4(),
                operation=BackendOperationType.BACKUP,
                started_at=base_time - timedelta(hours=1),
                completed_at=base_time - timedelta(minutes=55),
                state=RunState.INTERRUPTED,
                target_id="prod",
                trigger=OperationTrigger.SCHEDULED,
                result_code=ResultCode.OPERATION_INTERRUPTED,
            )
        ),
    ]
    client = TrayControlClient(
        client_factory=lambda: FakeBackend(
            runs,
            ScheduleSummary(None, None),
        ),
    )

    state = client.refresh_status()

    assert state.status == "success"
    assert state.latest_backup_status == "Backup completed successfully."


@mark.unit
def test_failed_newer_backup_does_not_replace_last_successful_completion() -> None:
    base_time = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    successful_completion = base_time - timedelta(hours=1)
    runs = [
        RunRecordView.from_record(
            RunRecord(
                run_id=uuid4(),
                operation=BackendOperationType.BACKUP,
                started_at=base_time - timedelta(hours=2),
                completed_at=successful_completion,
                state=RunState.SUCCEEDED,
                target_id="prod",
                trigger=OperationTrigger.SCHEDULED,
                result_code=ResultCode.BACKUP_SUCCEEDED,
            )
        ),
        RunRecordView.from_record(
            RunRecord(
                run_id=uuid4(),
                operation=BackendOperationType.BACKUP,
                started_at=base_time,
                completed_at=base_time + timedelta(minutes=5),
                state=RunState.FAILED,
                target_id="prod",
                trigger=OperationTrigger.SCHEDULED,
                result_code=ResultCode.OPERATION_FAILED,
            )
        ),
    ]
    state = TrayControlClient(
        client_factory=lambda: FakeBackend(
            runs,
            ScheduleSummary(None, None),
        ),
    ).refresh_status()

    assert state.status == "error"
    assert state.latest_backup_status == "Operation failed."
    assert state.last_successful_backup_completed_at == successful_completion
    expected = successful_completion.astimezone().strftime("%Y-%m-%d %H:%M %Z")
    assert f"Last Backup: {expected}".rstrip() in state.tooltip


@mark.unit
def test_no_successful_backup_is_presented_as_never() -> None:
    state = TrayControlClient(
        client_factory=lambda: FakeBackend([], ScheduleSummary(None, None)),
    ).refresh_status()

    assert state.last_successful_backup_completed_at is None
    assert state.status == "warning"
    assert "Last Backup: Never" in state.tooltip


@mark.unit
def test_successful_retention_does_not_make_never_run_backup_successful() -> None:
    base_time = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    retention = RunRecordView.from_record(
        RunRecord(
            run_id=uuid4(),
            operation=BackendOperationType.RETENTION,
            started_at=base_time,
            completed_at=base_time + timedelta(minutes=5),
            state=RunState.SUCCEEDED,
            target_id="prod",
            trigger=OperationTrigger.SCHEDULED,
            result_code=ResultCode.RETENTION_SUCCEEDED,
            policy_fingerprint="a" * 64,
        )
    )

    state = TrayControlClient(
        client_factory=lambda: FakeBackend(
            [retention],
            ScheduleSummary(None, None),
        ),
    ).refresh_status()

    assert state.status == "warning"
    assert state.last_successful_backup_completed_at is None


@mark.unit
def test_retention_action_requires_fingerprint() -> None:
    client = TrayControlClient(
        client_factory=lambda: FakeBackend([], ScheduleSummary(None, None)),
        retention_policy_fingerprint=None,
    )
    try:
        client.perform_action("retention_now")
    except ValueError as exc:
        assert "retention policy fingerprint is required" in str(exc)
    else:
        raise AssertionError("expected a ValueError")


@mark.unit
def test_unavailable_backend_errors_are_retriable() -> None:
    backend_error = SystemControlClientError(
        ProtocolErrorCode.SYSTEM_BACKEND_UNAVAILABLE,
        "backend unavailable",
        status=ResponseStatus.UNAVAILABLE,
    )
    client = TrayControlClient(
        client_factory=lambda: FakeBackend(
            [], ScheduleSummary(None, None), status_error=backend_error
        ),
    )

    unavailable = client.refresh_status()

    assert unavailable.backend_available is False
    assert unavailable.status == "warning"
    assert unavailable.health == "Backend unavailable"
    assert unavailable.activity == "Connecting"
    assert "backend unavailable" in unavailable.tooltip.lower()

    backend = client._client
    backend.status_error = None
    client._retry_at = 0.0
    recovered = client.refresh_status()

    assert recovered.backend_available is True
    assert recovered.status == "warning"


@mark.unit
def test_denied_backend_is_rendered_without_protected_detail() -> None:
    denied = SystemControlClientError(
        ProtocolErrorCode.SYSTEM_ACCESS_DENIED,
        "detail that must not be rendered",
        status=ResponseStatus.DENIED,
    )
    client = TrayControlClient(
        client_factory=lambda: FakeBackend(
            [], ScheduleSummary(None, None), status_error=denied
        ),
    )

    state = client.refresh_status()

    assert state.backend_available is True
    assert state.health == "Access denied"
    assert state.activity == "Idle"
    assert state.tooltip == "TimeLocker - Access denied"
    assert "detail" not in state.tooltip


@mark.unit
def test_tray_rejects_actions_outside_strict_allowlist() -> None:
    client = TrayControlClient(
        client_factory=lambda: FakeBackend([], ScheduleSummary(None, None)),
    )

    with pytest.raises(ValueError, match="unsupported tray action"):
        client.perform_action("shell")
