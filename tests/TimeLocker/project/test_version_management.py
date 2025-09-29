"""
Tests for version management functionality.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest


def get_project_root():
    """Get the project root directory."""
    # From tests/TimeLocker/project/test_version_management.py, go up 4 levels to reach project root
    return Path(__file__).parent.parent.parent.parent


def get_version_from_file(file_path, pattern):
    """Extract version from a file using a regex pattern."""
    if not file_path.exists():
        return None

    with open(file_path, "r") as f:
        content = f.read()
        match = re.search(pattern, content)
        if match:
            return match.group(1)

    return None


class TestVersionConsistency:
    """Test version consistency across files."""

    @pytest.mark.config
    @pytest.mark.unit
    def test_pyproject_toml_has_version(self):
        """Test that pyproject.toml contains a version."""
        pyproject_file = get_project_root() / "pyproject.toml"
        # Use more flexible regex to handle whitespace variations
        version = get_version_from_file(pyproject_file, r'version\s*=\s*["\']([^"\']+)["\']')

        assert version is not None, "pyproject.toml should contain a version"
        assert re.match(r'\d+\.\d+\.\d+', version), f"Version should be semantic: {version}"

    @pytest.mark.config
    @pytest.mark.unit
    def test_init_py_has_version(self):
        """Test that __init__.py contains a version."""
        init_file = get_project_root() / "src" / "TimeLocker" / "__init__.py"
        # Use more flexible regex to handle whitespace variations
        version = get_version_from_file(init_file, r'__version__\s*=\s*["\']([^"\']+)["\']')

        assert version is not None, "__init__.py should contain a __version__"
        assert re.match(r'\d+\.\d+\.\d+', version), f"Version should be semantic: {version}"

    @pytest.mark.config
    @pytest.mark.unit
    def test_versions_are_consistent(self):
        """Test that versions are consistent across files."""
        pyproject_file = get_project_root() / "pyproject.toml"
        init_file = get_project_root() / "src" / "TimeLocker" / "__init__.py"

        # Use more flexible regex patterns
        pyproject_version = get_version_from_file(pyproject_file, r'version\s*=\s*["\']([^"\']+)["\']')
        init_version = get_version_from_file(init_file, r'__version__\s*=\s*["\']([^"\']+)["\']')

        assert pyproject_version == init_version, (
                f"Versions must be consistent: "
                f"pyproject.toml={pyproject_version}, __init__.py={init_version}"
        )


class TestVersionManagementScript:
    """Test the version management script."""

    @pytest.mark.config
    @pytest.mark.unit
    def test_script_exists(self):
        """Test that the version management script exists."""
        script_path = get_project_root() / "scripts" / "bump_version.py"
        assert script_path.exists(), "Version management script should exist"
        assert script_path.is_file(), "Script should be a file"

    @pytest.mark.config
    @pytest.mark.unit
    def test_script_is_executable(self):
        """Test that the script has execute permissions."""
        script_path = get_project_root() / "scripts" / "bump_version.py"
        assert script_path.stat().st_mode & 0o111, "Script should be executable"

    @pytest.mark.config
    @pytest.mark.unit
    def test_show_command_works(self):
        """Test that the show command works."""
        script_path = get_project_root() / "scripts" / "bump_version.py"

        result = subprocess.run(
                [sys.executable, str(script_path), "show"],
                cwd=get_project_root(),
                capture_output=True,
                text=True
        )

        assert result.returncode == 0, f"Show command failed: {result.stderr}"
        assert "Current version:" in result.stdout, "Should show current version"
        assert "Versions are consistent" in result.stdout, "Should check consistency"

    @pytest.mark.config
    @pytest.mark.unit
    def test_dry_run_works(self):
        """Test that dry run works without making changes."""
        script_path = get_project_root() / "scripts" / "bump_version.py"

        # Get current version before dry run
        pyproject_file = get_project_root() / "pyproject.toml"
        version_before = get_version_from_file(pyproject_file, r'version = "([^"]+)"')

        # Run dry run
        result = subprocess.run(
                [sys.executable, str(script_path), "bump", "patch", "--dry-run"],
                cwd=get_project_root(),
                capture_output=True,
                text=True
        )

        # Check that command succeeded
        assert result.returncode == 0, f"Dry run failed: {result.stderr}"

        # Check that version wasn't actually changed
        version_after = get_version_from_file(pyproject_file, r'version = "([^"]+)"')
        assert version_before == version_after, "Dry run should not change version"


class TestBumpVersionConfig:
    """Test bump2version configuration."""

    @pytest.mark.config
    @pytest.mark.unit
    def test_config_file_exists(self):
        """Test that .bumpversion.cfg exists."""
        config_file = get_project_root() / ".bumpversion.cfg"
        assert config_file.exists(), ".bumpversion.cfg should exist"

    @pytest.mark.config
    @pytest.mark.unit
    def test_config_has_required_sections(self):
        """Test that config file has required sections."""
        config_file = get_project_root() / ".bumpversion.cfg"

        with open(config_file, "r") as f:
            content = f.read()

        assert "[bumpversion]" in content, "Should have [bumpversion] section"
        assert "[bumpversion:file:pyproject.toml]" in content, "Should configure pyproject.toml"
        assert "[bumpversion:file:src/TimeLocker/__init__.py]" in content, "Should configure __init__.py"

    @pytest.mark.config
    @pytest.mark.unit
    def test_config_current_version_matches(self):
        """Test that config current_version matches actual version."""
        config_file = get_project_root() / ".bumpversion.cfg"
        pyproject_file = get_project_root() / "pyproject.toml"

        config_version = get_version_from_file(config_file, r'current_version = ([^\s]+)')
        pyproject_version = get_version_from_file(pyproject_file, r'version = "([^"]+)"')

        assert config_version == pyproject_version, (
                f"Config version ({config_version}) should match "
                f"pyproject.toml version ({pyproject_version})"
        )
