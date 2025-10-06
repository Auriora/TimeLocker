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

from ..logging import logger
from ..restic_repository import RepositoryError, ResticRepository


class B2ResticRepository(ResticRepository):
    """
    Backblaze B2-backed restic repository implementation.

    Supports per-repository credential management through the credential manager,
    with fallback to constructor parameters and environment variables.
    """

    def __init__(self, location: str, password: Optional[str] = None,
                 b2_account_id: Optional[str] = None,
                 b2_account_key: Optional[str] = None,
                 credential_manager: Optional[object] = None,
                 repository_name: Optional[str] = None):
        """
        Initialize B2 restic repository.

        Args:
            location: B2 repository location (e.g., 'b2:bucket-name/path')
            password: Repository password for encryption
            b2_account_id: B2 account ID (optional, can be retrieved from credential manager or environment)
            b2_account_key: B2 account key (optional, can be retrieved from credential manager or environment)
            credential_manager: CredentialManager instance for retrieving stored credentials
            repository_name: Repository name for per-repository credential lookup from credential manager.
                           If provided with credential_manager, will attempt to retrieve repository-specific
                           credentials before falling back to constructor parameters or environment variables.
        """
        super().__init__(location, password, credential_manager=credential_manager)

        # Try to get per-repository credentials from credential manager first
        if credential_manager and repository_name:
            try:
                repo_creds = credential_manager.get_repository_backend_credentials(repository_name, "b2")
                if repo_creds:
                    logger.debug(f"Using per-repository B2 credentials for '{repository_name}'")
                    b2_account_id = b2_account_id or repo_creds.get("account_id")
                    b2_account_key = b2_account_key or repo_creds.get("account_key")
            except Exception as e:
                # Log but don't fail - fall back to other credential sources
                logger.debug(f"Could not retrieve per-repository B2 credentials: {e}")

        # Fall back to constructor parameters or environment variables
        self.b2_account_id = b2_account_id or os.getenv("B2_ACCOUNT_ID")
        self.b2_account_key = b2_account_key or os.getenv("B2_ACCOUNT_KEY")

    @classmethod
    def from_parsed_uri(cls, parsed_uri, password: Optional[str] = None, **kwargs) -> 'B2ResticRepository':
        bucket = parsed_uri.netloc
        path = parsed_uri.path.lstrip('/')
        location = f"b2:{bucket}/{path}"
        query_params = parse_qs(parsed_uri.query)

        return cls(
            location=location,
            password=password,
            b2_account_id=query_params.get('account_id', [None])[0],
            b2_account_key=query_params.get('account_key', [None])[0],
            **kwargs
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
