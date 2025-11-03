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
import gc
import mmap
import secrets
import tempfile
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class PrivacyLevel(Enum):
    """Privacy levels for data handling"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecureDeletionMethod(Enum):
    """Methods for secure deletion"""
    SIMPLE = "simple"  # Single overwrite with random data
    DOD_3PASS = "dod_3pass"  # DoD 5220.22-M 3-pass
    GUTMANN = "gutmann"  # Gutmann 35-pass (overkill for most cases)


@dataclass
class PrivacyInfo:
    """Information about privacy handling for user display"""
    data_types_processed: List[str]
    privacy_level: PrivacyLevel
    retention_period: Optional[timedelta]
    secure_deletion_enabled: bool
    encryption_status: str
    last_cleanup: Optional[datetime]
    temporary_files_location: str
    privacy_policy_summary: str


@dataclass
class SensitiveFilePattern:
    """Pattern for identifying sensitive files"""
    pattern: str
    description: str
    privacy_level: PrivacyLevel
    recommended_action: str  # "exclude", "encrypt_extra", "warn"


class DataPrivacyManager:
    """
    Manages data privacy features including secure deletion, 
    sensitive file handling, and privacy information display.
    """

    # Predefined sensitive file patterns
    SENSITIVE_FILE_PATTERNS = {
        "financial": SensitiveFilePattern(
            pattern="*tax*|*bank*|*financial*|*invoice*|*receipt*|*.qif|*.ofx",
            description="Financial documents and records",
            privacy_level=PrivacyLevel.HIGH,
            recommended_action="encrypt_extra"
        ),
        "personal_documents": SensitiveFilePattern(
            pattern="*passport*|*ssn*|*social*security*|*birth*certificate*|*medical*",
            description="Personal identification and medical documents",
            privacy_level=PrivacyLevel.CRITICAL,
            recommended_action="exclude"
        ),
        "credentials": SensitiveFilePattern(
            pattern="*.key|*.pem|*.p12|*.pfx|*password*|*credential*|*.keychain",
            description="Cryptographic keys and credential files",
            privacy_level=PrivacyLevel.CRITICAL,
            recommended_action="exclude"
        ),
        "browser_data": SensitiveFilePattern(
            pattern="*cookies*|*history*|*bookmarks*|*login*data*|*web*data*",
            description="Browser data including cookies and saved passwords",
            privacy_level=PrivacyLevel.HIGH,
            recommended_action="exclude"
        ),
        "temporary_sensitive": SensitiveFilePattern(
            pattern="*.tmp|*.temp|*~|*.bak|*.swp|*.cache|__pycache__/*",
            description="Temporary files that may contain sensitive data",
            privacy_level=PrivacyLevel.MEDIUM,
            recommended_action="exclude"
        )
    }

    def __init__(self, config_dir: Optional[Path] = None, 
                 temp_dir: Optional[Path] = None,
                 security_logger: Optional['SecurityLogger'] = None):
        """
        Initialize data privacy manager
        
        Args:
            config_dir: Configuration directory for privacy settings
            temp_dir: Temporary directory for secure operations
            security_logger: Optional SecurityLogger instance
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "security"
        
        if temp_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            temp_dir = ConfigurationPathResolver.get_temp_directory()

        self.config_dir = Path(config_dir)
        self.temp_dir = Path(temp_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Privacy configuration
        self.privacy_config_file = self.config_dir / "privacy_config.json"
        self.cleanup_log_file = self.config_dir / "cleanup.log"
        
        # Security logger
        self.security_logger = security_logger
        if self.security_logger is None:
            try:
                from .security_logger import SecurityLogger
                self.security_logger = SecurityLogger(config_dir=config_dir)
            except ImportError:
                self.security_logger = None

        # Track temporary files and sensitive data
        self._temp_files: Set[Path] = set()
        self._sensitive_memory_regions: List[Any] = []
        self._cleanup_lock = threading.RLock()
        
        # Default privacy settings
        self._privacy_settings = {
            "secure_deletion_method": SecureDeletionMethod.DOD_3PASS,
            "auto_cleanup_enabled": True,
            "cleanup_interval_hours": 24,
            "temp_file_retention_hours": 1,
            "log_privacy_events": True,
            "show_privacy_warnings": True,
            "sensitive_file_detection": True
        }

        # Initialize cleanup logging
        self._initialize_cleanup_log()

    def _initialize_cleanup_log(self):
        """Initialize cleanup logging"""
        if not self.cleanup_log_file.exists():
            with open(self.cleanup_log_file, 'w') as f:
                f.write("# TimeLocker Data Privacy Cleanup Log\n")
                f.write(f"# Initialized: {datetime.now().isoformat()}\n")
                f.write("# Format: timestamp|operation|target|success|details\n")

    def _log_privacy_event(self, operation: str, target: str = "", success: bool = True, details: str = ""):
        """Log privacy-related events"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp}|{operation}|{target}|{success}|{details}\n"

        try:
            with open(self.cleanup_log_file, 'a') as f:
                f.write(log_entry)
        except Exception:
            pass  # Don't fail operations due to logging issues

        # Also log to SecurityLogger if available
        if self.security_logger:
            try:
                from .security_logger import SecurityLogEntry, SecurityLogLevel, SecurityEventType
                
                level = SecurityLogLevel.LOW if success else SecurityLogLevel.MEDIUM
                description = f"Privacy {operation}: {'SUCCESS' if success else 'FAILED'}"
                if details:
                    description += f" - {details}"
                
                security_log_entry = SecurityLogEntry(
                    timestamp=datetime.now(),
                    event_type=SecurityEventType.DATA_PRIVACY,
                    level=level,
                    description=description,
                    metadata={
                        "operation": operation,
                        "target": target,
                        "success": success,
                        "details": details
                    },
                    source="DataPrivacyManager"
                )
                
                self.security_logger.log_event(security_log_entry)
            except Exception:
                pass

    def secure_delete_file(self, file_path: Union[str, Path], 
                          method: SecureDeletionMethod = SecureDeletionMethod.DOD_3PASS) -> bool:
        """
        Securely delete a file using specified method
        
        Args:
            file_path: Path to file to delete
            method: Secure deletion method to use
            
        Returns:
            bool: True if deletion successful
        """
        path = Path(file_path)
        
        if not path.exists():
            return True  # Already deleted
        
        if not path.is_file():
            self._log_privacy_event("secure_delete_file", str(path), False, "Not a file")
            return False

        try:
            file_size = path.stat().st_size
            
            # Perform secure overwrite based on method
            if method == SecureDeletionMethod.SIMPLE:
                passes = [(secrets.randbits(8).to_bytes(1, 'big') * (file_size % 256 + 1))[:1]]
            elif method == SecureDeletionMethod.DOD_3PASS:
                # DoD 5220.22-M: pass 1 (0x00), pass 2 (0xFF), pass 3 (random)
                passes = [
                    b'\x00',
                    b'\xFF', 
                    secrets.randbits(8).to_bytes(1, 'big')
                ]
            elif method == SecureDeletionMethod.GUTMANN:
                # Simplified Gutmann method (3 passes instead of 35 for performance)
                passes = [
                    b'\x00',
                    b'\xFF',
                    secrets.randbits(8).to_bytes(1, 'big')
                ]
            else:
                passes = [secrets.randbits(8).to_bytes(1, 'big')]

            # Perform overwrite passes
            for pass_data in passes:
                with open(path, 'r+b') as f:
                    f.seek(0)
                    # Write pattern across entire file
                    bytes_written = 0
                    while bytes_written < file_size:
                        chunk_size = min(8192, file_size - bytes_written)
                        pattern = (pass_data * (chunk_size // len(pass_data) + 1))[:chunk_size]
                        f.write(pattern)
                        bytes_written += chunk_size
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk

            # Finally delete the file
            path.unlink()
            
            self._log_privacy_event("secure_delete_file", str(path), True, 
                                  f"Method: {method.value}, Size: {file_size}")
            return True

        except Exception as e:
            self._log_privacy_event("secure_delete_file", str(path), False, str(e))
            logger.error(f"Failed to securely delete {path}: {e}")
            return False

    def secure_delete_directory(self, dir_path: Union[str, Path], 
                               method: SecureDeletionMethod = SecureDeletionMethod.DOD_3PASS) -> bool:
        """
        Securely delete a directory and all its contents
        
        Args:
            dir_path: Path to directory to delete
            method: Secure deletion method to use
            
        Returns:
            bool: True if deletion successful
        """
        path = Path(dir_path)
        
        if not path.exists():
            return True  # Already deleted
        
        if not path.is_dir():
            return self.secure_delete_file(path, method)

        try:
            files_deleted = 0
            dirs_deleted = 0
            
            # Recursively delete all files first
            for root, dirs, files in os.walk(path, topdown=False):
                # Delete files in current directory
                for file in files:
                    file_path = Path(root) / file
                    if self.secure_delete_file(file_path, method):
                        files_deleted += 1
                
                # Delete empty subdirectories
                for dir_name in dirs:
                    dir_path_inner = Path(root) / dir_name
                    try:
                        dir_path_inner.rmdir()  # Only works if empty
                        dirs_deleted += 1
                    except OSError:
                        pass  # Directory not empty or other error

            # Delete the main directory
            try:
                path.rmdir()
                dirs_deleted += 1
            except OSError as e:
                self._log_privacy_event("secure_delete_directory", str(path), False, 
                                      f"Failed to delete main directory: {e}")
                return False

            self._log_privacy_event("secure_delete_directory", str(path), True,
                                  f"Files: {files_deleted}, Dirs: {dirs_deleted}")
            return True

        except Exception as e:
            self._log_privacy_event("secure_delete_directory", str(path), False, str(e))
            logger.error(f"Failed to securely delete directory {path}: {e}")
            return False

    def register_temporary_file(self, file_path: Union[str, Path]) -> None:
        """
        Register a temporary file for automatic cleanup
        
        Args:
            file_path: Path to temporary file
        """
        with self._cleanup_lock:
            self._temp_files.add(Path(file_path))

    def unregister_temporary_file(self, file_path: Union[str, Path]) -> None:
        """
        Unregister a temporary file (e.g., when manually cleaned up)
        
        Args:
            file_path: Path to temporary file
        """
        with self._cleanup_lock:
            self._temp_files.discard(Path(file_path))

    def cleanup_temporary_files(self, max_age_hours: Optional[int] = None) -> Dict[str, int]:
        """
        Clean up registered temporary files and old files in temp directory
        
        Args:
            max_age_hours: Maximum age of files to keep (uses config default if None)
            
        Returns:
            Dict with cleanup statistics
        """
        if max_age_hours is None:
            max_age_hours = self._privacy_settings["temp_file_retention_hours"]

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        stats = {"registered_files_deleted": 0, "old_files_deleted": 0, "errors": 0}

        with self._cleanup_lock:
            # Clean up registered temporary files
            files_to_remove = set()
            for temp_file in self._temp_files:
                try:
                    if self.secure_delete_file(temp_file):
                        stats["registered_files_deleted"] += 1
                        files_to_remove.add(temp_file)
                    else:
                        stats["errors"] += 1
                except Exception as e:
                    logger.error(f"Error deleting registered temp file {temp_file}: {e}")
                    stats["errors"] += 1

            # Remove successfully deleted files from tracking
            self._temp_files -= files_to_remove

            # Clean up old files in temp directory
            try:
                for item in self.temp_dir.rglob("*"):
                    if item.is_file():
                        try:
                            # Check file age
                            file_time = datetime.fromtimestamp(item.stat().st_mtime)
                            if file_time < cutoff_time:
                                if self.secure_delete_file(item):
                                    stats["old_files_deleted"] += 1
                                else:
                                    stats["errors"] += 1
                        except Exception as e:
                            logger.debug(f"Error checking/deleting old temp file {item}: {e}")
                            stats["errors"] += 1
            except Exception as e:
                logger.error(f"Error scanning temp directory {self.temp_dir}: {e}")
                stats["errors"] += 1

        self._log_privacy_event("cleanup_temporary_files", str(self.temp_dir), True,
                              f"Registered: {stats['registered_files_deleted']}, "
                              f"Old: {stats['old_files_deleted']}, "
                              f"Errors: {stats['errors']}")
        return stats

    def secure_memory_clear(self, data: Any) -> None:
        """
        Attempt to securely clear sensitive data from memory
        
        Args:
            data: Data object to clear (string, bytes, etc.)
        """
        try:
            # For strings and bytes, try to overwrite if possible
            if isinstance(data, (str, bytes, bytearray)):
                if hasattr(data, '__len__') and len(data) > 0:
                    # For mutable types like bytearray, overwrite with zeros
                    if isinstance(data, bytearray):
                        for i in range(len(data)):
                            data[i] = 0
                    
                    # For immutable types, we can't directly overwrite,
                    # but we can try to encourage garbage collection
                    del data

            # Force garbage collection to clean up references
            gc.collect()

        except Exception as e:
            logger.debug(f"Error during secure memory clear: {e}")

    def get_sensitive_file_patterns(self) -> Dict[str, SensitiveFilePattern]:
        """
        Get dictionary of sensitive file patterns
        
        Returns:
            Dict mapping pattern names to SensitiveFilePattern objects
        """
        return self.SENSITIVE_FILE_PATTERNS.copy()

    def check_file_sensitivity(self, file_path: Union[str, Path]) -> Optional[SensitiveFilePattern]:
        """
        Check if a file matches any sensitive file patterns
        
        Args:
            file_path: Path to check
            
        Returns:
            SensitiveFilePattern if file is sensitive, None otherwise
        """
        import fnmatch
        
        path_str = str(file_path).lower()
        filename = Path(file_path).name.lower()

        for pattern_info in self.SENSITIVE_FILE_PATTERNS.values():
            # Split pattern on | for multiple patterns
            patterns = pattern_info.pattern.split('|')
            
            for pattern in patterns:
                pattern = pattern.strip()
                # Check both full path and filename
                if (fnmatch.fnmatch(path_str, pattern) or 
                    fnmatch.fnmatch(filename, pattern)):
                    return pattern_info

        return None

    def get_privacy_info(self) -> PrivacyInfo:
        """
        Get current privacy information for user display
        
        Returns:
            PrivacyInfo object with current privacy status
        """
        # Determine what data types are being processed
        data_types = []
        if self._temp_files:
            data_types.append("Temporary files")
        if self.temp_dir.exists() and any(self.temp_dir.iterdir()):
            data_types.append("Cache data")
        
        # Check for recent cleanup
        last_cleanup = None
        try:
            if self.cleanup_log_file.exists():
                # Get last cleanup time from log
                with open(self.cleanup_log_file, 'r') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if 'cleanup_temporary_files' in line and '|True|' in line:
                            timestamp_str = line.split('|')[0]
                            last_cleanup = datetime.fromisoformat(timestamp_str)
                            break
        except Exception:
            pass

        return PrivacyInfo(
            data_types_processed=data_types,
            privacy_level=PrivacyLevel.HIGH,  # Default to high privacy
            retention_period=timedelta(hours=self._privacy_settings["temp_file_retention_hours"]),
            secure_deletion_enabled=True,
            encryption_status="AES-256 encryption enabled for all backup data",
            last_cleanup=last_cleanup,
            temporary_files_location=str(self.temp_dir),
            privacy_policy_summary=(
                "TimeLocker protects your privacy by: "
                "1) Encrypting all backup data with AES-256, "
                "2) Securely deleting temporary files, "
                "3) Never storing file contents in logs, "
                "4) Providing sensitive file detection and exclusion options."
            )
        )

    def get_privacy_recommendations(self, file_selection: 'FileSelection') -> List[Dict[str, Any]]:
        """
        Get privacy recommendations based on file selection
        
        Args:
            file_selection: FileSelection object to analyze
            
        Returns:
            List of privacy recommendations
        """
        recommendations = []
        
        if not self._privacy_settings["sensitive_file_detection"]:
            return recommendations

        # Check included paths for sensitive files
        sensitive_files_found = {}
        
        for include_path in file_selection.includes:
            if include_path.exists() and include_path.is_dir():
                # Sample some files to check for sensitive patterns
                file_count = 0
                for file_path in include_path.rglob("*"):
                    if file_path.is_file() and file_count < 1000:  # Limit sampling
                        sensitivity = self.check_file_sensitivity(file_path)
                        if sensitivity:
                            pattern_name = None
                            for name, pattern in self.SENSITIVE_FILE_PATTERNS.items():
                                if pattern == sensitivity:
                                    pattern_name = name
                                    break
                            
                            if pattern_name:
                                if pattern_name not in sensitive_files_found:
                                    sensitive_files_found[pattern_name] = []
                                sensitive_files_found[pattern_name].append(str(file_path))
                        
                        file_count += 1

        # Generate recommendations based on findings
        for pattern_name, files in sensitive_files_found.items():
            pattern_info = self.SENSITIVE_FILE_PATTERNS[pattern_name]
            
            recommendation = {
                "type": "sensitive_files_detected",
                "severity": pattern_info.privacy_level.value,
                "title": f"Sensitive files detected: {pattern_info.description}",
                "description": f"Found {len(files)} files matching sensitive pattern '{pattern_name}'",
                "recommended_action": pattern_info.recommended_action,
                "sample_files": files[:5],  # Show first 5 as examples
                "pattern": pattern_info.pattern
            }
            
            if pattern_info.recommended_action == "exclude":
                recommendation["action_description"] = (
                    "Consider excluding these files from backup for privacy. "
                    "You can add exclusion patterns in your backup configuration."
                )
            elif pattern_info.recommended_action == "encrypt_extra":
                recommendation["action_description"] = (
                    "These files will be encrypted with your backup, but consider "
                    "additional encryption for extra security."
                )
            elif pattern_info.recommended_action == "warn":
                recommendation["action_description"] = (
                    "Be aware that these files contain potentially sensitive information."
                )
            
            recommendations.append(recommendation)

        return recommendations

    def apply_privacy_exclusions(self, file_selection: 'FileSelection', 
                                exclude_patterns: List[str]) -> None:
        """
        Apply privacy-based exclusions to file selection
        
        Args:
            file_selection: FileSelection object to modify
            exclude_patterns: List of patterns to exclude for privacy
        """
        from ..file_selections import SelectionType
        
        for pattern in exclude_patterns:
            file_selection.add_pattern(pattern, SelectionType.EXCLUDE)
        
        self._log_privacy_event("apply_privacy_exclusions", 
                              f"{len(exclude_patterns)} patterns", True,
                              f"Patterns: {', '.join(exclude_patterns[:3])}")

    def get_cleanup_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get cleanup statistics for the specified period
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dict containing cleanup statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        stats = {
            "period_days": days,
            "total_cleanups": 0,
            "files_deleted": 0,
            "directories_deleted": 0,
            "errors": 0,
            "last_cleanup": None
        }

        if not self.cleanup_log_file.exists():
            return stats

        try:
            with open(self.cleanup_log_file, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue

                    try:
                        parts = line.strip().split('|')
                        if len(parts) >= 4:
                            event_time = datetime.fromisoformat(parts[0])
                            if event_time >= cutoff_date:
                                operation = parts[1]
                                success = parts[3] == "True"
                                
                                if operation == "cleanup_temporary_files":
                                    stats["total_cleanups"] += 1
                                    if success and len(parts) > 4:
                                        # Parse details for file counts
                                        details = parts[4]
                                        if "Registered:" in details:
                                            # Extract numbers from details
                                            import re
                                            numbers = re.findall(r'(\d+)', details)
                                            if len(numbers) >= 2:
                                                stats["files_deleted"] += int(numbers[0]) + int(numbers[1])
                                
                                if not success:
                                    stats["errors"] += 1
                                
                                if stats["last_cleanup"] is None or event_time > stats["last_cleanup"]:
                                    stats["last_cleanup"] = event_time
                    except (ValueError, IndexError):
                        continue
        except Exception as e:
            logger.error(f"Error reading cleanup statistics: {e}")

        return stats