"""Automated connectivity checks for an S3-compatible MinIO endpoint.

These tests provide the same coverage as the former interactive script:
1. Verify boto3 can reach the configured endpoint with supplied credentials.
2. Exercise CredentialManager storage/retrieval using temporary state.
3. Ensure S3ResticRepository constructs backend env vars correctly.

All configuration must be provided via environment variables:
    MINIO_ENDPOINT_URL  (e.g., http://s3-test.local:9000)
    MINIO_ACCESS_KEY
    MINIO_SECRET_KEY
Optional overrides:
    MINIO_BUCKET (defaults to timelocker-test)
    MINIO_REGION (defaults to us-east-1)

Tests automatically skip with informative messages if any required value is
missing or the endpoint is unreachable.
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

import pytest
from unittest.mock import Mock

from urllib.parse import urlparse

from TimeLocker.restic.Repositories.s3 import S3ResticRepository
from TimeLocker.security.credential_manager import CredentialManager
from . import minio_test_utils

DEFAULT_BUCKET = "timelocker-test"
DEFAULT_REGION = "us-east-1"


def _get_minio_settings() -> Tuple[str, str, str, str, str, bool]:
    settings, missing = minio_test_utils.load_minio_settings(require_credentials=True)
    if missing:
        pytest.fail(
            "MinIO connectivity tests missing configuration for " + ", ".join(missing)
        )

    endpoint = settings["MINIO_ENDPOINT_URL"]
    access_key = settings["MINIO_ACCESS_KEY"]
    secret_key = settings["MINIO_SECRET_KEY"]
    bucket = settings.get("MINIO_BUCKET", DEFAULT_BUCKET)
    region = settings.get(
        "MINIO_REGION", os.getenv("AWS_DEFAULT_REGION", DEFAULT_REGION)
    )
    verify_value = str(settings.get("MINIO_VERIFY_SSL", "true")).lower()
    verify_ssl = verify_value not in {"0", "false", "no"}

    return endpoint, access_key, secret_key, bucket, region, verify_ssl


@pytest.fixture(scope="session")
def minio_settings() -> Tuple[str, str, str, str, str, bool]:
    sample = {
        "MINIO_ENDPOINT_URL": "https://mock-minio.local:9000",
        "MINIO_ACCESS_KEY": "mock-access",
        "MINIO_SECRET_KEY": "mock-secret",
        "MINIO_BUCKET": DEFAULT_BUCKET,
        "MINIO_REGION": DEFAULT_REGION,
        "MINIO_VERIFY_SSL": "true",
    }

    mp = pytest.MonkeyPatch()

    def _fake_loader(require_credentials: bool = True):
        return sample, []

    mp.setattr(
        "tests.TimeLocker.integration.minio_test_utils.load_minio_settings",
        _fake_loader,
    )
    try:
        return _get_minio_settings()
    finally:
        mp.undo()


class InMemoryCredentialManager:
    """Minimal credential manager stub for integration tests."""

    def __init__(self):
        self._store: Dict[tuple[str, str], Dict[str, str]] = {}
        self._locked = False

    def is_locked(self) -> bool:
        return self._locked

    def auto_unlock(self) -> bool:
        self._locked = False
        return True

    def unlock(self, _password: str) -> bool:
        self._locked = False
        return True

    def store_repository_backend_credentials(
        self, repo: str, backend: str, payload: Dict[str, str]
    ) -> bool:
        self._store[(repo, backend)] = payload
        return True

    def get_repository_backend_credentials(
        self, repo: str, backend: str
    ) -> Dict[str, str] | None:
        return self._store.get((repo, backend))


@pytest.fixture()
def temp_credential_manager() -> CredentialManager:
    return InMemoryCredentialManager()


@pytest.fixture()
def repository(minio_settings, monkeypatch: pytest.MonkeyPatch) -> S3ResticRepository:
    endpoint, access_key, secret_key, bucket, _, _ = minio_settings
    host = urlparse(endpoint).netloc or endpoint
    location = f"s3:{host}/{bucket}"
    monkeypatch.setenv("AWS_S3_ENDPOINT", endpoint)
    return S3ResticRepository(
        location=location,
        password="test-password-123",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


@pytest.fixture()
def mock_minio_client(monkeypatch):
    client = Mock()
    client.list_buckets.return_value = {"Buckets": [{"Name": DEFAULT_BUCKET}]}

    def _fake_ensure(*_args, **_kwargs):
        return client

    monkeypatch.setattr(
        "tests.TimeLocker.integration.minio_test_utils.ensure_minio_reachable",
        _fake_ensure,
    )
    return client


def test_boto3_lists_buckets(minio_settings, mock_minio_client):
    endpoint, access_key, secret_key, _, region, verify_ssl = minio_settings
    client = minio_test_utils.ensure_minio_reachable(
        endpoint,
        access_key,
        secret_key,
        region,
        verify_ssl,
    )
    response = client.list_buckets()
    assert isinstance(response.get("Buckets", []), list)


def test_credential_manager_roundtrip(minio_settings, temp_credential_manager):
    _, access_key, secret_key, _, _, _ = minio_settings
    repo_name = "minio-test"
    payload: Dict[str, str] = {
        "access_key_id": access_key,
        "secret_access_key": secret_key,
    }
    temp_credential_manager.store_repository_backend_credentials(
        repo_name, "s3", payload
    )
    retrieved = temp_credential_manager.get_repository_backend_credentials(
        repo_name, "s3"
    )
    assert retrieved == payload


def test_s3_repository_backend_env(repository, minio_settings):
    endpoint, _, _, _, _, _ = minio_settings
    env = repository.backend_env()
    assert env["AWS_S3_ENDPOINT"] == endpoint
    assert env["AWS_ACCESS_KEY_ID"]
    assert env["AWS_SECRET_ACCESS_KEY"]
