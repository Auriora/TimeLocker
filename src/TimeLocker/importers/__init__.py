"""
TimeLocker Import Modules

This package provides functionality to import configurations from other backup tools
into TimeLocker's configuration system.

Supported import sources:
- Timeshift: System backup tool for Linux
- Restic: Fast, secure backup program (via environment variables)
"""

from .timeshift_importer import TimeshiftConfigParser, TimeshiftToTimeLockerMapper

__all__ = [
        'TimeshiftConfigParser',
        'TimeshiftToTimeLockerMapper',
]
