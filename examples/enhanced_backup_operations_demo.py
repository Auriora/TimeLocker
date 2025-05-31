#!/usr/bin/env python3
"""
TimeLocker Enhanced Backup Operations Demo

This script demonstrates the completed enhanced backup operations functionality:
- Advanced file selection with pattern matching and exclusions
- Retry mechanisms with exponential backoff
- Comprehensive backup verification
- Full and incremental backup operations
- Error handling and recovery
"""

import tempfile
import shutil
import logging
from pathlib import Path

# Add src to path for demo
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.backup_manager import BackupManager, BackupManagerError
from TimeLocker.file_selections import FileSelection, SelectionType, PatternGroup
from TimeLocker.backup_target import BackupTarget
from TimeLocker.restic.Repositories.local import LocalResticRepository

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_demo_files(base_path: Path):
    """Create a variety of demo files for testing"""
    logger.info(f"Creating demo files in {base_path}")

    # Create main directory structure
    (base_path / "documents").mkdir(parents=True)
    (base_path / "projects").mkdir(parents=True)
    (base_path / "temp").mkdir(parents=True)
    (base_path / "media").mkdir(parents=True)

    # Create office documents
    (base_path / "documents" / "report.pdf").write_text("Important report content")
    (base_path / "documents" / "spreadsheet.xlsx").write_text("Financial data")
    (base_path / "documents" / "presentation.pptx").write_text("Project presentation")

    # Create source code files
    (base_path / "projects" / "main.py").write_text("print('Hello, World!')")
    (base_path / "projects" / "utils.py").write_text("def helper_function(): pass")
    (base_path / "projects" / "config.json").write_text('{"setting": "value"}')

    # Create temporary files (should be excluded)
    (base_path / "temp" / "cache.tmp").write_text("Temporary cache data")
    (base_path / "temp" / "backup.bak").write_text("Old backup file")
    (base_path / "projects" / "debug.log").write_text("Debug information")

    # Create media files
    (base_path / "media" / "photo.jpg").write_text("Image data")
    (base_path / "media" / "video.mp4").write_text("Video data")

    logger.info("Demo files created successfully")


def demo_enhanced_file_selection():
    """Demonstrate enhanced file selection capabilities"""
    logger.info("=== Enhanced File Selection Demo ===")

    # Create temporary directory with demo files
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_path = Path(temp_dir) / "demo_data"
        create_demo_files(demo_path)

        # Create file selection with advanced patterns
        selection = FileSelection()

        # Include the main directory
        selection.add_path(demo_path, SelectionType.INCLUDE)

        # Use pattern groups for common file types
        selection.add_pattern_group("office_documents", SelectionType.INCLUDE)
        selection.add_pattern_group("source_code", SelectionType.INCLUDE)
        selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)

        # Exclude specific directories
        selection.add_path(demo_path / "temp", SelectionType.EXCLUDE)

        # Test file inclusion logic
        logger.info("Testing file inclusion logic:")
        test_files = [
                demo_path / "documents" / "report.pdf",  # Should be included
                demo_path / "projects" / "main.py",  # Should be included
                demo_path / "temp" / "cache.tmp",  # Should be excluded (directory)
                demo_path / "projects" / "debug.log",  # Should be excluded (pattern)
                demo_path / "media" / "photo.jpg",  # Should be included
        ]

        for file_path in test_files:
            included = selection.should_include_file(file_path)
            logger.info(f"  {file_path.name}: {'INCLUDED' if included else 'EXCLUDED'}")

        # Get backup size estimation
        stats = selection.estimate_backup_size()
        logger.info(f"Estimated backup size: {stats['total_size']} bytes, "
                    f"{stats['file_count']} files, {stats['directory_count']} directories")

        # Show effective paths
        effective_paths = selection.get_effective_paths()
        logger.info(f"Files to be backed up: {len(effective_paths['included'])}")
        logger.info(f"Files to be excluded: {len(effective_paths['excluded'])}")


def demo_backup_with_retry():
    """Demonstrate backup operations with retry mechanisms"""
    logger.info("=== Backup with Retry Demo ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        demo_path = Path(temp_dir) / "demo_data"
        repo_path = Path(temp_dir) / "backup_repo"

        create_demo_files(demo_path)

        # Initialize backup manager and repository
        manager = BackupManager()

        try:
            # Create and initialize repository
            repository = LocalResticRepository(
                    location=str(repo_path),
                    password="demo_password_123"
            )

            # Initialize repository
            if repository.initialize_repository("demo_password_123"):
                logger.info("Repository initialized successfully")
            else:
                logger.error("Failed to initialize repository")
                return

            # Create backup target with enhanced file selection
            selection = FileSelection()
            selection.add_path(demo_path, SelectionType.INCLUDE)
            selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)

            target = BackupTarget(
                    selection=selection,
                    tags=["demo", "enhanced"]
            )

            # Demonstrate full backup with retry
            logger.info("Creating full backup with retry mechanism...")
            try:
                result = manager.create_full_backup(
                        repository, [target],
                        tags=["manual", "demo"],
                        max_retries=2,
                        retry_delay=0.5
                )
                logger.info(f"Full backup completed successfully: {result.get('snapshot_id', 'N/A')}")

                # Demonstrate incremental backup
                logger.info("Creating incremental backup...")
                incremental_result = manager.create_incremental_backup(
                        repository, [target],
                        parent_snapshot_id=result.get('snapshot_id'),
                        tags=["auto", "incremental"]
                )
                logger.info(f"Incremental backup completed: {incremental_result.get('snapshot_id', 'N/A')}")

            except BackupManagerError as e:
                logger.error(f"Backup failed: {e}")

        except Exception as e:
            logger.error(f"Demo failed: {e}")


def demo_comprehensive_verification():
    """Demonstrate comprehensive backup verification"""
    logger.info("=== Comprehensive Verification Demo ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        demo_path = Path(temp_dir) / "demo_data"
        repo_path = Path(temp_dir) / "backup_repo"

        create_demo_files(demo_path)

        try:
            # Create and initialize repository
            repository = LocalResticRepository(
                    location=str(repo_path),
                    password="demo_password_123"
            )

            if repository.initialize_repository("demo_password_123"):
                logger.info("Repository initialized for verification demo")

                # Create a backup first
                selection = FileSelection()
                selection.add_path(demo_path, SelectionType.INCLUDE)
                target = BackupTarget(selection=selection, tags=["verification_demo"])

                manager = BackupManager()
                result = manager.create_full_backup(repository, [target])
                snapshot_id = result.get('snapshot_id')

                if snapshot_id:
                    logger.info(f"Created backup with snapshot ID: {snapshot_id}")

                    # Demonstrate basic verification
                    logger.info("Performing basic verification...")
                    basic_result = repository.verify_backup(snapshot_id)
                    logger.info(f"Basic verification: {'PASSED' if basic_result else 'FAILED'}")

                    # Demonstrate comprehensive verification
                    logger.info("Performing comprehensive verification...")
                    comprehensive_result = repository.verify_backup_comprehensive(snapshot_id)

                    logger.info(f"Comprehensive verification: {'PASSED' if comprehensive_result['success'] else 'FAILED'}")
                    logger.info(f"Checks performed: {', '.join(comprehensive_result['checks_performed'])}")

                    if comprehensive_result['errors']:
                        logger.warning(f"Errors found: {comprehensive_result['errors']}")

                    if comprehensive_result['warnings']:
                        logger.warning(f"Warnings: {comprehensive_result['warnings']}")

                    if comprehensive_result['statistics']:
                        logger.info(f"Repository statistics: {comprehensive_result['statistics']}")

        except Exception as e:
            logger.error(f"Verification demo failed: {e}")


def demo_pattern_groups():
    """Demonstrate pattern group functionality"""
    logger.info("=== Pattern Groups Demo ===")

    # Show available common pattern groups
    logger.info("Available common pattern groups:")
    for group_name in PatternGroup.COMMON_GROUPS.keys():
        group = PatternGroup.get_common_group(group_name)
        logger.info(f"  {group_name}: {list(group.patterns)[:3]}...")  # Show first 3 patterns

    # Create custom pattern group
    custom_group = PatternGroup("config_files", ["*.conf", "*.ini", "*.yaml", "*.yml"])
    logger.info(f"Custom pattern group 'config_files': {list(custom_group.patterns)}")

    # Demonstrate usage in file selection
    selection = FileSelection()
    selection.add_pattern_group("office_documents", SelectionType.INCLUDE)
    selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)
    selection.add_pattern_group(custom_group, SelectionType.INCLUDE)

    logger.info(f"Include patterns: {selection.include_patterns}")
    logger.info(f"Exclude patterns: {selection.exclude_patterns}")


def main():
    """Run all demos"""
    logger.info("Starting TimeLocker Enhanced Backup Operations Demo")

    try:
        demo_pattern_groups()
        demo_enhanced_file_selection()
        demo_backup_with_retry()
        demo_comprehensive_verification()

        logger.info("All demos completed successfully!")

    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
