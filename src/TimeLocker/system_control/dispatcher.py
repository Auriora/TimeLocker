"""Bounded authorization and dispatch for the local system-control protocol."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from types import MappingProxyType
from typing import Any, Protocol
from uuid import UUID

from .interfaces import GroupMembershipResolver, PeerIdentity
from .models import SystemPolicy
from .protocol import RequestEnvelope, ResponseEnvelope
from .types import ProtocolErrorCode, ResponseStatus, SystemAction


_UNKNOWN_REQUEST_ID = UUID(int=0)
_OPERATOR_ACTIONS = frozenset(SystemAction)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Secret-free decision record retained inside the privileged boundary."""

    platform_id: str
    action: SystemAction | None
    decision: str
    status: ResponseStatus
    result_code: ProtocolErrorCode | None


class AuditSink(Protocol):
    """Consume secret-free authorization and dispatch decisions."""

    def record(self, event: AuditEvent) -> None:
        """Persist or emit one bounded audit event."""


class LocalControlDispatcher:
    """Authenticate every request and dispatch only strict allowlisted actions."""

    def __init__(
        self,
        *,
        policy: SystemPolicy,
        membership_resolver: GroupMembershipResolver,
        handlers: Mapping[SystemAction, Callable[[RequestEnvelope], object]],
        audit_sink: AuditSink,
    ) -> None:
        if not isinstance(policy, SystemPolicy):
            raise TypeError("policy must be a SystemPolicy")
        normalized_handlers: dict[
            SystemAction, Callable[[RequestEnvelope], object]
        ] = {}
        for action, handler in handlers.items():
            if not isinstance(action, SystemAction):
                raise TypeError("handler keys must be SystemAction values")
            if not callable(handler):
                raise TypeError("handlers must be callable")
            normalized_handlers[action] = handler
        self.policy = policy
        self.membership_resolver = membership_resolver
        self.handlers = MappingProxyType(normalized_handlers)
        if not hasattr(audit_sink, "record"):
            raise TypeError("audit_sink must provide record(event)")
        self.audit_sink = audit_sink

    def handle(self, request: bytes, identity: PeerIdentity) -> bytes:
        """Return one JSON response without propagating protected details."""
        if not isinstance(identity, PeerIdentity):
            raise TypeError("identity must be a PeerIdentity")
        request_id = _extract_request_id(request)
        if (
            not isinstance(request, bytes)
            or len(request) > self.policy.max_request_bytes
        ):
            return self._encoded_error(
                request_id,
                identity,
                None,
                ResponseStatus.INVALID,
                ProtocolErrorCode.INVALID_REQUEST,
            )
        try:
            decoded = json.loads(request.decode("utf-8"))
            envelope = RequestEnvelope.from_mapping(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            code = _parse_error_code(request)
            return self._encoded_error(
                request_id,
                identity,
                None,
                ResponseStatus.INVALID,
                code,
            )
        if not self._authorized(identity, envelope.action):
            return self._encoded_error(
                envelope.request_id,
                identity,
                envelope.action,
                ResponseStatus.DENIED,
                ProtocolErrorCode.SYSTEM_ACCESS_DENIED,
            )
        handler = self.handlers.get(envelope.action)
        if handler is None:
            return self._encoded_error(
                envelope.request_id,
                identity,
                envelope.action,
                ResponseStatus.UNAVAILABLE,
                ProtocolErrorCode.SYSTEM_BACKEND_UNAVAILABLE,
            )
        try:
            response = ResponseEnvelope.success(
                envelope.request_id,
                envelope.action,
                handler(envelope),
            )
        except Exception:
            response = ResponseEnvelope.error(
                envelope.request_id,
                ResponseStatus.FAILED,
                ProtocolErrorCode.OPERATION_FAILED,
            )
            self._audit(
                identity,
                envelope.action,
                "failed",
                ResponseStatus.FAILED,
                ProtocolErrorCode.OPERATION_FAILED,
            )
        else:
            self._audit(
                identity,
                envelope.action,
                "allowed",
                ResponseStatus.OK,
                None,
            )
        return _encode_response(response)

    def _authorized(self, identity: PeerIdentity, action: SystemAction) -> bool:
        if action not in _OPERATOR_ACTIONS:
            return False
        try:
            return bool(
                self.membership_resolver.is_current_member(
                    identity,
                    self.policy.operator_group,
                )
            )
        except (KeyError, OSError, RuntimeError, ValueError):
            return False

    def _encoded_error(
        self,
        request_id: UUID,
        identity: PeerIdentity,
        action: SystemAction | None,
        status: ResponseStatus,
        error_code: ProtocolErrorCode,
    ) -> bytes:
        self._audit(identity, action, "denied", status, error_code)
        return _encode_response(ResponseEnvelope.error(request_id, status, error_code))

    def _audit(
        self,
        identity: PeerIdentity,
        action: SystemAction | None,
        decision: str,
        status: ResponseStatus,
        result_code: ProtocolErrorCode | None,
    ) -> None:
        self.audit_sink.record(
            AuditEvent(
                platform_id=identity.platform_id,
                action=action,
                decision=decision,
                status=status,
                result_code=result_code,
            )
        )


def _encode_response(response: ResponseEnvelope) -> bytes:
    return (
        json.dumps(response.to_wire(), separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _extract_request_id(request: object) -> UUID:
    if not isinstance(request, bytes) or len(request) > 1_048_576:
        return _UNKNOWN_REQUEST_ID
    try:
        value = json.loads(request.decode("utf-8"))
        if not isinstance(value, Mapping):
            return _UNKNOWN_REQUEST_ID
        request_id = value.get("request_id")
        if not isinstance(request_id, str):
            return _UNKNOWN_REQUEST_ID
        parsed = UUID(request_id)
        return parsed if str(parsed) == request_id else _UNKNOWN_REQUEST_ID
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return _UNKNOWN_REQUEST_ID


def _parse_error_code(request: bytes) -> ProtocolErrorCode:
    try:
        value: Any = json.loads(request.decode("utf-8"))
        if isinstance(value, Mapping) and value.get("protocol_version") != 1:
            return ProtocolErrorCode.CONTRACT_VERSION_UNSUPPORTED
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return ProtocolErrorCode.INVALID_REQUEST
