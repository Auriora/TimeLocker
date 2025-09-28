import pytest

from src.TimeLocker.utils.snapshot_validation import validate_snapshot_id_format


@pytest.mark.parametrize("value", [
    "12345678",
    "abcdef12",
    "ABCDEF12",
    "a" * 64,
])
def test_validate_accepts_valid_snapshot_ids(value):
    # Should not raise
    validate_snapshot_id_format(value)


@pytest.mark.parametrize("value", [
    "",  # empty
    "1234567",  # too short
    "g1234567",  # non-hex
    "bad$$id",  # invalid chars
])
def test_validate_rejects_invalid_snapshot_ids(value):
    with pytest.raises(ValueError) as exc:
        validate_snapshot_id_format(value)
    msg = str(exc.value).lower()
    assert ("hexadecimal" in msg) or ("empty" in msg)


def test_allow_latest_flag():
    # Without flag, 'latest' is invalid
    with pytest.raises(ValueError):
        validate_snapshot_id_format("latest")

    # With flag, allowed
    validate_snapshot_id_format("latest", allow_latest=True)

