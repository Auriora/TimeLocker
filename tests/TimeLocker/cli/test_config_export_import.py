"""
Unit tests for TimeLocker CLI config export, import, and migrate commands.

Tests configuration export, import validation, and migration functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

from TimeLocker.cli import app, config_export_app, config_import_app, migrate_app

# Set wider terminal width to prevent help text truncation in CI
runner = CliRunner(env={'COLUMNS': '200'})


def _combined_output(result):
    """Combine stdout and stderr for matching convenience across environments."""
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


class TestConfigExportCommands:
    """Test suite for config export commands."""

    @pytest.mark.unit
    def test_config_export_help(self):
        """Test config export command help output."""
        result = runner.invoke(app, ["config", "export", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "export" in combined.lower()
        assert "configuration" in combined.lower()

    @pytest.mark.unit
    def test_config_export_config_help(self):
        """Test config export config command help output."""
        result = runner.invoke(app, ["config", "export", "config", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "export" in combined.lower()
        assert "configuration" in combined.lower()
        assert "--repositories" in combined or "repositories" in combined.lower()
        assert "--selections" in combined or "selections" in combined.lower()

    @pytest.mark.unit
    @patch('TimeLocker.cli._create_configuration_module')
    def test_config_export_basic(self, mock_config_module):
        """Test basic config export command execution."""
        # Create a temporary file for export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = Path(f.name)
        
        try:
            # Mock the configuration module
            mock_config = Mock()
            mock_config_module.return_value = mock_config
            
            # Mock config object with proper structure - use spec to avoid Mock iteration issues
            mock_general = Mock()
            mock_general.to_dict = Mock(return_value={
                "app_name": "TimeLocker",
                "version": "1.0.0"
            })
            
            # Create a more complete mock that won't have iteration issues
            mock_config_obj = type('MockConfig', (), {
                'general': mock_general,
                'repositories': {},
                'backup_targets': {},
            })()
            
            mock_config.get_config.return_value = mock_config_obj
            
            # Run export command
            result = runner.invoke(app, ["config", "export", "config", str(export_file), "--overwrite"])
            
            # Should succeed
            assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {_combined_output(result)}"
            combined = _combined_output(result)
            assert "exported" in combined.lower() or "success" in combined.lower()
            
            # Check that file was created
            assert export_file.exists()
            
            # Verify file content
            with open(export_file, 'r') as f:
                data = json.load(f)
            
            assert "metadata" in data
            assert "general" in data
            
        finally:
            # Clean up
            if export_file.exists():
                export_file.unlink()

    @pytest.mark.unit
    @patch('TimeLocker.cli._create_configuration_module')
    def test_config_export_file_exists_no_overwrite(self, mock_config_module):
        """Test config export fails when file exists without overwrite flag."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = Path(f.name)
            f.write("{}")
        
        try:
            # Mock the configuration module
            mock_config = Mock()
            mock_config_module.return_value = mock_config
            
            # Run export command without overwrite
            result = runner.invoke(app, ["config", "export", "config", str(export_file)])
            
            # Should fail - the command exits with code 2 for validation errors
            # but may exit with 1 if caught as a general exception
            assert result.exit_code in [1, 2], f"Expected exit code 1 or 2, got {result.exit_code}"
            combined = _combined_output(result)
            assert "exists" in combined.lower() or "overwrite" in combined.lower()
            
        finally:
            # Clean up
            if export_file.exists():
                export_file.unlink()


class TestConfigImportCommands:
    """Test suite for config import commands."""

    @pytest.mark.unit
    def test_config_import_config_help(self):
        """Test config import config command help output."""
        result = runner.invoke(app, ["config", "import", "config", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "import" in combined.lower()
        assert "configuration" in combined.lower()
        assert "--merge" in combined or "merge" in combined.lower()
        assert "--dry-run" in combined or "dry" in combined.lower()

    @pytest.mark.unit
    def test_config_import_file_not_found(self):
        """Test config import fails when file doesn't exist."""
        result = runner.invoke(app, ["config", "import", "config", "/nonexistent/file.json"])
        
        # Should fail with exit code 2
        assert result.exit_code == 2
        combined = _combined_output(result)
        assert "not found" in combined.lower() or "does not exist" in combined.lower()

    @pytest.mark.unit
    @patch('TimeLocker.cli._create_configuration_module')
    def test_config_import_dry_run(self, mock_config_module):
        """Test config import dry-run mode."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import_file = Path(f.name)
            json.dump({
                "metadata": {
                    "exported_at": "2024-01-01T00:00:00",
                    "timelocker_version": "1.0.0"
                },
                "general": {},
                "repositories": {},
                "backup_targets": {}
            }, f)
        
        try:
            # Mock the configuration module
            mock_config = Mock()
            mock_config_module.return_value = mock_config
            
            mock_config_obj = Mock()
            mock_config_obj.repositories = {}
            mock_config_obj.backup_targets = {}
            mock_config.get_config.return_value = mock_config_obj
            
            # Run import with dry-run
            result = runner.invoke(app, ["config", "import", "config", str(import_file), "--dry-run"])
            
            # Should succeed
            assert result.exit_code == 0
            combined = _combined_output(result)
            assert "dry" in combined.lower()
            
            # Verify import_configuration was NOT called
            mock_config.import_configuration.assert_not_called()
            
        finally:
            # Clean up
            if import_file.exists():
                import_file.unlink()


class TestMigrateCommands:
    """Test suite for migrate commands."""

    @pytest.mark.unit
    def test_migrate_help(self):
        """Test migrate command group help output."""
        result = runner.invoke(app, ["migrate", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "migrate" in combined.lower() or "migration" in combined.lower()

    @pytest.mark.unit
    def test_migrate_validate_help(self):
        """Test migrate validate command help output."""
        result = runner.invoke(app, ["migrate", "validate", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "validate" in combined.lower()
        assert "configuration" in combined.lower()
        assert "--show-changes" in combined or "changes" in combined.lower()

    @pytest.mark.unit
    def test_migrate_validate_file_not_found(self):
        """Test migrate validate fails when file doesn't exist."""
        result = runner.invoke(app, ["migrate", "validate", "/nonexistent/file.json"])
        
        # Should fail with exit code 2
        assert result.exit_code == 2
        combined = _combined_output(result)
        assert "not found" in combined.lower() or "does not exist" in combined.lower()

    @pytest.mark.unit
    def test_migrate_validate_invalid_json(self):
        """Test migrate validate fails with invalid JSON."""
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = Path(f.name)
            f.write("{ invalid json }")
        
        try:
            result = runner.invoke(app, ["migrate", "validate", str(config_file)])
            
            # Should fail with exit code 2
            assert result.exit_code == 2
            combined = _combined_output(result)
            assert "invalid" in combined.lower() or "json" in combined.lower()
            
        finally:
            # Clean up
            if config_file.exists():
                config_file.unlink()

    @pytest.mark.unit
    @patch('TimeLocker.cli._create_configuration_module')
    def test_migrate_validate_valid_config(self, mock_config_module):
        """Test migrate validate with valid configuration."""
        # Create a valid config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = Path(f.name)
            json.dump({
                "metadata": {
                    "exported_at": "2024-01-01T00:00:00",
                    "timelocker_version": "1.0.0"
                },
                "general": {},
                "repositories": {
                    "test-repo": {
                        "uri": "file:///backup/test",
                        "description": "Test repository"
                    }
                },
                "backup_targets": {}
            }, f)
        
        try:
            # Mock the configuration module
            mock_config = Mock()
            mock_config_module.return_value = mock_config
            
            mock_config_obj = Mock()
            mock_config_obj.repositories = {}
            mock_config_obj.backup_targets = {}
            mock_config.get_config.return_value = mock_config_obj
            
            # Run validate
            result = runner.invoke(app, ["migrate", "validate", str(config_file)])
            
            # Should succeed
            assert result.exit_code == 0
            combined = _combined_output(result)
            assert "valid" in combined.lower()
            
        finally:
            # Clean up
            if config_file.exists():
                config_file.unlink()


class TestCompletionCommands:
    """Test suite for completion command enhancements."""

    @pytest.mark.unit
    def test_completion_help(self):
        """Test completion command help output."""
        result = runner.invoke(app, ["completion", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "completion" in combined.lower()
        assert "shell" in combined.lower()

    @pytest.mark.unit
    def test_completion_no_args(self):
        """Test completion command with no arguments shows general info."""
        result = runner.invoke(app, ["completion"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "completion" in combined.lower()
        assert "bash" in combined.lower()
        assert "zsh" in combined.lower()
        assert "fish" in combined.lower()

    @pytest.mark.unit
    def test_completion_unsupported_shell(self):
        """Test completion command with unsupported shell."""
        result = runner.invoke(app, ["completion", "unsupported-shell"])
        
        # Should fail with exit code 2
        assert result.exit_code == 2
        combined = _combined_output(result)
        assert "unsupported" in combined.lower() or "not supported" in combined.lower()

    @pytest.mark.unit
    def test_completion_bash_instructions(self):
        """Test completion command shows bash instructions."""
        result = runner.invoke(app, ["completion", "bash"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "bash" in combined.lower()
        assert "completion" in combined.lower()

    @pytest.mark.unit
    def test_completion_install_flag(self):
        """Test completion command with install flag."""
        result = runner.invoke(app, ["completion", "bash", "--install"])
        combined = _combined_output(result)
        
        # Should show installation instructions
        assert result.exit_code in [0, 1]  # May fail if can't write files
        assert "bash" in combined.lower()

    @pytest.mark.unit
    def test_completion_verify_flag(self):
        """Test completion command with verify flag."""
        result = runner.invoke(app, ["completion", "bash", "--verify"])
        combined = _combined_output(result)
        
        # Should show verification results
        assert result.exit_code in [0, 1]  # May pass or fail depending on installation
        assert "verify" in combined.lower() or "completion" in combined.lower()
