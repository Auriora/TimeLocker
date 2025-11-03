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

import json
import logging
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from ..interfaces.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class EncryptionError(ConfigurationError):
    """Exception for encryption-related configuration errors"""
    pass


class IntegrityError(ConfigurationError):
    """Exception for configuration integrity verification failures"""
    pass


class EncryptionLevel(Enum):
    """Encryption levels for configuration values"""
    NONE = "none"
    SENSITIVE = "sensitive"  # Passwords, keys, tokens
    FULL = "full"  # All configuration data


@dataclass
class EncryptionMetadata:
    """Metadata for encrypted configuration values"""
    encrypted: bool
    algorithm: str
    key_id: str
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0


@dataclass
class ConfigurationSignature:
    """Digital signature for configuration integrity"""
    signature: str
    algorithm: str
    timestamp: datetime
    sections: List[str]
    checksum: str


class SecurityConfigurationManager:
    """
    Provides encryption and integrity verification for configuration data.
    
    Integrates with TimeLocker Security Services to encrypt sensitive configuration
    values and verify configuration integrity through digital signatures.
    """

    def __init__(self, security_service: Optional['SecurityService'] = None, 
                 config_dir: Optional[Path] = None):
        """
        Initialize security configuration manager.
        
        Args:
            security_service: SecurityService instance for encryption operations
            config_dir: Configuration directory for security metadata
        """
        self.security_service = security_service
        
        if config_dir is None:
            from .configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory()
        
        self.config_dir = Path(config_dir)
        self.security_dir = self.config_dir / "security"
        self.security_dir.mkdir(parents=True, exist_ok=True)
        
        # Security metadata files
        self.encryption_metadata_file = self.security_dir / "encryption_metadata.json"
        self.signature_file = self.security_dir / "configuration_signature.json"
        self.key_store_file = self.security_dir / "key_store.enc"
        
        # Sensitive configuration patterns
        self.sensitive_patterns = {
            "password", "passwd", "secret", "key", "token", "credential",
            "auth", "api_key", "access_key", "private_key", "cert", "certificate"
        }
        
        # Initialize encryption key management
        self._encryption_keys: Dict[str, bytes] = {}
        self._current_key_id: Optional[str] = None
        
        # Load existing metadata
        self._load_encryption_metadata()

    def _load_encryption_metadata(self) -> None:
        """Load encryption metadata from disk"""
        try:
            if self.encryption_metadata_file.exists():
                with open(self.encryption_metadata_file, 'r') as f:
                    metadata = json.load(f)
                    self._current_key_id = metadata.get("current_key_id")
                    
                    # Load encryption keys if security service is available
                    if self.security_service and self.key_store_file.exists():
                        self._load_encryption_keys()
                        
        except Exception as e:
            logger.warning(f"Failed to load encryption metadata: {e}")

    def _save_encryption_metadata(self) -> None:
        """Save encryption metadata to disk"""
        try:
            metadata = {
                "current_key_id": self._current_key_id,
                "created_at": datetime.now().isoformat(),
                "key_count": len(self._encryption_keys)
            }
            
            with open(self.encryption_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save encryption metadata: {e}")
            raise EncryptionError(f"Failed to save encryption metadata: {e}")

    def _generate_encryption_key(self) -> str:
        """
        Generate a new encryption key for configuration data.
        
        Returns:
            str: Key identifier for the generated key
        """
        try:
            # Generate a new Fernet key
            key = Fernet.generate_key()
            key_id = secrets.token_hex(16)
            
            # Store the key
            self._encryption_keys[key_id] = key
            self._current_key_id = key_id
            
            # Save keys to encrypted storage
            self._save_encryption_keys()
            self._save_encryption_metadata()
            
            logger.info(f"Generated new encryption key: {key_id}")
            return key_id
            
        except Exception as e:
            logger.error(f"Failed to generate encryption key: {e}")
            raise EncryptionError(f"Failed to generate encryption key: {e}")

    def _save_encryption_keys(self) -> None:
        """Save encryption keys to encrypted storage"""
        if not self.security_service:
            logger.warning("No security service available for key storage")
            return
            
        try:
            # Use credential manager to encrypt and store keys
            credential_manager = self.security_service.credential_manager
            
            # Serialize keys to JSON
            keys_data = {
                key_id: base64.b64encode(key).decode('utf-8')
                for key_id, key in self._encryption_keys.items()
            }
            
            # Store as a special credential
            credential_manager.store_repository_password(
                "timelocker_config_encryption_keys",
                json.dumps(keys_data)
            )
            
        except Exception as e:
            logger.error(f"Failed to save encryption keys: {e}")
            raise EncryptionError(f"Failed to save encryption keys: {e}")

    def _load_encryption_keys(self) -> None:
        """Load encryption keys from encrypted storage"""
        if not self.security_service:
            return
            
        try:
            credential_manager = self.security_service.credential_manager
            
            # Retrieve keys from credential manager
            keys_json = credential_manager.get_repository_password(
                "timelocker_config_encryption_keys"
            )
            
            if keys_json:
                keys_data = json.loads(keys_json)
                self._encryption_keys = {
                    key_id: base64.b64decode(key_b64.encode('utf-8'))
                    for key_id, key_b64 in keys_data.items()
                }
                
        except Exception as e:
            logger.warning(f"Failed to load encryption keys: {e}")

    def _get_encryption_key(self, key_id: Optional[str] = None) -> bytes:
        """
        Get encryption key by ID or current key.
        
        Args:
            key_id: Key identifier, uses current key if None
            
        Returns:
            bytes: Encryption key
        """
        if key_id is None:
            key_id = self._current_key_id
            
        if key_id is None or key_id not in self._encryption_keys:
            # Generate new key if none exists
            if not self._encryption_keys:
                self._generate_encryption_key()
                key_id = self._current_key_id
            else:
                raise EncryptionError(f"Encryption key not found: {key_id}")
                
        return self._encryption_keys[key_id]

    def is_sensitive_key(self, key: str) -> bool:
        """
        Check if a configuration key contains sensitive data.
        
        Args:
            key: Configuration key to check
            
        Returns:
            bool: True if key is considered sensitive
        """
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in self.sensitive_patterns)

    def encrypt_value(self, value: Any, key_path: str) -> Dict[str, Any]:
        """
        Encrypt a configuration value if it's sensitive.
        
        Args:
            value: Value to potentially encrypt
            key_path: Configuration key path for sensitivity detection
            
        Returns:
            Dict containing encrypted value and metadata
        """
        if not self.security_service:
            logger.warning("No security service available for encryption")
            return {"value": value, "encrypted": False}
            
        # Only encrypt sensitive string values
        if not isinstance(value, str) or not self.is_sensitive_key(key_path):
            return {"value": value, "encrypted": False}
            
        try:
            # Get encryption key
            key = self._get_encryption_key()
            fernet = Fernet(key)
            
            # Encrypt the value
            encrypted_value = fernet.encrypt(value.encode('utf-8'))
            encrypted_b64 = base64.b64encode(encrypted_value).decode('utf-8')
            
            # Create metadata
            metadata = EncryptionMetadata(
                encrypted=True,
                algorithm="Fernet-AES256",
                key_id=self._current_key_id,
                created_at=datetime.now()
            )
            
            # Log encryption event
            if self.security_service:
                from ..security.security_service import SecurityEvent, SecurityLevel
                self.security_service.log_security_event(
                    SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="configuration_encryption",
                        level=SecurityLevel.MEDIUM,
                        description=f"Configuration value encrypted: {key_path}",
                        metadata={
                            "key_path": key_path,
                            "algorithm": metadata.algorithm,
                            "key_id": metadata.key_id
                        }
                    )
                )
            
            return {
                "value": encrypted_b64,
                "encrypted": True,
                "metadata": {
                    "algorithm": metadata.algorithm,
                    "key_id": metadata.key_id,
                    "created_at": metadata.created_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt configuration value: {e}")
            raise EncryptionError(f"Failed to encrypt configuration value: {e}")

    def decrypt_value(self, encrypted_data: Dict[str, Any]) -> Any:
        """
        Decrypt an encrypted configuration value.
        
        Args:
            encrypted_data: Dictionary containing encrypted value and metadata
            
        Returns:
            Decrypted value
        """
        if not encrypted_data.get("encrypted", False):
            return encrypted_data.get("value")
            
        if not self.security_service:
            raise EncryptionError("No security service available for decryption")
            
        try:
            metadata = encrypted_data.get("metadata", {})
            key_id = metadata.get("key_id")
            
            # Get decryption key
            key = self._get_encryption_key(key_id)
            fernet = Fernet(key)
            
            # Decrypt the value
            encrypted_b64 = encrypted_data["value"]
            encrypted_bytes = base64.b64decode(encrypted_b64.encode('utf-8'))
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            decrypted_value = decrypted_bytes.decode('utf-8')
            
            # Update access metadata
            if self.security_service:
                from ..security.security_service import SecurityEvent, SecurityLevel
                self.security_service.log_security_event(
                    SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="configuration_decryption",
                        level=SecurityLevel.LOW,
                        description="Configuration value decrypted",
                        metadata={
                            "key_id": key_id,
                            "algorithm": metadata.get("algorithm")
                        }
                    )
                )
            
            return decrypted_value
            
        except Exception as e:
            logger.error(f"Failed to decrypt configuration value: {e}")
            raise EncryptionError(f"Failed to decrypt configuration value: {e}")

    def sign_configuration(self, config_data: Dict[str, Any]) -> ConfigurationSignature:
        """
        Create digital signature for configuration data.
        
        Args:
            config_data: Configuration data to sign
            
        Returns:
            ConfigurationSignature object
        """
        try:
            # Create deterministic JSON representation
            config_json = json.dumps(config_data, sort_keys=True, separators=(',', ':'))
            
            # Calculate checksum
            checksum = hashlib.sha256(config_json.encode('utf-8')).hexdigest()
            
            # Create signature using HMAC with current encryption key
            if self._current_key_id:
                key = self._get_encryption_key()
                signature_data = f"{checksum}:{datetime.now().isoformat()}"
                signature = hashlib.pbkdf2_hmac(
                    'sha256',
                    signature_data.encode('utf-8'),
                    key[:32],  # Use first 32 bytes as salt
                    100000
                ).hex()
            else:
                # Fallback to simple checksum if no encryption key
                signature = checksum
            
            config_signature = ConfigurationSignature(
                signature=signature,
                algorithm="PBKDF2-HMAC-SHA256",
                timestamp=datetime.now(),
                sections=list(config_data.keys()),
                checksum=checksum
            )
            
            # Save signature
            self._save_signature(config_signature)
            
            # Log signing event
            if self.security_service:
                from ..security.security_service import SecurityEvent, SecurityLevel
                self.security_service.log_security_event(
                    SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="configuration_signing",
                        level=SecurityLevel.MEDIUM,
                        description="Configuration signed for integrity verification",
                        metadata={
                            "sections": len(config_signature.sections),
                            "algorithm": config_signature.algorithm,
                            "checksum": checksum[:16]  # First 16 chars for logging
                        }
                    )
                )
            
            return config_signature
            
        except Exception as e:
            logger.error(f"Failed to sign configuration: {e}")
            raise IntegrityError(f"Failed to sign configuration: {e}")

    def verify_configuration(self, config_data: Dict[str, Any]) -> bool:
        """
        Verify configuration integrity using stored signature.
        
        Args:
            config_data: Configuration data to verify
            
        Returns:
            bool: True if verification passes
        """
        try:
            # Load stored signature
            stored_signature = self._load_signature()
            if not stored_signature:
                logger.warning("No stored signature found for verification")
                return False
            
            # Calculate current checksum
            config_json = json.dumps(config_data, sort_keys=True, separators=(',', ':'))
            current_checksum = hashlib.sha256(config_json.encode('utf-8')).hexdigest()
            
            # Verify checksum matches
            verification_passed = current_checksum == stored_signature.checksum
            
            # Log verification event
            if self.security_service:
                from ..security.security_service import SecurityEvent, SecurityLevel
                self.security_service.log_security_event(
                    SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="configuration_verification",
                        level=SecurityLevel.MEDIUM if verification_passed else SecurityLevel.HIGH,
                        description=f"Configuration integrity verification: {'PASSED' if verification_passed else 'FAILED'}",
                        metadata={
                            "verification_passed": verification_passed,
                            "stored_checksum": stored_signature.checksum[:16],
                            "current_checksum": current_checksum[:16],
                            "signature_timestamp": stored_signature.timestamp.isoformat()
                        }
                    )
                )
            
            return verification_passed
            
        except Exception as e:
            logger.error(f"Failed to verify configuration: {e}")
            return False

    def _save_signature(self, signature: ConfigurationSignature) -> None:
        """Save configuration signature to disk"""
        try:
            signature_data = {
                "signature": signature.signature,
                "algorithm": signature.algorithm,
                "timestamp": signature.timestamp.isoformat(),
                "sections": signature.sections,
                "checksum": signature.checksum
            }
            
            with open(self.signature_file, 'w') as f:
                json.dump(signature_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save signature: {e}")
            raise IntegrityError(f"Failed to save signature: {e}")

    def _load_signature(self) -> Optional[ConfigurationSignature]:
        """Load configuration signature from disk"""
        try:
            if not self.signature_file.exists():
                return None
                
            with open(self.signature_file, 'r') as f:
                signature_data = json.load(f)
                
            return ConfigurationSignature(
                signature=signature_data["signature"],
                algorithm=signature_data["algorithm"],
                timestamp=datetime.fromisoformat(signature_data["timestamp"]),
                sections=signature_data["sections"],
                checksum=signature_data["checksum"]
            )
            
        except Exception as e:
            logger.warning(f"Failed to load signature: {e}")
            return None

    def rotate_encryption_keys(self) -> str:
        """
        Rotate encryption keys for enhanced security.
        
        Returns:
            str: New key identifier
        """
        try:
            old_key_id = self._current_key_id
            new_key_id = self._generate_encryption_key()
            
            # Log key rotation event
            if self.security_service:
                from ..security.security_service import SecurityEvent, SecurityLevel
                self.security_service.log_security_event(
                    SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="key_rotation",
                        level=SecurityLevel.HIGH,
                        description="Configuration encryption keys rotated",
                        metadata={
                            "old_key_id": old_key_id,
                            "new_key_id": new_key_id,
                            "total_keys": len(self._encryption_keys)
                        }
                    )
                )
            
            logger.info(f"Encryption keys rotated: {old_key_id} -> {new_key_id}")
            return new_key_id
            
        except Exception as e:
            logger.error(f"Failed to rotate encryption keys: {e}")
            raise EncryptionError(f"Failed to rotate encryption keys: {e}")

    def get_encryption_status(self) -> Dict[str, Any]:
        """
        Get encryption status and statistics.
        
        Returns:
            Dict containing encryption status information
        """
        return {
            "encryption_enabled": self.security_service is not None,
            "current_key_id": self._current_key_id,
            "total_keys": len(self._encryption_keys),
            "sensitive_patterns": list(self.sensitive_patterns),
            "signature_exists": self.signature_file.exists(),
            "metadata_file_exists": self.encryption_metadata_file.exists()
        }

    def cleanup_old_keys(self, keep_count: int = 3) -> int:
        """
        Clean up old encryption keys while keeping recent ones.
        
        Args:
            keep_count: Number of recent keys to keep
            
        Returns:
            int: Number of keys removed
        """
        if len(self._encryption_keys) <= keep_count:
            return 0
            
        try:
            # Sort keys by creation order (assuming key_id contains timestamp info)
            sorted_keys = sorted(self._encryption_keys.keys())
            keys_to_remove = sorted_keys[:-keep_count]
            
            removed_count = 0
            for key_id in keys_to_remove:
                if key_id != self._current_key_id:  # Never remove current key
                    del self._encryption_keys[key_id]
                    removed_count += 1
            
            if removed_count > 0:
                self._save_encryption_keys()
                self._save_encryption_metadata()
                
                # Log cleanup event
                if self.security_service:
                    from ..security.security_service import SecurityEvent, SecurityLevel
                    self.security_service.log_security_event(
                        SecurityEvent(
                            timestamp=datetime.now(),
                            event_type="key_cleanup",
                            level=SecurityLevel.LOW,
                            description=f"Cleaned up {removed_count} old encryption keys",
                            metadata={
                                "removed_count": removed_count,
                                "remaining_count": len(self._encryption_keys)
                            }
                        )
                    )
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old keys: {e}")
            return 0