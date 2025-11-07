"""Authentication and session management helpers."""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...security.access_manager import AccessManager
    from ...security.credential_manager import CredentialManager

logger = logging.getLogger(__name__)


def _authenticate_user_session(access_manager: 'AccessManager', user_id: Optional[str] = None) -> Optional[str]:
    """
    Authenticate user and create session if needed.
    
    Args:
        access_manager: AccessManager instance
        user_id: Optional user ID (defaults to current system user)
        
    Returns:
        Session ID if authentication successful, None otherwise
    """
    try:
        if user_id is None:
            import os
            user_id = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
        
        from ...security.access_manager import UserCredentials
        credentials = UserCredentials(user_id=user_id)
        
        auth_result = access_manager.authenticate_user(credentials)
        if auth_result.success:
            return auth_result.session_id
        else:
            logger.warning(f"Authentication failed: {auth_result.error_message}")
            return None
            
    except Exception as e:
        logger.error(f"Session authentication error: {e}")
        return None


def _validate_session_for_operation(access_manager: 'AccessManager', operation: str, 
                                   repository_id: Optional[str] = None) -> bool:
    """
    Validate session for operation and create if needed.
    
    Args:
        access_manager: AccessManager instance
        operation: Operation being performed
        repository_id: Optional repository ID
        
    Returns:
        True if session is valid for operation
    """
    try:
        # Get or create session
        active_sessions = access_manager.get_active_sessions()
        session_id = None
        
        if active_sessions:
            # Use the most recent valid session
            for session in sorted(active_sessions, key=lambda s: s.last_accessed, reverse=True):
                if session.is_valid():
                    session_id = session.session_id
                    break
        
        if not session_id:
            # Create new session
            session_id = _authenticate_user_session(access_manager)
            if not session_id:
                return False
        
        # Validate session for operation
        if not access_manager.validate_session(session_id):
            return False
            
        # Extend session
        access_manager.extend_session(session_id)
        
        return True
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return False


def _ensure_manager_unlocked(manager: 'CredentialManager', master_password: Optional[str], interactive: bool) -> None:
    """
    Ensure credential manager is unlocked, prompting for password if needed.
    
    Args:
        manager: CredentialManager instance
        master_password: Optional master password
        interactive: Whether to prompt for password interactively
        
    Raises:
        typer.Exit: If manager cannot be unlocked
    """
    import typer
    from rich.prompt import Prompt
    from .display import show_error_panel, console
    
    if manager.is_unlocked():
        return
    
    password = master_password
    if not password and interactive:
        password = Prompt.ask("Enter master password", password=True, console=console)
    
    if not password:
        show_error_panel("Authentication Required", "Master password is required to access credentials.")
        raise typer.Exit(1)
    
    if not manager.unlock(password):
        show_error_panel("Authentication Failed", "Invalid master password.")
        raise typer.Exit(1)
