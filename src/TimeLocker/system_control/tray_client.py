"""Tray-facing status and action client for TimeLocker system control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, TypeVar

from .client import SystemControlClientError, UnixSocketSystemControlClient
from .interfaces import SystemControlClient
from .models import RunQuery, RunRecordView, ScheduleSummary
from .models import RetentionActionRequest, BackupActionRequest
from .types import OperationType, ProtocolErrorCode, ResponseStatus, RunState


ALLOWED_TRAY_ACTIONS = frozenset(
    {"status", "backup_now", "retention_now", "open_ui", "quit"}
)
_BACKEND_RETRY_DELAY_SECONDS = 2.0
_BACKEND_RETRY_MAX_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class TrayDisplayState:
    """Minimal projection used by the tray process to render user status."""

    status: str
    tooltip: str
    active_operations: int
    backend_available: bool
    last_backup_started_at: datetime | None
    last_backup_status: str | None
    last_retention_started_at: datetime | None
    last_retention_status: str | None
    next_backup_at: datetime | None
    next_retention_at: datetime | None
    repository_count: int


class TrayBackendUnavailable(RuntimeError):
    """Raised when the protected local backend is not currently reachable."""


_ClientFactory = Callable[[], SystemControlClient]
_T = TypeVar("_T")


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

        def _build_from_runs(
            runs: list[RunRecordView],
            summary: ScheduleSummary,
        ) -> TrayDisplayState:
            active_operations = self._count_active_runs(runs)
            backup_runs = [run for run in runs if run.operation is OperationType.BACKUP]
            retention_runs = [
                run for run in runs if run.operation is OperationType.RETENTION
            ]
            latest_backup = self._latest_run(backup_runs)
            latest_retention = self._latest_run(retention_runs)

            return TrayDisplayState(
                status=self._status_from_runs(runs),
                tooltip=self._build_tooltip(
                    latest_backup, latest_retention, summary, active_operations
                ),
                active_operations=active_operations,
                backend_available=True,
                last_backup_started_at=latest_backup.started_at
                if latest_backup
                else None,
                last_backup_status=latest_backup.safe_summary
                if latest_backup
                else None,
                last_retention_started_at=(
                    latest_retention.started_at if latest_retention else None
                ),
                last_retention_status=(
                    latest_retention.safe_summary if latest_retention else None
                ),
                next_backup_at=summary.next_backup_at,
                next_retention_at=summary.next_retention_at,
                repository_count=len({run.target_id for run in runs}),
            )

        try:
            runs = self._with_backend(
                lambda backend: backend.list_runs(
                    RunQuery(limit=self._max_history_runs)
                )
            )
            summary = self._with_backend(lambda backend: backend.get_schedule_summary())
        except TrayBackendUnavailable:
            return self._unavailable_state(
                "TimeLocker - System backend unavailable",
                backend_available=False,
            )
        except SystemControlClientError as error:
            if error.status is ResponseStatus.DENIED:
                return self._unavailable_state(
                    "TimeLocker - Access denied",
                    backend_available=True,
                )
            raise
        return _build_from_runs(runs, summary)

    def perform_action(
        self, action: str, *, dry_run_retention: bool = False
    ) -> TrayDisplayState | None:
        """Execute a supported tray action and refresh status when possible."""
        if action not in ALLOWED_TRAY_ACTIONS:
            raise ValueError(f"unsupported tray action: {action}")
        if action in {"status", "open_ui", "quit"}:
            if action == "quit":
                return None
            if action == "open_ui":
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
    def _unavailable_state(
        tooltip: str,
        *,
        backend_available: bool,
    ) -> TrayDisplayState:
        return TrayDisplayState(
            status="warning",
            tooltip=tooltip,
            active_operations=0,
            backend_available=backend_available,
            last_backup_started_at=None,
            last_backup_status=None,
            last_retention_started_at=None,
            last_retention_status=None,
            next_backup_at=None,
            next_retention_at=None,
            repository_count=0,
        )

    def _count_active_runs(self, runs: list[RunRecordView]) -> int:
        return sum(1 for run in runs if run.state is RunState.RUNNING)

    def _latest_run(self, runs: list[RunRecordView]) -> RunRecordView | None:
        if not runs:
            return None
        return sorted(runs, key=lambda run: run.started_at, reverse=True)[0]

    def _status_from_runs(self, runs: list[RunRecordView]) -> str:
        if any(run.state is RunState.RUNNING for run in runs):
            return "running"
        if any(run.state is RunState.FAILED for run in runs):
            return "error"
        if any(run.state is RunState.INTERRUPTED for run in runs):
            return "error"
        if any(run.state is RunState.SKIPPED for run in runs):
            return "warning"
        if any(run.state is RunState.SUCCEEDED for run in runs):
            return "success"
        return "idle"

    def _build_tooltip(
        self,
        latest_backup: RunRecordView | None,
        latest_retention: RunRecordView | None,
        summary: ScheduleSummary,
        active_operations: int,
    ) -> str:
        lines: list[str] = ["TimeLocker"]
        if active_operations:
            lines.append(f"Active: {active_operations}")
        if latest_backup:
            lines.append(f"Last backup: {latest_backup.started_at.isoformat()}")
            lines.append(f"Backup status: {latest_backup.safe_summary}")
        if latest_retention:
            lines.append(f"Last retention: {latest_retention.started_at.isoformat()}")
            lines.append(f"Retention status: {latest_retention.safe_summary}")
        if summary.next_backup_at:
            lines.append(f"Next backup: {summary.next_backup_at.isoformat()}")
        if summary.next_retention_at:
            lines.append(f"Next retention: {summary.next_retention_at.isoformat()}")
        return "\n".join(lines) if len(lines) > 1 else "TimeLocker - Idle"
