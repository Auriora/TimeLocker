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

import csv
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class BackupStatus(Enum):
    """Status of backup operations"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupRecord:
    """Historical record of a backup operation"""
    operation_id: str
    repository_id: str
    start_time: datetime
    end_time: datetime
    status: BackupStatus
    files_processed: int
    bytes_transferred: int
    duration_seconds: float
    snapshot_id: Optional[str] = None
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string"""
        hours, remainder = divmod(int(self.duration_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    @property
    def bytes_transferred_formatted(self) -> str:
        """Get formatted bytes transferred string"""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(self.bytes_transferred)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"

    @property
    def throughput_mbps(self) -> float:
        """Calculate throughput in MB/s"""
        if self.duration_seconds > 0:
            mb_transferred = self.bytes_transferred / (1024 * 1024)
            return mb_transferred / self.duration_seconds
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_id': self.operation_id,
            'repository_id': self.repository_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'status': self.status.value,
            'files_processed': self.files_processed,
            'bytes_transferred': self.bytes_transferred,
            'duration_seconds': self.duration_seconds,
            'snapshot_id': self.snapshot_id,
            'error_message': self.error_message,
            'warnings': self.warnings,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupRecord':
        """Create from dictionary"""
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['end_time'] = datetime.fromisoformat(data['end_time'])
        data['status'] = BackupStatus(data['status'])
        return cls(**data)


@dataclass
class HistoryFilters:
    """Filters for querying backup history"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    repository_id: Optional[str] = None
    status: Optional[BackupStatus] = None
    limit: Optional[int] = None


@dataclass
class PerformanceTrends:
    """Performance trends over a period"""
    period_days: int
    total_backups: int
    successful_backups: int
    failed_backups: int
    average_duration_seconds: float
    average_throughput_mbps: float
    total_bytes_transferred: int
    trend_data: List[Dict[str, Any]]


class BackupHistory:
    """
    Maintains searchable backup operation history.
    
    Responsibilities:
    - Operation history storage and retrieval
    - Performance metrics tracking
    - History search and filtering
    - Export capabilities for user records
    - Automatic cleanup based on retention policy
    """

    # Default retention period (90 days)
    DEFAULT_RETENTION_DAYS = 90

    def __init__(self, config_dir: Path):
        """
        Initialize backup history manager.
        
        Args:
            config_dir: Directory for history database and configuration
        """
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_db = self.config_dir / "history.db"
        self.retention_days = self.DEFAULT_RETENTION_DAYS
        
        # Load configuration
        self._load_config()
        
        # Initialize database
        self._init_database()
        
        # Perform initial cleanup
        self._cleanup_old_records()

    def record_backup_operation(self, operation: BackupRecord) -> None:
        """
        Record completed backup operation in history.
        
        Args:
            operation: Backup operation record to store
        """
        try:
            conn = sqlite3.connect(self.history_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO backup_history (
                    operation_id, repository_id, start_time, end_time,
                    status, files_processed, bytes_transferred, duration_seconds,
                    snapshot_id, error_message, warnings, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                operation.operation_id,
                operation.repository_id,
                operation.start_time.isoformat(),
                operation.end_time.isoformat(),
                operation.status.value,
                operation.files_processed,
                operation.bytes_transferred,
                operation.duration_seconds,
                operation.snapshot_id,
                operation.error_message,
                json.dumps(operation.warnings) if operation.warnings else None,
                json.dumps(operation.metadata) if operation.metadata else None
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded backup operation {operation.operation_id} in history")
            
        except Exception as e:
            logger.error(f"Failed to record backup operation: {e}")
            raise

    def get_backup_history(self, filters: Optional[HistoryFilters] = None) -> List[BackupRecord]:
        """
        Get filtered backup history.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List of backup records matching filters
        """
        if filters is None:
            filters = HistoryFilters()
        
        try:
            conn = sqlite3.connect(self.history_db)
            cursor = conn.cursor()
            
            # Build query
            query = "SELECT * FROM backup_history WHERE 1=1"
            params = []
            
            if filters.start_date:
                query += " AND start_time >= ?"
                params.append(filters.start_date.isoformat())
            
            if filters.end_date:
                query += " AND end_time <= ?"
                params.append(filters.end_date.isoformat())
            
            if filters.repository_id:
                query += " AND repository_id = ?"
                params.append(filters.repository_id)
            
            if filters.status:
                query += " AND status = ?"
                params.append(filters.status.value)
            
            query += " ORDER BY start_time DESC"
            
            if filters.limit:
                query += " LIMIT ?"
                params.append(filters.limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to BackupRecord objects
            records = []
            for row in rows:
                records.append(self._row_to_record(row))
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get backup history: {e}")
            return []

    def get_backup_by_id(self, operation_id: str) -> Optional[BackupRecord]:
        """
        Get a specific backup record by operation ID.
        
        Args:
            operation_id: Operation ID to retrieve
            
        Returns:
            Backup record or None if not found
        """
        try:
            conn = sqlite3.connect(self.history_db)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM backup_history WHERE operation_id = ?",
                (operation_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_record(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get backup by ID: {e}")
            return None

    def get_latest_backup(self, repository_id: Optional[str] = None) -> Optional[BackupRecord]:
        """
        Get the most recent backup record.
        
        Args:
            repository_id: Optional filter by repository
            
        Returns:
            Most recent backup record or None
        """
        filters = HistoryFilters(repository_id=repository_id, limit=1)
        records = self.get_backup_history(filters)
        return records[0] if records else None

    def get_performance_trends(self, days: int = 30, repository_id: Optional[str] = None) -> PerformanceTrends:
        """
        Get performance trends over specified period.
        
        Args:
            days: Number of days to analyze
            repository_id: Optional filter by repository
            
        Returns:
            Performance trends data
        """
        start_date = datetime.now() - timedelta(days=days)
        filters = HistoryFilters(start_date=start_date, repository_id=repository_id)
        records = self.get_backup_history(filters)
        
        if not records:
            return PerformanceTrends(
                period_days=days,
                total_backups=0,
                successful_backups=0,
                failed_backups=0,
                average_duration_seconds=0.0,
                average_throughput_mbps=0.0,
                total_bytes_transferred=0,
                trend_data=[]
            )
        
        # Calculate statistics
        successful = [r for r in records if r.status == BackupStatus.SUCCESS]
        failed = [r for r in records if r.status == BackupStatus.FAILED]
        
        total_duration = sum(r.duration_seconds for r in records)
        total_bytes = sum(r.bytes_transferred for r in records)
        
        avg_duration = total_duration / len(records) if records else 0.0
        avg_throughput = sum(r.throughput_mbps for r in records) / len(records) if records else 0.0
        
        # Build trend data (daily aggregates)
        trend_data = self._build_trend_data(records, days)
        
        return PerformanceTrends(
            period_days=days,
            total_backups=len(records),
            successful_backups=len(successful),
            failed_backups=len(failed),
            average_duration_seconds=avg_duration,
            average_throughput_mbps=avg_throughput,
            total_bytes_transferred=total_bytes,
            trend_data=trend_data
        )

    def export_history(self, output_path: Path, filters: Optional[HistoryFilters] = None) -> Path:
        """
        Export backup history to CSV format.
        
        Args:
            output_path: Path for the CSV file
            filters: Optional filters to apply
            
        Returns:
            Path to the created CSV file
        """
        records = self.get_backup_history(filters)
        
        try:
            with open(output_path, 'w', newline='') as csvfile:
                fieldnames = [
                    'operation_id', 'repository_id', 'start_time', 'end_time',
                    'status', 'files_processed', 'bytes_transferred', 'duration',
                    'throughput_mbps', 'snapshot_id', 'error_message'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in records:
                    writer.writerow({
                        'operation_id': record.operation_id,
                        'repository_id': record.repository_id,
                        'start_time': record.start_time.isoformat(),
                        'end_time': record.end_time.isoformat(),
                        'status': record.status.value,
                        'files_processed': record.files_processed,
                        'bytes_transferred': record.bytes_transferred_formatted,
                        'duration': record.duration_formatted,
                        'throughput_mbps': f"{record.throughput_mbps:.2f}",
                        'snapshot_id': record.snapshot_id or '',
                        'error_message': record.error_message or ''
                    })
            
            logger.info(f"Exported {len(records)} backup records to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export backup history: {e}")
            raise

    def set_retention_period(self, days: int) -> None:
        """
        Set retention period for backup history.
        
        Args:
            days: Number of days to retain history
        """
        if days < 1:
            raise ValueError("Retention period must be at least 1 day")
        
        self.retention_days = days
        self._save_config()
        self._cleanup_old_records()
        
        logger.info(f"Backup history retention period set to {days} days")

    def get_statistics(self, repository_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get overall statistics for backup history.
        
        Args:
            repository_id: Optional filter by repository
            
        Returns:
            Dictionary containing statistics
        """
        filters = HistoryFilters(repository_id=repository_id)
        records = self.get_backup_history(filters)
        
        if not records:
            return {
                'total_backups': 0,
                'successful_backups': 0,
                'failed_backups': 0,
                'success_rate': 0.0,
                'total_data_backed_up': 0,
                'oldest_backup': None,
                'newest_backup': None
            }
        
        successful = [r for r in records if r.status == BackupStatus.SUCCESS]
        failed = [r for r in records if r.status == BackupStatus.FAILED]
        
        return {
            'total_backups': len(records),
            'successful_backups': len(successful),
            'failed_backups': len(failed),
            'success_rate': (len(successful) / len(records) * 100) if records else 0.0,
            'total_data_backed_up': sum(r.bytes_transferred for r in records),
            'oldest_backup': min(r.start_time for r in records).isoformat(),
            'newest_backup': max(r.start_time for r in records).isoformat()
        }

    def _init_database(self) -> None:
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.history_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT UNIQUE NOT NULL,
                    repository_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    files_processed INTEGER NOT NULL,
                    bytes_transferred INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    snapshot_id TEXT,
                    error_message TEXT,
                    warnings TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for common queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_repository_id 
                ON backup_history(repository_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_start_time 
                ON backup_history(start_time)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_status 
                ON backup_history(status)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _cleanup_old_records(self) -> None:
        """Remove records older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            conn = sqlite3.connect(self.history_db)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM backup_history WHERE start_time < ?",
                (cutoff_date.isoformat(),)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backup records")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")

    def _row_to_record(self, row: Tuple) -> BackupRecord:
        """Convert database row to BackupRecord"""
        return BackupRecord(
            operation_id=row[1],
            repository_id=row[2],
            start_time=datetime.fromisoformat(row[3]),
            end_time=datetime.fromisoformat(row[4]),
            status=BackupStatus(row[5]),
            files_processed=row[6],
            bytes_transferred=row[7],
            duration_seconds=row[8],
            snapshot_id=row[9],
            error_message=row[10],
            warnings=json.loads(row[11]) if row[11] else None,
            metadata=json.loads(row[12]) if row[12] else None
        )

    def _build_trend_data(self, records: List[BackupRecord], days: int) -> List[Dict[str, Any]]:
        """Build daily trend data from records"""
        # Group records by date
        daily_data = {}
        
        for record in records:
            date_key = record.start_time.date().isoformat()
            
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'date': date_key,
                    'total_backups': 0,
                    'successful_backups': 0,
                    'failed_backups': 0,
                    'total_bytes': 0,
                    'total_duration': 0.0
                }
            
            daily_data[date_key]['total_backups'] += 1
            if record.status == BackupStatus.SUCCESS:
                daily_data[date_key]['successful_backups'] += 1
            elif record.status == BackupStatus.FAILED:
                daily_data[date_key]['failed_backups'] += 1
            
            daily_data[date_key]['total_bytes'] += record.bytes_transferred
            daily_data[date_key]['total_duration'] += record.duration_seconds
        
        # Convert to list and sort by date
        trend_data = list(daily_data.values())
        trend_data.sort(key=lambda x: x['date'])
        
        return trend_data

    def _load_config(self) -> None:
        """Load configuration"""
        config_file = self.config_dir / "history_config.json"
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    if 'retention_days' in data:
                        self.retention_days = data['retention_days']
        except Exception as e:
            logger.warning(f"Failed to load history config: {e}")

    def _save_config(self) -> None:
        """Save configuration"""
        config_file = self.config_dir / "history_config.json"
        
        try:
            with open(config_file, 'w') as f:
                json.dump({'retention_days': self.retention_days}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history config: {e}")
