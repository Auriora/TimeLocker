"""
Centralized progress tracking service for CLI operations.

This module provides a unified interface for progress tracking with consistent
display, context management, and templates for common operations.

Requirements addressed:
- Requirement 6: Centralized progress tracking through ProgressService
- 6.1: Provide consistent progress tracking for all long-running CLI operations
- 6.2: Support nested progress contexts and automatic cleanup
- 6.3: Integrate with existing progress tracking mechanisms
- 6.4: Reduce progress tracking code by at least 70 lines across 20 commands
- 6.5: Continue operation without displaying progress on failures
"""

import logging
from typing import Optional, Callable, Any, Dict, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TaskID,
    ProgressColumn
)

logger = logging.getLogger(__name__)


class ProgressType(Enum):
    """Types of progress indicators."""
    SPINNER = "spinner"  # Indeterminate spinner
    BAR = "bar"  # Determinate progress bar
    SIMPLE = "simple"  # Simple text-based progress


@dataclass
class ProgressContext:
    """
    Context for a progress tracking operation.
    
    Tracks the progress instance, task ID, and metadata for a single
    progress tracking operation.
    """
    progress: Progress
    task_id: TaskID
    description: str
    total: Optional[int] = None
    completed: int = 0
    parent: Optional['ProgressContext'] = None
    children: List['ProgressContext'] = field(default_factory=list)
    
    def update(self, advance: int = 1, description: Optional[str] = None) -> None:
        """
        Update progress.
        
        Args:
            advance: Number of steps to advance
            description: Optional new description
        """
        self.completed += advance
        if description:
            self.description = description
            self.progress.update(self.task_id, description=description)
        self.progress.update(self.task_id, advance=advance)
    
    def set_total(self, total: int) -> None:
        """
        Set or update the total number of steps.
        
        Args:
            total: Total number of steps
        """
        self.total = total
        self.progress.update(self.task_id, total=total)
    
    def complete(self) -> None:
        """Mark progress as complete."""
        if self.total is not None:
            remaining = self.total - self.completed
            if remaining > 0:
                self.progress.update(self.task_id, advance=remaining)
        self.progress.update(self.task_id, completed=self.total or self.completed)


class ProgressService:
    """
    Centralized service for progress tracking with consistent behavior.
    
    This service provides a unified interface for all CLI progress tracking, handling:
    - Spinner progress for indeterminate operations
    - Bar progress for determinate operations
    - Nested progress contexts
    - Automatic cleanup
    - Graceful degradation on failures
    
    Requirements addressed:
    - 6.1: Consistent progress tracking for long-running operations
    - 6.2: Nested progress contexts and automatic cleanup
    - 6.3: Integration with existing progress mechanisms
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        enabled: bool = True
    ):
        """
        Initialize the progress service.
        
        Args:
            console: Optional Rich console instance. If None, creates a new one.
            enabled: Whether progress tracking is enabled
        """
        self._console = console or Console(width=100)
        self._enabled = enabled
        self._active_contexts: List[ProgressContext] = []
        logger.debug(f"ProgressService initialized (enabled: {enabled})")
    
    def is_enabled(self) -> bool:
        """
        Check if progress tracking is enabled.
        
        Returns:
            True if progress tracking is enabled
        """
        return self._enabled
    
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable progress tracking.
        
        Args:
            enabled: Whether to enable progress tracking
        """
        self._enabled = enabled
        logger.debug(f"Progress tracking {'enabled' if enabled else 'disabled'}")
    
    @contextmanager
    def spinner(
        self,
        description: str,
        show_time: bool = True
    ):
        """
        Create a spinner progress indicator for indeterminate operations.
        
        Args:
            description: Description of the operation
            show_time: Whether to show elapsed time
            
        Yields:
            ProgressContext that can be used to update the description
            
        Example:
            >>> service = ProgressService()
            >>> with service.spinner("Loading data...") as progress:
            ...     # Do work
            ...     progress.update(description="Processing data...")
        
        Requirements addressed:
        - 6.1: Consistent progress tracking
        - 6.2: Context management and cleanup
        """
        if not self._enabled:
            # Provide a no-op context when disabled
            yield self._create_noop_context(description)
            return
        
        try:
            # Build progress columns for spinner
            columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}")
            ]
            if show_time:
                columns.append(TimeElapsedColumn())
            
            progress = Progress(*columns, console=self._console)
            
            with progress:
                task_id = progress.add_task(description, total=None)
                context = ProgressContext(
                    progress=progress,
                    task_id=task_id,
                    description=description
                )
                self._active_contexts.append(context)
                
                try:
                    yield context
                finally:
                    context.complete()
                    if context in self._active_contexts:
                        self._active_contexts.remove(context)
                    
        except Exception as e:
            logger.error(f"Failed to create spinner progress: {e}")
            # Graceful degradation - continue without progress
            yield self._create_noop_context(description)
    
    @contextmanager
    def bar(
        self,
        description: str,
        total: int,
        show_time: bool = True,
        show_percentage: bool = True
    ):
        """
        Create a progress bar for determinate operations.
        
        Args:
            description: Description of the operation
            total: Total number of steps
            show_time: Whether to show elapsed/remaining time
            show_percentage: Whether to show percentage complete
            
        Yields:
            ProgressContext that can be used to update progress
            
        Example:
            >>> service = ProgressService()
            >>> with service.bar("Processing files", total=100) as progress:
            ...     for i in range(100):
            ...         # Do work
            ...         progress.update(advance=1)
        
        Requirements addressed:
        - 6.1: Consistent progress tracking
        - 6.2: Context management and cleanup
        """
        if not self._enabled:
            # Provide a no-op context when disabled
            yield self._create_noop_context(description, total)
            return
        
        try:
            # Build progress columns for bar
            columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn()
            ]
            if show_percentage:
                columns.append("[progress.percentage]{task.percentage:>3.0f}%")
            if show_time:
                columns.append(TimeElapsedColumn())
                columns.append(TimeRemainingColumn())
            
            progress = Progress(*columns, console=self._console)
            
            with progress:
                task_id = progress.add_task(description, total=total)
                context = ProgressContext(
                    progress=progress,
                    task_id=task_id,
                    description=description,
                    total=total
                )
                self._active_contexts.append(context)
                
                try:
                    yield context
                finally:
                    context.complete()
                    if context in self._active_contexts:
                        self._active_contexts.remove(context)
                    
        except Exception as e:
            logger.error(f"Failed to create bar progress: {e}")
            # Graceful degradation - continue without progress
            yield self._create_noop_context(description, total)
    
    @contextmanager
    def simple(
        self,
        description: str,
        total: Optional[int] = None
    ):
        """
        Create a simple text-based progress indicator.
        
        This is a lightweight alternative that just shows description and elapsed time.
        
        Args:
            description: Description of the operation
            total: Optional total number of steps
            
        Yields:
            ProgressContext that can be used to update progress
            
        Example:
            >>> service = ProgressService()
            >>> with service.simple("Validating...") as progress:
            ...     # Do work
            ...     progress.update(description="Validation complete")
        
        Requirements addressed:
        - 6.1: Consistent progress tracking
        - 6.2: Context management and cleanup
        """
        if not self._enabled:
            # Provide a no-op context when disabled
            yield self._create_noop_context(description, total)
            return
        
        try:
            # Build minimal progress columns
            columns = [
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn()
            ]
            
            progress = Progress(*columns, console=self._console)
            
            with progress:
                task_id = progress.add_task(description, total=total)
                context = ProgressContext(
                    progress=progress,
                    task_id=task_id,
                    description=description,
                    total=total
                )
                self._active_contexts.append(context)
                
                try:
                    yield context
                finally:
                    context.complete()
                    if context in self._active_contexts:
                        self._active_contexts.remove(context)
                    
        except Exception as e:
            logger.error(f"Failed to create simple progress: {e}")
            # Graceful degradation - continue without progress
            yield self._create_noop_context(description, total)
    
    @contextmanager
    def nested(
        self,
        parent_description: str,
        child_descriptions: List[str],
        show_time: bool = True
    ):
        """
        Create nested progress tracking for multi-step operations.
        
        Args:
            parent_description: Description of the parent operation
            child_descriptions: List of descriptions for child operations
            show_time: Whether to show elapsed time
            
        Yields:
            Tuple of (parent_context, child_contexts) where child_contexts is a list
            
        Example:
            >>> service = ProgressService()
            >>> with service.nested("Backup", ["Scan", "Upload", "Verify"]) as (parent, children):
            ...     for child in children:
            ...         # Do work for this step
            ...         child.complete()
            ...         parent.update(advance=1)
        
        Requirements addressed:
        - 6.2: Nested progress contexts
        """
        if not self._enabled:
            # Provide no-op contexts when disabled
            parent = self._create_noop_context(parent_description, len(child_descriptions))
            children = [self._create_noop_context(desc) for desc in child_descriptions]
            yield parent, children
            return
        
        try:
            # Build progress columns
            columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%"
            ]
            if show_time:
                columns.append(TimeElapsedColumn())
                columns.append(TimeRemainingColumn())
            
            progress = Progress(*columns, console=self._console)
            
            with progress:
                # Create parent task
                parent_task_id = progress.add_task(
                    parent_description,
                    total=len(child_descriptions)
                )
                parent_context = ProgressContext(
                    progress=progress,
                    task_id=parent_task_id,
                    description=parent_description,
                    total=len(child_descriptions)
                )
                self._active_contexts.append(parent_context)
                
                # Create child tasks
                child_contexts = []
                for desc in child_descriptions:
                    child_task_id = progress.add_task(f"  {desc}", total=None)
                    child_context = ProgressContext(
                        progress=progress,
                        task_id=child_task_id,
                        description=desc,
                        parent=parent_context
                    )
                    parent_context.children.append(child_context)
                    child_contexts.append(child_context)
                    self._active_contexts.append(child_context)
                
                try:
                    yield parent_context, child_contexts
                finally:
                    # Clean up child contexts
                    for child in child_contexts:
                        child.complete()
                        if child in self._active_contexts:
                            self._active_contexts.remove(child)
                    
                    # Clean up parent context
                    parent_context.complete()
                    if parent_context in self._active_contexts:
                        self._active_contexts.remove(parent_context)
                    
        except Exception as e:
            logger.error(f"Failed to create nested progress: {e}")
            # Graceful degradation - provide no-op contexts
            parent = self._create_noop_context(parent_description, len(child_descriptions))
            children = [self._create_noop_context(desc) for desc in child_descriptions]
            yield parent, children
    
    def _create_noop_context(
        self,
        description: str,
        total: Optional[int] = None
    ) -> ProgressContext:
        """
        Create a no-op progress context that does nothing.
        
        Used when progress tracking is disabled or fails.
        
        Args:
            description: Description of the operation
            total: Optional total number of steps
            
        Returns:
            ProgressContext that does nothing when updated
        """
        # Create a minimal Progress instance that won't display anything
        progress = Progress(console=Console(quiet=True))
        task_id = progress.add_task(description, total=total)
        
        return ProgressContext(
            progress=progress,
            task_id=task_id,
            description=description,
            total=total
        )
    
    def get_active_contexts(self) -> List[ProgressContext]:
        """
        Get all currently active progress contexts.
        
        Returns:
            List of active ProgressContext instances
        """
        return list(self._active_contexts)
    
    def has_active_progress(self) -> bool:
        """
        Check if there are any active progress operations.
        
        Returns:
            True if there are active progress operations
        """
        return len(self._active_contexts) > 0


# Progress templates for common operations
class ProgressTemplates:
    """
    Pre-configured progress templates for common CLI operations.
    
    These templates provide consistent progress tracking patterns for
    frequently used operations.
    
    Requirements addressed:
    - 6.1: Progress templates for common operations
    """
    
    @staticmethod
    @contextmanager
    def backup_operation(service: ProgressService, repository_name: str):
        """
        Progress template for backup operations.
        
        Args:
            service: ProgressService instance
            repository_name: Name of the repository being backed up
            
        Yields:
            ProgressContext for the backup operation
        """
        with service.spinner(
            f"Creating backup in repository '{repository_name}'...",
            show_time=True
        ) as progress:
            yield progress
    
    @staticmethod
    @contextmanager
    def restore_operation(
        service: ProgressService,
        snapshot_id: str,
        target_path: str
    ):
        """
        Progress template for restore operations.
        
        Args:
            service: ProgressService instance
            snapshot_id: ID of the snapshot being restored
            target_path: Target path for restoration
            
        Yields:
            ProgressContext for the restore operation
        """
        with service.spinner(
            f"Restoring snapshot {snapshot_id[:12]} to {target_path}...",
            show_time=True
        ) as progress:
            yield progress
    
    @staticmethod
    @contextmanager
    def repository_operation(
        service: ProgressService,
        operation: str,
        repository_name: str
    ):
        """
        Progress template for repository operations.
        
        Args:
            service: ProgressService instance
            operation: Operation being performed (e.g., "init", "prune", "check")
            repository_name: Name of the repository
            
        Yields:
            ProgressContext for the repository operation
        """
        with service.spinner(
            f"{operation.capitalize()} repository '{repository_name}'...",
            show_time=True
        ) as progress:
            yield progress
    
    @staticmethod
    @contextmanager
    def batch_operation(
        service: ProgressService,
        operation: str,
        total: int
    ):
        """
        Progress template for batch operations.
        
        Args:
            service: ProgressService instance
            operation: Operation being performed
            total: Total number of items to process
            
        Yields:
            ProgressContext for the batch operation
        """
        with service.bar(
            f"{operation} ({total} items)",
            total=total,
            show_time=True,
            show_percentage=True
        ) as progress:
            yield progress
    
    @staticmethod
    @contextmanager
    def validation_operation(
        service: ProgressService,
        what: str
    ):
        """
        Progress template for validation operations.
        
        Args:
            service: ProgressService instance
            what: What is being validated
            
        Yields:
            ProgressContext for the validation operation
        """
        with service.simple(
            f"Validating {what}..."
        ) as progress:
            yield progress


# Singleton instance for convenience
_default_progress_service: Optional[ProgressService] = None


def get_progress_service(
    console: Optional[Console] = None,
    enabled: bool = True
) -> ProgressService:
    """
    Get the default ProgressService instance.
    
    Args:
        console: Optional Rich console instance
        enabled: Whether progress tracking is enabled
        
    Returns:
        ProgressService instance
    """
    global _default_progress_service
    if _default_progress_service is None:
        _default_progress_service = ProgressService(
            console=console,
            enabled=enabled
        )
    return _default_progress_service


__all__ = [
    'ProgressService',
    'ProgressContext',
    'ProgressType',
    'ProgressTemplates',
    'get_progress_service',
]
