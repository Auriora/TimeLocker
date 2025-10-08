"""
Integration tests for backend credential storage via the 'repos add' CLI command.

NOTE: The store_backend_credentials helper function has been refactored into a separate
module (cli_helpers.py) and is now tested directly in test_cli_helpers.py. These tests
serve as integration tests to verify the full CLI command flow including user prompts,
CLI argument parsing, and the interaction between the CLI and the helper function.

For direct unit tests of the store_backend_credentials helper logic, see:
    tests/TimeLocker/cli/test_cli_helpers.py

These integration tests exercise the complete 'repos add' command flow by invoking
the CLI with appropriate arguments and mocking dependencies to control CredentialManager
lock/unlock behavior and verify side effects.

Scenarios covered:
1. Credential manager locked and cannot unlock (should warn and not store credentials).
2. Credential manager locked, unlock succeeds (credentials stored, update_repository called).
3. Credential manager already unlocked (credentials stored without unlock attempt).
4. Credentials include region and insecure TLS flag when user supplies them.
5. Credentials omit optional fields when user leaves them blank / disabled.
6. Exception handling during credential storage.
7. User declining to store credentials.
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from src.TimeLocker.cli import app

runner = CliRunner(env={'COLUMNS': '200'})


def _combined_output(result):
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


# NOTE: We patch CredentialManager and ConfigurationModule at their definition modules
# because repos_add imports them dynamically inside the function body.

@pytest.mark.unit
@patch('src.TimeLocker.security.credential_manager.CredentialManager')
@patch('src.TimeLocker.config.configuration_module.ConfigurationModule')
@patch('src.TimeLocker.cli.BackupManager')
@patch('src.TimeLocker.cli.Confirm.ask')
@patch('src.TimeLocker.cli.Prompt.ask')
def test_store_backend_credentials_locked_cannot_unlock(mock_prompt, mock_confirm, mock_backup_mgr, mock_config_mod, mock_cred_mgr_cls):
    """Locked credential manager cannot unlock -> warning, no storage, no update_repository call."""
    mock_confirm.side_effect = [True, False]  # store AWS creds? then insecure TLS? -> False
    mock_prompt.side_effect = ["AKIA", "SECRET", ""]  # access key, secret, region blank

    config_instance = MagicMock()
    mock_config_mod.return_value = config_instance

    cred_instance = MagicMock()
    cred_instance.is_locked.return_value = True
    cred_instance.ensure_unlocked.return_value = False
    mock_cred_mgr_cls.return_value = cred_instance

    repo = MagicMock()
    repo.store_password.return_value = True
    mock_backup_mgr.return_value.from_uri.return_value = repo

    result = runner.invoke(app, [
            'repos', 'add', 'myrepo', 's3://dummyhost/bucket', '--password', 'repopass'
    ])
    combined = _combined_output(result)

    # Command should complete successfully (exit code 0) despite warning
    assert result.exit_code == 0
    assert 'Could not unlock credential manager' in combined
    cred_instance.store_repository_backend_credentials.assert_not_called()
    config_instance.update_repository.assert_not_called()


@pytest.mark.unit
@patch('src.TimeLocker.security.credential_manager.CredentialManager')
@patch('src.TimeLocker.config.configuration_module.ConfigurationModule')
@patch('src.TimeLocker.cli.BackupManager')
@patch('src.TimeLocker.cli.Confirm.ask')
@patch('src.TimeLocker.cli.Prompt.ask')
def test_store_backend_credentials_locked_unlocks_successfully(mock_prompt, mock_confirm, mock_backup_mgr, mock_config_mod, mock_cred_mgr_cls):
    """Locked credential manager unlocks -> credentials stored and repository updated."""
    mock_confirm.side_effect = [True, False]
    mock_prompt.side_effect = ["AKIA2", "SECRET2", ""]

    config_instance = MagicMock()
    mock_config_mod.return_value = config_instance

    cred_instance = MagicMock()
    cred_instance.is_locked.return_value = True
    cred_instance.ensure_unlocked.return_value = True
    mock_cred_mgr_cls.return_value = cred_instance

    repo = MagicMock()
    repo.store_password.return_value = True
    mock_backup_mgr.return_value.from_uri.return_value = repo

    result = runner.invoke(app, [
            'repos', 'add', 'myrepo2', 's3://dummyhost/bucket2', '--password', 'repopass2'
    ])
    combined = _combined_output(result)

    assert result.exit_code == 0
    cred_instance.ensure_unlocked.assert_called_once()
    cred_instance.store_repository_backend_credentials.assert_called_once()
    _, _, stored_credentials = cred_instance.store_repository_backend_credentials.call_args[0]
    assert stored_credentials == {
            'access_key_id':     'AKIA2',
            'secret_access_key': 'SECRET2'
    }
    # Verify has_backend_credentials flag was set in some update_repository call
    assert any(
            isinstance(call.args[1], dict) and call.args[1].get('has_backend_credentials')
            for call in config_instance.update_repository.call_args_list
    )
    assert ('AWS Credentials: Stored securely' in combined) or ('AWS credentials stored' in combined)


@pytest.mark.unit
@patch('src.TimeLocker.security.credential_manager.CredentialManager')
@patch('src.TimeLocker.config.configuration_module.ConfigurationModule')
@patch('src.TimeLocker.cli.BackupManager')
@patch('src.TimeLocker.cli.Confirm.ask')
@patch('src.TimeLocker.cli.Prompt.ask')
def test_store_backend_credentials_already_unlocked(mock_prompt, mock_confirm, mock_backup_mgr, mock_config_mod, mock_cred_mgr_cls):
    """Credential manager already unlocked -> store credentials without unlock attempt."""
    mock_confirm.side_effect = [True, False]
    mock_prompt.side_effect = ["AKIA3", "SECRET3", "us-west-1"]

    config_instance = MagicMock()
    mock_config_mod.return_value = config_instance

    cred_instance = MagicMock()
    cred_instance.is_locked.return_value = False
    mock_cred_mgr_cls.return_value = cred_instance

    repo = MagicMock()
    repo.store_password.return_value = True
    mock_backup_mgr.return_value.from_uri.return_value = repo

    result = runner.invoke(app, [
            'repos', 'add', 'myrepo3', 's3://dummyhost/bucket3', '--password', 'repopass3'
    ])

    assert result.exit_code == 0
    cred_instance.ensure_unlocked.assert_not_called()
    cred_instance.store_repository_backend_credentials.assert_called_once()
    stored_credentials = cred_instance.store_repository_backend_credentials.call_args[0][2]
    assert stored_credentials == {
            'access_key_id':     'AKIA3',
            'secret_access_key': 'SECRET3',
            'region':            'us-west-1'
    }


@pytest.mark.unit
@patch('src.TimeLocker.security.credential_manager.CredentialManager')
@patch('src.TimeLocker.config.configuration_module.ConfigurationModule')
@patch('src.TimeLocker.cli.BackupManager')
@patch('src.TimeLocker.cli.Confirm.ask')
@patch('src.TimeLocker.cli.Prompt.ask')
def test_store_backend_credentials_with_insecure_tls_and_region(mock_prompt, mock_confirm, mock_backup_mgr, mock_config_mod, mock_cred_mgr_cls):
    """User supplies region and chooses insecure TLS -> both fields appear in stored credentials."""
    mock_confirm.side_effect = [True, True]
    mock_prompt.side_effect = ["AKIA4", "SECRET4", "eu-central-1"]

    config_instance = MagicMock()
    mock_config_mod.return_value = config_instance

    cred_instance = MagicMock()
    cred_instance.is_locked.return_value = False
    mock_cred_mgr_cls.return_value = cred_instance

    repo = MagicMock()
    repo.store_password.return_value = True
    mock_backup_mgr.return_value.from_uri.return_value = repo

    result = runner.invoke(app, [
            'repos', 'add', 'myrepo4', 's3://dummyhost/bucket4', '--password', 'repopass4'
    ])

    assert result.exit_code == 0
    stored_credentials = cred_instance.store_repository_backend_credentials.call_args[0][2]
    assert stored_credentials == {
            'access_key_id':     'AKIA4',
            'secret_access_key': 'SECRET4',
            'region':            'eu-central-1',
            'insecure_tls':      True
    }


@pytest.mark.unit
@patch('src.TimeLocker.security.credential_manager.CredentialManager')
@patch('src.TimeLocker.config.configuration_module.ConfigurationModule')
@patch('src.TimeLocker.cli.BackupManager')
@patch('src.TimeLocker.cli.Confirm.ask')
@patch('src.TimeLocker.cli.Prompt.ask')
def test_store_backend_credentials_without_optional_fields(mock_prompt, mock_confirm, mock_backup_mgr, mock_config_mod, mock_cred_mgr_cls):
    """User leaves region blank and does not enable insecure TLS -> optional fields omitted."""
    mock_confirm.side_effect = [True, False]
    mock_prompt.side_effect = ["AKIA5", "SECRET5", ""]

    config_instance = MagicMock()
    mock_config_mod.return_value = config_instance

    cred_instance = MagicMock()
    cred_instance.is_locked.return_value = False
    mock_cred_mgr_cls.return_value = cred_instance

    repo = MagicMock()
    repo.store_password.return_value = True
    mock_backup_mgr.return_value.from_uri.return_value = repo

    result = runner.invoke(app, [
            'repos', 'add', 'myrepo5', 's3://dummyhost/bucket5', '--password', 'repopass5'
    ])

    assert result.exit_code == 0
    stored_credentials = cred_instance.store_repository_backend_credentials.call_args[0][2]
    assert stored_credentials == {
            'access_key_id':     'AKIA5',
            'secret_access_key': 'SECRET5'
    }


@pytest.mark.unit
@patch('src.TimeLocker.security.credential_manager.CredentialManager')
@patch('src.TimeLocker.config.configuration_module.ConfigurationModule')
@patch('src.TimeLocker.cli.BackupManager')
@patch('src.TimeLocker.cli.Confirm.ask')
@patch('src.TimeLocker.cli.Prompt.ask')
def test_store_backend_credentials_exception_propagates_and_handled(mock_prompt, mock_confirm, mock_backup_mgr, mock_config_mod, mock_cred_mgr_cls):
    """If storing backend credentials raises an exception, command should exit with error panel and not set flag."""
    # First Confirm -> store AWS credentials (True); second Confirm -> insecure TLS (False)
    mock_confirm.side_effect = [True, False]
    mock_prompt.side_effect = ["AKIA_EX", "SECRET_EX", ""]

    config_instance = MagicMock()
    mock_config_mod.return_value = config_instance

    # Credential manager instance raising error on store
    cred_instance = MagicMock()
    cred_instance.is_locked.return_value = False

    def _raise(*a, **kw):
        raise RuntimeError("Boom")

    cred_instance.store_repository_backend_credentials.side_effect = _raise
    mock_cred_mgr_cls.return_value = cred_instance

    repo = MagicMock()
    repo.store_password.return_value = True
    mock_backup_mgr.return_value.from_uri.return_value = repo

    result = runner.invoke(app, [
            'repos', 'add', 'failrepo', 's3://dummyhost/failbucket', '--password', 'repopass'
    ])
    combined = _combined_output(result)

    assert result.exit_code == 1  # Should exit with error
    assert 'Configuration Error' in combined
    assert 'Failed to add repository: Boom' in combined
    # Ensure has_backend_credentials never set
    assert not any(
            isinstance(call.args[1], dict) and call.args[1].get('has_backend_credentials')
            for call in config_instance.update_repository.call_args_list
    )


@pytest.mark.unit
@patch('src.TimeLocker.security.credential_manager.CredentialManager')
@patch('src.TimeLocker.config.configuration_module.ConfigurationModule')
@patch('src.TimeLocker.cli.BackupManager')
@patch('src.TimeLocker.cli.Confirm.ask')
@patch('src.TimeLocker.cli.Prompt.ask')
def test_store_backend_credentials_user_declines_first_confirm(mock_prompt, mock_confirm, mock_backup_mgr, mock_config_mod, mock_cred_mgr_cls):
    """When user declines to store credentials, no credential prompts or storage should occur."""
    # User declines first confirm; no second confirm for insecure TLS should be asked
    mock_confirm.side_effect = [False]
    # Prompt.ask should never be called for credentials if user declines

    config_instance = MagicMock()
    mock_config_mod.return_value = config_instance

    cred_instance = MagicMock()
    cred_instance.is_locked.return_value = False
    mock_cred_mgr_cls.return_value = cred_instance

    repo = MagicMock()
    repo.store_password.return_value = True
    mock_backup_mgr.return_value.from_uri.return_value = repo

    result = runner.invoke(app, [
            'repos', 'add', 'declinerepo', 's3://dummyhost/declbucket', '--password', 'repopass'
    ])
    combined = _combined_output(result)

    assert result.exit_code == 0
    mock_prompt.assert_not_called()
    cred_instance.store_repository_backend_credentials.assert_not_called()
    # Ensure has_backend_credentials never set
    assert not any(
            isinstance(call.args[1], dict) and call.args[1].get('has_backend_credentials')
            for call in config_instance.update_repository.call_args_list
    )
