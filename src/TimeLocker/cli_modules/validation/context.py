"""
Validation context for passing state between validators.

This module provides a context object that can be used to pass state
and configuration between validators during validation operations.
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationContext:
    """
    Context for validation operations.
    
    Provides a way to pass state, configuration, and other information
    between validators during validation.
    """
    
    # Configuration and state
    config: Optional[Any] = None
    repositories: Dict[str, Any] = field(default_factory=dict)
    backup_targets: Dict[str, Any] = field(default_factory=dict)
    
    # Validation options
    strict_mode: bool = False
    allow_warnings: bool = True
    
    # Custom data
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from custom data.
        
        Args:
            key: Key to retrieve
            default: Default value if key not found
            
        Returns:
            Value from custom data or default
        """
        return self.custom_data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in custom data.
        
        Args:
            key: Key to set
            value: Value to set
        """
        self.custom_data[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary.
        
        Returns:
            Dictionary representation of context
        """
        return {
            'strict_mode': self.strict_mode,
            'allow_warnings': self.allow_warnings,
            'has_config': self.config is not None,
            'repository_count': len(self.repositories),
            'backup_target_count': len(self.backup_targets),
            'custom_data': self.custom_data,
        }
