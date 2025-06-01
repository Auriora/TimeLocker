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
import time
from typing import Dict, List, Optional, Type, Callable
from urllib.parse import urlparse

from TimeLocker.backup_repository import BackupRepository
from TimeLocker.backup_target import BackupTarget

try:
    from TimeLocker.performance.profiler import profile_operation
    from TimeLocker.performance.metrics import start_operation_tracking, update_operation_tracking, complete_operation_tracking
except ImportError:
    # Fallback for when performance module is not available
    def profile_operation(name):
        def decorator(func):
            return func

        return decorator


    def start_operation_tracking(operation_id, operation_type, metadata=None):
        return None


    def update_operation_tracking(operation_id, files_processed=None, bytes_processed=None, errors_count=None, metadata=None):
        pass


    def complete_operation_tracking(operation_id):
        return None

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

        # Import repository classes with graceful handling of optional dependencies
        from TimeLocker.restic.Repositories.local import LocalResticRepository

        repo_classes = {
                'local': LocalResticRepository,
                '':      LocalResticRepository  # Default to local for empty scheme
        }

        # Try to import optional cloud storage repositories
        try:
            from TimeLocker.restic.Repositories.s3 import S3ResticRepository
            repo_classes['s3'] = S3ResticRepository
        except ImportError:
            logger.warning("S3 support not available - missing dependencies")

        try:
            from TimeLocker.restic.Repositories.b2 import B2ResticRepository
            repo_classes['b2'] = B2ResticRepository
        except ImportError:
            logger.warning("B2 support not available - missing dependencies")

        if scheme not in repo_classes:
            raise BackupManagerError(f"Unsupported repository scheme: {scheme}")

        repo_class = repo_classes[scheme]
        return repo_class.from_parsed_uri(parsed, password)

    @staticmethod
    def redact_sensitive_info(uri: str) -> str:
        parsed = urlparse(uri)
        redacted_netloc = f"{parsed.hostname}[:*****]" if parsed.username else parsed.netloc
        return parsed._replace(netloc=redacted_netloc).geturl()

    @profile_operation("execute_backup_with_retry")
    def execute_backup_with_retry(self,
                                  repository: BackupRepository,
                                  targets: List[BackupTarget],
                                  tags: Optional[List[str]] = None,
                                  max_retries: int = 3,
                                  retry_delay: float = 1.0,
                                  backoff_multiplier: float = 2.0) -> Dict:
        """
        Execute backup with retry mechanism and exponential backoff

        Args:
            repository: Repository to backup to
            targets: List of backup targets
            tags: Optional tags for the backup
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff

        Returns:
            Dict: Backup result information

        Raises:
            BackupManagerError: If backup fails after all retries
        """
        operation_id = f"backup_retry_{id(repository)}_{time.time()}"
        metrics = start_operation_tracking(operation_id, "backup_with_retry",
                                           metadata={"max_retries": max_retries, "targets_count": len(targets)})

        last_exception = None
        current_delay = retry_delay

        try:
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Backup attempt {attempt + 1}/{max_retries + 1}")
                    update_operation_tracking(operation_id, metadata={"current_attempt": attempt + 1})

                    # Validate targets before attempting backup
                    for target in targets:
                        target.validate()

                    # Execute backup
                    result = repository.backup_target(targets, tags)

                    # Verify backup if successful
                    if result and "snapshot_id" in result:
                        if self.verify_backup_integrity(repository, result["snapshot_id"]):
                            logger.info(f"Backup completed successfully on attempt {attempt + 1}")
                            update_operation_tracking(operation_id, metadata={"successful_attempt": attempt + 1})
                            return result
                        else:
                            raise BackupManagerError("Backup verification failed")

                    return result

                except Exception as e:
                    last_exception = e
                    logger.warning(f"Backup attempt {attempt + 1} failed: {e}")
                    update_operation_tracking(operation_id, errors_count=attempt + 1)

                    if attempt < max_retries:
                        logger.info(f"Retrying in {current_delay} seconds...")
                        time.sleep(current_delay)
                        current_delay *= backoff_multiplier
                    else:
                        logger.error(f"All backup attempts failed. Last error: {e}")

            raise BackupManagerError(f"Backup failed after {max_retries + 1} attempts: {last_exception}")

        finally:
            complete_operation_tracking(operation_id)

    def verify_backup_integrity(self,
                                repository: BackupRepository,
                                snapshot_id: Optional[str] = None) -> bool:
        """
        Verify backup integrity with enhanced checking

        Args:
            repository: Repository to verify
            snapshot_id: Specific snapshot to verify (optional)

        Returns:
            bool: True if verification successful
        """
        try:
            logger.info(f"Verifying backup integrity{f' for snapshot {snapshot_id}' if snapshot_id else ''}")

            # Use repository's verify method
            if hasattr(repository, 'verify_backup'):
                return repository.verify_backup(snapshot_id)
            else:
                # Fallback to basic check method
                return repository.check()

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def create_incremental_backup(self,
                                  repository: BackupRepository,
                                  targets: List[BackupTarget],
                                  parent_snapshot_id: Optional[str] = None,
                                  tags: Optional[List[str]] = None) -> Dict:
        """
        Create an incremental backup based on a parent snapshot

        Args:
            repository: Repository to backup to
            targets: List of backup targets
            parent_snapshot_id: ID of parent snapshot for incremental backup
            tags: Optional tags for the backup

        Returns:
            Dict: Backup result information
        """
        try:
            # Add incremental backup tag
            backup_tags = list(tags or [])
            backup_tags.append("incremental")

            if parent_snapshot_id:
                backup_tags.append(f"parent:{parent_snapshot_id}")
                logger.info(f"Creating incremental backup based on snapshot {parent_snapshot_id}")
            else:
                logger.info("Creating incremental backup (restic will auto-detect parent)")

            # Execute backup with retry
            return self.execute_backup_with_retry(repository, targets, backup_tags)

        except Exception as e:
            logger.error(f"Incremental backup failed: {e}")
            raise BackupManagerError(f"Incremental backup failed: {e}")

    def create_full_backup(self,
                           repository: BackupRepository,
                           targets: List[BackupTarget],
                           tags: Optional[List[str]] = None) -> Dict:
        """
        Create a full backup (first backup or forced full backup)

        Args:
            repository: Repository to backup to
            targets: List of backup targets
            tags: Optional tags for the backup

        Returns:
            Dict: Backup result information
        """
        try:
            # Add full backup tag
            backup_tags = list(tags or [])
            backup_tags.append("full")

            logger.info("Creating full backup")

            # Execute backup with retry
            return self.execute_backup_with_retry(repository, targets, backup_tags)

        except Exception as e:
            logger.error(f"Full backup failed: {e}")
            raise BackupManagerError(f"Full backup failed: {e}")
