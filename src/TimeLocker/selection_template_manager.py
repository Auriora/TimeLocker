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
import os
import uuid
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import asdict, dataclass, field

from .selection_models import (
    SelectionTemplate,
    SelectionConfig,
    PatternRule,
    PrecedenceConfig,
    PatternSyntax,
    PathComponent,
    PrecedenceStrategy,
    ConflictResolution
)

logger = logging.getLogger(__name__)


class TemplateNotFoundError(Exception):
    """Raised when a template is not found"""
    pass


class TemplateAlreadyExistsError(Exception):
    """Raised when attempting to create a template with an existing ID"""
    pass


class TemplateValidationError(Exception):
    """Raised when template validation fails"""
    pass


class TemplateImportError(Exception):
    """Raised when template import fails"""
    pass


class TemplateExportError(Exception):
    """Raised when template export fails"""
    pass


@dataclass
class ImportResult:
    """
    Result of a template import operation.
    
    Attributes:
        success: Whether the import was successful
        imported_count: Number of templates successfully imported
        skipped_count: Number of templates skipped
        failed_count: Number of templates that failed to import
        imported_ids: List of IDs of imported templates
        skipped_ids: List of IDs of skipped templates
        errors: List of error messages
        warnings: List of warning messages
    """
    success: bool
    imported_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    imported_ids: List[str] = field(default_factory=list)
    skipped_ids: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SelectionTemplateManager:
    """
    Manages selection templates with persistent storage.
    
    Provides CRUD operations for selection templates, including creation,
    retrieval, listing, updating, duplication, and deletion. Templates are
    stored in JSON format in the configuration directory.
    
    Attributes:
        storage_dir: Directory where templates are stored
        templates_cache: In-memory cache of loaded templates
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the template manager.
        
        Args:
            storage_dir: Optional directory for template storage.
                        Defaults to XDG_DATA_HOME/timelocker/templates
        """
        if storage_dir is None:
            # Use centralized path resolver for XDG compliance
            from .config.configuration_path_resolver import ConfigurationPathResolver
            
            # Templates are user data, so use XDG_DATA_HOME
            xdg_data_home = os.environ.get('XDG_DATA_HOME')
            if xdg_data_home:
                data_dir = Path(xdg_data_home) / "timelocker"
            else:
                data_dir = Path.home() / ".local" / "share" / "timelocker"
            
            storage_dir = data_dir / "templates"
        
        self.storage_dir = storage_dir
        self.templates_cache: Dict[str, SelectionTemplate] = {}
        
        # Ensure storage directory exists
        self._ensure_storage_directory()
        
        # Load existing templates into cache
        self._load_templates()
    
    def _ensure_storage_directory(self) -> None:
        """Ensure the template storage directory exists"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Template storage directory: {self.storage_dir}")
        except Exception as e:
            logger.error(f"Failed to create template storage directory: {e}")
            raise TemplateValidationError(f"Cannot create storage directory: {e}")
    
    def _load_templates(self) -> None:
        """Load all templates from storage into cache"""
        try:
            if not self.storage_dir.exists():
                return
            
            for template_file in self.storage_dir.glob("*.json"):
                try:
                    template = self._load_template_from_file(template_file)
                    self.templates_cache[template.id] = template
                    logger.debug(f"Loaded template: {template.name} ({template.id})")
                except Exception as e:
                    logger.warning(f"Failed to load template from {template_file}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
    
    def _load_template_from_file(self, file_path: Path) -> SelectionTemplate:
        """
        Load a template from a JSON file.
        
        Args:
            file_path: Path to the template file
            
        Returns:
            SelectionTemplate: The loaded template
            
        Raises:
            TemplateValidationError: If the template file is invalid
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            return self._deserialize_template(data)
        
        except json.JSONDecodeError as e:
            raise TemplateValidationError(f"Invalid JSON in template file: {e}")
        except Exception as e:
            raise TemplateValidationError(f"Failed to load template: {e}")
    
    def _save_template_to_file(self, template: SelectionTemplate) -> None:
        """
        Save a template to a JSON file.
        
        Args:
            template: The template to save
            
        Raises:
            TemplateValidationError: If saving fails
        """
        try:
            file_path = self.storage_dir / f"{template.id}.json"
            data = self._serialize_template(template)
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved template: {template.name} to {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
            raise TemplateValidationError(f"Cannot save template: {e}")
    
    def _delete_template_file(self, template_id: str) -> None:
        """
        Delete a template file from storage.
        
        Args:
            template_id: ID of the template to delete
        """
        try:
            file_path = self.storage_dir / f"{template_id}.json"
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted template file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete template file: {e}")
    
    def _serialize_template(self, template: SelectionTemplate) -> Dict[str, Any]:
        """
        Serialize a template to a dictionary for JSON storage.
        
        Args:
            template: The template to serialize
            
        Returns:
            Dict containing serialized template data
        """
        data = {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat(),
            'created_by': template.created_by,
            'tags': template.tags,
            'usage_count': template.usage_count,
            'is_system_template': template.is_system_template,
            'metadata': template.metadata,
            'selection_config': self._serialize_selection_config(template.selection_config)
        }
        return data
    
    def _serialize_selection_config(self, config: SelectionConfig) -> Dict[str, Any]:
        """Serialize a SelectionConfig to a dictionary"""
        return {
            'include_paths': [str(p) for p in config.include_paths],
            'exclude_paths': [str(p) for p in config.exclude_paths],
            'include_patterns': [self._serialize_pattern_rule(p) for p in config.include_patterns],
            'exclude_patterns': [self._serialize_pattern_rule(p) for p in config.exclude_patterns],
            'pattern_groups': config.pattern_groups,
            'precedence_config': self._serialize_precedence_config(config.precedence_config),
            'case_sensitive': config.case_sensitive,
            'performance_hints': config.performance_hints
        }
    
    def _serialize_pattern_rule(self, rule: PatternRule) -> Dict[str, Any]:
        """Serialize a PatternRule to a dictionary"""
        return {
            'pattern': rule.pattern,
            'syntax': rule.syntax.value,
            'case_sensitive': rule.case_sensitive,
            'applies_to': rule.applies_to.value,
            'priority': rule.priority,
            'metadata': rule.metadata
        }
    
    def _serialize_precedence_config(self, config: PrecedenceConfig) -> Dict[str, Any]:
        """Serialize a PrecedenceConfig to a dictionary"""
        return {
            'default_strategy': config.default_strategy.value,
            'path_specific_rules': {k: v.value for k, v in config.path_specific_rules.items()},
            'specificity_weight': config.specificity_weight,
            'explicit_override_weight': config.explicit_override_weight,
            'pattern_type_priority': {k.value: v for k, v in config.pattern_type_priority.items()},
            'conflict_resolution': config.conflict_resolution.value
        }
    
    def _deserialize_template(self, data: Dict[str, Any]) -> SelectionTemplate:
        """
        Deserialize a template from a dictionary.
        
        Args:
            data: Dictionary containing template data
            
        Returns:
            SelectionTemplate: The deserialized template
        """
        selection_config = self._deserialize_selection_config(data['selection_config'])
        
        return SelectionTemplate(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            selection_config=selection_config,
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            created_by=data.get('created_by'),
            tags=data.get('tags', []),
            usage_count=data.get('usage_count', 0),
            is_system_template=data.get('is_system_template', False),
            metadata=data.get('metadata', {})
        )
    
    def _deserialize_selection_config(self, data: Dict[str, Any]) -> SelectionConfig:
        """Deserialize a SelectionConfig from a dictionary"""
        return SelectionConfig(
            include_paths=[Path(p) for p in data.get('include_paths', [])],
            exclude_paths=[Path(p) for p in data.get('exclude_paths', [])],
            include_patterns=[self._deserialize_pattern_rule(p) for p in data.get('include_patterns', [])],
            exclude_patterns=[self._deserialize_pattern_rule(p) for p in data.get('exclude_patterns', [])],
            pattern_groups=data.get('pattern_groups', []),
            precedence_config=self._deserialize_precedence_config(data.get('precedence_config', {})),
            case_sensitive=data.get('case_sensitive', False),
            performance_hints=data.get('performance_hints', {})
        )
    
    def _deserialize_pattern_rule(self, data: Dict[str, Any]) -> PatternRule:
        """Deserialize a PatternRule from a dictionary"""
        return PatternRule(
            pattern=data['pattern'],
            syntax=PatternSyntax(data.get('syntax', 'glob')),
            case_sensitive=data.get('case_sensitive', False),
            applies_to=PathComponent(data.get('applies_to', 'full_path')),
            priority=data.get('priority', 100),
            metadata=data.get('metadata', {})
        )
    
    def _deserialize_precedence_config(self, data: Dict[str, Any]) -> PrecedenceConfig:
        """Deserialize a PrecedenceConfig from a dictionary"""
        if not data:
            return PrecedenceConfig()
        
        return PrecedenceConfig(
            default_strategy=PrecedenceStrategy(data.get('default_strategy', 'exclude_first')),
            path_specific_rules={
                k: PrecedenceStrategy(v) for k, v in data.get('path_specific_rules', {}).items()
            },
            specificity_weight=data.get('specificity_weight', 1.0),
            explicit_override_weight=data.get('explicit_override_weight', 1.0),
            pattern_type_priority={
                PatternSyntax(k): v for k, v in data.get('pattern_type_priority', {
                    'literal': 300,
                    'glob': 200,
                    'regex': 100
                }).items()
            },
            conflict_resolution=ConflictResolution(data.get('conflict_resolution', 'warn'))
        )
    
    def _validate_template(self, template: SelectionTemplate) -> None:
        """
        Validate a template before saving.
        
        Args:
            template: The template to validate
            
        Raises:
            TemplateValidationError: If validation fails
        """
        if not template.id:
            raise TemplateValidationError("Template ID cannot be empty")
        
        if not template.name:
            raise TemplateValidationError("Template name cannot be empty")
        
        if not template.selection_config:
            raise TemplateValidationError("Template must have a selection configuration")
        
        # Validate that at least one inclusion criterion exists
        config = template.selection_config
        if not (config.include_paths or config.include_patterns or config.pattern_groups):
            raise TemplateValidationError(
                "Template must have at least one include path, pattern, or pattern group"
            )
    
    def create_template(self, template: SelectionTemplate) -> str:
        """
        Create a new selection template.
        
        Args:
            template: The template to create
            
        Returns:
            str: The ID of the created template
            
        Raises:
            TemplateAlreadyExistsError: If a template with the same ID exists
            TemplateValidationError: If the template is invalid
        """
        # Validate template
        self._validate_template(template)
        
        # Check if template already exists
        if template.id in self.templates_cache:
            raise TemplateAlreadyExistsError(f"Template with ID '{template.id}' already exists")
        
        # Set timestamps
        now = datetime.utcnow()
        template.created_at = now
        template.updated_at = now
        
        # Save to storage
        self._save_template_to_file(template)
        
        # Add to cache
        self.templates_cache[template.id] = template
        
        logger.info(f"Created template: {template.name} ({template.id})")
        return template.id
    
    def get_template_by_name(self, name: str) -> Optional[SelectionTemplate]:
        """
        Get a template by name.
        
        Args:
            name: The name of the template to retrieve
            
        Returns:
            SelectionTemplate if found, None otherwise
            
        Note:
            This method searches through all templates to find a match by name.
            For better performance with large template collections, consider
            maintaining a name-to-ID index.
        """
        for template in self.templates_cache.values():
            if template.name == name:
                # Increment usage count
                template.usage_count += 1
                template.updated_at = datetime.utcnow()
                self._save_template_to_file(template)
                return template
        return None
    
    def get_template(self, identifier: str, by_name: bool = False) -> SelectionTemplate:
        """
        Get a template by ID or name.
        
        Args:
            identifier: Template ID or name
            by_name: If True, treat identifier as name; if False, treat as ID
            
        Returns:
            SelectionTemplate: The requested template
            
        Raises:
            TemplateNotFoundError: If the template is not found
        """
        if by_name:
            template = self.get_template_by_name(identifier)
            if template is None:
                raise TemplateNotFoundError(f"Template with name '{identifier}' not found")
            return template
        else:
            # Existing ID-based lookup
            if identifier not in self.templates_cache:
                raise TemplateNotFoundError(f"Template with ID '{identifier}' not found")
            
            # Increment usage count
            template = self.templates_cache[identifier]
            template.usage_count += 1
            template.updated_at = datetime.utcnow()
            
            # Save updated usage count
            self._save_template_to_file(template)
            
            return template

    def resolve_template(self, identifier: str) -> SelectionTemplate:
        """
        Resolve a template identifier or name to a template object.
        
        This helper first attempts to load by ID and falls back to name-based
        lookup, providing a single canonical entry point for modules that
        accept either form.
        
        Args:
            identifier: Template ID or human-friendly name
        
        Returns:
            SelectionTemplate matching the provided identifier
        
        Raises:
            TemplateNotFoundError: If no template matches the identifier
        """
        if not identifier:
            raise TemplateNotFoundError("Template identifier cannot be empty")
        
        try:
            return self.get_template(identifier)
        except TemplateNotFoundError:
            template = self.get_template(identifier, by_name=True)
            logger.info(
                "Resolved selection identifier '%s' to template id '%s'",
                identifier,
                template.id
            )
            return template
    
    def list_templates(self, filters: Optional[Dict[str, Any]] = None) -> List[SelectionTemplate]:
        """
        List all templates with optional filtering.
        
        Args:
            filters: Optional dictionary of filters to apply:
                - tags: List of tags (templates must have at least one)
                - name_contains: String that must be in the template name
                - is_system_template: Boolean to filter system/user templates
                - created_by: Filter by creator
                
        Returns:
            List[SelectionTemplate]: List of matching templates
        """
        templates = list(self.templates_cache.values())
        
        if not filters:
            return templates
        
        # Apply filters
        filtered_templates = []
        for template in templates:
            # Tag filter
            if 'tags' in filters:
                required_tags = filters['tags']
                if not any(tag in template.tags for tag in required_tags):
                    continue
            
            # Name filter
            if 'name_contains' in filters:
                if filters['name_contains'].lower() not in template.name.lower():
                    continue
            
            # System template filter
            if 'is_system_template' in filters:
                if template.is_system_template != filters['is_system_template']:
                    continue
            
            # Creator filter
            if 'created_by' in filters:
                if template.created_by != filters['created_by']:
                    continue
            
            filtered_templates.append(template)
        
        return filtered_templates
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> SelectionTemplate:
        """
        Update an existing template.
        
        Args:
            template_id: The ID of the template to update
            updates: Dictionary of fields to update
            
        Returns:
            SelectionTemplate: The updated template
            
        Raises:
            TemplateNotFoundError: If the template is not found
            TemplateValidationError: If the update is invalid
        """
        if template_id not in self.templates_cache:
            raise TemplateNotFoundError(f"Template with ID '{template_id}' not found")
        
        template = self.templates_cache[template_id]
        
        # Prevent updating system templates
        if template.is_system_template and 'is_system_template' not in updates:
            raise TemplateValidationError("Cannot modify system templates")
        
        # Apply updates
        if 'name' in updates:
            template.name = updates['name']
        
        if 'description' in updates:
            template.description = updates['description']
        
        if 'tags' in updates:
            template.tags = updates['tags']
        
        if 'selection_config' in updates:
            if isinstance(updates['selection_config'], dict):
                template.selection_config = self._deserialize_selection_config(updates['selection_config'])
            else:
                template.selection_config = updates['selection_config']
        
        if 'metadata' in updates:
            template.metadata.update(updates['metadata'])
        
        # Update timestamp
        template.updated_at = datetime.utcnow()
        
        # Validate updated template
        self._validate_template(template)
        
        # Save to storage
        self._save_template_to_file(template)
        
        logger.info(f"Updated template: {template.name} ({template.id})")
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: The ID of the template to delete
            
        Returns:
            bool: True if the template was deleted
            
        Raises:
            TemplateNotFoundError: If the template is not found
            TemplateValidationError: If attempting to delete a system template
        """
        if template_id not in self.templates_cache:
            raise TemplateNotFoundError(f"Template with ID '{template_id}' not found")
        
        template = self.templates_cache[template_id]
        
        # Prevent deleting system templates
        if template.is_system_template:
            raise TemplateValidationError("Cannot delete system templates")
        
        # Remove from cache
        del self.templates_cache[template_id]
        
        # Delete file
        self._delete_template_file(template_id)
        
        logger.info(f"Deleted template: {template.name} ({template.id})")
        return True
    
    def duplicate_template(self, template_id: str, new_name: str) -> SelectionTemplate:
        """
        Duplicate an existing template with a new name.
        
        Args:
            template_id: The ID of the template to duplicate
            new_name: Name for the new template
            
        Returns:
            SelectionTemplate: The duplicated template
            
        Raises:
            TemplateNotFoundError: If the source template is not found
        """
        if template_id not in self.templates_cache:
            raise TemplateNotFoundError(f"Template with ID '{template_id}' not found")
        
        source_template = self.templates_cache[template_id]
        
        # Create new template with copied configuration
        new_template = SelectionTemplate(
            id=str(uuid.uuid4()),
            name=new_name,
            description=f"Copy of {source_template.name}",
            selection_config=source_template.selection_config,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=source_template.created_by,
            tags=source_template.tags.copy(),
            usage_count=0,
            is_system_template=False,  # Duplicates are never system templates
            metadata=source_template.metadata.copy()
        )
        
        # Save the new template
        self.create_template(new_template)
        
        logger.info(f"Duplicated template: {source_template.name} -> {new_name}")
        return new_template
    
    def get_template_usage(self, template_id: str) -> Dict[str, Any]:
        """
        Get usage information for a template.
        
        Args:
            template_id: The ID of the template
            
        Returns:
            Dict containing usage information
            
        Raises:
            TemplateNotFoundError: If the template is not found
        """
        if template_id not in self.templates_cache:
            raise TemplateNotFoundError(f"Template with ID '{template_id}' not found")
        
        template = self.templates_cache[template_id]
        
        return {
            'template_id': template.id,
            'template_name': template.name,
            'usage_count': template.usage_count,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat(),
            'last_used': template.updated_at.isoformat(),  # Approximation
            'is_system_template': template.is_system_template
        }

    def export_template(
        self,
        template_id: str,
        output_path: Path,
        format: str = 'json'
    ) -> Path:
        """
        Export a template to a file.
        
        Args:
            template_id: The ID of the template to export
            output_path: Path where the template should be exported
            format: Export format ('json' or 'yaml')
            
        Returns:
            Path: The path to the exported file
            
        Raises:
            TemplateNotFoundError: If the template is not found
            TemplateExportError: If export fails
        """
        if template_id not in self.templates_cache:
            raise TemplateNotFoundError(f"Template with ID '{template_id}' not found")
        
        if format not in ('json', 'yaml'):
            raise TemplateExportError(f"Unsupported export format: {format}")
        
        template = self.templates_cache[template_id]
        
        try:
            # Serialize template
            data = self._serialize_template(template)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file based on format
            if format == 'json':
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            else:  # yaml
                with open(output_path, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Exported template '{template.name}' to {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Failed to export template: {e}")
            raise TemplateExportError(f"Export failed: {e}")
    
    def export_templates(
        self,
        template_ids: List[str],
        output_path: Path,
        format: str = 'json'
    ) -> Path:
        """
        Export multiple templates to a single file.
        
        Args:
            template_ids: List of template IDs to export
            output_path: Path where templates should be exported
            format: Export format ('json' or 'yaml')
            
        Returns:
            Path: The path to the exported file
            
        Raises:
            TemplateNotFoundError: If any template is not found
            TemplateExportError: If export fails
        """
        if format not in ('json', 'yaml'):
            raise TemplateExportError(f"Unsupported export format: {format}")
        
        # Validate all templates exist
        for template_id in template_ids:
            if template_id not in self.templates_cache:
                raise TemplateNotFoundError(f"Template with ID '{template_id}' not found")
        
        try:
            # Serialize all templates
            templates_data = []
            for template_id in template_ids:
                template = self.templates_cache[template_id]
                templates_data.append(self._serialize_template(template))
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file based on format
            if format == 'json':
                with open(output_path, 'w') as f:
                    json.dump({'templates': templates_data}, f, indent=2)
            else:  # yaml
                with open(output_path, 'w') as f:
                    yaml.dump({'templates': templates_data}, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Exported {len(template_ids)} templates to {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Failed to export templates: {e}")
            raise TemplateExportError(f"Export failed: {e}")
    
    def import_template(
        self,
        input_path: Path,
        merge_strategy: str = 'skip',
        validate: bool = True
    ) -> ImportResult:
        """
        Import a template from a file.
        
        Args:
            input_path: Path to the template file to import
            merge_strategy: Strategy for handling existing templates:
                - 'skip': Skip templates that already exist
                - 'overwrite': Overwrite existing templates
                - 'rename': Create new template with modified name
            validate: Whether to validate templates before importing
            
        Returns:
            ImportResult: Result of the import operation
            
        Raises:
            TemplateImportError: If import fails
        """
        if merge_strategy not in ('skip', 'overwrite', 'rename'):
            raise TemplateImportError(f"Invalid merge strategy: {merge_strategy}")
        
        result = ImportResult(success=True)
        
        try:
            # Determine file format
            if input_path.suffix.lower() in ('.yaml', '.yml'):
                with open(input_path, 'r') as f:
                    data = yaml.safe_load(f)
            else:  # Default to JSON
                with open(input_path, 'r') as f:
                    data = json.load(f)
            
            # Handle single template or multiple templates
            if 'templates' in data:
                templates_data = data['templates']
            else:
                templates_data = [data]
            
            # Import each template
            for template_data in templates_data:
                try:
                    self._import_single_template(
                        template_data,
                        merge_strategy,
                        validate,
                        result
                    )
                except Exception as e:
                    result.failed_count += 1
                    result.errors.append(f"Failed to import template: {e}")
                    logger.warning(f"Failed to import template: {e}")
            
            # Update overall success status
            result.success = result.failed_count == 0
            
            logger.info(
                f"Import completed: {result.imported_count} imported, "
                f"{result.skipped_count} skipped, {result.failed_count} failed"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to import templates: {e}")
            raise TemplateImportError(f"Import failed: {e}")
    
    def _import_single_template(
        self,
        template_data: Dict[str, Any],
        merge_strategy: str,
        validate: bool,
        result: ImportResult
    ) -> None:
        """
        Import a single template.
        
        Args:
            template_data: Template data to import
            merge_strategy: Strategy for handling existing templates
            validate: Whether to validate the template
            result: ImportResult to update
        """
        try:
            # Deserialize template
            template = self._deserialize_template(template_data)
            
            # Validate if requested
            if validate:
                self._validate_template(template)
            
            # Check if template already exists
            template_exists = template.id in self.templates_cache
            
            if template_exists:
                if merge_strategy == 'skip':
                    result.skipped_count += 1
                    result.skipped_ids.append(template.id)
                    result.warnings.append(
                        f"Skipped existing template: {template.name} ({template.id})"
                    )
                    return
                
                elif merge_strategy == 'rename':
                    # Generate new ID and modify name
                    original_name = template.name
                    template.id = str(uuid.uuid4())
                    template.name = f"{original_name} (imported)"
                    template.is_system_template = False
                    result.warnings.append(
                        f"Renamed template: {original_name} -> {template.name}"
                    )
                
                elif merge_strategy == 'overwrite':
                    # Check if it's a system template
                    existing_template = self.templates_cache[template.id]
                    if existing_template.is_system_template:
                        result.skipped_count += 1
                        result.skipped_ids.append(template.id)
                        result.warnings.append(
                            f"Cannot overwrite system template: {template.name}"
                        )
                        return
                    
                    result.warnings.append(
                        f"Overwriting existing template: {template.name}"
                    )
            
            # Update timestamps
            now = datetime.utcnow()
            if not template_exists or merge_strategy == 'overwrite':
                template.updated_at = now
            if not template_exists or merge_strategy == 'rename':
                template.created_at = now
            
            # Save template
            self._save_template_to_file(template)
            self.templates_cache[template.id] = template
            
            result.imported_count += 1
            result.imported_ids.append(template.id)
            
            logger.debug(f"Imported template: {template.name} ({template.id})")
        
        except Exception as e:
            raise TemplateImportError(f"Failed to import template: {e}")
    
    def bulk_import(
        self,
        input_paths: List[Path],
        merge_strategy: str = 'skip',
        validate: bool = True
    ) -> ImportResult:
        """
        Import templates from multiple files.
        
        Args:
            input_paths: List of paths to template files
            merge_strategy: Strategy for handling existing templates
            validate: Whether to validate templates before importing
            
        Returns:
            ImportResult: Combined result of all import operations
        """
        combined_result = ImportResult(success=True)
        
        for input_path in input_paths:
            try:
                result = self.import_template(input_path, merge_strategy, validate)
                
                # Combine results
                combined_result.imported_count += result.imported_count
                combined_result.skipped_count += result.skipped_count
                combined_result.failed_count += result.failed_count
                combined_result.imported_ids.extend(result.imported_ids)
                combined_result.skipped_ids.extend(result.skipped_ids)
                combined_result.errors.extend(result.errors)
                combined_result.warnings.extend(result.warnings)
                
            except Exception as e:
                combined_result.failed_count += 1
                combined_result.errors.append(f"Failed to import from {input_path}: {e}")
                logger.warning(f"Failed to import from {input_path}: {e}")
        
        # Update overall success status
        combined_result.success = combined_result.failed_count == 0
        
        logger.info(
            f"Bulk import completed: {combined_result.imported_count} imported, "
            f"{combined_result.skipped_count} skipped, {combined_result.failed_count} failed"
        )
        
        return combined_result
    
    def validate_import_file(self, input_path: Path) -> Dict[str, Any]:
        """
        Validate an import file without actually importing.
        
        Args:
            input_path: Path to the template file to validate
            
        Returns:
            Dict containing validation results:
                - valid: Whether the file is valid
                - template_count: Number of templates in the file
                - errors: List of validation errors
                - warnings: List of validation warnings
        """
        validation_result = {
            'valid': True,
            'template_count': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Determine file format and load
            if input_path.suffix.lower() in ('.yaml', '.yml'):
                with open(input_path, 'r') as f:
                    data = yaml.safe_load(f)
            else:
                with open(input_path, 'r') as f:
                    data = json.load(f)
            
            # Handle single template or multiple templates
            if 'templates' in data:
                templates_data = data['templates']
            else:
                templates_data = [data]
            
            validation_result['template_count'] = len(templates_data)
            
            # Validate each template
            for i, template_data in enumerate(templates_data):
                try:
                    template = self._deserialize_template(template_data)
                    self._validate_template(template)
                    
                    # Check for conflicts with existing templates
                    if template.id in self.templates_cache:
                        validation_result['warnings'].append(
                            f"Template {i+1} ({template.name}) already exists"
                        )
                
                except Exception as e:
                    validation_result['valid'] = False
                    validation_result['errors'].append(
                        f"Template {i+1} validation failed: {e}"
                    )
        
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Failed to read file: {e}")
        
        return validation_result
    
    def export_all_templates(
        self,
        output_path: Path,
        format: str = 'json',
        include_system: bool = False
    ) -> Path:
        """
        Export all templates to a single file.
        
        Args:
            output_path: Path where templates should be exported
            format: Export format ('json' or 'yaml')
            include_system: Whether to include system templates
            
        Returns:
            Path: The path to the exported file
            
        Raises:
            TemplateExportError: If export fails
        """
        # Get all template IDs
        template_ids = [
            tid for tid, template in self.templates_cache.items()
            if include_system or not template.is_system_template
        ]
        
        if not template_ids:
            raise TemplateExportError("No templates to export")
        
        return self.export_templates(template_ids, output_path, format)
