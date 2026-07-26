"""Strict platform-neutral models for TimeLocker system operations."""

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, ClassVar, Mapping
from uuid import UUID

from .types import (
    DiagnosticCode,
    DiagnosticComponent,
    DiagnosticLevel,
    OperationTrigger,
    OperationType,
    ResultCode,
    RunState,
)
from .validation import (
    MAX_COUNTER_VALUE,
    freeze_counters,
    require_bool,
    require_enum,
    require_exact_mapping,
    require_fingerprint,
    require_group_name,
    require_int,
    require_optional_utc_datetime,
    require_optional_wire_utc_datetime,
    require_optional_uuid,
    require_safe_identifier,
    require_utc_datetime,
    require_uuid,
    require_wire_utc_datetime,
)


PROTOCOL_VERSION = 1
DEFAULT_MAX_REQUEST_BYTES = 65_536
DEFAULT_MAX_RESPONSE_RECORDS = 100

RESULT_SUMMARIES: Mapping[ResultCode, str] = MappingProxyType(
    {
        ResultCode.OPERATION_QUEUED: "Operation queued.",
        ResultCode.OPERATION_RUNNING: "Operation is running.",
        ResultCode.BACKUP_SUCCEEDED: "Backup completed successfully.",
        ResultCode.RETENTION_SUCCEEDED: "Retention completed successfully.",
        ResultCode.OPERATION_FAILED: "Operation failed.",
        ResultCode.OPERATION_CONFLICT: "Operation skipped because another repository operation is active.",
        ResultCode.OPERATION_SKIPPED: "Operation was skipped.",
        ResultCode.OPERATION_INTERRUPTED: "Operation was interrupted.",
    }
)

DIAGNOSTIC_SUMMARIES: Mapping[DiagnosticCode, str] = MappingProxyType(
    {
        DiagnosticCode.BACKEND_STARTED: "System backend started.",
        DiagnosticCode.BACKEND_UNAVAILABLE: "System backend is unavailable.",
        DiagnosticCode.ACCESS_DENIED: "System access denied.",
        DiagnosticCode.INVALID_REQUEST: "System request is invalid.",
        DiagnosticCode.BACKUP_STARTED: "Backup started.",
        DiagnosticCode.BACKUP_SUCCEEDED: "Backup completed successfully.",
        DiagnosticCode.RETENTION_STARTED: "Retention started.",
        DiagnosticCode.RETENTION_SUCCEEDED: "Retention completed successfully.",
        DiagnosticCode.OPERATION_FAILED: "Operation failed.",
        DiagnosticCode.OPERATION_CONFLICT: "Another repository operation is active.",
        DiagnosticCode.OPERATION_INTERRUPTED: "Operation was interrupted.",
        DiagnosticCode.RECORD_CORRUPT: "A system record could not be read safely.",
    }
)

_STATE_RESULT_CODES: Mapping[RunState, frozenset[ResultCode]] = MappingProxyType(
    {
        RunState.QUEUED: frozenset({ResultCode.OPERATION_QUEUED}),
        RunState.RUNNING: frozenset({ResultCode.OPERATION_RUNNING}),
        RunState.SUCCEEDED: frozenset(
            {ResultCode.BACKUP_SUCCEEDED, ResultCode.RETENTION_SUCCEEDED}
        ),
        RunState.FAILED: frozenset({ResultCode.OPERATION_FAILED}),
        RunState.SKIPPED: frozenset(
            {ResultCode.OPERATION_CONFLICT, ResultCode.OPERATION_SKIPPED}
        ),
        RunState.INTERRUPTED: frozenset({ResultCode.OPERATION_INTERRUPTED}),
    }
)


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Approved retention values shared by all platform adapters."""

    keep_daily: int = 5
    keep_weekly: int = 4
    keep_monthly: int = 12
    keep_yearly: int = 3
    group_by: tuple[str, ...] = ("host", "paths")
    prune: bool = False
    approved_fingerprint: str | None = None

    _ALLOWED_GROUP_FIELDS: ClassVar[frozenset[str]] = frozenset({"host", "paths"})

    def __post_init__(self) -> None:
        """Reject unsafe or incomplete retention policies."""
        for name in ("keep_daily", "keep_weekly", "keep_monthly", "keep_yearly"):
            object.__setattr__(
                self,
                name,
                require_int(getattr(self, name), field=name, minimum=0, maximum=10_000),
            )
        if type(self.group_by) is not tuple:
            raise TypeError("group_by must be a tuple")
        if not self.group_by or len(set(self.group_by)) != len(self.group_by):
            raise ValueError("group_by must contain unique fields")
        if not set(self.group_by) <= self._ALLOWED_GROUP_FIELDS:
            raise ValueError("group_by contains an unsupported field")
        object.__setattr__(self, "prune", require_bool(self.prune, field="prune"))
        if self.approved_fingerprint is not None:
            object.__setattr__(
                self,
                "approved_fingerprint",
                require_fingerprint(
                    self.approved_fingerprint,
                    field="approved_fingerprint",
                ),
            )

    @property
    def mutation_approved(self) -> bool:
        """Return whether an operator approved a matching dry-run fingerprint."""
        return self.approved_fingerprint is not None


@dataclass(frozen=True, slots=True)
class SystemPolicy:
    """Root-owned policy values consumed by the system-control backend."""

    operator_group: str = "timelocker-operators"
    transport_identifier: str = "/run/timelocker/control.sock"
    protocol_version: int = PROTOCOL_VERSION
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES
    max_response_records: int = DEFAULT_MAX_RESPONSE_RECORDS
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)

    def __post_init__(self) -> None:
        """Validate bounded platform policy without interpreting its transport."""
        object.__setattr__(
            self,
            "operator_group",
            require_group_name(self.operator_group),
        )
        if not isinstance(self.transport_identifier, str):
            raise TypeError("transport_identifier must be a string")
        if (
            not 1 <= len(self.transport_identifier) <= 260
            or "\x00" in self.transport_identifier
        ):
            raise ValueError("transport_identifier must be bounded and contain no NUL")
        object.__setattr__(
            self,
            "protocol_version",
            require_int(
                self.protocol_version,
                field="protocol_version",
                minimum=1,
                maximum=255,
            ),
        )
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError("protocol_version is unsupported")
        object.__setattr__(
            self,
            "max_request_bytes",
            require_int(
                self.max_request_bytes,
                field="max_request_bytes",
                minimum=1_024,
                maximum=1_048_576,
            ),
        )
        object.__setattr__(
            self,
            "max_response_records",
            require_int(
                self.max_response_records,
                field="max_response_records",
                minimum=1,
                maximum=1_000,
            ),
        )
        if not isinstance(self.retention, RetentionPolicy):
            raise TypeError("retention must be a RetentionPolicy")


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Durable, secret-free state for one backup or retention attempt."""

    run_id: UUID
    operation: OperationType
    trigger: OperationTrigger
    target_id: str
    started_at: datetime
    state: RunState
    result_code: ResultCode
    completed_at: datetime | None = None
    policy_fingerprint: str | None = None
    counters: Mapping[str, int] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self) -> None:
        """Validate state consistency and freeze caller-owned mappings."""
        object.__setattr__(self, "run_id", require_uuid(self.run_id, field="run_id"))
        object.__setattr__(
            self,
            "operation",
            require_enum(self.operation, OperationType, field="operation"),
        )
        object.__setattr__(
            self,
            "trigger",
            require_enum(self.trigger, OperationTrigger, field="trigger"),
        )
        object.__setattr__(
            self,
            "target_id",
            require_safe_identifier(self.target_id, field="target_id"),
        )
        object.__setattr__(
            self,
            "started_at",
            require_utc_datetime(self.started_at, field="started_at"),
        )
        object.__setattr__(
            self,
            "completed_at",
            require_optional_utc_datetime(self.completed_at, field="completed_at"),
        )
        object.__setattr__(
            self,
            "state",
            require_enum(self.state, RunState, field="state"),
        )
        object.__setattr__(
            self,
            "result_code",
            require_enum(self.result_code, ResultCode, field="result_code"),
        )
        object.__setattr__(
            self,
            "schema_version",
            require_int(
                self.schema_version,
                field="schema_version",
                minimum=1,
                maximum=255,
            ),
        )
        if self.policy_fingerprint is not None:
            object.__setattr__(
                self,
                "policy_fingerprint",
                require_fingerprint(
                    self.policy_fingerprint, field="policy_fingerprint"
                ),
            )
        object.__setattr__(self, "counters", freeze_counters(self.counters))
        self._validate_state()

    def _validate_state(self) -> None:
        if self.result_code not in _STATE_RESULT_CODES[self.state]:
            raise ValueError("result_code is inconsistent with state")
        terminal = self.state not in {RunState.QUEUED, RunState.RUNNING}
        if terminal != (self.completed_at is not None):
            raise ValueError("completed_at must be present exactly for terminal states")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")
        if self.state is RunState.SUCCEEDED:
            expected = (
                ResultCode.BACKUP_SUCCEEDED
                if self.operation is OperationType.BACKUP
                else ResultCode.RETENTION_SUCCEEDED
            )
            if self.result_code is not expected:
                raise ValueError("success result_code does not match operation")
        if (
            self.operation is OperationType.BACKUP
            and self.trigger is OperationTrigger.BACKUP_SUCCESS
        ):
            raise ValueError("a backup cannot be triggered by backup success")
        if (
            self.operation is OperationType.BACKUP
            and self.policy_fingerprint is not None
        ):
            raise ValueError(
                "backup records cannot carry retention policy fingerprints"
            )

    @property
    def safe_summary(self) -> str:
        """Return the fixed summary owned by the stable result code."""
        return RESULT_SUMMARIES[self.result_code]


@dataclass(frozen=True, slots=True)
class RunTransition:
    """Validated request to move a queued or running record to a new state."""

    expected_states: frozenset[RunState]
    new_state: RunState
    result_code: ResultCode
    completed_at: datetime | None = None
    counters: Mapping[str, int] = field(default_factory=dict)

    _NON_TERMINAL: ClassVar[frozenset[RunState]] = frozenset(
        {RunState.QUEUED, RunState.RUNNING}
    )

    def __post_init__(self) -> None:
        """Reject terminal sources, no-op changes, and inconsistent results."""
        if type(self.expected_states) is not frozenset or not self.expected_states:
            raise ValueError("expected_states must be a non-empty frozenset")
        expected_states = frozenset(
            require_enum(state, RunState, field="expected_states")
            for state in self.expected_states
        )
        if not expected_states <= self._NON_TERMINAL:
            raise ValueError("transitions cannot start from a terminal state")
        new_state = require_enum(self.new_state, RunState, field="new_state")
        if new_state is RunState.QUEUED or new_state in expected_states:
            raise ValueError("transition must advance to a different state")
        result_code = require_enum(
            self.result_code,
            ResultCode,
            field="result_code",
        )
        if result_code not in _STATE_RESULT_CODES[new_state]:
            raise ValueError("result_code is inconsistent with new_state")
        completed_at = require_optional_utc_datetime(
            self.completed_at,
            field="completed_at",
        )
        terminal = new_state not in self._NON_TERMINAL
        if terminal != (completed_at is not None):
            raise ValueError("completed_at must be present exactly for terminal states")
        object.__setattr__(self, "expected_states", expected_states)
        object.__setattr__(self, "new_state", new_state)
        object.__setattr__(self, "result_code", result_code)
        object.__setattr__(self, "completed_at", completed_at)
        object.__setattr__(self, "counters", freeze_counters(self.counters))


@dataclass(frozen=True, slots=True)
class DiagnosticRecord:
    """One bounded, operator-visible diagnostic event."""

    record_id: UUID
    timestamp: datetime
    level: DiagnosticLevel
    component: DiagnosticComponent
    message_code: DiagnosticCode
    run_id: UUID | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        """Validate diagnostic identity and enum values."""
        object.__setattr__(
            self,
            "record_id",
            require_uuid(self.record_id, field="record_id"),
        )
        object.__setattr__(
            self,
            "run_id",
            require_optional_uuid(self.run_id, field="run_id"),
        )
        object.__setattr__(
            self,
            "timestamp",
            require_utc_datetime(self.timestamp, field="timestamp"),
        )
        object.__setattr__(
            self,
            "level",
            require_enum(self.level, DiagnosticLevel, field="level"),
        )
        object.__setattr__(
            self,
            "component",
            require_enum(self.component, DiagnosticComponent, field="component"),
        )
        object.__setattr__(
            self,
            "message_code",
            require_enum(self.message_code, DiagnosticCode, field="message_code"),
        )
        object.__setattr__(
            self,
            "schema_version",
            require_int(
                self.schema_version,
                field="schema_version",
                minimum=1,
                maximum=255,
            ),
        )

    @property
    def safe_summary(self) -> str:
        """Return the fixed summary owned by the stable diagnostic code."""
        return DIAGNOSTIC_SUMMARIES[self.message_code]


@dataclass(frozen=True, slots=True)
class ScheduleSummary:
    """Projected schedule timing used by user-facing status views."""

    next_backup_at: datetime | None
    next_retention_at: datetime | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "next_backup_at",
            require_optional_utc_datetime(
                self.next_backup_at,
                field="next_backup_at",
            ),
        )
        object.__setattr__(
            self,
            "next_retention_at",
            require_optional_utc_datetime(
                self.next_retention_at,
                field="next_retention_at",
            ),
        )

    @classmethod
    def from_mapping(cls, value: object) -> "ScheduleSummary":
        """Parse the strict wire projection returned by the protected backend."""
        mapping = require_exact_mapping(
            value,
            field="schedule_summary",
            required=frozenset({"next_backup_at", "next_retention_at"}),
        )
        return cls(
            next_backup_at=require_optional_wire_utc_datetime(
                mapping["next_backup_at"],
                field="next_backup_at",
            ),
            next_retention_at=require_optional_wire_utc_datetime(
                mapping["next_retention_at"],
                field="next_retention_at",
            ),
        )


@dataclass(frozen=True, slots=True)
class RunQuery:
    """Bounded filters for listing system runs."""

    limit: int = DEFAULT_MAX_RESPONSE_RECORDS
    operation: OperationType | None = None
    state: RunState | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "limit",
            require_int(self.limit, field="limit", minimum=1, maximum=1_000),
        )
        if self.operation is not None:
            object.__setattr__(
                self,
                "operation",
                require_enum(self.operation, OperationType, field="operation"),
            )
        if self.state is not None:
            object.__setattr__(
                self,
                "state",
                require_enum(self.state, RunState, field="state"),
            )


@dataclass(frozen=True, slots=True)
class DiagnosticQuery:
    """Bounded filters for listing system diagnostics."""

    limit: int = DEFAULT_MAX_RESPONSE_RECORDS
    run_id: UUID | None = None
    level: DiagnosticLevel | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "limit",
            require_int(self.limit, field="limit", minimum=1, maximum=1_000),
        )
        object.__setattr__(
            self,
            "run_id",
            require_optional_uuid(self.run_id, field="run_id"),
        )
        if self.level is not None:
            object.__setattr__(
                self,
                "level",
                require_enum(self.level, DiagnosticLevel, field="level"),
            )


@dataclass(frozen=True, slots=True)
class BackupActionRequest:
    """Allowlisted request for the configured system backup target."""

    target_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_id",
            require_safe_identifier(self.target_id, field="target_id"),
        )


@dataclass(frozen=True, slots=True)
class RetentionActionRequest:
    """Allowlisted request for an approved retention policy."""

    policy_fingerprint: str
    dry_run: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_fingerprint",
            require_fingerprint(self.policy_fingerprint, field="policy_fingerprint"),
        )
        object.__setattr__(self, "dry_run", require_bool(self.dry_run, field="dry_run"))


@dataclass(frozen=True, slots=True)
class ActionReceipt:
    """Secret-free acknowledgement for an accepted or rejected action."""

    request_id: UUID
    accepted: bool
    status: str
    run_id: UUID | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            require_uuid(self.request_id, field="request_id"),
        )
        object.__setattr__(
            self,
            "run_id",
            require_optional_uuid(self.run_id, field="run_id"),
        )
        object.__setattr__(
            self, "accepted", require_bool(self.accepted, field="accepted")
        )
        object.__setattr__(
            self,
            "status",
            require_safe_identifier(self.status, field="status", maximum=64),
        )
        if self.accepted != (self.run_id is not None):
            raise ValueError(
                "accepted receipts must contain a run_id and denied receipts must not"
            )

    def to_wire(self) -> dict[str, Any]:
        """Return JSON-compatible allowlisted receipt fields."""
        return {
            "request_id": str(self.request_id),
            "accepted": self.accepted,
            "status": self.status,
            "run_id": str(self.run_id) if self.run_id else None,
        }


@dataclass(frozen=True, slots=True)
class RunRecordView:
    """Allowlisted external projection of a run record."""

    run_id: UUID
    operation: OperationType
    trigger: OperationTrigger
    target_id: str
    started_at: datetime
    completed_at: datetime | None
    state: RunState
    result_code: ResultCode
    safe_summary: str
    policy_fingerprint: str | None
    counters: Mapping[str, int]

    def __post_init__(self) -> None:
        """Prevent direct construction from bypassing run-record invariants."""
        canonical = RunRecord(
            run_id=self.run_id,
            operation=self.operation,
            trigger=self.trigger,
            target_id=self.target_id,
            started_at=self.started_at,
            completed_at=self.completed_at,
            state=self.state,
            result_code=self.result_code,
            policy_fingerprint=self.policy_fingerprint,
            counters=self.counters,
        )
        if self.safe_summary != canonical.safe_summary:
            raise ValueError("safe_summary must match the stable result code")
        object.__setattr__(self, "run_id", canonical.run_id)
        object.__setattr__(self, "operation", canonical.operation)
        object.__setattr__(self, "trigger", canonical.trigger)
        object.__setattr__(self, "target_id", canonical.target_id)
        object.__setattr__(self, "started_at", canonical.started_at)
        object.__setattr__(self, "completed_at", canonical.completed_at)
        object.__setattr__(self, "state", canonical.state)
        object.__setattr__(self, "result_code", canonical.result_code)
        object.__setattr__(self, "policy_fingerprint", canonical.policy_fingerprint)
        object.__setattr__(self, "counters", canonical.counters)

    @classmethod
    def from_record(cls, record: RunRecord) -> "RunRecordView":
        """Create a response view without accepting caller-supplied fields."""
        return cls(
            run_id=record.run_id,
            operation=record.operation,
            trigger=record.trigger,
            target_id=record.target_id,
            started_at=record.started_at,
            completed_at=record.completed_at,
            state=record.state,
            result_code=record.result_code,
            safe_summary=record.safe_summary,
            policy_fingerprint=record.policy_fingerprint,
            counters=record.counters,
        )

    @classmethod
    def from_mapping(cls, value: object) -> "RunRecordView":
        """Parse all required fields from an untrusted projected mapping."""
        record = require_exact_mapping(
            value,
            field="run",
            required=frozenset(
                {
                    "run_id",
                    "operation",
                    "trigger",
                    "target_id",
                    "started_at",
                    "completed_at",
                    "state",
                    "result_code",
                    "safe_summary",
                    "policy_fingerprint",
                    "counters",
                }
            ),
        )
        if not isinstance(record["safe_summary"], str):
            raise TypeError("run.safe_summary must be a string")
        result_code = require_enum(
            record["result_code"],
            ResultCode,
            field="run.result_code",
        )
        return cls(
            run_id=require_uuid(record["run_id"], field="run.run_id"),
            operation=require_enum(
                record["operation"],
                OperationType,
                field="run.operation",
            ),
            trigger=require_enum(
                record["trigger"],
                OperationTrigger,
                field="run.trigger",
            ),
            target_id=require_safe_identifier(
                record["target_id"], field="run.target_id"
            ),
            started_at=require_wire_utc_datetime(
                record["started_at"],
                field="run.started_at",
            ),
            completed_at=require_optional_wire_utc_datetime(
                record["completed_at"],
                field="run.completed_at",
            ),
            state=require_enum(record["state"], RunState, field="run.state"),
            result_code=result_code,
            safe_summary=RESULT_SUMMARIES[result_code],
            policy_fingerprint=(
                None
                if record["policy_fingerprint"] is None
                else require_fingerprint(
                    record["policy_fingerprint"],
                    field="run.policy_fingerprint",
                )
            ),
            counters=record["counters"],
        )

    def to_wire(self) -> dict[str, Any]:
        """Return JSON-compatible allowlisted fields."""
        return {
            "run_id": str(self.run_id),
            "operation": self.operation.value,
            "trigger": self.trigger.value,
            "target_id": self.target_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "state": self.state.value,
            "result_code": self.result_code.value,
            "safe_summary": self.safe_summary,
            "policy_fingerprint": self.policy_fingerprint,
            "counters": dict(self.counters),
        }


@dataclass(frozen=True, slots=True)
class DiagnosticView:
    """Allowlisted external projection of a diagnostic record."""

    record_id: UUID
    run_id: UUID | None
    timestamp: datetime
    level: DiagnosticLevel
    component: DiagnosticComponent
    message_code: DiagnosticCode
    safe_summary: str

    def __post_init__(self) -> None:
        """Prevent direct construction from injecting operator-visible text."""
        canonical = DiagnosticRecord(
            record_id=self.record_id,
            run_id=self.run_id,
            timestamp=self.timestamp,
            level=self.level,
            component=self.component,
            message_code=self.message_code,
        )
        if self.safe_summary != canonical.safe_summary:
            raise ValueError("safe_summary must match the stable diagnostic code")
        object.__setattr__(self, "record_id", canonical.record_id)
        object.__setattr__(self, "run_id", canonical.run_id)
        object.__setattr__(self, "timestamp", canonical.timestamp)
        object.__setattr__(self, "level", canonical.level)
        object.__setattr__(self, "component", canonical.component)
        object.__setattr__(self, "message_code", canonical.message_code)

    @classmethod
    def from_record(cls, record: DiagnosticRecord) -> "DiagnosticView":
        """Create a response view without caller-controlled summary text."""
        return cls(
            record_id=record.record_id,
            run_id=record.run_id,
            timestamp=record.timestamp,
            level=record.level,
            component=record.component,
            message_code=record.message_code,
            safe_summary=record.safe_summary,
        )

    @classmethod
    def from_mapping(cls, value: object) -> "DiagnosticView":
        """Parse all required fields from an untrusted projected mapping."""
        diagnostic = require_exact_mapping(
            value,
            field="diagnostic",
            required=frozenset(
                {
                    "record_id",
                    "run_id",
                    "timestamp",
                    "level",
                    "component",
                    "message_code",
                    "safe_summary",
                }
            ),
        )
        if not isinstance(diagnostic["safe_summary"], str):
            raise TypeError("diagnostic.safe_summary must be a string")
        message_code = require_enum(
            diagnostic["message_code"],
            DiagnosticCode,
            field="diagnostic.message_code",
        )
        return cls(
            record_id=require_uuid(
                diagnostic["record_id"],
                field="diagnostic.record_id",
            ),
            run_id=require_optional_uuid(
                diagnostic["run_id"],
                field="diagnostic.run_id",
            ),
            timestamp=require_wire_utc_datetime(
                diagnostic["timestamp"],
                field="diagnostic.timestamp",
            ),
            level=require_enum(
                diagnostic["level"],
                DiagnosticLevel,
                field="diagnostic.level",
            ),
            component=require_enum(
                diagnostic["component"],
                DiagnosticComponent,
                field="diagnostic.component",
            ),
            message_code=message_code,
            safe_summary=DIAGNOSTIC_SUMMARIES[message_code],
        )

    def to_wire(self) -> dict[str, Any]:
        """Return JSON-compatible allowlisted fields."""
        return {
            "record_id": str(self.record_id),
            "run_id": str(self.run_id) if self.run_id else None,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "component": self.component.value,
            "message_code": self.message_code.value,
            "safe_summary": self.safe_summary,
        }


def validate_counter_value(value: object) -> int:
    """Public helper for adapters that build counter maps incrementally."""
    return require_int(
        value,
        field="counter",
        minimum=0,
        maximum=MAX_COUNTER_VALUE,
    )
