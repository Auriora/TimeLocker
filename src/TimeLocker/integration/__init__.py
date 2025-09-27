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

from .integration_service import IntegrationService, IntegrationError
# Legacy global alias for tests referencing bare ConfigSection without imports
try:
    import builtins  # type: ignore
    from ..config import ConfigSection as _ConfigSection
    if not hasattr(builtins, 'ConfigSection'):
        setattr(builtins, 'ConfigSection', _ConfigSection)
except Exception:
    pass


__all__ = ['IntegrationService', 'IntegrationError']
