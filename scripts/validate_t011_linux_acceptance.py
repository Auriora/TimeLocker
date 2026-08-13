#!/usr/bin/env python3
"""Validate redacted live evidence for Spec 010 T011.

The evidence collector records monotonic boundaries at the point where a
status mutation completes, where systemd reports the replacement backend
started, and where the tray presentation callback applies the new snapshot.
This validator deliberately does not count graceful backend shutdown time
against the ordinary two-second status-change budget.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any
from uuid import UUID


SCHEMA_VERSION = 1
STATUS_CHANGE_BUDGET_SECONDS = 2.0
MINIMUM_IDLE_OBSERVATION_SECONDS = 90.0


class AcceptanceEvidenceError(ValueError):
    """Raised when live evidence is missing, malformed, or does not pass."""


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise AcceptanceEvidenceError(f"{field} must be an object")
    return value


def _boolean(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise AcceptanceEvidenceError(f"{field} must be a boolean")
    return value


def _number(value: object, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value < 0
    ):
        raise AcceptanceEvidenceError(f"{field} must be a non-negative number")
    return float(value)


def _uuid(value: object, field: str) -> UUID:
    if not isinstance(value, str):
        raise AcceptanceEvidenceError(f"{field} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as error:
        raise AcceptanceEvidenceError(f"{field} must be a UUID string") from error


def _require_true(section: Mapping[str, Any], field: str) -> None:
    if not _boolean(section.get(field), field):
        raise AcceptanceEvidenceError(f"{field} did not pass")


def validate_evidence(payload: object) -> dict[str, float]:
    """Validate one complete, redacted T011 acceptance evidence document."""
    root = _mapping(payload, "evidence")
    if root.get("schema_version") != SCHEMA_VERSION:
        raise AcceptanceEvidenceError("unsupported schema_version")

    authorization = _mapping(root.get("authorization"), "authorization")
    _require_true(authorization, "authorized_initial_snapshot")
    if authorization.get("denied_state") != "denied":
        raise AcceptanceEvidenceError("denied_state must be 'denied'")

    change = _mapping(root.get("status_change"), "status_change")
    mutation_completed = _number(
        change.get("mutation_completed_monotonic"),
        "mutation_completed_monotonic",
    )
    tray_rendered = _number(
        change.get("tray_rendered_monotonic"),
        "tray_rendered_monotonic",
    )
    if tray_rendered < mutation_completed:
        raise AcceptanceEvidenceError("tray rendered before mutation completed")
    status_change_latency = tray_rendered - mutation_completed
    if status_change_latency > STATUS_CHANGE_BUDGET_SECONDS:
        raise AcceptanceEvidenceError(
            "status change exceeded the two-second acceptance bound"
        )

    restart = _mapping(root.get("backend_restart"), "backend_restart")
    restart_requested = _number(
        restart.get("restart_requested_monotonic"),
        "restart_requested_monotonic",
    )
    service_started = _number(
        restart.get("service_started_monotonic"),
        "service_started_monotonic",
    )
    restart_rendered = _number(
        restart.get("tray_rendered_monotonic"),
        "backend_restart.tray_rendered_monotonic",
    )
    if not restart_requested <= service_started <= restart_rendered:
        raise AcceptanceEvidenceError("backend restart boundaries are out of order")
    previous_session = _uuid(
        restart.get("previous_session_id"),
        "previous_session_id",
    )
    current_session = _uuid(
        restart.get("current_session_id"),
        "current_session_id",
    )
    if previous_session == current_session:
        raise AcceptanceEvidenceError("backend restart reused the prior session")
    _require_true(restart, "fresh_snapshot_rendered")

    idle = _mapping(root.get("idle_output"), "idle_output")
    if (
        _number(idle.get("observation_seconds"), "observation_seconds")
        < MINIMUM_IDLE_OBSERVATION_SECONDS
    ):
        raise AcceptanceEvidenceError("idle observation was shorter than 90 seconds")
    if _number(idle.get("stdout_bytes"), "stdout_bytes") != 0:
        raise AcceptanceEvidenceError("idle tray wrote to stdout")
    if _number(idle.get("stderr_bytes"), "stderr_bytes") != 0:
        raise AcceptanceEvidenceError("idle tray wrote to stderr")

    last_success = _mapping(root.get("last_success"), "last_success")
    _require_true(last_success, "matches_latest_successful_backup")
    _require_true(last_success, "failed_attempt_did_not_replace_success")

    tray_restart = _mapping(root.get("tray_restart"), "tray_restart")
    _require_true(tray_restart, "fresh_snapshot_rendered")

    independence = _mapping(root.get("action_independence"), "action_independence")
    _require_true(independence, "control_available_without_event_socket")
    _require_true(independence, "backup_timer_healthy")
    _require_true(independence, "retention_timer_healthy")

    rollback = _mapping(root.get("rollback"), "rollback")
    _require_true(rollback, "prior_release_reselected")
    _require_true(rollback, "control_available")
    _require_true(rollback, "backup_timer_healthy")
    _require_true(rollback, "retention_timer_healthy")

    return {
        "status_change_latency_seconds": status_change_latency,
        "backend_restart_shutdown_seconds": service_started - restart_requested,
        "backend_restart_convergence_seconds": restart_rendered - service_started,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate redacted Spec 010 T011 Linux acceptance evidence."
    )
    parser.add_argument("evidence", type=Path)
    arguments = parser.parse_args(argv)
    try:
        payload = json.loads(arguments.evidence.read_text(encoding="utf-8"))
        metrics = validate_evidence(payload)
    except (AcceptanceEvidenceError, OSError, json.JSONDecodeError) as error:
        print(f"T011 acceptance failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "pass", "metrics": metrics}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
