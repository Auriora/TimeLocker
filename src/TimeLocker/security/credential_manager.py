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
import json
import base64
import time
import hashlib
import secrets
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialManagerError(Exception):
    """Base exception for credential management operations"""
    pass


class CredentialAccessError(CredentialManagerError):
    """Exception for credential access violations"""
    pass


class CredentialSecurityError(CredentialManagerError):
    """Exception for security-related credential issues"""
    pass


class CredentialManager:
    """
    Secure credential management for TimeLocker.
    Stores credentials encrypted on disk using a master password.
    """

    def __init__(self, config_dir: Optional[Path] = None, auto_lock_timeout: int = 1800):
        """
        Initialize credential manager

        Args:
            config_dir: Directory to store encrypted credentials.
                       Defaults to ~/.timelocker/credentials
            auto_lock_timeout: Auto-lock timeout in seconds (default: 30 minutes)
        """
        if config_dir is None:
            config_dir = Path.home() / ".timelocker" / "credentials"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_file = self.config_dir / "credentials.enc"
        self.audit_log_file = self.config_dir / "credential_audit.log"
        self.access_log_file = self.config_dir / "access.log"

        self._fernet: Optional[Fernet] = None
        self._unlock_time: Optional[float] = None
        self._auto_lock_timeout = auto_lock_timeout
        self._failed_attempts = 0
        self._last_failed_attempt: Optional[float] = None
        self._max_failed_attempts = 5
        self._lockout_duration = 300  # 5 minutes

        # Thread safety for concurrent access
        self._file_lock = threading.RLock()

        # Initialize audit logging
        self._initialize_audit_log()

    def _initialize_audit_log(self):
        """Initialize audit logging for credential operations"""
        if not self.audit_log_file.exists():
            with open(self.audit_log_file, 'w') as f:
                f.write(f"# TimeLocker Credential Manager Audit Log\n")
                f.write(f"# Initialized: {datetime.now().isoformat()}\n")
                f.write(f"# Format: timestamp|operation|credential_id|success|details\n")

    def _log_audit_event(self, operation: str, credential_id: str = "", success: bool = True, details: str = ""):
        """Log audit event for credential operations"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp}|{operation}|{credential_id}|{success}|{details}\n"

        try:
            with open(self.audit_log_file, 'a') as f:
                f.write(log_entry)
        except Exception:
            # Don't fail operations due to audit logging issues
            pass

    def _log_access_event(self, operation: str, success: bool = True, details: str = ""):
        """Log access event for security monitoring"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp}|{operation}|{success}|{details}\n"

        try:
            with open(self.access_log_file, 'a') as f:
                f.write(log_entry)
        except Exception:
            # Don't fail operations due to access logging issues
            pass

    def _check_lockout(self):
        """Check if credential manager is in lockout state"""
        if self._failed_attempts >= self._max_failed_attempts:
            if self._last_failed_attempt:
                time_since_last_attempt = time.time() - self._last_failed_attempt
                if time_since_last_attempt < self._lockout_duration:
                    remaining_time = self._lockout_duration - time_since_last_attempt
                    raise CredentialAccessError(
                            f"Credential manager locked due to failed attempts. "
                            f"Try again in {remaining_time:.0f} seconds."
                    )
                else:
                    # Reset failed attempts after lockout period
                    self._failed_attempts = 0
                    self._last_failed_attempt = None

    def _check_auto_lock(self):
        """Check if credential manager should auto-lock due to timeout"""
        if self._unlock_time and self._auto_lock_timeout > 0:
            if time.time() - self._unlock_time > self._auto_lock_timeout:
                self.lock()
                raise CredentialAccessError("Credential manager auto-locked due to timeout")

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create new one"""
        salt_file = self.config_dir / "salt"
        if salt_file.exists():
            return salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            salt_file.write_bytes(salt)
            return salt

    def unlock(self, master_password: str) -> bool:
        """
        Unlock the credential store with master password

        Args:
            master_password: Master password to decrypt credentials

        Returns:
            bool: True if unlock successful, False otherwise
        """
        try:
            # Check for lockout state
            self._check_lockout()

            salt = self._get_or_create_salt()
            key = self._derive_key(master_password, salt)
            self._fernet = Fernet(key)

            # Test if we can decrypt existing credentials (if any)
            if self.credentials_file.exists():
                self._load_credentials()

            # Reset failed attempts on successful unlock
            self._failed_attempts = 0
            self._last_failed_attempt = None
            self._unlock_time = time.time()

            self._log_access_event("unlock", success=True)
            return True

        except CredentialAccessError:
            # Re-raise lockout errors as-is
            raise
        except Exception as e:
            self._fernet = None
            self._failed_attempts += 1
            self._last_failed_attempt = time.time()

            self._log_access_event("unlock", success=False, details=str(e))

            if self._failed_attempts >= self._max_failed_attempts:
                self._log_audit_event("lockout_triggered", success=False,
                                      details=f"Failed attempts: {self._failed_attempts}")

            raise CredentialManagerError(f"Failed to unlock credential store: {e}")

    def _load_credentials(self) -> Dict[str, Any]:
        """Load and decrypt credentials from disk"""
        if not self._fernet:
            raise CredentialManagerError("Credential store is locked")

        if not self.credentials_file.exists():
            return {}

        try:
            encrypted_data = self.credentials_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise CredentialManagerError(f"Failed to load credentials: {e}")

    def _save_credentials(self, credentials: Dict[str, Any]) -> None:
        """Encrypt and save credentials to disk"""
        if not self._fernet:
            raise CredentialManagerError("Credential store is locked")

        try:
            json_data = json.dumps(credentials).encode()
            encrypted_data = self._fernet.encrypt(json_data)
            self.credentials_file.write_bytes(encrypted_data)
        except Exception as e:
            raise CredentialManagerError(f"Failed to save credentials: {e}")

    def store_repository_password(self, repository_id: str, password: str) -> None:
        """
        Store password for a repository

        Args:
            repository_id: Unique identifier for the repository
            password: Repository password to store
        """
        self._check_auto_lock()

        if not repository_id or not password:
            raise CredentialManagerError("Repository ID and password cannot be empty")

        with self._file_lock:
            try:
                credentials = self._load_credentials()
                if "repositories" not in credentials:
                    credentials["repositories"] = {}

                # Add metadata for credential tracking
                credentials["repositories"][repository_id] = {
                        "password":      password,
                        "type":          "repository",
                        "created_at":    datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat(),
                        "access_count":  0
                }

                self._save_credentials(credentials)
                self._log_audit_event("store_repository_password", repository_id, success=True)

            except Exception as e:
                self._log_audit_event("store_repository_password", repository_id, success=False, details=str(e))
                raise

    def get_repository_password(self, repository_id: str) -> Optional[str]:
        """
        Retrieve password for a repository

        Args:
            repository_id: Unique identifier for the repository

        Returns:
            str: Repository password if found, None otherwise
        """
        self._check_auto_lock()

        with self._file_lock:
            try:
                credentials = self._load_credentials()
                repo_creds = credentials.get("repositories", {}).get(repository_id)

                if repo_creds:
                    # Update access tracking
                    repo_creds["last_accessed"] = datetime.now().isoformat()
                    repo_creds["access_count"] = repo_creds.get("access_count", 0) + 1
                    self._save_credentials(credentials)

                    self._log_audit_event("get_repository_password", repository_id, success=True)
                    return repo_creds.get("password")
                else:
                    self._log_audit_event("get_repository_password", repository_id, success=False,
                                          details="Repository not found")
                    return None

            except Exception as e:
                self._log_audit_event("get_repository_password", repository_id, success=False, details=str(e))
                raise

    def store_backend_credentials(self, backend_type: str, credentials_dict: Dict[str, str]) -> None:
        """
        Store backend-specific credentials (e.g., AWS keys, B2 keys)
        
        Args:
            backend_type: Type of backend (s3, b2, etc.)
            credentials_dict: Dictionary of credential key-value pairs
        """
        credentials = self._load_credentials()
        if "backends" not in credentials:
            credentials["backends"] = {}

        credentials["backends"][backend_type] = credentials_dict
        self._save_credentials(credentials)

    def get_backend_credentials(self, backend_type: str) -> Dict[str, str]:
        """
        Retrieve backend-specific credentials
        
        Args:
            backend_type: Type of backend (s3, b2, etc.)
            
        Returns:
            Dict[str, str]: Dictionary of credential key-value pairs
        """
        credentials = self._load_credentials()
        return credentials.get("backends", {}).get(backend_type, {})

    def list_repositories(self) -> list[str]:
        """List all stored repository IDs"""
        credentials = self._load_credentials()
        return list(credentials.get("repositories", {}).keys())

    def remove_repository(self, repository_id: str) -> bool:
        """
        Remove stored credentials for a repository

        Args:
            repository_id: Unique identifier for the repository

        Returns:
            bool: True if removed, False if not found
        """
        with self._file_lock:
            credentials = self._load_credentials()
            repositories = credentials.get("repositories", {})

            if repository_id in repositories:
                del repositories[repository_id]
                self._save_credentials(credentials)
                return True
            return False

    def is_locked(self) -> bool:
        """Check if credential store is locked"""
        return self._fernet is None

    def lock(self) -> None:
        """Lock the credential store"""
        self._fernet = None

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """
        Change the master password
        
        Args:
            old_password: Current master password
            new_password: New master password
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Verify old password by unlocking
            if not self.unlock(old_password):
                return False

            # Load existing credentials
            credentials = self._load_credentials()

            # Generate new salt and key
            new_salt = os.urandom(16)
            new_key = self._derive_key(new_password, new_salt)
            self._fernet = Fernet(new_key)

            # Save with new encryption
            salt_file = self.config_dir / "salt"
            salt_file.write_bytes(new_salt)
            self._save_credentials(credentials)

            return True
        except Exception as e:
            raise CredentialManagerError(f"Failed to change master password: {e}")

    def rotate_credential(self, repository_id: str, new_password: str) -> bool:
        """
        Rotate a repository credential with audit trail

        Args:
            repository_id: Repository to rotate credential for
            new_password: New password to set

        Returns:
            bool: True if rotation successful
        """
        try:
            old_password = self.get_repository_password(repository_id)
            if old_password is None:
                raise CredentialManagerError(f"Repository {repository_id} not found")

            self.store_repository_password(repository_id, new_password)

            self._log_audit_event("rotate_credential", repository_id, success=True,
                                  details="Credential rotated successfully")
            return True

        except Exception as e:
            self._log_audit_event("rotate_credential", repository_id, success=False, details=str(e))
            raise

    def secure_delete_credential(self, repository_id: str) -> bool:
        """
        Securely delete a credential with multiple overwrites

        Args:
            repository_id: Repository credential to delete

        Returns:
            bool: True if deletion successful
        """
        try:
            credentials = self._load_credentials()
            repositories = credentials.get("repositories", {})

            if repository_id not in repositories:
                return False

            # Overwrite the password multiple times before deletion
            for _ in range(3):
                repositories[repository_id]["password"] = secrets.token_urlsafe(32)
                self._save_credentials(credentials)

            # Finally delete the entry
            del repositories[repository_id]
            self._save_credentials(credentials)

            self._log_audit_event("secure_delete_credential", repository_id, success=True)
            return True

        except Exception as e:
            self._log_audit_event("secure_delete_credential", repository_id, success=False, details=str(e))
            raise

    def get_credential_metadata(self, repository_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a credential without exposing the password

        Args:
            repository_id: Repository to get metadata for

        Returns:
            Dict containing metadata (without password)
        """
        try:
            credentials = self._load_credentials()
            repo_creds = credentials.get("repositories", {}).get(repository_id)

            if repo_creds:
                metadata = repo_creds.copy()
                metadata.pop("password", None)  # Remove password from metadata
                return metadata
            return None

        except Exception as e:
            self._log_audit_event("get_credential_metadata", repository_id, success=False, details=str(e))
            raise

    def get_security_status(self) -> Dict[str, Any]:
        """
        Get security status and statistics

        Returns:
            Dict containing security status information
        """
        return {
                "is_locked":               self.is_locked(),
                "failed_attempts":         self._failed_attempts,
                "auto_lock_timeout":       self._auto_lock_timeout,
                "time_since_unlock":       time.time() - self._unlock_time if self._unlock_time else None,
                "lockout_active":          self._failed_attempts >= self._max_failed_attempts,
                "audit_log_exists":        self.audit_log_file.exists(),
                "credentials_file_exists": self.credentials_file.exists()
        }

    def get_audit_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent audit events

        Args:
            hours: Number of hours to look back

        Returns:
            List of audit events
        """
        events = []
        if not self.audit_log_file.exists():
            return events

        cutoff_time = datetime.now() - timedelta(hours=hours)

        try:
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue

                    parts = line.strip().split('|')
                    if len(parts) >= 4:
                        try:
                            event_time = datetime.fromisoformat(parts[0])
                            if event_time >= cutoff_time:
                                events.append({
                                        "timestamp":     parts[0],
                                        "operation":     parts[1],
                                        "credential_id": parts[2],
                                        "success":       parts[3] == "True",
                                        "details":       parts[4] if len(parts) > 4 else ""
                                })
                        except ValueError:
                            continue
        except Exception:
            pass

        return events

    def validate_credential_integrity(self) -> bool:
        """
        Validate the integrity of stored credentials

        Returns:
            bool: True if all credentials are valid and accessible
        """
        if self.is_locked():
            raise CredentialSecurityError("Cannot validate credentials while locked")

        try:
            credentials = self._load_credentials()

            # Check if we can access all stored credentials
            for repo_id in credentials.get("repositories", {}):
                password = self.get_repository_password(repo_id)
                if password is None:
                    return False

            self._log_audit_event("validate_integrity", success=True)
            return True

        except Exception as e:
            self._log_audit_event("validate_integrity", success=False, details=str(e))
            return False
