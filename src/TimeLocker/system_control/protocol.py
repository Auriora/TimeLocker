"""Strict request envelopes and response projection for local system control."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from uuid import UUID

from .models import (
    ActionReceipt,
    DiagnosticView,
    PROTOCOL_VERSION,
    RunRecordView,
    StatusSnapshot,
)
from .types import (
    DiagnosticLevel,
    OperationType,
    ProtocolErrorCode,
    ResponseStatus,
    RunState,
    SystemAction,
)
from .validation import (
    deep_freeze,
    deep_thaw,
    freeze_mapping,
    require_bool,
    require_enum,
    require_exact_mapping,
    require_fingerprint,
    require_int,
    require_safe_identifier,
    require_uuid,
    require_wire_utc_datetime,
)


_PARAMETER_FIELDS: Mapping[SystemAction, tuple[frozenset[str], frozenset[str]]] = {
    SystemAction.HEALTH: (frozenset(), frozenset()),
    SystemAction.RUN_LIST: (
        frozenset(),
        frozenset({"limit", "operation", "state"}),
    ),
    SystemAction.RUN_DETAIL: (frozenset({"run_id"}), frozenset()),
    SystemAction.DIAGNOSTIC_LIST: (
        frozenset(),
        frozenset({"limit", "run_id", "level"}),
    ),
    SystemAction.SCHEDULE_SUMMARY: (frozenset(), frozenset()),
    SystemAction.STATUS_SNAPSHOT: (frozenset(), frozenset()),
    SystemAction.BACKUP_REQUEST: (frozenset({"target_id"}), frozenset()),
    SystemAction.RETENTION_REQUEST: (
        frozenset({"policy_fingerprint"}),
        frozenset({"dry_run"}),
    ),
    SystemAction.UI_AVAILABILITY: (frozenset(), frozenset()),
}

_RUN_VIEW_FIELDS = frozenset(
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
)
_DIAGNOSTIC_VIEW_FIELDS = frozenset(
    {
        "record_id",
        "run_id",
        "timestamp",
        "level",
        "component",
        "message_code",
        "safe_summary",
    }
)
_ACTION_RECEIPT_FIELDS = frozenset({"request_id", "accepted", "status", "run_id"})
_STATUS_SNAPSHOT_FIELDS = frozenset(
    {
        "revision",
        "backend_status",
        "active_operations",
        "latest_backup",
        "last_successful_backup_completed_at",
        "latest_retention",
        "next_backup_at",
        "next_retention_at",
    }
)

PROTOCOL_ERROR_SUMMARIES: Mapping[ProtocolErrorCode, str] = MappingProxyType(
    {
        ProtocolErrorCode.SYSTEM_ACCESS_DENIED: "System access denied.",
        ProtocolErrorCode.SYSTEM_BACKEND_UNAVAILABLE: "System backend is unavailable.",
        ProtocolErrorCode.CONTRACT_VERSION_UNSUPPORTED: (
            "System contract version is unsupported."
        ),
        ProtocolErrorCode.INVALID_REQUEST: "System request is invalid.",
        ProtocolErrorCode.OPERATION_CONFLICT: (
            "Another repository operation is active."
        ),
        ProtocolErrorCode.OPERATION_FAILED: "System operation failed.",
    }
)


@dataclass(frozen=True, slots=True)
class RequestEnvelope:
    """Validated request that contains only action-specific parameters."""

    request_id: UUID
    action: SystemAction
    parameters: Mapping[str, Any]
    protocol_version: int = PROTOCOL_VERSION

    @classmethod
    def from_mapping(cls, payload: object) -> "RequestEnvelope":
        """Parse an untrusted mapping and reject unknown or unsafe fields."""
        envelope = require_exact_mapping(
            payload,
            field="request",
            required=frozenset(
                {"protocol_version", "request_id", "action", "parameters"}
            ),
        )
        return cls(
            protocol_version=envelope["protocol_version"],
            request_id=envelope["request_id"],
            action=envelope["action"],
            parameters=envelope["parameters"],
        )

    def __post_init__(self) -> None:
        """Ensure direct construction cannot bypass strict parsing."""
        protocol_version = require_int(
            self.protocol_version,
            field="protocol_version",
            minimum=1,
            maximum=255,
        )
        if protocol_version != PROTOCOL_VERSION:
            raise ValueError("protocol_version is unsupported")
        action = require_enum(self.action, SystemAction, field="action")
        required, optional = _PARAMETER_FIELDS[action]
        raw_parameters = require_exact_mapping(
            self.parameters,
            field="parameters",
            required=required,
            optional=optional,
        )
        object.__setattr__(
            self,
            "request_id",
            require_uuid(self.request_id, field="request_id"),
        )
        object.__setattr__(self, "action", action)
        object.__setattr__(
            self,
            "parameters",
            freeze_mapping(_validate_parameters(action, raw_parameters)),
        )
        object.__setattr__(self, "protocol_version", protocol_version)

    def to_wire(self) -> dict[str, Any]:
        """Return JSON-compatible protocol fields."""
        return {
            "protocol_version": self.protocol_version,
            "request_id": str(self.request_id),
            "action": self.action.value,
            "parameters": deep_thaw(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class ResponseEnvelope:
    """Validated response with a projected result or stable safe error."""

    request_id: UUID
    status: ResponseStatus
    result: Mapping[str, Any] | None = None
    error_code: ProtocolErrorCode | None = None
    safe_summary: str | None = None
    protocol_version: int = PROTOCOL_VERSION

    def __post_init__(self) -> None:
        """Validate success/error exclusivity and freeze the response result."""
        object.__setattr__(
            self,
            "request_id",
            require_uuid(self.request_id, field="request_id"),
        )
        object.__setattr__(
            self,
            "status",
            require_enum(self.status, ResponseStatus, field="status"),
        )
        protocol_version = require_int(
            self.protocol_version,
            field="protocol_version",
            minimum=1,
            maximum=255,
        )
        if protocol_version != PROTOCOL_VERSION:
            raise ValueError("protocol_version is unsupported")
        object.__setattr__(self, "protocol_version", protocol_version)
        if self.status is ResponseStatus.OK:
            if not isinstance(self.result, Mapping):
                raise TypeError("successful response result must be a mapping")
            if self.error_code is not None or self.safe_summary is not None:
                raise ValueError("successful responses cannot contain an error")
            object.__setattr__(self, "result", deep_freeze(self.result))
            return
        if self.result is not None:
            raise ValueError("error responses cannot contain a result")
        if self.error_code is None:
            raise ValueError("error responses require an error_code")
        error_code = require_enum(
            self.error_code,
            ProtocolErrorCode,
            field="error_code",
        )
        expected_summary = PROTOCOL_ERROR_SUMMARIES[error_code]
        if self.safe_summary != expected_summary:
            raise ValueError("safe_summary must match the stable error code")
        object.__setattr__(self, "error_code", error_code)

    @classmethod
    def success(
        cls,
        request_id: UUID,
        action: SystemAction,
        payload: object,
    ) -> "ResponseEnvelope":
        """Build a successful response through the action projection."""
        return cls(
            request_id=request_id,
            status=ResponseStatus.OK,
            result=project_response(action, payload),
        )

    @classmethod
    def error(
        cls,
        request_id: UUID,
        status: ResponseStatus,
        error_code: ProtocolErrorCode,
    ) -> "ResponseEnvelope":
        """Build a metadata-free error from a stable code."""
        if status is ResponseStatus.OK:
            raise ValueError("error response status cannot be ok")
        error_code = require_enum(
            error_code,
            ProtocolErrorCode,
            field="error_code",
        )
        return cls(
            request_id=request_id,
            status=status,
            error_code=error_code,
            safe_summary=PROTOCOL_ERROR_SUMMARIES[error_code],
        )

    @classmethod
    def from_mapping(
        cls,
        payload: object,
        *,
        action: SystemAction,
    ) -> "ResponseEnvelope":
        """Parse an untrusted response and re-project successful results."""
        response = require_exact_mapping(
            payload,
            field="response",
            required=frozenset(
                {
                    "protocol_version",
                    "request_id",
                    "status",
                    "result",
                    "error_code",
                    "safe_summary",
                }
            ),
        )
        status = require_enum(response["status"], ResponseStatus, field="status")
        result = response["result"]
        if status is ResponseStatus.OK:
            result = project_response(action, result)
        error_code = response["error_code"]
        if error_code is not None:
            error_code = require_enum(
                error_code,
                ProtocolErrorCode,
                field="error_code",
            )
        return cls(
            protocol_version=response["protocol_version"],
            request_id=response["request_id"],
            status=status,
            result=result,
            error_code=error_code,
            safe_summary=response["safe_summary"],
        )

    def to_wire(self) -> dict[str, Any]:
        """Return JSON-compatible protocol fields."""
        return {
            "protocol_version": self.protocol_version,
            "request_id": str(self.request_id),
            "status": self.status.value,
            "result": deep_thaw(self.result),
            "error_code": self.error_code.value if self.error_code else None,
            "safe_summary": self.safe_summary,
        }


def _validate_parameters(
    action: SystemAction,
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    if "limit" in parameters:
        validated["limit"] = require_int(
            parameters["limit"],
            field="parameters.limit",
            minimum=1,
            maximum=1_000,
        )
    if "run_id" in parameters:
        validated["run_id"] = str(
            require_uuid(parameters["run_id"], field="parameters.run_id")
        )
    enum_fields = {
        "operation": OperationType,
        "state": RunState,
        "level": DiagnosticLevel,
    }
    for field_name, enum_type in enum_fields.items():
        if field_name in parameters:
            validated[field_name] = require_enum(
                parameters[field_name],
                enum_type,
                field=f"parameters.{field_name}",
            ).value
    if action is SystemAction.BACKUP_REQUEST:
        validated["target_id"] = require_safe_identifier(
            parameters["target_id"],
            field="parameters.target_id",
        )
    if action is SystemAction.RETENTION_REQUEST:
        validated["policy_fingerprint"] = require_fingerprint(
            parameters["policy_fingerprint"],
            field="parameters.policy_fingerprint",
        )
        if "dry_run" in parameters:
            validated["dry_run"] = require_bool(
                parameters["dry_run"],
                field="parameters.dry_run",
            )
    return validated


def project_response(action: SystemAction, payload: object) -> dict[str, Any]:
    """Project backend data through the action's explicit response schema."""
    if not isinstance(payload, Mapping):
        raise TypeError("response payload must be a mapping")
    if action is SystemAction.RUN_LIST:
        return {"runs": _project_run_sequence(payload.get("runs"))}
    if action is SystemAction.RUN_DETAIL:
        return {"run": _project_run(payload.get("run"))}
    if action is SystemAction.DIAGNOSTIC_LIST:
        return {"diagnostics": _project_diagnostic_sequence(payload.get("diagnostics"))}
    if action in {SystemAction.BACKUP_REQUEST, SystemAction.RETENTION_REQUEST}:
        return _project_receipt(payload)
    if action is SystemAction.HEALTH:
        return _project_health(payload)
    if action is SystemAction.SCHEDULE_SUMMARY:
        return _project_schedule(payload)
    if action is SystemAction.STATUS_SNAPSHOT:
        return _project_status_snapshot(payload)
    if action is SystemAction.UI_AVAILABILITY:
        projected = _project_mapping(payload, frozenset({"available"}), "ui")
        if "available" not in projected:
            raise ValueError("ui available is required")
        return {"available": require_bool(projected["available"], field="ui.available")}
    raise ValueError("unsupported response action")


def _project_mapping(
    value: object,
    allowed: frozenset[str],
    field: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be a mapping")
    return {key: value[key] for key in allowed if key in value}


def _project_run(value: object) -> dict[str, Any]:
    projected = _project_mapping(value, _RUN_VIEW_FIELDS, "run")
    return RunRecordView.from_mapping(projected).to_wire()


def _project_run_sequence(value: object) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("runs must be a sequence")
    if len(value) > 1_000:
        raise ValueError("runs exceeds the response record bound")
    return [_project_run(item) for item in value]


def _project_diagnostic(value: object) -> dict[str, Any]:
    projected = _project_mapping(value, _DIAGNOSTIC_VIEW_FIELDS, "diagnostic")
    return DiagnosticView.from_mapping(projected).to_wire()


def _project_diagnostic_sequence(value: object) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("diagnostics must be a sequence")
    if len(value) > 1_000:
        raise ValueError("diagnostics exceeds the response record bound")
    return [_project_diagnostic(item) for item in value]


def _project_receipt(value: object) -> dict[str, Any]:
    projected = _project_mapping(value, _ACTION_RECEIPT_FIELDS, "receipt")
    required = _ACTION_RECEIPT_FIELDS - frozenset({"run_id"})
    missing = required - frozenset(projected)
    if missing:
        raise ValueError(f"receipt is missing required fields: {sorted(missing)}")
    receipt = ActionReceipt(
        request_id=projected["request_id"],
        accepted=projected["accepted"],
        status=projected["status"],
        run_id=projected.get("run_id"),
    )
    return receipt.to_wire()


def _project_health(value: object) -> dict[str, Any]:
    projected = _project_mapping(
        value,
        frozenset({"backend_available", "protocol_min", "protocol_max"}),
        "health",
    )
    missing = frozenset(
        {"backend_available", "protocol_min", "protocol_max"}
    ) - frozenset(projected)
    if missing:
        raise ValueError(f"health is missing required fields: {sorted(missing)}")
    protocol_min = require_int(
        projected["protocol_min"],
        field="health.protocol_min",
        minimum=1,
        maximum=255,
    )
    protocol_max = require_int(
        projected["protocol_max"],
        field="health.protocol_max",
        minimum=protocol_min,
        maximum=255,
    )
    return {
        "backend_available": require_bool(
            projected["backend_available"],
            field="health.backend_available",
        ),
        "protocol_min": protocol_min,
        "protocol_max": protocol_max,
    }


def _project_schedule(value: object) -> dict[str, Any]:
    projected = _project_mapping(
        value,
        frozenset({"next_backup_at", "next_retention_at"}),
        "schedule",
    )
    missing = frozenset({"next_backup_at", "next_retention_at"}) - frozenset(projected)
    if missing:
        raise ValueError(f"schedule is missing required fields: {sorted(missing)}")
    for key in ("next_backup_at", "next_retention_at"):
        timestamp = projected[key]
        if timestamp is not None:
            projected[key] = require_wire_utc_datetime(
                timestamp,
                field=f"schedule.{key}",
            ).isoformat()
    return projected


def _project_status_snapshot(value: object) -> dict[str, Any]:
    projected = _project_mapping(value, _STATUS_SNAPSHOT_FIELDS, "status_snapshot")
    missing = _STATUS_SNAPSHOT_FIELDS - frozenset(projected)
    if missing:
        raise ValueError(
            f"status_snapshot is missing required fields: {sorted(missing)}"
        )
    if projected["latest_backup"] is not None:
        projected["latest_backup"] = _project_run(projected["latest_backup"])
    if projected["latest_retention"] is not None:
        projected["latest_retention"] = _project_run(projected["latest_retention"])
    return StatusSnapshot.from_mapping(projected).to_wire()
