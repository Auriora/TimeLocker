"""
Repository Concurrency Manager for TimeLocker

This module provides concurrent operation management for repository operations
with semaphore-based limiting and exclusive locking to prevent conflicts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class LockInfo:
    """Information about a repository lock."""
    repository_name: str
    acquired_at: datetime
    holder: str  # Identifier of the lock holder (e.g., operation name)
    lock: asyncio.Lock = field(repr=False)


@dataclass
class ConcurrencyStats:
    """Statistics about concurrent operations."""
    total_locks_acquired: int = 0
    total_locks_released: int = 0
    total_validations_started: int = 0
    total_validations_completed: int = 0
    current_active_locks: int = 0
    current_active_validations: int = 0
    max_concurrent_validations_reached: int = 0


class RepositoryConcurrencyManager:
    """
    Manages concurrent repository operations for desktop usage.
    
    Provides:
    - Semaphore-based limiting for validation operations (up to 3 parallel)
    - Exclusive locking for repository operations to prevent conflicts
    - Lock timeout and deadlock detection
    - Concurrency statistics and monitoring
    """
    
    def __init__(self, max_concurrent_validations: int = 3):
        """
        Initialize concurrency manager.
        
        Args:
            max_concurrent_validations: Maximum number of parallel validation operations
        """
        self._max_concurrent_validations = max_concurrent_validations
        self._validation_semaphore = asyncio.Semaphore(max_concurrent_validations)
        self._operation_locks: Dict[str, LockInfo] = {}
        self._stats = ConcurrencyStats()
        self._lock_timeout = 300.0  # 5 minutes default timeout
        
        logger.debug(
            f"RepositoryConcurrencyManager initialized with "
            f"max_concurrent_validations={max_concurrent_validations}"
        )
    
    @asynccontextmanager
    async def acquire_repository_lock(
        self,
        repository_name: str,
        operation: str = "unknown",
        timeout: Optional[float] = None
    ):
        """
        Acquire exclusive lock for repository operations.
        
        This is a context manager that ensures the lock is properly released
        even if an exception occurs.
        
        Args:
            repository_name: Name of the repository to lock
            operation: Name of the operation acquiring the lock
            timeout: Optional timeout in seconds (uses default if not provided)
            
        Yields:
            None
            
        Raises:
            asyncio.TimeoutError: If lock cannot be acquired within timeout
            
        Example:
            async with manager.acquire_repository_lock("my-repo", "backup"):
                # Perform repository operation
                pass
        """
        lock = await self._get_or_create_lock(repository_name)
        timeout_value = timeout or self._lock_timeout
        
        try:
            # Try to acquire lock with timeout
            await asyncio.wait_for(lock.acquire(), timeout=timeout_value)
            
            # Record lock acquisition
            lock_info = LockInfo(
                repository_name=repository_name,
                acquired_at=datetime.utcnow(),
                holder=operation,
                lock=lock
            )
            self._operation_locks[repository_name] = lock_info
            self._stats.total_locks_acquired += 1
            self._stats.current_active_locks += 1
            
            logger.debug(
                f"Lock acquired for repository '{repository_name}' by operation '{operation}'"
            )
            
            yield
            
        except asyncio.TimeoutError:
            logger.error(
                f"Failed to acquire lock for repository '{repository_name}' "
                f"within {timeout_value}s timeout"
            )
            raise
            
        finally:
            # Release lock
            if lock.locked():
                lock.release()
                self._stats.total_locks_released += 1
                self._stats.current_active_locks -= 1
                
                # Remove lock info
                self._operation_locks.pop(repository_name, None)
                
                logger.debug(
                    f"Lock released for repository '{repository_name}' by operation '{operation}'"
                )
    
    async def _get_or_create_lock(self, repository_name: str) -> asyncio.Lock:
        """
        Get existing lock or create new one for repository.
        
        Args:
            repository_name: Repository name
            
        Returns:
            asyncio.Lock: Lock for the repository
        """
        # Check if lock already exists
        lock_info = self._operation_locks.get(repository_name)
        if lock_info:
            return lock_info.lock
        
        # Create new lock
        return asyncio.Lock()
    
    @asynccontextmanager
    async def limit_concurrent_validations(self, repository_name: Optional[str] = None):
        """
        Limit concurrent validation operations using semaphore.
        
        This context manager ensures that no more than the configured maximum
        number of validation operations run concurrently.
        
        Args:
            repository_name: Optional repository name for logging
            
        Yields:
            None
            
        Example:
            async with manager.limit_concurrent_validations("my-repo"):
                # Perform validation
                pass
        """
        self._stats.total_validations_started += 1
        
        try:
            async with self._validation_semaphore:
                self._stats.current_active_validations += 1
                
                # Track maximum concurrent validations
                if self._stats.current_active_validations > self._stats.max_concurrent_validations_reached:
                    self._stats.max_concurrent_validations_reached = self._stats.current_active_validations
                
                logger.debug(
                    f"Validation started for repository '{repository_name or 'unknown'}' "
                    f"({self._stats.current_active_validations}/{self._max_concurrent_validations} active)"
                )
                
                yield
                
        finally:
            self._stats.current_active_validations -= 1
            self._stats.total_validations_completed += 1
            
            logger.debug(
                f"Validation completed for repository '{repository_name or 'unknown'}' "
                f"({self._stats.current_active_validations}/{self._max_concurrent_validations} active)"
            )
    
    async def validate_with_concurrency_limit(
        self,
        repositories: List[Any],
        validation_func: Any
    ) -> List[Any]:
        """
        Validate repositories with desktop-appropriate concurrency limits.
        
        Args:
            repositories: List of repositories to validate
            validation_func: Async function to validate a single repository
            
        Returns:
            List[Any]: List of validation results (or exceptions)
        """
        async def validate_single(repository: Any) -> Any:
            """Validate single repository with concurrency limit."""
            async with self.limit_concurrent_validations(
                repository.name if hasattr(repository, 'name') else None
            ):
                try:
                    return await validation_func(repository)
                except Exception as e:
                    logger.error(f"Validation failed for repository: {e}")
                    return e
        
        # Create tasks for all repositories
        tasks = [validate_single(repo) for repo in repositories]
        
        # Execute with concurrency limit
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    def is_repository_locked(self, repository_name: str) -> bool:
        """
        Check if a repository is currently locked.
        
        Args:
            repository_name: Repository name
            
        Returns:
            bool: True if repository is locked, False otherwise
        """
        lock_info = self._operation_locks.get(repository_name)
        return lock_info is not None and lock_info.lock.locked()
    
    def get_lock_info(self, repository_name: str) -> Optional[LockInfo]:
        """
        Get information about a repository lock.
        
        Args:
            repository_name: Repository name
            
        Returns:
            Optional[LockInfo]: Lock information if locked, None otherwise
        """
        return self._operation_locks.get(repository_name)
    
    def get_all_locks(self) -> List[LockInfo]:
        """
        Get information about all active locks.
        
        Returns:
            List[LockInfo]: List of active lock information
        """
        return list(self._operation_locks.values())
    
    def get_stale_locks(self, max_age_seconds: float = 300.0) -> List[LockInfo]:
        """
        Get locks that have been held longer than the specified age.
        
        This can help identify potential deadlocks or stuck operations.
        
        Args:
            max_age_seconds: Maximum age in seconds before a lock is considered stale
            
        Returns:
            List[LockInfo]: List of stale locks
        """
        now = datetime.utcnow()
        stale_locks = []
        
        for lock_info in self._operation_locks.values():
            age = (now - lock_info.acquired_at).total_seconds()
            if age > max_age_seconds:
                stale_locks.append(lock_info)
        
        return stale_locks
    
    async def force_release_lock(self, repository_name: str) -> bool:
        """
        Force release a repository lock.
        
        This should only be used in exceptional circumstances, such as
        recovering from a deadlock or stuck operation.
        
        Args:
            repository_name: Repository name
            
        Returns:
            bool: True if lock was released, False if no lock existed
        """
        lock_info = self._operation_locks.get(repository_name)
        if not lock_info:
            return False
        
        try:
            if lock_info.lock.locked():
                lock_info.lock.release()
                self._stats.total_locks_released += 1
                self._stats.current_active_locks -= 1
            
            self._operation_locks.pop(repository_name, None)
            
            logger.warning(f"Force released lock for repository '{repository_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to force release lock for repository '{repository_name}': {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get concurrency statistics.
        
        Returns:
            Dict[str, Any]: Concurrency statistics
        """
        return {
            'max_concurrent_validations': self._max_concurrent_validations,
            'total_locks_acquired': self._stats.total_locks_acquired,
            'total_locks_released': self._stats.total_locks_released,
            'total_validations_started': self._stats.total_validations_started,
            'total_validations_completed': self._stats.total_validations_completed,
            'current_active_locks': self._stats.current_active_locks,
            'current_active_validations': self._stats.current_active_validations,
            'max_concurrent_validations_reached': self._stats.max_concurrent_validations_reached,
            'lock_timeout_seconds': self._lock_timeout
        }
    
    def reset_statistics(self) -> None:
        """Reset concurrency statistics."""
        self._stats = ConcurrencyStats()
        logger.debug("Concurrency statistics reset")
    
    def set_lock_timeout(self, timeout_seconds: float) -> None:
        """
        Set the default lock timeout.
        
        Args:
            timeout_seconds: Timeout in seconds
        """
        self._lock_timeout = timeout_seconds
        logger.debug(f"Lock timeout set to {timeout_seconds}s")
    
    def set_max_concurrent_validations(self, max_validations: int) -> None:
        """
        Update the maximum number of concurrent validations.
        
        Note: This creates a new semaphore, so it should only be called
        when no validations are active.
        
        Args:
            max_validations: Maximum number of concurrent validations
        """
        if self._stats.current_active_validations > 0:
            logger.warning(
                f"Changing max_concurrent_validations while {self._stats.current_active_validations} "
                "validations are active. This may cause unexpected behavior."
            )
        
        self._max_concurrent_validations = max_validations
        self._validation_semaphore = asyncio.Semaphore(max_validations)
        
        logger.info(f"Maximum concurrent validations set to {max_validations}")
    
    async def wait_for_all_operations(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all active operations to complete.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            bool: True if all operations completed, False if timeout occurred
        """
        start_time = datetime.utcnow()
        
        while self._stats.current_active_locks > 0 or self._stats.current_active_validations > 0:
            if timeout:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= timeout:
                    logger.warning(
                        f"Timeout waiting for operations to complete. "
                        f"Active locks: {self._stats.current_active_locks}, "
                        f"Active validations: {self._stats.current_active_validations}"
                    )
                    return False
            
            await asyncio.sleep(0.1)
        
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of concurrency manager.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        stale_locks = self.get_stale_locks()
        
        return {
            'healthy': len(stale_locks) == 0,
            'active_locks': self._stats.current_active_locks,
            'active_validations': self._stats.current_active_validations,
            'stale_locks_count': len(stale_locks),
            'stale_locks': [
                {
                    'repository': lock.repository_name,
                    'holder': lock.holder,
                    'age_seconds': (datetime.utcnow() - lock.acquired_at).total_seconds()
                }
                for lock in stale_locks
            ]
        }
