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
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any
from threading import Lock

from .interfaces.recovery_models import (
    RecoveryOperation,
    RecoveryOptions,
    RecoveryType,
    OperationStatus,
    SelectionCriteria,
    ProgressStatus,
    ErrorDetails
)
from .recovery_errors import (
    RecoveryError,
    RestoreError,
    RestoreTargetError,
    SnapshotNotFoundError,
    RepositoryAccessError
)
from .restore_manager import RestoreManager, RestoreOptions as LegacyRestoreOptions
from .backup_repository import BackupRepository
from .snapshot_manager import SnapshotManager
from .recovery_state_manager import RecoveryStateManager

logger = logging.getLogger(__name__)


class RecoveryOrchestrator:
    """
    Coordinates recovery operations across different backup tools and manages
    the overall recovery workflow including validation and progress monitoring.
    
    This class serves as the central coordination component for all recovery
    operations, providing a unified interface while maintaining backward
    compatibility with the existing RestoreManager.
    """
    
    def __init__(
        self,
        repository: BackupRepository,
        snapshot_manager: Optional[SnapshotManager] = None,
        restore_manager: Optional[RestoreManager] = None,
        state_manager: Optional[RecoveryStateManager] = None,
        repository_service: Optional['RepositoryService'] = None,
        security_service: Optional['SecurityService'] = None,
        selection_manager: Optional['SelectionManager'] = None
    ):
        """
        Initialize the RecoveryOrchestrator.
        
        Args:
            repository: BackupRepository instance for accessing snapshots
            snapshot_manager: Optional SnapshotManager instance
            restore_manager: Optional RestoreManager for backward compatibility
            state_manager: Optional RecoveryStateManager for operation persistence
            repository_service: Optional RepositoryService for repository management integration
            security_service: Optional SecurityService for security integration
            selection_manager: Optional SelectionManager for data selection integration
        """
        self.repository = repository
        self.snapshot_manager = snapshot_manager or SnapshotManager(repository)
        self.restore_manager = restore_manager or RestoreManager(repository, self.snapshot_manager)
        self.state_manager = state_manager or RecoveryStateManager()
        
        # Service integrations
        self.repository_service = repository_service
        self.security_service = security_service
        self.selection_manager = selection_manager
        
        # Track active and completed operations
        self._operations: Dict[str, RecoveryOperation] = {}
        self._operation_options: Dict[str, RecoveryOptions] = {}
        self._operations_lock = Lock()
        
        # Load any existing operations from persistent storage
        self._load_persisted_operations()
        
        logger.info("RecoveryOrchestrator initialized")
    
    def _validate_repository_accessibility(self) -> None:
        """
        Validate that the repository is accessible and ready for recovery operations.
        
        Raises:
            RepositoryAccessError: If repository is not accessible or not ready
        """
        try:
            # Check if repository is initialized
            if not self.repository.is_repository_initialized():
                raise RepositoryAccessError(
                    "Repository is not initialized. Cannot perform recovery operations."
                )
            
            # If repository service is available, perform additional checks
            if self.repository_service:
                try:
                    # Check repository health
                    check_result = self.repository_service.check_repository(self.repository)
                    if check_result['status'] != 'success':
                        errors = '; '.join(check_result.get('errors', ['Unknown error']))
                        raise RepositoryAccessError(
                            f"Repository health check failed: {errors}"
                        )
                except Exception as e:
                    logger.warning(f"Repository service check failed: {e}")
                    # Continue if repository service check fails but basic check passed
            
            logger.debug("Repository accessibility validated successfully")
            
        except RepositoryAccessError:
            raise
        except Exception as e:
            logger.error(f"Repository accessibility validation failed: {e}")
            raise RepositoryAccessError(
                f"Failed to validate repository accessibility: {e}"
            ) from e
    
    def _check_repository_conflicts(self, operation_type: str) -> None:
        """
        Check for conflicts with ongoing backup or maintenance operations.
        
        Args:
            operation_type: Type of recovery operation being initiated
            
        Raises:
            RecoveryError: If there are conflicting operations
        """
        try:
            # Check if repository is locked
            if self.security_service:
                repo_id = getattr(self.repository, 'id', str(self.repository._location))
                if self.security_service.is_repository_locked(repo_id):
                    raise RecoveryError(
                        f"Repository is locked. Cannot perform {operation_type} recovery operation."
                    )
                
                # Check if operation is allowed based on repository mode
                if not self.security_service.is_operation_allowed(repo_id, 'restore'):
                    mode = self.security_service.get_repository_mode(repo_id)
                    raise RecoveryError(
                        f"Recovery operation not allowed. Repository is in {mode} mode."
                    )
            
            logger.debug("No repository conflicts detected")
            
        except RecoveryError:
            raise
        except Exception as e:
            logger.warning(f"Repository conflict check failed: {e}")
            # Continue if conflict check fails - don't block recovery
    
    def _validate_repository_authentication(self) -> None:
        """
        Validate repository authentication and authorization.
        
        Raises:
            RepositoryAccessError: If authentication fails
        """
        try:
            # Check if repository has valid credentials
            if not self.repository._password:
                raise RepositoryAccessError(
                    "Repository password not available. Cannot access encrypted repository."
                )
            
            # If security service is available, audit the access
            if self.security_service:
                repo_id = getattr(self.repository, 'id', str(self.repository._location))
                self.security_service.log_security_event(
                    type('SecurityEvent', (), {
                        'timestamp': datetime.now(),
                        'event_type': 'repository_access',
                        'level': type('SecurityLevel', (), {'value': 'medium'})(),
                        'description': 'Repository authentication validated for recovery operation',
                        'repository_id': repo_id,
                        'metadata': {'operation': 'recovery_authentication'}
                    })()
                )
            
            logger.debug("Repository authentication validated successfully")
            
        except RepositoryAccessError:
            raise
        except Exception as e:
            logger.warning(f"Repository authentication validation failed: {e}")
            # Continue if authentication check fails but password is available
    
    def initiate_full_recovery(
        self,
        snapshot_id: str,
        target_path: str,
        options: Optional[RecoveryOptions] = None
    ) -> RecoveryOperation:
        """
        Initiates full snapshot restoration.
        
        This method performs a complete restoration of all files from the
        specified snapshot to the target location.
        
        Args:
            snapshot_id: ID of the snapshot to restore
            target_path: Destination path for restored files
            options: Optional recovery configuration options
            
        Returns:
            RecoveryOperation object tracking the operation
            
        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
            RestoreTargetError: If the target path is invalid
            RecoveryError: For other recovery-related errors
            RepositoryAccessError: If repository is not accessible
        """
        if options is None:
            options = RecoveryOptions()
        
        # Validate repository accessibility before starting recovery
        self._validate_repository_accessibility()
        
        # Check for conflicts with ongoing operations
        self._check_repository_conflicts('full')
        
        # Validate authentication and authorization
        self._validate_repository_authentication()
        
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())
        
        # Validate snapshot exists
        try:
            snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)
            if not snapshot:
                raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found") from e
        
        # Validate target path
        target = Path(target_path)
        if target.exists() and not target.is_dir():
            raise RestoreTargetError(f"Target path exists but is not a directory: {target_path}")
        
        # Create recovery operation
        operation = RecoveryOperation(
            operation_id=operation_id,
            snapshot_id=snapshot_id,
            recovery_type=RecoveryType.FULL,
            target_path=str(target),
            status=OperationStatus.PENDING,
            start_time=datetime.now()
        )
        
        # Store options separately (not part of the data model)
        self._operation_options[operation_id] = options
        
        # Register operation
        with self._operations_lock:
            self._operations[operation_id] = operation
        
        # Persist operation state
        self.state_manager.save_operation(operation)
        
        logger.info(f"Initiated full recovery operation {operation_id} for snapshot {snapshot_id}")
        
        # Execute recovery in the background (or synchronously for now)
        try:
            self._execute_full_recovery(operation)
        except Exception as e:
            logger.error(f"Full recovery operation {operation_id} failed: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            # Update persisted state
            self.state_manager.save_operation(operation)
        
        return operation
    
    def initiate_selective_recovery(
        self,
        snapshot_id: str,
        selection_criteria: SelectionCriteria,
        target_path: str,
        options: Optional[RecoveryOptions] = None
    ) -> RecoveryOperation:
        """
        Initiates selective file restoration.
        
        This method performs restoration of specific files matching the
        selection criteria from the specified snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to restore from
            selection_criteria: Criteria for selecting files to restore
            target_path: Destination path for restored files
            options: Optional recovery configuration options
            
        Returns:
            RecoveryOperation object tracking the operation
            
        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
            RestoreTargetError: If the target path is invalid
            RecoveryError: For other recovery-related errors
            RepositoryAccessError: If repository is not accessible
        """
        if options is None:
            options = RecoveryOptions()
        
        # Validate repository accessibility before starting recovery
        self._validate_repository_accessibility()
        
        # Check for conflicts with ongoing operations
        self._check_repository_conflicts('selective')
        
        # Validate authentication and authorization
        self._validate_repository_authentication()
        
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())
        
        # Validate snapshot exists
        try:
            snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)
            if not snapshot:
                raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found") from e
        
        # Validate target path
        target = Path(target_path)
        if target.exists() and not target.is_dir():
            raise RestoreTargetError(f"Target path exists but is not a directory: {target_path}")
        
        # Create recovery operation
        operation = RecoveryOperation(
            operation_id=operation_id,
            snapshot_id=snapshot_id,
            recovery_type=RecoveryType.SELECTIVE,
            target_path=str(target),
            status=OperationStatus.PENDING,
            start_time=datetime.now()
        )
        
        # Store options separately (not part of the data model)
        self._operation_options[operation_id] = options
        
        # Register operation
        with self._operations_lock:
            self._operations[operation_id] = operation
        
        # Persist operation state
        self.state_manager.save_operation(operation)
        
        logger.info(f"Initiated selective recovery operation {operation_id} for snapshot {snapshot_id}")
        
        # Execute recovery
        try:
            self._execute_selective_recovery(operation, selection_criteria)
        except Exception as e:
            logger.error(f"Selective recovery operation {operation_id} failed: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            # Update persisted state
            self.state_manager.save_operation(operation)
        
        return operation
    
    def get_recovery_status(self, operation_id: str) -> Optional[RecoveryOperation]:
        """
        Retrieves current status of a recovery operation.
        
        Args:
            operation_id: ID of the recovery operation
            
        Returns:
            RecoveryOperation object if found, None otherwise
        """
        with self._operations_lock:
            return self._operations.get(operation_id)
    
    def cancel_recovery(self, operation_id: str) -> bool:
        """
        Cancels an ongoing recovery operation.
        
        Args:
            operation_id: ID of the recovery operation to cancel
            
        Returns:
            True if operation was cancelled, False if not found or already complete
        """
        with self._operations_lock:
            operation = self._operations.get(operation_id)
            
            if not operation:
                logger.warning(f"Cannot cancel operation {operation_id}: not found")
                return False
            
            if not operation.is_active:
                logger.warning(f"Cannot cancel operation {operation_id}: already complete")
                return False
            
            # Mark as cancelled
            operation.status = OperationStatus.CANCELLED
            operation.completion_time = datetime.now()
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            
            logger.info(f"Cancelled recovery operation {operation_id}")
            return True

    
    def list_operations(self, include_completed: bool = True) -> List[RecoveryOperation]:
        """
        List all recovery operations.
        
        Args:
            include_completed: Whether to include completed operations
            
        Returns:
            List of RecoveryOperation objects
        """
        with self._operations_lock:
            operations = list(self._operations.values())
            
            if not include_completed:
                operations = [op for op in operations if op.is_active]
            
            return operations
    
    def _audit_recovery_operation(
        self,
        operation: RecoveryOperation,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Audit recovery operation for security monitoring.
        
        Args:
            operation: Recovery operation to audit
            status: Current status of the operation
            metadata: Additional metadata for auditing
        """
        if not self.security_service:
            return
        
        try:
            repo_id = getattr(self.repository, 'id', str(self.repository._location))
            
            audit_metadata = {
                'operation_id': operation.operation_id,
                'snapshot_id': operation.snapshot_id,
                'recovery_type': operation.recovery_type.value,
                'target_path': operation.target_path,
                'status': status
            }
            
            if metadata:
                audit_metadata.update(metadata)
            
            # Add progress information if available
            if operation.progress:
                audit_metadata['files_processed'] = operation.progress.files_processed
                audit_metadata['bytes_transferred'] = operation.progress.bytes_transferred
            
            success = status in ['completed', 'running']
            
            self.security_service.audit_restore_operation(
                repository=self.repository,
                snapshot_id=operation.snapshot_id,
                target_path=operation.target_path,
                success=success,
                metadata=audit_metadata,
                operation_id=operation.operation_id,
                repository_id=repo_id,
                status=status,
                files_restored=operation.progress.files_processed if operation.progress else 0
            )
            
            logger.debug(f"Recovery operation {operation.operation_id} audited: {status}")
            
        except Exception as e:
            logger.error(f"Failed to audit recovery operation: {e}")
            # Don't fail the recovery operation if auditing fails
    
    def _validate_encryption_keys(self, snapshot_id: str) -> None:
        """
        Validate encryption keys for encrypted snapshots.
        
        Args:
            snapshot_id: Snapshot ID to validate keys for
            
        Raises:
            EncryptionKeyError: If encryption keys are missing or invalid
        """
        if not self.security_service:
            logger.debug("SecurityService not available, skipping encryption key validation")
            return
        
        try:
            # Verify repository encryption status
            encryption_status = self.security_service.verify_repository_encryption(
                self.repository
            )
            
            if encryption_status.is_encrypted:
                # Check if we have valid credentials
                if not self.repository._password:
                    raise EncryptionKeyError(
                        f"Snapshot {snapshot_id} is encrypted but no decryption key is available"
                    )
                
                logger.debug(
                    f"Encryption keys validated for snapshot {snapshot_id}: "
                    f"{encryption_status.encryption_algorithm}"
                )
            
        except EncryptionKeyError:
            raise
        except Exception as e:
            logger.warning(f"Encryption key validation failed: {e}")
            # Continue if validation fails but password is available
    
    def _validate_target_access_control(self, target_path: str) -> None:
        """
        Validate access control for recovery target location.
        
        Args:
            target_path: Target path for recovery
            
        Raises:
            RestoreTargetError: If access control validation fails
        """
        if not self.security_service:
            logger.debug("SecurityService not available, skipping access control validation")
            return
        
        try:
            target = Path(target_path)
            
            # Check if target directory is writable
            if target.exists():
                if not os.access(target, os.W_OK):
                    raise RestoreTargetError(
                        f"Target path is not writable: {target_path}"
                    )
            else:
                # Check if parent directory is writable
                parent = target.parent
                if not parent.exists():
                    raise RestoreTargetError(
                        f"Parent directory does not exist: {parent}"
                    )
                if not os.access(parent, os.W_OK):
                    raise RestoreTargetError(
                        f"Parent directory is not writable: {parent}"
                    )
            
            logger.debug(f"Access control validated for target: {target_path}")
            
        except RestoreTargetError:
            raise
        except Exception as e:
            logger.warning(f"Access control validation failed: {e}")
            # Continue if validation fails but basic checks passed
    
    def _execute_full_recovery(self, operation: RecoveryOperation) -> None:
        """
        Execute full recovery using the RestoreManager for backward compatibility.
        
        Args:
            operation: RecoveryOperation to execute
        """
        operation.status = OperationStatus.RUNNING
        logger.info(f"Executing full recovery for operation {operation.operation_id}")
        
        # Audit operation start
        self._audit_recovery_operation(operation, 'running', {'phase': 'start'})
        
        # Validate encryption keys
        try:
            self._validate_encryption_keys(operation.snapshot_id)
        except EncryptionKeyError as e:
            logger.error(f"Encryption key validation failed: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type="EncryptionKeyError",
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            self.state_manager.save_operation(operation)
            self._audit_recovery_operation(operation, 'failed', {'error': str(e)})
            return
        
        # Validate target access control
        try:
            self._validate_target_access_control(operation.target_path)
        except RestoreTargetError as e:
            logger.error(f"Access control validation failed: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type="RestoreTargetError",
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            self.state_manager.save_operation(operation)
            self._audit_recovery_operation(operation, 'failed', {'error': str(e)})
            return
        
        try:
            # Convert new RecoveryOptions to legacy RestoreOptions
            legacy_options = self._convert_to_legacy_options(operation)
            
            # Execute restore using existing RestoreManager
            result = self.restore_manager.restore_snapshot(
                operation.snapshot_id,
                legacy_options
            )
            
            # Update operation with results
            operation.progress.files_processed = result.files_restored
            operation.progress.total_files = result.files_restored + result.files_skipped
            operation.progress.bytes_transferred = result.bytes_restored
            
            if result.success:
                operation.status = OperationStatus.COMPLETED
                logger.info(f"Full recovery operation {operation.operation_id} completed successfully")
                self._audit_recovery_operation(operation, 'completed', {
                    'files_restored': result.files_restored,
                    'bytes_restored': result.bytes_restored
                })
            else:
                operation.status = OperationStatus.FAILED
                error_msg = "; ".join(result.errors) if result.errors else "Unknown error"
                operation.error_details = ErrorDetails(
                    error_type="RestoreError",
                    error_message=error_msg,
                    timestamp=datetime.now(),
                    is_recoverable=False
                )
                logger.error(f"Full recovery operation {operation.operation_id} failed: {error_msg}")
                self._audit_recovery_operation(operation, 'failed', {'error': error_msg})
            
            operation.completion_time = datetime.now()
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            
        except Exception as e:
            logger.error(f"Exception during full recovery {operation.operation_id}: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            
            # Audit the failure
            self._audit_recovery_operation(operation, 'failed', {
                'error_type': type(e).__name__,
                'error': str(e)
            })
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            raise
    
    async def _apply_selection_template(
        self,
        selection_criteria: SelectionCriteria
    ) -> SelectionCriteria:
        """
        Apply selection template if specified in criteria.
        
        Args:
            selection_criteria: Original selection criteria
            
        Returns:
            SelectionCriteria with template applied
            
        Raises:
            SelectionValidationError: If template application fails
        """
        if not selection_criteria.selection_template_id:
            return selection_criteria
        
        if not self.selection_manager:
            logger.warning(
                "Selection template specified but SelectionManager not available. "
                "Using criteria as-is."
            )
            return selection_criteria
        
        try:
            # Retrieve template from selection manager
            template = self.selection_manager.template_manager.get_template(
                selection_criteria.selection_template_id
            )
            
            if not template:
                raise SelectionValidationError(
                    f"Selection template not found: {selection_criteria.selection_template_id}"
                )
            
            # Merge template patterns with criteria patterns
            merged_include = list(set(
                selection_criteria.include_patterns + 
                [rule.pattern for rule in template.config.include_patterns]
            ))
            merged_exclude = list(set(
                selection_criteria.exclude_patterns + 
                [rule.pattern for rule in template.config.exclude_patterns]
            ))
            
            # Create merged criteria
            from dataclasses import replace
            merged_criteria = replace(
                selection_criteria,
                include_patterns=merged_include,
                exclude_patterns=merged_exclude
            )
            
            logger.info(
                f"Applied selection template '{template.name}': "
                f"{len(merged_include)} include patterns, {len(merged_exclude)} exclude patterns"
            )
            
            return merged_criteria
            
        except Exception as e:
            logger.error(f"Failed to apply selection template: {e}")
            raise SelectionValidationError(
                f"Failed to apply selection template: {e}"
            ) from e
    
    async def _validate_selection_criteria(
        self,
        selection_criteria: SelectionCriteria,
        snapshot_id: str
    ) -> None:
        """
        Validate selection criteria against snapshot contents.
        
        Args:
            selection_criteria: Selection criteria to validate
            snapshot_id: Snapshot ID to validate against
            
        Raises:
            SelectionValidationError: If validation fails
        """
        if not self.selection_manager:
            logger.debug("SelectionManager not available, skipping selection validation")
            return
        
        try:
            # Create a temporary selection config for validation
            from .selection_models import SelectionConfig, PrecedenceConfig
            
            # Convert patterns to PatternRule objects
            from .selection_models import PatternRule, PatternSyntax, PathComponent
            
            include_rules = [
                PatternRule(
                    pattern=pattern,
                    syntax=PatternSyntax.GLOB,
                    case_sensitive=False,
                    applies_to=PathComponent.FULL_PATH
                )
                for pattern in selection_criteria.include_patterns
            ]
            
            exclude_rules = [
                PatternRule(
                    pattern=pattern,
                    syntax=PatternSyntax.GLOB,
                    case_sensitive=False,
                    applies_to=PathComponent.FULL_PATH
                )
                for pattern in selection_criteria.exclude_patterns
            ]
            
            config = SelectionConfig(
                name=f"recovery_validation_{snapshot_id}",
                include_patterns=include_rules,
                exclude_patterns=exclude_rules,
                precedence_config=PrecedenceConfig()
            )
            
            # Validate the configuration
            validation_result = await self.selection_manager.validation_service.validate_selection_config(
                config
            )
            
            if not validation_result.is_valid:
                error_messages = [e.message for e in validation_result.errors]
                raise SelectionValidationError(
                    f"Selection criteria validation failed: {'; '.join(error_messages)}"
                )
            
            # Log warnings
            for warning in validation_result.warnings:
                logger.warning(f"Selection criteria warning: {warning.message}")
            
            logger.debug("Selection criteria validated successfully")
            
        except SelectionValidationError:
            raise
        except Exception as e:
            logger.error(f"Selection criteria validation failed: {e}")
            raise SelectionValidationError(
                f"Failed to validate selection criteria: {e}"
            ) from e
    
    def _create_recovery_specific_selection(
        self,
        selection_criteria: SelectionCriteria,
        operation_id: str
    ) -> SelectionCriteria:
        """
        Create recovery-specific selection criteria modifications.
        
        This allows for recovery-specific adjustments without affecting
        the original template.
        
        Args:
            selection_criteria: Original selection criteria
            operation_id: Recovery operation ID
            
        Returns:
            Modified SelectionCriteria for recovery
        """
        # For now, return criteria as-is
        # Future enhancements could add recovery-specific patterns or filters
        logger.debug(f"Created recovery-specific selection for operation {operation_id}")
        return selection_criteria
    
    def _execute_selective_recovery(
        self,
        operation: RecoveryOperation,
        selection_criteria: SelectionCriteria
    ) -> None:
        """
        Execute selective recovery using the RestoreManager.
        
        Args:
            operation: RecoveryOperation to execute
            selection_criteria: Criteria for file selection
        """
        operation.status = OperationStatus.RUNNING
        logger.info(f"Executing selective recovery for operation {operation.operation_id}")
        
        try:
            # Apply selection template if specified (synchronous wrapper for async)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            selection_criteria = loop.run_until_complete(
                self._apply_selection_template(selection_criteria)
            )
            
            # Validate selection criteria against snapshot
            loop.run_until_complete(
                self._validate_selection_criteria(selection_criteria, operation.snapshot_id)
            )
            
            # Create recovery-specific selection
            selection_criteria = self._create_recovery_specific_selection(
                selection_criteria,
                operation.operation_id
            )
            
            # Convert new RecoveryOptions to legacy RestoreOptions
            legacy_options = self._convert_to_legacy_options(operation)
            
            # Apply selection criteria to legacy options
            if selection_criteria.include_patterns:
                legacy_options.include_paths = [
                    Path(pattern) for pattern in selection_criteria.include_patterns
                ]
            
            if selection_criteria.exclude_patterns:
                legacy_options.exclude_paths = [
                    Path(pattern) for pattern in selection_criteria.exclude_patterns
                ]
            
            # Execute restore using existing RestoreManager
            result = self.restore_manager.restore_snapshot(
                operation.snapshot_id,
                legacy_options
            )
            
            # Update operation with results
            operation.progress.files_processed = result.files_restored
            operation.progress.total_files = result.files_restored + result.files_skipped
            operation.progress.bytes_transferred = result.bytes_restored
            
            if result.success:
                operation.status = OperationStatus.COMPLETED
                logger.info(f"Selective recovery operation {operation.operation_id} completed successfully")
                self._audit_recovery_operation(operation, 'completed', {
                    'files_restored': result.files_restored,
                    'bytes_restored': result.bytes_restored,
                    'selection_applied': True
                })
            else:
                operation.status = OperationStatus.FAILED
                error_msg = "; ".join(result.errors) if result.errors else "Unknown error"
                operation.error_details = ErrorDetails(
                    error_type="RestoreError",
                    error_message=error_msg,
                    timestamp=datetime.now(),
                    is_recoverable=False
                )
                logger.error(f"Selective recovery operation {operation.operation_id} failed: {error_msg}")
                self._audit_recovery_operation(operation, 'failed', {'error': error_msg})
            
            operation.completion_time = datetime.now()
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            
        except Exception as e:
            logger.error(f"Exception during selective recovery {operation.operation_id}: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            
            # Audit the failure
            self._audit_recovery_operation(operation, 'failed', {
                'error_type': type(e).__name__,
                'error': str(e)
            })
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            raise
    
    def _convert_to_legacy_options(self, operation: RecoveryOperation) -> LegacyRestoreOptions:
        """
        Convert new RecoveryOptions to legacy RestoreOptions for backward compatibility.
        
        Args:
            operation: RecoveryOperation containing options to convert
            
        Returns:
            LegacyRestoreOptions instance
        """
        legacy_options = LegacyRestoreOptions()
        
        # Get options from separate storage
        options = self._operation_options.get(operation.operation_id)
        
        if options:
            legacy_options.target_path = Path(operation.target_path)
            legacy_options.preserve_permissions = options.preserve_permissions
            legacy_options.verify_after_restore = options.verify_integrity
            
            # Map conflict resolution based on overwrite setting
            from .restore_manager import ConflictResolution
            if options.overwrite_existing:
                legacy_options.conflict_resolution = ConflictResolution.OVERWRITE
            else:
                legacy_options.conflict_resolution = ConflictResolution.SKIP
        else:
            legacy_options.target_path = Path(operation.target_path)
        
        return legacy_options

    
    def cleanup_operation(self, operation_id: str) -> bool:
        """
        Clean up a completed recovery operation.
        
        This removes the operation from memory and optionally from persistent storage.
        
        Args:
            operation_id: ID of the operation to clean up
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        with self._operations_lock:
            operation = self._operations.get(operation_id)
            
            if not operation:
                logger.warning(f"Cannot cleanup operation {operation_id}: not found")
                return False
            
            if operation.is_active:
                logger.warning(f"Cannot cleanup operation {operation_id}: still active")
                return False
            
            # Remove from memory
            del self._operations[operation_id]
            
            # Remove from persistent storage
            self.state_manager.delete_operation(operation_id)
            
            logger.info(f"Cleaned up recovery operation {operation_id}")
            return True
    
    def cleanup_old_operations(self, days: int = 30) -> int:
        """
        Clean up old completed operations.
        
        Args:
            days: Number of days to keep operation history
            
        Returns:
            Number of operations cleaned up
        """
        # Clean up from persistent storage
        cleaned_count = self.state_manager.cleanup_old_operations(days)
        
        # Clean up from memory
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        with self._operations_lock:
            operations_to_remove = []
            
            for operation_id, operation in self._operations.items():
                if operation.is_complete():
                    completion_time = operation.completion_time or operation.start_time
                    if completion_time.timestamp() < cutoff_time:
                        operations_to_remove.append(operation_id)
            
            for operation_id in operations_to_remove:
                del self._operations[operation_id]
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old recovery operations")
        return cleaned_count
    
    def _load_persisted_operations(self) -> None:
        """Load persisted operations from storage on initialization."""
        try:
            # Load only active operations
            active_statuses = [
                OperationStatus.PENDING,
                OperationStatus.RUNNING,
                OperationStatus.VALIDATING
            ]
            
            persisted_operations = self.state_manager.list_operations(
                status_filter=active_statuses
            )
            
            with self._operations_lock:
                for operation in persisted_operations:
                    self._operations[operation.operation_id] = operation
            
            if persisted_operations:
                logger.info(f"Loaded {len(persisted_operations)} persisted recovery operations")
            
        except Exception as e:
            logger.error(f"Failed to load persisted operations: {e}")
