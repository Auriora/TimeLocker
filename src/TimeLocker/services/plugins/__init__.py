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

"""
Built-in Backup Engine Plugins

This package contains the built-in implementations of backup engine plugins
for Restic, Rsync, and Rclone.
"""

from .restic_plugin import ResticEnginePlugin
from .rsync_plugin import RsyncEnginePlugin
from .rclone_plugin import RcloneEnginePlugin

__all__ = [
    'ResticEnginePlugin',
    'RsyncEnginePlugin',
    'RcloneEnginePlugin',
]
