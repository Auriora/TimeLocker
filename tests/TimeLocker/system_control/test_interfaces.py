"""Portability tests for shared system-control adapter protocols."""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from TimeLocker.system_control import (
    ActionReceipt,
    BackupActionRequest,
    DiagnosticQuery,
    DiagnosticView,
    PeerIdentity,
    RetentionActionRequest,
    RunQuery,
    RunRecordView,
    StatusSnapshot,
)


@dataclass
class FakePeerIdentityProvider:
    """Platform test double that derives a configured identity."""

    identity: PeerIdentity

    def peer_identity(self, connection: object) -> PeerIdentity:
        return self.identity


@dataclass
class FakeGroupResolver:
    """Current-membership test double shared by Linux and Windows cases."""

    allowed_platform_id: str

    def is_current_member(self, identity: PeerIdentity, group_name: str) -> bool:
        return (
            group_name == "timelocker-operators"
            and identity.platform_id == self.allowed_platform_id
        )


class FakeSystemControlClient:
    """Minimal client test double proving the platform-neutral method surface."""

    def list_runs(self, query: RunQuery) -> list[RunRecordView]:
        return []

    def get_run(self, run_id: UUID) -> RunRecordView:
        raise LookupError(run_id)

    def list_diagnostics(self, query: DiagnosticQuery) -> list[DiagnosticView]:
        return []

    def request_backup(self, request: BackupActionRequest) -> ActionReceipt:
        return ActionReceipt(
            request_id=uuid4(),
            accepted=True,
            status="accepted",
            run_id=uuid4(),
        )

    def request_retention(self, request: RetentionActionRequest) -> ActionReceipt:
        return ActionReceipt(
            request_id=uuid4(),
            accepted=True,
            status="accepted",
            run_id=uuid4(),
        )

    def get_status_snapshot(self) -> StatusSnapshot:
        raise LookupError("no snapshot configured")


@pytest.mark.unit
@pytest.mark.platform
@pytest.mark.parametrize(
    "platform_id",
    ["uid:1000", "sid:S-1-5-21-1000"],
)
def test_linux_and_windows_identity_adapters_share_authorization_contract(
    platform_id: str,
) -> None:
    """Linux UID and Windows SID adapters can supply the same shared model."""
    provider = FakePeerIdentityProvider(PeerIdentity(platform_id, process_id=1234))
    resolver = FakeGroupResolver(platform_id)

    identity = provider.peer_identity(object())

    assert resolver.is_current_member(identity, "timelocker-operators") is True
    assert resolver.is_current_member(identity, "administrators") is False


@pytest.mark.unit
@pytest.mark.platform
def test_client_double_uses_only_bounded_action_models() -> None:
    client = FakeSystemControlClient()

    backup = client.request_backup(BackupActionRequest(target_id="production"))
    retention = client.request_retention(
        RetentionActionRequest(policy_fingerprint="a" * 64, dry_run=True)
    )

    assert backup.accepted is True
    assert retention.accepted is True
    assert client.list_runs(RunQuery(limit=10)) == []
    assert client.list_diagnostics(DiagnosticQuery(limit=10)) == []


@pytest.mark.unit
@pytest.mark.security
def test_peer_identity_rejects_path_or_payload_identity() -> None:
    with pytest.raises(ValueError):
        PeerIdentity("/proc/self")
