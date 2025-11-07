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
Plugin System Initializer

This module provides utilities for initializing and managing the backup engine
plugin system.
"""

import logging
from typing import List, Dict, Any

from ..interfaces.backup_engine_plugin import BackupEngine
from .plugin_registry import get_plugin_registry
from .plugins import ResticEnginePlugin, RsyncEnginePlugin, RcloneEnginePlugin

logger = logging.getLogger(__name__)


def initialize_plugins() -> None:
    """
    Initialize the plugin system with built-in backup engine plugins.
    
    This function registers all built-in plugins (Restic, Rsync, Rclone)
    with the global plugin registry.
    """
    registry = get_plugin_registry()
    
    try:
        # Register built-in plugins
        registry.register_plugin(ResticEnginePlugin)
        logger.debug("Registered Restic plugin")
        
        registry.register_plugin(RsyncEnginePlugin)
        logger.debug("Registered Rsync plugin")
        
        registry.register_plugin(RcloneEnginePlugin)
        logger.debug("Registered Rclone plugin")
        
        logger.info("Plugin system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize plugin system: {e}")
        raise


def get_available_engines_info() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all available backup engines.
    
    Returns:
        Dictionary mapping engine names to their information including
        availability, version, and capabilities
    """
    registry = get_plugin_registry()
    return registry.get_plugin_info()


def check_engine_availability(engine: BackupEngine) -> bool:
    """
    Check if a specific backup engine is available on the system.
    
    Args:
        engine: Backup engine to check
        
    Returns:
        True if engine is available, False otherwise
    """
    registry = get_plugin_registry()
    return registry.is_engine_available(engine)


def get_engines_for_storage(storage_type: str) -> List[BackupEngine]:
    """
    Get list of engines that support a specific storage backend.
    
    Args:
        storage_type: Storage backend type (e.g., 's3', 'local', 'sftp')
        
    Returns:
        List of BackupEngine types that support the storage type
    """
    registry = get_plugin_registry()
    return registry.get_engines_supporting_storage(storage_type)


def print_plugin_status() -> None:
    """
    Print status information about all registered plugins.
    
    This is useful for debugging and system diagnostics.
    """
    info = get_available_engines_info()
    
    print("\n=== Backup Engine Plugin Status ===\n")
    
    for engine_name, engine_info in info.items():
        print(f"Engine: {engine_name}")
        print(f"  Available: {engine_info.get('available', False)}")
        
        if engine_info.get('available'):
            print(f"  Version: {engine_info.get('version', 'unknown')}")
            
            capabilities = engine_info.get('capabilities', {})
            print("  Capabilities:")
            for cap_name, cap_value in capabilities.items():
                if cap_value:
                    print(f"    - {cap_name}")
            
            backends = engine_info.get('storage_backends', [])
            if backends:
                print(f"  Storage Backends: {', '.join(backends)}")
        else:
            error = engine_info.get('error', 'Unknown error')
            print(f"  Error: {error}")
        
        print()
