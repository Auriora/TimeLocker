"""Linux systemd schedule observation and event-driven deadline checks."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import subprocess
from threading import Event
from typing import Protocol

from .models import RunRecord, RunRecordView, ScheduleSummary
from .status_events import StatusChangeCoordinator
from .types import BackupScheduleHealth, OperationType, RunState


DEFAULT_BACKUP_TIMER = "timelocker-npbackup-migration.timer"
DEFAULT_BACKUP_SERVICE = "timelocker-npbackup-migration.service"
DEFAULT_MISSED_BACKUP_GRACE = timedelta(minutes=15)


class CommandRunner(Protocol):
    """Run one bounded local command without a shell."""

    def __call__(self, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        """Return captured command output."""


def _run_command(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed allowlisted systemctl arguments
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )


@dataclass(frozen=True, slots=True)
class BackupScheduleObservation:
    """Raw, safe scheduler facts used to derive backup health."""

    available: bool
    enabled: bool
    active: bool
    service_active: bool
    last_trigger_at: datetime | None
    next_trigger_at: datetime | None


class SystemdScheduleSummaryProvider:
    """Read the installed backup timer without exposing systemd internals."""

    def __init__(
        self,
        *,
        timer_unit: str = DEFAULT_BACKUP_TIMER,
        service_unit: str = DEFAULT_BACKUP_SERVICE,
        runner: CommandRunner = _run_command,
    ) -> None:
        self._timer_unit = timer_unit
        self._service_unit = service_unit
        self._runner = runner

    def get_schedule_summary(self) -> ScheduleSummary:
        observation = self.observe_backup_schedule()
        return ScheduleSummary(
            next_backup_at=observation.next_trigger_at,
            next_retention_at=None,
        )

    def observe_backup_schedule(self) -> BackupScheduleObservation:
        try:
            properties = self._runner(
                (
                    "systemctl",
                    "show",
                    self._timer_unit,
                    "--property=LoadState,ActiveState,UnitFileState",
                    "--no-pager",
                )
            )
            timers = self._runner(
                (
                    "systemctl",
                    "list-timers",
                    self._timer_unit,
                    "--all",
                    "--output=json",
                    "--no-pager",
                )
            )
            service = self._runner(
                (
                    "systemctl",
                    "show",
                    self._service_unit,
                    "--property=ActiveState",
                    "--no-pager",
                )
            )
        except (OSError, subprocess.SubprocessError):
            return _unavailable_observation()
        if properties.returncode != 0 or timers.returncode != 0:
            return _unavailable_observation()

        values = _parse_properties(properties.stdout)
        if values.get("LoadState") != "loaded":
            return _unavailable_observation()
        timer_row = _parse_timer_row(timers.stdout, self._timer_unit)
        service_values = (
            _parse_properties(service.stdout) if service.returncode == 0 else {}
        )
        return BackupScheduleObservation(
            available=True,
            enabled=values.get("UnitFileState") == "enabled",
            active=values.get("ActiveState") == "active",
            service_active=service_values.get("ActiveState") in {"active", "activating"},
            last_trigger_at=_timestamp_from_microseconds(timer_row.get("last")),
            next_trigger_at=_timestamp_from_microseconds(timer_row.get("next")),
        )


def derive_backup_schedule_health(
    observation: BackupScheduleObservation,
    runs: Iterable[RunRecord | RunRecordView],
    *,
    now: datetime,
    grace: timedelta = DEFAULT_MISSED_BACKUP_GRACE,
) -> BackupScheduleHealth:
    """Reconcile timer facts and run records into one user-facing health state."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if grace <= timedelta(0):
        raise ValueError("grace must be positive")
    if not observation.available:
        return BackupScheduleHealth.UNAVAILABLE
    if not observation.enabled or not observation.active:
        return BackupScheduleHealth.DISABLED
    if observation.service_active:
        return BackupScheduleHealth.HEALTHY
    last_trigger = observation.last_trigger_at
    if last_trigger is None or now <= last_trigger + grace:
        return BackupScheduleHealth.HEALTHY
    earliest_match = last_trigger - timedelta(minutes=5)
    matching_run = any(
        run.operation is OperationType.BACKUP
        and run.started_at >= earliest_match
        and run.started_at <= last_trigger + grace
        and run.state
        in {
            RunState.QUEUED,
            RunState.RUNNING,
            RunState.SUCCEEDED,
            RunState.FAILED,
            RunState.INTERRUPTED,
        }
        for run in runs
    )
    return (
        BackupScheduleHealth.HEALTHY
        if matching_run
        else BackupScheduleHealth.MISSED
    )


class ScheduleDeadlineMonitor:
    """Publish one invalidation after each known backup deadline plus grace."""

    def __init__(
        self,
        provider: SystemdScheduleSummaryProvider,
        coordinator: StatusChangeCoordinator,
        *,
        clock: Callable[[], datetime],
        grace: timedelta = DEFAULT_MISSED_BACKUP_GRACE,
    ) -> None:
        self._provider = provider
        self._coordinator = coordinator
        self._clock = clock
        self._grace = grace

    def run(self, stop_event: Event) -> None:
        while not stop_event.is_set():
            observation = self._provider.observe_backup_schedule()
            next_trigger = observation.next_trigger_at
            if (
                not observation.available
                or not observation.enabled
                or not observation.active
                or next_trigger is None
            ):
                stop_event.wait()
                return
            delay = max(
                0.0,
                (next_trigger + self._grace - self._clock()).total_seconds(),
            )
            if stop_event.wait(delay):
                return
            self._coordinator.schedule_changed()


def _parse_properties(output: str) -> dict[str, str]:
    return {
        key: value
        for line in output.splitlines()
        if "=" in line
        for key, value in (line.split("=", 1),)
    }


def _parse_timer_row(output: str, unit: str) -> dict[str, object]:
    try:
        value = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(value, list):
        return {}
    return next(
        (
            row
            for row in value
            if isinstance(row, dict) and row.get("unit") == unit
        ),
        {},
    )


def _timestamp_from_microseconds(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return datetime.fromtimestamp(value / 1_000_000, tz=UTC)


def _unavailable_observation() -> BackupScheduleObservation:
    return BackupScheduleObservation(False, False, False, False, None, None)


__all__ = [
    "BackupScheduleObservation",
    "DEFAULT_BACKUP_SERVICE",
    "DEFAULT_BACKUP_TIMER",
    "DEFAULT_MISSED_BACKUP_GRACE",
    "ScheduleDeadlineMonitor",
    "SystemdScheduleSummaryProvider",
    "derive_backup_schedule_health",
]
