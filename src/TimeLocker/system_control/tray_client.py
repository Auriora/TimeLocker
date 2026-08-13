"""Tray-facing status and action client for TimeLocker system control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Event
from typing import Callable, TypeVar

from .client import SystemControlClientError, UnixSocketSystemControlClient
from .interfaces import SystemControlClient
from .models import BackupActionRequest, RetentionActionRequest, StatusSnapshot
from .status_snapshot import (
    StatusSnapshotFileWatcher,
    StatusSnapshotUnavailable,
)
from .types import (
    BackendStatus,
    BackupScheduleHealth,
    ProtocolErrorCode,
    ResponseStatus,
    RunState,
)


ALLOWED_TRAY_ACTIONS = frozenset(
    {"status", "backup_now", "retention_now", "quit"}
)
_BACKEND_RETRY_DELAY_SECONDS = 2.0
_BACKEND_RETRY_MAX_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class TrayDisplayState:
    """Minimal projection used by the tray process to render user status."""

    status: str
    tooltip: str
    health: str
    activity: str
    active_operations: int
    backend_available: bool
    last_successful_backup_completed_at: datetime | None
    latest_backup_started_at: datetime | None
    latest_backup_status: str | None
    latest_retention_started_at: datetime | None
    latest_retention_status: str | None
    next_backup_at: datetime | None
    next_retention_at: datetime | None


class TrayBackendUnavailable(RuntimeError):
    """Raised when the protected local backend is not currently reachable."""


_ClientFactory = Callable[[], SystemControlClient]
_T = TypeVar("_T")


class TrayStatusSubscriptionClient:
    """Consume the sanitized status file without a privileged event service."""

    def __init__(
        self,
        *,
        watcher: StatusSnapshotFileWatcher | None = None,
    ) -> None:
        self._watcher = watcher or StatusSnapshotFileWatcher()

    def serve(
        self,
        stop_event: Event,
        *,
        on_snapshot: Callable[[StatusSnapshot], None],
        on_unavailable: Callable[[str], None] | None = None,
    ) -> None:
        """Consume invalidations and publish coherent snapshots to the tray."""
        if not isinstance(stop_event, Event):
            raise TypeError("stop_event must be a threading.Event")
        try:
            applied = None
            for snapshot in self._watcher.snapshots(stop_event):
                if stop_event.is_set():
                    return
                if (
                    applied is not None
                    and snapshot.revision.session_id == applied.session_id
                    and snapshot.revision.sequence <= applied.sequence
                ):
                    continue
                applied = snapshot.revision
                on_snapshot(snapshot)
        except StatusSnapshotUnavailable:
            if on_unavailable is not None:
                on_unavailable("unavailable")


class TrayControlClient:
    """Small client that powers the standalone tray process.

    The tray process must remain independent from regular CLI execution and
    should degrade gracefully whenever the protected backend is missing.
    """

    def __init__(
        self,
        *,
        client_factory: _ClientFactory | None = None,
        target_id: str = "production",
        retention_policy_fingerprint: str | None = None,
        max_history_runs: int = 25,
        base_retry_delay: float = _BACKEND_RETRY_DELAY_SECONDS,
        max_retry_delay: float = _BACKEND_RETRY_MAX_SECONDS,
    ) -> None:
        if max_history_runs < 1 or max_history_runs > 1_000:
            raise ValueError("max_history_runs must be between 1 and 1000")
        if base_retry_delay <= 0 or max_retry_delay < base_retry_delay:
            raise ValueError("retry delays are invalid")
        self._client_factory = client_factory or UnixSocketSystemControlClient
        self._target_id = target_id
        self._retention_policy_fingerprint = retention_policy_fingerprint
        self._max_history_runs = max_history_runs
        self._base_retry_delay = base_retry_delay
        self._max_retry_delay = max_retry_delay
        self._client: SystemControlClient = self._client_factory()
        self._retry_delay: float = base_retry_delay
        self._retry_at: float = 0.0

    @property
    def allowed_actions(self) -> frozenset[str]:
        return ALLOWED_TRAY_ACTIONS

    def refresh_status(self) -> TrayDisplayState:
        """Return a tray-safe status snapshot for the current backend state."""
        try:
            snapshot = self._with_backend(
                lambda backend: backend.get_status_snapshot()
            )
        except TrayBackendUnavailable:
            return self.unavailable_state(
                "TimeLocker - System backend unavailable",
                backend_available=False,
            )
        except SystemControlClientError as error:
            if error.status is ResponseStatus.DENIED:
                return self.unavailable_state(
                    "TimeLocker - Access denied",
                    backend_available=True,
                )
            raise
        return self.project_snapshot(snapshot)

    @staticmethod
    def project_snapshot(snapshot: StatusSnapshot) -> TrayDisplayState:
        """Project one coherent backend snapshot into safe desktop fields."""
        if not isinstance(snapshot, StatusSnapshot):
            raise TypeError("snapshot must be a StatusSnapshot")
        backup_active = (
            snapshot.latest_backup is not None
            and snapshot.latest_backup.state in {RunState.QUEUED, RunState.RUNNING}
        )
        retention_active = (
            snapshot.latest_retention is not None
            and snapshot.latest_retention.state
            in {RunState.QUEUED, RunState.RUNNING}
        )
        if snapshot.backend_status is BackendStatus.UNAVAILABLE:
            status = "warning"
            health = "Backend unavailable"
        elif snapshot.backup_schedule_health is BackupScheduleHealth.DISABLED:
            status = "warning"
            health = "Schedule disabled"
        elif snapshot.backup_schedule_health is BackupScheduleHealth.MISSED:
            status = "error"
            health = "Backup missed"
        elif snapshot.backup_schedule_health is BackupScheduleHealth.UNAVAILABLE:
            status = "warning"
            health = "Schedule unavailable"
        elif (
            snapshot.latest_backup is not None
            and snapshot.latest_backup.state
            in {RunState.FAILED, RunState.INTERRUPTED}
        ):
            status = "error"
            health = "Backup failed"
        else:
            status = "success"
            health = "Healthy"

        if backup_active and retention_active:
            activity = "Backup and retention running"
        elif backup_active:
            activity = "Backup running"
        elif retention_active:
            activity = "Retention running"
        elif snapshot.active_operations:
            activity = "Operation running"
        else:
            activity = "Idle"

        if activity != "Idle":
            status = "running"
        elif health == "Healthy" and snapshot.latest_backup is None:
            status = "warning"

        tooltip_lines = [
            "TimeLocker",
            f"State: {health}",
            f"Activity: {activity}",
            "Last Backup: "
            + _format_local_time(snapshot.last_successful_backup_completed_at),
        ]
        return TrayDisplayState(
            status=status,
            tooltip="\n".join(tooltip_lines),
            health=health,
            activity=activity,
            active_operations=snapshot.active_operations,
            backend_available=snapshot.backend_status is BackendStatus.AVAILABLE,
            last_successful_backup_completed_at=(
                snapshot.last_successful_backup_completed_at
            ),
            latest_backup_started_at=(
                snapshot.latest_backup.started_at
                if snapshot.latest_backup is not None
                else None
            ),
            latest_backup_status=(
                snapshot.latest_backup.safe_summary
                if snapshot.latest_backup is not None
                else None
            ),
            latest_retention_started_at=(
                snapshot.latest_retention.started_at
                if snapshot.latest_retention is not None
                else None
            ),
            latest_retention_status=(
                snapshot.latest_retention.safe_summary
                if snapshot.latest_retention is not None
                else None
            ),
            next_backup_at=snapshot.next_backup_at,
            next_retention_at=snapshot.next_retention_at,
        )

    def perform_action(
        self, action: str, *, dry_run_retention: bool = False
    ) -> TrayDisplayState | None:
        """Execute a supported tray action and refresh status when possible."""
        if action not in ALLOWED_TRAY_ACTIONS:
            raise ValueError(f"unsupported tray action: {action}")
        if action in {"status", "quit"}:
            if action == "quit":
                return None
            return self.refresh_status()
        if action == "backup_now":
            self._with_backend(
                lambda backend: backend.request_backup(
                    BackupActionRequest(target_id=self._target_id)
                )
            )
            return self.refresh_status()

        if self._retention_policy_fingerprint is None:
            raise ValueError(
                "retention policy fingerprint is required to request retention"
            )
        self._with_backend(
            lambda backend: backend.request_retention(
                RetentionActionRequest(
                    policy_fingerprint=self._retention_policy_fingerprint,
                    dry_run=dry_run_retention,
                )
            )
        )
        return self.refresh_status()

    def _with_backend(self, callback: Callable[[SystemControlClient], _T]) -> _T:
        """Protect tray polling from unavailable backend sessions."""
        from time import monotonic

        if monotonic() < self._retry_at:
            raise TrayBackendUnavailable("backend temporarily unavailable")
        try:
            result = callback(self._client)
        except SystemControlClientError as error:
            if error.error_code is ProtocolErrorCode.SYSTEM_BACKEND_UNAVAILABLE:
                self._retry_at = monotonic() + self._retry_delay
                self._retry_delay = min(self._retry_delay * 2.0, self._max_retry_delay)
                raise TrayBackendUnavailable(
                    "backend temporarily unavailable"
                ) from error
            raise
        self._retry_at = 0.0
        self._retry_delay = self._base_retry_delay
        return result

    @staticmethod
    def unavailable_state(
        tooltip: str,
        *,
        backend_available: bool,
    ) -> TrayDisplayState:
        return TrayDisplayState(
            status="warning",
            tooltip=tooltip,
            health=(
                "Access denied" if backend_available else "Backend unavailable"
            ),
            activity="Idle" if backend_available else "Connecting",
            active_operations=0,
            backend_available=backend_available,
            last_successful_backup_completed_at=None,
            latest_backup_started_at=None,
            latest_backup_status=None,
            latest_retention_started_at=None,
            latest_retention_status=None,
            next_backup_at=None,
            next_retention_at=None,
        )


def _format_local_time(value: datetime | None) -> str:
    if value is None:
        return "Never"
    return value.astimezone().strftime("%Y-%m-%d %H:%M %Z").rstrip()
