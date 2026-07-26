"""Boundary tests for strict system-control validation helpers."""

from datetime import datetime
from uuid import uuid4

import pytest

from TimeLocker.system_control.types import RunState
from TimeLocker.system_control.validation import (
    deep_freeze,
    freeze_counters,
    require_enum,
    require_exact_mapping,
    require_group_name,
    require_safe_identifier,
    require_uuid,
    require_wire_utc_datetime,
)


@pytest.mark.unit
@pytest.mark.security
class TestStrictValidation:
    """Exercise malformed values at the untrusted protocol boundary."""

    def test_exact_mapping_rejects_non_mapping_missing_and_non_string_keys(
        self,
    ) -> None:
        with pytest.raises(TypeError):
            require_exact_mapping(
                [],
                field="payload",
                required=frozenset({"id"}),
            )
        with pytest.raises(ValueError, match="missing"):
            require_exact_mapping(
                {},
                field="payload",
                required=frozenset({"id"}),
            )
        with pytest.raises(TypeError, match="keys"):
            require_exact_mapping(
                {1: "value"},
                field="payload",
                required=frozenset(),
                optional=frozenset({"id"}),
            )

    def test_enum_rejects_wrong_type_and_unknown_value(self) -> None:
        with pytest.raises(TypeError):
            require_enum(1, RunState, field="state")
        with pytest.raises(ValueError, match="unsupported"):
            require_enum("secret-state", RunState, field="state")

    def test_uuid_rejects_wrong_type_invalid_and_noncanonical_value(self) -> None:
        with pytest.raises(TypeError):
            require_uuid(123, field="id")
        with pytest.raises(ValueError, match="valid UUID"):
            require_uuid("not-a-uuid", field="id")
        uppercase = str(uuid4()).upper()
        with pytest.raises(ValueError, match="canonical"):
            require_uuid(uppercase, field="id")

    def test_safe_identifiers_and_groups_reject_wrong_types(self) -> None:
        with pytest.raises(TypeError):
            require_safe_identifier(123, field="target")
        with pytest.raises(TypeError):
            require_group_name(123)
        with pytest.raises(ValueError):
            require_group_name("Invalid Group")

    def test_wire_timestamp_requires_valid_aware_utc_iso_value(self) -> None:
        with pytest.raises(TypeError):
            require_wire_utc_datetime(datetime.now(), field="timestamp")
        with pytest.raises(ValueError, match="valid ISO"):
            require_wire_utc_datetime("not-a-timestamp", field="timestamp")
        with pytest.raises(ValueError, match="UTC"):
            require_wire_utc_datetime("2026-07-26T12:00:00", field="timestamp")

    def test_counters_and_recursive_freeze_reject_unbounded_or_invalid_maps(
        self,
    ) -> None:
        with pytest.raises(TypeError):
            freeze_counters([])
        with pytest.raises(ValueError, match="at most"):
            freeze_counters({f"count_{index}": index for index in range(9)})
        with pytest.raises(ValueError, match="snake_case"):
            freeze_counters({"Invalid Counter": 1})
        with pytest.raises(TypeError, match="keys"):
            deep_freeze({1: "value"})
