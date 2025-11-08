"""
Output filtering and pagination utilities for CLI commands.

This module provides utilities for filtering output fields,
paginating large datasets, and implementing quiet mode.
"""

from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass


@dataclass
class PaginationInfo:
    """Information about pagination state."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous
        }


class OutputFilter:
    """
    Handles output filtering and field selection.
    
    Provides utilities for:
    - Selecting specific fields from output
    - Excluding fields from output
    - Filtering data based on criteria
    """
    
    def __init__(
        self,
        include_fields: Optional[List[str]] = None,
        exclude_fields: Optional[List[str]] = None
    ):
        """
        Initialize output filter.
        
        Args:
            include_fields: List of fields to include (None = all fields)
            exclude_fields: List of fields to exclude
        """
        self.include_fields = set(include_fields) if include_fields else None
        self.exclude_fields = set(exclude_fields) if exclude_fields else set()
    
    def filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter a dictionary based on field selection.
        
        Args:
            data: Dictionary to filter
            
        Returns:
            Filtered dictionary
        """
        if self.include_fields is not None:
            # Only include specified fields
            filtered = {k: v for k, v in data.items() if k in self.include_fields}
        else:
            # Include all fields except excluded ones
            filtered = {k: v for k, v in data.items() if k not in self.exclude_fields}
        
        return filtered
    
    def filter_list(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter a list of dictionaries.
        
        Args:
            data: List of dictionaries to filter
            
        Returns:
            List of filtered dictionaries
        """
        return [self.filter_dict(item) for item in data]
    
    def filter_data(self, data: Any) -> Any:
        """
        Filter data (handles both dict and list).
        
        Args:
            data: Data to filter
            
        Returns:
            Filtered data
        """
        if isinstance(data, dict):
            return self.filter_dict(data)
        elif isinstance(data, list):
            return self.filter_list(data)
        else:
            return data


class Paginator:
    """
    Handles pagination of large datasets.
    
    Provides utilities for:
    - Paginating lists of items
    - Calculating pagination metadata
    - Generating page ranges
    """
    
    def __init__(self, page_size: int = 20):
        """
        Initialize paginator.
        
        Args:
            page_size: Number of items per page
        """
        self.page_size = page_size
    
    def paginate(
        self,
        items: List[Any],
        page: int = 1
    ) -> tuple[List[Any], PaginationInfo]:
        """
        Paginate a list of items.
        
        Args:
            items: List of items to paginate
            page: Page number (1-indexed)
            
        Returns:
            Tuple of (page_items, pagination_info)
        """
        total_items = len(items)
        total_pages = (total_items + self.page_size - 1) // self.page_size
        
        # Validate page number
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        
        # Calculate slice indices
        start_idx = (page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        
        # Get page items
        page_items = items[start_idx:end_idx]
        
        # Create pagination info
        pagination_info = PaginationInfo(
            page=page,
            page_size=self.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        return page_items, pagination_info
    
    def get_page_range(
        self,
        current_page: int,
        total_pages: int,
        max_pages: int = 5
    ) -> List[int]:
        """
        Get a range of page numbers to display.
        
        Args:
            current_page: Current page number
            total_pages: Total number of pages
            max_pages: Maximum number of page numbers to return
            
        Returns:
            List of page numbers
        """
        if total_pages <= max_pages:
            return list(range(1, total_pages + 1))
        
        # Calculate range around current page
        half = max_pages // 2
        start = max(1, current_page - half)
        end = min(total_pages, start + max_pages - 1)
        
        # Adjust start if we're near the end
        if end - start < max_pages - 1:
            start = max(1, end - max_pages + 1)
        
        return list(range(start, end + 1))


def create_filter(
    fields: Optional[str] = None,
    exclude: Optional[str] = None
) -> OutputFilter:
    """
    Create an output filter from command-line options.
    
    Args:
        fields: Comma-separated list of fields to include
        exclude: Comma-separated list of fields to exclude
        
    Returns:
        OutputFilter instance
    """
    include_fields = None
    if fields:
        include_fields = [f.strip() for f in fields.split(',')]
    
    exclude_fields = None
    if exclude:
        exclude_fields = [f.strip() for f in exclude.split(',')]
    
    return OutputFilter(
        include_fields=include_fields,
        exclude_fields=exclude_fields
    )


def create_paginator(page_size: Optional[int] = None) -> Paginator:
    """
    Create a paginator with specified page size.
    
    Args:
        page_size: Number of items per page (default: 20)
        
    Returns:
        Paginator instance
    """
    return Paginator(page_size=page_size or 20)


def apply_filters_and_pagination(
    data: List[Dict[str, Any]],
    filter: Optional[OutputFilter] = None,
    paginator: Optional[Paginator] = None,
    page: int = 1
) -> Dict[str, Any]:
    """
    Apply filtering and pagination to data.
    
    Args:
        data: List of items to process
        filter: Output filter (optional)
        paginator: Paginator (optional)
        page: Page number (if paginating)
        
    Returns:
        Dictionary with filtered/paginated data and metadata
    """
    # Apply filtering
    if filter:
        data = filter.filter_list(data)
    
    # Apply pagination
    if paginator:
        page_items, pagination_info = paginator.paginate(data, page)
        return {
            "items": page_items,
            "pagination": pagination_info.to_dict()
        }
    else:
        return {
            "items": data,
            "total_count": len(data)
        }


class QuietMode:
    """
    Handles quiet mode output suppression.
    
    In quiet mode:
    - Suppress informational messages
    - Suppress progress indicators
    - Only output essential data
    - Errors still shown (but minimal)
    """
    
    @staticmethod
    def should_suppress_info(quiet: bool) -> bool:
        """Check if informational output should be suppressed."""
        return quiet
    
    @staticmethod
    def should_suppress_progress(quiet: bool) -> bool:
        """Check if progress indicators should be suppressed."""
        return quiet
    
    @staticmethod
    def should_suppress_warnings(quiet: bool) -> bool:
        """Check if warnings should be suppressed."""
        # In quiet mode, still show warnings but in minimal format
        return False
    
    @staticmethod
    def should_suppress_errors(quiet: bool) -> bool:
        """Check if errors should be suppressed."""
        # Never suppress errors
        return False
    
    @staticmethod
    def format_minimal_error(message: str) -> str:
        """Format error message for quiet mode."""
        return f"ERROR: {message}"
    
    @staticmethod
    def format_minimal_warning(message: str) -> str:
        """Format warning message for quiet mode."""
        return f"WARNING: {message}"


def filter_sensitive_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out sensitive fields from output.
    
    Args:
        data: Dictionary potentially containing sensitive data
        
    Returns:
        Dictionary with sensitive fields masked or removed
    """
    sensitive_fields = {
        'password', 'secret', 'token', 'key', 'credential',
        'access_key', 'secret_key', 'api_key', 'auth_token'
    }
    
    filtered = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if field name contains sensitive keywords
        is_sensitive = any(sensitive in key_lower for sensitive in sensitive_fields)
        
        if is_sensitive:
            if isinstance(value, str) and len(value) > 4:
                # Mask sensitive string values
                filtered[key] = value[:2] + "***" + value[-2:]
            else:
                # Remove other sensitive values
                filtered[key] = "***"
        else:
            filtered[key] = value
    
    return filtered


__all__ = [
    "OutputFilter",
    "Paginator",
    "PaginationInfo",
    "QuietMode",
    "create_filter",
    "create_paginator",
    "apply_filters_and_pagination",
    "filter_sensitive_fields",
]
