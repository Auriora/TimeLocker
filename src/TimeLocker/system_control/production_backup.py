"""Durable coordination for the protected systemd backup unit."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import subprocess
from uuid import UUID, uuid4

from .models import (
    ActionReceipt,
    BackupActionRequest,
    DiagnosticRecord,
    RunRecord,
    RunTransition,
)
from .storage import AtomicRecordStore
from .types import (
    DiagnosticCode,
    DiagnosticComponent,
    DiagnosticLevel,
    OperationTrigger,
    OperationType,
    ResultCode,
    RunState,
)


DEFAULT_BACKUP_UNIT = "timelocker-npbackup-migration.service"


class SystemdBackupMutationAdapter:
    """Queue the one allowlisted systemd backup and return its durable run ID."""

    def __init__(
        self,
        *,
        store: AtomicRecordStore,
        target_id: str,
        worker_root: Path,
        unit_name: str = DEFAULT_BACKUP_UNIT,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        if not isinstance(store, AtomicRecordStore):
            raise TypeError("store must be an AtomicRecordStore")
        if not isinstance(worker_root, Path) or not worker_root.is_absolute():
            raise ValueError("worker_root must be an absolute Path")
        if unit_name != DEFAULT_BACKUP_UNIT:
            raise ValueError("backup unit is not allowlisted")
        self.store = store
        self.target_id = target_id
        self.worker_root = worker_root
        self.unit_name = unit_name
        self._runner = runner or subprocess.run
        worker_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        worker_root.chmod(0o700)

    @property
    def pending_path(self) -> Path:
        return self.worker_root / "pending-run.json"

    def request_backup(
        self,
        request: BackupActionRequest,
        *,
        request_id: UUID,
    ) -> ActionReceipt:
        if not isinstance(request, BackupActionRequest):
            raise TypeError("request must be a BackupActionRequest")
        if request.target_id != self.target_id:
            raise PermissionError("backup target is not allowlisted")
        if self._unit_active():
            return ActionReceipt(
                request_id=request_id,
                accepted=False,
                status="conflict",
            )
        run = RunRecord(
            run_id=request_id,
            operation=OperationType.BACKUP,
            trigger=OperationTrigger.EXPLICIT,
            target_id=self.target_id,
            started_at=datetime.now(timezone.utc),
            state=RunState.QUEUED,
            result_code=ResultCode.OPERATION_QUEUED,
        )
        try:
            _write_exclusive_json(
                self.pending_path,
                {"schema_version": 1, "run_id": str(run.run_id)},
            )
        except FileExistsError:
            return ActionReceipt(
                request_id=request_id,
                accepted=False,
                status="conflict",
            )
        try:
            self.store.create_run(run)
            result = self._runner(
                [
                    "/usr/bin/systemctl",
                    "start",
                    "--no-block",
                    self.unit_name,
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if result.returncode != 0:
                self.pending_path.unlink(missing_ok=True)
                self.store.transition(
                    run.run_id,
                    RunTransition(
                        expected_states=frozenset({RunState.QUEUED}),
                        new_state=RunState.FAILED,
                        result_code=ResultCode.OPERATION_FAILED,
                        completed_at=datetime.now(timezone.utc),
                    ),
                )
                return ActionReceipt(
                    request_id=request_id,
                    accepted=False,
                    status="failed",
                )
        except Exception:
            self.pending_path.unlink(missing_ok=True)
            raise
        return ActionReceipt(
            request_id=request_id,
            accepted=True,
            status=RunState.QUEUED.value,
            run_id=run.run_id,
        )

    def _unit_active(self) -> bool:
        result = self._runner(
            ["/usr/bin/systemctl", "is-active", "--quiet", self.unit_name],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0


class SystemBackupRunCoordinator:
    """Bind systemd pre/post hooks to one crash-recoverable backup record."""

    def __init__(
        self,
        *,
        store: AtomicRecordStore,
        target_id: str,
        worker_root: Path,
    ) -> None:
        if not isinstance(store, AtomicRecordStore):
            raise TypeError("store must be an AtomicRecordStore")
        if not isinstance(worker_root, Path) or not worker_root.is_absolute():
            raise ValueError("worker_root must be an absolute Path")
        self.store = store
        self.target_id = target_id
        self.worker_root = worker_root
        worker_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        worker_root.chmod(0o700)

    @property
    def pending_path(self) -> Path:
        return self.worker_root / "pending-run.json"

    @property
    def active_path(self) -> Path:
        return self.worker_root / "active-run.json"

    def start(self) -> RunRecord:
        self._reconcile_interrupted_active_run()
        pending_id = self._consume_pending()
        if pending_id is None:
            run = RunRecord(
                run_id=uuid4(),
                operation=OperationType.BACKUP,
                trigger=OperationTrigger.SCHEDULED,
                target_id=self.target_id,
                started_at=datetime.now(timezone.utc),
                state=RunState.QUEUED,
                result_code=ResultCode.OPERATION_QUEUED,
            )
            self.store.create_run(run)
        else:
            run = self.store.read_run(pending_id)
            if (
                run.operation is not OperationType.BACKUP
                or run.target_id != self.target_id
                or run.state is not RunState.QUEUED
            ):
                raise ValueError("pending backup run is invalid")
        running = self.store.transition(
            run.run_id,
            RunTransition(
                expected_states=frozenset({RunState.QUEUED}),
                new_state=RunState.RUNNING,
                result_code=ResultCode.OPERATION_RUNNING,
            ),
        )
        _write_exclusive_json(
            self.active_path,
            {"schema_version": 1, "run_id": str(run.run_id)},
        )
        self._diagnostic(run.run_id, DiagnosticCode.BACKUP_STARTED)
        return running

    def finish(self, *, result: str, exit_status: int | None = None) -> RunRecord | None:
        run_id = self._active_run_id()
        if run_id is None:
            return None
        run = self.store.read_run(run_id)
        if run.state not in {RunState.QUEUED, RunState.RUNNING}:
            self.active_path.unlink(missing_ok=True)
            return run
        now = datetime.now(timezone.utc)
        if result == "success":
            state = RunState.SUCCEEDED
            result_code = ResultCode.BACKUP_SUCCEEDED
            diagnostic = DiagnosticCode.BACKUP_SUCCEEDED
        elif exit_status == 75:
            state = RunState.SKIPPED
            result_code = ResultCode.OPERATION_CONFLICT
            diagnostic = DiagnosticCode.OPERATION_CONFLICT
        else:
            state = RunState.FAILED
            result_code = ResultCode.OPERATION_FAILED
            diagnostic = DiagnosticCode.OPERATION_FAILED
        finished = self.store.transition(
            run.run_id,
            RunTransition(
                expected_states=frozenset({run.state}),
                new_state=state,
                result_code=result_code,
                completed_at=max(now, run.started_at),
            ),
        )
        self.active_path.unlink(missing_ok=True)
        self._diagnostic(run.run_id, diagnostic)
        return finished

    def _reconcile_interrupted_active_run(self) -> None:
        run_id = self._active_run_id()
        if run_id is None:
            return
        run = self.store.read_run(run_id)
        if run.state in {RunState.QUEUED, RunState.RUNNING}:
            self.store.transition(
                run.run_id,
                RunTransition(
                    expected_states=frozenset({run.state}),
                    new_state=RunState.INTERRUPTED,
                    result_code=ResultCode.OPERATION_INTERRUPTED,
                    completed_at=max(datetime.now(timezone.utc), run.started_at),
                ),
            )
            self._diagnostic(run.run_id, DiagnosticCode.OPERATION_INTERRUPTED)
        self.active_path.unlink(missing_ok=True)

    def _consume_pending(self) -> UUID | None:
        try:
            descriptor = os.open(
                self.pending_path,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            )
        except FileNotFoundError:
            return None
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid():
                raise PermissionError("pending backup file is not trusted")
            with os.fdopen(descriptor, encoding="utf-8", closefd=False) as source:
                value = json.load(source)
            if set(value) != {"schema_version", "run_id"} or value["schema_version"] != 1:
                raise ValueError("pending backup file is invalid")
            return UUID(value["run_id"])
        finally:
            os.close(descriptor)
            self.pending_path.unlink(missing_ok=True)

    def _active_run_id(self) -> UUID | None:
        try:
            value = json.loads(self.active_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        if set(value) != {"schema_version", "run_id"} or value["schema_version"] != 1:
            raise ValueError("active backup file is invalid")
        return UUID(value["run_id"])

    def _diagnostic(self, run_id: UUID, code: DiagnosticCode) -> None:
        level = (
            DiagnosticLevel.INFO
            if code in {DiagnosticCode.BACKUP_STARTED, DiagnosticCode.BACKUP_SUCCEEDED}
            else DiagnosticLevel.WARNING
        )
        self.store.append_diagnostic(
            DiagnosticRecord(
                record_id=uuid4(),
                run_id=run_id,
                timestamp=datetime.now(timezone.utc),
                level=level,
                component=DiagnosticComponent.BACKUP,
                message_code=code,
            )
        )


def _write_exclusive_json(path: Path, value: dict[str, object]) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", closefd=False) as output:
            json.dump(value, output, sort_keys=True, separators=(",", ":"))
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
    finally:
        os.close(descriptor)


__all__: Sequence[str] = (
    "DEFAULT_BACKUP_UNIT",
    "SystemBackupRunCoordinator",
    "SystemdBackupMutationAdapter",
)
