"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.restic.Repositories.s3 import S3ResticRepository
from TimeLocker.restic.restic_repository import RepositoryError
from .minio_test_utils import ensure_minio_reachable, load_minio_settings

pytestmark = pytest.mark.integration

SYNTHETIC_ENDPOINT_URL = "https://minio.invalid:9000"
SYNTHETIC_ACCESS_KEY = "test-access"
SYNTHETIC_SECRET_KEY = "test-secret"
SYNTHETIC_BUCKET = "timelocker-test"
SYNTHETIC_REGION = "us-east-1"


def _verify_ssl(settings: dict[str, str]) -> bool:
    value = str(settings.get("MINIO_VERIFY_SSL", "true")).lower()
    return value not in {"0", "false", "no"}


@pytest.fixture(scope="session")
def minio_settings() -> dict[str, str]:
    """Load and validate live MinIO settings when a live test starts."""
    settings, missing = load_minio_settings(require_credentials=True)
    if missing:
        pytest.fail(
            "MinIO profile dependency error: missing configuration for "
            + ", ".join(missing)
            + ". Set environment variables or provide a test configuration."
        )
    return settings


@pytest.fixture(scope="session")
def minio_available(minio_settings: dict[str, str]) -> bool:
    """
    Check if MinIO is available for testing.

    This is a session-scoped fixture to avoid repeated connection attempts.
    Returns True if MinIO is available; otherwise fails with a dependency error.
    """
    try:
        ensure_minio_reachable(
            minio_settings["MINIO_ENDPOINT_URL"],
            minio_settings["MINIO_ACCESS_KEY"],
            minio_settings["MINIO_SECRET_KEY"],
            minio_settings["MINIO_REGION"],
            _verify_ssl(minio_settings),
        )
        return True
    except Exception as e:
        pytest.fail(f"MinIO profile dependency error: service is unavailable: {e}")


@pytest.fixture
def test_repo_path(
    minio_settings: dict[str, str],
    minio_available: bool,
) -> Generator[str, None, None]:
    """Create a unique test repository path in MinIO bucket."""
    import uuid

    test_id = str(uuid.uuid4())[:8]
    repo_path = f"test-repo-{test_id}"
    yield repo_path

    # Cleanup: Remove test repository from MinIO
    try:
        import boto3

        s3_client = boto3.client(
            "s3",
            endpoint_url=minio_settings["MINIO_ENDPOINT_URL"],
            aws_access_key_id=minio_settings["MINIO_ACCESS_KEY"],
            aws_secret_access_key=minio_settings["MINIO_SECRET_KEY"],
            region_name=minio_settings["MINIO_REGION"],
            verify=_verify_ssl(minio_settings),
        )

        # List and delete all objects in the test path
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=minio_settings["MINIO_BUCKET"], Prefix=repo_path
        ):
            if "Contents" in page:
                objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
                if objects:
                    s3_client.delete_objects(
                        Bucket=minio_settings["MINIO_BUCKET"],
                        Delete={"Objects": objects},
                    )
    except Exception as e:
        print(f"Warning: Failed to cleanup test repository: {e}")


@pytest.fixture
def temp_backup_source() -> Generator[Path, None, None]:
    """Create a temporary directory with test files for backup."""
    temp_dir = Path(tempfile.mkdtemp(prefix="timelocker_test_"))

    # Create test files
    (temp_dir / "file1.txt").write_text("Test content 1")
    (temp_dir / "file2.txt").write_text("Test content 2")

    subdir = temp_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("Test content 3")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def s3_repository(monkeypatch: pytest.MonkeyPatch) -> S3ResticRepository:
    """Create a repository for configuration-only tests without live I/O."""
    location = f"s3:minio.invalid:9000/{SYNTHETIC_BUCKET}/configuration-test"
    monkeypatch.setenv("AWS_S3_ENDPOINT", SYNTHETIC_ENDPOINT_URL)

    repo = S3ResticRepository(
        location=location,
        password="test-password-123",
        aws_access_key_id=SYNTHETIC_ACCESS_KEY,
        aws_secret_access_key=SYNTHETIC_SECRET_KEY,
        aws_default_region=SYNTHETIC_REGION,
    )
    return repo


@pytest.fixture
def live_s3_repository(
    test_repo_path: str,
    minio_settings: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> S3ResticRepository:
    """Create an S3 repository backed by the provisioned MinIO service."""
    location = (
        f"{minio_settings['MINIO_URI_PREFIX']}/"
        f"{minio_settings['MINIO_BUCKET']}/{test_repo_path}"
    )
    monkeypatch.setenv("AWS_S3_ENDPOINT", minio_settings["MINIO_ENDPOINT_URL"])

    repo = S3ResticRepository(
        location=location,
        password="test-password-123",
        aws_access_key_id=minio_settings["MINIO_ACCESS_KEY"],
        aws_secret_access_key=minio_settings["MINIO_SECRET_KEY"],
        aws_default_region=minio_settings["MINIO_REGION"],
    )

    return repo


def _make_backup_target(path: Path, *tags: str) -> BackupTarget:
    selection = FileSelection()
    selection.add_path(str(path), SelectionType.INCLUDE)
    return BackupTarget(selection=selection, tags=list(tags))


def test_s3_repository_initialization(s3_repository: S3ResticRepository):
    """Test S3 repository initialization with MinIO."""
    assert s3_repository is not None
    assert s3_repository.aws_access_key_id == SYNTHETIC_ACCESS_KEY
    assert s3_repository.aws_secret_access_key == SYNTHETIC_SECRET_KEY
    assert s3_repository.aws_default_region == SYNTHETIC_REGION


def test_s3_backend_env(s3_repository: S3ResticRepository):
    """Test that backend environment variables are correctly set."""
    env = s3_repository.backend_env()

    assert "AWS_ACCESS_KEY_ID" in env
    assert env["AWS_ACCESS_KEY_ID"] == SYNTHETIC_ACCESS_KEY
    assert "AWS_SECRET_ACCESS_KEY" in env
    assert env["AWS_SECRET_ACCESS_KEY"] == SYNTHETIC_SECRET_KEY
    assert "AWS_DEFAULT_REGION" in env
    assert env["AWS_DEFAULT_REGION"] == SYNTHETIC_REGION


@pytest.mark.network
@pytest.mark.minio
def test_s3_repository_init_and_check(live_s3_repository: S3ResticRepository):
    """Test initializing a repository in MinIO and checking it."""
    assert live_s3_repository.initialize() is True
    assert live_s3_repository.is_repository_initialized()
    assert live_s3_repository.check() is True


@pytest.mark.network
@pytest.mark.minio
def test_s3_backup_and_restore(
    live_s3_repository: S3ResticRepository, temp_backup_source: Path
):
    """Test complete backup and restore workflow with MinIO."""
    live_s3_repository.initialize()
    target = _make_backup_target(temp_backup_source, "test", "integration")
    backup_result = live_s3_repository.backup_target([target])
    assert backup_result is not None

    snapshots = live_s3_repository.snapshots()
    assert snapshots, "Expected at least one snapshot after backup"
    latest_snapshot = snapshots[0]

    restore_dir = Path(tempfile.mkdtemp(prefix="timelocker_restore_"))
    try:
        live_s3_repository.restore(latest_snapshot.id, restore_dir)

        def _find_file(name: str) -> Path:
            match = next((candidate for candidate in restore_dir.rglob(name)), None)
            assert (
                match is not None
            ), f"Expected restored file '{name}' not found under {restore_dir}"
            return match

        restored_file1 = _find_file("file1.txt")
        assert restored_file1.read_text() == "Test content 1"

        restored_file2 = _find_file("file2.txt")
        assert restored_file2.read_text() == "Test content 2"

        restored_file3 = _find_file("file3.txt")
        assert restored_file3.read_text() == "Test content 3"
    finally:
        shutil.rmtree(restore_dir, ignore_errors=True)


@pytest.mark.network
@pytest.mark.minio
def test_s3_multiple_backups(
    live_s3_repository: S3ResticRepository, temp_backup_source: Path
):
    """Test multiple backups to track incremental changes."""
    live_s3_repository.initialize()
    live_s3_repository.backup_target(
        [_make_backup_target(temp_backup_source, "backup1")]
    )

    (temp_backup_source / "file1.txt").write_text("Modified content 1")
    (temp_backup_source / "new_file.txt").write_text("New file content")

    live_s3_repository.backup_target(
        [_make_backup_target(temp_backup_source, "backup2")]
    )

    snapshots = live_s3_repository.snapshots()
    assert len(snapshots) >= 2

    tags_found = {
        tag for snapshot in snapshots for tag in getattr(snapshot, "tags", []) or []
    }
    assert {"backup1", "backup2"} & tags_found


@pytest.mark.network
@pytest.mark.minio
def test_s3_repository_stats(
    live_s3_repository: S3ResticRepository, temp_backup_source: Path
):
    """Test retrieving repository statistics."""
    live_s3_repository.initialize()
    live_s3_repository.backup_target([_make_backup_target(temp_backup_source)])
    stats = live_s3_repository.stats()
    assert isinstance(stats, dict) and stats


def test_s3_missing_credentials_error(monkeypatch):
    """Test that missing credentials raise appropriate errors."""
    for key in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    location = f"s3:minio.invalid:9000/{SYNTHETIC_BUCKET}/test"

    repo = S3ResticRepository(
        location=location,
        password="test-password",
        # No credentials provided
    )

    with pytest.raises(RepositoryError) as exc_info:
        repo.backend_env()

    assert "AWS credentials must be set" in str(exc_info.value)
