#!/usr/bin/env python3
"""
Snapshot Browser Demo

This example demonstrates the snapshot browsing capabilities of TimeLocker,
including listing snapshot contents, searching for files, comparing snapshots,
and retrieving detailed file metadata.

Copyright © Bruce Cherrington
Licensed under GPL v3
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.snapshot_browser import (
    SnapshotBrowser,
    PaginationOptions,
    SearchCriteria,
    FileMetadata
)
from TimeLocker.interfaces.recovery_models import (
    FileType,
    SizeRange,
    DateRange
)
from TimeLocker.restic.local import LocalRepository


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def demo_list_snapshot_contents():
    """Demonstrate listing snapshot contents with pagination"""
    print_section("1. Listing Snapshot Contents")
    
    # Initialize repository and browser
    repo = LocalRepository(
        location="/tmp/demo-repo",
        password="demo-password"
    )
    browser = SnapshotBrowser(repo)
    
    # Get latest snapshot
    snapshots = repo.snapshots()
    if not snapshots:
        print("No snapshots found in repository")
        return
    
    snapshot_id = snapshots[0].id
    print(f"Browsing snapshot: {snapshot_id}")
    print(f"Timestamp: {snapshots[0].timestamp}")
    
    # List root directory
    print("\n--- Root Directory ---")
    listing = browser.list_snapshot_contents(snapshot_id, path="/")
    print(f"Total entries: {listing.total_entries}")
    
    for entry in listing.entries[:10]:  # Show first 10
        type_icon = "📁" if entry.type == FileType.DIRECTORY else "📄"
        size_str = f"{entry.size:,} bytes" if entry.type == FileType.FILE else ""
        print(f"{type_icon} {entry.name:40} {size_str:>15} {entry.permissions}")
    
    # Demonstrate pagination
    print("\n--- Paginated Listing (Page 1, 5 items per page) ---")
    pagination = PaginationOptions(page=1, page_size=5)
    paginated_listing = browser.list_snapshot_contents(
        snapshot_id,
        path="/",
        pagination=pagination
    )
    
    if paginated_listing.pagination_info:
        pinfo = paginated_listing.pagination_info
        print(f"Page {pinfo.current_page} of {pinfo.total_pages}")
        print(f"Showing {len(paginated_listing.entries)} of {pinfo.total_entries} entries")
        print(f"Has next page: {pinfo.has_next}")
    
    for entry in paginated_listing.entries:
        print(f"  - {entry.name}")


def demo_search_snapshot_files():
    """Demonstrate searching for files within snapshots"""
    print_section("2. Searching Snapshot Files")
    
    repo = LocalRepository(
        location="/tmp/demo-repo",
        password="demo-password"
    )
    browser = SnapshotBrowser(repo)
    
    snapshots = repo.snapshots()
    if not snapshots:
        print("No snapshots found in repository")
        return
    
    snapshot_id = snapshots[0].id
    
    # Search by name pattern
    print("--- Search for Python files (*.py) ---")
    criteria = SearchCriteria(
        name_pattern="*.py",
        case_sensitive=False
    )
    
    results = browser.search_snapshot_files(snapshot_id, criteria)
    print(f"Found {len(results)} Python files")
    
    for entry in results[:5]:  # Show first 5
        print(f"  {entry.path}")
        print(f"    Size: {entry.size:,} bytes")
        print(f"    Modified: {entry.modification_time}")
    
    # Search by file type and size
    print("\n--- Search for large files (>1MB) ---")
    criteria = SearchCriteria(
        file_types=[FileType.FILE],
        size_range=SizeRange(min_size=1024 * 1024)  # 1MB
    )
    
    results = browser.search_snapshot_files(snapshot_id, criteria)
    print(f"Found {len(results)} files larger than 1MB")
    
    for entry in sorted(results, key=lambda e: e.size, reverse=True)[:5]:
        print(f"  {entry.name}: {entry.size / (1024*1024):.2f} MB")
    
    # Search by date range
    print("\n--- Search for recently modified files (last 7 days) ---")
    seven_days_ago = datetime.now() - timedelta(days=7)
    criteria = SearchCriteria(
        date_range=DateRange(start_date=seven_days_ago)
    )
    
    results = browser.search_snapshot_files(snapshot_id, criteria)
    print(f"Found {len(results)} files modified in the last 7 days")
    
    for entry in results[:5]:
        days_ago = (datetime.now() - entry.modification_time).days
        print(f"  {entry.name} (modified {days_ago} days ago)")


def demo_compare_snapshots():
    """Demonstrate comparing multiple snapshots"""
    print_section("3. Comparing Snapshots")
    
    repo = LocalRepository(
        location="/tmp/demo-repo",
        password="demo-password"
    )
    browser = SnapshotBrowser(repo)
    
    snapshots = repo.snapshots()
    if len(snapshots) < 2:
        print("Need at least 2 snapshots for comparison")
        return
    
    # Compare first and last snapshot
    snapshot_ids = [snapshots[-1].id, snapshots[0].id]
    print(f"Comparing snapshots:")
    print(f"  Older: {snapshots[-1].id} ({snapshots[-1].timestamp})")
    print(f"  Newer: {snapshots[0].id} ({snapshots[0].timestamp})")
    
    comparison = browser.compare_snapshots(snapshot_ids, path="/")
    
    print(f"\n--- Comparison Results ---")
    print(f"Added files: {len(comparison.added_files)}")
    print(f"Removed files: {len(comparison.removed_files)}")
    print(f"Modified files: {len(comparison.modified_files)}")
    print(f"Unchanged files: {len(comparison.unchanged_files)}")
    
    if comparison.added_files:
        print("\n--- Sample Added Files ---")
        for entry in comparison.added_files[:5]:
            print(f"  + {entry.path}")
    
    if comparison.removed_files:
        print("\n--- Sample Removed Files ---")
        for entry in comparison.removed_files[:5]:
            print(f"  - {entry.path}")
    
    if comparison.modified_files:
        print("\n--- Sample Modified Files ---")
        for old_entry, new_entry in comparison.modified_files[:5]:
            size_change = new_entry.size - old_entry.size
            change_str = f"+{size_change}" if size_change > 0 else str(size_change)
            print(f"  ~ {new_entry.path}")
            print(f"    Size change: {change_str} bytes")
            print(f"    Old: {old_entry.modification_time}")
            print(f"    New: {new_entry.modification_time}")


def demo_get_file_metadata():
    """Demonstrate retrieving detailed file metadata"""
    print_section("4. Retrieving File Metadata")
    
    repo = LocalRepository(
        location="/tmp/demo-repo",
        password="demo-password"
    )
    browser = SnapshotBrowser(repo)
    
    snapshots = repo.snapshots()
    if not snapshots:
        print("No snapshots found in repository")
        return
    
    snapshot_id = snapshots[0].id
    
    # List some files to get paths
    listing = browser.list_snapshot_contents(snapshot_id, path="/")
    
    if not listing.entries:
        print("No files found in snapshot")
        return
    
    # Get metadata for first file
    file_entry = listing.entries[0]
    print(f"Getting metadata for: {file_entry.path}")
    
    try:
        metadata = browser.get_file_metadata(snapshot_id, file_entry.path)
        
        print(f"\n--- File Metadata ---")
        print(f"Path: {metadata.file_entry.path}")
        print(f"Name: {metadata.file_entry.name}")
        print(f"Type: {metadata.file_entry.type.value}")
        print(f"Size: {metadata.file_entry.size:,} bytes")
        print(f"Permissions: {metadata.file_entry.permissions}")
        print(f"Modified: {metadata.file_entry.modification_time}")
        
        if metadata.file_entry.checksum:
            print(f"Checksum: {metadata.file_entry.checksum[:16]}...")
        
        if metadata.inode:
            print(f"Inode: {metadata.inode}")
        
        if metadata.user:
            print(f"Owner: {metadata.user}")
        
        if metadata.group:
            print(f"Group: {metadata.group}")
        
        # Demonstrate caching
        print("\n--- Testing Cache Performance ---")
        import time
        
        # First call (not cached)
        start = time.time()
        browser.get_file_metadata(snapshot_id, file_entry.path)
        first_call = time.time() - start
        
        # Second call (cached)
        start = time.time()
        browser.get_file_metadata(snapshot_id, file_entry.path)
        second_call = time.time() - start
        
        print(f"First call: {first_call*1000:.2f}ms")
        print(f"Second call (cached): {second_call*1000:.2f}ms")
        print(f"Speedup: {first_call/second_call:.1f}x")
        
    except Exception as e:
        print(f"Error retrieving metadata: {e}")


def demo_cache_management():
    """Demonstrate cache management"""
    print_section("5. Cache Management")
    
    repo = LocalRepository(
        location="/tmp/demo-repo",
        password="demo-password"
    )
    browser = SnapshotBrowser(repo)
    
    snapshots = repo.snapshots()
    if not snapshots:
        print("No snapshots found in repository")
        return
    
    snapshot_id = snapshots[0].id
    
    # Populate cache
    print("Populating cache...")
    listing1 = browser.list_snapshot_contents(snapshot_id, path="/")
    listing2 = browser.list_snapshot_contents(snapshot_id, path="/home")
    
    print(f"Cached {len(browser._listing_cache)} listings")
    
    # Clear cache
    print("\nClearing cache...")
    browser.clear_cache()
    
    print(f"Cache size after clear: {len(browser._listing_cache)} listings")
    print("Cache cleared successfully")


def main():
    """Run all demo examples"""
    print("\n" + "=" * 80)
    print("  TimeLocker Snapshot Browser Demo")
    print("=" * 80)
    
    try:
        demo_list_snapshot_contents()
        demo_search_snapshot_files()
        demo_compare_snapshots()
        demo_get_file_metadata()
        demo_cache_management()
        
        print("\n" + "=" * 80)
        print("  Demo completed successfully!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
