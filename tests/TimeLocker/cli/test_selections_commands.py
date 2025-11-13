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

import pytest
import tempfile
from pathlib import Path
from typer.testing import CliRunner

from src.TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import combined_output


@pytest.fixture
def runner():
    """Create a CLI test runner"""
    return CliRunner()


@pytest.fixture
def temp_storage_dir(monkeypatch):
    """Create a temporary storage directory for templates"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch the storage directory
        monkeypatch.setenv('XDG_DATA_HOME', tmpdir)
        yield Path(tmpdir)


class TestSelectionsCommands:
    """Test suite for selections CLI commands"""
    
    def test_selections_help(self, runner):
        """Test selections help command"""
        result = runner.invoke(app, ["selections", "--help"])
        assert result.exit_code == 0
        assert "Data selection template management" in result.stdout
    
    def test_selections_create_basic(self, runner, temp_storage_dir):
        """Test creating a basic selection template"""
        result = runner.invoke(app, [
            "selections", "create", "test-selection",
            "--description", "Test selection",
            "--include-path", str(Path.home() / "Documents")
        ])
        
        # Should succeed
        assert result.exit_code == 0
        assert "Selection Created" in result.stdout or "created successfully" in result.stdout.lower()
    
    def test_selections_create_with_patterns(self, runner, temp_storage_dir):
        """Test creating a selection with patterns"""
        result = runner.invoke(app, [
            "selections", "create", "code-selection",
            "--description", "Code files",
            "--include-path", str(Path.home() / "projects"),
            "--include", "*.py",
            "--include", "*.js",
            "--exclude", "node_modules/*",
            "--exclude", "__pycache__/*"
        ])
        
        assert result.exit_code == 0
        assert "Selection Created" in result.stdout or "created successfully" in result.stdout.lower()
    
    def test_selections_list(self, runner, temp_storage_dir):
        """Test listing selection templates"""
        # Create a template first
        runner.invoke(app, [
            "selections", "create", "list-test",
            "--include-path", str(Path.home())
        ])
        
        # List templates
        result = runner.invoke(app, ["selections", "list"])
        assert result.exit_code == 0
        # Should show the template or indicate no templates
        assert "list-test" in result.stdout or "No selection templates" in result.stdout
    
    def test_selections_show(self, runner, temp_storage_dir):
        """Test showing a selection template"""
        # Create a template first
        runner.invoke(app, [
            "selections", "create", "show-test",
            "--description", "Test description",
            "--include-path", str(Path.home() / "Documents")
        ])
        
        # Show the template
        result = runner.invoke(app, ["selections", "show", "show-test"])
        assert result.exit_code == 0
        assert "show-test" in result.stdout
    
    def test_selections_show_not_found(self, runner, temp_storage_dir):
        """Test showing a non-existent template"""
        result = runner.invoke(app, ["selections", "show", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
    
    def test_selections_delete(self, runner, temp_storage_dir):
        """Test deleting a selection template"""
        # Create a template first
        runner.invoke(app, [
            "selections", "create", "delete-test",
            "--include-path", str(Path.home())
        ])
        
        # Delete the template
        result = runner.invoke(app, [
            "selections", "delete", "delete-test", "--yes"
        ])
        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()
    
    def test_selections_export(self, runner, temp_storage_dir):
        """Test exporting a selection template"""
        # Create a template first
        runner.invoke(app, [
            "selections", "create", "export-test",
            "--include-path", str(Path.home())
        ])
        
        # Export the template
        output_file = temp_storage_dir / "export-test.json"
        result = runner.invoke(app, [
            "selections", "export", "export-test",
            "--output", str(output_file)
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        assert output_file.exists()
    
    def test_selections_import(self, runner, temp_storage_dir):
        """Test importing a selection template"""
        # Create and export a template first
        runner.invoke(app, [
            "selections", "create", "import-test",
            "--include-path", str(Path.home())
        ])
        
        export_file = temp_storage_dir / "import-test.json"
        runner.invoke(app, [
            "selections", "export", "import-test",
            "--output", str(export_file)
        ])
        
        # Delete the template
        runner.invoke(app, [
            "selections", "delete", "import-test", "--yes"
        ])
        
        # Import it back
        result = runner.invoke(app, [
            "selections", "import", str(export_file)
        ])
        
        assert result.exit_code == 0
        # Verify template exists again by listing
        list_result = runner.invoke(app, ["selections", "list"])
        assert list_result.exit_code == 0
        assert "import-test" in combined_output(list_result)
