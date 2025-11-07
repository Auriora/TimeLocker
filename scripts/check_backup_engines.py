#!/usr/bin/env python3
"""
Check Backup Engines

Simple utility to check which backup engines are available on the system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from TimeLocker.services import initialize_plugins, print_plugin_status


def main():
    """Check and display backup engine availability"""
    try:
        initialize_plugins()
        print_plugin_status()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
