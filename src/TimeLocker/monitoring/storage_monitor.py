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

import logging
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from ..backup_repository import BackupRepository

logger = logging.getLogger(__name__)


# Constants
CAPACITY_WARNING_THRESHOLD = 0.90  # 90% capacity
CACHE_TTL_SECONDS = 300  # 5 minutes
STORAGE_TRENDS_DAYS = 30  # 30 days for trend analysis


class WarningLevel(Enum):
    """Storage warning severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class StorageUsage:
    """Storage usage information for a repository"""
    repository_id: str
    used_bytes: int
    available_bytes: Optional[int]
    total_bytes: Optional[int]
    usage_percentage: Optional[float]
    deduplication_ratio: Optional[float]
    compression_ratio: Optional[float]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StorageUsage':
        """Create from dictionary"""
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


@dataclass
class CapacityWarning:
    """Warning about repository capacity"""
    repository_id: str
    level: WarningLevel
    message: str
    usage_percentage: float
    used_bytes: int
    available_bytes: Optional[int]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'repository_id': self.repository_id,
            'level': self.level.value,
            'message': self.message,
            'usage_percentage': self.usage_percentage,
            'used_bytes': self.used_bytes,
            'available_bytes': self.available_bytes,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class StorageTrends:
    """Storage growth trends for a repository"""
    repository_id: str
    start_date: datetime
    end_date: datetime
    data_points: List[Dict[str, Any]]  # List of {date, used_bytes, snapshot_count}
    average_daily_growth_bytes: float
    projected_full_date: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'repository_id': self.repository_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'data_points': self.data_points,
            'average_daily_growth_bytes': self.average_daily_growth_bytes,
            'projected_full_date': self.projected_full_date.isoformat() if self.projected_full_date else None
        }


@dataclass
class OptimizationRecommendation:
    """Storage optimization recommendation"""
    recommendation_type: str
    priority: str  # 'low', 'medium', 'high'
    title: str
    description: str
    estimated_savings_bytes: Optional[int]
    action_required: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


class StorageMonitor:
    """
    Monitors storage usage across all repositories.
    
    Responsibilities:
    - Repository storage usage tracking
    - Capacity warnings and recommendations
    - Growth trend analysis
    - Deduplication and compression reporting
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize storage monitor.
        
        Args:
            config_dir: Directory for storage monitoring data
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "monitoring" / "storage"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.usage_cache: Dict[str, StorageUsage] = {}
        self.cache_ttl = timedelta(seconds=CACHE_TTL_SECONDS)
        
        # Load historical data
        self._load_historical_data()
        
        logger.info("StorageMonitor initialized")

    def get_repository_usage(self, repository: BackupRepository, force_refresh: bool = False) -> StorageUsage:
        """
        Get current storage usage for repository.
        
        Args:
            repository: Repository to check
            force_refresh: Force refresh even if cached data is available
            
        Returns:
            StorageUsage: Current storage usage information
        """
        repository_id = repository.name
        
        # Check cache
        if not force_refresh and repository_id in self.usage_cache:
            cached = self.usage_cache[repository_id]
            if datetime.now() - cached.last_updated < self.cache_ttl:
                logger.debug(f"Using cached storage usage for repository '{repository_id}'")
                return cached
        
        # Fetch fresh data
        try:
            usage = self._fetch_repository_usage(repository)
            self.usage_cache[repository_id] = usage
            
            # Store in historical data
            self._record_usage_snapshot(usage)
            
            return usage
            
        except Exception as e:
            logger.error(f"Failed to get repository usage for '{repository_id}': {e}")
            # Return cached data if available, even if stale
            if repository_id in self.usage_cache:
                logger.warning(f"Returning stale cached data for repository '{repository_id}'")
                return self.usage_cache[repository_id]
            raise

    def check_capacity_warnings(self, repositories: List[BackupRepository]) -> List[CapacityWarning]:
        """
        Check for repositories approaching capacity limits.
        
        Args:
            repositories: List of repositories to check
            
        Returns:
            List[CapacityWarning]: List of capacity warnings
        """
        warnings = []
        
        for repository in repositories:
            try:
                usage = self.get_repository_usage(repository)
                
                if usage.usage_percentage is not None:
                    if usage.usage_percentage >= CAPACITY_WARNING_THRESHOLD:
                        level = WarningLevel.CRITICAL if usage.usage_percentage >= 0.95 else WarningLevel.WARNING
                        
                        message = (
                            f"Repository '{repository.name}' is at {usage.usage_percentage:.1%} capacity. "
                            f"Used: {self._format_bytes(usage.used_bytes)}"
                        )
                        
                        if usage.available_bytes:
                            message += f", Available: {self._format_bytes(usage.available_bytes)}"
                        
                        warning = CapacityWarning(
                            repository_id=repository.name,
                            level=level,
                            message=message,
                            usage_percentage=usage.usage_percentage,
                            used_bytes=usage.used_bytes,
                            available_bytes=usage.available_bytes,
                            timestamp=datetime.now()
                        )
                        
                        warnings.append(warning)
                        logger.warning(message)
                        
            except Exception as e:
                logger.error(f"Failed to check capacity for repository '{repository.name}': {e}")
        
        return warnings

    def get_storage_trends(self, repository: BackupRepository, days: int = STORAGE_TRENDS_DAYS) -> StorageTrends:
        """
        Get storage growth trends for repository.
        
        Args:
            repository: Repository to analyze
            days: Number of days to analyze (default: 30)
            
        Returns:
            StorageTrends: Storage growth trends
        """
        repository_id = repository.name
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Load historical data points
        data_points = self._get_historical_data_points(repository_id, start_date, end_date)
        
        # Calculate average daily growth
        average_daily_growth = 0.0
        projected_full_date = None
        
        if len(data_points) >= 2:
            first_point = data_points[0]
            last_point = data_points[-1]
            
            days_elapsed = (last_point['date'] - first_point['date']).days
            if days_elapsed > 0:
                bytes_growth = last_point['used_bytes'] - first_point['used_bytes']
                average_daily_growth = bytes_growth / days_elapsed
                
                # Project when repository will be full
                current_usage = self.get_repository_usage(repository)
                if current_usage.available_bytes and average_daily_growth > 0:
                    days_until_full = current_usage.available_bytes / average_daily_growth
                    projected_full_date = datetime.now() + timedelta(days=days_until_full)
        
        return StorageTrends(
            repository_id=repository_id,
            start_date=start_date,
            end_date=end_date,
            data_points=data_points,
            average_daily_growth_bytes=average_daily_growth,
            projected_full_date=projected_full_date
        )

    def get_deduplication_report(self, repository: BackupRepository) -> Dict[str, Any]:
        """
        Get detailed deduplication report for repository.
        
        Args:
            repository: Repository to analyze
            
        Returns:
            Dictionary with deduplication statistics and analysis
        """
        try:
            usage = self.get_repository_usage(repository)
            
            report = {
                'repository_id': repository.name,
                'deduplication_ratio': usage.deduplication_ratio,
                'compression_ratio': usage.compression_ratio,
                'total_size': usage.used_bytes,
                'formatted_total_size': self._format_bytes(usage.used_bytes),
                'timestamp': datetime.now().isoformat()
            }
            
            # Calculate estimated savings
            if usage.deduplication_ratio and usage.deduplication_ratio > 1.0:
                original_size = usage.used_bytes * usage.deduplication_ratio
                savings = original_size - usage.used_bytes
                report['deduplication_savings_bytes'] = int(savings)
                report['deduplication_savings_formatted'] = self._format_bytes(int(savings))
                report['deduplication_efficiency'] = f"{((savings / original_size) * 100):.1f}%"
            
            if usage.compression_ratio and usage.compression_ratio > 1.0:
                uncompressed_size = usage.used_bytes * usage.compression_ratio
                savings = uncompressed_size - usage.used_bytes
                report['compression_savings_bytes'] = int(savings)
                report['compression_savings_formatted'] = self._format_bytes(int(savings))
                report['compression_efficiency'] = f"{((savings / uncompressed_size) * 100):.1f}%"
            
            # Add interpretation
            report['interpretation'] = self._interpret_deduplication_stats(usage)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate deduplication report: {e}")
            return {
                'repository_id': repository.name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_compression_report(self, repository: BackupRepository) -> Dict[str, Any]:
        """
        Get detailed compression report for repository.
        
        Args:
            repository: Repository to analyze
            
        Returns:
            Dictionary with compression statistics and analysis
        """
        try:
            usage = self.get_repository_usage(repository)
            
            report = {
                'repository_id': repository.name,
                'compression_ratio': usage.compression_ratio,
                'total_size': usage.used_bytes,
                'formatted_total_size': self._format_bytes(usage.used_bytes),
                'timestamp': datetime.now().isoformat()
            }
            
            # Calculate compression effectiveness
            if usage.compression_ratio and usage.compression_ratio > 1.0:
                uncompressed_size = usage.used_bytes * usage.compression_ratio
                savings = uncompressed_size - usage.used_bytes
                report['compression_savings_bytes'] = int(savings)
                report['compression_savings_formatted'] = self._format_bytes(int(savings))
                report['compression_efficiency'] = f"{((savings / uncompressed_size) * 100):.1f}%"
                report['uncompressed_size'] = int(uncompressed_size)
                report['uncompressed_size_formatted'] = self._format_bytes(int(uncompressed_size))
            
            # Add interpretation and recommendations
            report['interpretation'] = self._interpret_compression_stats(usage)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compression report: {e}")
            return {
                'repository_id': repository.name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_optimization_recommendations(self, repository: BackupRepository) -> List[OptimizationRecommendation]:
        """
        Get storage optimization recommendations based on usage patterns.
        
        Args:
            repository: Repository to analyze
            
        Returns:
            List[OptimizationRecommendation]: List of recommendations
        """
        recommendations = []
        
        try:
            usage = self.get_repository_usage(repository)
            
            # Check if prune is needed
            if self._should_recommend_prune(repository):
                recommendations.append(OptimizationRecommendation(
                    recommendation_type='prune',
                    priority='medium',
                    title='Run repository prune',
                    description='Pruning removes unused data and can free up significant space. '
                               'This operation is safe and recommended after removing old snapshots.',
                    estimated_savings_bytes=None,
                    action_required='Run: timelocker repository prune <repository-name>'
                ))
            
            # Check deduplication ratio
            if usage.deduplication_ratio:
                if usage.deduplication_ratio < 1.5:
                    recommendations.append(OptimizationRecommendation(
                        recommendation_type='deduplication',
                        priority='low',
                        title='Low deduplication ratio detected',
                        description=f'Current deduplication ratio is {usage.deduplication_ratio:.2f}x. '
                                   'This suggests limited file redundancy across backups. '
                                   'Consider reviewing backup selection patterns.',
                        estimated_savings_bytes=None,
                        action_required='Review backup selection patterns and file types'
                    ))
                elif usage.deduplication_ratio > 3.0:
                    # High deduplication is good
                    recommendations.append(OptimizationRecommendation(
                        recommendation_type='deduplication',
                        priority='low',
                        title='Excellent deduplication ratio',
                        description=f'Current deduplication ratio is {usage.deduplication_ratio:.2f}x. '
                                   'Your backup strategy is efficiently utilizing deduplication.',
                        estimated_savings_bytes=None,
                        action_required='No action required - continue current backup strategy'
                    ))
            
            # Check compression ratio
            if usage.compression_ratio:
                if usage.compression_ratio < 1.2:
                    recommendations.append(OptimizationRecommendation(
                        recommendation_type='compression',
                        priority='low',
                        title='Low compression ratio detected',
                        description=f'Current compression ratio is {usage.compression_ratio:.2f}x. '
                                   'You may be backing up already-compressed files (images, videos, archives). '
                                   'This is normal for media-heavy backups.',
                        estimated_savings_bytes=None,
                        action_required='Review file types being backed up'
                    ))
                elif usage.compression_ratio > 2.0:
                    # High compression is good
                    recommendations.append(OptimizationRecommendation(
                        recommendation_type='compression',
                        priority='low',
                        title='Excellent compression ratio',
                        description=f'Current compression ratio is {usage.compression_ratio:.2f}x. '
                                   'Your data is compressing very well.',
                        estimated_savings_bytes=None,
                        action_required='No action required - compression is working effectively'
                    ))
            
            # Check capacity warnings
            if usage.usage_percentage and usage.usage_percentage >= CAPACITY_WARNING_THRESHOLD:
                priority = 'high' if usage.usage_percentage >= 0.95 else 'medium'
                
                # Calculate estimated time until full
                trends = self.get_storage_trends(repository, days=30)
                time_until_full = ""
                if trends.projected_full_date:
                    days_until_full = (trends.projected_full_date - datetime.now()).days
                    if days_until_full > 0:
                        time_until_full = f" Estimated full in {days_until_full} days."
                
                recommendations.append(OptimizationRecommendation(
                    recommendation_type='capacity',
                    priority=priority,
                    title='Repository approaching capacity',
                    description=f'Repository is at {usage.usage_percentage:.1%} capacity.{time_until_full} '
                               'Consider expanding storage or implementing retention policies to free up space.',
                    estimated_savings_bytes=None,
                    action_required='Expand storage or configure retention policy'
                ))
            
            # Check for old snapshots
            snapshot_recommendation = self._check_old_snapshots(repository)
            if snapshot_recommendation:
                recommendations.append(snapshot_recommendation)
            
            # Check storage growth trends
            trends = self.get_storage_trends(repository, days=30)
            if trends.average_daily_growth_bytes > 0:
                daily_growth_formatted = self._format_bytes(int(trends.average_daily_growth_bytes))
                monthly_growth = trends.average_daily_growth_bytes * 30
                monthly_growth_formatted = self._format_bytes(int(monthly_growth))
                
                recommendations.append(OptimizationRecommendation(
                    recommendation_type='growth_analysis',
                    priority='low',
                    title='Storage growth analysis',
                    description=f'Repository is growing at approximately {daily_growth_formatted}/day '
                               f'({monthly_growth_formatted}/month). Monitor growth trends to plan storage needs.',
                    estimated_savings_bytes=None,
                    action_required='Monitor storage growth and plan capacity accordingly'
                ))
            
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations: {e}")
        
        return recommendations

    def _fetch_repository_usage(self, repository: BackupRepository) -> StorageUsage:
        """
        Fetch current storage usage from repository.
        
        Args:
            repository: Repository to query
            
        Returns:
            StorageUsage: Current usage information
        """
        try:
            # Run restic stats command
            cmd = ['restic', 'stats', '--repo', repository.uri(), '--json']
            
            env = repository.to_env()
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
            
            if result.returncode != 0:
                raise RuntimeError(f"Failed to get repository stats: {result.stderr}")
            
            # Parse JSON output
            stats_data = json.loads(result.stdout)
            
            used_bytes = stats_data.get('total_size', 0)
            
            # Try to get filesystem information for available space
            available_bytes = None
            total_bytes = None
            usage_percentage = None
            
            # For local repositories, we can check filesystem space
            if repository.uri().startswith('/') or repository.uri().startswith('file://'):
                try:
                    import shutil
                    repo_path = repository.uri().replace('file://', '')
                    stat = shutil.disk_usage(repo_path)
                    total_bytes = stat.total
                    available_bytes = stat.free
                    usage_percentage = used_bytes / total_bytes if total_bytes > 0 else None
                except Exception as e:
                    logger.debug(f"Could not get filesystem stats: {e}")
            
            # Extract deduplication and compression ratios if available
            deduplication_ratio = None
            compression_ratio = None
            
            # Restic doesn't directly provide these, but we can estimate from stats
            if 'total_blob_count' in stats_data and stats_data['total_blob_count'] > 0:
                # Rough estimation based on repository efficiency
                repository_size = stats_data.get('repository_size', used_bytes)
                if repository_size > 0:
                    deduplication_ratio = used_bytes / repository_size
            
            return StorageUsage(
                repository_id=repository.name,
                used_bytes=used_bytes,
                available_bytes=available_bytes,
                total_bytes=total_bytes,
                usage_percentage=usage_percentage,
                deduplication_ratio=deduplication_ratio,
                compression_ratio=compression_ratio,
                last_updated=datetime.now()
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while fetching repository usage for '{repository.name}'")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse repository stats JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch repository usage: {e}")
            raise

    def _record_usage_snapshot(self, usage: StorageUsage) -> None:
        """
        Record usage snapshot in historical data.
        
        Args:
            usage: Storage usage to record
        """
        try:
            history_file = self.config_dir / f"{usage.repository_id}_history.json"
            
            # Load existing history
            history = []
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            
            # Add new data point
            history.append({
                'date': usage.last_updated.isoformat(),
                'used_bytes': usage.used_bytes,
                'available_bytes': usage.available_bytes,
                'deduplication_ratio': usage.deduplication_ratio,
                'compression_ratio': usage.compression_ratio
            })
            
            # Keep only last 90 days
            cutoff_date = datetime.now() - timedelta(days=90)
            history = [
                point for point in history
                if datetime.fromisoformat(point['date']) > cutoff_date
            ]
            
            # Save updated history
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to record usage snapshot: {e}")

    def _get_historical_data_points(self, repository_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get historical data points for repository.
        
        Args:
            repository_id: Repository identifier
            start_date: Start date for data points
            end_date: End date for data points
            
        Returns:
            List of data points with date and usage information
        """
        try:
            history_file = self.config_dir / f"{repository_id}_history.json"
            
            if not history_file.exists():
                return []
            
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            # Filter by date range
            data_points = []
            for point in history:
                point_date = datetime.fromisoformat(point['date'])
                if start_date <= point_date <= end_date:
                    data_points.append({
                        'date': point_date,
                        'used_bytes': point['used_bytes'],
                        'available_bytes': point.get('available_bytes'),
                        'deduplication_ratio': point.get('deduplication_ratio'),
                        'compression_ratio': point.get('compression_ratio')
                    })
            
            # Sort by date
            data_points.sort(key=lambda x: x['date'])
            
            return data_points
            
        except Exception as e:
            logger.error(f"Failed to get historical data points: {e}")
            return []

    def _load_historical_data(self) -> None:
        """Load historical storage data from disk."""
        try:
            # Historical data is loaded on-demand per repository
            pass
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")

    def _should_recommend_prune(self, repository: BackupRepository) -> bool:
        """
        Check if prune should be recommended.
        
        Args:
            repository: Repository to check
            
        Returns:
            bool: True if prune is recommended
        """
        try:
            # Check if there are snapshots that have been forgotten
            # This is a simplified check - in practice, we'd need to track forget operations
            snapshots = repository.list_snapshots()
            
            # If there are many snapshots, pruning is likely beneficial
            if len(snapshots) > 50:
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Could not determine if prune is needed: {e}")
            return False

    def _check_old_snapshots(self, repository: BackupRepository) -> Optional[OptimizationRecommendation]:
        """
        Check for old snapshots that could be removed.
        
        Args:
            repository: Repository to check
            
        Returns:
            OptimizationRecommendation if old snapshots found, None otherwise
        """
        try:
            snapshots = repository.list_snapshots()
            
            if not snapshots:
                return None
            
            # Check for snapshots older than 1 year
            one_year_ago = datetime.now().timestamp() - (365 * 24 * 60 * 60)
            old_snapshots = [s for s in snapshots if s.timestamp < one_year_ago]
            
            if len(old_snapshots) > 10:
                return OptimizationRecommendation(
                    recommendation_type='retention',
                    priority='medium',
                    title='Old snapshots detected',
                    description=f'Found {len(old_snapshots)} snapshots older than 1 year. '
                               'Consider implementing a retention policy to automatically remove old snapshots.',
                    estimated_savings_bytes=None,
                    action_required='Configure retention policy or manually remove old snapshots'
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not check for old snapshots: {e}")
            return None

    def _interpret_deduplication_stats(self, usage: StorageUsage) -> str:
        """
        Interpret deduplication statistics and provide user-friendly explanation.
        
        Args:
            usage: Storage usage information
            
        Returns:
            Human-readable interpretation
        """
        if not usage.deduplication_ratio:
            return "Deduplication statistics not available for this repository."
        
        ratio = usage.deduplication_ratio
        
        if ratio < 1.2:
            return ("Very low deduplication (< 1.2x). This suggests minimal file redundancy "
                   "across backups, which is typical for frequently changing unique files.")
        elif ratio < 2.0:
            return (f"Moderate deduplication ({ratio:.2f}x). Some file redundancy is being "
                   "eliminated, which is normal for typical backup scenarios.")
        elif ratio < 3.0:
            return (f"Good deduplication ({ratio:.2f}x). Significant file redundancy is being "
                   "eliminated, indicating efficient storage usage.")
        else:
            return (f"Excellent deduplication ({ratio:.2f}x). Very high file redundancy is being "
                   "eliminated, resulting in substantial storage savings.")

    def _interpret_compression_stats(self, usage: StorageUsage) -> str:
        """
        Interpret compression statistics and provide user-friendly explanation.
        
        Args:
            usage: Storage usage information
            
        Returns:
            Human-readable interpretation
        """
        if not usage.compression_ratio:
            return "Compression statistics not available for this repository."
        
        ratio = usage.compression_ratio
        
        if ratio < 1.2:
            return ("Low compression (< 1.2x). Your data is likely already compressed "
                   "(images, videos, archives) or consists of binary files that don't compress well.")
        elif ratio < 1.5:
            return (f"Moderate compression ({ratio:.2f}x). Your data is achieving reasonable "
                   "compression, typical for mixed file types.")
        elif ratio < 2.0:
            return (f"Good compression ({ratio:.2f}x). Your data is compressing well, "
                   "likely containing text files, documents, or other compressible content.")
        else:
            return (f"Excellent compression ({ratio:.2f}x). Your data is highly compressible, "
                   "resulting in significant storage savings.")

    @staticmethod
    def _format_bytes(bytes_value: int) -> str:
        """
        Format bytes as human-readable string.
        
        Args:
            bytes_value: Number of bytes
            
        Returns:
            Formatted string (e.g., "1.5 GB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
