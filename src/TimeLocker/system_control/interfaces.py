"""Platform and client interfaces for the TimeLocker system-control boundary."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from .models import (
    ActionReceipt,
    BackupActionRequest,
    DiagnosticQuery,
    DiagnosticView,
    ScheduleSummary,
    RetentionActionRequest,
    RunQuery,
    RunRecordView,
)
from .validation import require_int, require_safe_identifier


@dataclass(frozen=True, slots=True)
class PeerIdentity:
    """Identity derived from the operating-system transport."""

    platform_id: str
    process_id: int | None = None

    def __post_init__(self) -> None:
        """Reject payload-like or unbounded identity values."""
        object.__setattr__(
            self,
            "platform_id",
            require_safe_identifier(
                self.platform_id,
                field="platform_id",
                maximum=128,
            ),
        )
        if self.process_id is not None:
            object.__setattr__(
                self,
                "process_id",
                require_int(
                    self.process_id,
                    field="process_id",
                    minimum=1,
                    maximum=(2**31) - 1,
                ),
            )


class PeerIdentityProvider(Protocol):
    """Derive peer identity from a transport, never from request payload."""

    def peer_identity(self, connection: object) -> PeerIdentity:
        """Return the operating-system identity for a connected peer."""


class GroupMembershipResolver(Protocol):
    """Resolve current platform group membership for each protected request."""

    def is_current_member(self, identity: PeerIdentity, group_name: str) -> bool:
        """Return whether the peer is currently a member of the named group."""


class ControlRequestHandler(Protocol):
    """Handle one transport-decoded system-control request."""

    def handle(self, request: bytes, identity: PeerIdentity) -> bytes:
        """Return one bounded encoded response."""


class LocalControlTransport(Protocol):
    """Platform adapter for a local-only authenticated transport."""

    def serve(self, handler: ControlRequestHandler) -> None:
        """Serve requests until the transport is stopped."""


class SystemControlClient(Protocol):
    """Client contract shared by the CLI, tray, and platform adapters."""

    def list_runs(self, query: RunQuery) -> list[RunRecordView]:
        """Return authorized system run summaries."""

    def get_run(self, run_id: UUID) -> RunRecordView:
        """Return one authorized system run."""

    def list_diagnostics(self, query: DiagnosticQuery) -> list[DiagnosticView]:
        """Return authorized structured system diagnostics."""

    def request_backup(self, request: BackupActionRequest) -> ActionReceipt:
        """Request the configured system backup."""

    def request_retention(self, request: RetentionActionRequest) -> ActionReceipt:
        """Request an approved retention operation."""

    def get_schedule_summary(self) -> ScheduleSummary:
        """Return next scheduled backup and retention run timestamps."""
