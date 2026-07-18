"""
Unit tests for backend credential storage helper function.

These tests verify the store_backend_credentials helper function extracted from
the repos add command. They test credential manager locking/unlocking behavior,
credential storage, and configuration updates.
"""

import pytest
from unittest.mock import MagicMock
import io

from TimeLocker.cli_helpers import store_backend_credentials
from rich.console import Console


@pytest.mark.unit
def test_store_backend_credentials_locked_cannot_unlock():
    """Locked credential manager cannot unlock -> warning, no storage, no update_repository call."""
    # Create mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = True
    cred_mgr.ensure_unlocked.return_value = False  # Cannot unlock
    
    config_manager = MagicMock()
    repository_config: dict[str, object] = {}
    
    # Capture console output
    string_io = io.StringIO()
    console = Console(file=string_io, force_terminal=True)
    
    # Call helper function
    result = store_backend_credentials(
        repository_name='myrepo',
        backend_type='s3',
        backend_name='AWS',
        credentials_dict={'access_key': 'AKIA', 'secret_key': 'SECRET'},
        cred_mgr=cred_mgr,
        config_manager=config_manager,
        repository_config=repository_config,
        console=console,
        allow_prompt=False
    )
    
    # Should return False (failed to unlock)
    assert result is False
    
    # Should not have called store or update
    cred_mgr.store_repository_backend_credentials.assert_not_called()
    config_manager.update_repository.assert_not_called()
    
    # Should have warning in output
    output = string_io.getvalue()
    assert 'Could not unlock credential manager' in output


@pytest.mark.unit
def test_store_backend_credentials_locked_unlocks_successfully():
    """Locked credential manager unlocks -> credentials stored and repository updated."""
    # Create mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = True
    cred_mgr.ensure_unlocked.return_value = True  # Successfully unlocks
    
    config_manager = MagicMock()
    repository_config: dict[str, object] = {}
    
    # Capture console output
    string_io = io.StringIO()
    console = Console(file=string_io, force_terminal=True)
    
    # Call helper function
    result = store_backend_credentials(
        repository_name='myrepo',
        backend_type='s3',
        backend_name='AWS',
        credentials_dict={'access_key': 'AKIA2', 'secret_key': 'SECRET2'},
        cred_mgr=cred_mgr,
        config_manager=config_manager,
        repository_config=repository_config,
        console=console,
        allow_prompt=True
    )
    
    # Should return True (success)
    assert result is True
    
    # Should have called ensure_unlocked
    cred_mgr.ensure_unlocked.assert_called_once_with(allow_prompt=True)
    
    # Should have stored credentials
    cred_mgr.store_repository_backend_credentials.assert_called_once_with(
        'myrepo', 's3', {'access_key': 'AKIA2', 'secret_key': 'SECRET2'}
    )
    
    # Should have updated repository config
    assert repository_config['has_backend_credentials'] is True
    config_manager.update_repository.assert_called_once_with('myrepo', repository_config)


@pytest.mark.unit
def test_store_backend_credentials_already_unlocked():
    """Credential manager already unlocked -> store credentials without unlock attempt."""
    # Create mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False  # Already unlocked
    
    config_manager = MagicMock()
    repository_config: dict[str, object] = {}
    
    # Call helper function
    result = store_backend_credentials(
        repository_name='myrepo',
        backend_type='s3',
        backend_name='AWS',
        credentials_dict={'access_key': 'AKIA3', 'secret_key': 'SECRET3', 'region': 'us-west-1'},
        cred_mgr=cred_mgr,
        config_manager=config_manager,
        repository_config=repository_config,
        allow_prompt=False
    )
    
    # Should return True (success)
    assert result is True
    
    # Should NOT have called ensure_unlocked (already unlocked)
    cred_mgr.ensure_unlocked.assert_not_called()
    
    # Should have stored credentials
    cred_mgr.store_repository_backend_credentials.assert_called_once()
    
    # Should have updated repository config
    assert repository_config['has_backend_credentials'] is True
    config_manager.update_repository.assert_called_once()


@pytest.mark.unit
def test_store_backend_credentials_with_insecure_tls_and_region():
    """User supplies region and insecure TLS flag -> both fields appear in stored credentials."""
    # Create mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False
    
    config_manager = MagicMock()
    repository_config: dict[str, object] = {}
    
    credentials_dict: dict[str, object] = {
        'access_key': 'AKIA4',
        'secret_key': 'SECRET4',
        'region': 'eu-central-1',
        'insecure_tls': True  # Boolean value
    }
    
    # Call helper function
    result = store_backend_credentials(
        repository_name='myrepo',
        backend_type='s3',
        backend_name='AWS',
        credentials_dict=credentials_dict,
        cred_mgr=cred_mgr,
        config_manager=config_manager,
        repository_config=repository_config
    )
    
    # Should return True (success)
    assert result is True
    
    # Should have stored credentials with all fields
    cred_mgr.store_repository_backend_credentials.assert_called_once_with(
        'myrepo', 's3', credentials_dict
    )
    
    # Verify the credentials dict passed includes all fields
    call_args = cred_mgr.store_repository_backend_credentials.call_args
    stored_creds = call_args[0][2]
    assert stored_creds['access_key'] == 'AKIA4'
    assert stored_creds['secret_key'] == 'SECRET4'
    assert stored_creds['region'] == 'eu-central-1'
    assert stored_creds['insecure_tls'] is True


@pytest.mark.unit
def test_store_backend_credentials_without_optional_fields():
    """User leaves region blank and does not enable insecure TLS -> optional fields omitted."""
    # Create mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False
    
    config_manager = MagicMock()
    repository_config: dict[str, object] = {}
    
    credentials_dict: dict[str, object] = {
        'access_key': 'AKIA5',
        'secret_key': 'SECRET5'
        # No region, no insecure_tls
    }
    
    # Call helper function
    result = store_backend_credentials(
        repository_name='myrepo',
        backend_type='s3',
        backend_name='AWS',
        credentials_dict=credentials_dict,
        cred_mgr=cred_mgr,
        config_manager=config_manager,
        repository_config=repository_config
    )
    
    # Should return True (success)
    assert result is True
    
    # Should have stored credentials without optional fields
    call_args = cred_mgr.store_repository_backend_credentials.call_args
    stored_creds = call_args[0][2]
    assert stored_creds['access_key'] == 'AKIA5'
    assert stored_creds['secret_key'] == 'SECRET5'
    assert 'region' not in stored_creds
    assert 'insecure_tls' not in stored_creds


@pytest.mark.unit
def test_store_backend_credentials_exception_propagates():
    """If storing backend credentials raises an exception, it should propagate."""
    # Create mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False
    cred_mgr.store_repository_backend_credentials.side_effect = Exception("Storage failed")
    
    config_manager = MagicMock()
    repository_config: dict[str, object] = {}
    
    # Call helper function - should raise exception
    with pytest.raises(Exception, match="Storage failed"):
        store_backend_credentials(
            repository_name='myrepo',
            backend_type='s3',
            backend_name='AWS',
            credentials_dict={'access_key': 'AKIA6', 'secret_key': 'SECRET6'},
            cred_mgr=cred_mgr,
            config_manager=config_manager,
            repository_config=repository_config
        )
    
    # Should NOT have updated repository config (exception occurred before that)
    config_manager.update_repository.assert_not_called()
    assert 'has_backend_credentials' not in repository_config


@pytest.mark.unit
def test_store_backend_credentials_b2_backend():
    """Test storing B2 backend credentials."""
    # Create mocks
    cred_mgr = MagicMock()
    cred_mgr.is_locked.return_value = False
    
    config_manager = MagicMock()
    repository_config: dict[str, object] = {}
    
    credentials_dict: dict[str, object] = {
        'account_id': 'B2_ACCOUNT_ID',
        'application_key': 'B2_APP_KEY'
    }
    
    # Call helper function
    result = store_backend_credentials(
        repository_name='b2repo',
        backend_type='b2',
        backend_name='Backblaze B2',
        credentials_dict=credentials_dict,
        cred_mgr=cred_mgr,
        config_manager=config_manager,
        repository_config=repository_config
    )
    
    # Should return True (success)
    assert result is True
    
    # Should have stored B2 credentials
    cred_mgr.store_repository_backend_credentials.assert_called_once_with(
        'b2repo', 'b2', credentials_dict
    )
    
    # Should have updated repository config
    assert repository_config['has_backend_credentials'] is True
