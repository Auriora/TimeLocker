"""Contract tests for the Spec 010 T011 live-evidence validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[3]


def _load_validator() -> ModuleType:
    path = ROOT / "scripts/validate_t011_linux_acceptance.py"
    spec = importlib.util.spec_from_file_location(
        "validate_t011_linux_acceptance",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evidence() -> dict[str, object]:
    return {
        "schema_version": 1,
        "authorization": {
            "authorized_initial_snapshot": True,
            "denied_state": "denied",
        },
        "status_change": {
            "mutation_completed_monotonic": 100.0,
            "tray_rendered_monotonic": 101.5,
        },
        "backend_restart": {
            "restart_requested_monotonic": 200.0,
            "service_started_monotonic": 202.5,
            "tray_rendered_monotonic": 203.4,
            "previous_session_id": "526719f9-4c46-42ac-b286-2623079bc335",
            "current_session_id": "eb53eaf9-42c5-45e2-b772-a3c6d7ace818",
            "fresh_snapshot_rendered": True,
        },
        "idle_output": {
            "observation_seconds": 90.0,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
        },
        "last_success": {
            "matches_latest_successful_backup": True,
            "failed_attempt_did_not_replace_success": True,
        },
        "tray_restart": {"fresh_snapshot_rendered": True},
        "action_independence": {
            "control_available_without_event_socket": True,
            "backup_timer_healthy": True,
            "retention_timer_healthy": True,
        },
        "rollback": {
            "prior_release_reselected": True,
            "control_available": True,
            "backup_timer_healthy": True,
            "retention_timer_healthy": True,
        },
    }


def test_validator_separates_shutdown_from_restart_convergence() -> None:
    validator = _load_validator()

    metrics = validator.validate_evidence(_evidence())

    assert metrics == {
        "status_change_latency_seconds": 1.5,
        "backend_restart_shutdown_seconds": 2.5,
        "backend_restart_convergence_seconds": pytest.approx(0.9),
    }


def test_validator_rejects_slow_status_change_not_slow_shutdown() -> None:
    validator = _load_validator()
    evidence = _evidence()
    evidence["status_change"]["tray_rendered_monotonic"] = 102.01

    with pytest.raises(
        validator.AcceptanceEvidenceError,
        match="two-second",
    ):
        validator.validate_evidence(evidence)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("authorization", "authorized_initial_snapshot"),
        ("last_success", "matches_latest_successful_backup"),
        ("tray_restart", "fresh_snapshot_rendered"),
        ("action_independence", "control_available_without_event_socket"),
        ("rollback", "prior_release_reselected"),
    ],
)
def test_validator_rejects_missing_acceptance_proof(
    section: str,
    field: str,
) -> None:
    validator = _load_validator()
    evidence = _evidence()
    del evidence[section][field]

    with pytest.raises(validator.AcceptanceEvidenceError):
        validator.validate_evidence(evidence)
