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

# Regression coverage for repository factory backend registration.

import sys
import types

from TimeLocker.services.repository_factory import RepositoryFactory


def test_registers_local_and_s3_when_b2_import_fails(monkeypatch, caplog):
    """Simulate missing optional b2 dependency and verify local/s3 remain registered."""
    missing_b2_module = types.ModuleType("TimeLocker.restic.Repositories.b2")
    monkeypatch.setitem(
        sys.modules, "TimeLocker.restic.Repositories.b2", missing_b2_module
    )

    with caplog.at_level("WARNING"):
        factory = RepositoryFactory()

    supported = set(factory.get_supported_schemes())
    assert "local" in supported
    assert "file" in supported
    assert "s3" in supported
    assert "b2" not in supported
    assert "Repository backend 'b2' unavailable" in caplog.text
    assert factory.is_scheme_supported("s3")
    assert factory.is_scheme_supported("local")
