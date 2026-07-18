"""
Unit tests for TimeLocker CLI repository backend credentials sub-commands.

Covers:
- Help output for repos credentials group and subcommands (set/remove/show)
- Successful S3 credentials set (interactive prompts mocked)
- Unsupported repository type handling
- Credentials removal (found / not found)
- Credentials show (present / absent)
- Locked credential manager scenarios
"""

import pytest
from collections.abc import Generator
from types import SimpleNamespace
from typing import TypedDict
from unittest.mock import Mock, patch
from click.testing import Result
from typer.testing import CliRunner

from TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
    combined_output,
    assert_success,
)

runner = CliRunner(env={'COLUMNS': '200'})


class RepoS3Mocks(TypedDict):
    """Typed payload shared by repository credential command tests."""

    mock_cm_class: Mock
    mock_config_class: Mock
    repo_obj: SimpleNamespace
    cm_instance: Mock


# Fixture: patch ConfigurationModule
@pytest.fixture
def mock_config_module() -> Generator[Mock, None, None]:
    with patch('TimeLocker.config.configuration_module.ConfigurationModule') as m:
        yield m


# Fixture: patch CredentialManager
@pytest.fixture
def mock_cm() -> Generator[Mock, None, None]:
    with patch('TimeLocker.security.credential_manager.CredentialManager') as m:
        yield m


# Fixture: patch PromptService class globally for tests needing dynamic side effects
@pytest.fixture
def mock_prompt_service() -> Generator[Mock, None, None]:
    with patch('TimeLocker.utils.PromptService') as p:
        yield p


# New fixture to DRY up repeated ConfigurationModule/CredentialManager S3 repo setup
@pytest.fixture
def repo_s3_mocks(mock_cm: Mock, mock_config_module: Mock) -> Generator[RepoS3Mocks, None, None]:
    repo_obj = SimpleNamespace(uri='s3://bucket/path')
    mock_config_module.return_value.get_repository.return_value = repo_obj
    cm_instance = Mock()
    cm_instance.is_locked.return_value = False
    mock_cm.return_value = cm_instance
    yield {
            'mock_cm_class':     mock_cm,
            'mock_config_class': mock_config_module,
            'repo_obj':          repo_obj,
            'cm_instance':       cm_instance
    }


@pytest.mark.unit
def test_repos_credentials_group_help() -> None:
    result: Result = runner.invoke(app, ["repos", "credentials", "--help"])  # type: ignore[arg-type]
    combined = combined_output(result)
    assert result.exit_code == 0
    assert "credential" in combined.lower()
    assert "set" in combined.lower()
    assert "remove" in combined.lower()
    assert "show" in combined.lower()


@pytest.mark.unit
def test_repos_credentials_set_s3_success(repo_s3_mocks: RepoS3Mocks) -> None:
    # Patch PromptService methods
    with patch('TimeLocker.utils.PromptService.prompt_text', side_effect=["AKIA123", "us-east-1"]), \
            patch('TimeLocker.utils.PromptService.prompt_password', return_value="SECRET456"), \
            patch('TimeLocker.utils.PromptService.prompt_confirm', return_value=False):
        result: Result = runner.invoke(app, ["repos", "credentials", "set", "myrepo"])  # type: ignore[arg-type]
    combined = (result.stdout or "").lower()
    # Mocked prompts and credential manager should succeed
    assert_success(result)
    repo_s3_mocks['cm_instance'].store_repository_backend_credentials.assert_called_once_with('myrepo', 's3', {
            'access_key_id':     'AKIA123',
            'secret_access_key': 'SECRET456',
            'region':            'us-east-1'
    })
    assert 'credentials' in combined


@pytest.mark.unit
def test_repos_credentials_set_s3_insecure_tls(repo_s3_mocks: RepoS3Mocks) -> None:
    # Patch PromptService methods
    with patch('TimeLocker.utils.PromptService.prompt_text', side_effect=["AKIAKEY", ""]), \
            patch('TimeLocker.utils.PromptService.prompt_password', return_value="SECRETKEY"), \
            patch('TimeLocker.utils.PromptService.prompt_confirm', return_value=True):
        result: Result = runner.invoke(app, ["repos", "credentials", "set", "myrepo"])  # type: ignore[arg-type]
    repo_s3_mocks['cm_instance'].store_repository_backend_credentials.assert_called_once_with('myrepo', 's3', {
            'access_key_id':     'AKIAKEY',
            'secret_access_key': 'SECRETKEY',
            'insecure_tls':      True
    })
    # Mocked prompts and credential manager should succeed
    assert_success(result)


@pytest.mark.unit
def test_repos_credentials_set_unsupported_type(mock_config_module: Mock, mock_cm: Mock) -> None:
    repo_obj = SimpleNamespace(uri='file:///some/path')
    mock_config_module.return_value.get_repository.return_value = repo_obj
    mock_cm.return_value.is_locked.return_value = False

    result: Result = runner.invoke(app, ["repos", "credentials", "set", "localrepo"])  # type: ignore[arg-type]
    combined = combined_output(result)
    assert result.exit_code != 0
    assert "unsupported" in combined.lower()


@pytest.mark.unit
def test_repos_credentials_remove_found(repo_s3_mocks: RepoS3Mocks) -> None:
    repo_s3_mocks['cm_instance'].remove_repository_backend_credentials.return_value = True
    with patch('TimeLocker.utils.PromptService.prompt_confirm', return_value=True):
        result: Result = runner.invoke(app, ["repos", "credentials", "remove", "myrepo", "--yes"])  # type: ignore[arg-type]
    # Mocked credential manager returns True (found and removed), should succeed
    assert_success(result)
    repo_s3_mocks['cm_instance'].remove_repository_backend_credentials.assert_called_once_with('myrepo', 's3')


@pytest.mark.unit
def test_repos_credentials_remove_not_found(mock_config_module: Mock, mock_cm: Mock) -> None:
    repo_obj = SimpleNamespace(uri='s3://bucket/path')
    mock_config_module.return_value.get_repository.return_value = repo_obj
    cm_instance = Mock()
    cm_instance.is_locked.return_value = False
    cm_instance.remove_repository_backend_credentials.return_value = False
    mock_cm.return_value = cm_instance

    result: Result = runner.invoke(app, ["repos", "credentials", "remove", "myrepo", "--yes"])  # type: ignore[arg-type]
    assert_success(result)
    assert "no" in combined_output(result).lower()
    cm_instance.remove_repository_backend_credentials.assert_called_once()


@pytest.mark.unit
def test_repos_credentials_show_present(repo_s3_mocks: RepoS3Mocks) -> None:
    repo_s3_mocks['cm_instance'].has_repository_backend_credentials.return_value = True
    repo_s3_mocks['cm_instance'].get_repository_backend_credentials.return_value = {
            'access_key_id': 'AKIA', 'secret_access_key': 'SECR', 'region': 'us-east-1'
    }
    result: Result = runner.invoke(app, ["repos", "credentials", "show", "myrepo"])  # type: ignore[arg-type]
    combined = (result.stdout or "").lower()
    # Mocked credential manager returns credentials, should succeed
    assert_success(result)
    assert 'credentials' in combined and 'access key' in combined


@pytest.mark.unit
def test_repos_credentials_show_absent(mock_config_module: Mock, mock_cm: Mock) -> None:
    repo_obj = SimpleNamespace(uri='s3://bucket/path')
    mock_config_module.return_value.get_repository.return_value = repo_obj
    cm_instance = Mock()
    cm_instance.is_locked.return_value = False
    cm_instance.has_repository_backend_credentials.return_value = False
    mock_cm.return_value = cm_instance

    result: Result = runner.invoke(app, ["repos", "credentials", "show", "myrepo"])  # type: ignore[arg-type]
    assert_success(result)
    assert "no" in combined_output(result).lower()


@pytest.mark.unit
def test_repos_credentials_show_non_backend_repo(mock_config_module: Mock, mock_cm: Mock) -> None:
    repo_obj = SimpleNamespace(uri='file:///some/path')
    mock_config_module.return_value.get_repository.return_value = repo_obj
    cm_instance = Mock()
    cm_instance.is_locked.return_value = False
    mock_cm.return_value = cm_instance

    result: Result = runner.invoke(app, ["repos", "credentials", "show", "localrepo"])  # early exit
    assert_success(result)
    assert "unsupported" in combined_output(result).lower()


@pytest.mark.unit
def test_repos_credentials_set_locked_manager_then_fail_to_unlock(mock_config_module: Mock, mock_cm: Mock) -> None:
    repo_obj = SimpleNamespace(uri='s3://bucket/path')
    mock_config_module.return_value.get_repository.return_value = repo_obj

    cm_instance = Mock()
    cm_instance.is_locked.return_value = True
    cm_instance.ensure_unlocked.return_value = False
    mock_cm.return_value = cm_instance

    # Patch PromptService methods directly
    with patch('TimeLocker.utils.PromptService.prompt_text', side_effect=["AKIA1", "us-east-1"]), \
            patch('TimeLocker.utils.PromptService.prompt_password', return_value="SECRET2"), \
            patch('TimeLocker.utils.PromptService.prompt_confirm', return_value=False):
        result: Result = runner.invoke(app, ["repos", "credentials", "set", "myrepo"])  # type: ignore[arg-type]
    assert result.exit_code != 0
    cm_instance.store_repository_backend_credentials.assert_not_called()


@pytest.mark.unit
def test_repos_credentials_set_locked_manager_then_unlock(mock_config_module: Mock, mock_cm: Mock) -> None:
    repo_obj = SimpleNamespace(uri='s3://bucket/path')
    mock_config_module.return_value.get_repository.return_value = repo_obj

    cm_instance = Mock()
    cm_instance.is_locked.side_effect = [True, False]
    cm_instance.ensure_unlocked.return_value = True
    mock_cm.return_value = cm_instance

    # Patch PromptService methods directly
    with patch('TimeLocker.utils.PromptService.prompt_text', side_effect=["AKIAZ", "us-west-2"]), \
            patch('TimeLocker.utils.PromptService.prompt_password', return_value="SECRETZ"), \
            patch('TimeLocker.utils.PromptService.prompt_confirm', return_value=False):
        result: Result = runner.invoke(app, ["repos", "credentials", "set", "myrepo"])  # type: ignore[arg-type]
    # Mocked credential manager successfully unlocks and stores credentials, should succeed
    assert_success(result)
    cm_instance.store_repository_backend_credentials.assert_called_once()
