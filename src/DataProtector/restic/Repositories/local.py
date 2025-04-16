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

from DataProtector.restic.logging import logger
from DataProtector.restic.restic_repository import RepositoryError, ResticRepository


class LocalResticRepository(ResticRepository):
    @classmethod
    def from_parsed_uri(cls, parsed_uri, password: Optional[str] = None) -> 'LocalResticRepository':
        if hasattr(parsed_uri, "netloc") and parsed_uri.netloc:
            raise ValueError("parsed_uri must not have a 'netloc' attribute value for a local repository.")

        if not hasattr(parsed_uri, "path") or (hasattr(parsed_uri, "path") and not parsed_uri.path):
            raise ValueError("parsed_uri must have a 'path' attribute value set")

        # Generate the absolute path
        path = os.path.abspath(parsed_uri.path)

        # Return the initialized LocalRepository instance
        return cls(location=path, password=password)

    def backend_env(self) -> Dict[str, str]:
        return {}

    def validate(self):
        logger.info(f"Validating local repository path: {self._location}")
        try:
            if not os.path.isdir(self._location):
                raise RepositoryError(f"Local path does not exist: {self._location}")
        except OSError as e:
            raise RepositoryError(f"Error accessing local repository: {e}")
