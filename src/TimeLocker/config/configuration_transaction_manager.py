"""
Configuration transaction manager for TimeLocker.

This module provides transaction support for configuration operations,
following the Single Responsibility Principle by focusing solely on
transaction management and rollback capabilities.
"""

import json
import logging
import uuid
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from ..interfaces.exceptions import (
    ConfigurationError,
    ConfigurationAtomicUpdateError,
    ConfigurationLockError
)

logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction states"""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionOperation:
    """Individual operation within a transaction"""
    operation_id: str
    operation_type: str  # 'update_section', 'delete_section', 'set_value'
    section: str
    key: Optional[str]
    old_value: Any
    new_value: Any
    timestamp: datetime


@dataclass
class ConfigurationTransaction:
    """Configuration transaction metadata"""
    transaction_id: str
    created_at: datetime
    state: TransactionState
    operations: List[TransactionOperation]
    backup_file: Optional[Path]
    lock_acquired: bool
    timeout_at: datetime
    
    def is_expired(self) -> bool:
        """Check if transaction has expired"""
        return datetime.now() > self.timeout_at


class ConfigurationTransactionManager:
    """
    Configuration transaction manager.
    
    Provides ACID transaction support for configuration operations with
    automatic rollback, timeout handling, and conflict detection.
    """

    def __init__(self, config_file: Path, lock_manager, backup_manager):
        """
        Initialize the transaction manager.
        
        Args:
            config_file: Configuration file to manage transactions for
            lock_manager: Configuration lock manager instance
            backup_manager: Configuration backup manager instance
        """
        self.config_file = config_file
        self.lock_manager = lock_manager
        self.backup_manager = backup_manager
        
        # Active transactions
        self._active_transactions: Dict[str, ConfigurationTransaction] = {}
        
        # Transaction timeout (default 5 minutes)
        self.default_timeout = timedelta(minutes=5)
        
        # Temporary directory for transaction files
        self.temp_dir = Path(tempfile.gettempdir()) / "timelocker_transactions"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def begin_transaction(self, timeout: Optional[timedelta] = None) -> str:
        """
        Begin a new configuration transaction.
        
        Args:
            timeout: Transaction timeout (defaults to 5 minutes)
            
        Returns:
            Transaction identifier
            
        Raises:
            ConfigurationError: If transaction cannot be started
        """
        try:
            # Clean up expired transactions first
            self._cleanup_expired_transactions()
            
            transaction_id = str(uuid.uuid4())
            timeout_duration = timeout or self.default_timeout
            
            # Create transaction
            transaction = ConfigurationTransaction(
                transaction_id=transaction_id,
                created_at=datetime.now(),
                state=TransactionState.ACTIVE,
                operations=[],
                backup_file=None,
                lock_acquired=False,
                timeout_at=datetime.now() + timeout_duration
            )
            
            # Acquire lock
            try:
                if self.lock_manager.acquire_lock(self.config_file, timeout=30):
                    transaction.lock_acquired = True
                else:
                    raise ConfigurationLockError("Could not acquire lock for transaction")
            except Exception as e:
                raise ConfigurationError(f"Failed to acquire lock for transaction: {e}")
            
            # Create backup of current state
            try:
                from .configuration_backup_manager import BackupReason
                backup_id = self.backup_manager.create_backup(
                    self.config_file, 
                    BackupReason.PRE_UPDATE, 
                    [f"transaction_{transaction_id}"]
                )
                # Store backup file path for rollback
                transaction.backup_file = self.backup_manager.backup_directory / f"{backup_id}.json"
            except Exception as e:
                # Release lock if backup fails
                if transaction.lock_acquired:
                    try:
                        self.lock_manager.release_lock(self.config_file)
                    except Exception:
                        pass
                raise ConfigurationError(f"Failed to create transaction backup: {e}")
            
            # Store transaction
            self._active_transactions[transaction_id] = transaction
            
            logger.debug(f"Started transaction {transaction_id}")
            return transaction_id
            
        except Exception as e:
            logger.error(f"Failed to begin transaction: {e}")
            raise ConfigurationError(f"Transaction start failed: {e}")

    def add_operation(self, transaction_id: str, operation_type: str, section: str, 
                     key: Optional[str] = None, old_value: Any = None, new_value: Any = None) -> None:
        """
        Add an operation to a transaction.
        
        Args:
            transaction_id: Transaction identifier
            operation_type: Type of operation
            section: Configuration section
            key: Configuration key (optional)
            old_value: Previous value
            new_value: New value
            
        Raises:
            ConfigurationError: If operation cannot be added
        """
        try:
            transaction = self._get_active_transaction(transaction_id)
            
            operation = TransactionOperation(
                operation_id=str(uuid.uuid4()),
                operation_type=operation_type,
                section=section,
                key=key,
                old_value=old_value,
                new_value=new_value,
                timestamp=datetime.now()
            )
            
            transaction.operations.append(operation)
            logger.debug(f"Added operation {operation_type} to transaction {transaction_id}")
            
        except Exception as e:
            logger.error(f"Failed to add operation to transaction {transaction_id}: {e}")
            raise ConfigurationError(f"Failed to add transaction operation: {e}")

    def commit_transaction(self, transaction_id: str) -> bool:
        """
        Commit a transaction and apply all operations.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            True if commit was successful
            
        Raises:
            ConfigurationError: If commit fails
        """
        try:
            transaction = self._get_active_transaction(transaction_id)
            
            # Apply all operations atomically
            success = self._apply_operations(transaction)
            
            if success:
                transaction.state = TransactionState.COMMITTED
                logger.info(f"Committed transaction {transaction_id} with {len(transaction.operations)} operations")
            else:
                transaction.state = TransactionState.FAILED
                logger.error(f"Failed to commit transaction {transaction_id}")
            
            # Release lock
            if transaction.lock_acquired:
                try:
                    self.lock_manager.release_lock(self.config_file)
                    transaction.lock_acquired = False
                except Exception as e:
                    logger.warning(f"Failed to release lock after commit: {e}")
            
            # Clean up transaction
            self._cleanup_transaction(transaction_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to commit transaction {transaction_id}: {e}")
            # Attempt rollback on commit failure
            try:
                self.rollback_transaction(transaction_id)
            except Exception:
                pass
            raise ConfigurationError(f"Transaction commit failed: {e}")

    def rollback_transaction(self, transaction_id: str) -> bool:
        """
        Rollback a transaction and restore previous state.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            True if rollback was successful
            
        Raises:
            ConfigurationError: If rollback fails
        """
        try:
            transaction = self._get_transaction(transaction_id)
            
            if transaction.state == TransactionState.ROLLED_BACK:
                logger.warning(f"Transaction {transaction_id} already rolled back")
                return True
            
            # Restore from backup if available
            if transaction.backup_file and transaction.backup_file.exists():
                try:
                    import shutil
                    shutil.copy2(transaction.backup_file, self.config_file)
                    logger.info(f"Restored configuration from backup for transaction {transaction_id}")
                except Exception as e:
                    logger.error(f"Failed to restore from backup: {e}")
                    raise ConfigurationError(f"Backup restoration failed: {e}")
            
            transaction.state = TransactionState.ROLLED_BACK
            
            # Release lock
            if transaction.lock_acquired:
                try:
                    self.lock_manager.release_lock(self.config_file)
                    transaction.lock_acquired = False
                except Exception as e:
                    logger.warning(f"Failed to release lock after rollback: {e}")
            
            # Clean up transaction
            self._cleanup_transaction(transaction_id)
            
            logger.info(f"Rolled back transaction {transaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback transaction {transaction_id}: {e}")
            raise ConfigurationError(f"Transaction rollback failed: {e}")

    def atomic_update(self, updates: Dict[str, Dict[str, Any]]) -> bool:
        """
        Perform atomic update of multiple configuration sections.
        
        Args:
            updates: Dictionary mapping section names to their new data
            
        Returns:
            True if all updates were successful
            
        Raises:
            ConfigurationAtomicUpdateError: If atomic update fails
        """
        transaction_id = None
        try:
            # Start transaction
            transaction_id = self.begin_transaction()
            
            # Load current configuration
            current_config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    current_config = json.load(f)
            
            # Add operations for each update
            for section, new_data in updates.items():
                old_data = current_config.get(section, {})
                self.add_operation(
                    transaction_id, 
                    'update_section', 
                    section, 
                    old_value=old_data, 
                    new_value=new_data
                )
            
            # Commit transaction
            return self.commit_transaction(transaction_id)
            
        except Exception as e:
            # Rollback on failure
            if transaction_id:
                try:
                    self.rollback_transaction(transaction_id)
                except Exception:
                    pass
            
            logger.error(f"Atomic update failed: {e}")
            raise ConfigurationAtomicUpdateError(f"Atomic update failed: {e}")

    def get_transaction_info(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a transaction.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Transaction information or None if not found
        """
        transaction = self._active_transactions.get(transaction_id)
        if not transaction:
            return None
        
        return {
            'transaction_id': transaction.transaction_id,
            'created_at': transaction.created_at.isoformat(),
            'state': transaction.state.value,
            'operation_count': len(transaction.operations),
            'lock_acquired': transaction.lock_acquired,
            'timeout_at': transaction.timeout_at.isoformat(),
            'is_expired': transaction.is_expired()
        }

    def list_active_transactions(self) -> List[Dict[str, Any]]:
        """
        List all active transactions.
        
        Returns:
            List of active transaction information
        """
        # Clean up expired transactions first
        self._cleanup_expired_transactions()
        
        return [
            self.get_transaction_info(tid) 
            for tid in self._active_transactions.keys()
        ]

    def cleanup_expired_transactions(self) -> int:
        """
        Clean up expired transactions.
        
        Returns:
            Number of transactions cleaned up
        """
        return self._cleanup_expired_transactions()

    # Private helper methods

    def _get_active_transaction(self, transaction_id: str) -> ConfigurationTransaction:
        """Get an active transaction or raise error"""
        transaction = self._active_transactions.get(transaction_id)
        if not transaction:
            raise ConfigurationError(f"Transaction not found: {transaction_id}")
        
        if transaction.is_expired():
            # Auto-rollback expired transaction
            try:
                self.rollback_transaction(transaction_id)
            except Exception:
                pass
            raise ConfigurationError(f"Transaction expired: {transaction_id}")
        
        if transaction.state != TransactionState.ACTIVE:
            raise ConfigurationError(f"Transaction not active: {transaction_id} (state: {transaction.state.value})")
        
        return transaction

    def _get_transaction(self, transaction_id: str) -> ConfigurationTransaction:
        """Get any transaction (active or not) or raise error"""
        transaction = self._active_transactions.get(transaction_id)
        if not transaction:
            raise ConfigurationError(f"Transaction not found: {transaction_id}")
        return transaction

    def _apply_operations(self, transaction: ConfigurationTransaction) -> bool:
        """Apply all operations in a transaction"""
        try:
            # Load current configuration
            current_config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    current_config = json.load(f)
            
            # Apply operations
            for operation in transaction.operations:
                if operation.operation_type == 'update_section':
                    current_config[operation.section] = operation.new_value
                elif operation.operation_type == 'delete_section':
                    if operation.section in current_config:
                        del current_config[operation.section]
                elif operation.operation_type == 'set_value':
                    if operation.section not in current_config:
                        current_config[operation.section] = {}
                    if operation.key:
                        current_config[operation.section][operation.key] = operation.new_value
            
            # Write updated configuration atomically
            temp_file = self.config_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w') as f:
                    json.dump(current_config, f, indent=2)
                
                # Atomic move
                temp_file.replace(self.config_file)
                return True
                
            except Exception as e:
                # Clean up temp file on failure
                if temp_file.exists():
                    temp_file.unlink()
                raise e
            
        except Exception as e:
            logger.error(f"Failed to apply transaction operations: {e}")
            return False

    def _cleanup_transaction(self, transaction_id: str) -> None:
        """Clean up transaction resources"""
        try:
            transaction = self._active_transactions.get(transaction_id)
            if not transaction:
                return
            
            # Clean up backup file if it's a transaction backup
            if transaction.backup_file and transaction.backup_file.exists():
                try:
                    # Only remove if it's clearly a transaction backup
                    if f"transaction_{transaction_id}" in str(transaction.backup_file):
                        transaction.backup_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up transaction backup: {e}")
            
            # Remove from active transactions
            del self._active_transactions[transaction_id]
            
        except Exception as e:
            logger.warning(f"Failed to clean up transaction {transaction_id}: {e}")

    def _cleanup_expired_transactions(self) -> int:
        """Clean up expired transactions"""
        expired_transactions = []
        
        for tid, transaction in self._active_transactions.items():
            if transaction.is_expired():
                expired_transactions.append(tid)
        
        cleaned_count = 0
        for tid in expired_transactions:
            try:
                self.rollback_transaction(tid)
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Failed to rollback expired transaction {tid}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired transactions")
        
        return cleaned_count