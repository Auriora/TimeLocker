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
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pattern_engine import PatternEngine
from .precedence_resolver import PrecedenceResolver
from .selection_models import (
    ConflictResolution,
    PatternRule,
    PatternSyntax,
    PerformanceEstimate,
    PrecedenceConfig,
    SelectionConfig,
    ValidationError,
    ValidationResult,
    ValidationWarning
)

logger = logging.getLogger(__name__)


class SelectionValidationError(Exception):
    """Exception raised for selection validation failures"""
    pass


class ConflictType(Enum):
    """Types of selection conflicts"""
    INCLUDE_EXCLUDE_OVERLAP = "include_exclude"
    PATTERN_CONTRADICTION = "pattern_conflict"
    PATH_INACCESSIBLE = "access_denied"
    CIRCULAR_DEPENDENCY = "circular"
    PERFORMANCE_CONCERN = "performance"


class ConflictSeverity(Enum):
    """Severity levels for conflicts"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ConflictReport:
    """
    Report of a selection conflict.
    
    Attributes:
        conflict_type: Type of conflict
        affected_paths: Paths affected by the conflict
        conflicting_rules: Rules that are in conflict
        suggested_resolution: Suggested way to resolve the conflict
        severity: Severity of the conflict
        details: Additional details about the conflict
    """
    conflict_type: ConflictType
    affected_paths: List[Path]
    conflicting_rules: List[PatternRule]
    suggested_resolution: str
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessibilityResult:
    """
    Result of path accessibility check.
    
    Attributes:
        path: Path that was checked
        accessible: Whether the path is accessible
        exists: Whether the path exists
        readable: Whether the path is readable
        error_message: Error message if not accessible
        permissions: File permissions if accessible
    """
    path: Path
    accessible: bool
    exists: bool
    readable: bool
    error_message: Optional[str] = None
    permissions: Optional[str] = None


class SelectionValidationService:
    """
    Comprehensive validation service for selection configurations.
    
    Provides validation of selection rules, conflict detection, syntax checking,
    and logical consistency verification.
    """
    
    def __init__(
        self,
        pattern_engine: Optional[PatternEngine] = None,
        precedence_resolver: Optional[PrecedenceResolver] = None
    ):
        """
        Initialize the validation service.
        
        Args:
            pattern_engine: PatternEngine instance (creates new if None)
            precedence_resolver: PrecedenceResolver instance (creates new if None)
        """
        self.pattern_engine = pattern_engine or PatternEngine()
        self.precedence_resolver = precedence_resolver or PrecedenceResolver()
        
        # Statistics
        self._stats = {
            'total_validations': 0,
            'validation_failures': 0,
            'conflicts_detected': 0,
            'warnings_generated': 0
        }
    
    async def validate_selection_config(self, config: SelectionConfig) -> ValidationResult:
        """
        Validate a complete selection configuration.
        
        Args:
            config: Selection configuration to validate
            
        Returns:
            ValidationResult with validation details
        """
        self._stats['total_validations'] += 1
        
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        suggestions: List[str] = []
        
        logger.debug("Validating selection configuration")
        
        # 1. Validate that at least one include path or pattern exists
        if not config.include_paths and not config.include_patterns:
            errors.append(ValidationError(
                error_type="no_includes",
                message="Selection must include at least one path or pattern",
                context={"config": "include_paths and include_patterns are both empty"},
                suggested_fix="Add at least one include path or include pattern"
            ))
        
        # 2. Validate path syntax
        path_validation = self._validate_paths(config)
        errors.extend(path_validation['errors'])
        warnings.extend(path_validation['warnings'])
        
        # 3. Validate pattern syntax
        pattern_validation = await self.validate_pattern_syntax(
            config.include_patterns + config.exclude_patterns
        )
        errors.extend(pattern_validation.errors)
        warnings.extend(pattern_validation.warnings)
        
        # 4. Check for logical inconsistencies
        consistency_validation = self._check_logical_consistency(config)
        errors.extend(consistency_validation['errors'])
        warnings.extend(consistency_validation['warnings'])
        suggestions.extend(consistency_validation['suggestions'])
        
        # 5. Validate precedence configuration
        precedence_validation = self.precedence_resolver.validate_precedence_configuration(
            config.precedence_config
        )
        errors.extend(precedence_validation.errors)
        warnings.extend(precedence_validation.warnings)
        suggestions.extend(precedence_validation.suggestions)
        
        # 6. Estimate performance impact
        performance_estimate = await self.estimate_performance_impact(config)
        
        # Add performance warnings if needed
        if performance_estimate.estimated_files_per_second < 1000:
            warnings.append(ValidationWarning(
                warning_type="low_performance",
                message=f"Estimated performance is low ({performance_estimate.estimated_files_per_second:.0f} files/sec)",
                context={"estimate": performance_estimate},
                severity="medium"
            ))
            suggestions.extend(performance_estimate.optimization_opportunities)
        
        # Update statistics
        if errors:
            self._stats['validation_failures'] += 1
        if warnings:
            self._stats['warnings_generated'] += len(warnings)
        
        is_valid = len(errors) == 0
        
        logger.info(
            f"Validation complete: {'PASSED' if is_valid else 'FAILED'} "
            f"({len(errors)} errors, {len(warnings)} warnings)"
        )
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            estimated_performance=performance_estimate
        )
    
    def _validate_paths(self, config: SelectionConfig) -> Dict[str, List]:
        """
        Validate path syntax and format.
        
        Args:
            config: Selection configuration
            
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        # Check include paths
        for path in config.include_paths:
            if not isinstance(path, Path):
                errors.append(ValidationError(
                    error_type="invalid_path_type",
                    message=f"Include path must be a Path object: {path}",
                    context={"path": str(path), "type": type(path).__name__},
                    suggested_fix="Convert string paths to Path objects"
                ))
                continue
            
            # Check for absolute vs relative paths
            if not path.is_absolute():
                warnings.append(ValidationWarning(
                    warning_type="relative_path",
                    message=f"Include path is relative: {path}",
                    context={"path": str(path)},
                    severity="low"
                ))
        
        # Check exclude paths
        for path in config.exclude_paths:
            if not isinstance(path, Path):
                errors.append(ValidationError(
                    error_type="invalid_path_type",
                    message=f"Exclude path must be a Path object: {path}",
                    context={"path": str(path), "type": type(path).__name__},
                    suggested_fix="Convert string paths to Path objects"
                ))
                continue
            
            # Check if exclude path is within any include path
            is_within_include = False
            for include_path in config.include_paths:
                try:
                    path.relative_to(include_path)
                    is_within_include = True
                    break
                except ValueError:
                    continue
            
            if not is_within_include and config.include_paths:
                warnings.append(ValidationWarning(
                    warning_type="exclude_outside_include",
                    message=f"Exclude path {path} is not within any include path",
                    context={"path": str(path)},
                    severity="low"
                ))
        
        return {'errors': errors, 'warnings': warnings}
    
    async def validate_pattern_syntax(
        self,
        patterns: List[PatternRule]
    ) -> ValidationResult:
        """
        Validate syntax of pattern rules.
        
        Args:
            patterns: List of pattern rules to validate
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        suggestions = []
        
        for i, pattern in enumerate(patterns):
            # Validate pattern using pattern engine
            validation = self.pattern_engine.validate_pattern_syntax(
                pattern.pattern,
                pattern.syntax
            )
            
            # Add context to errors
            for error in validation.errors:
                error.context['pattern_index'] = i
                error.context['pattern_rule'] = pattern
                errors.append(error)
            
            # Add context to warnings
            for warning in validation.warnings:
                warning.context['pattern_index'] = i
                warning.context['pattern_rule'] = pattern
                warnings.append(warning)
            
            suggestions.extend(validation.suggestions)
            
            # Additional validation checks
            if not pattern.pattern:
                errors.append(ValidationError(
                    error_type="empty_pattern",
                    message=f"Pattern at index {i} is empty",
                    context={"pattern_index": i},
                    suggested_fix="Remove empty pattern or provide a valid pattern"
                ))
            
            if pattern.priority < 0:
                errors.append(ValidationError(
                    error_type="invalid_priority",
                    message=f"Pattern priority must be non-negative: {pattern.priority}",
                    context={"pattern_index": i, "priority": pattern.priority},
                    suggested_fix="Set priority to a non-negative value"
                ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _check_logical_consistency(self, config: SelectionConfig) -> Dict[str, List]:
        """
        Check for logical inconsistencies in the configuration.
        
        Args:
            config: Selection configuration
            
        Returns:
            Dictionary with 'errors', 'warnings', and 'suggestions' lists
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Check for duplicate patterns
        seen_patterns = set()
        for pattern_list, list_type in [
            (config.include_patterns, "include"),
            (config.exclude_patterns, "exclude")
        ]:
            for pattern in pattern_list:
                pattern_key = (pattern.pattern, pattern.syntax, pattern.case_sensitive)
                if pattern_key in seen_patterns:
                    warnings.append(ValidationWarning(
                        warning_type="duplicate_pattern",
                        message=f"Duplicate {list_type} pattern: {pattern.pattern}",
                        context={"pattern": pattern.pattern, "type": list_type},
                        severity="low"
                    ))
                seen_patterns.add(pattern_key)
        
        # Check for contradictory patterns
        for include_pattern in config.include_patterns:
            for exclude_pattern in config.exclude_patterns:
                if (include_pattern.pattern == exclude_pattern.pattern and
                    include_pattern.syntax == exclude_pattern.syntax and
                    include_pattern.case_sensitive == exclude_pattern.case_sensitive):
                    
                    warnings.append(ValidationWarning(
                        warning_type="contradictory_patterns",
                        message=f"Pattern appears in both include and exclude: {include_pattern.pattern}",
                        context={
                            "pattern": include_pattern.pattern,
                            "syntax": include_pattern.syntax.value
                        },
                        severity="high"
                    ))
                    suggestions.append(
                        f"Remove duplicate pattern '{include_pattern.pattern}' from either "
                        "include or exclude list, or adjust precedence configuration"
                    )
        
        # Check for overly broad exclusions
        for exclude_pattern in config.exclude_patterns:
            if exclude_pattern.pattern in ('*', '**', '.*'):
                warnings.append(ValidationWarning(
                    warning_type="broad_exclusion",
                    message=f"Very broad exclusion pattern: {exclude_pattern.pattern}",
                    context={"pattern": exclude_pattern.pattern},
                    severity="high"
                ))
                suggestions.append(
                    f"Pattern '{exclude_pattern.pattern}' will exclude almost everything. "
                    "Consider using more specific patterns."
                )
        
        # Check for conflicting path specifications
        for include_path in config.include_paths:
            for exclude_path in config.exclude_paths:
                if include_path == exclude_path:
                    errors.append(ValidationError(
                        error_type="path_conflict",
                        message=f"Path appears in both include and exclude: {include_path}",
                        context={"path": str(include_path)},
                        suggested_fix="Remove path from either include or exclude list"
                    ))
        
        # Check precedence configuration consistency
        if config.precedence_config.conflict_resolution == ConflictResolution.FAIL_ON_CONFLICT:
            if config.include_patterns and config.exclude_patterns:
                warnings.append(ValidationWarning(
                    warning_type="strict_conflict_mode",
                    message="Conflict resolution is set to FAIL_ON_CONFLICT with both include and exclude patterns",
                    context={"mode": "FAIL_ON_CONFLICT"},
                    severity="medium"
                ))
                suggestions.append(
                    "Consider using WARN_ON_CONFLICT or SILENT_RESOLUTION to handle "
                    "potential conflicts more gracefully"
                )
        
        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    async def detect_selection_conflicts(
        self,
        config: SelectionConfig
    ) -> List[ConflictReport]:
        """
        Detect conflicts in selection configuration.
        
        Args:
            config: Selection configuration to check
            
        Returns:
            List of ConflictReport objects
        """
        self._stats['conflicts_detected'] += 1
        
        conflicts = []
        
        # Detect include/exclude overlaps
        overlap_conflicts = self._detect_include_exclude_overlaps(config)
        conflicts.extend(overlap_conflicts)
        
        # Detect pattern contradictions
        pattern_conflicts = self._detect_pattern_contradictions(config)
        conflicts.extend(pattern_conflicts)
        
        # Detect performance concerns
        performance_conflicts = await self._detect_performance_concerns(config)
        conflicts.extend(performance_conflicts)
        
        logger.info(f"Detected {len(conflicts)} conflicts in selection configuration")
        
        return conflicts
    
    def _detect_include_exclude_overlaps(
        self,
        config: SelectionConfig
    ) -> List[ConflictReport]:
        """
        Detect overlaps between include and exclude rules.
        
        Args:
            config: Selection configuration
            
        Returns:
            List of ConflictReport objects
        """
        conflicts = []
        
        # Check for path overlaps
        for include_path in config.include_paths:
            for exclude_path in config.exclude_paths:
                # Check if exclude is within include
                try:
                    exclude_path.relative_to(include_path)
                    
                    # This is actually expected behavior, not necessarily a conflict
                    # Only report if it might be unintentional
                    if exclude_path == include_path:
                        conflicts.append(ConflictReport(
                            conflict_type=ConflictType.INCLUDE_EXCLUDE_OVERLAP,
                            affected_paths=[include_path, exclude_path],
                            conflicting_rules=[],
                            suggested_resolution=(
                                f"Remove {exclude_path} from either include or exclude list"
                            ),
                            severity=ConflictSeverity.HIGH,
                            details={
                                "include_path": str(include_path),
                                "exclude_path": str(exclude_path),
                                "reason": "Exact path match in both include and exclude"
                            }
                        ))
                except ValueError:
                    pass
        
        # Check for pattern overlaps
        for include_pattern in config.include_patterns:
            for exclude_pattern in config.exclude_patterns:
                if (include_pattern.pattern == exclude_pattern.pattern and
                    include_pattern.syntax == exclude_pattern.syntax):
                    
                    conflicts.append(ConflictReport(
                        conflict_type=ConflictType.PATTERN_CONTRADICTION,
                        affected_paths=[],
                        conflicting_rules=[include_pattern, exclude_pattern],
                        suggested_resolution=(
                            f"Remove pattern '{include_pattern.pattern}' from either "
                            "include or exclude list, or adjust precedence rules"
                        ),
                        severity=ConflictSeverity.MEDIUM,
                        details={
                            "pattern": include_pattern.pattern,
                            "syntax": include_pattern.syntax.value,
                            "reason": "Same pattern in both include and exclude"
                        }
                    ))
        
        return conflicts
    
    def _detect_pattern_contradictions(
        self,
        config: SelectionConfig
    ) -> List[ConflictReport]:
        """
        Detect contradictory patterns within the same list.
        
        Args:
            config: Selection configuration
            
        Returns:
            List of ConflictReport objects
        """
        conflicts = []
        
        # Check for contradictions within include patterns
        for i, pattern1 in enumerate(config.include_patterns):
            for pattern2 in config.include_patterns[i+1:]:
                if self._patterns_contradict(pattern1, pattern2):
                    conflicts.append(ConflictReport(
                        conflict_type=ConflictType.PATTERN_CONTRADICTION,
                        affected_paths=[],
                        conflicting_rules=[pattern1, pattern2],
                        suggested_resolution=(
                            "Review and consolidate contradictory include patterns"
                        ),
                        severity=ConflictSeverity.LOW,
                        details={
                            "pattern1": pattern1.pattern,
                            "pattern2": pattern2.pattern,
                            "reason": "Patterns may contradict each other"
                        }
                    ))
        
        # Check for contradictions within exclude patterns
        for i, pattern1 in enumerate(config.exclude_patterns):
            for pattern2 in config.exclude_patterns[i+1:]:
                if self._patterns_contradict(pattern1, pattern2):
                    conflicts.append(ConflictReport(
                        conflict_type=ConflictType.PATTERN_CONTRADICTION,
                        affected_paths=[],
                        conflicting_rules=[pattern1, pattern2],
                        suggested_resolution=(
                            "Review and consolidate contradictory exclude patterns"
                        ),
                        severity=ConflictSeverity.LOW,
                        details={
                            "pattern1": pattern1.pattern,
                            "pattern2": pattern2.pattern,
                            "reason": "Patterns may contradict each other"
                        }
                    ))
        
        return conflicts
    
    def _patterns_contradict(self, pattern1: PatternRule, pattern2: PatternRule) -> bool:
        """
        Check if two patterns contradict each other.
        
        Args:
            pattern1: First pattern
            pattern2: Second pattern
            
        Returns:
            True if patterns contradict
        """
        # Simple heuristic: patterns contradict if they're very similar but different
        if pattern1.syntax != pattern2.syntax:
            return False
        
        if pattern1.syntax == PatternSyntax.LITERAL:
            # Literals don't contradict unless they're the same (handled elsewhere)
            return False
        
        # For GLOB and REGEX, check for very similar patterns
        # This is a simple check - could be more sophisticated
        if pattern1.pattern == pattern2.pattern:
            return False
        
        # Check if patterns are subsets of each other
        if pattern1.syntax == PatternSyntax.GLOB:
            # Simple check: if one pattern is a prefix of another with wildcards
            p1_base = pattern1.pattern.rstrip('*')
            p2_base = pattern2.pattern.rstrip('*')
            
            if p1_base and p2_base:
                if p1_base.startswith(p2_base) or p2_base.startswith(p1_base):
                    return True
        
        return False
    
    async def _detect_performance_concerns(
        self,
        config: SelectionConfig
    ) -> List[ConflictReport]:
        """
        Detect potential performance concerns.
        
        Args:
            config: Selection configuration
            
        Returns:
            List of ConflictReport objects
        """
        conflicts = []
        
        # Check for too many patterns
        total_patterns = len(config.include_patterns) + len(config.exclude_patterns)
        if total_patterns > 100:
            conflicts.append(ConflictReport(
                conflict_type=ConflictType.PERFORMANCE_CONCERN,
                affected_paths=[],
                conflicting_rules=[],
                suggested_resolution=(
                    "Consider grouping related patterns or using pattern groups"
                ),
                severity=ConflictSeverity.MEDIUM,
                details={
                    "total_patterns": total_patterns,
                    "reason": "Large number of patterns may impact performance"
                }
            ))
        
        # Check for complex regex patterns
        complex_regex_count = 0
        for pattern in config.include_patterns + config.exclude_patterns:
            if pattern.syntax == PatternSyntax.REGEX and len(pattern.pattern) > 50:
                complex_regex_count += 1
        
        if complex_regex_count > 10:
            conflicts.append(ConflictReport(
                conflict_type=ConflictType.PERFORMANCE_CONCERN,
                affected_paths=[],
                conflicting_rules=[],
                suggested_resolution=(
                    "Consider simplifying complex regex patterns or using GLOB patterns"
                ),
                severity=ConflictSeverity.LOW,
                details={
                    "complex_regex_count": complex_regex_count,
                    "reason": "Many complex regex patterns may impact performance"
                }
            ))
        
        return conflicts
    
    async def check_path_accessibility(
        self,
        paths: List[Path]
    ) -> List[AccessibilityResult]:
        """
        Check accessibility of paths.
        
        Args:
            paths: List of paths to check
            
        Returns:
            List of AccessibilityResult objects
        """
        results = []
        
        for path in paths:
            try:
                exists = path.exists()
                readable = False
                permissions = None
                error_message = None
                
                if exists:
                    try:
                        # Try to read the path
                        if path.is_file():
                            readable = os.access(path, os.R_OK)
                        elif path.is_dir():
                            # For directories, check if we can list contents
                            list(path.iterdir())
                            readable = True
                        
                        # Get permissions
                        stat_info = path.stat()
                        permissions = oct(stat_info.st_mode)[-3:]
                        
                    except PermissionError as e:
                        readable = False
                        error_message = f"Permission denied: {e}"
                    except Exception as e:
                        readable = False
                        error_message = f"Error accessing path: {e}"
                else:
                    error_message = "Path does not exist"
                
                accessible = exists and readable
                
                results.append(AccessibilityResult(
                    path=path,
                    accessible=accessible,
                    exists=exists,
                    readable=readable,
                    error_message=error_message,
                    permissions=permissions
                ))
                
            except Exception as e:
                results.append(AccessibilityResult(
                    path=path,
                    accessible=False,
                    exists=False,
                    readable=False,
                    error_message=f"Error checking path: {e}"
                ))
        
        return results
    
    async def estimate_performance_impact(
        self,
        config: SelectionConfig
    ) -> PerformanceEstimate:
        """
        Estimate performance impact of selection configuration.
        
        Args:
            config: Selection configuration
            
        Returns:
            PerformanceEstimate with performance predictions
        """
        # Compile patterns to get complexity
        all_patterns = config.include_patterns + config.exclude_patterns
        
        if not all_patterns:
            # No patterns, very fast
            return PerformanceEstimate(
                estimated_files_per_second=50000.0,
                estimated_memory_mb=10.0,
                estimated_duration_seconds=0.1,
                optimization_opportunities=[],
                bottlenecks=[]
            )
        
        compiled_patterns = self.pattern_engine.compile_patterns(all_patterns)
        stats = self.pattern_engine.get_pattern_statistics(compiled_patterns)
        
        # Base performance estimate
        base_rate = 10000.0  # files per second
        
        # Adjust for pattern complexity
        complexity_factor = 1.0 / (1.0 + (stats.average_complexity / 50.0))
        
        # Adjust for pattern count
        count_factor = 1.0 / (1.0 + (stats.total_patterns / 100.0))
        
        # Adjust for regex patterns (slower than glob)
        regex_ratio = stats.regex_patterns / stats.total_patterns if stats.total_patterns > 0 else 0.0
        regex_factor = 1.0 - (regex_ratio * 0.3)
        
        # Calculate estimated rate
        estimated_rate = base_rate * complexity_factor * count_factor * regex_factor
        
        # Estimate memory usage (rough heuristic)
        estimated_memory = 10.0 + (stats.total_patterns * 0.1) + (stats.average_complexity * 0.05)
        
        # Estimate duration for 10,000 files
        estimated_duration = 10000.0 / estimated_rate if estimated_rate > 0 else 0.0
        
        # Identify optimization opportunities
        optimization_opportunities = []
        bottlenecks = []
        
        if stats.average_complexity > 50.0:
            bottlenecks.append("High average pattern complexity")
            optimization_opportunities.append("Simplify complex patterns")
        
        if stats.regex_patterns > 20:
            bottlenecks.append(f"Many regex patterns ({stats.regex_patterns})")
            optimization_opportunities.append("Convert regex patterns to GLOB where possible")
        
        if stats.total_patterns > 100:
            bottlenecks.append(f"Large number of patterns ({stats.total_patterns})")
            optimization_opportunities.append("Group related patterns using pattern groups")
        
        if estimated_rate < 1000:
            optimization_opportunities.append("Consider using pattern caching")
            optimization_opportunities.append("Review and optimize pattern order")
        
        return PerformanceEstimate(
            estimated_files_per_second=estimated_rate,
            estimated_memory_mb=estimated_memory,
            estimated_duration_seconds=estimated_duration,
            optimization_opportunities=optimization_opportunities,
            bottlenecks=bottlenecks
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get validation service statistics.
        
        Returns:
            Dictionary with statistics
        """
        return self._stats.copy()
    
    def clear_statistics(self) -> None:
        """Clear validation statistics."""
        self._stats = {
            'total_validations': 0,
            'validation_failures': 0,
            'conflicts_detected': 0,
            'warnings_generated': 0
        }
