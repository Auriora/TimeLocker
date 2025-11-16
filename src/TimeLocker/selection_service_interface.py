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
from pathlib import Path
from typing import Any, Dict, List, Optional

from .selection_manager import SelectionManager, DataSelection
from .selection_models import (
    SelectionConfig,
    SelectionResult,
    SizeEstimate,
    PreviewResult,
    ValidationResult
)

logger = logging.getLogger(__name__)


class SelectionServiceInterface:
    """
    Service interface for integrating selection management with backup operations.
    
    This interface provides a clean API for backup workflows to interact with
    the selection management system, including template resolution, selection
    evaluation, and override functionality.
    """
    
    def __init__(self, selection_manager: Optional[SelectionManager] = None):
        """
        Initialize the selection service interface.
        
        Args:
            selection_manager: SelectionManager instance (creates new if None)
        """
        self.selection_manager = selection_manager or SelectionManager()
        logger.info("SelectionServiceInterface initialized")
    
    async def create_selection_from_template(
        self,
        template_id: str,
        overrides: Optional[Dict[str, Any]] = None
    ) -> DataSelection:
        """
        Create a selection from a template with optional overrides.
        
        Args:
            template_id: ID of the template to use
            overrides: Optional dictionary of configuration overrides
            
        Returns:
            DataSelection: Created selection
            
        Raises:
            Exception: If template not found or creation fails
        """
        logger.info(f"Creating selection from template: {template_id}")
        
        # Get template
        template = self.selection_manager.template_manager.get_template(template_id)
        
        # Start with template configuration
        config = template.selection_config
        
        # Apply overrides if provided
        if overrides:
            config = self._apply_overrides(config, overrides)
            logger.debug(f"Applied {len(overrides)} override(s) to template configuration")
        
        # Create selection
        selection = await self.selection_manager.create_selection(config)
        
        # Add template metadata
        selection.metadata['template_id'] = template_id
        selection.metadata['template_name'] = template.name
        selection.metadata['overrides_applied'] = bool(overrides)
        
        logger.info(f"Created selection from template '{template.name}'")
        
        return selection
    
    async def create_selection_from_config(
        self,
        config: SelectionConfig
    ) -> DataSelection:
        """
        Create a selection from a configuration.
        
        Args:
            config: Selection configuration
            
        Returns:
            DataSelection: Created selection
        """
        logger.info("Creating selection from configuration")
        return await self.selection_manager.create_selection(config)
    
    async def evaluate_selection_for_backup(
        self,
        selection: DataSelection,
        source_paths: List[Path]
    ) -> SelectionResult:
        """
        Evaluate a selection for backup operations.
        
        Args:
            selection: Data selection to evaluate
            source_paths: Source paths for backup
            
        Returns:
            SelectionResult: Evaluation result
        """
        logger.info(f"Evaluating selection for backup with {len(source_paths)} source path(s)")
        return await self.selection_manager.evaluate_selection(selection, source_paths)
    
    async def estimate_backup_size(
        self,
        selection: DataSelection,
        source_paths: List[Path]
    ) -> SizeEstimate:
        """
        Estimate the size of a backup based on selection.
        
        Args:
            selection: Data selection
            source_paths: Source paths for backup
            
        Returns:
            SizeEstimate: Size estimation
        """
        logger.info("Estimating backup size")
        return await self.selection_manager.estimate_selection_size(selection, source_paths)
    
    async def preview_backup_selection(
        self,
        selection: DataSelection,
        source_paths: List[Path],
        limit: int = 100
    ) -> PreviewResult:
        """
        Preview what would be included in a backup.
        
        Args:
            selection: Data selection
            source_paths: Source paths for backup
            limit: Maximum number of files to preview
            
        Returns:
            PreviewResult: Preview result
        """
        logger.info("Generating backup preview")
        return await self.selection_manager.preview_selection(selection, source_paths, limit)
    
    async def validate_backup_selection(
        self,
        selection: DataSelection
    ) -> ValidationResult:
        """
        Validate a selection before backup.
        
        Args:
            selection: Data selection to validate
            
        Returns:
            ValidationResult: Validation result
        """
        logger.info("Validating backup selection")
        return await self.selection_manager.validate_selection(selection)
    
    async def list_available_templates(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List available selection templates.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List of template information dictionaries
        """
        logger.info("Listing available templates")
        
        templates = self.selection_manager.template_manager.list_templates(filters)
        
        # Convert to simple dictionaries
        template_list = []
        for template in templates:
            template_list.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'tags': template.tags,
                'is_system_template': template.is_system_template,
                'usage_count': template.usage_count
            })
        
        return template_list
    
    async def get_template_info(self, template_id: str) -> Dict[str, Any]:
        """
        Get information about a specific template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Dictionary with template information
        """
        logger.info(f"Getting template info: {template_id}")
        
        template = self.selection_manager.template_manager.get_template(template_id)
        
        return {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'tags': template.tags,
            'is_system_template': template.is_system_template,
            'usage_count': template.usage_count,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat(),
            'include_paths': [str(p) for p in template.selection_config.include_paths],
            'exclude_paths': [str(p) for p in template.selection_config.exclude_paths],
            'include_pattern_count': len(template.selection_config.include_patterns),
            'exclude_pattern_count': len(template.selection_config.exclude_patterns),
            'pattern_groups': template.selection_config.pattern_groups
        }
    
    def _apply_overrides(
        self,
        config: SelectionConfig,
        overrides: Dict[str, Any]
    ) -> SelectionConfig:
        """
        Apply overrides to a selection configuration.
        
        Args:
            config: Base configuration
            overrides: Dictionary of overrides
            
        Returns:
            SelectionConfig: Configuration with overrides applied
        """
        # Create a copy of the configuration
        from copy import deepcopy
        new_config = deepcopy(config)
        
        # Apply overrides
        if 'include_paths' in overrides:
            paths = overrides['include_paths']
            new_config.include_paths = [Path(p) if isinstance(p, str) else p for p in paths]
        
        if 'exclude_paths' in overrides:
            paths = overrides['exclude_paths']
            new_config.exclude_paths = [Path(p) if isinstance(p, str) else p for p in paths]
        
        if 'include_patterns' in overrides:
            new_config.include_patterns.extend(overrides['include_patterns'])
        
        if 'exclude_patterns' in overrides:
            new_config.exclude_patterns.extend(overrides['exclude_patterns'])
        
        if 'pattern_groups' in overrides:
            new_config.pattern_groups.extend(overrides['pattern_groups'])
        
        if 'case_sensitive' in overrides:
            new_config.case_sensitive = overrides['case_sensitive']
        
        if 'performance_hints' in overrides:
            new_config.performance_hints.update(overrides['performance_hints'])
        
        return new_config
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dictionary with statistics
        """
        return self.selection_manager.get_statistics()
