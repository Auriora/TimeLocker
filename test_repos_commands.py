#!/usr/bin/env python3
"""
Test script to verify repository commands work.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import the repositories module to register commands
from TimeLocker.cli_modules.commands import repositories

# Import the main CLI app
from TimeLocker.cli import app

# Test by invoking help
if __name__ == "__main__":
    from typer.testing import CliRunner
    
    runner = CliRunner()
    
    # Test repos help
    print("=" * 60)
    print("Testing: repos --help")
    print("=" * 60)
    result = runner.invoke(app, ["repos", "--help"])
    print(result.stdout)
    print(f"Exit code: {result.exit_code}")
    
    # Test repos list
    print("\n" + "=" * 60)
    print("Testing: repos list")
    print("=" * 60)
    result = runner.invoke(app, ["repos", "list"])
    print(result.stdout)
    print(f"Exit code: {result.exit_code}")
    
    # List available commands
    print("\n" + "=" * 60)
    print("Available repos commands:")
    print("=" * 60)
    from TimeLocker.cli_modules.commands.repositories import repos_app
    for cmd in repos_app.registered_commands:
        print(f"  - {cmd.name}")
