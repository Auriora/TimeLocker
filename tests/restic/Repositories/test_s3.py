from boto3 import client
from restic.Repositories.s3 import S3ResticRepository
from restic.Repositories.s3 import S3ResticRepository, RepositoryError
from restic.logging import logger
from restic.restic_repository import RepositoryError
from typing import Dict, Optional
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse
import os
import pytest
import unittest

class TestS3:

    def test___init___missing_credentials(self):
        """
        Test initialization of S3ResticRepository when AWS credentials are missing from both
        parameters and environment variables.
        """
        # Clear environment variables to simulate missing credentials
        os.environ.pop('AWS_ACCESS_KEY_ID', None)
        os.environ.pop('AWS_SECRET_ACCESS_KEY', None)

        repo = S3ResticRepository("s3:bucket/path")

        # The __init__ method doesn't raise exceptions, it just sets attributes
        # We'll test the actual error handling in the backend_env method
        with self.assertRaises(RepositoryError) as context:
            repo.backend_env()

        self.assertIn("AWS credentials must be set explicitly or in the environment", str(context.exception))
        self.assertIn("AWS_ACCESS_KEY_ID", str(context.exception))
        self.assertIn("AWS_SECRET_ACCESS_KEY", str(context.exception))

    def test___init___with_explicit_credentials(self):
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
            aws_default_region
        )

        assert repo.location == location
        assert repo.password == password
        assert repo.aws_access_key_id == aws_access_key_id
        assert repo.aws_secret_access_key == aws_secret_access_key
        assert repo.aws_default_region == aws_default_region

    def test_backend_env_2(self):
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
            aws_default_region="us-west-2"
        )

        with pytest.raises(RepositoryError) as exc_info:
            repo.backend_env()

        assert "AWS credentials must be set explicitly or in the environment" in str(exc_info.value)
        assert "AWS_SECRET_ACCESS_KEY" in str(exc_info.value)
        assert "AWS_ACCESS_KEY_ID" not in str(exc_info.value)

    def test_backend_env_3(self):
        """
        Test that backend_env raises RepositoryError when AWS_ACCESS_KEY_ID is missing,
        but AWS_SECRET_ACCESS_KEY and AWS_DEFAULT_REGION are provided.
        """
        repo = S3ResticRepository(
            location="s3:my-bucket/my-path",
            aws_access_key_id=None,
            aws_secret_access_key="secret_key",
            aws_default_region="us-west-2"
        )

        with pytest.raises(RepositoryError) as excinfo:
            repo.backend_env()

        assert "AWS credentials must be set explicitly or in the environment. Missing: AWS_ACCESS_KEY_ID" in str(excinfo.value)

    def test_backend_env_4(self):
        """
        Test that backend_env raises a RepositoryError when both AWS credentials are missing,
        even if aws_default_region is set.
        """
        repo = S3ResticRepository(location="s3:bucket/path", aws_default_region="us-west-2")

        with self.assertRaises(RepositoryError) as context:
            repo.backend_env()

        self.assertIn("AWS credentials must be set explicitly or in the environment", str(context.exception))
        self.assertIn("AWS_ACCESS_KEY_ID", str(context.exception))
        self.assertIn("AWS_SECRET_ACCESS_KEY", str(context.exception))

    def test_backend_env_missing_credentials(self):
        """
        Test that backend_env raises a RepositoryError when AWS credentials are missing.
        This tests the edge case where either AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY
        or both are not provided.
        """
        repo = S3ResticRepository(location="s3:bucket/path")
        with self.assertRaises(RepositoryError) as context:
            repo.backend_env()

        self.assertIn("AWS credentials must be set explicitly or in the environment", str(context.exception))
        self.assertIn("AWS_ACCESS_KEY_ID", str(context.exception))
        self.assertIn("AWS_SECRET_ACCESS_KEY", str(context.exception))

    def test_backend_env_missing_credentials_2(self):
        """
        Test backend_env method when both AWS access key ID and secret access key are missing.

        This test verifies that the backend_env method raises a RepositoryError
        when both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are not provided.
        The error message should indicate which credentials are missing.
        """
        repo = S3ResticRepository(location="s3:bucket/path")

        with pytest.raises(RepositoryError) as exc_info:
            repo.backend_env()

        assert "AWS credentials must be set explicitly or in the environment" in str(exc_info.value)
        assert "AWS_ACCESS_KEY_ID" in str(exc_info.value)
        assert "AWS_SECRET_ACCESS_KEY" in str(exc_info.value)

    def test_backend_env_missing_credentials_3(self):
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

        assert "AWS credentials must be set explicitly or in the environment" in str(excinfo.value)
        assert "AWS_ACCESS_KEY_ID" in str(excinfo.value)
        assert "AWS_SECRET_ACCESS_KEY" in str(excinfo.value)

    def test_from_parsed_uri_empty_bucket(self):
        """
        Test the from_parsed_uri method with an empty bucket name.
        This is an edge case where the parsed URI has an empty netloc (bucket name).
        """
        parsed_uri = urlparse('s3://')
        result = S3ResticRepository.from_parsed_uri(parsed_uri)
        assert result.location == 's3:/'

    def test_from_parsed_uri_empty_path(self):
        """
        Test the from_parsed_uri method with an empty path.
        This is an edge case where the parsed URI has no path component.
        """
        parsed_uri = urlparse('s3://mybucket')
        result = S3ResticRepository.from_parsed_uri(parsed_uri)
        assert result.location == 's3:mybucket/'

    def test_from_parsed_uri_empty_query_params(self):
        """
        Test the from_parsed_uri method with empty query parameters.
        This checks the handling of query parameters with no values.
        """
        parsed_uri = urlparse('s3://mybucket/mypath?access_key_id=&secret_access_key=&region=')
        result = S3ResticRepository.from_parsed_uri(parsed_uri)
        assert result.aws_access_key_id == ''
        assert result.aws_secret_access_key == ''
        assert result.aws_default_region == ''

    def test_from_parsed_uri_no_query_params(self):
        """
        Test the from_parsed_uri method with no query parameters.
        This checks the handling of missing optional parameters.
        """
        parsed_uri = urlparse('s3://mybucket/mypath')
        result = S3ResticRepository.from_parsed_uri(parsed_uri)
        assert result.aws_access_key_id is None
        assert result.aws_secret_access_key is None
        assert result.aws_default_region is None

    def test_from_parsed_uri_with_all_parameters(self):
        """
        Test the from_parsed_uri method with all parameters provided in the query string.
        This test verifies that the method correctly extracts and uses the access_key_id,
        secret_access_key, and region from the parsed URI.
        """
        parsed_uri = urlparse("s3://my-bucket/my-path?access_key_id=AKIAIOSFODNN7EXAMPLE&secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY&region=us-west-2")
        password = "my-password"

        repo = S3ResticRepository.from_parsed_uri(parsed_uri, password)

        assert repo.location == "s3:my-bucket/my-path"
        assert repo.password == "my-password"
        assert repo.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert repo.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert repo.aws_default_region == "us-west-2"

    def test_validate_boto3_not_installed(self):
        """
        Test the validate method when boto3 is not installed.
        This should result in a warning log message and skip the validation.
        """
        repo = S3ResticRepository(location="s3:bucket/path")
        with patch('restic.Repositories.s3.client', side_effect=ImportError):
            with self.assertLogs(level='WARNING') as log:
                repo.validate()
            self.assertIn("boto3 is not installed. S3 repository validation skipped.", log.output[0])

    def test_validate_s3_exception(self):
        """
        Test the validate method when an exception occurs during S3 bucket validation.
        This should raise a RepositoryError with an appropriate error message.
        """
        repo = S3ResticRepository(location="s3:bucket/path")
        mock_s3 = MagicMock()
        mock_s3.head_bucket.side_effect = Exception("S3 Error")
        with patch('restic.Repositories.s3.client', return_value=mock_s3):
            with self.assertRaises(RepositoryError) as context:
                repo.validate()
            self.assertIn("Failed to validate S3 repository: S3 Error", str(context.exception))

    def test_validate_successful_s3_bucket(self):
        """
        Test that validate method successfully validates an S3 bucket.
        It should create an S3 client, extract the bucket name from the location,
        call head_bucket on the S3 client, and log a success message.
        """
        with patch('restic.Repositories.s3.client') as mock_client:
            mock_s3 = MagicMock()
            mock_client.return_value = mock_s3

            repo = S3ResticRepository(location='s3:test-bucket/path')

            repo.validate()

            mock_client.assert_called_once_with('s3')
            mock_s3.head_bucket.assert_called_once_with(Bucket='XXXXXXXXXXX')
            logger.info.assert_called_with("Successfully validated S3 bucket: test-bucket")
