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

import logging
from typing import Dict, List, Optional, Type
from urllib.parse import urlparse

from DataProtector.backup_repository import BackupRepository

logger = logging.getLogger("restic")


class BackupManagerError(Exception):
    pass

class BackupManager:
    """Central manager for backup operations and plugin registration"""

    def __init__(self):
        self._repository_factories: Dict[str, Dict[str, Type[BackupRepository]]] = {}

    def register_repository_factory(self,
                                    name: str,
                                    repo_type: str,
                                    repository_class: Type[BackupRepository]):
        """Register a backup repository implementation for a specific type"""
        if name not in self._repository_factories:
            self._repository_factories[name] = {}
        if repo_type in self._repository_factories[name]:
            print(f"Warning: Overwriting existing repository class for {name}/{repo_type}")
        self._repository_factories[name][repo_type] = repository_class

    def get_repository_factory(self,
                               name: str,
                               repo_type: str) -> Optional[Type[BackupRepository]]:
        """Get repository class for given name and type"""
        return self._repository_factories.setdefault(name, {}).get(repo_type)

    def list_registered_backends(self) -> Dict[str, List[str]]:
        """List all registered backends and their supported repository types"""
        return {
            name: list(types.keys())
            for name, types in self._repository_factories.items()
        }

    @classmethod
    def from_uri(cls, uri: str, password: Optional[str] = None) -> 'BackupRepository':
        logger.info(f"Parsing repository URI: {cls.redact_sensitive_info(uri.replace('{', '{{').replace('}', '}}'))}")  # import re
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()

        # Repository classes are registered here
        repo_classes = getattr(cls.from_uri, 'repo_classes', {
            's3': None,  # Will be set in tests
            'b2': None,
            'local': None,
            '': None
        })

        if scheme not in repo_classes:
            raise BackupManagerError(f"Unsupported repository scheme: {scheme}") # Implement UnsupportedSchemeError

        repo_class = repo_classes[scheme]
        return repo_class.from_parsed_uri(parsed, password)

    @staticmethod
    def redact_sensitive_info(uri: str) -> str:
        parsed = urlparse(uri)
        redacted_netloc = f"{parsed.hostname}[:*****]" if parsed.username else parsed.netloc
        return parsed._replace(netloc=redacted_netloc).geturl()
