import os
from abc import abstractmethod

from typing import Optional, Dict
from urllib.parse import urlparse
from backup_repository import BackupRepository

from restic.errors import RepositoryError, UnsupportedSchemeError
from restic.logging import logger

class ResticRepository(BackupRepository):
    def __init__(self, location: str, password: Optional[str] = None):
        logger.info(f"Initializing repository at location: {location}")
        self.location = location
        self._explicit_password = password
        self._cached_env = None

    def restic_password(self) -> Optional[str]:
        return self._explicit_password or os.getenv("RESTIC_PASSWORD")

    def to_env(self) -> Dict[str, str]:
        if self._cached_env:
            return self._cached_env

        env = {}
        pwd = self.restic_password()
        if not pwd:
            raise RepositoryError("RESTIC_PASSWORD must be set explicitly or in the environment.")
        env["RESTIC_PASSWORD"] = pwd
        env.update(self.backend_env())
        logger.debug("Constructed environment for restic")
        self._cached_env = env
        return env

    @-abstractmethod
    def backend_env(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def validate(self):
        pass

