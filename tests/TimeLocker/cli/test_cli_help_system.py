"""
Comprehensive tests for TimeLocker CLI help system and documentation quality.

Tests help output, command discovery, documentation completeness, and user guidance.
"""

import pytest
import re
from typer.testing import CliRunner

from src.TimeLocker.cli import app

# Set wider terminal width to prevent help text truncation in CI
runner = CliRunner(env={'COLUMNS': '200'})


def _combined_output(result):
    """Combine stdout and stderr for matching convenience across environments."""
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


class TestCLIHelpSystem:
    """Test suite for CLI help system and documentation quality."""

    @pytest.mark.unit
    def test_main_help_output_quality(self):
        """Test main CLI help output quality and completeness."""
        result = runner.invoke(app, ["--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        
        # Check for essential content
        assert "timelocker" in combined.lower()
        assert "backup" in combined.lower()
        
        # Check for command groups
        expected_groups = ["backup", "snapshots", "repos", "targets", "config", "credentials"]
        for group in expected_groups:
            assert group in combined.lower(), f"Command group '{group}' not found in help"
        
        # Check for examples
        assert "examples" in combined.lower() or "example" in combined.lower()
        
        # Check for proper formatting (Rich markup)
        assert len(combined) > 500, "Help output should be substantial"

    @pytest.mark.unit
    def test_command_group_help_completeness(self):
        """Test that all command groups have proper help output."""
        command_groups = [
            "backup",
            "snapshots", 
            "repos",
            "targets",
            "config",
            "credentials"
        ]
        
        for group in command_groups:
            result = runner.invoke(app, [group, "--help"])
            combined = _combined_output(result)
            
            assert result.exit_code == 0, f"Help for '{group}' command group failed"
            assert group in combined.lower(), f"Group name '{group}' not in help output"
            assert len(combined) > 100, f"Help for '{group}' should be substantial"
            
            # Should show available subcommands
            assert "commands" in combined.lower() or "usage" in combined.lower()

    @pytest.mark.unit
    def test_backup_subcommands_help(self):
        """Test backup subcommands help output."""
        subcommands = ["create", "verify"]
        
        for subcmd in subcommands:
            result = runner.invoke(app, ["backup", subcmd, "--help"])
            combined = _combined_output(result)
            
            assert result.exit_code == 0, f"Help for 'backup {subcmd}' failed"
            assert subcmd in combined.lower()
            assert "backup" in combined.lower()
            
            # Should show options
            assert "--" in combined, f"No options shown for 'backup {subcmd}'"

    @pytest.mark.unit
    def test_snapshots_subcommands_help(self):
        """Test snapshots subcommands help output."""
        subcommands = [
            "list", "show", "contents", "restore", "mount", "umount",
            "find-in", "forget", "prune", "diff", "find"
        ]
        
        for subcmd in subcommands:
            result = runner.invoke(app, ["snapshots", subcmd, "--help"])
            combined = _combined_output(result)
            
            assert result.exit_code == 0, f"Help for 'snapshots {subcmd}' failed"
            assert len(combined) > 50, f"Help for 'snapshots {subcmd}' should be informative"

    @pytest.mark.unit
    def test_repos_subcommands_help(self):
        """Test repos subcommands help output."""
        subcommands = [
            "list", "add", "remove", "show", "default", "init", 
            "check", "stats", "unlock", "migrate", "forget",
            "check-all", "stats-all"
        ]
        
        for subcmd in subcommands:
            result = runner.invoke(app, ["repos", subcmd, "--help"])
            combined = _combined_output(result)
            
            assert result.exit_code == 0, f"Help for 'repos {subcmd}' failed"
            assert len(combined) > 50, f"Help for 'repos {subcmd}' should be informative"

    @pytest.mark.unit
    def test_targets_subcommands_help(self):
        """Test targets subcommands help output."""
        subcommands = ["list", "add", "show", "edit", "remove"]
        
        for subcmd in subcommands:
            result = runner.invoke(app, ["targets", subcmd, "--help"])
            combined = _combined_output(result)
            
            assert result.exit_code == 0, f"Help for 'targets {subcmd}' failed"
            assert len(combined) > 50, f"Help for 'targets {subcmd}' should be informative"

    @pytest.mark.unit
    def test_config_subcommands_help(self):
        """Test config subcommands help output."""
        subcommands = ["show", "setup"]
        
        for subcmd in subcommands:
            result = runner.invoke(app, ["config", subcmd, "--help"])
            combined = _combined_output(result)
            
            assert result.exit_code == 0, f"Help for 'config {subcmd}' failed"
            assert len(combined) > 50, f"Help for 'config {subcmd}' should be informative"

    @pytest.mark.unit
    def test_config_import_subcommands_help(self):
        """Test config import subcommands help output."""
        # Test import group
        result = runner.invoke(app, ["config", "import", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "import" in combined.lower()
        
        # Test import subcommands
        import_subcommands = ["restic", "timeshift"]
        for subcmd in import_subcommands:
            result = runner.invoke(app, ["config", "import", subcmd, "--help"])
            combined = _combined_output(result)
            
            assert result.exit_code == 0, f"Help for 'config import {subcmd}' failed"
            assert subcmd in combined.lower()

    @pytest.mark.unit
    def test_credentials_subcommands_help(self):
        """Test credentials subcommands help output."""
        subcommands = ["unlock", "set", "remove"]
        
        for subcmd in subcommands:
            result = runner.invoke(app, ["credentials", subcmd, "--help"])
            combined = _combined_output(result)
            
            assert result.exit_code == 0, f"Help for 'credentials {subcmd}' failed"
            assert len(combined) > 50, f"Help for 'credentials {subcmd}' should be informative"

    @pytest.mark.unit
    def test_help_option_consistency(self):
        """Test that --help option works consistently across all commands."""
        commands_to_test = [
            ["--help"],
            ["backup", "--help"],
            ["snapshots", "--help"],
            ["repos", "--help"],
            ["targets", "--help"],
            ["config", "--help"],
            ["credentials", "--help"],
            ["backup", "create", "--help"],
            ["snapshots", "list", "--help"],
            ["repos", "add", "--help"],
            ["targets", "add", "--help"],
            ["config", "show", "--help"],
            ["credentials", "set", "--help"]
        ]
        
        for cmd in commands_to_test:
            result = runner.invoke(app, cmd)
            assert result.exit_code == 0, f"Help failed for command: {' '.join(cmd)}"
            
            combined = _combined_output(result)
            # Should contain usage information
            assert "usage" in combined.lower() or "options" in combined.lower()

    @pytest.mark.unit
    def test_command_discovery(self):
        """Test that users can discover available commands."""
        # Main help should list all command groups
        result = runner.invoke(app, ["--help"])
        combined = _combined_output(result)
        
        command_groups = ["backup", "snapshots", "repos", "targets", "config", "credentials"]
        for group in command_groups:
            assert group in combined, f"Command group '{group}' not discoverable in main help"

    @pytest.mark.unit
    def test_option_documentation_quality(self):
        """Test that command options are well documented."""
        # Test key commands that should have good option documentation
        commands_with_options = [
            ["backup", "create", "--help"],
            ["snapshots", "list", "--help"],
            ["repos", "add", "--help"],
            ["targets", "add", "--help"]
        ]
        
        for cmd in commands_with_options:
            result = runner.invoke(app, cmd)
            combined = _combined_output(result)
            
            assert result.exit_code == 0
            
            # Should have option descriptions
            assert "--" in combined, f"No options found for {' '.join(cmd[:-1])}"
            
            # Common options should be documented
            if "backup" in cmd or "snapshots" in cmd:
                # Repository option should be documented
                assert "--repository" in combined or "-r" in combined

    @pytest.mark.unit
    def test_error_message_helpfulness(self):
        """Test that error messages provide helpful guidance."""
        # Test commands that should show helpful errors
        error_scenarios = [
            # Missing required arguments
            ["snapshots", "show"],  # Missing snapshot ID
            ["repos", "init"],      # Missing repository name
            ["targets", "show"],    # Missing target name
            ["credentials", "set"]  # Missing repository name
        ]
        
        for cmd in error_scenarios:
            result = runner.invoke(app, cmd)
            combined = _combined_output(result)
            
            # Should exit with error
            assert result.exit_code != 0, f"Command should fail: {' '.join(cmd)}"
            
            # Error message should be helpful (not just a stack trace)
            assert len(combined) > 10, f"Error message too short for: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_alias_documentation(self):
        """Test that command aliases are documented."""
        # Test that 'tl' alias is mentioned in help
        result = runner.invoke(app, ["--help"])
        combined = _combined_output(result)
        
        # Should mention the alias or show it in usage
        assert "tl" in combined.lower() or "alias" in combined.lower()

    @pytest.mark.unit
    def test_examples_in_help(self):
        """Test that help output includes useful examples."""
        result = runner.invoke(app, ["--help"])
        combined = _combined_output(result)
        
        # Should include examples
        assert "example" in combined.lower()
        
        # Should show actual command examples
        assert "tl " in combined or "timelocker " in combined

    @pytest.mark.unit
    def test_version_command_help(self):
        """Test version command help output."""
        result = runner.invoke(app, ["version", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "version" in combined.lower()

    @pytest.mark.unit
    def test_completion_command_help(self):
        """Test completion command help output."""
        result = runner.invoke(app, ["completion", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "completion" in combined.lower()
        assert "shell" in combined.lower()

    @pytest.mark.unit
    def test_help_formatting_quality(self):
        """Test that help output is well formatted and readable."""
        result = runner.invoke(app, ["--help"])
        combined = _combined_output(result)
        
        # Should not have obvious formatting issues
        assert not re.search(r'\[.*\].*\[.*\]', combined), "Potential Rich markup issues"
        
        # Should have reasonable line lengths (not too long)
        lines = combined.split('\n')
        long_lines = [line for line in lines if len(line) > 120]
        assert len(long_lines) < 5, "Too many overly long lines in help output"

    @pytest.mark.unit
    def test_help_consistency_across_commands(self):
        """Test that help output is consistent across similar commands."""
        # Test that similar commands have similar help structure
        list_commands = [
            ["repos", "list", "--help"],
            ["targets", "list", "--help"],
            ["snapshots", "list", "--help"]
        ]
        
        help_outputs = []
        for cmd in list_commands:
            result = runner.invoke(app, cmd)
            assert result.exit_code == 0
            help_outputs.append(_combined_output(result))
        
        # All should mention listing
        for output in help_outputs:
            assert "list" in output.lower()
        
        # Should have similar structure (all have options section, etc.)
        for output in help_outputs:
            assert "options" in output.lower() or "usage" in output.lower()
