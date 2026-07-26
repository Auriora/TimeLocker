"""Retention execution, approval, locking, and trigger tests."""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from TimeLocker.system_control.models import RetentionPolicy, RunRecord
from TimeLocker.system_control.retention import (
    RetentionExecutionResult,
    RetentionExecutor,
    RetentionPlan,
    RetentionRequestHandler,
    RetentionTriggerCoordinator,
    RetentionTriggerStore,
)
from TimeLocker.system_control.protocol import RequestEnvelope, project_response
from TimeLocker.system_control.storage import AtomicRecordStore, RepositoryMutationLock
from TimeLocker.system_control.types import (
    OperationTrigger,
    OperationType,
    ResultCode,
    RunState,
    SystemAction,
)


class RecordingAdapter:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[RetentionPlan, bool]] = []

    def execute(
        self,
        plan: RetentionPlan,
        *,
        dry_run: bool,
    ) -> RetentionExecutionResult:
        self.calls.append((plan, dry_run))
        if self.fail:
            raise RuntimeError("protected backend detail")
        return RetentionExecutionResult(selected_snapshots=8, removed_snapshots=3)


def _unapproved_plan(**changes: object) -> RetentionPlan:
    values = {
        "target_id": "npbackup-production",
        "repository_identity": "repository-01",
        "credential_source": "system-environment-01",
        "snapshot_filters": ("host:Bruce-5560",),
        "policy": RetentionPolicy(),
    }
    values.update(changes)
    return RetentionPlan(**values)


def _approved_plan(**changes: object) -> RetentionPlan:
    unapproved = _unapproved_plan(**changes)
    policy = replace(
        unapproved.policy,
        approved_fingerprint=unapproved.fingerprint,
    )
    return replace(unapproved, policy=policy)


def _executor(tmp_path, adapter: RecordingAdapter | None = None) -> RetentionExecutor:
    return RetentionExecutor(
        store=AtomicRecordStore(tmp_path / "records"),
        locks=RepositoryMutationLock(tmp_path / "locks"),
        adapter=adapter or RecordingAdapter(),
    )


def _successful_backup() -> RunRecord:
    now = datetime.now(timezone.utc)
    return RunRecord(
        run_id=uuid4(),
        operation=OperationType.BACKUP,
        trigger=OperationTrigger.SCHEDULED,
        target_id="npbackup-production",
        started_at=now,
        completed_at=now,
        state=RunState.SUCCEEDED,
        result_code=ResultCode.BACKUP_SUCCEEDED,
    )


def test_fingerprint_covers_every_execution_input() -> None:
    plan = _unapproved_plan()
    variants = (
        _unapproved_plan(repository_identity="repository-02"),
        _unapproved_plan(credential_source="system-environment-02"),
        _unapproved_plan(snapshot_filters=("host:other",)),
        _unapproved_plan(policy=replace(plan.policy, keep_daily=6)),
        _unapproved_plan(policy=replace(plan.policy, keep_weekly=5)),
        _unapproved_plan(policy=replace(plan.policy, keep_monthly=13)),
        _unapproved_plan(policy=replace(plan.policy, keep_yearly=4)),
        _unapproved_plan(policy=replace(plan.policy, group_by=("host",))),
        _unapproved_plan(policy=replace(plan.policy, prune=True)),
    )
    assert all(candidate.fingerprint != plan.fingerprint for candidate in variants)


def test_dry_run_does_not_authorize_later_mutation(tmp_path) -> None:
    executor = _executor(tmp_path)
    plan = _unapproved_plan()

    dry_run = executor.execute(
        plan,
        trigger=OperationTrigger.EXPLICIT,
        dry_run=True,
    )

    assert dry_run.state is RunState.SUCCEEDED
    assert dry_run.counters["dry_run"] == 1
    with pytest.raises(PermissionError, match="approval does not match"):
        executor.execute(
            plan,
            trigger=OperationTrigger.EXPLICIT,
            dry_run=False,
        )


def test_exact_approval_executes_separate_locked_run(tmp_path) -> None:
    adapter = RecordingAdapter()
    executor = _executor(tmp_path, adapter)
    plan = _approved_plan()

    result = executor.execute(
        plan,
        trigger=OperationTrigger.EXPLICIT,
        dry_run=False,
    )

    assert result.operation is OperationType.RETENTION
    assert result.state is RunState.SUCCEEDED
    assert result.policy_fingerprint == plan.fingerprint
    assert result.counters == {
        "dry_run": 0,
        "removed_snapshots": 3,
        "selected_snapshots": 8,
    }
    assert adapter.calls == [(plan, False)]


def test_lock_conflict_is_skipped_without_calling_adapter(tmp_path) -> None:
    adapter = RecordingAdapter()
    executor = _executor(tmp_path, adapter)
    plan = _approved_plan()

    with executor.locks.acquire(plan.target_id, uuid4()):
        result = executor.execute(
            plan,
            trigger=OperationTrigger.BACKUP_SUCCESS,
            dry_run=False,
        )

    assert result.state is RunState.SKIPPED
    assert result.result_code is ResultCode.OPERATION_CONFLICT
    assert adapter.calls == []


def test_adapter_failure_is_safe_and_terminal(tmp_path) -> None:
    adapter = RecordingAdapter(fail=True)
    executor = _executor(tmp_path, adapter)

    result = executor.execute(
        _approved_plan(),
        trigger=OperationTrigger.EXPLICIT,
        dry_run=False,
    )

    assert result.state is RunState.FAILED
    assert result.safe_summary == "Operation failed."


def test_post_backup_trigger_is_durable_at_most_once_and_does_not_change_backup(
    tmp_path,
) -> None:
    executor = _executor(tmp_path)
    coordinator = RetentionTriggerCoordinator(
        executor=executor,
        trigger_store=RetentionTriggerStore(tmp_path / "triggers"),
    )
    backup = _successful_backup()
    plan = _approved_plan()

    first = coordinator.after_backup_success(backup, plan)
    second = coordinator.after_backup_success(backup, plan)

    assert first is not None
    assert first.trigger is OperationTrigger.BACKUP_SUCCESS
    assert second is None
    assert backup.state is RunState.SUCCEEDED
    restarted = RetentionTriggerCoordinator(
        executor=executor,
        trigger_store=RetentionTriggerStore(tmp_path / "triggers"),
    )
    assert restarted.after_backup_success(backup, plan) is None


def test_post_backup_trigger_rejects_non_success(tmp_path) -> None:
    backup = replace(
        _successful_backup(),
        state=RunState.FAILED,
        result_code=ResultCode.OPERATION_FAILED,
    )
    coordinator = RetentionTriggerCoordinator(
        executor=_executor(tmp_path),
        trigger_store=RetentionTriggerStore(tmp_path / "triggers"),
    )

    assert coordinator.after_backup_success(backup, _approved_plan()) is None


def test_independent_schedule_is_disabled_by_default_and_can_be_enabled(
    tmp_path,
) -> None:
    executor = _executor(tmp_path)
    plan = _approved_plan()
    disabled = RetentionTriggerCoordinator(
        executor=executor,
        trigger_store=RetentionTriggerStore(tmp_path / "disabled-triggers"),
    )
    enabled = RetentionTriggerCoordinator(
        executor=executor,
        trigger_store=RetentionTriggerStore(tmp_path / "enabled-triggers"),
        independent_schedule_enabled=True,
    )

    assert disabled.scheduled(plan) is None
    result = enabled.scheduled(plan)
    assert result is not None
    assert result.trigger is OperationTrigger.SCHEDULED


def test_protected_request_handler_requires_exact_fingerprint(tmp_path) -> None:
    plan = _approved_plan()
    coordinator = RetentionTriggerCoordinator(
        executor=_executor(tmp_path),
        trigger_store=RetentionTriggerStore(tmp_path / "triggers"),
    )
    handler = RetentionRequestHandler(coordinator=coordinator, plan=plan)
    request = RequestEnvelope(
        request_id=uuid4(),
        action=SystemAction.RETENTION_REQUEST,
        parameters={"policy_fingerprint": plan.fingerprint, "dry_run": False},
    )

    receipt = handler(request)

    assert receipt["accepted"] is True
    assert receipt["status"] == "succeeded"
    assert project_response(SystemAction.RETENTION_REQUEST, receipt) == receipt
    with pytest.raises(PermissionError, match="does not match"):
        handler(
            RequestEnvelope(
                request_id=uuid4(),
                action=SystemAction.RETENTION_REQUEST,
                parameters={"policy_fingerprint": "0" * 64, "dry_run": True},
            )
        )
