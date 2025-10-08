"""Shared test fixtures for S3 restic repository tests.

Fixtures provided:
- mock_s3_client: patches boto3 client used in S3ResticRepository to avoid real AWS calls
- clear_aws_env: ensures a clean AWS-related environment for tests that rely on fallback ordering

Note: The `patch` import is only required here (not in individual test modules) because
these fixtures centralize all boto3 client patching logic.
"""
from unittest.mock import MagicMock, patch

import pytest

# Internal constant listing AWS-related environment variables we sanitize between tests.
# Leading underscore denotes module-private usage.
_AWS_ENVIRONMENT_VARIABLES = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "AWS_S3_ENDPOINT",
        "RESTIC_INSECURE_TLS",
]


@pytest.fixture
def mock_s3_client():
    """Fixture to mock the boto3 client used by S3ResticRepository.

    Prevents real network interactions while allowing tests to proceed through
    initialization and validation logic paths.
    """
    with patch('TimeLocker.restic.Repositories.s3.client') as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def clear_aws_env(monkeypatch):
    """Clear AWS-related environment variables for isolated test behavior."""
    for var in _AWS_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(var, raising=False)
