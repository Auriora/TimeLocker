#!/usr/bin/env python3
"""
Plugin System Demo

This script demonstrates the backup engine plugin system functionality,
showing how to discover, query, and use different backup engines.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from TimeLocker.interfaces.backup_engine_plugin import BackupEngine
from TimeLocker.services import (
    initialize_plugins,
    get_available_engines_info,
    check_engine_availability,
    get_engines_for_storage,
    get_plugin_registry
)


def main():
    """Demonstrate plugin system functionality"""
    
    print("=" * 70)
    print("TimeLocker Backup Engine Plugin System Demo")
    print("=" * 70)
    print()
    
    # Initialize the plugin system
    print("1. Initializing plugin system...")
    try:
        initialize_plugins()
        print("   ✓ Plugin system initialized successfully")
    except Exception as e:
        print(f"   ✗ Failed to initialize plugins: {e}")
        return 1
    
    print()
    
    # Get plugin registry
    registry = get_plugin_registry()
    
    # Display registered engines
    print("2. Registered Backup Engines:")
    registered = registry.get_registered_engines()
    for engine in registered:
        print(f"   - {engine.value}")
    print()
    
    # Check availability of each engine
    print("3. Engine Availability Check:")
    for engine in registered:
        available = check_engine_availability(engine)
        status = "✓ Available" if available else "✗ Not Available"
        print(f"   {engine.value:10s} : {status}")
    print()
    
    # Display detailed information about available engines
    print("4. Detailed Engine Information:")
    engine_info = get_available_engines_info()
    
    for engine_name, info in engine_info.items():
        print(f"\n   Engine: {engine_name}")
        print(f"   {'─' * 60}")
        
        if info.get('available'):
            print(f"   Status:  Available")
            print(f"   Version: {info.get('version', 'unknown')}")
            
            capabilities = info.get('capabilities', {})
            print(f"   Capabilities:")
            for cap_name, cap_value in capabilities.items():
                symbol = "✓" if cap_value else "✗"
                print(f"     {symbol} {cap_name.replace('_', ' ').title()}")
            
            backends = info.get('storage_backends', [])
            if backends:
                print(f"   Storage Backends: {', '.join(backends[:5])}")
                if len(backends) > 5:
                    print(f"                     ... and {len(backends) - 5} more")
        else:
            print(f"   Status: Not Available")
            print(f"   Reason: {info.get('error', 'Unknown')}")
    
    print()
    
    # Query engines by storage type
    print("5. Engines Supporting Specific Storage Types:")
    storage_types = ['local', 's3', 'b2', 'sftp']
    
    for storage_type in storage_types:
        engines = get_engines_for_storage(storage_type)
        engine_names = [e.value for e in engines]
        print(f"   {storage_type:10s} : {', '.join(engine_names) if engine_names else 'none'}")
    
    print()
    
    # Test plugin retrieval and validation
    print("6. Plugin Validation Tests:")
    
    # Test Restic plugin if available
    if check_engine_availability(BackupEngine.RESTIC):
        print("\n   Testing Restic Plugin:")
        try:
            plugin = registry.get_plugin(BackupEngine.RESTIC)
            
            # Test URI validation
            test_uris = [
                '/local/path',
                's3:s3.amazonaws.com/my-bucket',
                'invalid://bad-uri'
            ]
            
            for uri in test_uris:
                result = plugin.validate_uri(uri)
                status = "✓ Valid" if result.is_valid else "✗ Invalid"
                print(f"     {status}: {uri}")
                if result.errors:
                    for error in result.errors:
                        print(f"       Error: {error}")
        
        except Exception as e:
            print(f"     Error testing Restic plugin: {e}")
    
    # Test Rsync plugin if available
    if check_engine_availability(BackupEngine.RSYNC):
        print("\n   Testing Rsync Plugin:")
        try:
            plugin = registry.get_plugin(BackupEngine.RSYNC)
            
            # Test configuration validation
            test_configs = [
                {'archive_mode': True, 'compress': True},
                {'transfers': 'invalid'},  # Should fail
            ]
            
            for i, config in enumerate(test_configs, 1):
                result = plugin.validate_configuration(config)
                status = "✓ Valid" if result.is_valid else "✗ Invalid"
                print(f"     Config {i}: {status}")
                if result.errors:
                    for error in result.errors:
                        print(f"       Error: {error}")
        
        except Exception as e:
            print(f"     Error testing Rsync plugin: {e}")
    
    print()
    print("=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
