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

from b2sdk.v2 import B2Api, InMemoryAccountInfo

from TimeLocker.restic.logging import logger
from TimeLocker.restic.restic_repository import RepositoryError, ResticRepository


class B2ResticRepository(ResticRepository):
    def __init__(self, location: str, password: Optional[str] = None,
                 b2_account_id: Optional[str] = None,
                 b2_account_key: Optional[str] = None):
        super().__init__(location, password)
        self.b2_account_id = b2_account_id or os.getenv("B2_ACCOUNT_ID")
        self.b2_account_key = b2_account_key or os.getenv("B2_ACCOUNT_KEY")

    @classmethod
    def from_parsed_uri(cls, parsed_uri, password: Optional[str] = None) -> 'B2ResticRepository':
        bucket = parsed_uri.netloc
        path = parsed_uri.path.lstrip('/')
        location = f"b2:{bucket}/{path}"
        query_params = parse_qs(parsed_uri.query)

        return cls(
            location=location,
            password=password,
            b2_account_id=query_params.get('account_id', [None])[0],
            b2_account_key=query_params.get('account_key', [None])[0]
        )

    def backend_env(self) -> Dict[str, str]:
        env = {}
        missing_credentials = []
        if not self.b2_account_id:
            missing_credentials.append("B2_ACCOUNT_ID")
        if not self.b2_account_key:
            missing_credentials.append("B2_ACCOUNT_KEY")
        if missing_credentials:
            raise RepositoryError(f"B2 credentials must be set explicitly or in the environment. Missing: {', '.join(missing_credentials)}")
        env["B2_ACCOUNT_ID"] = self.b2_account_id
        env["B2_ACCOUNT_KEY"] = self.b2_account_key
        return env

    def validate(self):
        logger.info("Validating B2 repository configuration")
        if not self.b2_account_id or not self.b2_account_key:
            raise RepositoryError("B2 credentials are missing or incomplete.")
        try:
            info = InMemoryAccountInfo()
            b2_api = B2Api(info)
            b2_api.authorize_account("production", self.b2_account_id, self.b2_account_key)
            bucket_name = self._location.split(':')[1].split('/')[0]
            bucket = b2_api.get_bucket_by_name(bucket_name)
            logger.info(f"Successfully validated B2 bucket: {bucket_name}")
        except Exception as e:
            raise RepositoryError(f"Failed to validate B2 repository: {str(e)}")
