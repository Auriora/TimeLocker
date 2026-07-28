"""Behavior tests for strict system-control value models."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from TimeLocker.system_control import (
    ActionReceipt,
    DiagnosticCode,
    DiagnosticComponent,
    DiagnosticLevel,
    DiagnosticRecord,
    DiagnosticView,
    OperationTrigger,
    OperationType,
    ResultCode,
    RetentionPolicy,
    RunRecord,
    RunRecordView,
    RunState,
    RunTransition,
    SystemPolicy,
)


NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)


@pytest.mark.unit
class TestRunRecord:
    """Validate state transitions and secret-free run projections."""

    def test_valid_backup_success_projects_only_contract_fields(self) -> None:
        record = RunRecord(
            run_id=uuid4(),
            operation=OperationType.BACKUP,
            trigger=OperationTrigger.SCHEDULED,
            target_id="npbackup-production",
            started_at=NOW,
            completed_at=NOW + timedelta(minutes=10),
            state=RunState.SUCCEEDED,
            result_code=ResultCode.BACKUP_SUCCEEDED,
            counters={"files_processed": 42, "bytes_added": 1_024},
        )

        view = RunRecordView.from_record(record)
        wire = view.to_wire()

        assert wire["safe_summary"] == "Backup completed successfully."
        assert wire["target_id"] == "npbackup-production"
        assert wire["counters"] == {"files_processed": 42, "bytes_added": 1_024}
        assert "environment" not in wire
        assert "repository_uri" not in wire
        assert "source_paths" not in wire

    @pytest.mark.parametrize(
        ("state", "result_code", "completed_at"),
        [
            (RunState.RUNNING, ResultCode.OPERATION_FAILED, None),
            (RunState.FAILED, ResultCode.OPERATION_FAILED, None),
            (RunState.SUCCEEDED, ResultCode.RETENTION_SUCCEEDED, NOW),
        ],
    )
    def test_inconsistent_state_is_rejected(
        self,
        state: RunState,
        result_code: ResultCode,
        completed_at: datetime | None,
    ) -> None:
        with pytest.raises(ValueError):
            RunRecord(
                run_id=uuid4(),
                operation=OperationType.BACKUP,
                trigger=OperationTrigger.SCHEDULED,
                target_id="production",
                started_at=NOW,
                completed_at=completed_at,
                state=state,
                result_code=result_code,
            )

    @pytest.mark.parametrize(
        "target_id",
        [
            "/etc/timelocker",
            "s3://private-bucket/repository",
            "../root",
            "contains spaces",
        ],
    )
    def test_target_id_cannot_encode_paths_or_repository_uris(
        self, target_id: str
    ) -> None:
        with pytest.raises(ValueError):
            RunRecord(
                run_id=uuid4(),
                operation=OperationType.BACKUP,
                trigger=OperationTrigger.SCHEDULED,
                target_id=target_id,
                started_at=NOW,
                state=RunState.RUNNING,
                result_code=ResultCode.OPERATION_RUNNING,
            )

    def test_counters_are_bounded_and_immutable(self) -> None:
        counters = {"files_processed": 1}
        record = RunRecord(
            run_id=uuid4(),
            operation=OperationType.BACKUP,
            trigger=OperationTrigger.SCHEDULED,
            target_id="production",
            started_at=NOW,
            state=RunState.RUNNING,
            result_code=ResultCode.OPERATION_RUNNING,
            counters=counters,
        )
        counters["files_processed"] = 99

        assert record.counters["files_processed"] == 1
        with pytest.raises(TypeError):
            record.counters["files_processed"] = 2  # type: ignore[index]

    def test_records_are_frozen(self) -> None:
        record = RunRecord(
            run_id=uuid4(),
            operation=OperationType.RETENTION,
            trigger=OperationTrigger.EXPLICIT,
            target_id="production",
            started_at=NOW,
            state=RunState.RUNNING,
            result_code=ResultCode.OPERATION_RUNNING,
            policy_fingerprint="a" * 64,
        )

        with pytest.raises(FrozenInstanceError):
            record.state = RunState.FAILED  # type: ignore[misc]


@pytest.mark.unit
class TestRunTransition:
    """Validate storage-independent state-transition commands."""

    def test_running_to_terminal_transition_is_valid(self) -> None:
        transition = RunTransition(
            expected_states=frozenset({RunState.RUNNING}),
            new_state=RunState.SUCCEEDED,
            result_code=ResultCode.BACKUP_SUCCEEDED,
            completed_at=NOW,
            counters={"files_processed": 10},
        )

        assert transition.new_state is RunState.SUCCEEDED
        assert transition.counters["files_processed"] == 10

    @pytest.mark.parametrize(
        "transition",
        [
            {
                "expected_states": frozenset({RunState.SUCCEEDED}),
                "new_state": RunState.FAILED,
                "result_code": ResultCode.OPERATION_FAILED,
                "completed_at": NOW,
            },
            {
                "expected_states": frozenset({RunState.RUNNING}),
                "new_state": RunState.RUNNING,
                "result_code": ResultCode.OPERATION_RUNNING,
            },
            {
                "expected_states": frozenset({RunState.RUNNING}),
                "new_state": RunState.FAILED,
                "result_code": ResultCode.OPERATION_FAILED,
            },
            {
                "expected_states": frozenset({RunState.QUEUED}),
                "new_state": RunState.RUNNING,
                "result_code": ResultCode.OPERATION_FAILED,
            },
        ],
    )
    def test_invalid_transition_is_rejected(
        self,
        transition: dict[str, object],
    ) -> None:
        with pytest.raises(ValueError):
            RunTransition(**transition)  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.security
class TestDiagnosticRecord:
    """Prove diagnostic summaries cannot contain caller-controlled text."""

    def test_safe_summary_is_derived_from_code(self) -> None:
        record = DiagnosticRecord(
            record_id=uuid4(),
            run_id=uuid4(),
            timestamp=NOW,
            level=DiagnosticLevel.ERROR,
            component=DiagnosticComponent.BACKUP,
            message_code=DiagnosticCode.OPERATION_FAILED,
        )

        view = DiagnosticView.from_record(record).to_wire()

        assert view["safe_summary"] == "Operation failed."
        assert set(view) == {
            "record_id",
            "run_id",
            "timestamp",
            "level",
            "component",
            "message_code",
            "safe_summary",
        }

    def test_raw_summary_is_not_an_input_field(self) -> None:
        with pytest.raises(TypeError):
            DiagnosticRecord(
                record_id=uuid4(),
                timestamp=NOW,
                level=DiagnosticLevel.ERROR,
                component=DiagnosticComponent.BACKUP,
                message_code=DiagnosticCode.OPERATION_FAILED,
                safe_summary="password=secret /protected/path",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestPolicyModels:
    """Validate policy bounds and explicit retention defaults."""

    def test_production_retention_defaults_are_explicit_and_non_pruning(self) -> None:
        policy = SystemPolicy()

        assert policy.operator_group == "timelocker-operators"
        assert policy.retention.keep_daily == 5
        assert policy.retention.keep_weekly == 4
        assert policy.retention.keep_monthly == 12
        assert policy.retention.keep_yearly == 3
        assert policy.retention.group_by == ("host", "paths")
        assert policy.retention.prune is False
        assert policy.retention.mutation_approved is False

    def test_policy_fingerprint_must_be_lowercase_sha256(self) -> None:
        with pytest.raises(ValueError):
            RetentionPolicy(approved_fingerprint="not-a-fingerprint")

    def test_unknown_grouping_field_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            RetentionPolicy(group_by=("host", "paths", "tags"))

    def test_system_policy_rejects_unsupported_protocol_version(self) -> None:
        with pytest.raises(ValueError, match="unsupported"):
            SystemPolicy(protocol_version=3)

    def test_system_policy_accepts_legacy_protocol_declaration_for_upgrade(
        self,
    ) -> None:
        assert SystemPolicy(protocol_version=1).protocol_version == 1


@pytest.mark.unit
class TestActionReceipt:
    """Validate action acknowledgement consistency."""

    def test_accepted_receipt_requires_run_id(self) -> None:
        with pytest.raises(ValueError):
            ActionReceipt(
                request_id=uuid4(),
                accepted=True,
                status="accepted",
            )

    def test_denied_receipt_cannot_disclose_run_id(self) -> None:
        with pytest.raises(ValueError):
            ActionReceipt(
                request_id=uuid4(),
                accepted=False,
                status="denied",
                run_id=uuid4(),
            )
