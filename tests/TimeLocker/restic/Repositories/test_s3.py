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

from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest

from TimeLocker.restic.logging import logger
from TimeLocker.restic.Repositories.s3 import S3ResticRepository
from TimeLocker.restic.restic_repository import RepositoryError


@pytest.fixture
def mock_s3_client():
    """Fixture to mock the S3 client for all tests"""
    with patch('TimeLocker.restic.Repositories.s3.client') as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        yield mock_s3


@pytest.mark.unit
def test_init_missing_credentials(monkeypatch, mock_s3_client):
    """
    Test initialization of S3ResticRepository when AWS credentials are missing from both
    parameters and environment variables.
    """
    # Clear environment variables to simulate missing credentials
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    repo = S3ResticRepository("s3:bucket/path")

    # The __init__ method doesn't raise exceptions, it just sets attributes
    # We'll test the actual error handling in the backend_env method
    with pytest.raises(RepositoryError) as exc_info:
        repo.backend_env()

    assert "AWS credentials must be set explicitly or in the environment" in str(
        exc_info.value
    )
    assert "AWS_ACCESS_KEY_ID" in str(exc_info.value)
    assert "AWS_SECRET_ACCESS_KEY" in str(exc_info.value)


@pytest.mark.unit
def test___init___with_explicit_credentials(mock_s3_client):
    """
    Test initializing S3ResticRepository with explicitly provided credentials.
    Verifies that the provided credentials are correctly assigned to instance variables.
    """
    location = "s3:mybucket/mypath"
    password = "mypassword"
    aws_access_key_id = "my_access_key"
    aws_secret_access_key = "my_secret_key"
    aws_default_region = "us-west-2"

    repo = S3ResticRepository(
        location,
        password,
        aws_access_key_id,
        aws_secret_access_key,
        aws_default_region,
    )

    assert repo.location() == location
    assert repo.password() == password
    assert repo.aws_access_key_id == aws_access_key_id
    assert repo.aws_secret_access_key == aws_secret_access_key
    assert repo.aws_default_region == aws_default_region


@pytest.mark.unit
def test_backend_env_2(mock_s3_client):
    """
    Test backend_env method when AWS access key is present, but secret access key is missing,
    and default region is set.

    This test verifies that:
    1. A RepositoryError is raised when the secret access key is missing.
    2. The error message correctly identifies the missing credential.
    3. The AWS default region is not considered in the missing credentials check.
    """
    repo = S3ResticRepository(
        location="s3:test-bucket/path",
        aws_access_key_id="test_access_key",
        aws_secret_access_key=None,
        aws_default_region="us-west-2",
    )

    with pytest.raises(RepositoryError) as exc_info:
        repo.backend_env()

    assert "AWS credentials must be set explicitly or in the environment" in str(
        exc_info.value
    )
    assert "AWS_SECRET_ACCESS_KEY" in str(exc_info.value)
    assert "AWS_ACCESS_KEY_ID" not in str(exc_info.value)


@pytest.mark.unit
def test_backend_env_3(mock_s3_client):
    """
    Test that backend_env raises RepositoryError when AWS_ACCESS_KEY_ID is missing,
    but AWS_SECRET_ACCESS_KEY and AWS_DEFAULT_REGION are provided.
    """
    repo = S3ResticRepository(
        location="s3:my-bucket/my-path",
        aws_access_key_id=None,
        aws_secret_access_key="secret_key",
        aws_default_region="us-west-2",
    )

    with pytest.raises(RepositoryError) as excinfo:
        repo.backend_env()

    assert (
        "AWS credentials must be set explicitly or in the environment. Missing: AWS_ACCESS_KEY_ID"
        in str(excinfo.value)
    )


@pytest.mark.unit
def test_backend_env_4(mock_s3_client):
    """
    Test that backend_env raises a RepositoryError when both AWS credentials are missing,
    even if aws_default_region is set.
    """
    repo = S3ResticRepository(location="s3:bucket/path", aws_default_region="us-west-2")

    with pytest.raises(RepositoryError) as exc_info:
        repo.backend_env()

    assert "AWS credentials must be set explicitly or in the environment" in str(
        exc_info.value
    )
    assert "AWS_ACCESS_KEY_ID" in str(exc_info.value)
    assert "AWS_SECRET_ACCESS_KEY" in str(exc_info.value)


@pytest.mark.unit
def test_backend_env_missing_credentials(mock_s3_client):
    """
    Test that backend_env raises a RepositoryError when AWS credentials are missing.
    This tests the edge case where either AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY
    or both are not provided.
    """
    repo = S3ResticRepository(location="s3:bucket/path")
    with pytest.raises(RepositoryError) as exc_info:
        repo.backend_env()

    assert "AWS credentials must be set explicitly or in the environment" in str(
        exc_info.value
    )
    assert "AWS_ACCESS_KEY_ID" in str(exc_info.value)
    assert "AWS_SECRET_ACCESS_KEY" in str(exc_info.value)


@pytest.mark.unit
def test_backend_env_missing_credentials_2(mock_s3_client):
    """
    Test backend_env method when both AWS access key ID and secret access key are missing.

    This test verifies that the backend_env method raises a RepositoryError
    when both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are not provided.
    The error message should indicate which credentials are missing.
    """
    repo = S3ResticRepository(location="s3:bucket/path")

    with pytest.raises(RepositoryError) as exc_info:
        repo.backend_env()

    assert "AWS credentials must be set explicitly or in the environment" in str(
        exc_info.value
    )
    assert "AWS_ACCESS_KEY_ID" in str(exc_info.value)
    assert "AWS_SECRET_ACCESS_KEY" in str(exc_info.value)


@pytest.mark.unit
def test_backend_env_missing_credentials_3(mock_s3_client):
    """
    Test the backend_env method when both AWS access key ID and secret access key are missing.

    This test verifies that:
    1. A RepositoryError is raised when credentials are missing.
    2. The error message correctly identifies the missing credentials.
    3. The method fails before setting any environment variables.
    """
    repo = S3ResticRepository(location="s3:bucket/path")

    with pytest.raises(RepositoryError) as excinfo:
        repo.backend_env()

    assert "AWS credentials must be set explicitly or in the environment" in str(
        excinfo.value
    )
    assert "AWS_ACCESS_KEY_ID" in str(excinfo.value)
    assert "AWS_SECRET_ACCESS_KEY" in str(excinfo.value)


@pytest.mark.unit
def test_from_parsed_uri_empty_bucket(mock_s3_client):
    """
    Test the from_parsed_uri method with an empty bucket name.
    This is an edge case where the parsed URI has an empty netloc (bucket name).
    """
    parsed_uri = urlparse("s3://")
    result = S3ResticRepository.from_parsed_uri(parsed_uri)
    assert result.location() == "s3:/"


@pytest.mark.unit
def test_from_parsed_uri_empty_path(mock_s3_client):
    """
    Test the from_parsed_uri method with an empty path.
    This is an edge case where the parsed URI has no path component.
    """
    parsed_uri = urlparse("s3://mybucket")
    result = S3ResticRepository.from_parsed_uri(parsed_uri)
    assert result.location() == "s3:mybucket/"


@pytest.mark.unit
def test_from_parsed_uri_empty_query_params(mock_s3_client):
    """
    Test the from_parsed_uri method with empty query parameters.
    This checks the handling of query parameters with no values.
    """
    parsed_uri = urlparse(
        "s3://mybucket/mypath?access_key_id=&secret_access_key=&region="
    )
    result = S3ResticRepository.from_parsed_uri(parsed_uri)
    assert result.aws_access_key_id == ""
    assert result.aws_secret_access_key == ""
    assert result.aws_default_region == ""


@pytest.mark.unit
def test_from_parsed_uri_no_query_params(mock_s3_client):
    """
    Test the from_parsed_uri method with no query parameters.
    This checks the handling of missing optional parameters.
    """
    parsed_uri = urlparse("s3://mybucket/mypath")
    result = S3ResticRepository.from_parsed_uri(parsed_uri)
    assert result.aws_access_key_id is None
    assert result.aws_secret_access_key is None
    assert result.aws_default_region is None


@pytest.mark.unit
def test_from_parsed_uri_with_all_parameters(mock_s3_client):
    """
    Test the from_parsed_uri method with all parameters provided in the query string.
    This test verifies that the method correctly extracts and uses the access_key_id,
    secret_access_key, and region from the parsed URI.
    """
    parsed_uri = urlparse(
        "s3://my-bucket/my-path?access_key_id=AKIAIOSFODNN7EXAMPLE&secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY&region=us-west-2"
    )
    password = "my-password"

    repo = S3ResticRepository.from_parsed_uri(parsed_uri, password)

    assert repo.location() == "s3:my-bucket/my-path"
    assert repo.password() == "my-password"
    assert repo.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
    assert repo.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    assert repo.aws_default_region == "us-west-2"


@pytest.mark.unit
def test_validate_lightweight(caplog):
    """
    Test that validate performs lightweight validation without network calls.
    Validation should check format and log configuration but not make S3 API calls.
    """
    repo = S3ResticRepository(
        location="s3:bucket/path",
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret"
    )
    with caplog.at_level("DEBUG"):
        repo.validate()
    # Should log bucket configuration
    assert "S3 repository configured for bucket: bucket" in caplog.text
    # Should log credentials configured
    assert "S3 credentials configured" in caplog.text


@pytest.mark.unit
def test_validate_no_credentials(caplog):
    """
    Test that validate handles missing credentials gracefully.
    Should log that credentials will come from environment or IAM role.
    """
    repo = S3ResticRepository(location="s3:bucket/path")
    with caplog.at_level("DEBUG"):
        repo.validate()
    # Should log that credentials not configured
    assert "S3 credentials not configured - will use environment or IAM role" in caplog.text


@pytest.mark.unit
def test_validate_bucket_extraction(caplog):
    """
    Test that validate method correctly extracts bucket name from location.
    Should log the bucket name without making network calls.
    """
    repo = S3ResticRepository(
        location="s3:test-bucket/path",
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret"
    )
    with caplog.at_level("DEBUG"):
        repo.validate()
    # Should log the extracted bucket name
    assert "S3 repository configured for bucket: test-bucket" in caplog.text


@pytest.mark.unit
def test_endpoint_from_parameter(mock_s3_client):
    """Test that endpoint is set from constructor parameter."""
    repo = S3ResticRepository(
        location="s3:minio.local/bucket",
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret",
        aws_s3_endpoint="http://minio.local:9000"
    )

    assert repo.aws_s3_endpoint == "http://minio.local:9000"

    # Verify it's included in backend_env
    env = repo.backend_env()
    assert env["AWS_S3_ENDPOINT"] == "http://minio.local:9000"


@pytest.mark.unit
def test_endpoint_from_environment(monkeypatch, mock_s3_client):
    """Test that endpoint is retrieved from environment variable."""
    monkeypatch.setenv("AWS_S3_ENDPOINT", "http://localhost:9000")

    repo = S3ResticRepository(
        location="s3:bucket/path",
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret"
    )

    assert repo.aws_s3_endpoint == "http://localhost:9000"

    # Verify it's included in backend_env
    env = repo.backend_env()
    assert env["AWS_S3_ENDPOINT"] == "http://localhost:9000"


@pytest.mark.unit
def test_endpoint_from_credential_manager(mock_s3_client):
    """Test that endpoint is retrieved from credential manager."""
    mock_cred_manager = MagicMock()
    mock_cred_manager.get_repository_backend_credentials.return_value = {
        "access_key_id": "cred_key",
        "secret_access_key": "cred_secret",
        "region": "us-west-2",
        "endpoint": "http://minio.local"
    }

    repo = S3ResticRepository(
        location="s3:bucket/path",
        credential_manager=mock_cred_manager,
        repository_name="test-repo"
    )

    assert repo.aws_s3_endpoint == "http://minio.local"
    assert repo.aws_access_key_id == "cred_key"
    assert repo.aws_secret_access_key == "cred_secret"

    # Verify it's included in backend_env
    env = repo.backend_env()
    assert env["AWS_S3_ENDPOINT"] == "http://minio.local"


@pytest.mark.unit
def test_endpoint_not_set(mock_s3_client):
    """Test that endpoint is not included in backend_env when not configured."""
    repo = S3ResticRepository(
        location="s3:s3.amazonaws.com/bucket",
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret"
    )

    assert repo.aws_s3_endpoint is None

    # Verify it's NOT included in backend_env
    env = repo.backend_env()
    assert "AWS_S3_ENDPOINT" not in env


@pytest.mark.unit
def test_endpoint_parameter_overrides_credential_manager(mock_s3_client):
    """Test that constructor parameter takes precedence over credential manager."""
    mock_cred_manager = MagicMock()
    mock_cred_manager.get_repository_backend_credentials.return_value = {
        "access_key_id": "cred_key",
        "secret_access_key": "cred_secret",
        "endpoint": "http://from-cred-manager"
    }

    repo = S3ResticRepository(
        location="s3:bucket/path",
        aws_s3_endpoint="http://from-parameter",
        credential_manager=mock_cred_manager,
        repository_name="test-repo"
    )

    # Parameter should take precedence
    assert repo.aws_s3_endpoint == "http://from-parameter"
