import os
import pytest

from TimeLocker.utils.repository_resolver import validate_repository_name_or_uri


@pytest.mark.parametrize("value", [
    "file:///tmp/repo",
    "file:///var/backups",
    "s3://bucket/path",
    "s3:region/bucket",
    "b2:mybucket",
    "rclone:remote:bucket",
    "swift:container",
    "rest:server/repo",
    "myrepo",
    "prod_backup",
])
@pytest.mark.config
@pytest.mark.unit
def test_validate_accepts_valid_names_and_uris(value):
    # Should not raise
    validate_repository_name_or_uri(value)


@pytest.mark.parametrize("value", [
    "/tmp/repo",
    "repo/subdir",
    "./local/repo",
    "..\\relative\\repo",
    "C:/repo",
    r"C:\\repo",
])
@pytest.mark.config
@pytest.mark.unit
def test_validate_rejects_local_paths_without_file_scheme(value):
    with pytest.raises(ValueError) as exc:
        validate_repository_name_or_uri(value)
    assert "file://" in str(exc.value)

