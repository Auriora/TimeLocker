"""
Unit tests for TimeLocker CLI credentials command group.

Tests credentials command parsing, parameter validation, help output, and error handling.

Notes:
- The legacy 'credentials set' command has been renamed to 'credentials store'; tests updated accordingly.
- Exit code assertions are now strict (exact expected codes) except where explicitly documented as environment-dependent.
- Patch targets use 'src.TimeLocker.security.credential_manager.CredentialManager' because the CLI
  imports CredentialManager inside each command function rather than at module scope.
"""

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from src.TimeLocker.cli import app
from .test_utils import (
    combined_output,
    assert_success,
    assert_handled_error,
    assert_exit_code,
)

# Standard runner
runner = CliRunner(env={'COLUMNS': '200'})


class TestCredentialsCommands:
    """Test suite for credentials command group."""

    @pytest.mark.unit
    def test_credentials_help_output(self):
        result = runner.invoke(app, ["credentials", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "credential" in combined.lower()
        assert "management" in combined.lower()
        assert "unlock" in combined.lower()
        assert "store" in combined.lower()
        assert "remove" in combined.lower()

    @pytest.mark.unit
    def test_credentials_unlock_help(self):
        result = runner.invoke(app, ["credentials", "unlock", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "unlock" in combined.lower()
        assert "credential" in combined.lower()

    @pytest.mark.unit
    def test_credentials_store_help(self):
        result = runner.invoke(app, ["credentials", "store", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "store" in combined.lower()
        assert "repository" in combined.lower()
        assert "password" in combined.lower()

    @pytest.mark.unit
    def test_credentials_remove_help(self):
        result = runner.invoke(app, ["credentials", "remove", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "remove" in combined.lower()
        assert "repository" in combined.lower()
        assert "password" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_unlock_command_success(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.unlock.return_value = True
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "unlock", "--password", "master"])
        assert_success(result)
        mock_cm.unlock.assert_called_once_with("master")

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_unlock_command_failure(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.unlock.return_value = False
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "unlock", "--password", "wrong"])
        assert_handled_error(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_store_command_success(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = False
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "store", "repo1", "--password", "pw"])
        assert_success(result)
        mock_cm.store_repository_password.assert_called_once_with("repo1", "pw")

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_store_command_locked_unlocks(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = True
        mock_cm.unlock.return_value = True
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "store", "repo2", "--master-password", "master", "--password", "pw2"])
        assert_success(result)
        mock_cm.unlock.assert_called_once_with("master")
        mock_cm.store_repository_password.assert_called_once_with("repo2", "pw2")

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_store_command_unlock_failure(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = True
        mock_cm.unlock.return_value = False
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "store", "repo3", "--master-password", "bad", "--password", "pw"])
        assert_handled_error(result)
        mock_cm.store_repository_password.assert_not_called()

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_store_failure(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = False
        mock_cm.store_repository_password.side_effect = RuntimeError("boom")
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "store", "repo4", "--password", "pw"])
        assert_handled_error(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_list_success_empty(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = False
        mock_cm.list_repositories.return_value = []
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "list", "--password", "master"])
        assert_success(result)  # Empty list is still success

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_list_unlock_failure(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = True
        mock_cm.unlock.return_value = False
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "list", "--password", "bad"])
        assert_handled_error(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_remove_success(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = False
        mock_cm.remove_repository.return_value = True
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "remove", "repo1", "--password", "master"])
        assert_success(result)
        mock_cm.remove_repository.assert_called_once_with("repo1")

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_remove_no_password_found(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = False
        mock_cm.remove_repository.return_value = False
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "remove", "repoX", "--password", "master"])
        assert_success(result)  # Warning only

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_remove_unlock_failure(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = True
        mock_cm.unlock.return_value = False
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "remove", "repoY", "--password", "master"])
        assert_handled_error(result)

    @pytest.mark.unit
    def test_credentials_store_missing_repository(self):
        result = runner.invoke(app, ["credentials", "store"])
        assert_exit_code(result, 2, "Missing repository name should be a usage error")

    @pytest.mark.unit
    def test_credentials_remove_missing_repository(self):
        result = runner.invoke(app, ["credentials", "remove"])
        assert_exit_code(result, 2, "Missing repository name should be a usage error")

    @pytest.mark.unit
    @patch('src.TimeLocker.security.credential_manager.CredentialManager')
    def test_credentials_remove_failure(self, mock_cm_cls):
        mock_cm = Mock()
        mock_cm.is_locked.return_value = False
        mock_cm.remove_repository.side_effect = RuntimeError("fail remove")
        mock_cm_cls.return_value = mock_cm
        result = runner.invoke(app, ["credentials", "remove", "repoZ", "--password", "master"])
        assert_handled_error(result)
