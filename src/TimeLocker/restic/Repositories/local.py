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
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any

from ..logging import logger
from ..restic_repository import RepositoryError, ResticRepository
from ...security import CredentialManager


class LocalResticRepository(ResticRepository):
    def __init__(self, location: str, password: Optional[str] = None,
                 credential_manager: Optional[CredentialManager] = None,
                 repository_name: Optional[str] = None, **kwargs):
        """
        Initialize local restic repository.

        Args:
            location: Local filesystem path for the repository
            password: Repository password for encryption
            credential_manager: CredentialManager instance for retrieving stored credentials
            repository_name: Repository name for per-repository credential lookup from credential manager.
                           For local repositories, this is primarily used for password storage/retrieval.
            **kwargs: Additional parameters passed to parent class
        """
        # Local repositories don't have backend-specific credentials like S3/B2,
        # but we accept repository_name for consistency and password management
        super().__init__(location, password=password, credential_manager=credential_manager, **kwargs)

    @classmethod
    def from_parsed_uri(cls, parsed_uri, password: Optional[str] = None, **kwargs) -> 'LocalResticRepository':
        if hasattr(parsed_uri, "netloc") and parsed_uri.netloc:
            raise ValueError("parsed_uri must not have a 'netloc' attribute value for a local repository.")

        if not hasattr(parsed_uri, "path") or (hasattr(parsed_uri, "path") and not parsed_uri.path):
            raise ValueError("parsed_uri must have a 'path' attribute value set")

        # Generate the absolute path
        path = os.path.abspath(parsed_uri.path)

        # Return the initialized LocalRepository instance with all kwargs
        return cls(location=path, password=password, **kwargs)

    def backend_env(self) -> Dict[str, str]:
        return {}

    def validate(self):
        logger.info(f"Validating local repository path: {self._location}")
        try:
            # Check if parent directory exists and is writable
            parent_dir = os.path.dirname(self._location)
            if not os.path.exists(parent_dir):
                raise RepositoryError(f"Parent directory does not exist: {parent_dir}")

            if not os.access(parent_dir, os.W_OK):
                raise RepositoryError(f"Parent directory is not writable: {parent_dir}")

            # If repository directory doesn't exist, that's OK - we can create it during init
            if os.path.exists(self._location):
                if not os.path.isdir(self._location):
                    raise RepositoryError(f"Path exists but is not a directory: {self._location}")

                # Check if it's already a restic repository
                if os.path.exists(os.path.join(self._location, "config")):
                    logger.info("Existing restic repository detected")
                else:
                    logger.info("Directory exists but is not a restic repository")
            else:
                logger.info("Repository directory will be created during initialization")

        except OSError as e:
            raise RepositoryError(f"Error accessing local repository: {e}")

    def create_repository_directory(self) -> bool:
        """Create the repository directory if it doesn't exist"""
        try:
            if not os.path.exists(self._location):
                os.makedirs(self._location, exist_ok=True)
                logger.info(f"Created repository directory: {self._location}")
            return True
        except OSError as e:
            logger.error(f"Failed to create repository directory: {e}")
            return False

    def initialize_repository(self, password: Optional[str] = None) -> bool:
        """
        Initialize a new restic repository with enhanced error handling

        Args:
            password: Optional password to use for initialization. If not provided,
                     uses the repository's configured password

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Ensure directory exists
            if not self.create_repository_directory():
                return False

            # Use provided password or fall back to configured password
            if password:
                original_password = self._explicit_password
                self._explicit_password = password
                # Clear cached environment to force regeneration with new password
                self._cached_env = None

            try:
                # Check if repository is already initialized
                if self.is_repository_initialized():
                    logger.warning(f"Repository at {self._location} is already initialized")
                    return True

                # Initialize the repository
                result = self.initialize()

                if result and password:
                    # Store the password in credential manager if available
                    self.store_password(password)

                return result

            finally:
                # Restore original password if we changed it
                if password:
                    self._explicit_password = original_password
                    self._cached_env = None

        except Exception as e:
            logger.error(f"Failed to initialize repository: {e}")
            return False

    def is_repository_initialized(self) -> bool:
        """
        Check if the repository is already initialized

        Returns:
            bool: True if repository is initialized, False otherwise
        """
        try:
            config_file = os.path.join(self._location, "config")
            return os.path.exists(config_file) and os.path.isfile(config_file)
        except Exception as e:
            logger.error(f"Error checking repository initialization status: {e}")
            return False

    def get_repository_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the repository

        Returns:
            Dict containing repository information
        """
        info = {
                "location":         self._location,
                "type":             "local",
                "repository_id":    self.repository_id(),
                "initialized":      self.is_repository_initialized(),
                "directory_exists": os.path.exists(self._location),
                "writable":         False,
                "size_bytes":       0,
                "config":           {}
        }

        try:
            # Check if directory is writable
            if os.path.exists(self._location):
                info["writable"] = os.access(self._location, os.W_OK)

                # Get directory size
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(self._location):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, IOError):
                            continue
                info["size_bytes"] = total_size

                # Get repository config if available
                if self.is_repository_initialized():
                    try:
                        config_file = os.path.join(self._location, "config")
                        if os.path.exists(config_file):
                            with open(config_file, 'r') as f:
                                config_content = f.read()
                                # Try to parse as JSON, fall back to raw content
                                try:
                                    info["config"] = json.loads(config_content)
                                except json.JSONDecodeError:
                                    info["config"] = {"raw": config_content}
                    except Exception as e:
                        logger.warning(f"Could not read repository config: {e}")

        except Exception as e:
            logger.error(f"Error gathering repository information: {e}")

        return info

    def validate_repository_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive repository health validation

        Returns:
            Dict containing validation results and any issues found
        """
        health_report = {
                "healthy":  True,
                "issues":   [],
                "warnings": [],
                "checks":   {
                        "directory_exists":       False,
                        "directory_writable":     False,
                        "repository_initialized": False,
                        "password_available":     False,
                        "restic_accessible":      False
                }
        }

        try:
            # Check directory existence
            if os.path.exists(self._location):
                health_report["checks"]["directory_exists"] = True

                # Check if directory is writable
                if os.access(self._location, os.W_OK):
                    health_report["checks"]["directory_writable"] = True
                else:
                    health_report["issues"].append("Repository directory is not writable")
                    health_report["healthy"] = False
            else:
                health_report["issues"].append("Repository directory does not exist")
                health_report["healthy"] = False

            # Check repository initialization
            if self.is_repository_initialized():
                health_report["checks"]["repository_initialized"] = True
            else:
                health_report["warnings"].append("Repository is not initialized")

            # Check password availability
            try:
                password = self.password()
                if password:
                    health_report["checks"]["password_available"] = True
                else:
                    health_report["issues"].append("No repository password available")
                    health_report["healthy"] = False
            except Exception as e:
                health_report["issues"].append(f"Error accessing password: {e}")
                health_report["healthy"] = False

            # Check restic accessibility (if repository is initialized)
            if health_report["checks"]["repository_initialized"] and health_report["checks"]["password_available"]:
                try:
                    # Try a simple repository check
                    check_result = self.check()
                    health_report["checks"]["restic_accessible"] = check_result
                    if not check_result:
                        health_report["issues"].append("Repository check failed - repository may be corrupted")
                        health_report["healthy"] = False
                except Exception as e:
                    health_report["issues"].append(f"Repository accessibility check failed: {e}")
                    health_report["healthy"] = False

        except Exception as e:
            health_report["issues"].append(f"Health validation failed: {e}")
            health_report["healthy"] = False

        return health_report

    def setup_repository_with_credentials(self, password: str,
                                          credential_manager: Optional[CredentialManager] = None) -> bool:
        """
        Complete repository setup including initialization and credential storage

        Args:
            password: Repository password to use
            credential_manager: Optional credential manager for secure storage

        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            logger.info(f"Setting up repository at {self._location}")

            # Set credential manager if provided
            if credential_manager:
                self._credential_manager = credential_manager

            # Initialize repository with password
            if not self.initialize_repository(password):
                logger.error("Failed to initialize repository")
                return False

            # Verify repository health
            health = self.validate_repository_health()
            if not health["healthy"]:
                logger.error(f"Repository health check failed: {health['issues']}")
                return False

            logger.info("Repository setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Repository setup failed: {e}")
            return False

    def get_common_repository_issues(self) -> Dict[str, str]:
        """
        Get common repository issues and their solutions

        Returns:
            Dict mapping issue descriptions to suggested solutions
        """
        return {
                "Permission denied":          "Check that the user has read/write permissions to the repository directory",
                "Directory not found":        "Ensure the parent directory exists and create the repository directory",
                "Repository not initialized": "Run repository initialization before performing backup operations",
                "Password not available":     "Set RESTIC_PASSWORD environment variable or store password in credential manager",
                "Repository locked":          "Another restic process may be running. Wait or remove lock file if process is dead",
                "Repository corrupted":       "Run 'restic check' to verify repository integrity and 'restic repair' if needed",
                "Insufficient disk space":    "Free up disk space or choose a different repository location",
                "Network connectivity":       "For remote repositories, check network connection and credentials"
        }
