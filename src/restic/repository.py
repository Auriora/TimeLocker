import os

from abc import ABC, abstractmethod
from typing import Optional, Dict
from urllib.parse import urlparse

from restic.errors import RepositoryError, UnsupportedSchemeError
from restic.logging import logger

class Repository(ABC):
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

    @abstractmethod
    def backend_env(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def validate(self):
        pass

    @classmethod
    def from_uri(cls, uri: str, password: Optional[str] = None) -> 'Repository':
        logger.info(f"Parsing repository URI: {cls.redact_sensitive_info(uri)}")
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()

        # TODO Refactor this code to create a repo factory class which Repository child classes can register with indicating which repo class they handle.
        repo_classes = {
            # 's3': S3Repository,
            # 'b2': B2Repository,
            # 'local': LocalRepository,
            # '': LocalRepository
        }

        if scheme not in repo_classes:
            raise UnsupportedSchemeError(f"Unsupported repository scheme: {scheme}") # Implement UnsupportedSchemeError

        repo_class = repo_classes[scheme]
        return repo_class.from_parsed_uri(parsed, password)

    @staticmethod
    def redact_sensitive_info(uri: str) -> str:
        parsed = urlparse(uri)
        redacted_netloc = f"{parsed.hostname}[:*****]" if parsed.username else parsed.netloc
        return parsed._replace(netloc=redacted_netloc).geturl()
