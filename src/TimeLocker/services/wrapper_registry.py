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

"""
Wrapper Registry System

This module provides a registry system for managing backup tool plugin wrappers.
The registry allows registration, discovery, and retrieval of wrappers for
different backup tools.
"""

import logging
from typing import Dict, List, Optional, Type, Set
from .plugin_wrapper import PluginWrapper, PluginWrapperError
from .tool_manager import Feature

logger = logging.getLogger(__name__)


class WrapperRegistry:
    """
    Registry for backup tool plugin wrappers.
    
    This class manages the lifecycle of plugin wrappers, including
    registration, discovery, and retrieval. It follows the Singleton
    pattern to ensure a single registry instance across the application.
    """
    
    _instance: Optional['WrapperRegistry'] = None
    
    def __new__(cls):
        """Ensure singleton instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the wrapper registry"""
        if self._initialized:
            return
        
        self._wrappers: Dict[str, PluginWrapper] = {}
        self._wrapper_classes: Dict[str, Type[PluginWrapper]] = {}
        self._initialized = True
        logger.debug("WrapperRegistry initialized")
    
    def register_wrapper(
        self,
        tool_name: str,
        wrapper_class: Type[PluginWrapper]
    ) -> None:
        """
        Register a plugin wrapper class for a backup tool.
        
        Args:
            tool_name: Name of the backup tool (e.g., 'restic', 'borg')
            wrapper_class: Wrapper class to register
            
        Raises:
            PluginWrapperError: If wrapper registration fails
        """
        if not issubclass(wrapper_class, PluginWrapper):
            raise PluginWrapperError(
                f"Wrapper class must inherit from PluginWrapper: {wrapper_class}"
            )
        
        tool_name_lower = tool_name.lower()
        
        if tool_name_lower in self._wrapper_classes:
            logger.warning(
                f"Overriding existing wrapper for tool: {tool_name}"
            )
        
        self._wrapper_classes[tool_name_lower] = wrapper_class
        logger.info(f"Registered wrapper for tool: {tool_name}")
    
    def get_wrapper(self, tool_name: str) -> PluginWrapper:
        """
        Get a wrapper instance for the specified tool.
        
        Args:
            tool_name: Name of the backup tool
            
        Returns:
            PluginWrapper instance
            
        Raises:
            PluginWrapperError: If wrapper is not registered
        """
        tool_name_lower = tool_name.lower()
        
        # Check if we have a cached instance
        if tool_name_lower in self._wrappers:
            return self._wrappers[tool_name_lower]
        
        # Check if wrapper class is registered
        if tool_name_lower not in self._wrapper_classes:
            raise PluginWrapperError(
                f"No wrapper registered for tool: {tool_name}. "
                f"Available tools: {', '.join(self._wrapper_classes.keys())}"
            )
        
        # Create and cache wrapper instance
        try:
            wrapper_class = self._wrapper_classes[tool_name_lower]
            wrapper = wrapper_class()
            self._wrappers[tool_name_lower] = wrapper
            logger.debug(f"Created wrapper instance for {tool_name}")
            return wrapper
        except Exception as e:
            raise PluginWrapperError(
                f"Failed to create wrapper instance for {tool_name}: {e}"
            ) from e
    
    def is_tool_supported(self, tool_name: str) -> bool:
        """
        Check if a tool has a registered wrapper.
        
        Args:
            tool_name: Name of the backup tool
            
        Returns:
            True if tool has a registered wrapper
        """
        return tool_name.lower() in self._wrapper_classes
    
    def get_supported_tools(self) -> List[str]:
        """
        Get list of tools with registered wrappers.
        
        Returns:
            List of tool names
        """
        return list(self._wrapper_classes.keys())
    
    def get_wrapper_info(self, tool_name: str) -> Dict[str, any]:
        """
        Get information about a wrapper.
        
        Args:
            tool_name: Name of the backup tool
            
        Returns:
            Dictionary with wrapper information
            
        Raises:
            PluginWrapperError: If wrapper is not registered
        """
        wrapper = self.get_wrapper(tool_name)
        return wrapper.get_capability_info()
    
    def get_all_wrapper_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get information about all registered wrappers.
        
        Returns:
            Dictionary mapping tool names to wrapper information
        """
        info = {}
        for tool_name in self._wrapper_classes.keys():
            try:
                info[tool_name] = self.get_wrapper_info(tool_name)
            except Exception as e:
                logger.warning(f"Failed to get info for {tool_name}: {e}")
                info[tool_name] = {
                    'tool_name': tool_name,
                    'error': str(e)
                }
        return info
    
    def find_wrappers_with_capability(
        self,
        feature: Feature
    ) -> List[str]:
        """
        Find wrappers that support a specific capability.
        
        Args:
            feature: Feature to search for
            
        Returns:
            List of tool names that support the feature
        """
        matching_tools = []
        
        for tool_name in self._wrapper_classes.keys():
            try:
                wrapper = self.get_wrapper(tool_name)
                if wrapper.has_capability(feature):
                    matching_tools.append(tool_name)
            except Exception as e:
                logger.warning(
                    f"Error checking capability for {tool_name}: {e}"
                )
        
        return matching_tools
    
    def find_wrappers_with_native_capability(
        self,
        feature: Feature
    ) -> List[str]:
        """
        Find wrappers where the tool natively supports a capability.
        
        Args:
            feature: Feature to search for
            
        Returns:
            List of tool names with native support
        """
        matching_tools = []
        
        for tool_name in self._wrapper_classes.keys():
            try:
                wrapper = self.get_wrapper(tool_name)
                if wrapper.is_native_capability(feature):
                    matching_tools.append(tool_name)
            except Exception as e:
                logger.warning(
                    f"Error checking native capability for {tool_name}: {e}"
                )
        
        return matching_tools
    
    def compare_wrappers(
        self,
        tool_names: List[str]
    ) -> Dict[str, any]:
        """
        Compare capabilities of multiple wrappers.
        
        Args:
            tool_names: List of tool names to compare
            
        Returns:
            Dictionary with comparison results
        """
        comparison = {
            'tools': tool_names,
            'capabilities': {},
            'native_only': {},
            'wrapper_only': {}
        }
        
        # Get all unique features across all tools
        all_features: Set[Feature] = set()
        for tool_name in tool_names:
            try:
                wrapper = self.get_wrapper(tool_name)
                all_features.update(wrapper.get_all_capabilities())
            except Exception as e:
                logger.warning(f"Error getting capabilities for {tool_name}: {e}")
        
        # Compare each feature across tools
        for feature in all_features:
            comparison['capabilities'][feature.value] = {}
            
            for tool_name in tool_names:
                try:
                    wrapper = self.get_wrapper(tool_name)
                    has_feature = wrapper.has_capability(feature)
                    is_native = wrapper.is_native_capability(feature)
                    
                    comparison['capabilities'][feature.value][tool_name] = {
                        'supported': has_feature,
                        'native': is_native,
                        'wrapper': has_feature and not is_native
                    }
                except Exception as e:
                    comparison['capabilities'][feature.value][tool_name] = {
                        'error': str(e)
                    }
        
        return comparison
    
    def unregister_wrapper(self, tool_name: str) -> bool:
        """
        Unregister a wrapper.
        
        Args:
            tool_name: Name of the backup tool
            
        Returns:
            True if wrapper was unregistered, False if not found
        """
        tool_name_lower = tool_name.lower()
        removed = False
        
        if tool_name_lower in self._wrapper_classes:
            del self._wrapper_classes[tool_name_lower]
            removed = True
            logger.debug(f"Unregistered wrapper class for {tool_name}")
        
        if tool_name_lower in self._wrappers:
            del self._wrappers[tool_name_lower]
            logger.debug(f"Removed wrapper instance for {tool_name}")
        
        return removed
    
    def clear(self) -> None:
        """Clear all registered wrappers"""
        self._wrappers.clear()
        self._wrapper_classes.clear()
        logger.debug("Cleared all wrappers from registry")


# Global registry instance
_global_wrapper_registry: Optional[WrapperRegistry] = None


def get_wrapper_registry() -> WrapperRegistry:
    """
    Get the global wrapper registry instance.
    
    Returns:
        Global WrapperRegistry instance
    """
    global _global_wrapper_registry
    if _global_wrapper_registry is None:
        _global_wrapper_registry = WrapperRegistry()
    return _global_wrapper_registry


def initialize_wrappers() -> None:
    """
    Initialize and register all built-in wrappers.
    
    This function should be called during application startup to
    register all available plugin wrappers.
    """
    logger.info("Initializing plugin wrappers")
    
    registry = get_wrapper_registry()
    
    # Register Restic wrapper
    try:
        from .restic_plugin_wrapper import ResticPluginWrapper
        registry.register_wrapper('restic', ResticPluginWrapper)
        logger.info("Registered Restic plugin wrapper")
    except Exception as e:
        logger.warning(f"Failed to register Restic wrapper: {e}")
    
    # Future: Register other wrappers (Borg, Duplicity, etc.)
    
    logger.info(
        f"Plugin wrapper initialization complete. "
        f"Registered {len(registry.get_supported_tools())} wrappers"
    )
