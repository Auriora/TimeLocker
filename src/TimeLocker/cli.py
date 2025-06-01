#!/usr/bin/env python3
"""
TimeLocker Command Line Interface

This module provides a command-line interface for TimeLocker backup operations.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional, List

from . import __version__
from .backup_manager import BackupManager
from .backup_target import BackupTarget
from .file_selections import FileSelection, SelectionType
from .restore_manager import RestoreManager
from .snapshot_manager import SnapshotManager
from .config import ConfigurationManager


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
    )


def cmd_backup(args) -> int:
    """Execute backup command."""
    try:
        manager = BackupManager()

        # Create backup target
        target = BackupTarget(
                name=args.name or "cli_backup",
                source_paths=args.sources,
                repository_uri=args.repository,
                password=args.password
        )

        # Add file selections if specified
        if args.exclude:
            for pattern in args.exclude:
                target.add_file_selection(FileSelection(
                        pattern=pattern,
                        selection_type=SelectionType.EXCLUDE
                ))

        if args.include:
            for pattern in args.include:
                target.add_file_selection(FileSelection(
                        pattern=pattern,
                        selection_type=SelectionType.INCLUDE
                ))

        # Perform backup
        result = manager.backup(target, tags=args.tags)

        if result.success:
            print(f"✓ Backup completed successfully")
            print(f"  Snapshot ID: {result.snapshot_id}")
            print(f"  Files processed: {result.files_new + result.files_changed + result.files_unmodified}")
            print(f"  Data added: {result.data_added_formatted}")
            return 0
        else:
            print(f"✗ Backup failed: {result.error}")
            return 1

    except Exception as e:
        print(f"✗ Error during backup: {e}")
        return 1


def cmd_restore(args) -> int:
    """Execute restore command."""
    try:
        manager = RestoreManager()

        # Perform restore
        result = manager.restore_snapshot(
                repository_uri=args.repository,
                password=args.password,
                snapshot_id=args.snapshot,
                target_path=Path(args.target),
                include_patterns=args.include,
                exclude_patterns=args.exclude
        )

        if result.success:
            print(f"✓ Restore completed successfully")
            print(f"  Files restored: {result.files_restored}")
            print(f"  Target path: {args.target}")
            return 0
        else:
            print(f"✗ Restore failed: {result.error}")
            return 1

    except Exception as e:
        print(f"✗ Error during restore: {e}")
        return 1


def cmd_list(args) -> int:
    """List snapshots in repository."""
    try:
        manager = SnapshotManager()

        snapshots = manager.list_snapshots(
                repository_uri=args.repository,
                password=args.password
        )

        if not snapshots:
            print("No snapshots found in repository")
            return 0

        print(f"Found {len(snapshots)} snapshots:")
        print(f"{'ID':<12} {'Date':<20} {'Host':<15} {'Tags':<20} {'Paths'}")
        print("-" * 80)

        for snapshot in snapshots:
            tags_str = ",".join(snapshot.tags) if snapshot.tags else ""
            paths_str = ",".join(str(p) for p in snapshot.paths[:2])
            if len(snapshot.paths) > 2:
                paths_str += f" (+{len(snapshot.paths) - 2} more)"

            print(f"{snapshot.id[:12]:<12} {snapshot.time.strftime('%Y-%m-%d %H:%M:%S'):<20} "
                  f"{snapshot.hostname:<15} {tags_str:<20} {paths_str}")

        return 0

    except Exception as e:
        print(f"✗ Error listing snapshots: {e}")
        return 1


def cmd_init(args) -> int:
    """Initialize a new repository."""
    try:
        manager = BackupManager()

        # Initialize repository
        repo = manager.from_uri(args.repository, password=args.password)
        repo.init()

        print(f"✓ Repository initialized successfully at: {args.repository}")
        return 0

    except Exception as e:
        print(f"✗ Error initializing repository: {e}")
        return 1


def cmd_version(args) -> int:
    """Show version information."""
    print(f"TimeLocker {__version__}")
    print("High-level Python interface for backup operations using Restic")
    print("Copyright © Bruce Cherrington")
    print("Licensed under GNU General Public License v3.0")
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
            prog="timelocker",
            description="TimeLocker - High-level Python interface for backup operations",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  timelocker backup --repository /path/to/repo --password mypass /home/user
  timelocker restore --repository /path/to/repo --password mypass --snapshot abc123 /restore/path
  timelocker list --repository /path/to/repo --password mypass
  timelocker init --repository /path/to/repo --password mypass
        """
    )

    parser.add_argument(
            "--version", action="version", version=f"TimeLocker {__version__}"
    )
    parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument("sources", nargs="+", help="Source paths to backup")
    backup_parser.add_argument("--repository", "-r", required=True, help="Repository URI")
    backup_parser.add_argument("--password", "-p", required=True, help="Repository password")
    backup_parser.add_argument("--name", "-n", help="Backup target name")
    backup_parser.add_argument("--exclude", "-e", action="append", help="Exclude pattern")
    backup_parser.add_argument("--include", "-i", action="append", help="Include pattern")
    backup_parser.add_argument("--tags", "-t", action="append", help="Backup tags")
    backup_parser.set_defaults(func=cmd_backup)

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("target", help="Target path for restore")
    restore_parser.add_argument("--repository", "-r", required=True, help="Repository URI")
    restore_parser.add_argument("--password", "-p", required=True, help="Repository password")
    restore_parser.add_argument("--snapshot", "-s", required=True, help="Snapshot ID to restore")
    restore_parser.add_argument("--exclude", "-e", action="append", help="Exclude pattern")
    restore_parser.add_argument("--include", "-i", action="append", help="Include pattern")
    restore_parser.set_defaults(func=cmd_restore)

    # List command
    list_parser = subparsers.add_parser("list", help="List snapshots")
    list_parser.add_argument("--repository", "-r", required=True, help="Repository URI")
    list_parser.add_argument("--password", "-p", required=True, help="Repository password")
    list_parser.set_defaults(func=cmd_list)

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize repository")
    init_parser.add_argument("--repository", "-r", required=True, help="Repository URI")
    init_parser.add_argument("--password", "-p", required=True, help="Repository password")
    init_parser.set_defaults(func=cmd_init)

    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")
    version_parser.set_defaults(func=cmd_version)

    return parser


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Handle no command case
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1

    # Execute the command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n✗ Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
