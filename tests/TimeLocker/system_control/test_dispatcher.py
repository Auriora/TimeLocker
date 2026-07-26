"""Authorization, malformed-request, and redaction tests for local dispatch."""

from collections.abc import Sequence
import json
from uuid import uuid4

import pytest

from TimeLocker.system_control import (
    AuditEvent,
    LocalControlDispatcher,
    PeerIdentity,
    SystemAction,
    SystemPolicy,
)


class MembershipSequence:
    """Return explicit current-membership results and count every lookup."""

    def __init__(self, results: Sequence[bool]) -> None:
        self.results = iter(results)
        self.calls = 0

    def is_current_member(self, identity: PeerIdentity, group_name: str) -> bool:
        self.calls += 1
        assert identity.platform_id == "linux-uid:1000"
        assert group_name == "timelocker-operators"
        return next(self.results)


class CollectingAuditSink:
    """Capture bounded audit events for assertions."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def request(
    action: str = "health",
    parameters: dict[str, object] | None = None,
    *,
    version: int = 1,
) -> bytes:
    return json.dumps(
        {
            "protocol_version": version,
            "request_id": str(uuid4()),
            "action": action,
            "parameters": parameters or {},
        }
    ).encode("utf-8")


def decode(response: bytes) -> dict[str, object]:
    value = json.loads(response)
    assert isinstance(value, dict)
    return value


def health(_request: object) -> dict[str, object]:
    return {
        "backend_available": True,
        "protocol_min": 1,
        "protocol_max": 1,
        "protected_path": "/var/lib/timelocker",
    }


@pytest.mark.unit
@pytest.mark.security
class TestLocalControlDispatcher:
    """Prove every protected request uses fresh OS-derived authorization."""

    def test_authorized_request_is_projected_and_audited(self) -> None:
        membership = MembershipSequence([True])
        audit = CollectingAuditSink()
        dispatcher = LocalControlDispatcher(
            policy=SystemPolicy(),
            membership_resolver=membership,
            handlers={SystemAction.HEALTH: health},
            audit_sink=audit,
        )

        response = decode(
            dispatcher.handle(request(), PeerIdentity("linux-uid:1000", 1234))
        )

        assert response["status"] == "ok"
        assert response["result"] == {
            "backend_available": True,
            "protocol_min": 1,
            "protocol_max": 1,
        }
        assert membership.calls == 1
        assert audit.events[0].decision == "allowed"
        assert audit.events[0].status.value == "ok"

    def test_membership_is_revalidated_and_removed_member_is_denied(self) -> None:
        membership = MembershipSequence([True, False])
        dispatcher = LocalControlDispatcher(
            policy=SystemPolicy(),
            membership_resolver=membership,
            handlers={SystemAction.HEALTH: health},
            audit_sink=CollectingAuditSink(),
        )
        identity = PeerIdentity("linux-uid:1000")

        first = decode(dispatcher.handle(request(), identity))
        second = decode(dispatcher.handle(request(), identity))

        assert first["status"] == "ok"
        assert second["status"] == "denied"
        assert second["error_code"] == "system_access_denied"
        assert second["result"] is None
        assert membership.calls == 2

    def test_denial_does_not_disclose_handler_or_protected_metadata(self) -> None:
        identity = PeerIdentity("linux-uid:1000")
        responses = []
        for handlers in ({}, {SystemAction.RUN_DETAIL: lambda _request: {}}):
            dispatcher = LocalControlDispatcher(
                policy=SystemPolicy(),
                membership_resolver=MembershipSequence([False]),
                handlers=handlers,
                audit_sink=CollectingAuditSink(),
            )
            responses.append(
                decode(
                    dispatcher.handle(
                        request(
                            "run.detail",
                            {"run_id": str(uuid4())},
                        ),
                        identity,
                    )
                )
            )

        for response in responses:
            assert response["status"] == "denied"
            assert response["result"] is None
            assert response["safe_summary"] == "System access denied."
            assert "target_id" not in response
            assert "repository" not in response

    @pytest.mark.parametrize(
        ("payload", "error_code"),
        [
            (b"{", "invalid_request"),
            (request(version=2), "contract_version_unsupported"),
            (
                request(
                    "backup.request",
                    {"target_id": "production", "uid": 0},
                ),
                "invalid_request",
            ),
        ],
    )
    def test_malformed_version_and_self_asserted_identity_fail_closed(
        self,
        payload: bytes,
        error_code: str,
    ) -> None:
        dispatcher = LocalControlDispatcher(
            policy=SystemPolicy(),
            membership_resolver=MembershipSequence([]),
            handlers={},
            audit_sink=CollectingAuditSink(),
        )

        response = decode(dispatcher.handle(payload, PeerIdentity("linux-uid:1000")))

        assert response["status"] == "invalid"
        assert response["error_code"] == error_code
        assert response["result"] is None

    def test_oversized_request_is_rejected_before_membership_or_dispatch(self) -> None:
        membership = MembershipSequence([])
        dispatcher = LocalControlDispatcher(
            policy=SystemPolicy(max_request_bytes=1_024),
            membership_resolver=membership,
            handlers={SystemAction.HEALTH: lambda _request: pytest.fail("dispatched")},
            audit_sink=CollectingAuditSink(),
        )

        response = decode(
            dispatcher.handle(b"x" * 1_025, PeerIdentity("linux-uid:1000"))
        )

        assert response["error_code"] == "invalid_request"
        assert membership.calls == 0

    def test_handler_exception_is_replaced_with_safe_stable_error(self) -> None:
        def failing_handler(_request: object) -> object:
            raise RuntimeError("password=secret /protected/path")

        dispatcher = LocalControlDispatcher(
            policy=SystemPolicy(),
            membership_resolver=MembershipSequence([True]),
            handlers={SystemAction.HEALTH: failing_handler},
            audit_sink=CollectingAuditSink(),
        )

        encoded = dispatcher.handle(request(), PeerIdentity("linux-uid:1000"))
        response = decode(encoded)

        assert response["error_code"] == "operation_failed"
        assert b"password" not in encoded
        assert b"/protected" not in encoded
