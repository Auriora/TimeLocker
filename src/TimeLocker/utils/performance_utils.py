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

from typing import Optional, Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)


class PerformanceModule:
    """
    Centralized performance tracking module with graceful fallback handling.
    
    This module provides a single point for performance-related functionality,
    eliminating code duplication across the codebase and following DRY principles.
    """

    _instance: Optional['PerformanceModule'] = None
    _initialized: bool = False

    def __new__(cls) -> 'PerformanceModule':
        """Singleton pattern to ensure single instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize performance module with optional dependencies"""
        if not self._initialized:
            self._load_performance_dependencies()
            PerformanceModule._initialized = True

    def _load_performance_dependencies(self) -> None:
        """Load performance dependencies with graceful fallback"""
        try:
            from TimeLocker.performance.profiler import profile_operation as _profile_operation
            from TimeLocker.performance.metrics import (
                start_operation_tracking as _start_operation_tracking,
                update_operation_tracking as _update_operation_tracking,
                complete_operation_tracking as _complete_operation_tracking
            )

            self._profile_operation = _profile_operation
            self._start_operation_tracking = _start_operation_tracking
            self._update_operation_tracking = _update_operation_tracking
            self._complete_operation_tracking = _complete_operation_tracking
            self._performance_available = True

            logger.debug("Performance tracking modules loaded successfully")

        except ImportError as e:
            logger.debug(f"Performance modules not available: {e}. Using fallback implementations.")
            self._setup_fallback_implementations()
            self._performance_available = False

    def _setup_fallback_implementations(self) -> None:
        """Setup fallback implementations when performance modules are not available"""

        def profile_operation_fallback(name: str):
            """Fallback decorator that does nothing"""

            def decorator(func: Callable) -> Callable:
                return func

            return decorator

        def start_operation_tracking_fallback(
                operation_id: str,
                operation_type: str,
                metadata: Optional[Dict[str, Any]] = None
        ) -> None:
            """Fallback that does nothing"""
            pass

        def update_operation_tracking_fallback(
                operation_id: str,
                files_processed: Optional[int] = None,
                bytes_processed: Optional[int] = None,
                errors_count: Optional[int] = None,
                metadata: Optional[Dict[str, Any]] = None
        ) -> None:
            """Fallback that does nothing"""
            pass

        def complete_operation_tracking_fallback(operation_id: str) -> None:
            """Fallback that does nothing"""
            pass

        self._profile_operation = profile_operation_fallback
        self._start_operation_tracking = start_operation_tracking_fallback
        self._update_operation_tracking = update_operation_tracking_fallback
        self._complete_operation_tracking = complete_operation_tracking_fallback

    @property
    def is_available(self) -> bool:
        """Check if performance tracking is available"""
        return self._performance_available

    def profile_operation(self, name: str):
        """Profile operation decorator with fallback"""
        return self._profile_operation(name)

    def start_operation_tracking(
            self,
            operation_id: str,
            operation_type: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Start operation tracking with fallback"""
        return self._start_operation_tracking(operation_id, operation_type, metadata)

    def update_operation_tracking(
            self,
            operation_id: str,
            files_processed: Optional[int] = None,
            bytes_processed: Optional[int] = None,
            errors_count: Optional[int] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update operation tracking with fallback"""
        return self._update_operation_tracking(
                operation_id, files_processed, bytes_processed, errors_count, metadata
        )

    def complete_operation_tracking(self, operation_id: str) -> None:
        """Complete operation tracking with fallback"""
        return self._complete_operation_tracking(operation_id)


# Global instance for easy access
performance = PerformanceModule()


# Convenience functions for backward compatibility and ease of use
def profile_operation(name: str):
    """Convenience function for profiling operations"""
    return performance.profile_operation(name)


def start_operation_tracking(
        operation_id: str,
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function for starting operation tracking"""
    return performance.start_operation_tracking(operation_id, operation_type, metadata)


def update_operation_tracking(
        operation_id: str,
        files_processed: Optional[int] = None,
        bytes_processed: Optional[int] = None,
        errors_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function for updating operation tracking"""
    return performance.update_operation_tracking(
            operation_id, files_processed, bytes_processed, errors_count, metadata
    )


def complete_operation_tracking(operation_id: str) -> None:
    """Convenience function for completing operation tracking"""
    return performance.complete_operation_tracking(operation_id)
