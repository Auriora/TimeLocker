"""Security and contract tests for system-control request parsing."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from TimeLocker.system_control import (
    BackendStatus,
    ProtocolErrorCode,
    RequestEnvelope,
    ResponseEnvelope,
    ResponseStatus,
    SystemAction,
    StatusRevision,
    StatusSnapshot,
    project_response,
)


def request_payload(
    action: str = "health",
    parameters: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build one otherwise-valid protocol request."""
    return {
        "protocol_version": 2,
        "request_id": str(uuid4()),
        "action": action,
        "parameters": parameters or {},
    }


def run_payload(**overrides: object) -> dict[str, object]:
    """Build a complete projected run with optional malicious fields."""
    payload: dict[str, object] = {
        "run_id": str(uuid4()),
        "operation": "backup",
        "trigger": "scheduled",
        "target_id": "production",
        "started_at": datetime(2026, 7, 26, 3, 30, tzinfo=timezone.utc).isoformat(),
        "completed_at": datetime(2026, 7, 26, 3, 45, tzinfo=timezone.utc).isoformat(),
        "state": "succeeded",
        "result_code": "backup_succeeded",
        "safe_summary": "untrusted text",
        "policy_fingerprint": None,
        "counters": {"files_processed": 10},
    }
    payload.update(overrides)
    return payload


def diagnostic_payload(**overrides: object) -> dict[str, object]:
    """Build a complete projected diagnostic with optional malicious fields."""
    payload: dict[str, object] = {
        "record_id": str(uuid4()),
        "run_id": str(uuid4()),
        "timestamp": datetime(2026, 7, 26, 3, 45, tzinfo=timezone.utc).isoformat(),
        "level": "error",
        "component": "backup",
        "message_code": "operation_failed",
        "safe_summary": "untrusted text",
    }
    payload.update(overrides)
    return payload


@pytest.mark.unit
@pytest.mark.security
class TestRequestEnvelope:
    """Reject payload identity, secrets, arbitrary paths, and unbounded input."""

    def test_valid_request_is_frozen_and_normalized(self) -> None:
        request = RequestEnvelope.from_mapping(
            request_payload(
                "run.list",
                {"limit": 25, "operation": "backup", "state": "succeeded"},
            )
        )

        assert request.action is SystemAction.RUN_LIST
        assert request.parameters == {
            "limit": 25,
            "operation": "backup",
            "state": "succeeded",
        }
        assert request.to_wire()["action"] == "run.list"
        with pytest.raises(TypeError):
            request.parameters["limit"] = 50  # type: ignore[index]

    @pytest.mark.parametrize(
        "field",
        [
            "password",
            "environment",
            "executable_path",
            "arguments",
            "uid",
            "groups",
            "authorized",
        ],
    )
    def test_unknown_or_identity_fields_are_rejected(self, field: str) -> None:
        payload = request_payload("backup.request", {"target_id": "production"})
        parameters = payload["parameters"]
        assert isinstance(parameters, dict)
        parameters[field] = "attacker-controlled"

        with pytest.raises(ValueError, match="unknown fields"):
            RequestEnvelope.from_mapping(payload)

    def test_unknown_envelope_field_is_rejected(self) -> None:
        payload = request_payload()
        payload["repository_password"] = "secret"

        with pytest.raises(ValueError, match="unknown fields"):
            RequestEnvelope.from_mapping(payload)

    @pytest.mark.parametrize(
        "target_id",
        [
            "/root",
            r"C:\Users\Administrator",
            "s3://bucket/private",
            "../etc",
        ],
    )
    def test_backup_request_rejects_paths_and_uris(self, target_id: str) -> None:
        with pytest.raises(ValueError):
            RequestEnvelope.from_mapping(
                request_payload("backup.request", {"target_id": target_id})
            )

    def test_retention_request_requires_exact_policy_fingerprint(self) -> None:
        request = RequestEnvelope.from_mapping(
            request_payload(
                "retention.request",
                {"policy_fingerprint": "a" * 64, "dry_run": True},
            )
        )

        assert request.parameters["dry_run"] is True
        with pytest.raises(ValueError):
            RequestEnvelope.from_mapping(
                request_payload(
                    "retention.request",
                    {"policy_fingerprint": "A" * 64},
                )
            )

    @pytest.mark.parametrize("version", [0, 3, True, "2"])
    def test_unsupported_or_mistyped_protocol_version_is_rejected(
        self,
        version: object,
    ) -> None:
        payload = request_payload()
        payload["protocol_version"] = version

        with pytest.raises((TypeError, ValueError)):
            RequestEnvelope.from_mapping(payload)

    def test_query_limit_is_bounded_and_bool_is_not_an_integer(self) -> None:
        for limit in (0, 1_001, True):
            with pytest.raises((TypeError, ValueError)):
                RequestEnvelope.from_mapping(
                    request_payload("run.list", {"limit": limit})
                )


@pytest.mark.unit
@pytest.mark.security
class TestResponseProjection:
    """Ensure backend-only and secret-bearing fields never reach clients."""

    def test_run_projection_copies_only_allowlisted_fields(self) -> None:
        projected = project_response(
            SystemAction.RUN_LIST,
            {
                "runs": [
                    run_payload(
                        safe_summary="password=secret /protected/path",
                        repository_uri="s3://private/repository",
                        environment={"AWS_SECRET_ACCESS_KEY": "secret"},
                        source_paths=["/root"],
                        raw_output="sensitive output",
                        peer_uid=1000,
                    )
                ],
                "audit": {"account": "another-user"},
            },
        )

        run = projected["runs"][0]
        assert run["safe_summary"] == "Backup completed successfully."
        assert run["target_id"] == "production"
        assert "repository_uri" not in run
        assert "environment" not in run
        assert "source_paths" not in run
        assert "raw_output" not in run
        assert "peer_uid" not in run

    def test_diagnostic_projection_drops_raw_exception_and_audit_identity(self) -> None:
        projected = project_response(
            SystemAction.DIAGNOSTIC_LIST,
            {
                "diagnostics": [
                    diagnostic_payload(
                        safe_summary="password=secret /protected/path",
                        raw_exception="password=secret",
                        peer_uid=1000,
                        account_name="operator",
                    )
                ]
            },
        )

        diagnostic = projected["diagnostics"][0]
        assert diagnostic["safe_summary"] == "Operation failed."
        assert "raw_exception" not in diagnostic
        assert "peer_uid" not in diagnostic
        assert "account_name" not in diagnostic

    def test_response_count_is_bounded(self) -> None:
        with pytest.raises(ValueError, match="bound"):
            project_response(
                SystemAction.RUN_LIST,
                {"runs": [{} for _ in range(1_001)]},
            )

    def test_status_snapshot_projection_drops_non_allowlisted_fields(self) -> None:
        snapshot = StatusSnapshot.from_run_history(
            revision=StatusRevision(uuid4(), 0),
            backend_status=BackendStatus.AVAILABLE,
            active_operations=0,
            runs=(),
        ).to_wire()
        snapshot["repository_password"] = "secret"
        snapshot["environment"] = {"AWS_SECRET_ACCESS_KEY": "secret"}

        projected = project_response(SystemAction.STATUS_SNAPSHOT, snapshot)

        assert set(projected) == {
            "revision",
            "backend_status",
            "backup_schedule_health",
            "active_operations",
            "latest_backup",
            "last_successful_backup_completed_at",
            "latest_retention",
            "next_backup_at",
            "next_retention_at",
        }
        assert "repository_password" not in projected
        assert "environment" not in projected

    def test_detail_health_schedule_ui_and_receipt_are_strictly_projected(self) -> None:
        detail = project_response(
            SystemAction.RUN_DETAIL,
            {"run": run_payload(repository_password="secret")},
        )
        health = project_response(
            SystemAction.HEALTH,
            {
                "backend_available": True,
                "protocol_min": 1,
                "protocol_max": 1,
                "internal_path": "/var/lib/timelocker",
            },
        )
        schedule = project_response(
            SystemAction.SCHEDULE_SUMMARY,
            {
                "next_backup_at": "2026-07-27T03:30:00+00:00",
                "next_retention_at": None,
            },
        )
        ui = project_response(SystemAction.UI_AVAILABILITY, {"available": False})
        receipt = project_response(
            SystemAction.BACKUP_REQUEST,
            {
                "request_id": str(uuid4()),
                "accepted": True,
                "status": "accepted",
                "run_id": str(uuid4()),
                "raw_arguments": ["--password-file", "/secret"],
            },
        )

        assert detail["run"]["safe_summary"] == "Backup completed successfully."
        assert "repository_password" not in detail["run"]
        assert health == {
            "backend_available": True,
            "protocol_min": 1,
            "protocol_max": 1,
        }
        assert schedule["next_retention_at"] is None
        assert ui == {"available": False}
        assert "raw_arguments" not in receipt

    @pytest.mark.parametrize(
        ("action", "payload"),
        [
            (
                SystemAction.HEALTH,
                {"backend_available": "yes", "protocol_min": 1, "protocol_max": 1},
            ),
            (
                SystemAction.SCHEDULE_SUMMARY,
                {"next_backup_at": "/secret", "next_retention_at": None},
            ),
            (SystemAction.UI_AVAILABILITY, {"available": 1}),
            (
                SystemAction.BACKUP_REQUEST,
                {"request_id": str(uuid4()), "accepted": True, "status": "accepted"},
            ),
        ],
    )
    def test_invalid_projected_response_shapes_are_rejected(
        self,
        action: SystemAction,
        payload: dict[str, object],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            project_response(action, payload)


@pytest.mark.unit
@pytest.mark.security
class TestResponseEnvelope:
    """Validate success projection and metadata-free error envelopes."""

    def test_success_response_is_projected_and_recursively_frozen(self) -> None:
        request_id = uuid4()
        response = ResponseEnvelope.success(
            request_id,
            SystemAction.RUN_LIST,
            {
                "runs": [
                    run_payload(
                        safe_summary="raw untrusted text",
                        environment={"PASSWORD": "secret"},
                    )
                ]
            },
        )

        wire = response.to_wire()

        assert wire["request_id"] == str(request_id)
        assert wire["result"]["runs"][0]["safe_summary"] == (
            "Backup completed successfully."
        )
        assert "environment" not in wire["result"]["runs"][0]
        with pytest.raises(TypeError):
            response.result["runs"] = ()  # type: ignore[index,union-attr]

    def test_error_response_summary_is_owned_by_error_code(self) -> None:
        response = ResponseEnvelope.error(
            uuid4(),
            ResponseStatus.DENIED,
            ProtocolErrorCode.SYSTEM_ACCESS_DENIED,
        )

        assert response.safe_summary == "System access denied."
        assert response.result is None

    def test_untrusted_error_summary_is_rejected(self) -> None:
        payload = {
            "protocol_version": 2,
            "request_id": str(uuid4()),
            "status": "denied",
            "result": None,
            "error_code": "system_access_denied",
            "safe_summary": "Repository production exists at /protected/path",
        }

        with pytest.raises(ValueError, match="stable error code"):
            ResponseEnvelope.from_mapping(payload, action=SystemAction.RUN_LIST)

    def test_success_response_rejects_error_fields(self) -> None:
        with pytest.raises(ValueError):
            ResponseEnvelope(
                request_id=uuid4(),
                status=ResponseStatus.OK,
                result={},
                error_code=ProtocolErrorCode.OPERATION_FAILED,
                safe_summary="System operation failed.",
            )

    def test_success_response_round_trip_reprojects_untrusted_result(self) -> None:
        request_id = uuid4()
        payload = {
            "protocol_version": 2,
            "request_id": str(request_id),
            "status": "ok",
            "result": {"runs": [run_payload(environment={"PASSWORD": "secret"})]},
            "error_code": None,
            "safe_summary": None,
        }

        response = ResponseEnvelope.from_mapping(
            payload,
            action=SystemAction.RUN_LIST,
        )

        assert response.to_wire()["request_id"] == str(request_id)
        assert "environment" not in response.to_wire()["result"]["runs"][0]

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"status": ResponseStatus.OK, "result": None},
            {
                "status": ResponseStatus.DENIED,
                "result": {},
                "error_code": ProtocolErrorCode.SYSTEM_ACCESS_DENIED,
                "safe_summary": "System access denied.",
            },
            {"status": ResponseStatus.DENIED, "result": None},
            {"status": ResponseStatus.OK, "result": {}, "protocol_version": 3},
        ],
    )
    def test_response_envelope_rejects_inconsistent_shapes(
        self,
        kwargs: dict[str, object],
    ) -> None:
        with pytest.raises((TypeError, ValueError)):
            ResponseEnvelope(request_id=uuid4(), **kwargs)  # type: ignore[arg-type]

    def test_error_builder_rejects_ok_status(self) -> None:
        with pytest.raises(ValueError):
            ResponseEnvelope.error(
                uuid4(),
                ResponseStatus.OK,
                ProtocolErrorCode.OPERATION_FAILED,
            )
