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

# Core components
from .backup_manager import BackupManager
from .backup_repository import BackupRepository
from .backup_snapshot import BackupSnapshot
from .backup_target import BackupTarget
from .restore_manager import RestoreManager
from .snapshot_manager import SnapshotManager
from .file_selections import FileSelection, PatternGroup

# Security components
from .security import SecurityService, CredentialManager

# Monitoring components
from .monitoring import StatusReporter, NotificationService

# Configuration components
from .config import ConfigurationModule

# Integration components
from .integration import IntegrationService

__version__ = "1.0.0"

__all__ = [
        # Core components
        'BackupManager',
        'BackupRepository',
        'BackupSnapshot',
        'BackupTarget',
        'RestoreManager',
        'SnapshotManager',
        'FileSelection',
        'PatternGroup',

        # Security components
        'SecurityService',
        'CredentialManager',

        # Monitoring components
        'StatusReporter',
        'NotificationService',

        # Configuration components
        'ConfigurationManager',

        # Integration components
        'IntegrationService',
]
