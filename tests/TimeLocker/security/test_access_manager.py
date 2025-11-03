"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import os
import time
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from TimeLocker.security.access_manager import (
    AccessManager, AccessManagerError, AuthenticationError, AuthorizationError,
    UserCredentials, AuthResult, Session, SecurityContext, Operation
)


class TestAccessManager:
    """Test cases for AccessManager"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def access_manager(self, temp_config_dir):
        """Create AccessManager instance for testing"""
        return AccessManager(config_dir=temp_config_dir, session_timeout_minutes=1)

    @pytest.fixture
    def current_user(self):
        """Get current system user"""
        return os.getenv('USER', os.getenv('USERNAME', 'testuser'))

    def test_initialization(self, temp_config_dir):
        """Test AccessManager initialization"""
        manager = AccessManager(config_dir=temp_config_dir)
        
        assert manager.config_dir == temp_config_dir
        assert manager.session_timeout_minutes == AccessManager.DEFAULT_SESSION_TIMEOUT
        assert manager.sessions_file.exists() is False  # No sessions initially
        assert manager.access_log_file.exists()

    def test_authenticate_user_success(self, access_manager, current_user):
        """Test successful user authentication"""
        credentials = UserCredentials(user_id=current_user)
        result = access_manager.authenticate_user(credentials)
        
        assert result.success is True
        assert result.user_id == current_user
        assert result.session_id is not None
        assert result.error_message is None

    def test_authenticate_user_invalid_user(self, access_manager):
        """Test authentication with invalid user"""
        credentials = UserCredentials(user_id="invalid_user")
        result = access_manager.authenticate_user(credentials)
        
        assert result.success is False
        assert result.user_id is None
        assert result.session_id is None
        assert "Invalid user" in result.error_message

    def test_authenticate_user_empty_user_id(self, access_manager):
        """Test authentication with empty user ID"""
        credentials = UserCredentials(user_id="")
        result = access_manager.authenticate_user(credentials)
        
        assert result.success is False
        assert "User ID cannot be empty" in result.error_message

    def test_session_creation(self, access_manager, current_user):
        """Test session creation"""
        session = access_manager.create_session(current_user)
        
        assert session.user_id == current_user
        assert session.session_id is not None
        assert session.is_active is True
        assert session.is_valid() is True
        assert session.created_at <= datetime.now()
        assert session.expires_at > datetime.now()

    def test_session_validation(self, access_manager, current_user):
        """Test session validation"""
        session = access_manager.create_session(current_user)
        
        # Valid session should pass validation
        assert access_manager.validate_session(session.session_id) is True
        
        # Invalid session ID should fail
        assert access_manager.validate_session("invalid_session_id") is False

    def test_session_expiry(self, access_manager, current_user):
        """Test session expiry handling"""
        # Create session with very short timeout
        manager = AccessManager(config_dir=access_manager.config_dir, session_timeout_minutes=0.01)
        session = manager.create_session(current_user)
        
        # Session should be valid initially
        assert manager.validate_session(session.session_id) is True
        
        # Wait for session to expire
        time.sleep(2)
        
        # Session should now be invalid
        assert manager.validate_session(session.session_id) is False

    def test_session_extension(self, access_manager, current_user):
        """Test session extension"""
        session = access_manager.create_session(current_user)
        original_expiry = session.expires_at
        
        # Extend session
        assert access_manager.extend_session(session.session_id) is True
        
        # Expiry time should be updated
        updated_session = access_manager.get_session_info(session.session_id)
        assert updated_session.expires_at > original_expiry

    def test_session_termination(self, access_manager, current_user):
        """Test session termination"""
        session = access_manager.create_session(current_user)
        
        # Session should be valid
        assert access_manager.validate_session(session.session_id) is True
        
        # Terminate session
        access_manager.terminate_session(session.session_id)
        
        # Session should no longer be valid
        assert access_manager.validate_session(session.session_id) is False

    def test_failed_attempts_lockout(self, access_manager):
        """Test user lockout after failed attempts"""
        invalid_user = "invalid_user"
        credentials = UserCredentials(user_id=invalid_user)
        
        # Make multiple failed attempts
        for _ in range(AccessManager.MAX_FAILED_ATTEMPTS):
            result = access_manager.authenticate_user(credentials)
            assert result.success is False
        
        # Next attempt should be locked out
        result = access_manager.authenticate_user(credentials)
        assert result.success is False
        assert "locked out" in result.error_message

    def test_file_permissions_check(self, access_manager, temp_config_dir):
        """Test file permission checking"""
        # Create test file
        test_file = temp_config_dir / "test_file.txt"
        test_file.write_text("test content")
        
        # Check read permission
        assert access_manager.check_file_permissions(str(test_file), "read") is True
        
        # Check write permission
        assert access_manager.check_file_permissions(str(test_file), "write") is True
        
        # Check non-existent file
        assert access_manager.check_file_permissions(str(temp_config_dir / "nonexistent"), "read") is False

    def test_operation_authorization(self, access_manager, current_user):
        """Test operation authorization"""
        # Create session
        session = access_manager.create_session(current_user)
        
        # Create operation and context
        operation = Operation("backup", "repository")
        context = SecurityContext(
            user_id=current_user,
            session_id=session.session_id,
            operation="backup"
        )
        
        # Authorization should succeed
        assert access_manager.authorize_operation(operation, context) is True
        
        # Authorization with invalid session should fail
        invalid_context = SecurityContext(
            user_id=current_user,
            session_id="invalid_session",
            operation="backup"
        )
        assert access_manager.authorize_operation(operation, invalid_context) is False

    def test_get_active_sessions(self, access_manager, current_user):
        """Test getting active sessions"""
        # Initially no active sessions
        assert len(access_manager.get_active_sessions()) == 0
        
        # Create sessions
        session1 = access_manager.create_session(current_user)
        session2 = access_manager.create_session(current_user)
        
        # Should have 2 active sessions
        active_sessions = access_manager.get_active_sessions()
        assert len(active_sessions) == 2
        
        # Filter by user
        user_sessions = access_manager.get_active_sessions(current_user)
        assert len(user_sessions) == 2

    def test_cleanup_expired_sessions(self, access_manager, current_user):
        """Test cleanup of expired sessions"""
        # Create manager with very short timeout
        manager = AccessManager(config_dir=access_manager.config_dir, session_timeout_minutes=0.01)
        
        # Create sessions
        session1 = manager.create_session(current_user)
        session2 = manager.create_session(current_user)
        
        # Wait for sessions to expire
        time.sleep(2)
        
        # Cleanup expired sessions
        cleaned_count = manager.cleanup_expired_sessions()
        assert cleaned_count == 2
        
        # No active sessions should remain
        assert len(manager.get_active_sessions()) == 0

    def test_security_status(self, access_manager, current_user):
        """Test security status reporting"""
        # Get initial status
        status = access_manager.get_security_status()
        assert status['active_sessions'] == 0
        assert status['total_sessions'] == 0
        assert status['locked_users'] == 0
        
        # Create session
        session = access_manager.create_session(current_user)
        
        # Check updated status
        status = access_manager.get_security_status()
        assert status['active_sessions'] == 1
        assert status['total_sessions'] == 1

    def test_session_persistence(self, temp_config_dir, current_user):
        """Test session persistence across manager instances"""
        # Create manager and session
        manager1 = AccessManager(config_dir=temp_config_dir, session_timeout_minutes=60)
        session = manager1.create_session(current_user)
        
        # Create new manager instance
        manager2 = AccessManager(config_dir=temp_config_dir, session_timeout_minutes=60)
        
        # Session should still be valid
        assert manager2.validate_session(session.session_id) is True
        
        # Should be able to get session info
        session_info = manager2.get_session_info(session.session_id)
        assert session_info is not None
        assert session_info.user_id == current_user

    def test_access_logging(self, access_manager, current_user):
        """Test access event logging"""
        # Perform some operations
        credentials = UserCredentials(user_id=current_user)
        result = access_manager.authenticate_user(credentials)
        
        session_id = result.session_id
        access_manager.extend_session(session_id)
        access_manager.terminate_session(session_id)
        
        # Check that log file exists and has content
        assert access_manager.access_log_file.exists()
        log_content = access_manager.access_log_file.read_text()
        
        assert "authenticate" in log_content
        assert "extend_session" in log_content
        assert "terminate_session" in log_content