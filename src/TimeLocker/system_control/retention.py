"""Approved, locked retention execution for protected system repositories."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from .models import (
    ActionReceipt,
    DiagnosticRecord,
    RetentionPolicy,
    RunRecord,
    RunTransition,
)
from .protocol import RequestEnvelope
from .storage import AtomicRecordStore, MutationConflictError, RepositoryMutationLock
from .types import (
    DiagnosticCode,
    DiagnosticComponent,
    DiagnosticLevel,
    OperationTrigger,
    OperationType,
    ResultCode,
    RunState,
)
from .validation import require_safe_identifier


@dataclass(frozen=True, slots=True)
class RetentionPlan:
    """Complete, secret-free input whose canonical form is operator-approved."""

    target_id: str
    repository_identity: str
    credential_source: str
    snapshot_filters: tuple[str, ...] = ()
    policy: RetentionPolicy = field(default_factory=RetentionPolicy)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_id",
            require_safe_identifier(self.target_id, field="target_id"),
        )
        for field_name in ("repository_identity", "credential_source"):
            value = getattr(self, field_name)
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 512
                or "\x00" in value
            ):
                raise ValueError(f"{field_name} must be a bounded non-empty string")
        if type(self.snapshot_filters) is not tuple:
            raise TypeError("snapshot_filters must be a tuple")
        for value in self.snapshot_filters:
            if not isinstance(value, str) or len(value) > 1_024 or "\x00" in value:
                raise ValueError("snapshot_filters must contain bounded strings")
        if not isinstance(self.policy, RetentionPolicy):
            raise TypeError("policy must be a RetentionPolicy")

    @property
    def fingerprint(self) -> str:
        """Return the exact canonical policy and repository-context fingerprint."""
        payload = {
            "credential_source": self.credential_source,
            "group_by": list(self.policy.group_by),
            "keep_daily": self.policy.keep_daily,
            "keep_monthly": self.policy.keep_monthly,
            "keep_weekly": self.policy.keep_weekly,
            "keep_yearly": self.policy.keep_yearly,
            "prune": self.policy.prune,
            "repository_identity": self.repository_identity,
            "snapshot_filters": list(self.snapshot_filters),
            "target_id": self.target_id,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionExecutionResult:
    """Safe counters returned by a protected retention adapter."""

    selected_snapshots: int = 0
    removed_snapshots: int = 0

    def __post_init__(self) -> None:
        for value in (self.selected_snapshots, self.removed_snapshots):
            if type(value) is not int or value < 0 or value > 2**63 - 1:
                raise ValueError(
                    "retention counters must be bounded non-negative integers"
                )

    def counters(self, *, dry_run: bool) -> Mapping[str, int]:
        return {
            "dry_run": int(dry_run),
            "selected_snapshots": self.selected_snapshots,
            "removed_snapshots": self.removed_snapshots,
        }


class RetentionAdapter(Protocol):
    """Resolve protected configuration and execute one exact retention plan."""

    def execute(
        self,
        plan: RetentionPlan,
        *,
        dry_run: bool,
    ) -> RetentionExecutionResult:
        """Execute without exposing credentials or backend output."""


class RetentionExecutor:
    """Create a separate durable run around one repository mutation lease."""

    def __init__(
        self,
        *,
        store: AtomicRecordStore,
        locks: RepositoryMutationLock,
        adapter: RetentionAdapter,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.locks = locks
        self.adapter = adapter
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def execute(
        self,
        plan: RetentionPlan,
        *,
        trigger: OperationTrigger,
        dry_run: bool,
    ) -> RunRecord:
        """Execute an approved mutation, or an unapproved dry run, fail-closed."""
        if not isinstance(plan, RetentionPlan):
            raise TypeError("plan must be a RetentionPlan")
        if trigger not in {
            OperationTrigger.EXPLICIT,
            OperationTrigger.SCHEDULED,
            OperationTrigger.BACKUP_SUCCESS,
            OperationTrigger.RETRY,
        }:
            raise ValueError("unsupported retention trigger")
        if type(dry_run) is not bool:
            raise TypeError("dry_run must be a bool")
        fingerprint = plan.fingerprint
        if not dry_run and plan.policy.approved_fingerprint != fingerprint:
            raise PermissionError("retention policy approval does not match")

        started_at = self._now()
        run = RunRecord(
            run_id=uuid4(),
            operation=OperationType.RETENTION,
            trigger=trigger,
            target_id=plan.target_id,
            started_at=started_at,
            state=RunState.QUEUED,
            result_code=ResultCode.OPERATION_QUEUED,
            policy_fingerprint=fingerprint,
            counters={"dry_run": int(dry_run)},
        )
        self.store.create_run(run)
        try:
            lease = self.locks.acquire(plan.target_id, run.run_id)
        except MutationConflictError:
            result = self._finish(
                run,
                RunState.SKIPPED,
                ResultCode.OPERATION_CONFLICT,
                {"dry_run": int(dry_run)},
            )
            self._diagnostic(
                run.run_id, DiagnosticLevel.WARNING, DiagnosticCode.OPERATION_CONFLICT
            )
            return result

        with lease:
            self.store.transition(
                run.run_id,
                RunTransition(
                    expected_states=frozenset({RunState.QUEUED}),
                    new_state=RunState.RUNNING,
                    result_code=ResultCode.OPERATION_RUNNING,
                    counters={"dry_run": int(dry_run)},
                ),
            )
            self._diagnostic(
                run.run_id, DiagnosticLevel.INFO, DiagnosticCode.RETENTION_STARTED
            )
            try:
                adapter_result = self.adapter.execute(plan, dry_run=dry_run)
                if not isinstance(adapter_result, RetentionExecutionResult):
                    raise TypeError("retention adapter returned an invalid result")
            except Exception:
                result = self._finish(
                    run,
                    RunState.FAILED,
                    ResultCode.OPERATION_FAILED,
                    {"dry_run": int(dry_run)},
                )
                self._diagnostic(
                    run.run_id, DiagnosticLevel.ERROR, DiagnosticCode.OPERATION_FAILED
                )
                return result
            result = self._finish(
                run,
                RunState.SUCCEEDED,
                ResultCode.RETENTION_SUCCEEDED,
                adapter_result.counters(dry_run=dry_run),
            )
            self._diagnostic(
                run.run_id, DiagnosticLevel.INFO, DiagnosticCode.RETENTION_SUCCEEDED
            )
            return result

    def _finish(
        self,
        run: RunRecord,
        state: RunState,
        result_code: ResultCode,
        counters: Mapping[str, int],
    ) -> RunRecord:
        current = self.store.read_run(run.run_id)
        return self.store.transition(
            run.run_id,
            RunTransition(
                expected_states=frozenset({current.state}),
                new_state=state,
                result_code=result_code,
                completed_at=max(self._now(), run.started_at),
                counters=counters,
            ),
        )

    def _diagnostic(
        self,
        run_id: UUID,
        level: DiagnosticLevel,
        code: DiagnosticCode,
    ) -> None:
        self.store.append_diagnostic(
            DiagnosticRecord(
                record_id=uuid4(),
                run_id=run_id,
                timestamp=self._now(),
                level=level,
                component=DiagnosticComponent.RETENTION,
                message_code=code,
            )
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("clock must return an aware UTC datetime")
        return value


class RetentionTriggerStore:
    """Durably claim each successful backup trigger at most once."""

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path):
            raise TypeError("root must be a Path")
        self.root = root
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)

    def claim(self, backup_run_id: UUID, policy_fingerprint: str) -> bool:
        """Atomically claim a backup/fingerprint pair across processes."""
        name = hashlib.sha256(
            f"{backup_run_id}:{policy_fingerprint}".encode("ascii")
        ).hexdigest()
        path = self.root / f"{name}.json"
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            return False
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(
                {
                    "backup_run_id": str(backup_run_id),
                    "policy_fingerprint": policy_fingerprint,
                    "schema_version": 1,
                },
                output,
                sort_keys=True,
                separators=(",", ":"),
            )
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        directory_descriptor = os.open(
            self.root,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return True


class RetentionTriggerCoordinator:
    """Expose explicit, independent, and post-backup retention triggers."""

    def __init__(
        self,
        *,
        executor: RetentionExecutor,
        trigger_store: RetentionTriggerStore,
        independent_schedule_enabled: bool = False,
    ) -> None:
        self.executor = executor
        self.trigger_store = trigger_store
        self.independent_schedule_enabled = independent_schedule_enabled

    def explicit(self, plan: RetentionPlan, *, dry_run: bool = False) -> RunRecord:
        return self.executor.execute(
            plan,
            trigger=OperationTrigger.EXPLICIT,
            dry_run=dry_run,
        )

    def scheduled(self, plan: RetentionPlan) -> RunRecord | None:
        if not self.independent_schedule_enabled:
            return None
        return self.executor.execute(
            plan,
            trigger=OperationTrigger.SCHEDULED,
            dry_run=False,
        )

    def after_backup_success(
        self,
        backup: RunRecord,
        plan: RetentionPlan,
    ) -> RunRecord | None:
        """Trigger once after a terminal successful scheduled backup is released."""
        if (
            backup.operation is not OperationType.BACKUP
            or backup.trigger is not OperationTrigger.SCHEDULED
            or backup.state is not RunState.SUCCEEDED
            or backup.result_code is not ResultCode.BACKUP_SUCCEEDED
        ):
            return None
        if not self.trigger_store.claim(backup.run_id, plan.fingerprint):
            return None
        return self.executor.execute(
            plan,
            trigger=OperationTrigger.BACKUP_SUCCESS,
            dry_run=False,
        )


class RetentionRequestHandler:
    """Bind the protected retention domain to the allowlisted IPC dispatcher."""

    def __init__(
        self,
        *,
        coordinator: RetentionTriggerCoordinator,
        plan: RetentionPlan,
    ) -> None:
        self.coordinator = coordinator
        self.plan = plan

    def __call__(self, request: RequestEnvelope) -> Mapping[str, object]:
        supplied_fingerprint = request.parameters["policy_fingerprint"]
        dry_run = request.parameters["dry_run"]
        if supplied_fingerprint != self.plan.fingerprint:
            raise PermissionError("retention policy fingerprint does not match")
        run = self.coordinator.explicit(self.plan, dry_run=dry_run)
        return ActionReceipt(
            request_id=request.request_id,
            accepted=True,
            status=run.state.value,
            run_id=run.run_id,
        ).to_wire()
