#!/usr/bin/env python3
"""
CLI Cleanup Script

Removes extracted command code from cli.py after successful extraction.
Creates a backup before making changes.

Usage:
    python scripts/cleanup_cli.py --backup
    python scripts/cleanup_cli.py --execute
"""

import argparse
import shutil
from pathlib import Path
from datetime import datetime


def create_backup(cli_file: Path) -> Path:
    """Create a backup of cli.py."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = cli_file.parent / f"cli.py.backup_{timestamp}"
    shutil.copy2(cli_file, backup_file)
    print(f"✅ Backup created: {backup_file}")
    return backup_file


def find_command_blocks(cli_file: Path, app_names: list) -> dict:
    """Find all command blocks for specified apps."""
    with open(cli_file, 'r') as f:
        lines = f.readlines()
    
    blocks = {}
    for app_name in app_names:
        blocks[app_name] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Look for @app_name.command
            if f'@{app_name}.command(' in line:
                start = i
                # Find end of function
                j = i + 1
                # Skip to function definition
                while j < len(lines) and not lines[j].strip().startswith('def '):
                    j += 1
                if j < len(lines):
                    # Find end of function
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    k = j + 1
                    while k < len(lines):
                        if lines[k].strip():
                            curr_indent = len(lines[k]) - len(lines[k].lstrip())
                            if curr_indent <= indent and (
                                lines[k].strip().startswith('def ') or
                                lines[k].strip().startswith('@') or
                                lines[k].strip().startswith('class ')
                            ):
                                break
                        k += 1
                    blocks[app_name].append((start, k))
                    i = k
                    continue
            i += 1
    
    return blocks


def remove_blocks(cli_file: Path, blocks: dict, dry_run: bool = True):
    """Remove command blocks from cli.py."""
    with open(cli_file, 'r') as f:
        lines = f.readlines()
    
    # Collect all line ranges to remove
    lines_to_remove = set()
    for app_name, block_list in blocks.items():
        for start, end in block_list:
            for i in range(start, end):
                lines_to_remove.add(i)
    
    # Keep lines that aren't in removal set
    new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
    
    # Show what will be removed
    total_removed = len(lines_to_remove)
    print(f"\n📊 Summary:")
    for app_name, block_list in blocks.items():
        if block_list:
            print(f"   {app_name}: {len(block_list)} commands")
    print(f"   Total lines to remove: {total_removed}")
    print(f"   Original size: {len(lines)} lines")
    print(f"   New size: {len(new_lines)} lines")
    print(f"   Reduction: {total_removed} lines ({total_removed/len(lines)*100:.1f}%)")
    
    if not dry_run:
        with open(cli_file, 'w') as f:
            f.writelines(new_lines)
        print(f"\n✅ cli.py updated successfully")
    else:
        print(f"\n⚠️  Dry run - no changes made")
        print(f"   Run with --execute to apply changes")
    
    return len(new_lines)


def main():
    parser = argparse.ArgumentParser(description="Clean up cli.py after extraction")
    parser.add_argument('--backup', action='store_true', help='Create backup only')
    parser.add_argument('--execute', action='store_true', help='Execute cleanup (removes code)')
    parser.add_argument('--cli-file', type=Path, default=Path('src/TimeLocker/cli.py'))
    
    args = parser.parse_args()
    
    if not args.cli_file.exists():
        print(f"❌ CLI file not found: {args.cli_file}")
        return 1
    
    # Apps that have been extracted
    extracted_apps = [
        'security_app',
        'credentials_app',
        'snapshots_app',
        'repos_app',
        'config_app',
        'targets_app',  # Already extracted
        'backup_app',   # Already extracted
    ]
    
    print(f"🧹 CLI Cleanup Script")
    print(f"   File: {args.cli_file}")
    print(f"   Apps to remove: {', '.join(extracted_apps)}")
    
    # Always create backup
    backup_file = create_backup(args.cli_file)
    
    if args.backup:
        print(f"\n✅ Backup created successfully")
        print(f"   To restore: cp {backup_file} {args.cli_file}")
        return 0
    
    # Find command blocks
    print(f"\n🔍 Finding command blocks...")
    blocks = find_command_blocks(args.cli_file, extracted_apps)
    
    # Remove blocks
    dry_run = not args.execute
    new_size = remove_blocks(args.cli_file, blocks, dry_run=dry_run)
    
    if args.execute:
        print(f"\n📝 Next steps:")
        print(f"   1. Test imports: python -c \"from TimeLocker.cli import app; print('✓ OK')\"")
        print(f"   2. Run tests: pytest tests/test_cli.py -v")
        print(f"   3. If issues: cp {backup_file} {args.cli_file}")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
