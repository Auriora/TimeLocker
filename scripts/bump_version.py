#!/usr/bin/env python3
"""
Version management script for TimeLocker.
Provides easy-to-use commands for version bumping using bump2version.
"""

import argparse
import subprocess
import sys
from pathlib import Path
import re


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_current_version():
    """Get current version from pyproject.toml."""
    pyproject_file = get_project_root() / "pyproject.toml"

    if not pyproject_file.exists():
        return "unknown"

    with open(pyproject_file, "r") as f:
        content = f.read()
        match = re.search(r'version = "([^"]+)"', content)
        if match:
            return match.group(1)

    return "unknown"


def run_command(cmd, description):
    """Run a command and handle output."""
    print(f"🔄 {description}...")

    try:
        result = subprocess.run(
                cmd,
                cwd=get_project_root(),
                capture_output=True,
                text=True,
                shell=True
        )

        if result.returncode == 0:
            print(f"✅ {description} completed successfully!")
            if result.stdout.strip():
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} failed!")
            if result.stderr.strip():
                print(f"Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False


def check_git_status():
    """Check if git repository is clean."""
    result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=get_project_root(),
            capture_output=True,
            text=True
    )

    if result.stdout.strip():
        print("⚠️  Warning: Git repository has uncommitted changes:")
        print(result.stdout)
        response = input("Continue anyway? (y/N): ")
        return response.lower() in ['y', 'yes']

    return True


def show_current_version():
    """Show current version information."""
    version = get_current_version()
    print(f"📦 Current version: {version}")

    # Check version consistency
    pyproject_version = get_current_version()

    # Check __init__.py version
    init_file = get_project_root() / "src" / "TimeLocker" / "__init__.py"
    init_version = "unknown"

    if init_file.exists():
        with open(init_file, "r") as f:
            content = f.read()
            match = re.search(r'__version__ = "([^"]+)"', content)
            if match:
                init_version = match.group(1)

    print(f"📄 pyproject.toml: {pyproject_version}")
    print(f"📄 __init__.py: {init_version}")

    if pyproject_version == init_version:
        print("✅ Versions are consistent")
    else:
        print("❌ Version mismatch detected!")
        return False

    return True


def bump_version(part, dry_run=False, no_commit=False, no_tag=False):
    """Bump version using bump2version."""
    valid_parts = ["major", "minor", "patch", "release", "num"]

    if part not in valid_parts:
        print(f"❌ Invalid part '{part}'. Valid parts: {', '.join(valid_parts)}")
        return False

    current_version = get_current_version()
    print(f"📦 Current version: {current_version}")

    if not dry_run and not check_git_status():
        print("❌ Aborting due to git status")
        return False

    # Build bump2version command
    cmd_parts = ["bump2version"]

    if dry_run:
        cmd_parts.extend(["--dry-run", "--verbose", "--allow-dirty"])

    if no_commit:
        cmd_parts.append("--no-commit")

    if no_tag:
        cmd_parts.append("--no-tag")

    cmd_parts.append(part)

    cmd = " ".join(cmd_parts)
    description = f"Bump {part} version"

    if dry_run:
        description += " (dry run)"

    success = run_command(cmd, description)

    if success and not dry_run:
        new_version = get_current_version()
        print(f"🎉 Version bumped: {current_version} → {new_version}")

        if not no_tag:
            print(f"🏷️  Git tag created: v{new_version}")

    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
            description="TimeLocker version management tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python scripts/bump_version.py show                    # Show current version
  python scripts/bump_version.py bump patch              # Bump patch version
  python scripts/bump_version.py bump minor --dry-run    # Preview minor bump
  python scripts/bump_version.py bump major --no-tag     # Bump major without tag
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show current version information")

    # Bump command
    bump_parser = subparsers.add_parser("bump", help="Bump version")
    bump_parser.add_argument(
            "part",
            choices=["major", "minor", "patch", "release", "num"],
            help="Version part to bump"
    )
    bump_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes"
    )
    bump_parser.add_argument(
            "--no-commit",
            action="store_true",
            help="Don't create git commit"
    )
    bump_parser.add_argument(
            "--no-tag",
            action="store_true",
            help="Don't create git tag"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "show":
        success = show_current_version()
        return 0 if success else 1

    elif args.command == "bump":
        success = bump_version(
                args.part,
                dry_run=args.dry_run,
                no_commit=args.no_commit,
                no_tag=args.no_tag
        )
        return 0 if success else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
