"""
Snapshot ID validation utilities for TimeLocker CLI.

Rules (aligned with restic snapshot IDs):
- Hexadecimal ID (case-insensitive), length between 8 and 64 characters (inclusive)
- No whitespace; no punctuation other than hex
- Optionally allow special keyword "latest" when CLI semantics permit
"""

import re
from typing import Optional

_HEX_RE = re.compile(r"^[0-9a-fA-F]{8,64}$")


def validate_snapshot_id_format(value: Optional[str], allow_latest: bool = False) -> None:
    """
    Validate snapshot identifier format.

    Args:
        value: The snapshot identifier string.
        allow_latest: If True, the special value "latest" is accepted.

    Raises:
        ValueError: If the value is not a valid snapshot identifier.
    """
    if value is None:
        # Keep a consistent error message to satisfy CLI tests
        raise ValueError(
                "Invalid snapshot ID format. Expected 8–64 hexadecimal characters (e.g., 1a2b3c4d...)."
        )

    v = value.strip()
    if not v:
        raise ValueError(
                "Invalid snapshot ID format. Expected 8–64 hexadecimal characters (e.g., 1a2b3c4d...)."
        )

    if allow_latest and v.lower() == "latest":
        return

    if not _HEX_RE.match(v):
        raise ValueError(
                "Invalid snapshot ID format. Expected 8–64 hexadecimal characters (e.g., 1a2b3c4d...)."
        )

    # OK
    return
