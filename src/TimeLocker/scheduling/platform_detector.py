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

Platform Detection System

This module provides automatic detection of available platform schedulers
and selects the most appropriate scheduler for the current system.
"""

import platform
import subprocess
from pathlib import Path
from typing import Type, List, Dict, Any
import logging

from .scheduling_exceptions import UnsupportedPlatformError

logger = logging.getLogger(__name__)


class PlatformDetector:
    """
    Detects platform capabilities and selects appropriate scheduler adapter.
    
    This class provides static methods to detect available schedulers on the
    current platform and select the best option based on system capabilities.
    """
    
    @staticmethod
    def detect_best_scheduler() -> Type['PlatformAdapter']:
        """
        Detect the best available scheduler for the current platform.
        
        Returns:
            Type[PlatformAdapter]: The most appropriate adapter class
            
        Raises:
            UnsupportedPlatformError: If no supported scheduler is found
        """
        system = platform.system().lower()
        
        logger.info(f"Detecting scheduler for platform: {system}")
        
        if system == "linux":
            return PlatformDetector._detect_linux_scheduler()
        elif system == "darwin":
            return PlatformDetector._detect_macos_scheduler()
        elif system == "windows":
            return PlatformDetector._detect_windows_scheduler()
        else:
            raise UnsupportedPlatformError(
                f"Platform {system} is not supported",
                details={"platform": system}
            )
    
    @staticmethod
    def _detect_linux_scheduler() -> Type['PlatformAdapter']:
        """
        Detect best scheduler for Linux systems.
        
        Preference order: systemd > cron
        
        Returns:
            Type[PlatformAdapter]: Best available Linux scheduler adapter
            
        Raises:
            UnsupportedPlatformError: If no supported scheduler is found
        """
        # Import here to avoid circular dependencies
        from .systemd_adapter import SystemdAdapter
        from .cron_adapter import CronAdapter
        
        if PlatformDetector._has_systemd():
            logger.info("Detected systemd scheduler")
            return SystemdAdapter
        elif PlatformDetector._has_cron():
            logger.info("Detected cron scheduler")
            return CronAdapter
        else:
            raise UnsupportedPlatformError(
                "No supported scheduler found on Linux system",
                details={"platform": "linux", "checked": ["systemd", "cron"]}
            )
    
    @staticmethod
    def _detect_macos_scheduler() -> Type['PlatformAdapter']:
        """
        Detect best scheduler for macOS systems.
        
        Preference order: launchd > cron
        
        Returns:
            Type[PlatformAdapter]: Best available macOS scheduler adapter
            
        Raises:
            UnsupportedPlatformError: If no supported scheduler is found
        """
        # Import here to avoid circular dependencies
        from .launchd_adapter import LaunchdAdapter
        from .cron_adapter import CronAdapter
        
        if PlatformDetector._has_launchd():
            logger.info("Detected launchd scheduler")
            return LaunchdAdapter
        elif PlatformDetector._has_cron():
            logger.info("Detected cron scheduler")
            return CronAdapter
        else:
            raise UnsupportedPlatformError(
                "No supported scheduler found on macOS system",
                details={"platform": "darwin", "checked": ["launchd", "cron"]}
            )
    
    @staticmethod
    def _detect_windows_scheduler() -> Type['PlatformAdapter']:
        """
        Detect scheduler for Windows systems.
        
        Returns:
            Type[PlatformAdapter]: Windows Task Scheduler adapter
            
        Raises:
            UnsupportedPlatformError: If Task Scheduler is not available
        """
        # Import here to avoid circular dependencies
        from .windows_adapter import WindowsTaskSchedulerAdapter
        
        if PlatformDetector._has_task_scheduler():
            logger.info("Detected Windows Task Scheduler")
            return WindowsTaskSchedulerAdapter
        else:
            raise UnsupportedPlatformError(
                "Windows Task Scheduler not available",
                details={"platform": "windows"}
            )
    
    @staticmethod
    def _has_systemd() -> bool:
        """
        Check if systemd is available and user services are supported.
        
        Returns:
            bool: True if systemd user services are available
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "status"],
                capture_output=True,
                timeout=5,
                text=True
            )
            # systemctl returns 0 for success, even if no services are running
            available = result.returncode == 0
            if available:
                logger.debug("systemd user services are available")
            else:
                logger.debug(f"systemd check failed: {result.stderr}")
            return available
        except subprocess.TimeoutExpired:
            logger.debug("systemd check timed out")
            return False
        except FileNotFoundError:
            logger.debug("systemctl command not found")
            return False
        except Exception as e:
            logger.debug(f"systemd check failed with exception: {e}")
            return False
    
    @staticmethod
    def _has_cron() -> bool:
        """
        Check if cron is available.
        
        Returns:
            bool: True if cron is available
        """
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                timeout=5,
                text=True
            )
            # crontab returns 0 if has entries, 1 if no entries (both are valid)
            available = result.returncode in [0, 1]
            if available:
                logger.debug("cron is available")
            else:
                logger.debug(f"cron check failed: {result.stderr}")
            return available
        except subprocess.TimeoutExpired:
            logger.debug("cron check timed out")
            return False
        except FileNotFoundError:
            logger.debug("crontab command not found")
            return False
        except Exception as e:
            logger.debug(f"cron check failed with exception: {e}")
            return False
    
    @staticmethod
    def _has_launchd() -> bool:
        """
        Check if launchd is available.
        
        Returns:
            bool: True if launchd is available
        """
        launchctl_path = Path("/bin/launchctl")
        available = launchctl_path.exists()
        if available:
            logger.debug("launchd is available")
        else:
            logger.debug("launchctl not found at /bin/launchctl")
        return available
    
    @staticmethod
    def _has_task_scheduler() -> bool:
        """
        Check if Windows Task Scheduler is available.
        
        Returns:
            bool: True if Task Scheduler is available
        """
        try:
            result = subprocess.run(
                ["schtasks", "/query"],
                capture_output=True,
                timeout=5,
                text=True
            )
            available = result.returncode == 0
            if available:
                logger.debug("Windows Task Scheduler is available")
            else:
                logger.debug(f"Task Scheduler check failed: {result.stderr}")
            return available
        except subprocess.TimeoutExpired:
            logger.debug("Task Scheduler check timed out")
            return False
        except FileNotFoundError:
            logger.debug("schtasks command not found")
            return False
        except Exception as e:
            logger.debug(f"Task Scheduler check failed with exception: {e}")
            return False
    
    @staticmethod
    def get_platform_info() -> Dict[str, Any]:
        """
        Get detailed platform information for diagnostics.
        
        Returns:
            dict: Platform information including system, available schedulers
        """
        system = platform.system().lower()
        
        info = {
            "system": system,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "available_schedulers": []
        }
        
        # Check all possible schedulers
        if PlatformDetector._has_systemd():
            info["available_schedulers"].append("systemd")
        if PlatformDetector._has_cron():
            info["available_schedulers"].append("cron")
        if PlatformDetector._has_launchd():
            info["available_schedulers"].append("launchd")
        if PlatformDetector._has_task_scheduler():
            info["available_schedulers"].append("windows_task_scheduler")
        
        try:
            best_scheduler = PlatformDetector.detect_best_scheduler()
            info["recommended_scheduler"] = best_scheduler.__name__
        except UnsupportedPlatformError:
            info["recommended_scheduler"] = None
        
        return info
