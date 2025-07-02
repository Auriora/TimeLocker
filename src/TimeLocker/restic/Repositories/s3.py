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
    def __init__(
            self,
            location: str,
            password: Optional[str] = None,
            aws_access_key_id: Optional[str] = None,
            aws_secret_access_key: Optional[str] = None,
            aws_default_region: Optional[str] = None,
    ):
        super().__init__(location, password=password)
        self.aws_access_key_id = aws_access_key_id if aws_access_key_id is not None else os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key if aws_secret_access_key is not None else os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_default_region = aws_default_region if aws_default_region is not None else os.getenv("AWS_DEFAULT_REGION")

    @classmethod
    def from_parsed_uri(
            cls, parsed_uri, password: Optional[str] = None
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
                location = f"s3:{bucket}"

        query_params = parse_qs(parsed_uri.query, keep_blank_values=True)

        return cls(
                location=location,
                password=password,
                aws_access_key_id=query_params.get("access_key_id", [None])[0],
                aws_secret_access_key=query_params.get("secret_access_key", [None])[0],
                aws_default_region=query_params.get("region", [None])[0],
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
        return env

    def validate(self):
        logger.info("Validating S3 repository configuration")
        try:
            s3 = client("s3")
            # Extract bucket name from restic-style location: s3:s3.region.amazonaws.com/bucket-name
            location_parts = self._location.split(":", 1)[1]  # Remove "s3:" prefix
            # Split by "/" and get the last part (bucket name)
            path_parts = location_parts.split("/")
            if len(path_parts) >= 2:
                bucket_name = path_parts[1]  # bucket-name is after the hostname
            else:
                bucket_name = path_parts[0]  # fallback if no path separator

            if not bucket_name:
                raise RepositoryError("Could not extract bucket name from S3 location")

            s3.head_bucket(Bucket=bucket_name)
            logger.info(f"Successfully validated S3 bucket: {bucket_name}")
        except ImportError:
            logger.warning("boto3 is not installed. S3 repository validation skipped.")
        except Exception as e:
            raise RepositoryError(f"Failed to validate S3 repository: {str(e)}")
