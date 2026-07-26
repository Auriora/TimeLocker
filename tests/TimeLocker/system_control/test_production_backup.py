"""Production systemd backup coordination tests."""

from __future__ import annotations

from pathlib import Path
import subprocess
from uuid import uuid4

import pytest

from TimeLocker.system_control.models import BackupActionRequest, RunQuery
from TimeLocker.system_control.production_backup import (
    SystemBackupRunCoordinator,
    SystemdBackupMutationAdapter,
)
from TimeLocker.system_control.storage import AtomicRecordStore
from TimeLocker.system_control.types import (
    OperationTrigger,
    OperationType,
    ResultCode,
    RunState,
)


@pytest.mark.unit
def test_on_demand_request_and_hooks_share_the_receipt_run(
    tmp_path: Path,
) -> None:
    store = AtomicRecordStore(tmp_path / "records")
    worker_root = tmp_path / "worker"
    request_id = uuid4()
    commands: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 3 if "is-active" in command else 0)

    adapter = SystemdBackupMutationAdapter(
        store=store,
        target_id="production",
        worker_root=worker_root,
        runner=runner,
    )
    receipt = adapter.request_backup(
        BackupActionRequest(target_id="production"),
        request_id=request_id,
    )
    coordinator = SystemBackupRunCoordinator(
        store=store,
        target_id="production",
        worker_root=worker_root,
    )

    running = coordinator.start()
    finished = coordinator.finish(result="success")

    assert receipt.accepted is True
    assert receipt.run_id == request_id
    assert running.run_id == request_id
    assert running.trigger is OperationTrigger.EXPLICIT
    assert finished is not None
    assert finished.state is RunState.SUCCEEDED
    assert finished.result_code is ResultCode.BACKUP_SUCCEEDED
    assert commands[-1] == [
        "/usr/bin/systemctl",
        "start",
        "--no-block",
        "timelocker-npbackup-migration.service",
    ]


@pytest.mark.unit
def test_active_unit_rejects_on_demand_request_without_creating_run(
    tmp_path: Path,
) -> None:
    store = AtomicRecordStore(tmp_path / "records")
    adapter = SystemdBackupMutationAdapter(
        store=store,
        target_id="production",
        worker_root=tmp_path / "worker",
        runner=lambda command, **_kwargs: subprocess.CompletedProcess(command, 0),
    )

    receipt = adapter.request_backup(
        BackupActionRequest(target_id="production"),
        request_id=uuid4(),
    )

    assert receipt.accepted is False
    assert receipt.status == "conflict"
    assert store.list_runs() == []


@pytest.mark.unit
def test_scheduled_hook_creates_run_and_maps_lock_conflict(
    tmp_path: Path,
) -> None:
    store = AtomicRecordStore(tmp_path / "records")
    coordinator = SystemBackupRunCoordinator(
        store=store,
        target_id="production",
        worker_root=tmp_path / "worker",
    )

    running = coordinator.start()
    finished = coordinator.finish(result="failure", exit_status=75)

    assert running.operation is OperationType.BACKUP
    assert running.trigger is OperationTrigger.SCHEDULED
    assert finished is not None
    assert finished.state is RunState.SKIPPED
    assert finished.result_code is ResultCode.OPERATION_CONFLICT
    assert store.list_runs(RunQuery(operation=OperationType.BACKUP)) == [finished]


@pytest.mark.unit
def test_systemd_start_failure_is_terminal_and_secret_free(
    tmp_path: Path,
) -> None:
    store = AtomicRecordStore(tmp_path / "records")

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            3 if "is-active" in command else 1,
            stdout="",
            stderr="protected unit detail",
        )

    adapter = SystemdBackupMutationAdapter(
        store=store,
        target_id="production",
        worker_root=tmp_path / "worker",
        runner=runner,
    )
    receipt = adapter.request_backup(
        BackupActionRequest(target_id="production"),
        request_id=uuid4(),
    )

    assert receipt.accepted is False
    assert receipt.status == "failed"
    [run] = store.list_runs()
    assert run.state is RunState.FAILED
    assert "protected" not in run.safe_summary


@pytest.mark.unit
def test_next_systemd_start_recovers_interrupted_active_run(
    tmp_path: Path,
) -> None:
    store = AtomicRecordStore(tmp_path / "records")
    coordinator = SystemBackupRunCoordinator(
        store=store,
        target_id="production",
        worker_root=tmp_path / "worker",
    )
    abandoned = coordinator.start()

    replacement = coordinator.start()

    recovered = store.read_run(abandoned.run_id)
    assert recovered.state is RunState.INTERRUPTED
    assert recovered.result_code is ResultCode.OPERATION_INTERRUPTED
    assert replacement.run_id != abandoned.run_id
    assert replacement.state is RunState.RUNNING
