#!/usr/bin/env python3
"""
Script to fix absolute imports to relative imports in TimeLocker codebase
"""

import os
import re
from pathlib import Path


def fix_imports_in_file(file_path: Path):
    """Fix imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Calculate relative path depth based on file location
        parts = file_path.relative_to(Path('src/TimeLocker')).parts
        depth = len(parts) - 1  # -1 because we don't count the file itself

        if depth == 0:
            # Files in src/TimeLocker/ root
            prefix = '.'
        else:
            # Files in subdirectories
            prefix = '.' + '.' * depth

        # Pattern to match TimeLocker imports
        patterns = [
                (r'from TimeLocker\.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)', f'from {prefix}.\\1'),
                (r'import TimeLocker\.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)', f'import {prefix}.\\1'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed imports in {file_path}")
            return True
        else:
            print(f"No changes needed in {file_path}")
            return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to fix all imports"""
    src_dir = Path('src/TimeLocker')

    if not src_dir.exists():
        print("src/TimeLocker directory not found!")
        return

    # Find all Python files
    python_files = list(src_dir.rglob('*.py'))

    fixed_count = 0
    for file_path in python_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1

    print(f"\nFixed imports in {fixed_count} files out of {len(python_files)} total files.")


if __name__ == '__main__':
    main()
