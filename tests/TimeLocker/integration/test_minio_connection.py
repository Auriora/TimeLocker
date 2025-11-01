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
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urlparse

import boto3
import pytest
from botocore.client import Config
from botocore.exceptions import ClientError

from TimeLocker.restic.Repositories.s3 import S3ResticRepository
from TimeLocker.security.credential_manager import CredentialManager

REQUIRED_ENV_VARS = ["MINIO_ENDPOINT_URL", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"]
DEFAULT_BUCKET = "timelocker-test"
DEFAULT_REGION = "us-east-1"


def _sanitize_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else endpoint


def _get_minio_settings() -> Tuple[str, str, str, str, str]:
    missing = [key for key in REQUIRED_ENV_VARS if not os.getenv(key)]
    if missing:
        pytest.skip(
                "MinIO connectivity tests skipped: missing environment variables "
                + ", ".join(missing)
        )

    endpoint = os.environ["MINIO_ENDPOINT_URL"]
    access_key = os.environ["MINIO_ACCESS_KEY"]
    secret_key = os.environ["MINIO_SECRET_KEY"]
    bucket = os.getenv("MINIO_BUCKET", DEFAULT_BUCKET)
    region = os.getenv("MINIO_REGION", DEFAULT_REGION)

    return endpoint, access_key, secret_key, bucket, region


@pytest.fixture(scope="session")
def minio_settings() -> Tuple[str, str, str, str, str]:
    return _get_minio_settings()


@pytest.fixture(scope="session")
def boto3_client(minio_settings) -> boto3.client:
    endpoint, access_key, secret_key, _, region = minio_settings
    try:
        client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                config=Config(signature_version="s3v4"),
        )
        client.list_buckets()
        return client
    except Exception as exc:
        pytest.skip(f"MinIO not reachable: {exc}")


@pytest.fixture()
def temp_credential_manager(tmp_path: Path) -> CredentialManager:
    cred_dir = tmp_path / "creds"
    cred_dir.mkdir(parents=True, exist_ok=True)
    manager = CredentialManager(config_dir=cred_dir)
    if manager.is_locked() and not manager.auto_unlock():
        manager.unlock("test-password-123")
    if manager.is_locked():
        pytest.skip("CredentialManager could not be unlocked for testing")
    return manager


@pytest.fixture()
def repository(minio_settings) -> S3ResticRepository:
    endpoint, access_key, secret_key, bucket, _ = minio_settings
    host = urlparse(endpoint).netloc or endpoint
    location = f"s3:{host}/{bucket}"
    os.environ["AWS_S3_ENDPOINT"] = endpoint
    return S3ResticRepository(
            location=location,
            password="test-password-123",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
    )


def test_boto3_lists_buckets(boto3_client):
    buckets = boto3_client.list_buckets().get("Buckets", [])
    assert isinstance(buckets, list)


def test_credential_manager_roundtrip(minio_settings, temp_credential_manager):
    _, access_key, secret_key, _, _ = minio_settings
    repo_name = "minio-test"
    payload: Dict[str, str] = {
            "access_key_id":     access_key,
            "secret_access_key": secret_key,
    }
    temp_credential_manager.store_repository_backend_credentials(repo_name, "s3", payload)
    retrieved = temp_credential_manager.get_repository_backend_credentials(repo_name, "s3")
    assert retrieved == payload


def test_s3_repository_backend_env(repository, minio_settings):
    endpoint, _, _, _, _ = minio_settings
    env = repository.backend_env()
    assert env["AWS_S3_ENDPOINT"] == endpoint
    assert env["AWS_ACCESS_KEY_ID"]
    assert env["AWS_SECRET_ACCESS_KEY"]
