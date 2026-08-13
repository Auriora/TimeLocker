"""Daemonless sanitized status snapshot persistence and observation."""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
from queue import Empty, Full, Queue
import stat
from threading import Event
from uuid import uuid4

from .models import StatusSnapshot


DEFAULT_STATUS_SNAPSHOT_PATH = Path("/run/timelocker/status.json")
MAX_STATUS_SNAPSHOT_BYTES = 1_048_576


class StatusSnapshotUnavailable(RuntimeError):
    """The sanitized status snapshot is missing or cannot be trusted."""


class AtomicStatusSnapshotStore:
    """Read and atomically replace one exact, sanitized status snapshot."""

    def __init__(
        self,
        path: Path = DEFAULT_STATUS_SNAPSHOT_PATH,
        *,
        expected_owner_uid: int = 0,
        group_gid: int | None = None,
    ) -> None:
        if not isinstance(path, Path) or not path.is_absolute():
            raise ValueError("status snapshot path must be absolute")
        if type(expected_owner_uid) is not int or expected_owner_uid < 0:
            raise ValueError("expected_owner_uid must be a non-negative integer")
        self.path = path
        self.expected_owner_uid = expected_owner_uid
        if group_gid is not None and (type(group_gid) is not int or group_gid < 0):
            raise ValueError("group_gid must be a non-negative integer")
        self.group_gid = group_gid

    def read(self) -> StatusSnapshot:
        """Read without producing any state-change notification."""
        descriptor = -1
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(self.path, flags)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise StatusSnapshotUnavailable("system status is unavailable")
            if metadata.st_uid != self.expected_owner_uid or metadata.st_mode & 0o022:
                raise StatusSnapshotUnavailable("system status is unavailable")
            if metadata.st_size > MAX_STATUS_SNAPSHOT_BYTES:
                raise StatusSnapshotUnavailable("system status is unavailable")
            blocks: list[bytes] = []
            remaining = MAX_STATUS_SNAPSHOT_BYTES + 1
            while remaining > 0:
                block = os.read(descriptor, min(65_536, remaining))
                if not block:
                    break
                blocks.append(block)
                remaining -= len(block)
            raw = b"".join(blocks)
            if len(raw) > MAX_STATUS_SNAPSHOT_BYTES:
                raise StatusSnapshotUnavailable("system status is unavailable")
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict) or set(value) != {
                "schema_version",
                "snapshot",
            } or value["schema_version"] != 1:
                raise ValueError("invalid status file")
            return StatusSnapshot.from_mapping(value["snapshot"])
        except StatusSnapshotUnavailable:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            raise StatusSnapshotUnavailable("system status is unavailable") from None
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def write(self, snapshot: StatusSnapshot) -> None:
        """Publish one allowlisted snapshot with atomic replacement."""
        if not isinstance(snapshot, StatusSnapshot):
            raise TypeError("snapshot must be a StatusSnapshot")
        parent_existed = self.path.parent.exists()
        self.path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
        if not parent_existed:
            self.path.parent.chmod(0o750)
        parent = self.path.parent.lstat()
        if (
            not stat.S_ISDIR(parent.st_mode)
            or stat.S_ISLNK(parent.st_mode)
            or parent.st_uid != self.expected_owner_uid
            or parent.st_mode & 0o022
        ):
            raise PermissionError("status directory is not trusted")
        payload = (
            json.dumps(
                {"schema_version": 1, "snapshot": snapshot.to_wire()},
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if len(payload) > MAX_STATUS_SNAPSHOT_BYTES:
            raise ValueError("status snapshot exceeds configured bound")
        temporary = self.path.with_name(
            f".{self.path.name}.{os.getpid()}.{uuid4().hex}.tmp"
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o640)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o640)
            if self.group_gid is not None:
                os.chown(temporary, self.expected_owner_uid, self.group_gid)
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


class StatusSnapshotFileWatcher:
    """Yield the initial status and direct filesystem changes without polling."""

    def __init__(self, store: AtomicStatusSnapshotStore | None = None) -> None:
        self.store = store or AtomicStatusSnapshotStore()

    def snapshots(self, stop_event: Event) -> Iterator[StatusSnapshot]:
        if not isinstance(stop_event, Event):
            raise TypeError("stop_event must be a threading.Event")
        try:
            from watchdog.events import FileSystemEvent, FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError as error:  # pragma: no cover - packaging failure
            raise StatusSnapshotUnavailable("system status is unavailable") from error

        changes: Queue[bool] = Queue(maxsize=1)
        watched = self.store.path

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event: FileSystemEvent) -> None:
                # Reads generate open/close events on Linux. Ignoring those is
                # the invariant that prevents a read-notify-read CPU loop.
                if event.event_type not in {"created", "modified", "moved"}:
                    return
                paths = {Path(event.src_path)}
                destination = getattr(event, "dest_path", None)
                if destination:
                    paths.add(Path(destination))
                if watched not in paths:
                    return
                try:
                    changes.put_nowait(True)
                except Full:
                    pass

        observer = Observer()
        observer.schedule(Handler(), str(watched.parent), recursive=False)
        observer.start()
        try:
            # Register observation before the initial read so an atomic replace
            # cannot disappear into a read/watch setup race.
            try:
                initial = self.store.read()
            except StatusSnapshotUnavailable:
                initial = None
            if initial is not None:
                yield initial
            while not stop_event.is_set():
                try:
                    changes.get(timeout=0.25)
                except Empty:
                    continue
                try:
                    yield self.store.read()
                except StatusSnapshotUnavailable:
                    continue
        finally:
            observer.stop()
            observer.join(timeout=1.0)
