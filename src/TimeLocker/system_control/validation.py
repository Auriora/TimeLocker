"""Strict validation helpers for the local system-control contract."""

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, TypeVar
from uuid import UUID


MAX_SAFE_IDENTIFIER_LENGTH = 128
MAX_COUNTERS = 8
MAX_COUNTER_VALUE = (2**63) - 1

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_GROUP_NAME = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
_COUNTER_NAME = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_FINGERPRINT = re.compile(r"^[a-f0-9]{64}$")

_EnumType = TypeVar("_EnumType", bound=Enum)


def require_exact_mapping(
    value: object,
    *,
    field: str,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
) -> Mapping[str, Any]:
    """Return a mapping only when it contains exactly the allowed string keys."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise TypeError(f"{field} keys must be strings")
    keys = frozenset(value)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise ValueError(f"{field} is missing required fields: {sorted(missing)}")
    if unknown:
        raise ValueError(f"{field} contains unknown fields: {sorted(unknown)}")
    return value


def require_int(
    value: object,
    *,
    field: str,
    minimum: int,
    maximum: int,
) -> int:
    """Validate a bounded integer while rejecting booleans."""
    if type(value) is not int:
        raise TypeError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return value


def require_bool(value: object, *, field: str) -> bool:
    """Validate a strict boolean."""
    if type(value) is not bool:
        raise TypeError(f"{field} must be a boolean")
    return value


def require_enum(
    value: object,
    enum_type: type[_EnumType],
    *,
    field: str,
) -> _EnumType:
    """Validate an enum instance or its exact string value."""
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise ValueError(f"{field} has an unsupported value") from error


def require_uuid(value: object, *, field: str) -> UUID:
    """Validate a UUID instance or canonical UUID string."""
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a UUID")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise ValueError(f"{field} must be a valid UUID") from error
    if str(parsed) != value:
        raise ValueError(f"{field} must use canonical UUID form")
    return parsed


def require_optional_uuid(value: object, *, field: str) -> UUID | None:
    """Validate an optional UUID."""
    if value is None:
        return None
    return require_uuid(value, field=field)


def require_safe_identifier(
    value: object,
    *,
    field: str,
    maximum: int = MAX_SAFE_IDENTIFIER_LENGTH,
) -> str:
    """Validate an opaque identifier that cannot encode a path or URI."""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not 1 <= len(value) <= maximum or not _SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a bounded opaque identifier")
    if "://" in value or value.startswith(("/", "\\", ".")):
        raise ValueError(f"{field} must not be a path or URI")
    return value


def require_group_name(value: object, *, field: str = "operator_group") -> str:
    """Validate a portable, bounded Unix-style group policy name."""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not _GROUP_NAME.fullmatch(value):
        raise ValueError(f"{field} must be a valid bounded group name")
    return value


def require_fingerprint(value: object, *, field: str) -> str:
    """Validate a lowercase SHA-256 policy fingerprint."""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not _FINGERPRINT.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def require_utc_datetime(value: object, *, field: str) -> datetime:
    """Validate an aware UTC timestamp."""
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field} must be timezone-aware UTC")
    return value


def require_optional_utc_datetime(value: object, *, field: str) -> datetime | None:
    """Validate an optional UTC timestamp."""
    if value is None:
        return None
    return require_utc_datetime(value, field=field)


def require_wire_utc_datetime(value: object, *, field: str) -> datetime:
    """Parse a wire-format ISO timestamp and require a UTC offset."""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be an ISO timestamp string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be a valid ISO timestamp") from error
    return require_utc_datetime(parsed, field=field)


def require_optional_wire_utc_datetime(
    value: object,
    *,
    field: str,
) -> datetime | None:
    """Parse an optional wire-format UTC timestamp."""
    if value is None:
        return None
    return require_wire_utc_datetime(value, field=field)


def freeze_counters(value: object) -> Mapping[str, int]:
    """Return a read-only, bounded map of non-negative numeric counters."""
    if not isinstance(value, Mapping):
        raise TypeError("counters must be a mapping")
    if len(value) > MAX_COUNTERS:
        raise ValueError(f"counters must contain at most {MAX_COUNTERS} entries")
    counters: dict[str, int] = {}
    for key, counter in value.items():
        if not isinstance(key, str) or not _COUNTER_NAME.fullmatch(key):
            raise ValueError("counter names must use bounded snake_case")
        counters[key] = require_int(
            counter,
            field=f"counters.{key}",
            minimum=0,
            maximum=MAX_COUNTER_VALUE,
        )
    return MappingProxyType(counters)


def freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Copy a mapping into a read-only wrapper."""
    return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})


def deep_freeze(value: Any) -> Any:
    """Recursively copy protocol containers into immutable equivalents."""
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("protocol mapping keys must be strings")
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(deep_freeze(item) for item in value)
    return value


def deep_thaw(value: Any) -> Any:
    """Return JSON-compatible mutable containers from a frozen protocol value."""
    if isinstance(value, Mapping):
        return {key: deep_thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [deep_thaw(item) for item in value]
    return value
