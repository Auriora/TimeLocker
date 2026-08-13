"""Crash-safe storage and repository mutation locking for system operations."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Callable, Iterator, Mapping
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from uuid import UUID

from .models import (
    DiagnosticQuery,
    DiagnosticRecord,
    RunQuery,
    RunRecord,
    RunTransition,
)
from .types import ResultCode, RunState
from .validation import require_exact_mapping, require_safe_identifier, require_uuid

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised by Windows adapter validation
    fcntl = None  # type: ignore[assignment]


_NON_TERMINAL_STATES = frozenset({RunState.QUEUED, RunState.RUNNING})
_RUN_FIELDS = frozenset(
    {
        "schema_version",
        "run_id",
        "operation",
        "trigger",
        "target_id",
        "started_at",
        "completed_at",
        "state",
        "result_code",
        "policy_fingerprint",
        "counters",
    }
)
_DIAGNOSTIC_FIELDS = frozenset(
    {
        "schema_version",
        "record_id",
        "run_id",
        "timestamp",
        "level",
        "component",
        "message_code",
    }
)


class RecordStoreError(RuntimeError):
    """Base error for durable system-control state."""


class RecordNotFoundError(RecordStoreError):
    """Raised when a requested run does not exist."""


class RecordCorruptionError(RecordStoreError):
    """Raised when persisted state does not satisfy the strict schema."""


class InvalidTransitionError(RecordStoreError):
    """Raised when the current record cannot accept a requested transition."""


class MutationConflictError(RecordStoreError):
    """Raised when another process owns a repository mutation lease."""


def _run_to_wire(record: RunRecord) -> dict[str, Any]:
    return {
        "schema_version": record.schema_version,
        "run_id": str(record.run_id),
        "operation": record.operation.value,
        "trigger": record.trigger.value,
        "target_id": record.target_id,
        "started_at": record.started_at.isoformat(),
        "completed_at": record.completed_at.isoformat()
        if record.completed_at
        else None,
        "state": record.state.value,
        "result_code": record.result_code.value,
        "policy_fingerprint": record.policy_fingerprint,
        "counters": dict(record.counters),
    }


def _run_from_wire(value: object) -> RunRecord:
    mapping = require_exact_mapping(
        value,
        field="run record",
        required=_RUN_FIELDS,
    )
    return RunRecord(
        schema_version=mapping["schema_version"],
        run_id=mapping["run_id"],
        operation=mapping["operation"],
        trigger=mapping["trigger"],
        target_id=mapping["target_id"],
        started_at=datetime.fromisoformat(mapping["started_at"]),
        completed_at=(
            datetime.fromisoformat(mapping["completed_at"])
            if mapping["completed_at"] is not None
            else None
        ),
        state=mapping["state"],
        result_code=mapping["result_code"],
        policy_fingerprint=mapping["policy_fingerprint"],
        counters=mapping["counters"],
    )


def _diagnostic_to_wire(record: DiagnosticRecord) -> dict[str, Any]:
    return {
        "schema_version": record.schema_version,
        "record_id": str(record.record_id),
        "run_id": str(record.run_id) if record.run_id else None,
        "timestamp": record.timestamp.isoformat(),
        "level": record.level.value,
        "component": record.component.value,
        "message_code": record.message_code.value,
    }


def _diagnostic_from_wire(value: object) -> DiagnosticRecord:
    mapping = require_exact_mapping(
        value,
        field="diagnostic record",
        required=_DIAGNOSTIC_FIELDS,
    )
    return DiagnosticRecord(
        schema_version=mapping["schema_version"],
        record_id=mapping["record_id"],
        run_id=mapping["run_id"],
        timestamp=datetime.fromisoformat(mapping["timestamp"]),
        level=mapping["level"],
        component=mapping["component"],
        message_code=mapping["message_code"],
    )


class AtomicRecordStore:
    """Persist strictly validated records with process-safe atomic replacement."""

    def __init__(
        self,
        root: Path,
        *,
        max_diagnostics: int = 1_000,
        status_change_callback: Callable[[], object] | None = None,
    ) -> None:
        if not isinstance(root, Path):
            raise TypeError("root must be a Path")
        if type(max_diagnostics) is not int or not 1 <= max_diagnostics <= 100_000:
            raise ValueError("max_diagnostics must be between 1 and 100000")
        self.root = root
        self.runs_directory = root / "runs"
        self.diagnostics_directory = root / "diagnostics"
        self._store_lock_path = root / ".record-store.lock"
        self.max_diagnostics = max_diagnostics
        if status_change_callback is not None and not callable(
            status_change_callback
        ):
            raise TypeError("status_change_callback must be callable")
        self._status_change_callback = status_change_callback
        for directory in (root, self.runs_directory, self.diagnostics_directory):
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            directory.chmod(0o700)
        self._store_lock_path.touch(mode=0o600, exist_ok=True)
        self._store_lock_path.chmod(0o600)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        _require_file_locking()
        with self._store_lock_path.open("r+b") as lock_file:
            assert fcntl is not None
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def create_run(self, record: RunRecord) -> None:
        """Create a run exactly once."""
        if not isinstance(record, RunRecord):
            raise TypeError("record must be a RunRecord")
        destination = self._run_path(record.run_id)
        with self._locked():
            if destination.exists():
                raise InvalidTransitionError("run already exists")
            self._atomic_write_json(destination, _run_to_wire(record))
        self._notify_status_change()

    def read_run(self, run_id: UUID | str) -> RunRecord:
        """Read and validate one durable run."""
        run_id = require_uuid(run_id, field="run_id")
        with self._locked():
            return self._read_run_unlocked(run_id)

    def list_runs(self, query: RunQuery | None = None) -> list[RunRecord]:
        """Return newest runs first, bounded by the validated query."""
        query = query or RunQuery()
        if not isinstance(query, RunQuery):
            raise TypeError("query must be a RunQuery")
        records = self._list_runs_unbounded()
        return [
            record
            for record in records
            if (query.operation is None or record.operation is query.operation)
            and (query.state is None or record.state is query.state)
        ][: query.limit]

    def list_status_runs(self) -> list[RunRecord]:
        """Return one locked run-history snapshot for internal status projection."""
        return self._list_runs_unbounded()

    def _list_runs_unbounded(self) -> list[RunRecord]:
        """Return all runs for internal startup reconciliation."""
        with self._locked():
            records = [
                self._read_run_path(path) for path in self.runs_directory.glob("*.json")
            ]
        records.sort(key=lambda item: (item.started_at, str(item.run_id)), reverse=True)
        return records

    def transition(self, run_id: UUID | str, transition: RunTransition) -> RunRecord:
        """Apply one compare-and-swap state transition atomically."""
        run_id = require_uuid(run_id, field="run_id")
        if not isinstance(transition, RunTransition):
            raise TypeError("transition must be a RunTransition")
        with self._locked():
            current = self._read_run_unlocked(run_id)
            if current.state not in transition.expected_states:
                raise InvalidTransitionError("run state does not match expected_states")
            counters = dict(current.counters)
            counters.update(transition.counters)
            candidate = replace(
                current,
                state=transition.new_state,
                result_code=transition.result_code,
                completed_at=transition.completed_at,
                counters=counters,
            )
            self._atomic_write_json(self._run_path(run_id), _run_to_wire(candidate))
        self._notify_status_change()
        return candidate

    def append_diagnostic(self, record: DiagnosticRecord) -> None:
        """Append one immutable diagnostic and trim only records beyond the bound."""
        if not isinstance(record, DiagnosticRecord):
            raise TypeError("record must be a DiagnosticRecord")
        destination = self.diagnostics_directory / f"{record.record_id}.json"
        with self._locked():
            if destination.exists():
                raise InvalidTransitionError("diagnostic already exists")
            self._atomic_write_json(destination, _diagnostic_to_wire(record))
            records = self._diagnostic_paths_unlocked()
            for stale in records[: max(0, len(records) - self.max_diagnostics)]:
                stale.unlink()
            self._fsync_directory(self.diagnostics_directory)

    def _notify_status_change(self) -> None:
        callback = self._status_change_callback
        if callback is None:
            return
        try:
            callback()
        except Exception:
            # Status delivery must never make a completed durable mutation fail.
            return

    def list_diagnostics(
        self,
        query: DiagnosticQuery | None = None,
    ) -> list[DiagnosticRecord]:
        """Return newest structured diagnostics first."""
        query = query or DiagnosticQuery()
        if not isinstance(query, DiagnosticQuery):
            raise TypeError("query must be a DiagnosticQuery")
        with self._locked():
            records = [
                self._read_diagnostic_path(path)
                for path in self._diagnostic_paths_unlocked()
            ]
        records.sort(
            key=lambda item: (item.timestamp, str(item.record_id)),
            reverse=True,
        )
        return [
            record
            for record in records
            if (query.run_id is None or record.run_id == query.run_id)
            and (query.level is None or record.level is query.level)
        ][: query.limit]

    def _run_path(self, run_id: UUID) -> Path:
        return self.runs_directory / f"{run_id}.json"

    def _read_run_unlocked(self, run_id: UUID) -> RunRecord:
        path = self._run_path(run_id)
        if not path.is_file():
            raise RecordNotFoundError("run not found")
        return self._read_run_path(path)

    def _read_run_path(self, path: Path) -> RunRecord:
        try:
            return _run_from_wire(self._read_json(path))
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise RecordCorruptionError("run record is corrupt") from error

    def _read_diagnostic_path(self, path: Path) -> DiagnosticRecord:
        try:
            return _diagnostic_from_wire(self._read_json(path))
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise RecordCorruptionError("diagnostic record is corrupt") from error

    def _diagnostic_paths_unlocked(self) -> list[Path]:
        paths = list(self.diagnostics_directory.glob("*.json"))
        paths.sort(key=lambda path: (path.stat().st_mtime_ns, path.name))
        return paths

    @staticmethod
    def _read_json(path: Path) -> object:
        with path.open("r", encoding="utf-8") as source:
            return json.load(source)

    def _atomic_write_json(self, destination: Path, payload: Mapping[str, Any]) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump(payload, output, separators=(",", ":"), sort_keys=True)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, destination)
            destination.chmod(0o600)
            self._fsync_directory(destination.parent)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class RepositoryMutationLease:
    """One held advisory repository lock and its safe ownership metadata."""

    def __init__(self, file_object: Any, path: Path, run_id: UUID) -> None:
        self._file = file_object
        self.path = path
        self.run_id = run_id
        self._released = False

    def release(self) -> None:
        """Release this lease once; process exit also releases the kernel lock."""
        if self._released:
            return
        _require_file_locking()
        assert fcntl is not None
        self._file.seek(0)
        self._file.truncate()
        self._file.flush()
        os.fsync(self._file.fileno())
        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()
        self._released = True

    def __enter__(self) -> "RepositoryMutationLease":
        return self

    def __exit__(self, *_args: object) -> None:
        self.release()


class RepositoryMutationLock:
    """Coordinate repository mutations across independent system processes."""

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            raise TypeError("root must be a Path")
        self.root = root
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)

    def acquire(
        self,
        target_id: str,
        run_id: UUID | str,
        *,
        blocking: bool = False,
    ) -> RepositoryMutationLease:
        """Acquire the target mutation lease or raise a stable conflict."""
        target_id = require_safe_identifier(target_id, field="target_id")
        run_id = require_uuid(run_id, field="run_id")
        _require_file_locking()
        assert fcntl is not None
        path = self._path(target_id)
        file_object = path.open("a+", encoding="utf-8")
        path.chmod(0o600)
        operation = fcntl.LOCK_EX
        if not blocking:
            operation |= fcntl.LOCK_NB
        try:
            fcntl.flock(file_object.fileno(), operation)
        except BlockingIOError as error:
            file_object.close()
            raise MutationConflictError(
                "another repository mutation is active"
            ) from error
        metadata = {
            "schema_version": 1,
            "run_id": str(run_id),
            "process_id": os.getpid(),
        }
        file_object.seek(0)
        file_object.truncate()
        json.dump(metadata, file_object, separators=(",", ":"), sort_keys=True)
        file_object.write("\n")
        file_object.flush()
        os.fsync(file_object.fileno())
        return RepositoryMutationLease(file_object, path, run_id)

    def is_active(self, target_id: str, run_id: UUID | str) -> bool:
        """Return whether a live process holds this target lease for the run."""
        target_id = require_safe_identifier(target_id, field="target_id")
        run_id = require_uuid(run_id, field="run_id")
        _require_file_locking()
        assert fcntl is not None
        path = self._path(target_id)
        file_object = path.open("a+", encoding="utf-8")
        path.chmod(0o600)
        try:
            try:
                fcntl.flock(
                    file_object.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            except BlockingIOError:
                file_object.seek(0)
                try:
                    metadata = json.load(file_object)
                    stored_run_id = require_uuid(metadata["run_id"], field="run_id")
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    return True
                return stored_run_id == run_id
            else:
                fcntl.flock(file_object.fileno(), fcntl.LOCK_UN)
                return False
        finally:
            file_object.close()

    def clear_stale(self, target_id: str) -> None:
        """Clear metadata only when no process holds the kernel lock."""
        target_id = require_safe_identifier(target_id, field="target_id")
        _require_file_locking()
        assert fcntl is not None
        path = self._path(target_id)
        with path.open("a+", encoding="utf-8") as file_object:
            try:
                fcntl.flock(
                    file_object.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            except BlockingIOError as error:
                raise MutationConflictError(
                    "another repository mutation is active"
                ) from error
            file_object.seek(0)
            file_object.truncate()
            file_object.flush()
            os.fsync(file_object.fileno())
            fcntl.flock(file_object.fileno(), fcntl.LOCK_UN)

    def _path(self, target_id: str) -> Path:
        return self.root / f"{target_id}.lock"


def _require_file_locking() -> None:
    if fcntl is None:
        raise OSError("repository mutation locking is unavailable on this platform")


def reconcile_abandoned_runs(
    store: AtomicRecordStore,
    locks: RepositoryMutationLock,
    *,
    now: datetime | None = None,
) -> list[RunRecord]:
    """Mark non-terminal runs without a live matching lease as interrupted."""
    if not isinstance(store, AtomicRecordStore):
        raise TypeError("store must be an AtomicRecordStore")
    if not isinstance(locks, RepositoryMutationLock):
        raise TypeError("locks must be a RepositoryMutationLock")
    completed_at = now or datetime.now(timezone.utc)
    if (
        completed_at.tzinfo is None
        or completed_at.utcoffset() != timezone.utc.utcoffset(completed_at)
    ):
        raise ValueError("now must be an aware UTC timestamp")
    reconciled: list[RunRecord] = []
    for record in store._list_runs_unbounded():
        if record.state not in _NON_TERMINAL_STATES:
            continue
        if locks.is_active(record.target_id, record.run_id):
            continue
        transition = RunTransition(
            expected_states=frozenset({record.state}),
            new_state=RunState.INTERRUPTED,
            result_code=ResultCode.OPERATION_INTERRUPTED,
            completed_at=max(completed_at, record.started_at),
        )
        try:
            reconciled.append(store.transition(record.run_id, transition))
        except InvalidTransitionError:
            continue
        try:
            locks.clear_stale(record.target_id)
        except MutationConflictError:
            # A newer run may already own the repository lock. Its live lease
            # must not prevent the older abandoned record being reconciled.
            pass
    return reconciled
