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
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialManagerError(Exception):
    """Base exception for credential management operations"""
    pass


class CredentialManager:
    """
    Secure credential management for TimeLocker.
    Stores credentials encrypted on disk using a master password.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize credential manager
        
        Args:
            config_dir: Directory to store encrypted credentials. 
                       Defaults to ~/.timelocker/credentials
        """
        if config_dir is None:
            config_dir = Path.home() / ".timelocker" / "credentials"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_file = self.config_dir / "credentials.enc"
        self._fernet: Optional[Fernet] = None

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
            salt = self._get_or_create_salt()
            key = self._derive_key(master_password, salt)
            self._fernet = Fernet(key)

            # Test if we can decrypt existing credentials (if any)
            if self.credentials_file.exists():
                self._load_credentials()

            return True
        except Exception as e:
            self._fernet = None
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
        credentials = self._load_credentials()
        if "repositories" not in credentials:
            credentials["repositories"] = {}

        credentials["repositories"][repository_id] = {
                "password": password,
                "type":     "repository"
        }

        self._save_credentials(credentials)

    def get_repository_password(self, repository_id: str) -> Optional[str]:
        """
        Retrieve password for a repository
        
        Args:
            repository_id: Unique identifier for the repository
            
        Returns:
            str: Repository password if found, None otherwise
        """
        credentials = self._load_credentials()
        repo_creds = credentials.get("repositories", {}).get(repository_id)
        return repo_creds.get("password") if repo_creds else None

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
