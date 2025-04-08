import os

from typing import Dict, Optional

from restic.restic_repository import ResticRepository, RepositoryError
from restic.restic_client import logger

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
        logger.info(f"Validating local repository path: {self.location}")
        try:
            if not os.path.isdir(self.location):
                raise RepositoryError(f"Local path does not exist: {self.location}")
        except OSError as e:
            raise RepositoryError(f"Error accessing local repository: {e}")
