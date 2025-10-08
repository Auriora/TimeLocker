"""
Direct unit tests for CLI helper functions in cli_helpers module.

This module tests the extracted helper functions directly without invoking
the full CLI command flow. This provides faster, more focused tests with
better isolation and easier debugging.

Tests for store_backend_credentials helper:
1. Credential manager locked and cannot unlock (should warn and return False).
2. Credential manager locked, unlock succeeds (credentials stored, config updated, returns True).
3. Credential manager already unlocked (credentials stored without unlock attempt).
4. Credentials with all optional fields (region, insecure_tls).
5. Credentials with only required fields (optional fields omitted).
6. Exception during storage propagates to caller.
7. Verify config update sets has_backend_credentials flag.
8. Verify logger and console output.
"""

import pytest
import logging
from unittest.mock import MagicMock, Mock, call
from io import StringIO

from src.TimeLocker.cli_helpers import store_backend_credentials


@pytest.mark.unit
def test_store_backend_credentials_locked_cannot_unlock():
    """Locked credential manager cannot unlock -> warning printed, returns False, no storage."""
    # Setup mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = True
    cred_mgr.ensure_unlocked.return_value = False

    config_manager = MagicMock()
    repository_config = {}
    console = MagicMock()
    logger = MagicMock()

    credentials = {
            'access_key_id':     'AKIA123',
            'secret_access_key': 'SECRET123'
    }

    # Call helper
    result = store_backend_credentials(
            repository_name='test-repo',
            backend_type='s3',
            backend_name='AWS',
            credentials_dict=credentials,
            cred_mgr=cred_mgr,
            config_manager=config_manager,
            repository_config=repository_config,
            console=console,
            logger=logger,
            allow_prompt=True
    )

    # Assertions
    assert result is False
    cred_mgr.is_locked.assert_called_once()
    cred_mgr.ensure_unlocked.assert_called_once_with(allow_prompt=True)
    cred_mgr.store_repository_backend_credentials.assert_not_called()
    config_manager.update_repository.assert_not_called()
    assert 'has_backend_credentials' not in repository_config

    # Verify warning was printed
    console.print.assert_called_once()
    warning_msg = console.print.call_args[0][0]
    assert 'Could not unlock credential manager' in warning_msg
    assert 'AWS credentials not stored' in warning_msg


@pytest.mark.unit
def test_store_backend_credentials_locked_unlocks_successfully():
    """Locked credential manager unlocks -> credentials stored, config updated, returns True."""
    # Setup mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = True
    cred_mgr.ensure_unlocked.return_value = True

    config_manager = MagicMock()
    repository_config = {'uri': 's3://bucket/path'}
    console = MagicMock()
    logger = MagicMock()

    credentials = {
            'access_key_id':     'AKIA456',
            'secret_access_key': 'SECRET456'
    }

    # Call helper
    result = store_backend_credentials(
            repository_name='test-repo2',
            backend_type='s3',
            backend_name='AWS',
            credentials_dict=credentials,
            cred_mgr=cred_mgr,
            config_manager=config_manager,
            repository_config=repository_config,
            console=console,
            logger=logger,
            allow_prompt=True
    )

    # Assertions
    assert result is True
    cred_mgr.is_locked.assert_called_once()
    cred_mgr.ensure_unlocked.assert_called_once_with(allow_prompt=True)
    cred_mgr.store_repository_backend_credentials.assert_called_once_with(
            'test-repo2', 's3', credentials
    )
    config_manager.update_repository.assert_called_once_with(
            'test-repo2', repository_config
    )
    assert repository_config['has_backend_credentials'] is True
    logger.info.assert_called_once()
    assert 'AWS credentials stored' in logger.info.call_args[0][0]


@pytest.mark.unit
def test_store_backend_credentials_already_unlocked():
    """Credential manager already unlocked -> store credentials without unlock attempt."""
    # Setup mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False

    config_manager = MagicMock()
    repository_config = {'uri': 's3://bucket/path'}
    console = MagicMock()
    logger = MagicMock()

    credentials = {
            'access_key_id':     'AKIA789',
            'secret_access_key': 'SECRET789',
            'region':            'us-west-1'
    }

    # Call helper
    result = store_backend_credentials(
            repository_name='test-repo3',
            backend_type='s3',
            backend_name='AWS',
            credentials_dict=credentials,
            cred_mgr=cred_mgr,
            config_manager=config_manager,
            repository_config=repository_config,
            console=console,
            logger=logger,
            allow_prompt=True
    )

    # Assertions
    assert result is True
    cred_mgr.is_locked.assert_called_once()
    cred_mgr.ensure_unlocked.assert_not_called()
    cred_mgr.store_repository_backend_credentials.assert_called_once_with(
            'test-repo3', 's3', credentials
    )
    assert repository_config['has_backend_credentials'] is True


@pytest.mark.unit
def test_store_backend_credentials_with_all_optional_fields():
    """Credentials include region and insecure_tls -> all fields stored."""
    # Setup mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False

    config_manager = MagicMock()
    repository_config = {}

    credentials = {
            'access_key_id':     'AKIAOPT',
            'secret_access_key': 'SECRETOPT',
            'region':            'eu-central-1',
            'insecure_tls':      True
    }

    # Call helper (minimal args, using defaults for console/logger)
    result = store_backend_credentials(
            repository_name='opt-repo',
            backend_type='s3',
            backend_name='AWS',
            credentials_dict=credentials,
            cred_mgr=cred_mgr,
            config_manager=config_manager,
            repository_config=repository_config
    )

    # Assertions
    assert result is True
    stored_creds = cred_mgr.store_repository_backend_credentials.call_args[0][2]
    assert stored_creds == credentials
    assert stored_creds['region'] == 'eu-central-1'
    assert stored_creds['insecure_tls'] is True


@pytest.mark.unit
def test_store_backend_credentials_without_optional_fields():
    """Credentials with only required fields -> optional fields not present."""
    # Setup mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False

    config_manager = MagicMock()
    repository_config = {}

    credentials = {
            'access_key_id':     'AKIAMIN',
            'secret_access_key': 'SECRETMIN'
    }

    # Call helper
    result = store_backend_credentials(
            repository_name='min-repo',
            backend_type='s3',
            backend_name='AWS',
            credentials_dict=credentials,
            cred_mgr=cred_mgr,
            config_manager=config_manager,
            repository_config=repository_config
    )

    # Assertions
    assert result is True
    stored_creds = cred_mgr.store_repository_backend_credentials.call_args[0][2]
    assert stored_creds == credentials
    assert 'region' not in stored_creds
    assert 'insecure_tls' not in stored_creds


@pytest.mark.unit
def test_store_backend_credentials_exception_propagates():
    """Exception during storage propagates to caller."""
    # Setup mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False
    cred_mgr.store_repository_backend_credentials.side_effect = RuntimeError("Storage failed")

    config_manager = MagicMock()
    repository_config = {}

    credentials = {
            'access_key_id':     'AKIAERR',
            'secret_access_key': 'SECRETERR'
    }

    # Call helper and expect exception
    with pytest.raises(RuntimeError, match="Storage failed"):
        store_backend_credentials(
                repository_name='err-repo',
                backend_type='s3',
                backend_name='AWS',
                credentials_dict=credentials,
                cred_mgr=cred_mgr,
                config_manager=config_manager,
                repository_config=repository_config
        )

    # Config should not be updated when exception occurs
    config_manager.update_repository.assert_not_called()
    assert 'has_backend_credentials' not in repository_config


@pytest.mark.unit
def test_store_backend_credentials_b2_backend():
    """Test with B2 backend type and credentials."""
    # Setup mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False

    config_manager = MagicMock()
    repository_config = {}
    logger = MagicMock()

    credentials = {
            'account_id':  'b2_account_123',
            'account_key': 'b2_key_secret'
    }

    # Call helper
    result = store_backend_credentials(
            repository_name='b2-repo',
            backend_type='b2',
            backend_name='B2',
            credentials_dict=credentials,
            cred_mgr=cred_mgr,
            config_manager=config_manager,
            repository_config=repository_config,
            logger=logger
    )

    # Assertions
    assert result is True
    cred_mgr.store_repository_backend_credentials.assert_called_once_with(
            'b2-repo', 'b2', credentials
    )
    assert repository_config['has_backend_credentials'] is True
    # Verify B2 appears in log message
    assert 'B2 credentials stored' in logger.info.call_args[0][0]


@pytest.mark.unit
def test_store_backend_credentials_allow_prompt_false():
    """Test with allow_prompt=False passed to ensure_unlocked."""
    # Setup mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = True
    cred_mgr.ensure_unlocked.return_value = True

    config_manager = MagicMock()
    repository_config = {}

    credentials = {'access_key_id': 'AKIA', 'secret_access_key': 'SECRET'}

    # Call helper with allow_prompt=False
    result = store_backend_credentials(
            repository_name='no-prompt-repo',
            backend_type='s3',
            backend_name='AWS',
            credentials_dict=credentials,
            cred_mgr=cred_mgr,
            config_manager=config_manager,
            repository_config=repository_config,
            allow_prompt=False
    )

    # Verify allow_prompt was passed correctly
    cred_mgr.ensure_unlocked.assert_called_once_with(allow_prompt=False)
    assert result is True
