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

import os
from typing import Dict, Optional
from urllib.parse import parse_qs

from boto3 import client

from ..logging import logger
from ..restic_repository import RepositoryError, ResticRepository


class S3ResticRepository(ResticRepository):
    """
    S3-backed restic repository implementation.

    Supports per-repository credential management through the credential manager,
    with fallback to constructor parameters and environment variables.
    """

    def __init__(
            self,
            location: str,
            password: Optional[str] = None,
            aws_access_key_id: Optional[str] = None,
            aws_secret_access_key: Optional[str] = None,
            aws_default_region: Optional[str] = None,
            aws_s3_endpoint: Optional[str] = None,
            credential_manager: Optional[object] = None,
            repository_name: Optional[str] = None,
    ):
        """
        Initialize S3 restic repository.

        Args:
            location: S3 repository location (e.g., 's3:s3.amazonaws.com/bucket/path')
            password: Repository password for encryption
            aws_access_key_id: AWS access key ID (optional, can be retrieved from credential manager or environment)
            aws_secret_access_key: AWS secret access key (optional, can be retrieved from credential manager or environment)
            aws_default_region: AWS region (optional, can be retrieved from credential manager or environment)
            aws_s3_endpoint: S3 endpoint URL for S3-compatible services like MinIO, Wasabi, etc. (optional)
            credential_manager: CredentialManager instance for retrieving stored credentials
            repository_name: Repository name for per-repository credential lookup from credential manager.
                           If provided with credential_manager, will attempt to retrieve repository-specific
                           credentials before falling back to constructor parameters or environment variables.
        """
        # Try to get per-repository credentials from credential manager first
        if credential_manager and repository_name:
            try:
                repo_creds = credential_manager.get_repository_backend_credentials(repository_name, "s3")
                if repo_creds:
                    logger.debug(f"Using per-repository S3 credentials for '{repository_name}'")
                    aws_access_key_id = aws_access_key_id or repo_creds.get("access_key_id")
                    aws_secret_access_key = aws_secret_access_key or repo_creds.get("secret_access_key")
                    aws_default_region = aws_default_region or repo_creds.get("region")
                    aws_s3_endpoint = aws_s3_endpoint or repo_creds.get("endpoint")
            except Exception as e:
                # Log but don't fail - fall back to other credential sources
                logger.debug(f"Could not retrieve per-repository S3 credentials: {e}")

        # Set attributes BEFORE calling super().__init__() because validate() needs them
        self.aws_access_key_id = aws_access_key_id if aws_access_key_id is not None else os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key if aws_secret_access_key is not None else os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_default_region = aws_default_region if aws_default_region is not None else os.getenv("AWS_DEFAULT_REGION")
        self.aws_s3_endpoint = aws_s3_endpoint if aws_s3_endpoint is not None else os.getenv("AWS_S3_ENDPOINT")

        # Call parent __init__ which will trigger validate()
        super().__init__(location, password=password, credential_manager=credential_manager)

    @classmethod
    def from_parsed_uri(
            cls, parsed_uri, password: Optional[str] = None, **kwargs
    ) -> "S3ResticRepository":
        # Handle both standard URI format (s3://host/bucket) and restic format (s3:host/bucket)
        if parsed_uri.netloc:
            # Standard format: s3://s3.region.amazonaws.com/bucket-name
            bucket = parsed_uri.netloc
            path = parsed_uri.path.lstrip("/")
            location = f"s3:{bucket}/{path}"
        else:
            # Restic format: s3:s3.region.amazonaws.com/bucket-name
            # The path contains the full "host/bucket" part
            path_parts = parsed_uri.path.split("/", 1)
            if len(path_parts) >= 2:
                bucket = path_parts[0]  # s3.region.amazonaws.com
                path = path_parts[1]  # bucket-name/optional-path
                location = f"s3:{bucket}/{path}"
            else:
                # Fallback for malformed URIs
                bucket = parsed_uri.path
                path = ""
                # For completely empty bucket/path, ensure trailing slash per test expectations
                location = "s3:/" if (bucket == "" and path == "") else f"s3:{bucket}"

        query_params = parse_qs(parsed_uri.query, keep_blank_values=True)

        return cls(
                location=location,
                password=password,
                aws_access_key_id=query_params.get("access_key_id", [None])[0],
                aws_secret_access_key=query_params.get("secret_access_key", [None])[0],
                aws_default_region=query_params.get("region", [None])[0],
                aws_s3_endpoint=query_params.get("endpoint", [None])[0],
                **kwargs,
        )

    def backend_env(self) -> Dict[str, str]:
        env = {}
        missing_credentials = []
        if not self.aws_access_key_id:
            missing_credentials.append("AWS_ACCESS_KEY_ID")
        if not self.aws_secret_access_key:
            missing_credentials.append("AWS_SECRET_ACCESS_KEY")
        if missing_credentials:
            raise RepositoryError(
                    f"AWS credentials must be set explicitly or in the environment. Missing: {', '.join(missing_credentials)}"
            )
        env["AWS_ACCESS_KEY_ID"] = self.aws_access_key_id
        env["AWS_SECRET_ACCESS_KEY"] = self.aws_secret_access_key
        if self.aws_default_region:
            env["AWS_DEFAULT_REGION"] = self.aws_default_region
        if self.aws_s3_endpoint:
            env["AWS_S3_ENDPOINT"] = self.aws_s3_endpoint
            logger.debug(f"Setting AWS_S3_ENDPOINT to {self.aws_s3_endpoint}")
        return env

    def validate(self):
        """
        Validate S3 repository configuration.

        Performs lightweight validation during initialization:
        - Checks location format is valid
        - Verifies credentials are available

        Note: Does NOT make network calls to check bucket existence during init
        to avoid delays. Bucket validation happens during actual operations.
        """
        logger.info("Validating S3 repository configuration")
        try:
            # If location is empty or root-only, skip validation gracefully
            location_parts = self._location.split(":", 1)[1]  # Remove "s3:" prefix
            if location_parts in ("", "/"):
                logger.warning("S3 location has empty bucket; validation skipped.")
                return

            # Extract bucket name from location for basic format validation
            path_parts = location_parts.split("/")
            host = path_parts[0]
            # More reliable hostname detection for host/bucket style
            # If endpoint is configured, first part is always hostname
            is_hostname = (
                self.aws_s3_endpoint is not None or  # Endpoint configured = host/bucket format
                host.endswith('.amazonaws.com') or
                host.endswith('.backblazeb2.com') or
                ('.' in host and len(host.split('.')) >= 2)  # Any domain name (e.g., minio.local)
            )
            if len(path_parts) >= 2 and is_hostname:
                bucket_name = path_parts[1]
            else:
                bucket_name = path_parts[0]

            if not bucket_name:
                logger.warning("Could not extract S3 bucket from location; validation skipped.")
                return

            # Just log that we have the bucket name - don't make network calls
            logger.debug(f"S3 repository configured for bucket: {bucket_name}")

            # Verify we have credentials (but don't test them with network calls)
            if not self.aws_access_key_id or not self.aws_secret_access_key:
                logger.debug("S3 credentials not configured - will use environment or IAM role")
            else:
                logger.debug("S3 credentials configured")

        except ImportError:
            logger.warning("boto3 is not installed. S3 repository validation skipped.")
        except Exception as e:
            # Don't fail on validation errors during init - let restic handle it
            logger.debug(f"S3 repository validation warning: {str(e)}")

    def is_repository_initialized(self) -> bool:
        """
        Check if the repository is already initialized by attempting to read config.

        Returns:
            bool: True if repository is initialized, False otherwise
        """
        try:
            # Use restic cat config to check if repository exists
            result = self._run_restic_command(["cat", "config"], capture_output=True)
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Repository not initialized or error checking: {e}")
            return False

    def initialize_repository(self, password: Optional[str] = None) -> bool:
        """
        Initialize a new restic repository in S3.

        Args:
            password: Optional password to use for initialization. If not provided,
                     uses the repository's configured password

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Use provided password or fall back to configured password
            if password:
                original_password = self._explicit_password
                self._explicit_password = password
                # Clear cached environment to force regeneration with new password
                self._cached_env = None

            try:
                # Check if repository is already initialized
                if self.is_repository_initialized():
                    logger.warning(f"Repository at {self._location} is already initialized")
                    return True

                # Initialize the repository
                result = self.initialize()

                if result and password:
                    # Store the password in credential manager if available
                    self.store_password(password)

                return result

            finally:
                # Restore original password if we changed it
                if password:
                    self._explicit_password = original_password
                    self._cached_env = None

        except Exception as e:
            logger.error(f"Failed to initialize repository: {e}")
            return False
