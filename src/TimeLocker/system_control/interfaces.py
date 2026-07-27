"""Platform and client interfaces for the TimeLocker system-control boundary."""

from collections.abc import Iterator
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
    StatusEvent,
    StatusRevision,
    StatusSnapshot,
)
from .types import StatusEventKind
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


class StatusSnapshotProvider(Protocol):
    """Provide the current platform-neutral status snapshot."""

    def snapshot(self) -> StatusSnapshot:
        """Return the latest safe status snapshot."""


class StatusEventBroker(Protocol):
    """Own monotonic status revisions and publish bounded event updates."""

    def current_revision(self) -> StatusRevision:
        """Return the current backend-session revision."""

    def publish_change(self, kind: StatusEventKind) -> StatusRevision:
        """Advance and return the revision for an emitted status change."""

    def subscribe(self) -> "StatusSubscription":
        """Return one bounded status subscription."""


class StatusSubscription(Protocol):
    """Bounded event queue owned by one subscribed client."""

    def next_event(self, timeout_seconds: float | None = None) -> StatusEvent | None:
        """Return the next event, or None after timeout or closure."""

    def close(self) -> None:
        """Close and unregister this subscription."""


class StatusEventTransport(Protocol):
    """Serve authenticated event subscriptions without owning platform state."""

    def serve(
        self,
        broker: StatusEventBroker,
        identity_provider: PeerIdentityProvider,
        membership_resolver: GroupMembershipResolver,
    ) -> None:
        """Serve status events until the transport is stopped."""


class StatusEventClient(Protocol):
    """Consume status events from a platform event transport."""

    def events(self, stop_event: object) -> Iterator[StatusEvent]:
        """Yield status events until the caller signals shutdown."""


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

    def get_status_snapshot(self) -> StatusSnapshot:
        """Return one authorized safe backend status snapshot."""
