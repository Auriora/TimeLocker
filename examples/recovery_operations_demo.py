#!/usr/bin/env python3
"""
TimeLocker Recovery Operations Demo

This script demonstrates the Phase 3 recovery functionality:
- Snapshot listing and filtering
- Snapshot selection by various criteria
- Full restore operations with verification
- Error handling for recovery edge cases
"""

import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for demo
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.snapshot_manager import SnapshotManager, SnapshotFilter
from TimeLocker.restore_manager import RestoreManager, RestoreOptions, ConflictResolution
from TimeLocker.recovery_errors import SnapshotNotFoundError, RestoreError

# Import test repository for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
from tests.TimeLocker.recovery.mock_recovery_repository import MockRecoveryRepository


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def print_snapshot_info(snapshot):
    """Print formatted snapshot information"""
    print(f"  ID: {snapshot.id}")
    print(f"  Timestamp: {snapshot.timestamp}")
    print(f"  Paths: {[str(p) for p in snapshot.paths]}")
    print(f"  Tags: {getattr(snapshot, 'tags', [])}")
    print(f"  Size: {getattr(snapshot, 'size', 0)} bytes")


def demo_snapshot_listing():
    """Demonstrate snapshot listing and filtering"""
    print_section("Snapshot Listing and Filtering")

    # Initialize repository and managers
    repository = MockRecoveryRepository()
    snapshot_manager = SnapshotManager(repository)

    print("1. List all snapshots:")
    snapshots = snapshot_manager.list_snapshots()
    for i, snapshot in enumerate(snapshots, 1):
        print(f"\nSnapshot {i}:")
        print_snapshot_info(snapshot)

    print(f"\nTotal snapshots found: {len(snapshots)}")

    print("\n2. Filter snapshots by tags (full backups only):")
    filter_criteria = SnapshotFilter().with_tags(["full"])
    full_snapshots = snapshot_manager.list_snapshots(filter_criteria)
    for snapshot in full_snapshots:
        print(f"  - {snapshot.id} ({snapshot.timestamp})")

    print("\n3. Filter snapshots by date (last 5 days):")
    date_from = datetime.now() - timedelta(days=5)
    filter_criteria = SnapshotFilter().with_date_range(date_from=date_from)
    recent_snapshots = snapshot_manager.list_snapshots(filter_criteria)
    for snapshot in recent_snapshots:
        print(f"  - {snapshot.id} ({snapshot.timestamp})")

    print("\n4. Get latest snapshot:")
    latest = snapshot_manager.get_latest_snapshot()
    if latest:
        print(f"  Latest snapshot: {latest.id} ({latest.timestamp})")

    print("\n5. Get snapshot by ID:")
    try:
        specific_snapshot = snapshot_manager.get_snapshot_by_id("abc123")
        print(f"  Found snapshot: {specific_snapshot.id}")
    except SnapshotNotFoundError as e:
        print(f"  Error: {e}")


def demo_restore_operations():
    """Demonstrate restore operations"""
    print_section("Restore Operations")

    # Initialize components
    repository = MockRecoveryRepository()
    snapshot_manager = SnapshotManager(repository)
    restore_manager = RestoreManager(repository, snapshot_manager)

    # Create temporary directory for restore testing
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Using temporary directory: {temp_dir}")

    try:
        print("\n1. Basic restore operation:")
        target_path = temp_dir / "basic_restore"
        options = RestoreOptions().with_target_path(target_path)

        result = restore_manager.restore_snapshot("abc123", options)
        print(f"  Success: {result.success}")
        print(f"  Duration: {result.duration_seconds:.2f} seconds")
        print(f"  Files restored: {result.files_restored}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")

        print("\n2. Restore with verification:")
        target_path = temp_dir / "verified_restore"
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_verification(True))

        result = restore_manager.restore_snapshot("def456", options)
        print(f"  Success: {result.success}")
        print(f"  Verification passed: {result.verification_passed}")

        print("\n3. Dry run restore:")
        target_path = temp_dir / "dry_run_restore"
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_dry_run(True))

        result = restore_manager.restore_snapshot("ghi789", options)
        print(f"  Dry run success: {result.success}")
        print(f"  Target directory created: {target_path.exists()}")

        print("\n4. Restore latest snapshot:")
        target_path = temp_dir / "latest_restore"
        options = RestoreOptions().with_target_path(target_path)

        result = restore_manager.restore_latest_snapshot(options)
        print(f"  Latest restore success: {result.success}")
        print(f"  Snapshot ID: {result.snapshot_id}")

        print("\n5. Restore with include/exclude paths:")
        target_path = temp_dir / "selective_restore"
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_include_paths([Path("/home/user/documents")])
                   .with_exclude_paths([Path("/home/user/photos")]))

        result = restore_manager.restore_snapshot("abc123", options)
        print(f"  Selective restore success: {result.success}")

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")


def demo_error_handling():
    """Demonstrate error handling scenarios"""
    print_section("Error Handling Scenarios")

    repository = MockRecoveryRepository()
    snapshot_manager = SnapshotManager(repository)
    restore_manager = RestoreManager(repository, snapshot_manager)

    print("1. Snapshot not found error:")
    try:
        snapshot = snapshot_manager.get_snapshot_by_id("nonexistent")
    except SnapshotNotFoundError as e:
        print(f"  Caught expected error: {e}")

    print("\n2. Restore without target path:")
    options = RestoreOptions()  # No target path specified
    result = restore_manager.restore_snapshot("abc123", options)
    print(f"  Success: {result.success}")
    print(f"  Errors: {result.errors}")

    print("\n3. Repository restore failure:")
    repository.set_restore_failure(True)
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "failed_restore"
        options = RestoreOptions().with_target_path(target_path)
        result = restore_manager.restore_snapshot("abc123", options)
        print(f"  Success: {result.success}")
        print(f"  Errors: {result.errors}")
    finally:
        shutil.rmtree(temp_dir)
        repository.set_restore_failure(False)  # Reset for other demos

    print("\n4. Snapshot listing failure:")
    repository.set_snapshots_failure(True)
    try:
        snapshots = snapshot_manager.list_snapshots()
    except Exception as e:
        print(f"  Caught expected error: {type(e).__name__}: {e}")
    finally:
        repository.set_snapshots_failure(False)


def demo_advanced_features():
    """Demonstrate advanced recovery features"""
    print_section("Advanced Recovery Features")

    repository = MockRecoveryRepository()
    snapshot_manager = SnapshotManager(repository)
    restore_manager = RestoreManager(repository, snapshot_manager)

    print("1. Snapshot summary information:")
    snapshot = snapshot_manager.get_snapshot_by_id("abc123")
    summary = snapshot_manager.get_snapshot_summary(snapshot)
    print(f"  Snapshot summary:")
    for key, value in summary.items():
        print(f"    {key}: {value}")

    print("\n2. Combined filtering:")
    filter_criteria = (SnapshotFilter()
                       .with_tags(["documents"])
                       .with_date_range(datetime.now() - timedelta(days=10))
                       .with_max_results(2))

    filtered_snapshots = snapshot_manager.list_snapshots(filter_criteria)
    print(f"  Found {len(filtered_snapshots)} snapshots matching combined criteria")

    print("\n3. Snapshot caching:")
    # First call - loads from repository
    start_time = datetime.now()
    snapshots1 = snapshot_manager.list_snapshots()
    first_duration = (datetime.now() - start_time).total_seconds()

    # Second call - uses cache
    start_time = datetime.now()
    snapshots2 = snapshot_manager.list_snapshots()
    second_duration = (datetime.now() - start_time).total_seconds()

    print(f"  First call duration: {first_duration:.4f}s")
    print(f"  Second call duration: {second_duration:.4f}s")
    print(f"  Cache effectiveness: {len(snapshots1) == len(snapshots2)}")

    print("\n4. Progress callback demonstration:")

    def progress_callback(message, current, total):
        if total > 0:
            percent = (current / total) * 100
            print(f"    Progress: {message} - {percent:.1f}% ({current}/{total})")
        else:
            print(f"    Progress: {message}")

    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "progress_restore"
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_progress_callback(progress_callback))

        print("  Starting restore with progress callback:")
        result = restore_manager.restore_snapshot("abc123", options)
        print(f"  Restore completed: {result.success}")
    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all recovery operations demonstrations"""
    print("TimeLocker Recovery Operations Demo")
    print("This demo showcases Phase 3 recovery functionality")

    try:
        demo_snapshot_listing()
        demo_restore_operations()
        demo_error_handling()
        demo_advanced_features()

        print_section("Demo Completed Successfully")
        print("All recovery operations demonstrated successfully!")
        print("\nKey features demonstrated:")
        print("✓ Snapshot listing and filtering")
        print("✓ Snapshot selection by ID, date, and tags")
        print("✓ Full restore operations")
        print("✓ Restore verification")
        print("✓ Error handling and recovery")
        print("✓ Advanced filtering and caching")
        print("✓ Progress tracking")

    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
