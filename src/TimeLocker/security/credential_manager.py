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
import socket
import uuid
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

    def _get_auto_master_key(self) -> Optional[str]:
        """
        Derive master key from system fingerprint for auto-unlock

        This creates a deterministic key based on stable system identifiers,
        allowing non-interactive unlock while maintaining security.

        Returns:
            str: Auto-derived master key, or None if derivation fails
        """
        try:
            # Collect stable system identifiers
            identifiers = []

            # Machine ID (Linux/systemd)
            machine_id_file = Path("/etc/machine-id")
            if machine_id_file.exists():
                identifiers.append(machine_id_file.read_text().strip())
            else:
                # Fallback: try /var/lib/dbus/machine-id
                dbus_machine_id = Path("/var/lib/dbus/machine-id")
                if dbus_machine_id.exists():
                    identifiers.append(dbus_machine_id.read_text().strip())
                else:
                    # Generate a stable UUID based on hostname and user
                    hostname = socket.gethostname()
                    username = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
                    stable_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{hostname}.{username}"))
                    identifiers.append(stable_id)

            # User ID
            try:
                identifiers.append(str(os.getuid()))
            except AttributeError:
                # Windows doesn't have getuid
                identifiers.append(os.getenv('USERNAME', 'unknown'))

            # Hostname
            identifiers.append(socket.gethostname())

            # TimeLocker-specific salt for namespace separation
            identifiers.append("timelocker-auto-unlock-v1")

            # Create deterministic but secure fingerprint
            fingerprint = ":".join(identifiers)

            # Use PBKDF2 to create a strong key from the fingerprint
            auto_key = hashlib.pbkdf2_hmac(
                    'sha256',
                    fingerprint.encode('utf-8'),
                    b'timelocker_auto_salt_v1',
                    100000  # Same iteration count as manual keys
            ).hex()

            return auto_key

        except Exception as e:
            # Log the failure but don't expose details
            self._log_access_event("auto_key_derivation", success=False,
                                   details="Auto-key derivation failed")
            return None

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create new one"""
        salt_file = self.config_dir / "salt"
        if salt_file.exists():
            return salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            salt_file.write_bytes(salt)
            return salt

    def auto_unlock(self) -> bool:
        """
        Attempt to unlock credential store using auto-derived key

        This enables non-interactive operation by deriving the master key
        from stable system identifiers.

        Returns:
            bool: True if auto-unlock successful, False otherwise
        """
        try:
            auto_key = self._get_auto_master_key()
            if not auto_key:
                return False

            return self.unlock(auto_key, is_auto_unlock=True)

        except Exception as e:
            self._log_access_event("auto_unlock", success=False, details=str(e))
            return False

    def unlock(self, master_password: str, is_auto_unlock: bool = False) -> bool:
        """
        Unlock the credential store with master password

        Args:
            master_password: Master password to decrypt credentials
            is_auto_unlock: Whether this is an automatic unlock attempt

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

            unlock_type = "auto_unlock" if is_auto_unlock else "manual_unlock"
            self._log_access_event(unlock_type, success=True)
            return True

        except CredentialAccessError:
            # Re-raise lockout errors as-is
            raise
        except Exception as e:
            self._fernet = None
            # Only increment failed attempts for manual unlocks to avoid lockout from auto-unlock attempts
            if not is_auto_unlock:
                self._failed_attempts += 1
                self._last_failed_attempt = time.time()

            unlock_type = "auto_unlock" if is_auto_unlock else "manual_unlock"
            self._log_access_event(unlock_type, success=False, details=str(e))

            if self._failed_attempts >= self._max_failed_attempts:
                self._log_audit_event("lockout_triggered", success=False,
                                      details=f"Failed attempts: {self._failed_attempts}")

            raise CredentialManagerError(f"Failed to unlock credential store: {e}")

    def ensure_unlocked(self, allow_prompt: bool = True) -> bool:
        """
        Ensure credential store is unlocked using the best available method

        This method implements the credential resolution chain:
        1. Check if already unlocked
        2. Try auto-unlock (non-interactive)
        3. Try environment variable (TIMELOCKER_MASTER_PASSWORD)
        4. Prompt user (if allowed)

        Args:
            allow_prompt: Whether to prompt user if other methods fail

        Returns:
            bool: True if successfully unlocked, False otherwise
        """
        # Already unlocked?
        if not self.is_locked():
            return True

        # Try auto-unlock first (non-interactive)
        if self.auto_unlock():
            return True

        # Try environment variable
        env_master_password = os.getenv('TIMELOCKER_MASTER_PASSWORD')
        if env_master_password:
            try:
                if self.unlock(env_master_password):
                    return True
            except Exception:
                pass  # Continue to next method

        # Last resort: prompt user (if allowed)
        if allow_prompt:
            try:
                import getpass
                master_password = getpass.getpass("TimeLocker master password: ")
                if master_password and self.unlock(master_password):
                    return True
            except (KeyboardInterrupt, EOFError):
                pass  # User cancelled
            except Exception:
                pass  # Import or other error

        return False

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

    def store_repository_password(self, repository_id: str, password: str, allow_prompt: bool = True) -> None:
        """
        Store password for a repository

        Security policy: do not auto-unlock here. If locked, raise
        CredentialManagerError so callers can decide how to unlock.

        Args:
            repository_id: Unique identifier for the repository
            password: Repository password to store
            allow_prompt: Unused here (kept for API compatibility)
        """
        self._check_auto_lock()

        if not repository_id or not password:
            raise CredentialManagerError("Repository ID and password cannot be empty")

        # Strict: do not auto-unlock in storage path
        if self.is_locked():
            raise CredentialManagerError("Credential store is locked")

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

    def get_repository_password(self, repository_id: str, allow_prompt: bool = False) -> Optional[str]:
        """
        Retrieve password for a repository

        Security policy: do not auto-unlock here. If locked, raise
        CredentialManagerError so callers can decide how to unlock.

        Args:
            repository_id: Unique identifier for the repository
            allow_prompt: Unused here (kept for API compatibility)

        Returns:
            str: Repository password if found, None otherwise
        """
        self._check_auto_lock()

        # Strict: do not auto-unlock in retrieval path
        if self.is_locked():
            raise CredentialManagerError("Credential store is locked")

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

    def store_repository_backend_credentials(
        self,
        repository_id: str,
        backend_type: str,
        credentials_dict: Dict[str, str]
    ) -> None:
        """
        Store backend-specific credentials for a specific repository.

        Args:
            repository_id: Repository identifier (name)
            backend_type: Type of backend (s3, b2, etc.)
            credentials_dict: Dictionary of credential key-value pairs
                For S3: {"access_key_id": "...", "secret_access_key": "...", "region": "..."}
                For B2: {"account_id": "...", "account_key": "..."}
        """
        self._check_auto_lock()

        if not repository_id or not backend_type:
            raise CredentialManagerError("Repository ID and backend type cannot be empty")

        if self.is_locked():
            raise CredentialManagerError("Credential store is locked")

        with self._file_lock:
            try:
                credentials = self._load_credentials()

                # Initialize nested structure if needed
                if "repository_backends" not in credentials:
                    credentials["repository_backends"] = {}
                if repository_id not in credentials["repository_backends"]:
                    credentials["repository_backends"][repository_id] = {}

                # Store credentials with metadata
                credentials["repository_backends"][repository_id][backend_type] = {
                    "credentials": credentials_dict,
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                    "access_count": 0
                }

                self._save_credentials(credentials)
                self._log_audit_event(
                    "store_repository_backend_credentials",
                    f"{repository_id}:{backend_type}",
                    success=True
                )

            except Exception as e:
                self._log_audit_event(
                    "store_repository_backend_credentials",
                    f"{repository_id}:{backend_type}",
                    success=False,
                    details=str(e)
                )
                raise

    def get_repository_backend_credentials(
        self,
        repository_id: str,
        backend_type: str
    ) -> Dict[str, str]:
        """
        Retrieve backend-specific credentials for a specific repository.

        Args:
            repository_id: Repository identifier (name)
            backend_type: Type of backend (s3, b2, etc.)

        Returns:
            Dict[str, str]: Dictionary of credential key-value pairs, empty dict if not found
        """
        self._check_auto_lock()

        if self.is_locked():
            raise CredentialManagerError("Credential store is locked")

        with self._file_lock:
            try:
                credentials = self._load_credentials()
                repo_backends = credentials.get("repository_backends", {}).get(repository_id, {})
                backend_creds = repo_backends.get(backend_type)

                if backend_creds:
                    # Update access tracking
                    backend_creds["last_accessed"] = datetime.now().isoformat()
                    backend_creds["access_count"] = backend_creds.get("access_count", 0) + 1
                    self._save_credentials(credentials)

                    self._log_audit_event(
                        "get_repository_backend_credentials",
                        f"{repository_id}:{backend_type}",
                        success=True
                    )
                    return backend_creds.get("credentials", {})
                else:
                    self._log_audit_event(
                        "get_repository_backend_credentials",
                        f"{repository_id}:{backend_type}",
                        success=False,
                        details="Credentials not found"
                    )
                    return {}

            except Exception as e:
                self._log_audit_event(
                    "get_repository_backend_credentials",
                    f"{repository_id}:{backend_type}",
                    success=False,
                    details=str(e)
                )
                raise

    def remove_repository_backend_credentials(
        self,
        repository_id: str,
        backend_type: str
    ) -> bool:
        """
        Remove backend credentials for a specific repository.

        Args:
            repository_id: Repository identifier (name)
            backend_type: Type of backend (s3, b2, etc.)

        Returns:
            bool: True if removed, False if not found
        """
        if self.is_locked():
            raise CredentialManagerError("Credential store is locked")

        with self._file_lock:
            try:
                credentials = self._load_credentials()
                repo_backends = credentials.get("repository_backends", {}).get(repository_id, {})

                if backend_type in repo_backends:
                    del repo_backends[backend_type]

                    # Clean up empty repository entry
                    if not repo_backends:
                        del credentials["repository_backends"][repository_id]

                    self._save_credentials(credentials)
                    self._log_audit_event(
                        "remove_repository_backend_credentials",
                        f"{repository_id}:{backend_type}",
                        success=True
                    )
                    return True
                else:
                    return False

            except Exception as e:
                self._log_audit_event(
                    "remove_repository_backend_credentials",
                    f"{repository_id}:{backend_type}",
                    success=False,
                    details=str(e)
                )
                raise

    def has_repository_backend_credentials(
        self,
        repository_id: str,
        backend_type: str
    ) -> bool:
        """
        Check if repository has backend credentials stored.

        Args:
            repository_id: Repository identifier (name)
            backend_type: Type of backend (s3, b2, etc.)

        Returns:
            bool: True if credentials exist, False otherwise
        """
        if self.is_locked():
            # Don't raise error for check operations, just return False
            return False

        try:
            credentials = self._load_credentials()
            repo_backends = credentials.get("repository_backends", {}).get(repository_id, {})
            return backend_type in repo_backends
        except Exception:
            return False

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
