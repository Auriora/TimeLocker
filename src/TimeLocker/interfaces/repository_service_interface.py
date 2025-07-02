"""
Repository Service Interface for TimeLocker

This interface defines the contract for advanced repository management operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path

from .data_models import RepositoryInfo, OperationStatus
from .repository_interface import IRepository


class IRepositoryService(ABC):
    """Interface for advanced repository management operations"""

    @abstractmethod
    def check_repository(self, repository: IRepository) -> Dict[str, Any]:
        """
        Check repository integrity
        
        Args:
            repository: Repository to check
            
        Returns:
            Dictionary with check results and statistics
        """
        pass

    @abstractmethod
    def get_repository_stats(self, repository: IRepository) -> Dict[str, Any]:
        """
        Get detailed repository statistics
        
        Args:
            repository: Repository to analyze
            
        Returns:
            Dictionary with repository statistics
        """
        pass

    @abstractmethod
    def unlock_repository(self, repository: IRepository) -> bool:
        """
        Remove locks from repository
        
        Args:
            repository: Repository to unlock
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def migrate_repository(self, repository: IRepository) -> bool:
        """
        Migrate repository format
        
        Args:
            repository: Repository to migrate
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def apply_retention_policy(self, repository: IRepository,
                               keep_daily: int = 7, keep_weekly: int = 4,
                               keep_monthly: int = 12, keep_yearly: int = 3,
                               dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply retention policy to repository
        
        Args:
            repository: Repository to apply policy to
            keep_daily: Number of daily snapshots to keep
            keep_weekly: Number of weekly snapshots to keep
            keep_monthly: Number of monthly snapshots to keep
            keep_yearly: Number of yearly snapshots to keep
            dry_run: If True, only show what would be removed
            
        Returns:
            Dictionary with policy application results
        """
        pass

    @abstractmethod
    def prune_repository(self, repository: IRepository) -> Dict[str, Any]:
        """
        Prune unused data from repository
        
        Args:
            repository: Repository to prune
            
        Returns:
            Dictionary with prune results
        """
        pass
