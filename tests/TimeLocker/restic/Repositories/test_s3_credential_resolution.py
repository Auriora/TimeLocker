"""
Tests for S3ResticRepository credential resolution chain.

Precedence order per implementation:
1. Explicit constructor parameters (highest precedence per field)
2. Per-repository credentials from credential manager
3. Environment variables

Additionally, insecure_tls precedence:
1. Explicit constructor parameter
2. Credential manager value (repo_creds["insecure_tls"], default False if missing)
3. Environment variable RESTIC_INSECURE_TLS (only used if insecure_tls still None)

Note:
- Missing credential error scenarios are already comprehensively covered in test_s3.py; they are not duplicated here.
"""
from unittest.mock import MagicMock, patch
import os
import pytest

from TimeLocker.restic.Repositories.s3 import S3ResticRepository


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for var in [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_DEFAULT_REGION",
            "AWS_S3_ENDPOINT",
            "RESTIC_INSECURE_TLS",
    ]:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_s3_client():
    with patch('TimeLocker.restic.Repositories.s3.client') as mock_client:
        yield mock_client


# -----------------------------
# Parameterized credential resolution chain test
# -----------------------------
@pytest.mark.unit
@pytest.mark.parametrize(
        "env_vars, cm_creds, constructor_kwargs, expected",
        [
                # Case 1: Constructor overrides CM & env for provided fields; CM supplies remaining; env ignored.
                (
                            {"AWS_ACCESS_KEY_ID": "env_key", "AWS_SECRET_ACCESS_KEY": "env_secret", "AWS_DEFAULT_REGION": "env-region"},
                            {"access_key_id": "cm_key", "secret_access_key": "cm_secret", "region": "cm-region"},
                            {"aws_access_key_id": "param_key"},
                            {"aws_access_key_id": "param_key", "aws_secret_access_key": "cm_secret", "aws_default_region": "cm-region"},
                ),
                # Case 2: CM used when constructor omits credentials; env ignored.
                (
                            {"AWS_ACCESS_KEY_ID": "env_key", "AWS_SECRET_ACCESS_KEY": "env_secret", "AWS_DEFAULT_REGION": "env-region"},
                            {"access_key_id": "cm_key", "secret_access_key": "cm_secret", "region": "cm-region"},
                            {},
                            {"aws_access_key_id": "cm_key", "aws_secret_access_key": "cm_secret", "aws_default_region": "cm-region"},
                ),
                # Case 3: Env used when CM supplies nothing (empty dict) and constructor empty.
                (
                            {"AWS_ACCESS_KEY_ID": "env_key", "AWS_SECRET_ACCESS_KEY": "env_secret", "AWS_DEFAULT_REGION": "env-region"},
                            {},
                            {},
                            {"aws_access_key_id": "env_key", "aws_secret_access_key": "env_secret", "aws_default_region": "env-region"},
                ),
                # Case 4: Pure environment (no CM provided at all).
                (
                            {"AWS_ACCESS_KEY_ID": "env_only_key", "AWS_SECRET_ACCESS_KEY": "env_only_secret", "AWS_DEFAULT_REGION": "env-only-region"},
                            None,
                            {},
                            {"aws_access_key_id": "env_only_key", "aws_secret_access_key": "env_only_secret", "aws_default_region": "env-only-region"},
                ),
                # Case 5: Partial mix - constructor key, CM secret, env region (CM lacks region)
                (
                            {"AWS_ACCESS_KEY_ID": "env_key", "AWS_SECRET_ACCESS_KEY": "env_secret", "AWS_DEFAULT_REGION": "env-region"},
                            {"access_key_id": "cm_key", "secret_access_key": "cm_secret"},  # no region in CM
                            {"aws_access_key_id": "param_key"},
                            {"aws_access_key_id": "param_key", "aws_secret_access_key": "cm_secret", "aws_default_region": "env-region"},
                ),
        ],
)
def test_credential_resolution_chain(monkeypatch, mock_s3_client, env_vars, cm_creds, constructor_kwargs, expected):
    # Arrange environment
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)

    # Arrange credential manager
    credential_manager = None
    repository_name = None
    if cm_creds is not None:
        mock_cm = MagicMock()
        mock_cm.get_repository_backend_credentials.return_value = cm_creds
        credential_manager = mock_cm
        repository_name = "repo-param"

    # Act
    repo = S3ResticRepository(
            location="s3:bucket/path",
            credential_manager=credential_manager,
            repository_name=repository_name,
            **constructor_kwargs,
    )

    # Assert expected resolved values
    assert repo.aws_access_key_id == expected["aws_access_key_id"]
    assert repo.aws_secret_access_key == expected["aws_secret_access_key"]
    assert repo.aws_default_region == expected["aws_default_region"]


# -----------------------------
# insecure_tls precedence tests
# -----------------------------
@pytest.mark.unit
def test_insecure_tls_precedence_constructor_overrides_credential_manager(monkeypatch, mock_s3_client):
    monkeypatch.setenv("RESTIC_INSECURE_TLS", "false")
    mock_cm = MagicMock()
    mock_cm.get_repository_backend_credentials.return_value = {
            "access_key_id":     "cm_key",
            "secret_access_key": "cm_secret",
            "insecure_tls":      False,
    }
    repo = S3ResticRepository(
            location="s3:bucket/path",
            aws_access_key_id="param_key",
            aws_secret_access_key="param_secret",
            insecure_tls=True,
            credential_manager=mock_cm,
            repository_name="repo4",
    )
    assert repo.insecure_tls is True


@pytest.mark.unit
def test_insecure_tls_from_credential_manager_over_env(monkeypatch, mock_s3_client):
    monkeypatch.setenv("RESTIC_INSECURE_TLS", "true")
    mock_cm = MagicMock()
    mock_cm.get_repository_backend_credentials.return_value = {
            "access_key_id":     "cm_key",
            "secret_access_key": "cm_secret",
            "insecure_tls":      False,
    }
    repo = S3ResticRepository(
            location="s3:bucket/path",
            credential_manager=mock_cm,
            repository_name="repo5",
    )
    assert repo.insecure_tls is False


@pytest.mark.unit
def test_insecure_tls_env_used_when_no_constructor_or_cm(monkeypatch, mock_s3_client):
    monkeypatch.setenv("RESTIC_INSECURE_TLS", "true")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "env_key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "env_secret")
    repo = S3ResticRepository(location="s3:bucket/path")
    assert repo.insecure_tls is True


# -----------------------------
# Logging behavior tests (backend_env)
# -----------------------------
@pytest.mark.unit
def test_backend_env_logs_insecure_tls_true(monkeypatch, mock_s3_client, caplog):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "k")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "s")
    repo = S3ResticRepository(
            location="s3:bucket/path",
            aws_access_key_id="k",  # explicit
            aws_secret_access_key="s",
            insecure_tls=True,
    )
    with caplog.at_level("INFO"):
        env = repo.backend_env()
    assert env["RESTIC_INSECURE_TLS"] == "true"
    assert "Setting RESTIC_INSECURE_TLS=true" in caplog.text


@pytest.mark.unit
def test_backend_env_logs_insecure_tls_false(monkeypatch, mock_s3_client, caplog):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "k")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "s")
    repo = S3ResticRepository(
            location="s3:bucket/path",
            aws_access_key_id="k",
            aws_secret_access_key="s",
            insecure_tls=False,
    )
    with caplog.at_level("INFO"):
        env = repo.backend_env()
    assert "RESTIC_INSECURE_TLS" not in env
    assert "insecure_tls is False or None: False" in caplog.text


@pytest.mark.unit
def test_backend_env_logs_endpoint(monkeypatch, mock_s3_client, caplog):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "k")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "s")
    repo = S3ResticRepository(
            location="s3:minio.local/bucket",
            aws_access_key_id="k",
            aws_secret_access_key="s",
            aws_s3_endpoint="http://minio.local:9000",
    )
    with caplog.at_level("INFO"):
        env = repo.backend_env()
    assert env["AWS_S3_ENDPOINT"] == "http://minio.local:9000"
    assert "Setting AWS_S3_ENDPOINT to http://minio.local:9000" in caplog.text
