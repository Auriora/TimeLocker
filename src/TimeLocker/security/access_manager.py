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
import stat
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class AccessManagerError(Exception):
    """Base exception for access manager operations"""
    pass


class AuthenticationError(AccessManagerError):
    """Exception for authentication failures"""
    pass


class AuthorizationError(AccessManagerError):
    """Exception for authorization failures"""
    pass


class SessionError(AccessManagerError):
    """Exception for session management errors"""
    pass


@dataclass
class UserCredentials:
    """User credentials for authentication"""
    user_id: str
    password: Optional[str] = None
    token: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthResult:
    """Result of authentication attempt"""
    success: bool
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """User session information"""
    session_id: str
    user_id: str
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if session is valid (active and not expired)"""
        return self.is_active and not self.is_expired()

    def extend_expiry(self, timeout_minutes: int = 30) -> None:
        """Extend session expiry time"""
        self.expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
        self.last_accessed = datetime.now()


@dataclass
class SecurityContext:
    """Security context for operations"""
    user_id: str
    session_id: str
    operation: str
    resource: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Operation:
    """Represents an operation that requires authorization"""
    
    def __init__(self, name: str, resource_type: str = "general", 
                 required_permissions: Optional[List[str]] = None):
        self.name = name
        self.resource_type = resource_type
        self.required_permissions = required_permissions or []


class AccessManager:
    """
    Access Manager for session management and access control in TimeLocker.
    
    Provides user authentication, session management with timeout handling,
    and file system permission checks suitable for desktop environments.
    """

    # Default session timeout in minutes
    DEFAULT_SESSION_TIMEOUT = 30
    
    # Maximum failed authentication attempts before lockout
    MAX_FAILED_ATTEMPTS = 3
    
    # Lockout duration in minutes
    LOCKOUT_DURATION = 15

    def __init__(self, config_dir: Optional[Path] = None, 
                 session_timeout_minutes: int = DEFAULT_SESSION_TIMEOUT):
        """
        Initialize Access Manager
        
        Args:
            config_dir: Directory for access control configuration and session storage
            session_timeout_minutes: Session timeout in minutes (default: 30)
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            base_config_dir = ConfigurationPathResolver.get_config_directory()
            config_dir = base_config_dir / "access"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure proper permissions on config directory
        self._secure_directory(self.config_dir)

        self.session_timeout_minutes = session_timeout_minutes
        self.sessions_file = self.config_dir / "sessions.json"
        self.access_log_file = self.config_dir / "access.log"
        self.failed_attempts_file = self.config_dir / "failed_attempts.json"

        # In-memory session storage for performance
        self._sessions: Dict[str, Session] = {}
        self._failed_attempts: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self._session_lock = threading.RLock()
        self._failed_attempts_lock = threading.RLock()

        # Load existing sessions and failed attempts
        self._load_sessions()
        self._load_failed_attempts()

        # Initialize access logging
        self._initialize_access_log()

    def _initialize_access_log(self) -> None:
        """Initialize access logging"""
        if not self.access_log_file.exists():
            with open(self.access_log_file, 'w') as f:
                f.write("# TimeLocker Access Manager Log\n")
                f.write(f"# Initialized: {datetime.now().isoformat()}\n")
                f.write("# Format: timestamp|operation|user_id|session_id|success|details\n")

    def _log_access_event(self, operation: str, user_id: str = "", 
                         session_id: str = "", success: bool = True, 
                         details: str = "") -> None:
        """Log access event"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp}|{operation}|{user_id}|{session_id}|{success}|{details}\n"

        try:
            with open(self.access_log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.warning(f"Failed to log access event: {e}")

    def _secure_directory(self, directory: Path) -> None:
        """
        Secure directory permissions for user-only access
        
        Args:
            directory: Directory to secure
        """
        try:
            # Set permissions to user read/write/execute only (700)
            directory.chmod(stat.S_IRWXU)
            logger.debug(f"Secured directory permissions: {directory}")
        except Exception as e:
            logger.warning(f"Failed to secure directory {directory}: {e}")

    def _load_sessions(self) -> None:
        """Load sessions from persistent storage"""
        if not self.sessions_file.exists():
            return

        try:
            with open(self.sessions_file, 'r') as f:
                sessions_data = json.load(f)

            with self._session_lock:
                for session_id, session_dict in sessions_data.items():
                    session = Session(
                        session_id=session_dict['session_id'],
                        user_id=session_dict['user_id'],
                        created_at=datetime.fromisoformat(session_dict['created_at']),
                        last_accessed=datetime.fromisoformat(session_dict['last_accessed']),
                        expires_at=datetime.fromisoformat(session_dict['expires_at']),
                        is_active=session_dict.get('is_active', True),
                        metadata=session_dict.get('metadata', {})
                    )
                    
                    # Only load valid sessions
                    if session.is_valid():
                        self._sessions[session_id] = session

            logger.debug(f"Loaded {len(self._sessions)} valid sessions")

        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            self._sessions = {}

    def _save_sessions(self) -> None:
        """Save sessions to persistent storage"""
        try:
            sessions_data = {}
            
            with self._session_lock:
                for session_id, session in self._sessions.items():
                    if session.is_valid():
                        sessions_data[session_id] = {
                            'session_id': session.session_id,
                            'user_id': session.user_id,
                            'created_at': session.created_at.isoformat(),
                            'last_accessed': session.last_accessed.isoformat(),
                            'expires_at': session.expires_at.isoformat(),
                            'is_active': session.is_active,
                            'metadata': session.metadata
                        }

            with open(self.sessions_file, 'w') as f:
                json.dump(sessions_data, f, indent=2)

            # Secure the sessions file
            self.sessions_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def _load_failed_attempts(self) -> None:
        """Load failed authentication attempts from storage"""
        if not self.failed_attempts_file.exists():
            return

        try:
            with open(self.failed_attempts_file, 'r') as f:
                self._failed_attempts = json.load(f)

            # Clean up old failed attempts (older than lockout duration)
            self._cleanup_old_failed_attempts()

        except Exception as e:
            logger.error(f"Failed to load failed attempts: {e}")
            self._failed_attempts = {}

    def _save_failed_attempts(self) -> None:
        """Save failed authentication attempts to storage"""
        try:
            with open(self.failed_attempts_file, 'w') as f:
                json.dump(self._failed_attempts, f, indent=2)

            # Secure the failed attempts file
            self.failed_attempts_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

        except Exception as e:
            logger.error(f"Failed to save failed attempts: {e}")

    def _cleanup_old_failed_attempts(self) -> None:
        """Clean up old failed authentication attempts"""
        cutoff_time = datetime.now() - timedelta(minutes=self.LOCKOUT_DURATION)
        
        with self._failed_attempts_lock:
            users_to_remove = []
            for user_id, attempt_data in self._failed_attempts.items():
                last_attempt = datetime.fromisoformat(attempt_data.get('last_attempt', '1970-01-01'))
                if last_attempt < cutoff_time:
                    users_to_remove.append(user_id)

            for user_id in users_to_remove:
                del self._failed_attempts[user_id]

    def _is_user_locked_out(self, user_id: str) -> bool:
        """
        Check if user is locked out due to failed attempts
        
        Args:
            user_id: User ID to check
            
        Returns:
            bool: True if user is locked out
        """
        with self._failed_attempts_lock:
            if user_id not in self._failed_attempts:
                return False

            attempt_data = self._failed_attempts[user_id]
            attempt_count = attempt_data.get('count', 0)
            
            if attempt_count < self.MAX_FAILED_ATTEMPTS:
                return False

            last_attempt = datetime.fromisoformat(attempt_data.get('last_attempt', '1970-01-01'))
            lockout_expires = last_attempt + timedelta(minutes=self.LOCKOUT_DURATION)
            
            if datetime.now() > lockout_expires:
                # Lockout expired, reset attempts
                del self._failed_attempts[user_id]
                self._save_failed_attempts()
                return False

            return True

    def _record_failed_attempt(self, user_id: str) -> None:
        """
        Record a failed authentication attempt
        
        Args:
            user_id: User ID that failed authentication
        """
        with self._failed_attempts_lock:
            if user_id not in self._failed_attempts:
                self._failed_attempts[user_id] = {'count': 0}

            self._failed_attempts[user_id]['count'] += 1
            self._failed_attempts[user_id]['last_attempt'] = datetime.now().isoformat()

            self._save_failed_attempts()

    def _reset_failed_attempts(self, user_id: str) -> None:
        """
        Reset failed authentication attempts for user
        
        Args:
            user_id: User ID to reset attempts for
        """
        with self._failed_attempts_lock:
            if user_id in self._failed_attempts:
                del self._failed_attempts[user_id]
                self._save_failed_attempts()

    def authenticate_user(self, credentials: UserCredentials) -> AuthResult:
        """
        Authenticate user with provided credentials
        
        Args:
            credentials: User credentials for authentication
            
        Returns:
            AuthResult: Result of authentication attempt
        """
        try:
            # Check if user is locked out
            if self._is_user_locked_out(credentials.user_id):
                error_msg = f"User {credentials.user_id} is locked out due to failed attempts"
                self._log_access_event("authenticate", credentials.user_id, 
                                     success=False, details="User locked out")
                return AuthResult(
                    success=False,
                    error_message=error_msg
                )

            # For desktop environment, we use simplified authentication
            # In a real implementation, this would validate against system users
            # or a user database. For now, we accept any non-empty user_id
            if not credentials.user_id:
                error_msg = "User ID cannot be empty"
                self._log_access_event("authenticate", credentials.user_id,
                                     success=False, details="Empty user ID")
                return AuthResult(
                    success=False,
                    error_message=error_msg
                )

            # Simple validation: user_id should be the current system user
            current_user = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
            if credentials.user_id != current_user:
                self._record_failed_attempt(credentials.user_id)
                error_msg = f"Invalid user: {credentials.user_id}"
                self._log_access_event("authenticate", credentials.user_id,
                                     success=False, details="Invalid user")
                return AuthResult(
                    success=False,
                    error_message=error_msg
                )

            # Authentication successful
            self._reset_failed_attempts(credentials.user_id)
            session = self.create_session(credentials.user_id)
            
            self._log_access_event("authenticate", credentials.user_id, 
                                 session.session_id, success=True)
            
            return AuthResult(
                success=True,
                user_id=credentials.user_id,
                session_id=session.session_id
            )

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self._log_access_event("authenticate", credentials.user_id,
                                 success=False, details=str(e))
            return AuthResult(
                success=False,
                error_message=f"Authentication failed: {e}"
            )

    def create_session(self, user_id: str) -> Session:
        """
        Create a new session for authenticated user
        
        Args:
            user_id: User ID to create session for
            
        Returns:
            Session: New session object
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(minutes=self.session_timeout_minutes)

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_accessed=now,
            expires_at=expires_at
        )

        with self._session_lock:
            self._sessions[session_id] = session
            self._save_sessions()

        self._log_access_event("create_session", user_id, session_id, success=True)
        logger.debug(f"Created session {session_id} for user {user_id}")

        return session

    def validate_session(self, session_id: str) -> bool:
        """
        Validate if session is active and not expired
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            bool: True if session is valid
        """
        try:
            with self._session_lock:
                session = self._sessions.get(session_id)
                
                if not session:
                    self._log_access_event("validate_session", session_id=session_id,
                                         success=False, details="Session not found")
                    return False

                if not session.is_valid():
                    # Remove invalid session
                    del self._sessions[session_id]
                    self._save_sessions()
                    self._log_access_event("validate_session", session.user_id, session_id,
                                         success=False, details="Session expired or inactive")
                    return False

                # Update last accessed time
                session.last_accessed = datetime.now()
                self._save_sessions()
                
                return True

        except Exception as e:
            logger.error(f"Session validation error: {e}")
            self._log_access_event("validate_session", session_id=session_id,
                                 success=False, details=str(e))
            return False

    def extend_session(self, session_id: str) -> bool:
        """
        Extend session expiry time
        
        Args:
            session_id: Session ID to extend
            
        Returns:
            bool: True if session was extended successfully
        """
        try:
            with self._session_lock:
                session = self._sessions.get(session_id)
                
                if not session or not session.is_valid():
                    self._log_access_event("extend_session", session_id=session_id,
                                         success=False, details="Invalid session")
                    return False

                session.extend_expiry(self.session_timeout_minutes)
                self._save_sessions()

                self._log_access_event("extend_session", session.user_id, session_id,
                                     success=True)
                return True

        except Exception as e:
            logger.error(f"Session extension error: {e}")
            self._log_access_event("extend_session", session_id=session_id,
                                 success=False, details=str(e))
            return False

    def terminate_session(self, session_id: str) -> None:
        """
        Terminate a session
        
        Args:
            session_id: Session ID to terminate
        """
        try:
            with self._session_lock:
                session = self._sessions.get(session_id)
                
                if session:
                    user_id = session.user_id
                    del self._sessions[session_id]
                    self._save_sessions()
                    
                    self._log_access_event("terminate_session", user_id, session_id,
                                         success=True)
                    logger.debug(f"Terminated session {session_id}")

        except Exception as e:
            logger.error(f"Session termination error: {e}")
            self._log_access_event("terminate_session", session_id=session_id,
                                 success=False, details=str(e))

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            int: Number of sessions cleaned up
        """
        cleaned_count = 0
        
        try:
            with self._session_lock:
                expired_sessions = []
                
                for session_id, session in self._sessions.items():
                    if not session.is_valid():
                        expired_sessions.append(session_id)

                for session_id in expired_sessions:
                    del self._sessions[session_id]
                    cleaned_count += 1

                if cleaned_count > 0:
                    self._save_sessions()
                    self._log_access_event("cleanup_sessions", 
                                         details=f"Cleaned {cleaned_count} expired sessions")

        except Exception as e:
            logger.error(f"Session cleanup error: {e}")

        return cleaned_count

    def check_file_permissions(self, path: str, operation: str) -> bool:
        """
        Check file system permissions for operation
        
        Args:
            path: File or directory path to check
            operation: Operation type ('read', 'write', 'execute')
            
        Returns:
            bool: True if operation is permitted
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return False

            if operation == 'read':
                return os.access(file_path, os.R_OK)
            elif operation == 'write':
                return os.access(file_path, os.W_OK)
            elif operation == 'execute':
                return os.access(file_path, os.X_OK)
            else:
                # Unknown operation, deny by default
                return False

        except Exception as e:
            logger.error(f"Permission check error for {path}: {e}")
            return False

    def authorize_operation(self, operation: Operation, context: SecurityContext) -> bool:
        """
        Authorize operation based on security context
        
        Args:
            operation: Operation to authorize
            context: Security context for the operation
            
        Returns:
            bool: True if operation is authorized
        """
        try:
            # Validate session first
            if not self.validate_session(context.session_id):
                self._log_access_event("authorize_operation", context.user_id, 
                                     context.session_id, success=False, 
                                     details=f"Invalid session for {operation.name}")
                return False

            # For desktop environment, we use simplified authorization
            # All authenticated users can perform all operations
            # In a more complex system, this would check roles and permissions
            
            self._log_access_event("authorize_operation", context.user_id,
                                 context.session_id, success=True,
                                 details=f"Authorized {operation.name}")
            return True

        except Exception as e:
            logger.error(f"Authorization error: {e}")
            self._log_access_event("authorize_operation", context.user_id,
                                 context.session_id, success=False,
                                 details=str(e))
            return False

    def get_session_info(self, session_id: str) -> Optional[Session]:
        """
        Get session information
        
        Args:
            session_id: Session ID to get info for
            
        Returns:
            Session: Session object if found and valid, None otherwise
        """
        with self._session_lock:
            session = self._sessions.get(session_id)
            if session and session.is_valid():
                return session
            return None

    def get_active_sessions(self, user_id: Optional[str] = None) -> List[Session]:
        """
        Get list of active sessions
        
        Args:
            user_id: Optional user ID to filter sessions
            
        Returns:
            List[Session]: List of active sessions
        """
        active_sessions = []
        
        with self._session_lock:
            for session in self._sessions.values():
                if session.is_valid():
                    if user_id is None or session.user_id == user_id:
                        active_sessions.append(session)

        return active_sessions

    def get_security_status(self) -> Dict[str, Any]:
        """
        Get security status information
        
        Returns:
            Dict: Security status information
        """
        with self._session_lock:
            active_sessions = len([s for s in self._sessions.values() if s.is_valid()])
            
        with self._failed_attempts_lock:
            locked_users = len([
                user_id for user_id in self._failed_attempts.keys()
                if self._is_user_locked_out(user_id)
            ])

        return {
            'active_sessions': active_sessions,
            'total_sessions': len(self._sessions),
            'locked_users': locked_users,
            'session_timeout_minutes': self.session_timeout_minutes,
            'max_failed_attempts': self.MAX_FAILED_ATTEMPTS,
            'lockout_duration_minutes': self.LOCKOUT_DURATION,
            'config_directory': str(self.config_dir),
            'access_log_exists': self.access_log_file.exists()
        }