"""Atomic daemonless status-file contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import stat
from threading import Event
from uuid import UUID

import pytest

from TimeLocker.system_control.models import StatusRevision, StatusSnapshot
from TimeLocker.system_control.status_snapshot import (
    AtomicStatusSnapshotStore,
    StatusSnapshotFileWatcher,
    StatusSnapshotUnavailable,
)
from TimeLocker.system_control.types import BackendStatus


def _snapshot(sequence: int) -> StatusSnapshot:
    return StatusSnapshot(
        revision=StatusRevision(
            UUID("526719f9-4c46-42ac-b286-2623079bc335"), sequence
        ),
        backend_status=BackendStatus.AVAILABLE,
        active_operations=sequence,
    )


def _store(path: Path) -> AtomicStatusSnapshotStore:
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    path.parent.chmod(0o750)
    return AtomicStatusSnapshotStore(path, expected_owner_uid=os.getuid())


@pytest.mark.unit
def test_atomic_status_round_trip_is_group_readable_and_read_only(tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "status.json"
    store = _store(path)
    store.write(_snapshot(1))
    before = path.stat()

    assert store.read() == _snapshot(1)
    after = path.stat()
    assert stat.S_IMODE(after.st_mode) == 0o640
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)


@pytest.mark.unit
def test_status_reader_rejects_writable_symlink_and_invalid_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "status.json"
    store = _store(path)
    store.write(_snapshot(0))
    path.chmod(0o660)
    with pytest.raises(StatusSnapshotUnavailable, match="unavailable"):
        store.read()

    target = tmp_path / "target.json"
    path.rename(target)
    path.symlink_to(target)
    with pytest.raises(StatusSnapshotUnavailable, match="unavailable"):
        store.read()

    path.unlink()
    path.write_text('{"schema_version":2,"snapshot":{}}')
    path.chmod(0o640)
    with pytest.raises(StatusSnapshotUnavailable, match="unavailable"):
        store.read()


@pytest.mark.unit
def test_watcher_registers_before_initial_read_and_observes_atomic_replace(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path / "runtime" / "status.json")
    store.write(_snapshot(0))
    stop = Event()
    snapshots = StatusSnapshotFileWatcher(store).snapshots(stop)
    assert next(snapshots) == _snapshot(0)

    with ThreadPoolExecutor(max_workers=1) as executor:
        changed = executor.submit(next, snapshots)
        store.write(_snapshot(1))
        assert changed.result(timeout=3) == _snapshot(1)

    stop.set()
    snapshots.close()


@pytest.mark.unit
def test_watcher_waits_for_first_snapshot_when_status_is_initially_absent(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path / "runtime" / "status.json")
    stop = Event()
    snapshots = StatusSnapshotFileWatcher(store).snapshots(stop)

    with ThreadPoolExecutor(max_workers=1) as executor:
        created = executor.submit(next, snapshots)
        store.write(_snapshot(1))
        assert created.result(timeout=3) == _snapshot(1)

    stop.set()
    snapshots.close()
