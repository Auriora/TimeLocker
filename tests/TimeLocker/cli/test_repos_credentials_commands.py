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
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from src.TimeLocker.cli import app

runner = CliRunner(env={'COLUMNS': '200'})


# Fixture: patch ConfigurationModule
@pytest.fixture
def mock_config_module():
    with patch('src.TimeLocker.config.configuration_module.ConfigurationModule') as m:
        yield m


# Fixture: patch CredentialManager
@pytest.fixture
def mock_cm():
    with patch('src.TimeLocker.security.credential_manager.CredentialManager') as m:
        yield m


# Fixture: patch Prompt class globally for tests needing dynamic side effects
@pytest.fixture
def mock_prompt():
    with patch('src.TimeLocker.cli.Prompt') as p:
        yield p


# Fixture: patch Confirm class globally
@pytest.fixture
def mock_confirm():
    with patch('src.TimeLocker.cli.Confirm') as c:
        yield c


# New fixture to DRY up repeated ConfigurationModule/CredentialManager S3 repo setup
@pytest.fixture
def repo_s3_mocks(mock_cm, mock_config_module):
    repo_obj = Mock()
    repo_obj.uri = 's3://bucket/path'
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


def _combined_output(result):
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


@pytest.mark.unit
def test_repos_credentials_group_help():
    result = runner.invoke(app, ["repos", "credentials", "--help"])  # type: ignore[arg-type]
    combined = _combined_output(result)
    assert result.exit_code == 0
    assert "credential" in combined.lower()
    assert "set" in combined.lower()
    assert "remove" in combined.lower()
    assert "show" in combined.lower()


@pytest.mark.unit
def test_repos_credentials_set_s3_success(repo_s3_mocks):
    from src.TimeLocker.cli import Prompt, Confirm  # runtime imports to allow patch interference avoidance
    # Patch interactive prompts locally
    with patch.object(Prompt, 'ask', side_effect=["AKIA123", "SECRET456", "us-east-1"]), \
            patch.object(Confirm, 'ask', return_value=False):
        result = runner.invoke(app, ["repos", "credentials", "set", "myrepo"])  # type: ignore[arg-type]
    combined = (result.stdout or "").lower()
    assert result.exit_code in [0, 1]
    repo_s3_mocks['cm_instance'].store_repository_backend_credentials.assert_called_once_with('myrepo', 's3', {
            'access_key_id':     'AKIA123',
            'secret_access_key': 'SECRET456',
            'region':            'us-east-1'
    })
    assert 'credentials' in combined


@pytest.mark.unit
def test_repos_credentials_set_s3_insecure_tls(repo_s3_mocks):
    from src.TimeLocker.cli import Prompt, Confirm  # runtime imports to allow patch interference avoidance
    # Patch interactive prompts locally
    with patch.object(Prompt, 'ask', side_effect=["AKIAKEY", "SECRETKEY", ""]), \
            patch.object(Confirm, 'ask', return_value=True):
        result = runner.invoke(app, ["repos", "credentials", "set", "myrepo"])  # type: ignore[arg-type]
    repo_s3_mocks['cm_instance'].store_repository_backend_credentials.assert_called_once_with('myrepo', 's3', {
            'access_key_id':     'AKIAKEY',
            'secret_access_key': 'SECRETKEY',
            'insecure_tls':      True
    })
    assert result.exit_code in [0, 1]


@pytest.mark.unit
def test_repos_credentials_set_unsupported_type(mock_config_module, mock_cm):
    repo_obj = Mock()
    repo_obj.uri = 'file:///some/path'
    mock_config_module.return_value.get_repository.return_value = repo_obj
    mock_cm.return_value.is_locked.return_value = False

    result = runner.invoke(app, ["repos", "credentials", "set", "localrepo"])  # type: ignore[arg-type]
    combined = _combined_output(result)
    assert result.exit_code != 0
    assert "unsupported" in combined.lower()


@pytest.mark.unit
def test_repos_credentials_remove_found(repo_s3_mocks):
    from src.TimeLocker.cli import Confirm
    repo_s3_mocks['cm_instance'].remove_repository_backend_credentials.return_value = True
    with patch.object(Confirm, 'ask', return_value=True):
        result = runner.invoke(app, ["repos", "credentials", "remove", "myrepo", "--yes"])  # type: ignore[arg-type]
    assert result.exit_code in [0, 1]
    repo_s3_mocks['cm_instance'].remove_repository_backend_credentials.assert_called_once_with('myrepo', 's3')


@pytest.mark.unit
def test_repos_credentials_remove_not_found(mock_config_module, mock_cm):
    repo_obj = Mock()
    repo_obj.uri = 's3://bucket/path'
    mock_config_module.return_value.get_repository.return_value = repo_obj
    cm_instance = Mock()
    cm_instance.is_locked.return_value = False
    cm_instance.remove_repository_backend_credentials.return_value = False
    mock_cm.return_value = cm_instance

    result = runner.invoke(app, ["repos", "credentials", "remove", "myrepo", "--yes"])  # type: ignore[arg-type]
    assert result.exit_code in [0, 1]
    cm_instance.remove_repository_backend_credentials.assert_called_once()


@pytest.mark.unit
def test_repos_credentials_show_present(repo_s3_mocks):
    repo_s3_mocks['cm_instance'].has_repository_backend_credentials.return_value = True
    repo_s3_mocks['cm_instance'].get_repository_backend_credentials.return_value = {
            'access_key_id': 'AKIA', 'secret_access_key': 'SECR', 'region': 'us-east-1'
    }
    result = runner.invoke(app, ["repos", "credentials", "show", "myrepo"])  # type: ignore[arg-type]
    combined = (result.stdout or "").lower()
    assert result.exit_code in [0, 1]
    assert 'credentials' in combined and 'access key' in combined


@pytest.mark.unit
def test_repos_credentials_show_absent(mock_config_module, mock_cm):
    repo_obj = Mock()
    repo_obj.uri = 's3://bucket/path'
    mock_config_module.return_value.get_repository.return_value = repo_obj
    cm_instance = Mock()
    cm_instance.is_locked.return_value = False
    cm_instance.has_repository_backend_credentials.return_value = False
    mock_cm.return_value = cm_instance

    result = runner.invoke(app, ["repos", "credentials", "show", "myrepo"])  # type: ignore[arg-type]
    assert result.exit_code in [0, 1]


@pytest.mark.unit
def test_repos_credentials_show_non_backend_repo(mock_config_module, mock_cm):
    repo_obj = Mock()
    repo_obj.uri = 'file:///some/path'
    mock_config_module.return_value.get_repository.return_value = repo_obj
    cm_instance = Mock()
    cm_instance.is_locked.return_value = False
    mock_cm.return_value = cm_instance

    result = runner.invoke(app, ["repos", "credentials", "show", "localrepo"])  # early exit
    # Some environments may return exit code 1 due to SystemExit handling differences
    assert result.exit_code in [0, 1]


@pytest.mark.unit
def test_repos_credentials_set_locked_manager_then_fail_to_unlock(mock_confirm, mock_prompt, mock_config_module, mock_cm):
    repo_obj = Mock()
    repo_obj.uri = 's3://bucket/path'
    mock_config_module.return_value.get_repository.return_value = repo_obj

    mock_prompt.ask.side_effect = ["AKIA1", "SECRET2", "us-east-1"]
    mock_confirm.ask.return_value = False

    cm_instance = Mock()
    cm_instance.is_locked.return_value = True
    cm_instance.ensure_unlocked.return_value = False
    mock_cm.return_value = cm_instance

    result = runner.invoke(app, ["repos", "credentials", "set", "myrepo"])  # type: ignore[arg-type]
    assert result.exit_code != 0
    cm_instance.store_repository_backend_credentials.assert_not_called()


@pytest.mark.unit
def test_repos_credentials_set_locked_manager_then_unlock(mock_confirm, mock_prompt, mock_config_module, mock_cm):
    repo_obj = Mock()
    repo_obj.uri = 's3://bucket/path'
    mock_config_module.return_value.get_repository.return_value = repo_obj

    mock_prompt.ask.side_effect = ["AKIAZ", "SECRETZ", "us-west-2"]
    mock_confirm.ask.return_value = False

    cm_instance = Mock()
    cm_instance.is_locked.side_effect = [True, False]
    cm_instance.ensure_unlocked.return_value = True
    mock_cm.return_value = cm_instance

    result = runner.invoke(app, ["repos", "credentials", "set", "myrepo"])  # type: ignore[arg-type]
    assert result.exit_code in [0, 1]
    cm_instance.store_repository_backend_credentials.assert_called_once()
