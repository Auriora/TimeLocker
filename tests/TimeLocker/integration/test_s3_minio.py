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

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator
from urllib.parse import urlparse

import pytest

from TimeLocker.restic.Repositories.s3 import S3ResticRepository
from TimeLocker.restic.restic_repository import RepositoryError


def _extract_host_bucket_from_s3_uri(uri: str) -> tuple[str | None, str | None, str]:
    """Extract host, bucket, and scheme from an s3: URI."""
    if not uri or not uri.startswith("s3:"):
        return None, None, "http"
    remainder = uri[3:]
    if remainder.startswith("//"):
        remainder = remainder[2:]
    scheme = "http"
    host = None
    path_part = ""
    if remainder.startswith(("http://", "https://")):
        parsed = urlparse(remainder)
        host = parsed.netloc or parsed.path
        path_part = parsed.path.lstrip("/")
        scheme = parsed.scheme or scheme
    else:
        segment = remainder.split("/", 1)
        host = segment[0]
        path_part = segment[1] if len(segment) > 1 else ""
    bucket = path_part.split("/", 1)[0] if path_part else None
    return host, bucket, scheme


def _load_minio_settings() -> dict[str, str]:
    """Load MinIO settings from environment or configuration files."""
    settings: dict[str, str] = {}

    env_keys = [
            "MINIO_ENDPOINT",
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
            "MINIO_BUCKET",
            "MINIO_REGION",
            "AWS_S3_ENDPOINT",
    ]
    for key in env_keys:
        value = os.getenv(key)
        if value:
            settings[key] = value

    config_candidates = []
    env_config_path = os.getenv("TIMELOCKER_CONFIG_FILE")
    if env_config_path:
        config_candidates.append(Path(env_config_path))
    config_candidates.append(Path("test-config.json"))
    config_candidates.append(Path("test-config.example.json"))

    for config_path in config_candidates:
        if not config_path or not config_path.is_file():
            continue
        try:
            config_data = json.loads(config_path.read_text())
        except Exception:
            continue

        for repo in config_data.get("repositories", []):
            uri = repo.get("uri") or repo.get("location")
            if not uri or not str(uri).startswith("s3"):
                continue
            host, bucket, scheme = _extract_host_bucket_from_s3_uri(str(uri))
            if host and "MINIO_ENDPOINT" not in settings:
                settings["MINIO_ENDPOINT"] = host
                settings.setdefault("AWS_S3_ENDPOINT", f"{scheme}://{host}")
                settings.setdefault("MINIO_URI_PREFIX", f"s3:{scheme}://{host}")
            if bucket and "MINIO_BUCKET" not in settings:
                settings["MINIO_BUCKET"] = bucket

            credentials = repo.get("credentials", {})
            if isinstance(credentials, dict):
                settings.setdefault("MINIO_ACCESS_KEY", credentials.get("aws_access_key_id", ""))
                settings.setdefault("MINIO_SECRET_KEY", credentials.get("aws_secret_access_key", ""))
                settings.setdefault("MINIO_REGION", credentials.get("aws_default_region", ""))
            break

        missing = [key for key in ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET", "MINIO_REGION") if not settings.get(key)]
        if not missing:
            break

    # Normalize endpoint host and URL values
    endpoint = settings.get("MINIO_ENDPOINT")
    if endpoint:
        parsed = urlparse(endpoint)
        if parsed.scheme:
            settings["MINIO_ENDPOINT"] = parsed.netloc or parsed.path
    endpoint_url = settings.get("AWS_S3_ENDPOINT")
    if endpoint_url:
        if not urlparse(endpoint_url).scheme:
            settings["AWS_S3_ENDPOINT"] = f"http://{endpoint_url}"
    elif settings.get("MINIO_ENDPOINT"):
        settings["AWS_S3_ENDPOINT"] = f"http://{settings['MINIO_ENDPOINT']}"
    if "MINIO_URI_PREFIX" not in settings and settings.get("AWS_S3_ENDPOINT"):
        settings["MINIO_URI_PREFIX"] = f"s3:{settings['AWS_S3_ENDPOINT']}"

    return {k: v for k, v in settings.items() if v}


_MINIO_SETTINGS = _load_minio_settings()
_REQUIRED_KEYS = ["MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET", "MINIO_REGION"]
_MISSING_KEYS = [key for key in _REQUIRED_KEYS if key not in _MINIO_SETTINGS]

if _MISSING_KEYS:
    missing_list = ", ".join(_MISSING_KEYS)
    pytest.skip(
            f"MinIO integration tests skipped: missing configuration for {missing_list}. "
            f"Set environment variables or update your test configuration file.",
            allow_module_level=True
    )

MINIO_ENDPOINT = _MINIO_SETTINGS["MINIO_ENDPOINT"]
MINIO_ACCESS_KEY = _MINIO_SETTINGS["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY = _MINIO_SETTINGS["MINIO_SECRET_KEY"]
MINIO_BUCKET = _MINIO_SETTINGS["MINIO_BUCKET"]
MINIO_REGION = _MINIO_SETTINGS["MINIO_REGION"]
MINIO_ENDPOINT_URL = _MINIO_SETTINGS.get("AWS_S3_ENDPOINT", f"http://{MINIO_ENDPOINT}")
MINIO_URI_PREFIX = _MINIO_SETTINGS.get("MINIO_URI_PREFIX", f"s3:{MINIO_ENDPOINT_URL}")


@pytest.fixture(scope="session")
def minio_available() -> bool:
    """
    Check if MinIO is available for testing.

    This is a session-scoped fixture to avoid repeated connection attempts.
    Returns True if MinIO is available, otherwise skips all tests that depend on it.
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        s3_client = boto3.client(
                's3',
                endpoint_url=MINIO_ENDPOINT_URL,
                aws_access_key_id=MINIO_ACCESS_KEY,
                aws_secret_access_key=MINIO_SECRET_KEY,
                region_name=MINIO_REGION
        )

        # Try to list buckets to verify connection
        s3_client.list_buckets()
        return True
    except Exception as e:
        pytest.skip(f"MinIO not available: {e}")


@pytest.fixture
def test_repo_path() -> Generator[str, None, None]:
    """Create a unique test repository path in MinIO bucket."""
    import uuid
    test_id = str(uuid.uuid4())[:8]
    repo_path = f"test-repo-{test_id}"
    yield repo_path

    # Cleanup: Remove test repository from MinIO
    try:
        import boto3
        s3_client = boto3.client(
                's3',
                endpoint_url=MINIO_ENDPOINT_URL,
                aws_access_key_id=MINIO_ACCESS_KEY,
                aws_secret_access_key=MINIO_SECRET_KEY,
                region_name=MINIO_REGION
        )

        # List and delete all objects in the test path
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=MINIO_BUCKET, Prefix=repo_path):
            if 'Contents' in page:
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                if objects:
                    s3_client.delete_objects(
                            Bucket=MINIO_BUCKET,
                            Delete={'Objects': objects}
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
def s3_repository(test_repo_path: str, minio_available: bool) -> S3ResticRepository:
    """Create an S3 repository instance configured for MinIO."""
    # MinIO location format
    location = f"{MINIO_URI_PREFIX}/{MINIO_BUCKET}/{test_repo_path}"

    repo = S3ResticRepository(
            location=location,
            password="test-password-123",
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            aws_default_region=MINIO_REGION
    )

    # Set MinIO endpoint in environment for restic
    os.environ['AWS_S3_ENDPOINT'] = MINIO_ENDPOINT_URL

    return repo


@pytest.mark.integration
@pytest.mark.network
def test_s3_repository_initialization(s3_repository: S3ResticRepository):
    """Test S3 repository initialization with MinIO."""
    assert s3_repository is not None
    assert s3_repository.aws_access_key_id == MINIO_ACCESS_KEY
    assert s3_repository.aws_secret_access_key == MINIO_SECRET_KEY
    assert s3_repository.aws_default_region == MINIO_REGION


@pytest.mark.integration
@pytest.mark.network
def test_s3_backend_env(s3_repository: S3ResticRepository):
    """Test that backend environment variables are correctly set."""
    env = s3_repository.backend_env()

    assert "AWS_ACCESS_KEY_ID" in env
    assert env["AWS_ACCESS_KEY_ID"] == MINIO_ACCESS_KEY
    assert "AWS_SECRET_ACCESS_KEY" in env
    assert env["AWS_SECRET_ACCESS_KEY"] == MINIO_SECRET_KEY
    assert "AWS_DEFAULT_REGION" in env
    assert env["AWS_DEFAULT_REGION"] == MINIO_REGION


@pytest.mark.integration
@pytest.mark.network
def test_s3_repository_init_and_check(s3_repository: S3ResticRepository):
    """Test initializing a repository in MinIO and checking it."""
    # Initialize the repository
    s3_repository.init()

    # Verify repository is initialized
    assert s3_repository.is_repository_initialized()

    # Check repository integrity
    check_result = s3_repository.check()
    assert check_result is not None


@pytest.mark.integration
@pytest.mark.network
def test_s3_backup_and_restore(
        s3_repository: S3ResticRepository,
        temp_backup_source: Path
):
    """Test complete backup and restore workflow with MinIO."""
    # Initialize repository
    s3_repository.init()

    # Perform backup
    backup_result = s3_repository.backup(
            paths=[str(temp_backup_source)],
            tags=["test", "integration"]
    )

    assert backup_result is not None
    assert "snapshot_id" in backup_result or backup_result.get("files_new", 0) >= 0

    # List snapshots
    snapshots = s3_repository.list_snapshots()
    assert len(snapshots) > 0

    # Get the latest snapshot
    latest_snapshot = snapshots[0]

    # Create restore directory
    restore_dir = Path(tempfile.mkdtemp(prefix="timelocker_restore_"))

    try:
        # Restore from snapshot
        s3_repository.restore(
                snapshot_id=latest_snapshot.get("id", latest_snapshot.get("short_id")),
                target_path=str(restore_dir)
        )

        # Verify restored files
        restored_file1 = restore_dir / temp_backup_source.name / "file1.txt"
        assert restored_file1.exists()
        assert restored_file1.read_text() == "Test content 1"

        restored_file2 = restore_dir / temp_backup_source.name / "file2.txt"
        assert restored_file2.exists()
        assert restored_file2.read_text() == "Test content 2"

        restored_file3 = restore_dir / temp_backup_source.name / "subdir" / "file3.txt"
        assert restored_file3.exists()
        assert restored_file3.read_text() == "Test content 3"

    finally:
        # Cleanup restore directory
        shutil.rmtree(restore_dir, ignore_errors=True)


@pytest.mark.integration
@pytest.mark.network
def test_s3_multiple_backups(
        s3_repository: S3ResticRepository,
        temp_backup_source: Path
):
    """Test multiple backups to track incremental changes."""
    # Initialize repository
    s3_repository.init()

    # First backup
    s3_repository.backup(paths=[str(temp_backup_source)], tags=["backup1"])

    # Modify files
    (temp_backup_source / "file1.txt").write_text("Modified content 1")
    (temp_backup_source / "new_file.txt").write_text("New file content")

    # Second backup
    s3_repository.backup(paths=[str(temp_backup_source)], tags=["backup2"])

    # List snapshots
    snapshots = s3_repository.list_snapshots()
    assert len(snapshots) >= 2

    # Verify tags
    tags_found = set()
    for snapshot in snapshots:
        if "tags" in snapshot:
            tags_found.update(snapshot["tags"])

    assert "backup1" in tags_found or "backup2" in tags_found


@pytest.mark.integration
@pytest.mark.network
def test_s3_repository_stats(s3_repository: S3ResticRepository, temp_backup_source: Path):
    """Test retrieving repository statistics."""
    # Initialize and backup
    s3_repository.init()
    s3_repository.backup(paths=[str(temp_backup_source)])

    # Get repository stats
    stats = s3_repository.stats()

    assert stats is not None
    # Stats should contain information about the repository


@pytest.mark.integration
@pytest.mark.network
def test_s3_missing_credentials_error():
    """Test that missing credentials raise appropriate errors."""
    location = f"{MINIO_URI_PREFIX}/{MINIO_BUCKET}/test"

    repo = S3ResticRepository(
            location=location,
            password="test-password"
            # No credentials provided
    )

    with pytest.raises(RepositoryError) as exc_info:
        repo.backend_env()

    assert "AWS credentials must be set" in str(exc_info.value)
