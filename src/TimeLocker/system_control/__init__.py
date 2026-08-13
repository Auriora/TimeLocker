"""Platform-neutral contracts for privileged TimeLocker system operations."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ActionReceipt",
    "ActionClass",
    "ActionRoute",
    "AuditEvent",
    "AuditSink",
    "BackendStatus",
    "BackupScheduleHealth",
    "AtomicRecordStore",
    "BackupActionRequest",
    "BoundedStatusEventBroker",
    "BoundedStatusSubscription",
    "FileSystemProtectedStateWatcher",
    "ControlRequestHandler",
    "DiagnosticCode",
    "DiagnosticComponent",
    "DiagnosticLevel",
    "DiagnosticQuery",
    "DiagnosticRecord",
    "DiagnosticView",
    "GroupMembershipResolver",
    "InvalidTransitionError",
    "LocalControlTransport",
    "LocalControlDispatcher",
    "MutationConflictError",
    "OperationTrigger",
    "OperationType",
    "PeerIdentity",
    "PeerIdentityProvider",
    "ProtocolErrorCode",
    "ProtectedStateChangeMonitor",
    "ProtectedStateWatcher",
    "RecordCorruptionError",
    "RecordNotFoundError",
    "RecordStoreError",
    "RequestEnvelope",
    "ResponseEnvelope",
    "ResponseStatus",
    "ResultCode",
    "RetentionActionRequest",
    "RetentionAdapter",
    "RetentionExecutionResult",
    "RetentionExecutor",
    "RetentionPlan",
    "RetentionPolicy",
    "RetentionRequestHandler",
    "RetentionTriggerCoordinator",
    "RetentionTriggerStore",
    "ScheduleSummary",
    "RepositoryMutationLease",
    "RepositoryMutationLock",
    "RunQuery",
    "RunRecord",
    "RunRecordView",
    "RunTransition",
    "RunState",
    "StatusEvent",
    "StatusEventAccessDenied",
    "StatusEventBroker",
    "StatusEventClient",
    "StatusEventConnectionState",
    "StatusEventKind",
    "StatusEventTransport",
    "StatusRevision",
    "StatusSnapshot",
    "StatusSnapshotProvider",
    "StatusSubscription",
    "StatusSubscriptionLimitError",
    "StatusChangeCoordinator",
    "StatusWatchSignal",
    "STATUS_EVENT_PROTOCOL_VERSION",
    "STATUS_EVENT_SCHEMA_VERSION",
    "SystemAction",
    "SystemControlClient",
    "SystemControlClientError",
    "SystemPolicy",
    "UnixSocketSystemControlClient",
    "UnixSocketStatusEventClient",
    "UnknownPublicActionError",
    "classify_public_action",
    "project_response",
    "reconcile_abandoned_runs",
]

_MODULE_EXPORTS = {
    ".action_policy": (
        "ActionClass",
        "ActionRoute",
        "UnknownPublicActionError",
        "classify_public_action",
    ),
    ".client": (
        "SystemControlClientError",
        "UnixSocketSystemControlClient",
    ),
    ".dispatcher": (
        "AuditEvent",
        "AuditSink",
        "LocalControlDispatcher",
    ),
    ".event_client": (
        "StatusEventAccessDenied",
        "UnixSocketStatusEventClient",
    ),
    ".interfaces": (
        "ControlRequestHandler",
        "GroupMembershipResolver",
        "LocalControlTransport",
        "PeerIdentity",
        "PeerIdentityProvider",
        "StatusEventBroker",
        "StatusEventClient",
        "StatusEventTransport",
        "StatusSnapshotProvider",
        "StatusSubscription",
        "SystemControlClient",
    ),
    ".models": (
        "ActionReceipt",
        "BackupActionRequest",
        "DiagnosticQuery",
        "DiagnosticRecord",
        "DiagnosticView",
        "RetentionActionRequest",
        "RetentionPolicy",
        "RunQuery",
        "RunRecord",
        "RunRecordView",
        "RunTransition",
        "ScheduleSummary",
        "StatusEvent",
        "StatusRevision",
        "StatusSnapshot",
        "STATUS_EVENT_PROTOCOL_VERSION",
        "STATUS_EVENT_SCHEMA_VERSION",
        "SystemPolicy",
    ),
    ".protocol": (
        "RequestEnvelope",
        "ResponseEnvelope",
        "project_response",
    ),
    ".retention": (
        "RetentionAdapter",
        "RetentionExecutionResult",
        "RetentionExecutor",
        "RetentionPlan",
        "RetentionRequestHandler",
        "RetentionTriggerCoordinator",
        "RetentionTriggerStore",
    ),
    ".status_events": (
        "BoundedStatusEventBroker",
        "BoundedStatusSubscription",
        "FileSystemProtectedStateWatcher",
        "ProtectedStateChangeMonitor",
        "ProtectedStateWatcher",
        "StatusChangeCoordinator",
        "StatusSubscriptionLimitError",
        "StatusWatchSignal",
    ),
    ".storage": (
        "AtomicRecordStore",
        "InvalidTransitionError",
        "MutationConflictError",
        "RecordCorruptionError",
        "RecordNotFoundError",
        "RecordStoreError",
        "RepositoryMutationLease",
        "RepositoryMutationLock",
        "reconcile_abandoned_runs",
    ),
    ".types": (
        "BackendStatus",
        "BackupScheduleHealth",
        "DiagnosticCode",
        "DiagnosticComponent",
        "DiagnosticLevel",
        "OperationTrigger",
        "OperationType",
        "ProtocolErrorCode",
        "ResponseStatus",
        "ResultCode",
        "RunState",
        "StatusEventConnectionState",
        "StatusEventKind",
        "SystemAction",
    ),
}
_LAZY_EXPORTS = {
    name: module_name
    for module_name, names in _MODULE_EXPORTS.items()
    for name in names
}


def __getattr__(name: str) -> Any:
    """Load public system-control contracts only when requested."""
    try:
        module_name = _LAZY_EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Include lazy public contracts in interactive discovery."""
    return sorted({*globals(), *_LAZY_EXPORTS})
