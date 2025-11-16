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
Data Selection Integration Service

This module provides integration between the backup operations system and the
data selection system. It handles retrieval of data selection configurations,
translation of selection rules to backup tool-specific formats, validation of
compatibility, and warning generation for unsupported features.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

from ..interfaces.data_models import BackupJob, BackupJobConfig, ToolConfiguration
from ..selection_models import (
    SelectionConfig,
    PatternRule,
    PatternSyntax,
    PathComponent
)
from ..selection_manager import SelectionManager
from ..selection_template_manager import TemplateNotFoundError
from .tool_manager import ToolManager, Feature, ToolCapabilities
from .plugin_wrapper import PluginWrapper

logger = logging.getLogger(__name__)


@dataclass
class SelectionTranslationResult:
    """
    Result of translating selection rules to tool-specific format.
    
    Attributes:
        include_patterns: Translated include patterns
        exclude_patterns: Translated exclude patterns
        include_paths: Explicit include paths
        exclude_paths: Explicit exclude paths
        unsupported_patterns: Patterns that couldn't be translated
        warnings: List of warning messages
        translation_notes: Additional notes about the translation
    """
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    include_paths: List[Path] = field(default_factory=list)
    exclude_paths: List[Path] = field(default_factory=list)
    unsupported_patterns: List[PatternRule] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    translation_notes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SelectionCompatibilityResult:
    """
    Result of validating selection compatibility with a backup tool.
    
    Attributes:
        is_compatible: Whether selection is fully compatible
        supported_features: Features that are supported
        unsupported_features: Features that are not supported
        warnings: List of warning messages
        recommendations: List of recommendations
        alternative_approaches: Suggested alternative approaches for unsupported features
    """
    is_compatible: bool
    supported_features: List[str] = field(default_factory=list)
    unsupported_features: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    alternative_approaches: Dict[str, str] = field(default_factory=dict)


class DataSelectionIntegrationService:
    """
    Service for integrating data selection with backup operations.
    
    This service provides:
    - Retrieval of data selection configurations
    - Translation of selection rules to tool-specific formats
    - Validation of selection compatibility with backup tools
    - Warning generation for unsupported selection features
    - Integration with plugin wrappers for capability gap filling
    """
    
    def __init__(
        self,
        selection_manager: Optional[SelectionManager] = None,
        tool_manager: Optional[ToolManager] = None
    ):
        """
        Initialize data selection integration service.
        
        Args:
            selection_manager: SelectionManager instance (creates new if None)
            tool_manager: ToolManager instance (creates new if None)
        """
        self.selection_manager = selection_manager or SelectionManager()
        self.tool_manager = tool_manager or ToolManager()
        
        # Cache for selection configurations
        self._selection_cache: Dict[str, SelectionConfig] = {}
        
        # Statistics
        self._stats = {
            'translations_performed': 0,
            'validations_performed': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info("DataSelectionIntegrationService initialized")
    
    def retrieve_selection_config(
        self,
        selection_id: str
    ) -> Optional[SelectionConfig]:
        """
        Retrieve data selection configuration by ID.
        
        Args:
            selection_id: Data selection identifier
            
        Returns:
            SelectionConfig if found, None otherwise
        """
        logger.debug(f"Retrieving selection configuration: {selection_id}")
        
        # Check cache first
        if selection_id in self._selection_cache:
            self._stats['cache_hits'] += 1
            logger.debug(f"Selection config cache hit: {selection_id}")
            return self._selection_cache[selection_id]
        
        self._stats['cache_misses'] += 1
        
        # Try to load from template manager using ID, then fall back to name for compatibility
        try:
            template = self.selection_manager.template_manager.get_template(selection_id)
        except TemplateNotFoundError:
            try:
                template = self.selection_manager.template_manager.get_template(
                    selection_id,
                    by_name=True
                )
                if template:
                    logger.info(f"Resolved selection identifier '{selection_id}' by name.")
            except TemplateNotFoundError:
                template = None
        except Exception as e:
            logger.warning(f"Could not load selection config {selection_id}: {e}")
            template = None

        if template:
            config = template.selection_config
            self._selection_cache[template.id] = config
            if selection_id != template.id:
                self._selection_cache[selection_id] = config
            logger.info(f"Loaded selection config from template: {template.id}")
            return config
        
        return None
    
    def apply_selection_to_job(
        self,
        job: BackupJob,
        selection_config: SelectionConfig
    ) -> BackupJob:
        """
        Apply data selection configuration to a backup job.
        
        This method translates the selection configuration to the appropriate
        format for the backup tool and updates the job with the translated rules.
        
        Args:
            job: Backup job to apply selection to
            selection_config: Selection configuration to apply
            
        Returns:
            Updated BackupJob with selection rules applied
        """
        logger.info(f"Applying selection config to job: {job.config.job_id}")
        
        # Translate selection rules for the tool
        translation_result = self.translate_selection_for_tool(
            selection_config,
            job.config.tool_type
        )
        
        # Update job with translated rules
        job.source_paths.extend(translation_result.include_paths)
        job.exclude_patterns.extend(translation_result.exclude_patterns)
        job.include_patterns.extend(translation_result.include_patterns)
        
        # Add warnings to job metadata
        if translation_result.warnings:
            if 'selection_warnings' not in job.config.metadata:
                job.config.metadata['selection_warnings'] = []
            job.config.metadata['selection_warnings'].extend(translation_result.warnings)
        
        # Add unsupported patterns to metadata
        if translation_result.unsupported_patterns:
            job.config.metadata['unsupported_selection_patterns'] = [
                {
                    'pattern': p.pattern,
                    'syntax': p.syntax.value,
                    'reason': 'Tool does not support this pattern type'
                }
                for p in translation_result.unsupported_patterns
            ]
        
        logger.info(
            f"Selection applied: {len(translation_result.include_patterns)} include, "
            f"{len(translation_result.exclude_patterns)} exclude patterns, "
            f"{len(translation_result.warnings)} warnings"
        )
        
        return job
    
    def translate_selection_for_tool(
        self,
        selection_config: SelectionConfig,
        tool_type: str,
        plugin_wrapper: Optional[PluginWrapper] = None
    ) -> SelectionTranslationResult:
        """
        Translate data selection rules to tool-specific format.
        
        This method handles the translation of TimeLocker selection rules to
        the format required by the specific backup tool, using plugin wrappers
        when available to fill capability gaps.
        
        Args:
            selection_config: Selection configuration to translate
            tool_type: Type of backup tool
            plugin_wrapper: Optional plugin wrapper for enhanced translation
            
        Returns:
            SelectionTranslationResult with translated rules
        """
        logger.debug(f"Translating selection rules for tool: {tool_type}")
        self._stats['translations_performed'] += 1
        
        result = SelectionTranslationResult()
        
        # Get tool capabilities
        try:
            capabilities = self.tool_manager.get_tool_capabilities(tool_type)
        except ValueError as e:
            logger.error(f"Unknown tool type: {tool_type}")
            result.warnings.append(f"Unknown tool type: {tool_type}")
            return result
        
        # Add explicit paths
        result.include_paths = selection_config.include_paths.copy()
        result.exclude_paths = selection_config.exclude_paths.copy()
        
        # Translate include patterns
        for pattern_rule in selection_config.include_patterns:
            translated = self._translate_pattern_rule(
                pattern_rule,
                capabilities,
                plugin_wrapper,
                is_include=True
            )
            
            if translated['success']:
                result.include_patterns.extend(translated['patterns'])
                if translated.get('notes'):
                    result.translation_notes[pattern_rule.pattern] = translated['notes']
            else:
                result.unsupported_patterns.append(pattern_rule)
                result.warnings.append(
                    f"Could not translate include pattern '{pattern_rule.pattern}': "
                    f"{translated.get('reason', 'unknown')}"
                )
        
        # Translate exclude patterns
        for pattern_rule in selection_config.exclude_patterns:
            translated = self._translate_pattern_rule(
                pattern_rule,
                capabilities,
                plugin_wrapper,
                is_include=False
            )
            
            if translated['success']:
                result.exclude_patterns.extend(translated['patterns'])
                if translated.get('notes'):
                    result.translation_notes[pattern_rule.pattern] = translated['notes']
            else:
                result.unsupported_patterns.append(pattern_rule)
                result.warnings.append(
                    f"Could not translate exclude pattern '{pattern_rule.pattern}': "
                    f"{translated.get('reason', 'unknown')}"
                )
        
        # Add summary to translation notes
        result.translation_notes['summary'] = {
            'total_patterns': len(selection_config.include_patterns) + len(selection_config.exclude_patterns),
            'translated': len(result.include_patterns) + len(result.exclude_patterns),
            'unsupported': len(result.unsupported_patterns),
            'tool_type': tool_type
        }
        
        logger.info(
            f"Translation complete: {len(result.include_patterns)} include, "
            f"{len(result.exclude_patterns)} exclude, "
            f"{len(result.unsupported_patterns)} unsupported"
        )
        
        return result
    
    def _translate_pattern_rule(
        self,
        pattern_rule: PatternRule,
        capabilities: ToolCapabilities,
        plugin_wrapper: Optional[PluginWrapper],
        is_include: bool
    ) -> Dict[str, Any]:
        """
        Translate a single pattern rule to tool-specific format.
        
        Args:
            pattern_rule: Pattern rule to translate
            capabilities: Tool capabilities
            plugin_wrapper: Optional plugin wrapper
            is_include: Whether this is an include pattern
            
        Returns:
            Dictionary with translation result
        """
        # Check if tool supports the pattern syntax
        if pattern_rule.syntax == PatternSyntax.GLOB:
            if not capabilities.has_feature(Feature.INCLUDE_PATTERNS if is_include else Feature.EXCLUDE_PATTERNS):
                return {
                    'success': False,
                    'reason': 'Tool does not support glob patterns'
                }
            
            # Glob patterns are widely supported, return as-is
            return {
                'success': True,
                'patterns': [pattern_rule.pattern],
                'notes': 'Native glob pattern support'
            }
        
        elif pattern_rule.syntax == PatternSyntax.REGEX:
            # Check if tool natively supports regex
            if capabilities.has_feature(Feature.REGEX_PATTERNS):
                return {
                    'success': True,
                    'patterns': [pattern_rule.pattern],
                    'notes': 'Native regex pattern support'
                }
            
            # Try to use plugin wrapper for translation
            if plugin_wrapper and plugin_wrapper.has_capability(Feature.REGEX_PATTERNS):
                # Plugin wrapper can handle regex translation
                try:
                    translated = plugin_wrapper.translate_selection_rules(
                        [pattern_rule.pattern] if is_include else [],
                        [pattern_rule.pattern] if not is_include else []
                    )
                    
                    patterns = translated['include'] if is_include else translated['exclude']
                    if patterns:
                        return {
                            'success': True,
                            'patterns': patterns,
                            'notes': 'Translated from regex via plugin wrapper'
                        }
                except Exception as e:
                    logger.warning(f"Plugin wrapper translation failed: {e}")
            
            # Try basic regex to glob conversion
            glob_pattern = self._regex_to_glob(pattern_rule.pattern)
            if glob_pattern:
                return {
                    'success': True,
                    'patterns': [glob_pattern],
                    'notes': 'Converted from regex to glob (may be approximate)'
                }
            
            return {
                'success': False,
                'reason': 'Tool does not support regex patterns and conversion failed'
            }
        
        elif pattern_rule.syntax == PatternSyntax.LITERAL:
            # Literal patterns can usually be represented as glob patterns
            return {
                'success': True,
                'patterns': [pattern_rule.pattern],
                'notes': 'Literal pattern (exact match)'
            }
        
        return {
            'success': False,
            'reason': f'Unknown pattern syntax: {pattern_rule.syntax}'
        }
    
    def _regex_to_glob(self, regex_pattern: str) -> Optional[str]:
        """
        Attempt to convert a regex pattern to a glob pattern.
        
        This is a best-effort conversion for common regex patterns.
        
        Args:
            regex_pattern: Regex pattern to convert
            
        Returns:
            Glob pattern or None if conversion not possible
        """
        import re
        
        # Pattern: .*\.ext$ -> *.ext
        match = re.match(r'\.\*\\\.(\w+)\$', regex_pattern)
        if match:
            return f"*.{match.group(1)}"
        
        # Pattern: ^/path/.* -> /path/*
        match = re.match(r'\^(/[^*]+)/\.\*', regex_pattern)
        if match:
            return f"{match.group(1)}/*"
        
        # Pattern: .*/filename -> **/filename
        match = re.match(r'\.\*/(.+)', regex_pattern)
        if match:
            return f"**/{match.group(1)}"
        
        # Pattern: filename.* -> filename*
        match = re.match(r'([^.*]+)\.\*', regex_pattern)
        if match:
            return f"{match.group(1)}*"
        
        # If no conversion possible, return None
        return None
    
    def validate_selection_compatibility(
        self,
        selection_config: SelectionConfig,
        tool_type: str,
        plugin_wrapper: Optional[PluginWrapper] = None
    ) -> SelectionCompatibilityResult:
        """
        Validate that a selection configuration is compatible with a backup tool.
        
        Args:
            selection_config: Selection configuration to validate
            tool_type: Type of backup tool
            plugin_wrapper: Optional plugin wrapper
            
        Returns:
            SelectionCompatibilityResult with validation details
        """
        logger.debug(f"Validating selection compatibility with {tool_type}")
        self._stats['validations_performed'] += 1
        
        result = SelectionCompatibilityResult(is_compatible=True)
        
        # Get tool capabilities
        try:
            capabilities = self.tool_manager.get_tool_capabilities(tool_type)
        except ValueError as e:
            result.is_compatible = False
            result.warnings.append(f"Unknown tool type: {tool_type}")
            return result
        
        # Check pattern syntax support
        pattern_syntaxes = set()
        for pattern in selection_config.include_patterns + selection_config.exclude_patterns:
            pattern_syntaxes.add(pattern.syntax)
        
        for syntax in pattern_syntaxes:
            if syntax == PatternSyntax.GLOB:
                if capabilities.has_feature(Feature.INCLUDE_PATTERNS):
                    result.supported_features.append(f"GLOB patterns ({syntax.value})")
                else:
                    result.unsupported_features.append(f"GLOB patterns ({syntax.value})")
                    result.is_compatible = False
                    result.warnings.append(
                        f"Tool {tool_type} does not support glob patterns"
                    )
            
            elif syntax == PatternSyntax.REGEX:
                if capabilities.has_feature(Feature.REGEX_PATTERNS):
                    result.supported_features.append(f"REGEX patterns ({syntax.value})")
                elif plugin_wrapper and plugin_wrapper.has_capability(Feature.REGEX_PATTERNS):
                    result.supported_features.append(
                        f"REGEX patterns ({syntax.value}) via plugin wrapper"
                    )
                    result.warnings.append(
                        f"REGEX patterns will be translated by plugin wrapper "
                        f"(may not be exact match)"
                    )
                else:
                    result.unsupported_features.append(f"REGEX patterns ({syntax.value})")
                    result.warnings.append(
                        f"Tool {tool_type} does not support regex patterns"
                    )
                    result.alternative_approaches['regex_patterns'] = (
                        "Convert regex patterns to glob patterns manually, or use a "
                        "tool that supports regex patterns natively"
                    )
        
        # Check path component support
        path_components = set()
        for pattern in selection_config.include_patterns + selection_config.exclude_patterns:
            path_components.add(pattern.applies_to)
        
        if PathComponent.FILENAME in path_components or PathComponent.DIRECTORY in path_components:
            result.warnings.append(
                f"Tool {tool_type} may not support path component-specific matching. "
                "Patterns will be applied to full paths."
            )
            result.recommendations.append(
                "Consider using full path patterns instead of filename/directory-specific patterns"
            )
        
        # Check case sensitivity
        case_sensitive_patterns = [
            p for p in selection_config.include_patterns + selection_config.exclude_patterns
            if p.case_sensitive
        ]
        if case_sensitive_patterns:
            result.warnings.append(
                f"Found {len(case_sensitive_patterns)} case-sensitive patterns. "
                f"Tool {tool_type} may not preserve case sensitivity."
            )
        
        # Check precedence configuration
        if selection_config.precedence_config:
            result.warnings.append(
                "Precedence configuration may not be fully honored by backup tool. "
                "TimeLocker will apply precedence rules before passing to tool."
            )
        
        # Add recommendations based on findings
        if result.unsupported_features:
            result.recommendations.append(
                f"Consider using a different backup tool that supports all required features, "
                f"or simplify selection rules to use only supported features"
            )
        
        if result.warnings:
            result.recommendations.append(
                "Test the backup with a dry run to verify selection rules work as expected"
            )
        
        logger.info(
            f"Compatibility validation complete: compatible={result.is_compatible}, "
            f"warnings={len(result.warnings)}, unsupported={len(result.unsupported_features)}"
        )
        
        return result
    
    def generate_selection_warnings(
        self,
        job: BackupJob,
        selection_config: SelectionConfig
    ) -> List[str]:
        """
        Generate warnings for potential issues with selection configuration.
        
        Args:
            job: Backup job
            selection_config: Selection configuration
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check for empty selection
        if not selection_config.include_paths and not selection_config.include_patterns:
            warnings.append(
                "No include paths or patterns specified. "
                "Backup may not include any files."
            )
        
        # Check for conflicting patterns
        include_set = set(p.pattern for p in selection_config.include_patterns)
        exclude_set = set(p.pattern for p in selection_config.exclude_patterns)
        conflicts = include_set & exclude_set
        if conflicts:
            warnings.append(
                f"Found {len(conflicts)} patterns in both include and exclude lists. "
                "Precedence rules will determine final behavior."
            )
        
        # Check for very complex patterns
        complex_patterns = [
            p for p in selection_config.include_patterns + selection_config.exclude_patterns
            if len(p.pattern) > 100 or p.pattern.count('*') > 5
        ]
        if complex_patterns:
            warnings.append(
                f"Found {len(complex_patterns)} complex patterns that may impact performance"
            )
        
        # Check for patterns that might match everything
        broad_patterns = [
            p for p in selection_config.exclude_patterns
            if p.pattern in ['*', '**', '**/*', '.*']
        ]
        if broad_patterns:
            warnings.append(
                "Found exclude patterns that may match all files. "
                "Verify this is intentional."
            )
        
        return warnings
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dictionary with statistics
        """
        cache_total = self._stats['cache_hits'] + self._stats['cache_misses']
        cache_hit_ratio = (
            self._stats['cache_hits'] / cache_total
            if cache_total > 0 else 0.0
        )
        
        return {
            **self._stats,
            'cache_size': len(self._selection_cache),
            'cache_hit_ratio': cache_hit_ratio
        }
    
    def clear_cache(self) -> None:
        """Clear the selection configuration cache."""
        self._selection_cache.clear()
        logger.info("Selection configuration cache cleared")
