"""Linux backend composition and entrypoint for system-control operations."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import socket
import stat
from threading import Event, Thread
from types import FrameType
from typing import Protocol
from uuid import UUID, uuid4

from .dispatcher import AuditEvent, AuditSink, LocalControlDispatcher
from .interfaces import GroupMembershipResolver
from .linux_adapter import (
    LinuxNssGroupMembershipResolver,
    LinuxStatusEventTransport,
    LinuxUnixSocketTransport,
)
from .models import (
    ActionReceipt,
    BackupActionRequest,
    DiagnosticQuery,
    DiagnosticRecord,
    DiagnosticView,
    PROTOCOL_VERSION,
    RetentionPolicy,
    RunQuery,
    RunRecordView,
    ScheduleSummary,
    StatusRevision,
    StatusSnapshot,
    SystemPolicy,
)
from .policy_loader import load_system_policy
from .production_backup import (
    SystemBackupRunCoordinator,
    SystemdBackupMutationAdapter,
)
from .production_retention import (
    DEFAULT_PRODUCTION_TARGET_PATH,
    DEFAULT_RETENTION_ENABLE_MARKER,
    ProductionRetentionTarget,
    TimeLockerCliRetentionAdapter,
    load_production_retention_components,
    require_retention_enable_marker,
)
from .retention import (
    RetentionAdapter,
    RetentionExecutionResult,
    RetentionExecutor,
    RetentionPlan,
    RetentionRequestHandler,
    RetentionTriggerCoordinator,
    RetentionTriggerStore,
)
from .storage import (
    AtomicRecordStore,
    RepositoryMutationLock,
    reconcile_abandoned_runs,
)
from .status_events import BoundedStatusEventBroker, StatusChangeCoordinator
from .types import (
    BackendStatus,
    DiagnosticCode,
    DiagnosticComponent,
    DiagnosticLevel,
    OperationType,
    OperationTrigger,
    RunState,
    SystemAction,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BackupMutationAdapter(Protocol):
    """Execute one allowlisted system backup request."""

    def request_backup(
        self,
        request: BackupActionRequest,
        *,
        request_id: UUID,
    ) -> ActionReceipt:
        """Return a bounded receipt for the requested backup."""


class RetentionPlanProvider(Protocol):
    """Resolve the live retention plan for the protected system repository."""

    def resolve_retention_plan(self, policy: SystemPolicy) -> RetentionPlan:
        """Return the exact plan that matches the installed system policy."""


class ScheduleSummaryProvider(Protocol):
    """Project the next scheduled backup and retention times."""

    def get_schedule_summary(self) -> ScheduleSummary:
        """Return a safe schedule projection."""


class FailClosedBackupMutationAdapter:
    """Default backup adapter that intentionally exposes no mutation path."""

    def request_backup(
        self,
        request: BackupActionRequest,
        *,
        request_id: UUID,
    ) -> ActionReceipt:
        raise RuntimeError("system backup mutation is unavailable")


class FailClosedRetentionAdapter:
    """Default retention adapter that intentionally exposes no mutation path."""

    def execute(
        self,
        plan: RetentionPlan,
        *,
        dry_run: bool,
    ) -> RetentionExecutionResult:
        raise RuntimeError("system retention mutation is unavailable")


class FailClosedRetentionPlanProvider:
    """Default retention-plan provider that refuses to invent live config."""

    def resolve_retention_plan(self, policy: SystemPolicy) -> RetentionPlan:
        raise RuntimeError("system retention plan is unavailable")


@dataclass(frozen=True, slots=True)
class StaticScheduleSummaryProvider:
    """Safe default when no live scheduler projection is available."""

    summary: ScheduleSummary = field(
        default_factory=lambda: ScheduleSummary(
            next_backup_at=None,
            next_retention_at=None,
        )
    )

    def get_schedule_summary(self) -> ScheduleSummary:
        return self.summary


@dataclass(frozen=True, slots=True)
class LinuxBackendPaths:
    """Filesystem locations owned by the privileged local backend."""

    policy_path: Path
    record_root: Path
    lock_root: Path
    trigger_root: Path
    audit_log_path: Path
    expected_owner: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "policy_path",
            "record_root",
            "lock_root",
            "trigger_root",
            "audit_log_path",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, Path):
                raise TypeError(f"{field_name} must be a Path")
        if type(self.expected_owner) is not int or self.expected_owner < 0:
            raise ValueError("expected_owner must be a non-negative UID")

    @classmethod
    def from_state_root(
        cls,
        *,
        policy_path: Path,
        state_root: Path,
        expected_owner: int = 0,
    ) -> "LinuxBackendPaths":
        if not isinstance(state_root, Path):
            raise TypeError("state_root must be a Path")
        return cls(
            policy_path=policy_path,
            record_root=state_root / "records",
            lock_root=state_root / "locks",
            trigger_root=state_root / "retention-triggers",
            audit_log_path=state_root / "audit" / "events.jsonl",
            expected_owner=expected_owner,
        )


class RootOnlyJsonlAuditSink(AuditSink):
    """Persist bounded audit decisions in a root-only JSONL file."""

    def __init__(
        self,
        path: Path,
        *,
        expected_owner: int = 0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(path, Path):
            raise TypeError("path must be a Path")
        if type(expected_owner) is not int or expected_owner < 0:
            raise ValueError("expected_owner must be a non-negative UID")
        self.path = path
        self.expected_owner = expected_owner
        self._clock = clock or _utc_now
        self._ensure_private_parent()

    def record(self, event: AuditEvent) -> None:
        if not isinstance(event, AuditEvent):
            raise TypeError("event must be an AuditEvent")
        payload = {
            "timestamp": self._timestamp().isoformat(),
            "platform_id": event.platform_id,
            "action": event.action.value if event.action else None,
            "decision": event.decision,
            "status": event.status.value,
            "result_code": event.result_code.value if event.result_code else None,
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.path, flags, 0o600)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("audit log must be a regular file")
            if metadata.st_uid != self.expected_owner:
                raise PermissionError("audit log has an unexpected owner")
            if stat.S_IMODE(metadata.st_mode) != 0o600:
                raise PermissionError(
                    "audit log must be owner-readable and owner-writable only"
                )
            with os.fdopen(descriptor, "a", encoding="utf-8", closefd=False) as output:
                json.dump(payload, output, sort_keys=True, separators=(",", ":"))
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)

    def _ensure_private_parent(self) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path.parent.chmod(0o700)
        metadata = self.path.parent.stat()
        if metadata.st_uid != self.expected_owner:
            raise PermissionError("audit directory has an unexpected owner")
        if stat.S_IMODE(metadata.st_mode) != 0o700:
            raise PermissionError("audit directory must be owner-accessible only")

    def _timestamp(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("clock must return an aware UTC datetime")
        return value


class _BackupRequestHandler:
    """Bind a system backup mutation adapter to the strict protocol."""

    def __init__(self, adapter: BackupMutationAdapter) -> None:
        self._adapter = adapter

    def __call__(self, request: object) -> Mapping[str, object]:
        from .protocol import RequestEnvelope

        if not isinstance(request, RequestEnvelope):
            raise TypeError("request must be a RequestEnvelope")
        receipt = self._adapter.request_backup(
            BackupActionRequest(target_id=request.parameters["target_id"]),
            request_id=request.request_id,
        )
        if not isinstance(receipt, ActionReceipt):
            raise TypeError("backup adapter returned an invalid receipt")
        if receipt.request_id != request.request_id:
            raise ValueError("backup adapter returned a mismatched request_id")
        return receipt.to_wire()


@dataclass(slots=True)
class LinuxBackendService:
    """Composed Linux backend ready for socket-activated serving."""

    policy: SystemPolicy
    store: AtomicRecordStore
    locks: RepositoryMutationLock
    dispatcher: LocalControlDispatcher
    transport: LinuxUnixSocketTransport
    status_event_transport: LinuxStatusEventTransport | None
    audit_sink: AuditSink
    stop_event: Event
    status_event_broker: BoundedStatusEventBroker
    status_change_coordinator: StatusChangeCoordinator
    membership_resolver: GroupMembershipResolver
    reconciled_run_ids: tuple[UUID, ...] = ()

    def serve_forever(self, *, install_signal_handlers: bool = True) -> None:
        if install_signal_handlers:
            self.install_signal_handlers()
        status_thread = None
        if self.status_event_transport is not None:
            status_thread = Thread(
                target=self._serve_status_events,
                name="timelocker-status-events",
                daemon=True,
            )
            status_thread.start()
        try:
            self.transport.serve(self.dispatcher)
        except OSError:
            if not self.stop_event.is_set():
                raise
        finally:
            self.stop()
            if status_thread is not None:
                status_thread.join(timeout=1.0)

    def _serve_status_events(self) -> None:
        assert self.status_event_transport is not None
        try:
            self.status_event_transport.serve(
                self.status_event_broker,
                self.transport.identity_provider,
                self.membership_resolver,
            )
        except OSError:
            return

    def install_signal_handlers(self) -> None:
        def _handle_signal(_signum: int, _frame: FrameType | None) -> None:
            self.stop()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

    def stop(self) -> None:
        self.stop_event.set()
        listener = getattr(self.transport, "listener", None)
        if isinstance(listener, socket.socket):
            try:
                listener.close()
            except OSError:
                pass
        status_listener = (
            getattr(self.status_event_transport, "listener", None)
            if self.status_event_transport is not None
            else None
        )
        if isinstance(status_listener, socket.socket):
            try:
                status_listener.close()
            except OSError:
                pass


def build_linux_backend(
    *,
    paths: LinuxBackendPaths,
    socket_mode: str = "systemd",
    listener: socket.socket | None = None,
    status_listener: socket.socket | None = None,
    systemd_descriptor: int = 3,
    status_systemd_descriptor: int | None = 4,
    status_socket_mode: str = "systemd",
    request_timeout_seconds: float = 5.0,
    membership_resolver: GroupMembershipResolver | None = None,
    backup_adapter: BackupMutationAdapter | None = None,
    retention_adapter: RetentionAdapter | None = None,
    retention_plan_provider: RetentionPlanProvider | None = None,
    production_target_path: Path | None = None,
    schedule_summary_provider: ScheduleSummaryProvider | None = None,
    max_diagnostics: int = 1_000,
    stop_event: Event | None = None,
    clock: Callable[[], datetime] | None = None,
) -> LinuxBackendService:
    """Compose the Linux backend from strict local components."""
    if type(max_diagnostics) is not int or not 1 <= max_diagnostics <= 100_000:
        raise ValueError("max_diagnostics must be between 1 and 100000")
    if socket_mode not in {"systemd", "listener"}:
        raise ValueError("socket_mode must be 'systemd' or 'listener'")
    if status_socket_mode not in {"systemd", "listener", "disabled"}:
        raise ValueError(
            "status_socket_mode must be 'systemd', 'listener', or 'disabled'"
        )
    if socket_mode == "listener":
        if listener is None:
            raise ValueError("listener socket is required for listener mode")
    elif listener is not None:
        raise ValueError("listener socket can only be provided in listener mode")
    if status_socket_mode == "listener":
        if status_listener is None:
            raise ValueError("status socket listener is required for listener mode")
    elif status_listener is not None:
        raise ValueError("status socket listener can only be provided in listener mode")
    if status_socket_mode == "systemd" and status_systemd_descriptor is None:
        raise ValueError("status systemd descriptor is required for systemd mode")

    now = clock or _utc_now
    stop_event = stop_event or Event()
    policy = load_system_policy(paths.policy_path, expected_owner=paths.expected_owner)
    status_event_broker = BoundedStatusEventBroker()
    status_change_coordinator = StatusChangeCoordinator(status_event_broker)
    store = AtomicRecordStore(
        paths.record_root,
        max_diagnostics=max_diagnostics,
        status_change_callback=status_change_coordinator.run_changed,
    )
    locks = RepositoryMutationLock(paths.lock_root)
    audit_sink = RootOnlyJsonlAuditSink(
        paths.audit_log_path,
        expected_owner=paths.expected_owner,
        clock=now,
    )
    schedule_summary_provider = (
        schedule_summary_provider or StaticScheduleSummaryProvider()
    )
    membership_resolver = membership_resolver or LinuxNssGroupMembershipResolver()
    if (
        retention_adapter is None
        and retention_plan_provider is None
        and production_target_path is not None
    ):
        retention_adapter, retention_plan_provider = (
            load_production_retention_components(
                target_path=production_target_path,
                expected_owner=paths.expected_owner,
            )
        )
    if backup_adapter is None and isinstance(
        retention_adapter,
        TimeLockerCliRetentionAdapter,
    ):
        backup_adapter = SystemdBackupMutationAdapter(
            store=store,
            target_id=retention_adapter.target.target_id,
            worker_root=paths.record_root.parent / "backup-worker",
        )
    backup_adapter = backup_adapter or FailClosedBackupMutationAdapter()
    retention_adapter = retention_adapter or FailClosedRetentionAdapter()
    retention_plan_provider = (
        retention_plan_provider or FailClosedRetentionPlanProvider()
    )

    reconciled = reconcile_abandoned_runs(store, locks, now=now())
    _emit_startup_diagnostics(store, reconciled, clock=now)
    transport = _build_transport(
        policy=policy,
        socket_mode=socket_mode,
        listener=listener,
        systemd_descriptor=systemd_descriptor,
        request_timeout_seconds=request_timeout_seconds,
        stop_event=stop_event,
    )
    status_event_transport = (
        None
        if status_socket_mode == "disabled"
        else _build_status_transport(
            policy=policy,
            socket_mode=status_socket_mode,
            listener=status_listener if status_socket_mode == "listener" else None,
            systemd_descriptor=status_systemd_descriptor,
            stop_event=stop_event,
        )
    )
    dispatcher = LocalControlDispatcher(
        policy=policy,
        membership_resolver=membership_resolver,
        handlers=_build_handlers(
            policy=policy,
            store=store,
            locks=locks,
            backup_adapter=backup_adapter,
            retention_adapter=retention_adapter,
            retention_plan_provider=retention_plan_provider,
            schedule_summary_provider=schedule_summary_provider,
            status_change_coordinator=status_change_coordinator,
            trigger_root=paths.trigger_root,
            clock=now,
        ),
        audit_sink=audit_sink,
    )
    return LinuxBackendService(
        policy=policy,
        store=store,
        locks=locks,
        dispatcher=dispatcher,
        transport=transport,
        status_event_transport=status_event_transport,
        audit_sink=audit_sink,
        stop_event=stop_event,
        status_event_broker=status_event_broker,
        status_change_coordinator=status_change_coordinator,
        membership_resolver=membership_resolver,
        reconciled_run_ids=tuple(record.run_id for record in reconciled),
    )


def run_linux_backend(**kwargs: object) -> None:
    """Build and serve the Linux backend until the process is stopped."""
    service = build_linux_backend(**kwargs)
    service.serve_forever()


def run_scheduled_retention(
    *,
    paths: LinuxBackendPaths,
    production_target_path: Path,
    trigger: OperationTrigger = OperationTrigger.SCHEDULED,
    enable_marker: Path = DEFAULT_RETENTION_ENABLE_MARKER,
) -> None:
    """Run one approved independent retention attempt using protected config."""
    if trigger not in {
        OperationTrigger.SCHEDULED,
        OperationTrigger.BACKUP_SUCCESS,
    }:
        raise ValueError("unsupported automatic retention trigger")
    require_retention_enable_marker(
        enable_marker,
        expected_owner=paths.expected_owner,
    )
    policy = load_system_policy(
        paths.policy_path,
        expected_owner=paths.expected_owner,
    )
    store = AtomicRecordStore(paths.record_root)
    locks = RepositoryMutationLock(paths.lock_root)
    adapter, provider = load_production_retention_components(
        target_path=production_target_path,
        expected_owner=paths.expected_owner,
    )
    plan = _apply_policy_defaults(
        provider.resolve_retention_plan(policy),
        policy.retention,
    )
    run = RetentionExecutor(
        store=store,
        locks=locks,
        adapter=adapter,
    ).execute(
        plan,
        trigger=trigger,
        dry_run=False,
    )
    if run.state is RunState.FAILED:
        raise RuntimeError("scheduled retention failed safely")


def run_backup_record_start(
    *,
    paths: LinuxBackendPaths,
    production_target_path: Path,
) -> None:
    """Create or claim the run record for one systemd backup invocation."""
    target = ProductionRetentionTarget.load(
        production_target_path,
        expected_owner=paths.expected_owner,
    )
    SystemBackupRunCoordinator(
        store=AtomicRecordStore(paths.record_root),
        target_id=target.target_id,
        worker_root=paths.record_root.parent / "backup-worker",
    ).start()


def run_backup_record_finish(
    *,
    paths: LinuxBackendPaths,
    production_target_path: Path,
    result: str,
    exit_status: int | None,
) -> None:
    """Finish the active systemd backup record exactly once."""
    target = ProductionRetentionTarget.load(
        production_target_path,
        expected_owner=paths.expected_owner,
    )
    SystemBackupRunCoordinator(
        store=AtomicRecordStore(paths.record_root),
        target_id=target.target_id,
        worker_root=paths.record_root.parent / "backup-worker",
    ).finish(result=result, exit_status=exit_status)


def _systemd_exit_status(value: str | None) -> int | None:
    """Return systemd's numeric process status without trusting free-form input."""
    if value is None or not value.isascii() or not value.isdecimal():
        return None
    parsed = int(value)
    return parsed if 0 <= parsed <= 255 else None


def _systemd_socket_descriptors(
    environment: Mapping[str, str] | None = None,
    *,
    process_id: int | None = None,
) -> tuple[int, int | None]:
    """Resolve required control and optional event systemd descriptors."""
    environment = os.environ if environment is None else environment
    process_id = os.getpid() if process_id is None else process_id
    if type(process_id) is not int or process_id <= 0:
        raise ValueError("process_id must be a positive integer")
    listen_pid = environment.get("LISTEN_PID", "")
    listen_fds = environment.get("LISTEN_FDS", "")
    if (
        not listen_pid.isascii()
        or not listen_pid.isdecimal()
        or int(listen_pid) != process_id
        or not listen_fds.isascii()
        or not listen_fds.isdecimal()
        or int(listen_fds) not in {1, 2}
    ):
        raise RuntimeError("required systemd socket for control is unavailable")
    names = environment.get("LISTEN_FDNAMES", "").split(":")
    expected_names = (
        {"control"}
        if int(listen_fds) == 1
        else {"control", "status-events"}
    )
    if len(names) != int(listen_fds) or set(names) != expected_names:
        raise RuntimeError("required systemd socket name for control is unavailable")
    descriptors = {name: 3 + index for index, name in enumerate(names)}
    return descriptors["control"], descriptors.get("status-events")


def main(argv: list[str] | None = None) -> None:
    """Run one allowlisted privileged system-control process mode."""
    parser = argparse.ArgumentParser(prog="timelocker-system-control")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--systemd-socket",
        action="store_true",
        help="Accept the listening socket from systemd descriptor 3.",
    )
    modes.add_argument(
        "--scheduled-retention",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    modes.add_argument(
        "--backup-run-start",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    modes.add_argument(
        "--backup-run-finish",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("/etc/timelocker/system-control-policy.json"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path("/var/lib/timelocker"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--production-target",
        type=Path,
        default=DEFAULT_PRODUCTION_TARGET_PATH,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--retention-trigger",
        choices=("scheduled", "backup-success"),
        default="scheduled",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--backup-result",
        choices=(
            "success",
            "protocol",
            "timeout",
            "exit-code",
            "signal",
            "core-dump",
            "watchdog",
            "start-limit-hit",
            "resources",
        ),
        default="failure",
        help=argparse.SUPPRESS,
    )
    arguments = parser.parse_args(argv)
    try:
        paths = LinuxBackendPaths.from_state_root(
            policy_path=arguments.policy,
            state_root=arguments.state_root,
        )
        if arguments.scheduled_retention:
            run_scheduled_retention(
                paths=paths,
                production_target_path=arguments.production_target,
                trigger=(
                    OperationTrigger.BACKUP_SUCCESS
                    if arguments.retention_trigger == "backup-success"
                    else OperationTrigger.SCHEDULED
                ),
            )
        elif arguments.backup_run_start:
            run_backup_record_start(
                paths=paths,
                production_target_path=arguments.production_target,
            )
        elif arguments.backup_run_finish:
            run_backup_record_finish(
                paths=paths,
                production_target_path=arguments.production_target,
                result=arguments.backup_result,
                exit_status=_systemd_exit_status(os.environ.get("EXIT_STATUS")),
            )
        else:
            control_descriptor, status_descriptor = _systemd_socket_descriptors()
            run_linux_backend(
                paths=paths,
                socket_mode="systemd",
                systemd_descriptor=control_descriptor,
                status_systemd_descriptor=status_descriptor,
                status_socket_mode=(
                    "systemd" if status_descriptor is not None else "disabled"
                ),
                production_target_path=arguments.production_target,
            )
    except (OSError, PermissionError, RuntimeError, TypeError, ValueError):
        parser.exit(78, "TimeLocker system backend failed to initialize safely.\n")


def _build_transport(
    *,
    policy: SystemPolicy,
    socket_mode: str,
    listener: socket.socket | None,
    systemd_descriptor: int,
    request_timeout_seconds: float,
    stop_event: Event,
) -> LinuxUnixSocketTransport:
    if socket_mode == "listener":
        assert listener is not None
        return LinuxUnixSocketTransport(
            listener,
            max_request_bytes=policy.max_request_bytes,
            request_timeout_seconds=request_timeout_seconds,
            stop_event=stop_event,
        )
    return LinuxUnixSocketTransport.from_systemd(
        descriptor=systemd_descriptor,
        max_request_bytes=policy.max_request_bytes,
        request_timeout_seconds=request_timeout_seconds,
        stop_event=stop_event,
    )


def _build_status_transport(
    *,
    policy: SystemPolicy,
    socket_mode: str,
    listener: socket.socket | None,
    systemd_descriptor: int | None,
    stop_event: Event,
) -> LinuxStatusEventTransport:
    if socket_mode == "listener":
        assert listener is not None
        return LinuxStatusEventTransport(
            listener,
            max_frame_bytes=policy.max_request_bytes,
            heartbeat_interval_seconds=5.0,
            operator_group=policy.operator_group,
            stop_event=stop_event,
        )
    assert systemd_descriptor is not None
    return LinuxStatusEventTransport.from_systemd(
        descriptor=systemd_descriptor,
        heartbeat_interval_seconds=5.0,
        max_frame_bytes=policy.max_request_bytes,
        operator_group=policy.operator_group,
        stop_event=stop_event,
    )


def _build_handlers(
    *,
    policy: SystemPolicy,
    store: AtomicRecordStore,
    locks: RepositoryMutationLock,
    backup_adapter: BackupMutationAdapter,
    retention_adapter: RetentionAdapter,
    retention_plan_provider: RetentionPlanProvider,
    schedule_summary_provider: ScheduleSummaryProvider,
    status_change_coordinator: StatusChangeCoordinator | None = None,
    trigger_root: Path,
    clock: Callable[[], datetime],
) -> Mapping[SystemAction, Callable[[object], object]]:
    from .protocol import RequestEnvelope

    status_change_coordinator = status_change_coordinator or StatusChangeCoordinator(
        BoundedStatusEventBroker()
    )

    def health(_request: object) -> Mapping[str, object]:
        return {
            "backend_available": True,
            "protocol_min": PROTOCOL_VERSION,
            "protocol_max": PROTOCOL_VERSION,
        }

    def run_list(request: object) -> Mapping[str, object]:
        if not isinstance(request, RequestEnvelope):
            raise TypeError("request must be a RequestEnvelope")
        operation = request.parameters.get("operation")
        state = request.parameters.get("state")
        query = RunQuery(
            limit=min(
                int(request.parameters.get("limit", policy.max_response_records)),
                policy.max_response_records,
            ),
            operation=OperationType(operation) if operation is not None else None,
            state=RunState(state) if state is not None else None,
        )
        return {
            "runs": [
                RunRecordView.from_record(record).to_wire()
                for record in store.list_runs(query)
            ]
        }

    def run_detail(request: object) -> Mapping[str, object]:
        if not isinstance(request, RequestEnvelope):
            raise TypeError("request must be a RequestEnvelope")
        return {
            "run": RunRecordView.from_record(
                store.read_run(request.parameters["run_id"])
            ).to_wire()
        }

    def diagnostic_list(request: object) -> Mapping[str, object]:
        if not isinstance(request, RequestEnvelope):
            raise TypeError("request must be a RequestEnvelope")
        level = request.parameters.get("level")
        query = DiagnosticQuery(
            limit=min(
                int(request.parameters.get("limit", policy.max_response_records)),
                policy.max_response_records,
            ),
            run_id=request.parameters.get("run_id"),
            level=DiagnosticLevel(level) if level is not None else None,
        )
        return {
            "diagnostics": [
                DiagnosticView.from_record(record).to_wire()
                for record in store.list_diagnostics(query)
            ]
        }

    def schedule_summary(_request: object) -> Mapping[str, object]:
        summary = schedule_summary_provider.get_schedule_summary()
        if not isinstance(summary, ScheduleSummary):
            raise TypeError("schedule_summary_provider returned an invalid summary")
        return _schedule_to_wire(summary)

    def status_snapshot(_request: object) -> Mapping[str, object]:
        def build_snapshot(revision: StatusRevision) -> StatusSnapshot:
            summary = schedule_summary_provider.get_schedule_summary()
            if not isinstance(summary, ScheduleSummary):
                raise TypeError(
                    "schedule_summary_provider returned an invalid summary"
                )
            runs = store.list_status_runs()
            return StatusSnapshot.from_run_history(
                revision=revision,
                backend_status=BackendStatus.AVAILABLE,
                active_operations=sum(
                    record.state in {RunState.QUEUED, RunState.RUNNING}
                    for record in runs
                ),
                runs=runs,
                next_backup_at=summary.next_backup_at,
                next_retention_at=summary.next_retention_at,
            )

        return status_change_coordinator.snapshot(build_snapshot).to_wire()

    def ui_availability(_request: object) -> Mapping[str, object]:
        return {"available": False}

    handlers: dict[SystemAction, Callable[[object], object]] = {
        SystemAction.HEALTH: health,
        SystemAction.RUN_LIST: run_list,
        SystemAction.RUN_DETAIL: run_detail,
        SystemAction.DIAGNOSTIC_LIST: diagnostic_list,
        SystemAction.SCHEDULE_SUMMARY: schedule_summary,
        SystemAction.STATUS_SNAPSHOT: status_snapshot,
        SystemAction.UI_AVAILABILITY: ui_availability,
    }
    if not isinstance(backup_adapter, FailClosedBackupMutationAdapter):
        handlers[SystemAction.BACKUP_REQUEST] = _BackupRequestHandler(backup_adapter)
    if not isinstance(retention_adapter, FailClosedRetentionAdapter) and not isinstance(
        retention_plan_provider, FailClosedRetentionPlanProvider
    ):
        plan = retention_plan_provider.resolve_retention_plan(policy)
        if not isinstance(plan, RetentionPlan):
            raise TypeError("retention_plan_provider returned an invalid plan")
        plan = _apply_policy_defaults(plan, policy.retention)
        coordinator = RetentionTriggerCoordinator(
            executor=RetentionExecutor(
                store=store,
                locks=locks,
                adapter=retention_adapter,
                clock=clock,
            ),
            trigger_store=RetentionTriggerStore(trigger_root),
        )
        handlers[SystemAction.RETENTION_REQUEST] = RetentionRequestHandler(
            coordinator=coordinator,
            plan=plan,
        )
    return handlers


def _apply_policy_defaults(
    plan: RetentionPlan,
    policy: RetentionPolicy,
) -> RetentionPlan:
    approved_fingerprint = (
        policy.approved_fingerprint or plan.policy.approved_fingerprint
    )
    return RetentionPlan(
        target_id=plan.target_id,
        repository_identity=plan.repository_identity,
        credential_source=plan.credential_source,
        snapshot_filters=plan.snapshot_filters,
        policy=RetentionPolicy(
            keep_daily=policy.keep_daily,
            keep_weekly=policy.keep_weekly,
            keep_monthly=policy.keep_monthly,
            keep_yearly=policy.keep_yearly,
            group_by=policy.group_by,
            prune=policy.prune,
            approved_fingerprint=approved_fingerprint,
        ),
    )


def _schedule_to_wire(summary: ScheduleSummary) -> dict[str, object]:
    return {
        "next_backup_at": (
            summary.next_backup_at.isoformat() if summary.next_backup_at else None
        ),
        "next_retention_at": (
            summary.next_retention_at.isoformat() if summary.next_retention_at else None
        ),
    }


def _emit_startup_diagnostics(
    store: AtomicRecordStore,
    reconciled: list[object],
    *,
    clock: Callable[[], datetime],
) -> None:
    timestamp = clock()
    for record in reconciled:
        run_id = getattr(record, "run_id", None)
        if not isinstance(run_id, UUID):
            continue
        store.append_diagnostic(
            DiagnosticRecord(
                record_id=uuid4(),
                run_id=run_id,
                timestamp=timestamp,
                level=DiagnosticLevel.WARNING,
                component=DiagnosticComponent.RUN_STORE,
                message_code=DiagnosticCode.OPERATION_INTERRUPTED,
            )
        )
    store.append_diagnostic(
        DiagnosticRecord(
            record_id=uuid4(),
            run_id=None,
            timestamp=timestamp,
            level=DiagnosticLevel.INFO,
            component=DiagnosticComponent.BACKEND,
            message_code=DiagnosticCode.BACKEND_STARTED,
        )
    )


__all__ = [
    "BackupMutationAdapter",
    "FailClosedBackupMutationAdapter",
    "FailClosedRetentionAdapter",
    "FailClosedRetentionPlanProvider",
    "LinuxBackendPaths",
    "LinuxBackendService",
    "RetentionPlanProvider",
    "RootOnlyJsonlAuditSink",
    "ScheduleSummaryProvider",
    "StaticScheduleSummaryProvider",
    "build_linux_backend",
    "main",
    "run_linux_backend",
    "run_scheduled_retention",
    "run_backup_record_finish",
    "run_backup_record_start",
]


if __name__ == "__main__":
    main()
