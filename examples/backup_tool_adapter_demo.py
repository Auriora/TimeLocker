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
Backup Tool Adapter Framework Demo

This example demonstrates how to use the backup tool adapter framework
to perform recovery operations with different backup tools (Restic, Borg, etc.)
while maintaining a consistent interface.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.adapters import ResticAdapter
from TimeLocker.interfaces.backup_tool_adapter import (
    FileSelection,
    RestoreOptions,
    ToolCapability
)


def demonstrate_tool_detection():
    """Demonstrate backup tool detection and capability discovery"""
    print("=" * 80)
    print("Backup Tool Detection and Capability Discovery")
    print("=" * 80)
    
    # Create adapter instance
    adapter = ResticAdapter(
        repository_path="/path/to/repository",
        password="your-password"
    )
    
    # Detect tool availability
    print("\n1. Detecting Restic tool...")
    is_available = adapter.detect_tool()
    print(f"   Restic available: {is_available}")
    
    # Get tool information
    print("\n2. Getting tool information...")
    tool_info = adapter.get_tool_info()
    print(f"   Tool type: {tool_info.tool_type.value}")
    print(f"   Version: {tool_info.version}")
    print(f"   Executable: {tool_info.executable_path}")
    print(f"   Available: {tool_info.is_available}")
    
    # Get capabilities
    print("\n3. Checking tool capabilities...")
    capabilities = adapter.get_capabilities()
    print(f"   Supported capabilities:")
    for capability in capabilities:
        print(f"   - {capability.value}")
    
    # Check specific capabilities
    print("\n4. Checking specific capabilities...")
    print(f"   Supports snapshot browsing: {adapter.supports_capability(ToolCapability.SNAPSHOT_BROWSING)}")
    print(f"   Supports selective restore: {adapter.supports_capability(ToolCapability.SELECTIVE_RESTORE)}")
    print(f"   Supports checksum verification: {adapter.supports_capability(ToolCapability.CHECKSUM_VERIFICATION)}")


def demonstrate_snapshot_browsing():
    """Demonstrate snapshot browsing using the adapter"""
    print("\n" + "=" * 80)
    print("Snapshot Browsing")
    print("=" * 80)
    
    # Create adapter instance
    adapter = ResticAdapter(
        repository_path="/path/to/repository",
        password="your-password"
    )
    
    # Check if tool supports browsing
    if not adapter.supports_capability(ToolCapability.SNAPSHOT_BROWSING):
        print("Tool does not support snapshot browsing")
        return
    
    print("\n1. Browsing snapshot contents...")
    try:
        # Browse root directory of snapshot
        listing = adapter.browse_snapshot(
            repository_path="/path/to/repository",
            snapshot_id="latest",
            path="/"
        )
        
        print(f"   Path: {listing.path}")
        print(f"   Total entries: {listing.total_entries}")
        print(f"\n   First 5 entries:")
        for entry in listing.entries[:5]:
            print(f"   - {entry.name} ({entry.type.value}, {entry.size} bytes)")
    
    except Exception as e:
        print(f"   Error browsing snapshot: {e}")


def demonstrate_file_restoration():
    """Demonstrate file restoration using the adapter"""
    print("\n" + "=" * 80)
    print("File Restoration")
    print("=" * 80)
    
    # Create adapter instance
    adapter = ResticAdapter(
        repository_path="/path/to/repository",
        password="your-password"
    )
    
    print("\n1. Preparing file selection...")
    # Create file selection
    selection = FileSelection(
        include_paths=["/home/user/documents"],
        exclude_patterns=["*.tmp", "*.cache"]
    )
    print(f"   Include paths: {selection.include_paths}")
    print(f"   Exclude patterns: {selection.exclude_patterns}")
    
    print("\n2. Configuring restore options...")
    # Create restore options
    options = RestoreOptions(
        target_path=Path("/restore/target"),
        overwrite_existing=False,
        preserve_permissions=True,
        preserve_timestamps=True,
        verify_after_restore=True
    )
    print(f"   Target path: {options.target_path}")
    print(f"   Overwrite existing: {options.overwrite_existing}")
    print(f"   Verify after restore: {options.verify_after_restore}")
    
    print("\n3. Executing restore operation...")
    try:
        # Execute restore
        operation = adapter.restore_files(
            repository_path="/path/to/repository",
            snapshot_id="latest",
            selection=selection,
            target_path="/restore/target",
            options=options
        )
        
        print(f"   Operation ID: {operation.operation_id}")
        print(f"   Snapshot ID: {operation.snapshot_id}")
        print(f"   Files restored: {operation.files_restored}")
        print(f"   Bytes restored: {operation.bytes_restored}")
        print(f"   Success: {operation.success}")
    
    except Exception as e:
        print(f"   Error during restore: {e}")


def demonstrate_verification():
    """Demonstrate restoration verification using the adapter"""
    print("\n" + "=" * 80)
    print("Restoration Verification")
    print("=" * 80)
    
    # Create adapter instance
    adapter = ResticAdapter(
        repository_path="/path/to/repository",
        password="your-password"
    )
    
    # Check if tool supports verification
    if not adapter.supports_capability(ToolCapability.CHECKSUM_VERIFICATION):
        print("Tool does not support checksum verification")
        return
    
    print("\n1. Verifying restored files...")
    try:
        # List of files to verify
        restored_files = [
            "/restore/target/file1.txt",
            "/restore/target/file2.txt",
            "/restore/target/subdir/file3.txt"
        ]
        
        # Verify restoration
        result = adapter.verify_restoration(
            repository_path="/path/to/repository",
            snapshot_id="latest",
            restored_files=restored_files
        )
        
        print(f"   Verified files: {result.verified_files}")
        print(f"   Failed files: {result.failed_files}")
        print(f"   Success: {result.success}")
        
        if result.checksum_mismatches:
            print(f"\n   Checksum mismatches:")
            for file_path in result.checksum_mismatches:
                print(f"   - {file_path}")
        
        if result.missing_files:
            print(f"\n   Missing files:")
            for file_path in result.missing_files:
                print(f"   - {file_path}")
    
    except Exception as e:
        print(f"   Error during verification: {e}")


def demonstrate_repository_validation():
    """Demonstrate repository validation using the adapter"""
    print("\n" + "=" * 80)
    print("Repository Validation")
    print("=" * 80)
    
    # Create adapter instance
    adapter = ResticAdapter(
        repository_path="/path/to/repository",
        password="your-password"
    )
    
    print("\n1. Validating repository...")
    try:
        is_valid = adapter.validate_repository("/path/to/repository")
        print(f"   Repository valid: {is_valid}")
    except Exception as e:
        print(f"   Error validating repository: {e}")


def demonstrate_snapshot_metadata():
    """Demonstrate snapshot metadata retrieval using the adapter"""
    print("\n" + "=" * 80)
    print("Snapshot Metadata Retrieval")
    print("=" * 80)
    
    # Create adapter instance
    adapter = ResticAdapter(
        repository_path="/path/to/repository",
        password="your-password"
    )
    
    print("\n1. Getting snapshot metadata...")
    try:
        metadata = adapter.get_snapshot_metadata(
            repository_path="/path/to/repository",
            snapshot_id="latest"
        )
        
        print(f"   Snapshot ID: {metadata.get('id', 'N/A')}")
        print(f"   Time: {metadata.get('time', 'N/A')}")
        print(f"   Hostname: {metadata.get('hostname', 'N/A')}")
        print(f"   Username: {metadata.get('username', 'N/A')}")
        print(f"   Tags: {metadata.get('tags', [])}")
    
    except Exception as e:
        print(f"   Error getting metadata: {e}")


def demonstrate_size_estimation():
    """Demonstrate restore size estimation using the adapter"""
    print("\n" + "=" * 80)
    print("Restore Size Estimation")
    print("=" * 80)
    
    # Create adapter instance
    adapter = ResticAdapter(
        repository_path="/path/to/repository",
        password="your-password"
    )
    
    print("\n1. Estimating restore size...")
    try:
        # Estimate size for full restore
        size = adapter.estimate_restore_size(
            repository_path="/path/to/repository",
            snapshot_id="latest"
        )
        
        # Convert to human-readable format
        size_mb = size / (1024 * 1024)
        size_gb = size / (1024 * 1024 * 1024)
        
        print(f"   Estimated size: {size} bytes")
        print(f"   Estimated size: {size_mb:.2f} MB")
        print(f"   Estimated size: {size_gb:.2f} GB")
    
    except Exception as e:
        print(f"   Error estimating size: {e}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 80)
    print("Backup Tool Adapter Framework Demo")
    print("=" * 80)
    print("\nThis demo shows how to use the backup tool adapter framework")
    print("to perform recovery operations with different backup tools.")
    print("\nNote: This is a demonstration with example paths.")
    print("Replace with actual repository paths and credentials to run.")
    
    # Run demonstrations
    demonstrate_tool_detection()
    demonstrate_snapshot_browsing()
    demonstrate_file_restoration()
    demonstrate_verification()
    demonstrate_repository_validation()
    demonstrate_snapshot_metadata()
    demonstrate_size_estimation()
    
    print("\n" + "=" * 80)
    print("Demo completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
