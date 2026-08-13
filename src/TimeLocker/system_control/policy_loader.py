"""Strict loading for the root-controlled system-control policy."""

from __future__ import annotations

import json
from pathlib import Path
import stat

from .models import RetentionPolicy, SystemPolicy
from .validation import require_exact_mapping


_POLICY_FIELDS = frozenset(
    {
        "operator_group",
        "transport_identifier",
        "protocol_version",
        "max_request_bytes",
        "max_response_records",
        "retention",
    }
)
_RETENTION_FIELDS = frozenset(
    {
        "keep_daily",
        "keep_weekly",
        "keep_monthly",
        "keep_yearly",
        "group_by",
        "prune",
        "approved_fingerprint",
    }
)


def load_system_policy(path: Path, *, expected_owner: int = 0) -> SystemPolicy:
    """Load a regular, owner-controlled policy without accepting extra fields."""
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    if type(expected_owner) is not int or expected_owner < 0:
        raise ValueError("expected_owner must be a non-negative UID")
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("system policy must be a regular file")
    if metadata.st_uid != expected_owner:
        raise PermissionError("system policy has an unexpected owner")
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise PermissionError("system policy must not be group- or world-writable")
    with path.open("r", encoding="utf-8") as source:
        payload = json.load(source)
    policy = require_exact_mapping(
        payload,
        field="system policy",
        required=_POLICY_FIELDS,
    )
    retention_value = require_exact_mapping(
        policy["retention"],
        field="retention policy",
        required=_RETENTION_FIELDS,
    )
    group_by = retention_value["group_by"]
    if not isinstance(group_by, list) or not all(
        isinstance(item, str) for item in group_by
    ):
        raise TypeError("retention group_by must be a string list")
    retention = RetentionPolicy(
        keep_daily=retention_value["keep_daily"],
        keep_weekly=retention_value["keep_weekly"],
        keep_monthly=retention_value["keep_monthly"],
        keep_yearly=retention_value["keep_yearly"],
        group_by=tuple(group_by),
        prune=retention_value["prune"],
        approved_fingerprint=retention_value["approved_fingerprint"],
    )
    return SystemPolicy(
        operator_group=policy["operator_group"],
        transport_identifier=policy["transport_identifier"],
        protocol_version=policy["protocol_version"],
        max_request_bytes=policy["max_request_bytes"],
        max_response_records=policy["max_response_records"],
        retention=retention,
    )
