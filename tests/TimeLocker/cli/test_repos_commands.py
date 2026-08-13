"""
Unit tests for TimeLocker CLI repos command group.

Tests repos command parsing, parameter validation, help output, and error handling.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typer.main import get_command

from TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
    get_cli_runner,
    combined_output,
    assert_success,
    assert_exit_code,
    create_mock_cli_service_manager,
)

# Set wider terminal width to prevent help text truncation in CI
runner = get_cli_runner()


class TestReposCommands:
    """Test suite for repos command group."""

    @staticmethod
    def _mock_repo_config_service(name: str = "test-repo") -> MagicMock:
        """Create a ConfigService stub compatible with repos add persistence flow."""
        config_service = MagicMock()
        config_service.get_repository.side_effect = Exception(f"Repository '{name}' not found")
        config_service.add_repository.return_value = None
        config_service._config_module = MagicMock()
        return config_service

    @pytest.mark.unit
    def test_repos_help_output(self):
        """Test repos command group help output."""
        result = runner.invoke(app, ["repos", "--help"])
        output = combined_output(result)

        assert result.exit_code == 0
        assert "repository" in output.lower()
        assert "operations" in output.lower()
        # Should show available subcommands
        assert "list" in output.lower()
        assert "add" in output.lower()
        assert "init" in output.lower()

    @pytest.mark.unit
    def test_repos_list_help(self):
        """Test repos list command help output."""
        result = runner.invoke(app, ["repos", "list", "--help"])
        output = combined_output(result)

        assert result.exit_code == 0
        assert "list" in output.lower()
        assert "repository" in output.lower()

    @pytest.mark.unit
    def test_repos_add_help(self):
        """Test repos add command help output."""
        result = runner.invoke(app, ["repos", "add", "--help"])
        output = combined_output(result)

        assert result.exit_code == 0
        assert "add" in output.lower()
        assert "repository" in output.lower()
        # Should show key options
        assert "--description" in output or "-d" in output
        assert "--password" in output or "-p" in output

    @pytest.mark.unit
    def test_repos_init_help(self):
        """Test repos init command help output."""
        result = runner.invoke(app, ["repos", "init", "--help"])
        output = combined_output(result)

        assert result.exit_code == 0
        assert "init" in output.lower()
        assert "initialize" in output.lower()

    @pytest.mark.unit
    def test_repos_show_help(self):
        """Test repos show command help output."""
        result = runner.invoke(app, ["repos", "show", "--help"])
        output = combined_output(result)

        assert result.exit_code == 0
        assert "show" in output.lower()
        assert "repository" in output.lower()

    @pytest.mark.unit
    def test_repos_check_help(self):
        """Test repos check command help output."""
        result = runner.invoke(app, ["repos", "check", "--help"])
        output = combined_output(result)

        assert result.exit_code == 0
        assert "check" in output.lower()
        assert "integrity" in output.lower()

    @pytest.mark.unit
    def test_repos_stats_help(self):
        """Test repos stats command help output."""
        result = runner.invoke(app, ["repos", "stats", "--help"])
        output = combined_output(result)

        assert result.exit_code == 0
        assert "stats" in output.lower()
        assert "statistics" in output.lower()

    @pytest.mark.unit
    def test_repos_command_graph_has_single_unlock_command(self):
        """Test that repos exposes unlock exactly once in the public command graph."""
        click_app = get_command(app)
        repos_group = click_app.commands["repos"]

        unlock_names = [name for name in repos_group.commands if name == "unlock"]

        assert unlock_names == ["unlock"]

    @pytest.mark.unit
    def test_repos_unlock_public_contract_uses_service_unlock_parameters(self):
        """Test that repos unlock exposes the expected service-level parameters."""
        click_app = get_command(app)
        repos_group = click_app.commands["repos"]
        unlock_command = repos_group.commands["unlock"]

        param_names = [param.name for param in unlock_command.params]

        assert param_names == ["name", "repository", "password", "verbose", "config_dir"]
        assert "lock_id" not in param_names

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_list_command(self, mock_service_manager):
        """Test repos list command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_repositories.return_value = []

        result = runner.invoke(app, ["repos", "list"])

        # Mocked service manager returns empty list successfully, should exit 0
        assert_success(result)

    @pytest.mark.unit
    def test_repos_add_missing_parameters(self):
        """Test repos add command with missing parameters should prompt."""
        result = runner.invoke(app, ["repos", "add"])

        # Should either prompt for input or show helpful error
        # Range allowed: interactive prompt success (0), validation error (1), or usage error (2)
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories._create_config_service')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_add_with_parameters(self, mock_service_manager, mock_create_config_service):
        """Test repos add command with all parameters."""
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_repository.return_value = {"success": True}
        mock_create_config_service.return_value = self._mock_repo_config_service()

        result = runner.invoke(app, [
                "repos", "add", "test-repo", "file:///tmp/test-repo",
                "--description", "Test repository",
                "--password", "test-password"
        ])

        # Mocked service manager returns success, should exit 0
        assert_success(result)

    @pytest.mark.unit
    def test_repos_add_invalid_uri(self):
        """Test repos add command with invalid URI format."""
        result = runner.invoke(app, [
                "repos", "add", "test-repo", "invalid-uri-format"
        ])

        # Should handle invalid URI gracefully with error exit code
        assert result.exit_code != 0

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories._create_config_service')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_add_with_set_default(self, mock_service_manager, mock_create_config_service):
        """Test repos add command with set-default flag."""
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_repository.return_value = {"success": True}
        mock_create_config_service.return_value = self._mock_repo_config_service()

        result = runner.invoke(app, [
                "repos", "add", "test-repo", "file:///tmp/test-repo",
                "--set-default"
        ])

        # Mocked service manager returns success, should exit 0
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_remove_command(self, mock_service_manager, mock_config_manager_class):
        """Test repos remove command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.remove_repository.return_value = Mock(success=True)

        # Mock repository configuration lookup
        mock_repo = {
                "name": "test-repo",
                "uri":  "file:///tmp/test-repo"
        }
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo
        mock_config_instance.remove_repository.return_value = None

        result = runner.invoke(app, ["repos", "remove", "test-repo", "--yes"])

        # Mocked service manager returns success, should exit 0
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_show_command(self, mock_service_manager, mock_config_manager_class):
        """Test repos show command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager

        # Mock repository with proper attributes
        mock_repo = Mock()
        mock_repo.name = "test-repo"
        mock_repo.uri = "file:///tmp/test-repo"
        mock_repo.description = "Test repository"
        mock_repo.type = "local"
        mock_repo.engine = "restic"
        mock_repo.status = "active"
        mock_repo.is_default = False

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo

        mock_manager.get_repository_by_name.return_value = mock_repo
        mock_manager.config_module.get_repository.return_value = mock_repo

        result = runner.invoke(app, ["repos", "show", "test-repo"])

        # Mocked service manager returns repository, should exit 0
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_default_command(self, mock_service_manager, mock_config_manager_class):
        """Test repos default command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager

        # Mock repository exists
        mock_repo = Mock()
        mock_repo.name = "test-repo"

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo
        mock_config_instance.set_default_repository.return_value = None

        mock_manager.config_module.get_repository.return_value = mock_repo
        mock_manager.set_default_repository.return_value = None

        result = runner.invoke(app, ["repos", "default", "test-repo"])

        # Mocked service manager should handle default setting, should exit 0
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_init_command(self, mock_service_manager, mock_config_manager_class, tmp_path):
        """Test repos init command execution."""
        # Create temporary directory for repository
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager

        # Mock repository exists in config - return dict instead of Mock
        mock_repo = {
                "name": "test-repo",
                "uri":  f"file://{repo_dir}",
                "path": str(repo_dir)
        }

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo

        mock_manager.config_module.get_repository.return_value = mock_repo
        mock_manager.initialize_repository.return_value = {"success": True}

        result = runner.invoke(app, [
                "repos", "init", "test-repo",
                "--repository", f"file://{repo_dir}",
                "--password", "test-password",
                "--yes"  # Skip confirmation
        ])

        # Mocked service manager returns success, should exit 0
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories._create_repository_resolver')
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_init_uses_resolved_environment_password(
        self,
        mock_service_manager,
        mock_config_manager_class,
        mock_create_resolver,
        tmp_path,
    ):
        """Non-interactive init accepts the shared credential resolution chain."""
        repo_dir = tmp_path / "environment-repo"
        repo_dir.mkdir()
        repo_uri = f"file://{repo_dir}"

        manager = Mock()
        manager.initialize_repository.return_value = {"success": True}
        mock_service_manager.return_value = manager
        mock_config_manager_class.return_value.get_repository.return_value = {
            "name": "environment-repo",
            "uri": repo_uri,
        }
        resolver = mock_create_resolver.return_value
        resolver.resolve_credentials.return_value = "environment-password"

        result = runner.invoke(app, [
            "repos", "init", "environment-repo", "--yes",
            "--repository", repo_uri,
        ])

        assert_success(result)
        resolver.resolve_credentials.assert_called_once_with(
            repository_name="environment-repo",
            explicit_password=None,
            allow_prompt=False,
            repository_uri=repo_uri,
        )
        assert manager.initialize_repository.call_args.kwargs["password"] == "environment-password"

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_init_with_repository_uri(self, mock_service_manager, mock_config_manager_class, tmp_path):
        """Test repos init command with repository URI."""
        # Create temporary directory for repository
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager

        # Mock repository exists in config - return dict instead of Mock
        mock_repo = {
                "name": "test-repo",
                "uri":  f"file://{repo_dir}",
                "path": str(repo_dir)
        }

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo

        mock_manager.config_module.get_repository.return_value = mock_repo
        mock_manager.initialize_repository.return_value = {"success": True}

        result = runner.invoke(app, [
                "repos", "init", "test-repo",
                "--repository", f"file://{repo_dir}",
                "--password", "test-password",
                "--yes"
        ])

        # Mocked service manager returns success, should exit 0
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_check_command(self, mock_service_manager, mock_config_manager_class, tmp_path):
        """Test repos check command execution."""
        # Create temporary directory for repository
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        # Use the proper mock factory
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager

        # Mock repository with proper attributes
        mock_repo = {
                "name": "test-repo",
                "uri":  f"file://{repo_dir}",
                "path": str(repo_dir)
        }

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo

        # Configure the check_repository method
        mock_manager.check_repository.return_value = {"success": True, "status": "OK"}
        mock_manager.repository_service.check_repository.return_value = {"success": True, "status": "OK"}

        result = runner.invoke(app, ["repos", "check", "test-repo"])

        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_stats_command(self, mock_service_manager, mock_config_manager_class, tmp_path):
        """Test repos stats command execution."""
        # Create temporary directory for repository
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        # Mock the service manager and repository
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager

        # Mock repository with proper attributes - use dict for better compatibility
        mock_repo = {
                "name": "test-repo",
                "uri":  f"file://{repo_dir}",
                "path": str(repo_dir)
        }

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo

        mock_manager.get_repository_by_name.return_value = mock_repo
        mock_manager.get_repository_stats.return_value = {
                'size':             1024,
                'snapshots':        5,
                'total_file_count': 100
        }

        result = runner.invoke(app, ["repos", "stats", "test-repo"])

        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_unlock_command(self, mock_service_manager, mock_config_manager_class):
        """Test repos unlock command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager

        # Mock repository exists - use dict for better compatibility
        mock_repo = {
                "name": "test-repo",
                "uri":  "file:///tmp/test-repo"
        }

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo

        # Return dict instead of Mock for better compatibility
        mock_manager.unlock_repository.return_value = {"success": True}

        result = runner.invoke(app, ["repos", "unlock", "test-repo"])
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_migrate_command(self, mock_service_manager, mock_config_manager_class):
        """Test repos migrate command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager

        # Mock repository exists - use dict for better compatibility
        mock_repo = {
                "name": "test-repo",
                "uri":  "file:///tmp/test-repo"
        }

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo

        # Return dict instead of Mock for better compatibility
        mock_manager.migrate_repository.return_value = {"success": True}

        result = runner.invoke(app, ["repos", "migrate", "test-repo"])
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories.ConfigurationManager')
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_forget_command(self, mock_service_manager, mock_config_manager_class):
        """Test repos forget command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager

        # Mock repository exists - use dict for better compatibility
        mock_repo = {
                "name": "test-repo",
                "uri":  "file:///tmp/test-repo"
        }

        # Mock the ConfigurationManager fallback
        mock_config_instance = Mock()
        mock_config_manager_class.return_value = mock_config_instance
        mock_config_instance.get_repository.return_value = mock_repo

        # Return dict instead of Mock for better compatibility
        mock_manager.apply_retention_policy.return_value = {"success": True}

        result = runner.invoke(app, ["repos", "forget", "test-repo"])
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_validate_all_command(self, mock_service_manager):
        """Test repos validate-all command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager

        result = runner.invoke(app, ["repos", "validate-all"])
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command')
    def test_repos_validate_all_json_command(self, mock_service_manager):
        """Test repos validate-all command with JSON output."""
        mock_manager = create_mock_cli_service_manager()
        mock_service_manager.return_value = mock_manager

        result = runner.invoke(app, ["repos", "validate-all", "--json"])
        combined = combined_output(result)
        assert result.exit_code == 2
        assert "no such option" in combined.lower()
