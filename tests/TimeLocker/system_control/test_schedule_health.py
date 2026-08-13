"""Schedule-health and native protected-record invalidation tests."""

from datetime import UTC, datetime, timedelta
import subprocess
from threading import Event, Thread
from time import monotonic
from uuid import uuid4

import pytest

from TimeLocker.system_control.models import RunRecord
from TimeLocker.system_control.schedule_health import (
    BackupScheduleObservation,
    ScheduleDeadlineMonitor,
    SystemdScheduleSummaryProvider,
    derive_backup_schedule_health,
)
from TimeLocker.system_control.status_events import (
    FileSystemProtectedStateWatcher,
    StatusWatchSignal,
)
from TimeLocker.system_control.storage import AtomicRecordStore
from TimeLocker.system_control.types import (
    BackupScheduleHealth,
    OperationTrigger,
    OperationType,
    ResultCode,
    RunState,
)


NOW = datetime(2026, 7, 28, 6, 0, tzinfo=UTC)


def _observation(**overrides: object) -> BackupScheduleObservation:
    values = {
        "available": True,
        "enabled": True,
        "active": True,
        "service_active": False,
        "last_trigger_at": NOW - timedelta(hours=2),
        "next_trigger_at": NOW + timedelta(hours=22),
    }
    values.update(overrides)
    return BackupScheduleObservation(**values)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("observation", "expected"),
    (
        (
            _observation(available=False),
            BackupScheduleHealth.UNAVAILABLE,
        ),
        (
            _observation(enabled=False),
            BackupScheduleHealth.DISABLED,
        ),
        (
            _observation(active=False),
            BackupScheduleHealth.DISABLED,
        ),
        (
            _observation(),
            BackupScheduleHealth.MISSED,
        ),
        (
            _observation(last_trigger_at=NOW - timedelta(minutes=5)),
            BackupScheduleHealth.HEALTHY,
        ),
    ),
)
def test_schedule_health_is_derived_from_timer_and_grace(
    observation: BackupScheduleObservation,
    expected: BackupScheduleHealth,
) -> None:
    assert derive_backup_schedule_health(observation, (), now=NOW) is expected


@pytest.mark.unit
def test_run_started_for_last_trigger_prevents_false_missed_state() -> None:
    run = RunRecord(
        run_id=uuid4(),
        operation=OperationType.BACKUP,
        trigger=OperationTrigger.SCHEDULED,
        target_id="production",
        started_at=NOW - timedelta(hours=2),
        completed_at=NOW - timedelta(hours=1, minutes=55),
        state=RunState.FAILED,
        result_code=ResultCode.OPERATION_FAILED,
    )

    assert (
        derive_backup_schedule_health(_observation(), (run,), now=NOW)
        is BackupScheduleHealth.HEALTHY
    )


@pytest.mark.unit
def test_late_manual_backup_does_not_erase_a_missed_occurrence() -> None:
    run = RunRecord(
        run_id=uuid4(),
        operation=OperationType.BACKUP,
        trigger=OperationTrigger.EXPLICIT,
        target_id="production",
        started_at=NOW - timedelta(hours=1),
        completed_at=NOW - timedelta(minutes=55),
        state=RunState.SUCCEEDED,
        result_code=ResultCode.BACKUP_SUCCEEDED,
    )

    assert (
        derive_backup_schedule_health(_observation(), (run,), now=NOW)
        is BackupScheduleHealth.MISSED
    )


@pytest.mark.unit
def test_systemd_provider_parses_numeric_timer_timestamps() -> None:
    responses = iter(
        (
            subprocess.CompletedProcess(
                (),
                0,
                "LoadState=loaded\nActiveState=active\nUnitFileState=enabled\n",
                "",
            ),
            subprocess.CompletedProcess(
                (),
                0,
                (
                    '[{"next":1785292200000000,"last":1785205806710183,'
                    '"unit":"timelocker-npbackup-migration.timer"}]'
                ),
                "",
            ),
            subprocess.CompletedProcess((), 0, "ActiveState=inactive\n", ""),
        )
    )
    provider = SystemdScheduleSummaryProvider(
        runner=lambda _command: next(responses)
    )

    observation = provider.observe_backup_schedule()

    assert observation.available is True
    assert observation.enabled is True
    assert observation.active is True
    assert observation.next_trigger_at == datetime.fromtimestamp(
        1785292200,
        tz=UTC,
    )
    assert observation.last_trigger_at == datetime.fromtimestamp(
        1785205806.710183,
        tz=UTC,
    )


@pytest.mark.unit
def test_schedule_deadline_publishes_once_without_fixed_polling() -> None:
    observations = iter(
        (
            _observation(next_trigger_at=NOW - timedelta(minutes=20)),
            _observation(enabled=False, next_trigger_at=None),
        )
    )

    class Provider:
        def observe_backup_schedule(self) -> BackupScheduleObservation:
            return next(observations)

    class Coordinator:
        calls = 0

        def schedule_changed(self) -> None:
            self.calls += 1

    class StopSignal:
        def is_set(self) -> bool:
            return False

        def wait(self, timeout: float | None = None) -> bool:
            return timeout is None

    coordinator = Coordinator()
    monitor = ScheduleDeadlineMonitor(
        Provider(),  # type: ignore[arg-type]
        coordinator,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    monitor.run(StopSignal())  # type: ignore[arg-type]

    assert coordinator.calls == 1


@pytest.mark.unit
def test_filesystem_watcher_reports_external_record_change(tmp_path) -> None:
    record_root = tmp_path / "records"
    store = AtomicRecordStore(record_root)
    root = record_root / "runs"
    stop_event = Event()
    watcher = FileSystemProtectedStateWatcher((root,))
    observed: list[StatusWatchSignal] = []

    def consume() -> None:
        for signal in watcher.events(stop_event):
            observed.append(signal)
            stop_event.set()

    thread = Thread(target=consume)
    thread.start()
    try:
        deadline = monotonic() + 1.5
        attempt = 0
        while not observed and monotonic() < deadline:
            store.create_run(
                RunRecord(
                    run_id=uuid4(),
                    operation=OperationType.BACKUP,
                    trigger=OperationTrigger.SCHEDULED,
                    target_id=f"external-{attempt}",
                    started_at=NOW,
                    state=RunState.RUNNING,
                    result_code=ResultCode.OPERATION_RUNNING,
                )
            )
            attempt += 1
            stop_event.wait(0.02)
        thread.join(timeout=2)
    finally:
        stop_event.set()
        thread.join(timeout=2)

    assert observed == [StatusWatchSignal.CHANGED]
