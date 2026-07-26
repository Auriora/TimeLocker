"""Focused protected system-control client tests."""

import json
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from TimeLocker.system_control.client import (
    SystemControlClientError,
    UnixSocketSystemControlClient,
)
from TimeLocker.system_control.models import (
    DiagnosticQuery,
    DiagnosticRecord,
    DiagnosticView,
    RunQuery,
    RunRecord,
    RunRecordView,
    BackupActionRequest,
    RetentionActionRequest,
    ActionReceipt,
)
from TimeLocker.system_control.protocol import ResponseEnvelope
from TimeLocker.system_control.types import (
    DiagnosticCode,
    DiagnosticComponent,
    DiagnosticLevel,
    OperationTrigger,
    OperationType,
    ProtocolErrorCode,
    ResponseStatus,
    ResultCode,
    RunState,
    SystemAction,
)


RUN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _run() -> RunRecordView:
    return RunRecordView.from_record(
        RunRecord(
            run_id=RUN_ID,
            operation=OperationType.BACKUP,
            trigger=OperationTrigger.SCHEDULED,
            target_id="production",
            started_at=datetime(2026, 7, 26, 2, 30, tzinfo=UTC),
            completed_at=datetime(2026, 7, 26, 2, 45, tzinfo=UTC),
            state=RunState.SUCCEEDED,
            result_code=ResultCode.BACKUP_SUCCEEDED,
        )
    )


def _success_exchange(action: SystemAction, result: object):
    def exchange(request: bytes) -> bytes:
        parsed = json.loads(request)
        assert parsed["action"] == action.value
        response = ResponseEnvelope.success(
            UUID(parsed["request_id"]),
            action,
            result,
        )
        return json.dumps(response.to_wire()).encode()

    return exchange


@pytest.mark.unit
def test_list_runs_sends_bounded_filters_and_parses_projected_records() -> None:
    def exchange(request: bytes) -> bytes:
        parsed = json.loads(request)
        assert parsed["parameters"] == {
            "limit": 5,
            "operation": "backup",
            "state": "succeeded",
        }
        return json.dumps(
            ResponseEnvelope.success(
                UUID(parsed["request_id"]),
                SystemAction.RUN_LIST,
                {"runs": [_run().to_wire()]},
            ).to_wire()
        ).encode()

    client = UnixSocketSystemControlClient(exchange=exchange)
    runs = client.list_runs(
        RunQuery(
            limit=5,
            operation=OperationType.BACKUP,
            state=RunState.SUCCEEDED,
        )
    )
    assert runs == [_run()]


@pytest.mark.unit
def test_get_run_and_diagnostics_use_only_structured_contract_fields() -> None:
    run_client = UnixSocketSystemControlClient(
        exchange=_success_exchange(
            SystemAction.RUN_DETAIL,
            {"run": _run().to_wire()},
        )
    )
    assert run_client.get_run(RUN_ID) == _run()

    diagnostic = DiagnosticView.from_record(
        DiagnosticRecord(
            record_id=uuid4(),
            run_id=RUN_ID,
            timestamp=datetime(2026, 7, 26, 2, 45, tzinfo=UTC),
            level=DiagnosticLevel.INFO,
            component=DiagnosticComponent.BACKUP,
            message_code=DiagnosticCode.BACKUP_SUCCEEDED,
        )
    )
    diagnostics_client = UnixSocketSystemControlClient(
        exchange=_success_exchange(
            SystemAction.DIAGNOSTIC_LIST,
            {"diagnostics": [diagnostic.to_wire()]},
        )
    )
    assert diagnostics_client.list_diagnostics(DiagnosticQuery(limit=10)) == [
        diagnostic
    ]


@pytest.mark.unit
def test_denial_exposes_only_stable_safe_error() -> None:
    secret = "s3://secret-bucket repository-password"

    def exchange(request: bytes) -> bytes:
        request_id = UUID(json.loads(request)["request_id"])
        response = ResponseEnvelope.error(
            request_id,
            ResponseStatus.DENIED,
            ProtocolErrorCode.SYSTEM_ACCESS_DENIED,
        )
        encoded = json.dumps(response.to_wire())
        assert secret not in encoded
        return encoded.encode()

    client = UnixSocketSystemControlClient(exchange=exchange)
    with pytest.raises(SystemControlClientError) as caught:
        client.list_runs(RunQuery())
    assert caught.value.error_code is ProtocolErrorCode.SYSTEM_ACCESS_DENIED
    assert str(caught.value) == "System access denied."
    assert secret not in str(caught.value)


@pytest.mark.unit
def test_unavailable_transport_has_actionable_bounded_message() -> None:
    def unavailable(_request: bytes) -> bytes:
        raise FileNotFoundError

    client = UnixSocketSystemControlClient(exchange=unavailable)
    with pytest.raises(SystemControlClientError) as caught:
        client.list_runs(RunQuery())
    assert caught.value.error_code is ProtocolErrorCode.SYSTEM_BACKEND_UNAVAILABLE
    assert "systemctl status timelocker-control.socket" in str(caught.value)


@pytest.mark.unit
def test_mismatched_response_id_is_rejected() -> None:
    def exchange(_request: bytes) -> bytes:
        return json.dumps(
            ResponseEnvelope.success(
                uuid4(),
                SystemAction.RUN_LIST,
                {"runs": []},
            ).to_wire()
        ).encode()

    client = UnixSocketSystemControlClient(exchange=exchange)
    with pytest.raises(SystemControlClientError) as caught:
        client.list_runs(RunQuery())
    assert caught.value.error_code is ProtocolErrorCode.INVALID_REQUEST


@pytest.mark.unit
def test_action_requests_preserve_only_allowlisted_parameters() -> None:
    accepted_id = uuid4()

    def exchange(request: bytes) -> bytes:
        parsed = json.loads(request)
        if parsed["action"] == SystemAction.BACKUP_REQUEST.value:
            assert parsed["parameters"] == {"target_id": "production"}
            action = SystemAction.BACKUP_REQUEST
        else:
            assert parsed["parameters"] == {
                "policy_fingerprint": "a" * 64,
                "dry_run": True,
            }
            action = SystemAction.RETENTION_REQUEST
        response = ResponseEnvelope.success(
            UUID(parsed["request_id"]),
            action,
            ActionReceipt(
                request_id=UUID(parsed["request_id"]),
                accepted=True,
                status="queued",
                run_id=accepted_id,
            ).to_wire(),
        )
        return json.dumps(response.to_wire()).encode()

    client = UnixSocketSystemControlClient(exchange=exchange)
    assert (
        client.request_backup(BackupActionRequest("production")).run_id == accepted_id
    )
    assert (
        client.request_retention(RetentionActionRequest("a" * 64, dry_run=True)).run_id
        == accepted_id
    )


@pytest.mark.unit
def test_invalid_or_oversized_response_fails_closed() -> None:
    invalid = UnixSocketSystemControlClient(exchange=lambda _request: b"{")
    with pytest.raises(SystemControlClientError) as invalid_error:
        invalid.list_runs(RunQuery())
    assert invalid_error.value.error_code is ProtocolErrorCode.INVALID_REQUEST

    oversized = UnixSocketSystemControlClient(
        max_response_bytes=1024,
        exchange=lambda _request: b"x" * 1025,
    )
    with pytest.raises(SystemControlClientError) as oversized_error:
        oversized.list_runs(RunQuery())
    assert oversized_error.value.error_code is ProtocolErrorCode.INVALID_REQUEST


@pytest.mark.unit
def test_unix_socket_exchange_is_bounded_and_line_framed() -> None:
    class FakeSocket:
        request: bytes
        timeout: float
        connected: str

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def settimeout(self, timeout: float) -> None:
            self.timeout = timeout

        def connect(self, path: str) -> None:
            self.connected = path

        def sendall(self, request: bytes) -> None:
            self.request = request

        def recv(self, _maximum: int) -> bytes:
            parsed = json.loads(self.request)
            response = ResponseEnvelope.success(
                UUID(parsed["request_id"]),
                SystemAction.RUN_LIST,
                {"runs": []},
            )
            return json.dumps(response.to_wire()).encode() + b"\nignored"

    connection = FakeSocket()
    with patch(
        "TimeLocker.system_control.client.socket.socket",
        return_value=connection,
    ):
        client = UnixSocketSystemControlClient(timeout_seconds=1)
        assert client.list_runs(RunQuery()) == []
    assert connection.timeout == 1
    assert connection.connected == "/run/timelocker/control.sock"
