"""Crash-safety and concurrency tests for system-control durable state."""

from datetime import datetime, timedelta, timezone
import multiprocessing
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from TimeLocker.system_control import (
    AtomicRecordStore,
    DiagnosticCode,
    DiagnosticComponent,
    DiagnosticLevel,
    DiagnosticQuery,
    DiagnosticRecord,
    InvalidTransitionError,
    MutationConflictError,
    OperationTrigger,
    OperationType,
    RecordCorruptionError,
    RepositoryMutationLock,
    ResultCode,
    RunQuery,
    RunRecord,
    RunState,
    RunTransition,
    reconcile_abandoned_runs,
)


NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)


def running_record(
    *, run_id: UUID | None = None, target_id: str = "production"
) -> RunRecord:
    """Create one valid running backup record."""
    return RunRecord(
        run_id=run_id or uuid4(),
        operation=OperationType.BACKUP,
        trigger=OperationTrigger.SCHEDULED,
        target_id=target_id,
        started_at=NOW,
        state=RunState.RUNNING,
        result_code=ResultCode.OPERATION_RUNNING,
    )


def _hold_lease(lock_root: str, target_id: str, run_id: str, ready: object) -> None:
    lock = RepositoryMutationLock(Path(lock_root))
    lease = lock.acquire(target_id, run_id)
    ready.set()
    try:
        ready.wait(10)
    finally:
        lease.release()


@pytest.mark.unit
class TestAtomicRecordStore:
    """Verify durable state, strict parsing, and terminal-state compare-and-swap."""

    def test_record_survives_store_recreation(self, tmp_path: Path) -> None:
        record = running_record()
        AtomicRecordStore(tmp_path).create_run(record)

        restored = AtomicRecordStore(tmp_path).read_run(record.run_id)

        assert restored == record
        assert (
            tmp_path / "runs" / f"{record.run_id}.json"
        ).stat().st_mode & 0o777 == 0o600

    def test_exactly_one_terminal_transition_wins(self, tmp_path: Path) -> None:
        store = AtomicRecordStore(tmp_path)
        record = running_record()
        store.create_run(record)
        succeeded = store.transition(
            record.run_id,
            RunTransition(
                expected_states=frozenset({RunState.RUNNING}),
                new_state=RunState.SUCCEEDED,
                result_code=ResultCode.BACKUP_SUCCEEDED,
                completed_at=NOW + timedelta(minutes=1),
            ),
        )

        with pytest.raises(InvalidTransitionError):
            store.transition(
                record.run_id,
                RunTransition(
                    expected_states=frozenset({RunState.RUNNING}),
                    new_state=RunState.FAILED,
                    result_code=ResultCode.OPERATION_FAILED,
                    completed_at=NOW + timedelta(minutes=2),
                ),
            )

        assert store.read_run(record.run_id) == succeeded

    def test_transition_merges_bounded_counters(self, tmp_path: Path) -> None:
        store = AtomicRecordStore(tmp_path)
        record = running_record()
        store.create_run(record)

        result = store.transition(
            record.run_id,
            RunTransition(
                expected_states=frozenset({RunState.RUNNING}),
                new_state=RunState.SUCCEEDED,
                result_code=ResultCode.BACKUP_SUCCEEDED,
                completed_at=NOW + timedelta(minutes=1),
                counters={"files_processed": 42},
            ),
        )

        assert result.counters == {"files_processed": 42}

    def test_corrupt_or_unknown_record_fields_fail_closed(self, tmp_path: Path) -> None:
        store = AtomicRecordStore(tmp_path)
        record = running_record()
        store.create_run(record)
        path = tmp_path / "runs" / f"{record.run_id}.json"
        path.write_text('{"run_id":"secret","repository_password":"value"}\n')

        with pytest.raises(RecordCorruptionError, match="corrupt"):
            store.read_run(record.run_id)

    def test_run_queries_are_filtered_and_bounded(self, tmp_path: Path) -> None:
        store = AtomicRecordStore(tmp_path)
        backup = running_record(target_id="backup")
        retention = RunRecord(
            run_id=uuid4(),
            operation=OperationType.RETENTION,
            trigger=OperationTrigger.EXPLICIT,
            target_id="retention",
            started_at=NOW + timedelta(minutes=1),
            state=RunState.RUNNING,
            result_code=ResultCode.OPERATION_RUNNING,
            policy_fingerprint="a" * 64,
        )
        store.create_run(backup)
        store.create_run(retention)

        assert store.list_runs(RunQuery(limit=1))[0] == retention
        assert store.list_runs(RunQuery(limit=10, operation=OperationType.BACKUP)) == [
            backup
        ]

    def test_diagnostic_stream_is_bounded_and_filtered(self, tmp_path: Path) -> None:
        store = AtomicRecordStore(tmp_path, max_diagnostics=2)
        run_id = uuid4()
        records = [
            DiagnosticRecord(
                record_id=uuid4(),
                run_id=run_id,
                timestamp=NOW + timedelta(seconds=index),
                level=DiagnosticLevel.ERROR if index == 2 else DiagnosticLevel.INFO,
                component=DiagnosticComponent.RUN_STORE,
                message_code=DiagnosticCode.OPERATION_FAILED,
            )
            for index in range(3)
        ]
        for record in records:
            store.append_diagnostic(record)

        assert store.list_diagnostics() == [records[2], records[1]]
        assert store.list_diagnostics(
            DiagnosticQuery(limit=10, level=DiagnosticLevel.ERROR)
        ) == [records[2]]


@pytest.mark.unit
@pytest.mark.filesystem
class TestRepositoryMutationLock:
    """Verify kernel leases reject overlap and recover after process exit."""

    def test_same_repository_cannot_be_mutated_concurrently(
        self, tmp_path: Path
    ) -> None:
        locks = RepositoryMutationLock(tmp_path)
        first = locks.acquire("production", uuid4())
        try:
            with pytest.raises(MutationConflictError):
                locks.acquire("production", uuid4())
        finally:
            first.release()

    def test_different_repositories_have_independent_locks(
        self, tmp_path: Path
    ) -> None:
        locks = RepositoryMutationLock(tmp_path)
        with (
            locks.acquire("production-a", uuid4()),
            locks.acquire("production-b", uuid4()),
        ):
            pass

    def test_process_exit_releases_kernel_lease(self, tmp_path: Path) -> None:
        context = multiprocessing.get_context("spawn")
        ready = context.Event()
        run_id = uuid4()
        process = context.Process(
            target=_hold_lease,
            args=(str(tmp_path), "production", str(run_id), ready),
        )
        process.start()
        assert ready.wait(10)
        process.terminate()
        process.join(10)
        assert process.exitcode is not None

        with RepositoryMutationLock(tmp_path).acquire("production", uuid4()):
            pass


@pytest.mark.unit
@pytest.mark.filesystem
class TestStartupReconciliation:
    """Verify abandoned attempts become interrupted exactly once."""

    def test_abandoned_run_is_interrupted_and_lock_reusable(
        self, tmp_path: Path
    ) -> None:
        store = AtomicRecordStore(tmp_path / "state")
        locks = RepositoryMutationLock(tmp_path / "locks")
        record = running_record()
        store.create_run(record)
        stale = locks.acquire(record.target_id, record.run_id)
        stale.release()

        reconciled = reconcile_abandoned_runs(
            store,
            locks,
            now=NOW + timedelta(hours=1),
        )

        assert len(reconciled) == 1
        assert reconciled[0].state is RunState.INTERRUPTED
        assert (
            reconcile_abandoned_runs(
                store,
                locks,
                now=NOW + timedelta(hours=2),
            )
            == []
        )
        with locks.acquire(record.target_id, uuid4()):
            pass

    def test_live_matching_lease_is_not_interrupted(self, tmp_path: Path) -> None:
        store = AtomicRecordStore(tmp_path / "state")
        locks = RepositoryMutationLock(tmp_path / "locks")
        record = running_record()
        store.create_run(record)
        with locks.acquire(record.target_id, record.run_id):
            assert reconcile_abandoned_runs(store, locks, now=NOW) == []
            assert store.read_run(record.run_id).state is RunState.RUNNING

    def test_newer_live_lease_does_not_block_old_run_reconciliation(
        self,
        tmp_path: Path,
    ) -> None:
        store = AtomicRecordStore(tmp_path / "state")
        locks = RepositoryMutationLock(tmp_path / "locks")
        old_record = running_record()
        store.create_run(old_record)
        newer_run_id = uuid4()

        with locks.acquire(old_record.target_id, newer_run_id):
            reconciled = reconcile_abandoned_runs(
                store,
                locks,
                now=NOW + timedelta(minutes=1),
            )
            assert reconciled[0].run_id == old_record.run_id
            assert reconciled[0].state is RunState.INTERRUPTED
            assert locks.is_active(old_record.target_id, newer_run_id)

    def test_clock_rollback_does_not_make_reconciliation_invalid(
        self,
        tmp_path: Path,
    ) -> None:
        store = AtomicRecordStore(tmp_path / "state")
        locks = RepositoryMutationLock(tmp_path / "locks")
        record = running_record()
        store.create_run(record)

        reconciled = reconcile_abandoned_runs(
            store,
            locks,
            now=NOW - timedelta(hours=1),
        )

        assert reconciled[0].completed_at == record.started_at
