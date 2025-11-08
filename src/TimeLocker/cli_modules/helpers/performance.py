"""
CLI Performance Monitoring and Optimization

This module provides performance monitoring and optimization features for the TimeLocker CLI.
It tracks command startup times, provides progress indicators for long-running operations,
and supports graceful command cancellation.

Requirements: 20.1, 20.2, 20.3, 20.4
"""

import time
import signal
import sys
import threading
from typing import Optional, Callable, Any, Dict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TaskID
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for CLI commands.
    
    Tracks timing information and performance thresholds for CLI operations.
    """
    command_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    
    # Performance thresholds (in milliseconds)
    SIMPLE_COMMAND_THRESHOLD: float = 200.0  # Simple commands should complete within 200ms
    COMPLEX_COMMAND_THRESHOLD: float = 500.0  # Complex commands should complete within 500ms
    PROGRESS_INDICATOR_THRESHOLD: float = 2000.0  # Show progress for operations > 2s
    
    def complete(self) -> None:
        """Mark the operation as complete and calculate duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def is_slow(self, is_complex: bool = False) -> bool:
        """
        Check if the operation exceeded performance thresholds.
        
        Args:
            is_complex: Whether this is a complex command
            
        Returns:
            True if the operation was slower than expected
        """
        if self.duration_ms is None:
            return False
        
        threshold = self.COMPLEX_COMMAND_THRESHOLD if is_complex else self.SIMPLE_COMMAND_THRESHOLD
        return self.duration_ms > threshold
    
    def needs_progress_indicator(self) -> bool:
        """
        Check if this operation should show a progress indicator.
        
        Returns:
            True if operation is expected to take > 2 seconds
        """
        if self.duration_ms is None:
            # For ongoing operations, check elapsed time
            elapsed_ms = (time.time() - self.start_time) * 1000
            return elapsed_ms > self.PROGRESS_INDICATOR_THRESHOLD
        
        return self.duration_ms > self.PROGRESS_INDICATOR_THRESHOLD
    
    def get_performance_warning(self, is_complex: bool = False) -> Optional[str]:
        """
        Get a performance warning message if applicable.
        
        Args:
            is_complex: Whether this is a complex command
            
        Returns:
            Warning message or None
        """
        if not self.is_slow(is_complex):
            return None
        
        threshold = self.COMPLEX_COMMAND_THRESHOLD if is_complex else self.SIMPLE_COMMAND_THRESHOLD
        return (
            f"Command '{self.command_name}' took {self.duration_ms:.0f}ms "
            f"(expected < {threshold:.0f}ms). Consider optimizing your configuration "
            "or checking system resources."
        )


class PerformanceMonitor:
    """
    Monitor and track CLI command performance.
    
    This class provides functionality for:
    - Tracking command execution times
    - Detecting slow operations
    - Providing performance warnings and suggestions
    """
    
    def __init__(self):
        """Initialize the performance monitor."""
        self._metrics: Dict[str, PerformanceMetrics] = {}
        self._current_command: Optional[str] = None
    
    @contextmanager
    def track_command(self, command_name: str, is_complex: bool = False):
        """
        Context manager to track command performance.
        
        Args:
            command_name: Name of the command being executed
            is_complex: Whether this is a complex command
            
        Yields:
            PerformanceMetrics instance for the command
            
        Example:
            >>> monitor = PerformanceMonitor()
            >>> with monitor.track_command("repos list") as metrics:
            ...     # Execute command
            ...     pass
        """
        metrics = PerformanceMetrics(command_name=command_name)
        self._metrics[command_name] = metrics
        self._current_command = command_name
        
        try:
            yield metrics
        finally:
            metrics.complete()
            self._current_command = None
            
            # Log performance warning if needed
            warning = metrics.get_performance_warning(is_complex)
            if warning:
                logger.warning(warning)
    
    def get_metrics(self, command_name: str) -> Optional[PerformanceMetrics]:
        """
        Get performance metrics for a command.
        
        Args:
            command_name: Name of the command
            
        Returns:
            PerformanceMetrics or None if not found
        """
        return self._metrics.get(command_name)
    
    def get_all_metrics(self) -> Dict[str, PerformanceMetrics]:
        """
        Get all tracked performance metrics.
        
        Returns:
            Dictionary of command names to metrics
        """
        return dict(self._metrics)
    
    def clear_metrics(self) -> None:
        """Clear all tracked metrics."""
        self._metrics.clear()
        self._current_command = None


class ProgressIndicator:
    """
    Progress indicator for long-running CLI operations.
    
    Provides rich progress bars with spinners, time elapsed, and estimated completion.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the progress indicator.
        
        Args:
            console: Rich console instance (creates new one if not provided)
        """
        self.console = console or Console()
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None
        self._is_active = False
    
    @contextmanager
    def show_progress(
        self,
        description: str,
        total: Optional[int] = None,
        show_spinner: bool = True,
        show_time: bool = True
    ):
        """
        Context manager to show progress indicator.
        
        Args:
            description: Description of the operation
            total: Total number of steps (None for indeterminate)
            show_spinner: Whether to show a spinner
            show_time: Whether to show elapsed/remaining time
            
        Yields:
            Function to update progress: update(advance=1, description=None)
            
        Example:
            >>> indicator = ProgressIndicator()
            >>> with indicator.show_progress("Processing files", total=100) as update:
            ...     for i in range(100):
            ...         # Do work
            ...         update(advance=1)
        """
        # Build progress columns
        columns = []
        if show_spinner:
            columns.append(SpinnerColumn())
        columns.append(TextColumn("[progress.description]{task.description}"))
        if total is not None:
            columns.append(BarColumn())
            columns.append("[progress.percentage]{task.percentage:>3.0f}%")
        if show_time:
            columns.append(TimeElapsedColumn())
            if total is not None:
                columns.append(TimeRemainingColumn())
        
        self._progress = Progress(*columns, console=self.console)
        self._is_active = True
        
        try:
            with self._progress:
                self._task_id = self._progress.add_task(description, total=total)
                
                def update(advance: int = 1, description: Optional[str] = None):
                    """Update progress."""
                    if self._progress and self._task_id is not None:
                        if description:
                            self._progress.update(self._task_id, description=description)
                        self._progress.update(self._task_id, advance=advance)
                
                yield update
        finally:
            self._is_active = False
            self._progress = None
            self._task_id = None
    
    def is_active(self) -> bool:
        """Check if progress indicator is currently active."""
        return self._is_active


class CancellationHandler:
    """
    Handle graceful command cancellation with cleanup.
    
    Supports Ctrl+C (SIGINT) and SIGTERM with configurable cleanup callbacks.
    """
    
    def __init__(self, cleanup_timeout: float = 1.0):
        """
        Initialize the cancellation handler.
        
        Args:
            cleanup_timeout: Maximum time to wait for cleanup (seconds)
        """
        self.cleanup_timeout = cleanup_timeout
        self._cleanup_callbacks: list[Callable[[], None]] = []
        self._cancelled = False
        self._original_sigint_handler = None
        self._original_sigterm_handler = None
    
    def register_cleanup(self, callback: Callable[[], None]) -> None:
        """
        Register a cleanup callback to be called on cancellation.
        
        Args:
            callback: Function to call during cleanup
        """
        self._cleanup_callbacks.append(callback)
    
    def _handle_signal(self, signum: int, frame: Any) -> None:
        """
        Handle cancellation signal.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        if self._cancelled:
            # Force exit if already cancelled once
            sys.exit(130)
        
        self._cancelled = True
        logger.info("Cancellation requested, cleaning up...")
        
        # Run cleanup callbacks with timeout
        cleanup_thread = threading.Thread(target=self._run_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        cleanup_thread.join(timeout=self.cleanup_timeout)
        
        if cleanup_thread.is_alive():
            logger.warning(f"Cleanup did not complete within {self.cleanup_timeout}s")
        
        # Exit with standard cancellation code
        sys.exit(130)
    
    def _run_cleanup(self) -> None:
        """Run all registered cleanup callbacks."""
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
    
    @contextmanager
    def handle_cancellation(self):
        """
        Context manager to handle command cancellation.
        
        Yields:
            None
            
        Example:
            >>> handler = CancellationHandler()
            >>> handler.register_cleanup(lambda: print("Cleaning up..."))
            >>> with handler.handle_cancellation():
            ...     # Long-running operation
            ...     pass
        """
        # Install signal handlers
        self._original_sigint_handler = signal.signal(signal.SIGINT, self._handle_signal)
        if hasattr(signal, 'SIGTERM'):
            self._original_sigterm_handler = signal.signal(signal.SIGTERM, self._handle_signal)
        
        try:
            yield
        finally:
            # Restore original handlers
            signal.signal(signal.SIGINT, self._original_sigint_handler)
            if hasattr(signal, 'SIGTERM') and self._original_sigterm_handler:
                signal.signal(signal.SIGTERM, self._original_sigterm_handler)
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancelled


# Global instances for easy access
_performance_monitor = PerformanceMonitor()
_cancellation_handler = CancellationHandler()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def get_cancellation_handler() -> CancellationHandler:
    """Get the global cancellation handler instance."""
    return _cancellation_handler


@contextmanager
def track_command_performance(command_name: str, is_complex: bool = False):
    """
    Convenience function to track command performance.
    
    Args:
        command_name: Name of the command
        is_complex: Whether this is a complex command
        
    Yields:
        PerformanceMetrics instance
    """
    with _performance_monitor.track_command(command_name, is_complex) as metrics:
        yield metrics
