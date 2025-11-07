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
Plugin Registry for Backup Engines

This module provides a registry system for discovering, managing, and accessing
backup engine plugins in a consistent manner.
"""

import logging
from typing import Dict, List, Optional, Type
from ..interfaces.backup_engine_plugin import (
    BackupEnginePlugin,
    BackupEngine,
    EngineCapabilities,
    PluginError,
    EngineNotAvailableError
)

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Registry for backup engine plugins.
    
    This class manages the lifecycle of backup engine plugins, including
    registration, discovery, and retrieval. It follows the Singleton pattern
    to ensure a single registry instance across the application.
    """
    
    _instance: Optional['PluginRegistry'] = None
    
    def __new__(cls):
        """Ensure singleton instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the plugin registry"""
        if self._initialized:
            return
            
        self._plugins: Dict[BackupEngine, BackupEnginePlugin] = {}
        self._plugin_classes: Dict[BackupEngine, Type[BackupEnginePlugin]] = {}
        self._initialized = True
        logger.debug("PluginRegistry initialized")
    
    def register_plugin(self, plugin_class: Type[BackupEnginePlugin]) -> None:
        """
        Register a backup engine plugin class.
        
        Args:
            plugin_class: Plugin class to register
            
        Raises:
            PluginError: If plugin registration fails
        """
        if not issubclass(plugin_class, BackupEnginePlugin):
            raise PluginError(
                f"Plugin class must inherit from BackupEnginePlugin: {plugin_class}"
            )
        
        try:
            # Create temporary instance to get engine type
            temp_instance = plugin_class()
            engine_type = temp_instance.engine_type
            
            if engine_type in self._plugin_classes:
                logger.warning(
                    f"Overriding existing plugin for engine: {engine_type.value}"
                )
            
            self._plugin_classes[engine_type] = plugin_class
            logger.info(
                f"Registered plugin '{temp_instance.engine_name}' "
                f"for engine type: {engine_type.value}"
            )
            
        except Exception as e:
            raise PluginError(f"Failed to register plugin {plugin_class}: {e}") from e
    
    def get_plugin(self, engine_type: BackupEngine) -> BackupEnginePlugin:
        """
        Get a plugin instance for the specified engine type.
        
        Args:
            engine_type: Type of backup engine
            
        Returns:
            Plugin instance
            
        Raises:
            PluginError: If plugin is not registered
            EngineNotAvailableError: If engine is not available on system
        """
        # Check if we have a cached instance
        if engine_type in self._plugins:
            return self._plugins[engine_type]
        
        # Check if plugin class is registered
        if engine_type not in self._plugin_classes:
            raise PluginError(
                f"No plugin registered for engine type: {engine_type.value}. "
                f"Available engines: {', '.join(e.value for e in self._plugin_classes.keys())}"
            )
        
        # Create and cache plugin instance
        try:
            plugin_class = self._plugin_classes[engine_type]
            plugin = plugin_class()
            
            # Verify engine is available
            if not plugin.is_available():
                raise EngineNotAvailableError(
                    f"Backup engine '{plugin.engine_name}' is not available on this system. "
                    f"Please ensure it is installed and in the PATH."
                )
            
            self._plugins[engine_type] = plugin
            logger.debug(
                f"Created plugin instance for {engine_type.value} "
                f"(version: {plugin.engine_version})"
            )
            return plugin
            
        except EngineNotAvailableError:
            raise
        except Exception as e:
            raise PluginError(
                f"Failed to create plugin instance for {engine_type.value}: {e}"
            ) from e
    
    def is_engine_available(self, engine_type: BackupEngine) -> bool:
        """
        Check if a backup engine is available on the system.
        
        Args:
            engine_type: Type of backup engine
            
        Returns:
            True if engine is registered and available, False otherwise
        """
        try:
            plugin = self.get_plugin(engine_type)
            return plugin.is_available()
        except (PluginError, EngineNotAvailableError):
            return False
    
    def get_available_engines(self) -> List[BackupEngine]:
        """
        Get list of available backup engines.
        
        Returns:
            List of BackupEngine types that are registered and available
        """
        available = []
        for engine_type in self._plugin_classes.keys():
            if self.is_engine_available(engine_type):
                available.append(engine_type)
        return available
    
    def get_registered_engines(self) -> List[BackupEngine]:
        """
        Get list of registered backup engines (regardless of availability).
        
        Returns:
            List of registered BackupEngine types
        """
        return list(self._plugin_classes.keys())
    
    def get_engine_capabilities(self, engine_type: BackupEngine) -> EngineCapabilities:
        """
        Get capabilities for a specific engine.
        
        Args:
            engine_type: Type of backup engine
            
        Returns:
            EngineCapabilities describing engine features
            
        Raises:
            PluginError: If engine is not registered or available
        """
        plugin = self.get_plugin(engine_type)
        return plugin.get_capabilities()
    
    def get_engines_supporting_storage(self, storage_type: str) -> List[BackupEngine]:
        """
        Get list of engines that support a specific storage backend.
        
        Args:
            storage_type: Storage backend type (e.g., 's3', 'local')
            
        Returns:
            List of BackupEngine types supporting the storage type
        """
        supporting_engines = []
        for engine_type in self.get_available_engines():
            try:
                plugin = self.get_plugin(engine_type)
                if plugin.supports_storage_type(storage_type):
                    supporting_engines.append(engine_type)
            except Exception as e:
                logger.warning(
                    f"Error checking storage support for {engine_type.value}: {e}"
                )
        return supporting_engines
    
    def unregister_plugin(self, engine_type: BackupEngine) -> bool:
        """
        Unregister a plugin.
        
        Args:
            engine_type: Type of backup engine to unregister
            
        Returns:
            True if plugin was unregistered, False if not found
        """
        removed = False
        
        if engine_type in self._plugin_classes:
            del self._plugin_classes[engine_type]
            removed = True
            logger.debug(f"Unregistered plugin class for {engine_type.value}")
        
        if engine_type in self._plugins:
            del self._plugins[engine_type]
            logger.debug(f"Removed plugin instance for {engine_type.value}")
        
        return removed
    
    def clear(self) -> None:
        """Clear all registered plugins"""
        self._plugins.clear()
        self._plugin_classes.clear()
        logger.debug("Cleared all plugins from registry")
    
    def get_plugin_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get information about all registered plugins.
        
        Returns:
            Dictionary mapping engine names to plugin information
        """
        info = {}
        for engine_type, plugin_class in self._plugin_classes.items():
            try:
                plugin = self.get_plugin(engine_type)
                capabilities = plugin.get_capabilities()
                
                info[engine_type.value] = {
                    'name': plugin.engine_name,
                    'version': plugin.engine_version,
                    'available': plugin.is_available(),
                    'capabilities': {
                        'encryption': capabilities.supports_encryption,
                        'deduplication': capabilities.supports_deduplication,
                        'compression': capabilities.supports_compression,
                        'snapshots': capabilities.supports_snapshots,
                        'incremental': capabilities.supports_incremental,
                        'verification': capabilities.supports_verification,
                        'retention_policies': capabilities.supports_retention_policies,
                        'tags': capabilities.supports_tags,
                    },
                    'storage_backends': capabilities.storage_backends
                }
            except Exception as e:
                info[engine_type.value] = {
                    'name': engine_type.value,
                    'available': False,
                    'error': str(e)
                }
        
        return info


# Global registry instance
_global_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """
    Get the global plugin registry instance.
    
    Returns:
        Global PluginRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry
