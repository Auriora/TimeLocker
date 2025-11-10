#!/usr/bin/env python3
"""
Selective Recovery Demo

This example demonstrates selective recovery operations with different
selection criteria including:
- Pattern-based file selection
- Size and date range filtering
- Selection template usage
- Multiple selection strategies
- Verification of selective restoration

Copyright © Bruce Cherrington
Licensed under GPL v3
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
from TimeLocker.snapshot_browser import SnapshotBrowser, SearchCriteria
from TimeLocker.interfaces.recovery_models import (
    SelectionCriteria,
    RecoveryOptions,
    FileType,
    SizeRange,
    DateRange,
    ConflictResolution
)
from TimeLocker.backup_repository import BackupRepository


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def demo_pattern_based_selection():
    """Demonstrate pattern-based file selection"""
    print_section("Pattern-Based Selection")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    browser = SnapshotBrowser(repository)
    
    # Get latest snapshot
    snapshots = repository.snapshots()
    if not snapshots:
        print("✗ No snapshots found")
        return
    
    snapshot_id = snapshots[0].id
    print(f"Using snapshot: {snapshot_id}")
    
    # Example 1: Restore only PDF documents
    print("\n1. Restoring PDF documents only...")
    criteria = SelectionCriteria(
        include_patterns=["*.pdf", "**/*.pdf"],
        exclude_patterns=[]
    )
    
    # Preview what will be restored
    search_criteria = SearchCriteria(name_pattern="*.pdf")
    matching_files = browser.search_snapshot_files(snapshot_id, search_criteria)
    print(f"   Found {len(matching_files)} PDF files")
    
    for file_entry in matching_files[:5]:
        print(f"   - {file_entry.path} ({file_entry.size:,} bytes)")
    
    # Perform selective recovery
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "pdf_restore"
        options = RecoveryOptions(verify_integrity=True)
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery operation started: {operation.operation_id}")
        
    finally:
        shutil.rmtree(temp_dir)
    
    # Example 2: Restore documents excluding temporary files
    print("\n2. Restoring documents excluding temporary files...")
    criteria = SelectionCriteria(
        include_patterns=["*.pdf", "*.docx", "*.xlsx"],
        exclude_patterns=["*.tmp", "*~", "*/temp/*", "*/.cache/*"]
    )
    
    print("   Include patterns:")
    for pattern in criteria.include_patterns:
        print(f"     + {pattern}")
    
    print("   Exclude patterns:")
    for pattern in criteria.exclude_patterns:
        print(f"     - {pattern}")
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "documents_restore"
        options = RecoveryOptions()
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery operation started: {operation.operation_id}")
        
    finally:
        shutil.rmtree(temp_dir)
    
    # Example 3: Restore specific directory tree
    print("\n3. Restoring specific directory tree...")
    criteria = SelectionCriteria(
        include_patterns=["/home/user/projects/**"],
        exclude_patterns=["/home/user/projects/*/node_modules/**"]
    )
    
    print(f"   Restoring: /home/user/projects/")
    print(f"   Excluding: node_modules directories")
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "projects_restore"
        options = RecoveryOptions(preserve_permissions=True)
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery operation started: {operation.operation_id}")
        
    finally:
        shutil.rmtree(temp_dir)


def demo_size_and_date_filtering():
    """Demonstrate size and date range filtering"""
    print_section("Size and Date Range Filtering")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    browser = SnapshotBrowser(repository)
    
    snapshots = repository.snapshots()
    if not snapshots:
        print("✗ No snapshots found")
        return
    
    snapshot_id = snapshots[0].id
    
    # Example 1: Restore files within size range
    print("\n1. Restoring files between 1KB and 10MB...")
    criteria = SelectionCriteria(
        include_patterns=["**/*"],
        size_range=SizeRange(
            min_size=1024,           # 1 KB
            max_size=10 * 1024 * 1024  # 10 MB
        ),
        file_types=[FileType.FILE]
    )
    
    # Preview matching files
    search_criteria = SearchCriteria(
        size_range=criteria.size_range,
        file_types=criteria.file_types
    )
    matching_files = browser.search_snapshot_files(snapshot_id, search_criteria)
    print(f"   Found {len(matching_files)} files in size range")
    
    # Show size distribution
    if matching_files:
        sizes = [f.size for f in matching_files]
        print(f"   Smallest: {min(sizes):,} bytes")
        print(f"   Largest: {max(sizes):,} bytes")
        print(f"   Average: {sum(sizes) // len(sizes):,} bytes")
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "size_filtered_restore"
        options = RecoveryOptions()
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery operation started: {operation.operation_id}")
        
    finally:
        shutil.rmtree(temp_dir)
    
    # Example 2: Restore recently modified files
    print("\n2. Restoring files modified in last 30 days...")
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    criteria = SelectionCriteria(
        include_patterns=["**/*"],
        date_range=DateRange(
            start_date=thirty_days_ago,
            end_date=datetime.now()
        ),
        file_types=[FileType.FILE]
    )
    
    # Preview matching files
    search_criteria = SearchCriteria(
        date_range=criteria.date_range,
        file_types=criteria.file_types
    )
    matching_files = browser.search_snapshot_files(snapshot_id, search_criteria)
    print(f"   Found {len(matching_files)} recently modified files")
    
    if matching_files:
        print("   Sample files:")
        for file_entry in matching_files[:5]:
            days_ago = (datetime.now() - file_entry.modification_time).days
            print(f"     - {file_entry.name} (modified {days_ago} days ago)")
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "recent_files_restore"
        options = RecoveryOptions()
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery operation started: {operation.operation_id}")
        
    finally:
        shutil.rmtree(temp_dir)
    
    # Example 3: Combined size and date filtering
    print("\n3. Restoring large recent files...")
    criteria = SelectionCriteria(
        include_patterns=["**/*"],
        size_range=SizeRange(min_size=5 * 1024 * 1024),  # > 5 MB
        date_range=DateRange(start_date=thirty_days_ago),
        file_types=[FileType.FILE]
    )
    
    print(f"   Criteria: Files > 5MB modified in last 30 days")
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "large_recent_restore"
        options = RecoveryOptions()
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery operation started: {operation.operation_id}")
        
    finally:
        shutil.rmtree(temp_dir)


def demo_selection_template_usage():
    """Demonstrate using selection templates"""
    print_section("Selection Template Usage")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    
    snapshots = repository.snapshots()
    if not snapshots:
        print("✗ No snapshots found")
        return
    
    snapshot_id = snapshots[0].id
    
    # Example 1: Use predefined template
    print("\n1. Using 'documents' selection template...")
    criteria = SelectionCriteria(
        selection_template_id="documents-template"
    )
    
    print("   Template includes:")
    print("     - Office documents (*.docx, *.xlsx, *.pptx)")
    print("     - PDFs (*.pdf)")
    print("     - Text files (*.txt, *.md)")
    print("   Template excludes:")
    print("     - Temporary files")
    print("     - Cache directories")
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "template_restore"
        options = RecoveryOptions()
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery operation started: {operation.operation_id}")
        
    finally:
        shutil.rmtree(temp_dir)
    
    # Example 2: Template with additional patterns
    print("\n2. Using template with additional patterns...")
    criteria = SelectionCriteria(
        selection_template_id="documents-template",
        include_patterns=["*.odt", "*.ods"],  # Add LibreOffice formats
        exclude_patterns=["*/archive/*"]       # Exclude archive directory
    )
    
    print("   Base template: documents-template")
    print("   Additional includes: *.odt, *.ods")
    print("   Additional excludes: */archive/*")
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "extended_template_restore"
        options = RecoveryOptions()
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery operation started: {operation.operation_id}")
        
    finally:
        shutil.rmtree(temp_dir)


def demo_verification_strategies():
    """Demonstrate verification of selective restoration"""
    print_section("Verification Strategies")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    
    snapshots = repository.snapshots()
    if not snapshots:
        print("✗ No snapshots found")
        return
    
    snapshot_id = snapshots[0].id
    
    # Example 1: Restore with integrity verification
    print("\n1. Selective restore with integrity verification...")
    criteria = SelectionCriteria(
        include_patterns=["*.pdf"],
        file_types=[FileType.FILE]
    )
    
    options = RecoveryOptions(
        verify_integrity=True,
        continue_on_error=True
    )
    
    temp_dir = Path(tempfile.mkdtemp())
    try:
        target_path = temp_dir / "verified_restore"
        
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id=snapshot_id,
            selection_criteria=criteria,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   ✓ Recovery with verification started: {operation.operation_id}")
        print(f"   Verification enabled: {options.verify_integrity}")
        
        # Check validation results
        if operation.validation_result:
            result = operation.validation_result
            print(f"   Files validated: {result.validated_files}")
            print(f"   Validation status: {'PASSED' if result.is_valid else 'FAILED'}")
        
    finally:
        shutil.rmtree(temp_dir)
    
    # Example 2: Dry run to preview selection
    print("\n2. Dry run to preview selective restoration...")
    criteria = SelectionCriteria(
        include_patterns=["*.jpg", "*.png"],
        size_range=SizeRange(max_size=5 * 1024 * 1024)  # < 5 MB
    )
    
    # Note: Dry run would be implemented in RecoveryOptions
    print("   Selection criteria:")
    print(f"     Include: {', '.join(criteria.include_patterns)}")
    print(f"     Max size: 5 MB")
    print("   Dry run mode: Preview only, no files restored")


def main():
    """Run all selective recovery demos"""
    print("\n" + "=" * 80)
    print("  TimeLocker Selective Recovery Demo")
    print("=" * 80)
    print("\nThis demo showcases various selective recovery strategies including")
    print("pattern-based selection, size/date filtering, and template usage.\n")
    
    try:
        demo_pattern_based_selection()
        demo_size_and_date_filtering()
        demo_selection_template_usage()
        demo_verification_strategies()
        
        print_section("Demo Summary")
        print("✓ Pattern-based file selection demonstrated")
        print("✓ Size and date range filtering shown")
        print("✓ Selection template usage illustrated")
        print("✓ Verification strategies explained")
        print("\nSelective recovery demo completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
