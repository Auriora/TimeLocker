"""
TimeLocker Utilities Package

This package contains utility modules that provide common functionality
across the TimeLocker codebase, following DRY principles.
"""

from .performance_utils import (
    PerformanceModule,
    performance,
    profile_operation,
    start_operation_tracking,
    update_operation_tracking,
    complete_operation_tracking
)

from .error_handling import (
    ErrorHandler,
    ErrorContext,
    error_handler,
    handle_error,
    with_error_handling,
    with_retry
)

from .platform_compatibility import (
    PlatformCompatibility,
    Platform,
    get_platform_compatibility
)

__all__ = [
        # Performance utilities
        'PerformanceModule',
        'performance',
        'profile_operation',
        'start_operation_tracking',
        'update_operation_tracking',
        'complete_operation_tracking',

        # Error handling utilities
        'ErrorHandler',
        'ErrorContext',
        'error_handler',
        'handle_error',
        'with_error_handling',
        'with_retry',
        
        # Platform compatibility utilities
        'PlatformCompatibility',
        'Platform',
        'get_platform_compatibility'
]
