"""Focused client for the protected local system-control contract."""

import json
import socket
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .models import (
    ActionReceipt,
    BackupActionRequest,
    DiagnosticQuery,
    DiagnosticView,
    RetentionActionRequest,
    RunQuery,
    RunRecordView,
)
from .protocol import RequestEnvelope, ResponseEnvelope
from .types import ProtocolErrorCode, ResponseStatus, SystemAction


DEFAULT_SOCKET_PATH = Path("/run/timelocker/control.sock")
DEFAULT_MAX_RESPONSE_BYTES = 1_048_576


class SystemControlClientError(RuntimeError):
    """Safe client-visible backend failure."""

    def __init__(
        self,
        error_code: ProtocolErrorCode,
        safe_summary: str,
        *,
        status: ResponseStatus,
    ) -> None:
        super().__init__(safe_summary)
        self.error_code = error_code
        self.status = status


class UnixSocketSystemControlClient:
    """Versioned system-control client with a bounded Unix socket transport."""

    def __init__(
        self,
        *,
        socket_path: Path = DEFAULT_SOCKET_PATH,
        timeout_seconds: float = 5.0,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        exchange: Callable[[bytes], bytes] | None = None,
    ) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 60:
            raise ValueError("timeout_seconds must be between zero and 60")
        if max_response_bytes < 1_024 or max_response_bytes > 16_777_216:
            raise ValueError("max_response_bytes is outside the supported range")
        self.socket_path = socket_path
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self._exchange_override = exchange

    def list_runs(self, query: RunQuery) -> list[RunRecordView]:
        parameters: dict[str, object] = {"limit": query.limit}
        if query.operation is not None:
            parameters["operation"] = query.operation.value
        if query.state is not None:
            parameters["state"] = query.state.value
        result = self._request(SystemAction.RUN_LIST, parameters)
        return [RunRecordView.from_mapping(item) for item in result["runs"]]

    def get_run(self, run_id: UUID) -> RunRecordView:
        result = self._request(
            SystemAction.RUN_DETAIL,
            {"run_id": str(run_id)},
        )
        return RunRecordView.from_mapping(result["run"])

    def list_diagnostics(self, query: DiagnosticQuery) -> list[DiagnosticView]:
        parameters: dict[str, object] = {"limit": query.limit}
        if query.run_id is not None:
            parameters["run_id"] = str(query.run_id)
        if query.level is not None:
            parameters["level"] = query.level.value
        result = self._request(SystemAction.DIAGNOSTIC_LIST, parameters)
        return [DiagnosticView.from_mapping(item) for item in result["diagnostics"]]

    def request_backup(self, request: BackupActionRequest) -> ActionReceipt:
        result = self._request(
            SystemAction.BACKUP_REQUEST,
            {"target_id": request.target_id},
        )
        return _receipt_from_mapping(result)

    def request_retention(self, request: RetentionActionRequest) -> ActionReceipt:
        result = self._request(
            SystemAction.RETENTION_REQUEST,
            {
                "policy_fingerprint": request.policy_fingerprint,
                "dry_run": request.dry_run,
            },
        )
        return _receipt_from_mapping(result)

    def _request(
        self,
        action: SystemAction,
        parameters: Mapping[str, object],
    ) -> Mapping[str, Any]:
        request = RequestEnvelope(
            request_id=uuid4(),
            action=action,
            parameters=parameters,
        )
        payload = (
            json.dumps(request.to_wire(), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        try:
            raw_response = (
                self._exchange_override(payload)
                if self._exchange_override is not None
                else self._socket_exchange(payload)
            )
            if len(raw_response) > self.max_response_bytes:
                raise ValueError("response exceeds configured bound")
            decoded = json.loads(raw_response.decode("utf-8"))
            response = ResponseEnvelope.from_mapping(decoded, action=action)
        except SystemControlClientError:
            raise
        except (OSError, TimeoutError):
            raise SystemControlClientError(
                ProtocolErrorCode.SYSTEM_BACKEND_UNAVAILABLE,
                "System backend is unavailable. "
                "Run 'systemctl status timelocker-control.socket'.",
                status=ResponseStatus.UNAVAILABLE,
            ) from None
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            raise SystemControlClientError(
                ProtocolErrorCode.INVALID_REQUEST,
                "System backend returned an invalid response.",
                status=ResponseStatus.INVALID,
            ) from None
        if response.request_id != request.request_id:
            raise SystemControlClientError(
                ProtocolErrorCode.INVALID_REQUEST,
                "System backend returned an invalid response.",
                status=ResponseStatus.INVALID,
            )
        if response.status is not ResponseStatus.OK:
            assert response.error_code is not None
            assert response.safe_summary is not None
            raise SystemControlClientError(
                response.error_code,
                response.safe_summary,
                status=response.status,
            )
        assert response.result is not None
        return response.result

    def _socket_exchange(self, request: bytes) -> bytes:
        if not hasattr(socket, "AF_UNIX"):
            raise OSError("Unix sockets are unavailable")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(self.timeout_seconds)
            connection.connect(str(self.socket_path))
            connection.sendall(request)
            chunks: list[bytes] = []
            size = 0
            while size <= self.max_response_bytes:
                chunk = connection.recv(min(65_536, self.max_response_bytes + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if b"\n" in chunk:
                    break
            response = b"".join(chunks)
            newline = response.find(b"\n")
            return response[:newline] if newline >= 0 else response


def _receipt_from_mapping(value: Mapping[str, Any]) -> ActionReceipt:
    return ActionReceipt(
        request_id=value["request_id"],
        accepted=value["accepted"],
        status=value["status"],
        run_id=value.get("run_id"),
    )
