"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "0.9.1"

_LAZY_EXPORTS = {
    "BackupManager": (".backup_manager", "BackupManager"),
    "BackupRepository": (".backup_repository", "BackupRepository"),
    "BackupSnapshot": (".backup_snapshot", "BackupSnapshot"),
    "BackupTarget": (".backup_target", "BackupTarget"),
    "RestoreManager": (".restore_manager", "RestoreManager"),
    "SnapshotManager": (".snapshot_manager", "SnapshotManager"),
    "FileSelection": (".file_selections", "FileSelection"),
    "PatternGroup": (".file_selections", "PatternGroup"),
    "SecurityService": (".security", "SecurityService"),
    "CredentialManager": (".security", "CredentialManager"),
    "SecurityLogger": (".security", "SecurityLogger"),
    "StatusReporter": (".monitoring", "StatusReporter"),
    "NotificationService": (".monitoring", "NotificationService"),
    "ConfigurationModule": (".config", "ConfigurationModule"),
    "ConfigurationManager": (
        ".config.configuration_manager",
        "ConfigurationManager",
    ),
    "IntegrationService": (".integration", "IntegrationService"),
}


def __getattr__(name: str) -> Any:
    """Load legacy package exports only when callers request them."""
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Include lazy compatibility exports in interactive discovery."""
    return sorted({*globals(), *_LAZY_EXPORTS})


__all__ = [
    "BackupManager",
    "BackupRepository",
    "BackupSnapshot",
    "BackupTarget",
    "RestoreManager",
    "SnapshotManager",
    "FileSelection",
    "PatternGroup",
    "SecurityService",
    "CredentialManager",
    "SecurityLogger",
    "StatusReporter",
    "NotificationService",
    "ConfigurationManager",
    "IntegrationService",
]
