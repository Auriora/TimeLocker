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

from TimeLocker.restic.logging import logger
from TimeLocker.restic.restic_repository import RepositoryError, ResticRepository


class S3ResticRepository(ResticRepository):
    def __init__(
        self,
        location: str,
        password: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_default_region: Optional[str] = None,
    ):
        super().__init__(location, password)
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv(
            "AWS_SECRET_ACCESS_KEY"
        )
        self.aws_default_region = aws_default_region or os.getenv("AWS_DEFAULT_REGION")

    @classmethod
    def from_parsed_uri(
        cls, parsed_uri, password: Optional[str] = None
    ) -> "S3ResticRepository":
        bucket = parsed_uri.netloc
        path = parsed_uri.path.lstrip("/")
        location = f"s3:{bucket}/{path}"
        query_params = parse_qs(parsed_uri.query)

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
            bucket_name = self._location.split(":")[1].split("/")[0]
            s3.head_bucket(Bucket=bucket_name)
            logger.info(f"Successfully validated S3 bucket: {bucket_name}")
        except ImportError:
            logger.warning("boto3 is not installed. S3 repository validation skipped.")
        except Exception as e:
            raise RepositoryError(f"Failed to validate S3 repository: {str(e)}")
