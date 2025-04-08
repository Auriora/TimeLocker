from typing import Dict, List, Optional, Type

from backup_repository import BackupRepository


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
        self._repository_factories[name][repo_type] = repository_class

    def get_repository_factory(self,
                               name: str,
                               repo_type: str) -> Optional[Type[BackupRepository]]:
        """Get repository class for given name and type"""
        return self._repository_factories.get(name, {}).get(repo_type)

    def list_supported_backends(self) -> Dict[str, List[str]]:
        """List all registered backends and their supported repository types"""
        return {
            name: list(types.keys())
            for name, types in self._repository_factories.items()
        }
