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

"""
Backup CLI Handler for data selection integration.

This module provides CLI-specific integration between backup operations
and the data selection system, handling template resolution, validation,
and translation to backup job configurations.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from TimeLocker.selection_manager import SelectionManager, SelectionError
from TimeLocker.selection_template_manager import TemplateNotFoundError
from TimeLocker.interfaces.backup_orchestrator import (
    IBackupOrchestrator,
    BackupResult,
    BackupOrchestratorError
)
from TimeLocker.interfaces.data_models import (
    BackupJobConfig,
    ExecutionMode,
    RetryConfig,
    NotificationConfig
)

logger = logging.getLogger(__name__)


class BackupCLIHandlerError(Exception):
    """Base exception for BackupCLIHandler operations"""
    pass


class SelectionTemplateNotFoundError(BackupCLIHandlerError):
    """Exception raised when a selection template is not found"""
    pass


class InvalidSelectionConfigError(BackupCLIHandlerError):
    """Exception raised when a selection configuration is invalid"""
    pass


class BackupCLIHandler:
    """
    Handles CLI commands for backup operations with data selection integration.
    
    This handler provides the bridge between CLI commands and the backup
    orchestration system, with special focus on data selection template
    resolution and validation.
    
    Responsibilities:
    - Selection template resolution and validation
    - CLI parameter translation to backup job configuration
    - User-friendly error handling and messaging
    - Help text generation and consistency
    
    Attributes:
        selection_manager: Manager for data selection operations
        backup_orchestrator: Orchestrator for backup job execution
    """
    
    def __init__(
        self,
        selection_manager: SelectionManager,
        backup_orchestrator: IBackupOrchestrator
    ):
        """
        Initialize the backup CLI handler.
        
        Args:
            selection_manager: SelectionManager instance for template operations
            backup_orchestrator: BackupOrchestrator instance for job execution
            
        Raises:
            ValueError: If required dependencies are None
        """
        if selection_manager is None:
            raise ValueError("selection_manager cannot be None")
        if backup_orchestrator is None:
            raise ValueError("backup_orchestrator cannot be None")
        
        self.selection_manager = selection_manager
        self.backup_orchestrator = backup_orchestrator
        
        logger.info("BackupCLIHandler initialized")
    
    async def validate_selection_exists(self, selection_name: str) -> bool:
        """
        Check if a selection template exists.
        
        Args:
            selection_name: Name of the selection template
            
        Returns:
            True if the template exists, False otherwise
        """
        if not selection_name:
            return False
        
        try:
            template = await self.selection_manager.template_manager.get_template(
                selection_name, by_name=True
            )
            return template is not None
        except TemplateNotFoundError:
            return False
        except Exception as e:
            logger.debug(f"Error checking template existence: {e}")
            return False
    
    async def get_selection_summary(self, selection_name: str) -> str:
        """
        Get human-readable summary of selection template.
        
        Args:
            selection_name: Name of the selection template
            
        Returns:
            Human-readable summary string
            
        Raises:
            SelectionTemplateNotFoundError: If template doesn't exist
        """
        try:
            template = await self.selection_manager.template_manager.get_template(
                selection_name, by_name=True
            )
            
            # Build summary from template configuration
            config = template.selection_config
            summary_parts = [f"Selection: {selection_name}"]
            
            if config.include_paths:
                summary_parts.append(f"  Include paths: {len(config.include_paths)}")
            if config.exclude_paths:
                summary_parts.append(f"  Exclude paths: {len(config.exclude_paths)}")
            if config.include_patterns:
                summary_parts.append(f"  Include patterns: {len(config.include_patterns)}")
            if config.exclude_patterns:
                summary_parts.append(f"  Exclude patterns: {len(config.exclude_patterns)}")
            
            return "\n".join(summary_parts)
            
        except TemplateNotFoundError as e:
            raise SelectionTemplateNotFoundError(
                f"Failed to get template '{selection_name}': {e}"
            ) from e
        except SelectionError as e:
            raise SelectionTemplateNotFoundError(
                f"Failed to get template '{selection_name}': {e}"
            ) from e
    
    async def execute_backup_with_selection(
        self,
        selection_name: str,
        repository: str,
        tags: Optional[List[str]] = None,
        dry_run: bool = False,
        execution_mode: ExecutionMode = ExecutionMode.ON_DEMAND,
        **cli_options
    ) -> BackupResult:
        """
        Execute backup using a named data selection template.
        
        This method resolves the selection template, validates it, translates
        it to a backup job configuration, and executes the backup operation.
        
        Args:
            selection_name: Name of the data selection template
            repository: Repository name or identifier
            tags: Optional list of tags to apply to the backup
            dry_run: Whether to perform a dry run without actual backup
            execution_mode: Execution mode for the backup job
            **cli_options: Additional CLI options to pass through
            
        Returns:
            BackupResult with operation details
            
        Raises:
            SelectionTemplateNotFoundError: If template doesn't exist
            InvalidSelectionConfigError: If template configuration is invalid
            BackupCLIHandlerError: If backup execution fails
        """
        logger.info(f"Executing backup with selection template: {selection_name}")
        
        try:
            # Validate template exists
            if not await self.validate_selection_exists(selection_name):
                error_msg = (
                    f"Selection template '{selection_name}' not found.\n\n"
                    f"💡 Create a selection template using:\n"
                    f"   tl selections create {selection_name} --paths /path/to/backup\n\n"
                    f"Or list available templates:\n"
                    f"   tl selections list"
                )
                raise SelectionTemplateNotFoundError(error_msg)
            
            # Get template by name
            template = await self.selection_manager.template_manager.get_template(
                selection_name, by_name=True
            )
            
            # Validate selection configuration
            validation_result = await self.selection_manager.validate_selection(
                await self.selection_manager.create_selection(template.selection_config)
            )
            
            if not validation_result.is_valid:
                error_messages = [e.message for e in validation_result.errors]
                raise InvalidSelectionConfigError(
                    f"Selection template '{selection_name}' has invalid configuration:\n" +
                    "\n".join(f"  - {msg}" for msg in error_messages)
                )
            
            # Log warnings
            for warning in validation_result.warnings:
                logger.warning(f"Selection validation warning: {warning.message}")
            
            # Translate selection template to backup job configuration
            job_config = self._translate_selection_to_job_config(
                selection_name=selection_name,
                template=template,
                repository=repository,
                tags=tags,
                dry_run=dry_run,
                execution_mode=execution_mode,
                cli_options=cli_options
            )
            
            # Execute backup job
            logger.info(f"Executing backup job: {job_config.job_id}")
            result = self.backup_orchestrator.execute_backup_job(job_config)
            
            logger.info(
                f"Backup completed: status={result.status.value}, "
                f"snapshot_id={result.snapshot_id}"
            )
            
            return result
            
        except SelectionTemplateNotFoundError:
            raise
        except InvalidSelectionConfigError:
            raise
        except BackupOrchestratorError as e:
            logger.error(f"Backup execution failed: {e}")
            raise BackupCLIHandlerError(
                f"Backup execution failed: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            raise BackupCLIHandlerError(
                f"Unexpected error during backup: {e}"
            ) from e
    
    def _translate_selection_to_job_config(
        self,
        selection_name: str,
        template: Any,
        repository: str,
        tags: Optional[List[str]],
        dry_run: bool,
        execution_mode: ExecutionMode,
        cli_options: Dict[str, Any]
    ) -> BackupJobConfig:
        """
        Translate a selection template to a backup job configuration.
        
        This method creates a BackupJobConfig from a selection template,
        incorporating CLI options and defaults.
        
        Args:
            selection_name: Name of the selection template
            template: Selection template object
            repository: Repository name or identifier
            tags: Optional list of tags
            dry_run: Whether this is a dry run
            execution_mode: Execution mode for the job
            cli_options: Additional CLI options
            
        Returns:
            BackupJobConfig ready for execution
        """
        # Generate unique job ID
        job_id = f"backup-{selection_name}-{uuid.uuid4().hex[:8]}"
        
        # Extract tool type from CLI options or use default
        tool_type = cli_options.get('tool_type', 'restic')
        
        # Extract retry configuration from CLI options
        max_retries = cli_options.get('max_retries', 3)
        retry_config = RetryConfig(max_retries=max_retries)
        
        # Extract notification configuration from CLI options
        notify_on_success = cli_options.get('notify_on_success', True)
        notify_on_failure = cli_options.get('notify_on_failure', True)
        notification_config = NotificationConfig(
            enabled=cli_options.get('notifications_enabled', True),
            notify_on_success=notify_on_success,
            notify_on_failure=notify_on_failure
        )
        
        # Create backup job configuration
        job_config = BackupJobConfig(
            job_id=job_id,
            repository_id=repository,
            data_selection_id=selection_name,
            execution_mode=execution_mode,
            tool_type=tool_type,
            tags=tags or [],
            retry_config=retry_config,
            notification_config=notification_config,
            dry_run=dry_run,
            priority=cli_options.get('priority', 0),
            metadata={
                'selection_template': selection_name,
                'cli_invoked': True,
                'cli_options': cli_options
            }
        )
        
        logger.debug(
            f"Translated selection '{selection_name}' to job config: "
            f"job_id={job_config.job_id}, repository={repository}, "
            f"tool={tool_type}, dry_run={dry_run}"
        )
        
        return job_config
    
    def get_available_templates(self) -> List[str]:
        """
        Get list of available selection template names.
        
        Returns:
            List of template names
        """
        try:
            templates = self.selection_manager.template_manager.list_templates()
            return [t.name for t in templates]
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    def suggest_template_creation(self, selection_name: str) -> str:
        """
        Generate a helpful message suggesting how to create a template.
        
        Args:
            selection_name: Name of the missing template
            
        Returns:
            Helpful suggestion message
        """
        available_templates = self.get_available_templates()
        
        message = f"Selection template '{selection_name}' not found.\n\n"
        
        if available_templates:
            message += "Available templates:\n"
            for template_name in available_templates[:5]:  # Show first 5
                message += f"  - {template_name}\n"
            if len(available_templates) > 5:
                message += f"  ... and {len(available_templates) - 5} more\n"
            message += "\n"
        
        message += "To create a new selection template:\n"
        message += f"  tl selections create {selection_name} --paths /path/to/backup\n\n"
        message += "For more information:\n"
        message += "  tl selections --help"
        
        return message
