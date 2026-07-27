"""Shared, platform-neutral system-control enumerations."""

from enum import StrEnum


class SystemAction(StrEnum):
    """Actions exposed by the bounded local system-control contract."""

    HEALTH = "health"
    RUN_LIST = "run.list"
    RUN_DETAIL = "run.detail"
    DIAGNOSTIC_LIST = "diagnostic.list"
    SCHEDULE_SUMMARY = "schedule.summary"
    STATUS_SNAPSHOT = "status.snapshot"
    BACKUP_REQUEST = "backup.request"
    RETENTION_REQUEST = "retention.request"
    UI_AVAILABILITY = "ui.availability"


class ResponseStatus(StrEnum):
    """Protocol-level outcomes that do not expose backend internals."""

    OK = "ok"
    DENIED = "denied"
    CONFLICT = "conflict"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"
    FAILED = "failed"


class BackendStatus(StrEnum):
    """Bounded backend availability states for status snapshots."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class StatusEventKind(StrEnum):
    """Allowlisted status event kinds for the event-driven tray contract."""

    SNAPSHOT_REQUIRED = "snapshot_required"
    CHANGED = "changed"
    HEARTBEAT = "heartbeat"
    RESYNC_REQUIRED = "resync_required"


class ProtocolErrorCode(StrEnum):
    """Stable response errors with metadata-free, code-owned summaries."""

    SYSTEM_ACCESS_DENIED = "system_access_denied"
    SYSTEM_BACKEND_UNAVAILABLE = "system_backend_unavailable"
    CONTRACT_VERSION_UNSUPPORTED = "contract_version_unsupported"
    INVALID_REQUEST = "invalid_request"
    OPERATION_CONFLICT = "operation_conflict"
    OPERATION_FAILED = "operation_failed"


class OperationType(StrEnum):
    """Machine operations recorded by the system backend."""

    BACKUP = "backup"
    RETENTION = "retention"


class OperationTrigger(StrEnum):
    """Origin of a system operation."""

    SCHEDULED = "scheduled"
    BACKUP_SUCCESS = "backup_success"
    EXPLICIT = "explicit"
    RETRY = "retry"
    RECOVERY = "recovery"


class RunState(StrEnum):
    """Allowed run-record states."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    INTERRUPTED = "interrupted"


class ResultCode(StrEnum):
    """Stable run result codes with safe, code-owned summaries."""

    OPERATION_QUEUED = "operation_queued"
    OPERATION_RUNNING = "operation_running"
    BACKUP_SUCCEEDED = "backup_succeeded"
    RETENTION_SUCCEEDED = "retention_succeeded"
    OPERATION_FAILED = "operation_failed"
    OPERATION_CONFLICT = "operation_conflict"
    OPERATION_SKIPPED = "operation_skipped"
    OPERATION_INTERRUPTED = "operation_interrupted"


class DiagnosticLevel(StrEnum):
    """Severity of an operator-visible structured diagnostic."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DiagnosticComponent(StrEnum):
    """Components allowed to emit operator-visible diagnostics."""

    BACKEND = "backend"
    AUTHORIZATION = "authorization"
    BACKUP = "backup"
    RETENTION = "retention"
    SCHEDULER = "scheduler"
    RUN_STORE = "run_store"


class DiagnosticCode(StrEnum):
    """Stable diagnostic codes whose summaries are owned by TimeLocker."""

    BACKEND_STARTED = "backend_started"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    ACCESS_DENIED = "access_denied"
    INVALID_REQUEST = "invalid_request"
    BACKUP_STARTED = "backup_started"
    BACKUP_SUCCEEDED = "backup_succeeded"
    RETENTION_STARTED = "retention_started"
    RETENTION_SUCCEEDED = "retention_succeeded"
    OPERATION_FAILED = "operation_failed"
    OPERATION_CONFLICT = "operation_conflict"
    OPERATION_INTERRUPTED = "operation_interrupted"
    RECORD_CORRUPT = "record_corrupt"
