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

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pattern_engine import PatternEngine, MatchResult
from .precedence_resolver import PrecedenceResolver
from .selection_models import (
    PatternRule,
    PrecedenceConfig,
    RuleMatch,
    SelectionConfig,
    SelectionDecision,
    SelectionResult,
    SizeEstimate,
    PreviewResult,
    ValidationResult,
    EvaluationStats,
    PerformanceMetrics
)
from .selection_performance_optimizer import (
    SelectionPerformanceOptimizer,
    OptimizedSelection
)
from .selection_template_manager import SelectionTemplateManager
from .selection_validation_service import SelectionValidationService

logger = logging.getLogger(__name__)


class SelectionError(Exception):
    """Base exception for selection operations"""
    pass


class SelectionEvaluationError(SelectionError):
    """Exception raised during selection evaluation"""
    pass


@dataclass
class DataSelection:
    """
    Complete data selection with compiled patterns and configuration.
    
    Attributes:
        config: Selection configuration
        compiled_patterns: Compiled pattern set (if patterns exist)
        precedence_resolver: Precedence resolver instance
        performance_optimizer: Performance optimizer instance
        metadata: Additional metadata
        created_at: Creation timestamp
        last_optimized: Last optimization timestamp
    """
    config: SelectionConfig
    compiled_patterns: Optional[Any] = None
    precedence_resolver: Optional[PrecedenceResolver] = None
    performance_optimizer: Optional[SelectionPerformanceOptimizer] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_optimized: Optional[float] = None


class SelectionManager:
    """
    Central coordinator for data selection operations and rule evaluation.
    
    The SelectionManager orchestrates all selection-related operations including:
    - Selection creation and compilation
    - File system evaluation with rule application
    - Template management integration
    - Performance optimization
    - Validation and conflict detection
    - Size estimation and preview generation
    - Testing and debugging support
    
    This is the primary interface for working with data selection in TimeLocker.
    """
    
    def __init__(
        self,
        template_manager: Optional[SelectionTemplateManager] = None,
        pattern_engine: Optional[PatternEngine] = None,
        validation_service: Optional[SelectionValidationService] = None,
        performance_optimizer: Optional[SelectionPerformanceOptimizer] = None
    ):
        """
        Initialize the selection manager.
        
        Args:
            template_manager: Template manager instance (creates new if None)
            pattern_engine: Pattern engine instance (creates new if None)
            validation_service: Validation service instance (creates new if None)
            performance_optimizer: Performance optimizer instance (creates new if None)
        """
        self.template_manager = template_manager or SelectionTemplateManager()
        self.pattern_engine = pattern_engine or PatternEngine()
        self.validation_service = validation_service or SelectionValidationService(
            pattern_engine=self.pattern_engine
        )
        self.performance_optimizer = performance_optimizer or SelectionPerformanceOptimizer(
            pattern_engine=self.pattern_engine
        )
        
        # Statistics
        self._stats = {
            'selections_created': 0,
            'evaluations_performed': 0,
            'validations_performed': 0,
            'optimizations_applied': 0,
            'total_files_evaluated': 0
        }
        
        logger.info("SelectionManager initialized")
    
    async def create_selection(self, config: SelectionConfig) -> DataSelection:
        """
        Create a new data selection from configuration.
        
        This method validates the configuration, compiles patterns, and creates
        a ready-to-use DataSelection object with all necessary components.
        
        Args:
            config: Selection configuration
            
        Returns:
            DataSelection: Compiled and ready-to-use selection
            
        Raises:
            SelectionError: If configuration is invalid or compilation fails
        """
        start_time = time.time()
        self._stats['selections_created'] += 1
        
        logger.info("Creating new data selection")
        
        # Validate configuration
        validation_result = await self.validation_service.validate_selection_config(config)
        if not validation_result.is_valid:
            error_messages = [e.message for e in validation_result.errors]
            raise SelectionError(
                f"Invalid selection configuration: {'; '.join(error_messages)}"
            )
        
        # Log warnings
        for warning in validation_result.warnings:
            logger.warning(f"Selection configuration warning: {warning.message}")
        
        # Compile patterns
        compiled_patterns = None
        all_patterns = config.include_patterns + config.exclude_patterns
        if all_patterns:
            try:
                compiled_patterns = self.pattern_engine.compile_patterns(all_patterns)
                logger.debug(
                    f"Compiled {len(all_patterns)} patterns in "
                    f"{compiled_patterns.compilation_time_ms:.2f}ms"
                )
            except Exception as e:
                raise SelectionError(f"Failed to compile patterns: {e}")
        
        # Create precedence resolver
        precedence_resolver = PrecedenceResolver(config.precedence_config)
        
        # Create data selection
        selection = DataSelection(
            config=config,
            compiled_patterns=compiled_patterns,
            precedence_resolver=precedence_resolver,
            performance_optimizer=self.performance_optimizer,
            metadata={
                'validation_warnings': len(validation_result.warnings),
                'pattern_count': len(all_patterns),
                'creation_time_ms': (time.time() - start_time) * 1000
            }
        )
        
        logger.info(
            f"Created data selection with {len(all_patterns)} patterns in "
            f"{selection.metadata['creation_time_ms']:.2f}ms"
        )
        
        return selection
    
    async def evaluate_selection(
        self,
        selection: DataSelection,
        base_paths: List[Path]
    ) -> SelectionResult:
        """
        Evaluate a selection against file system paths.
        
        This method traverses the specified base paths and applies the selection
        rules to determine which files should be included or excluded.
        
        Args:
            selection: Data selection to evaluate
            base_paths: Base paths to evaluate
            
        Returns:
            SelectionResult: Result of the evaluation
            
        Raises:
            SelectionEvaluationError: If evaluation fails
        """
        start_time = time.time()
        self._stats['evaluations_performed'] += 1
        
        logger.info(f"Evaluating selection against {len(base_paths)} base path(s)")
        
        included_paths = []
        excluded_paths = []
        warnings = []
        files_evaluated = 0
        
        try:
            # Evaluate each base path
            for base_path in base_paths:
                if not base_path.exists():
                    warning = f"Base path does not exist: {base_path}"
                    warnings.append(warning)
                    logger.warning(warning)
                    continue
                
                # Traverse and evaluate
                if base_path.is_file():
                    # Single file
                    decision = await self._evaluate_path(selection, base_path)
                    if decision.include:
                        included_paths.append(base_path)
                    else:
                        excluded_paths.append(base_path)
                    files_evaluated += 1
                    
                elif base_path.is_dir():
                    # Directory - traverse recursively
                    for path in self._traverse_directory(base_path, selection):
                        decision = await self._evaluate_path(selection, path)
                        if decision.include:
                            included_paths.append(path)
                        else:
                            excluded_paths.append(path)
                        files_evaluated += 1
                        
                        # Log progress for large evaluations
                        if files_evaluated % 10000 == 0:
                            logger.info(f"Evaluated {files_evaluated} files...")
            
            # Calculate statistics
            evaluation_time = time.time() - start_time
            files_per_second = files_evaluated / evaluation_time if evaluation_time > 0 else 0
            
            # Update global statistics
            self._stats['total_files_evaluated'] += files_evaluated
            
            # Create result
            result = SelectionResult(
                included_paths=included_paths,
                excluded_paths=excluded_paths,
                evaluation_stats=EvaluationStats(
                    files_evaluated=files_evaluated,
                    files_included=len(included_paths),
                    files_excluded=len(excluded_paths),
                    evaluation_time_seconds=evaluation_time
                ),
                warnings=warnings,
                performance_metrics=PerformanceMetrics(
                    files_per_second=files_per_second,
                    evaluation_time_ms=evaluation_time * 1000
                )
            )
            
            logger.info(
                f"Evaluation complete: {len(included_paths)} included, "
                f"{len(excluded_paths)} excluded, {files_per_second:.0f} files/sec"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Selection evaluation failed: {e}")
            raise SelectionEvaluationError(f"Evaluation failed: {e}")
    
    def _traverse_directory(
        self,
        directory: Path,
        selection: DataSelection
    ) -> List[Path]:
        """
        Traverse directory and return all file paths.
        
        This method performs optimized directory traversal, skipping excluded
        directories early to improve performance.
        
        Args:
            directory: Directory to traverse
            selection: Data selection for optimization hints
            
        Returns:
            List of file paths
        """
        paths = []
        
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    paths.append(item)
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {directory}: {e}")
        except Exception as e:
            logger.error(f"Error traversing {directory}: {e}")
        
        return paths
    
    async def _evaluate_path(
        self,
        selection: DataSelection,
        path: Path
    ) -> SelectionDecision:
        """
        Evaluate a single path against selection rules.
        
        Args:
            selection: Data selection
            path: Path to evaluate
            
        Returns:
            SelectionDecision for the path
        """
        # Check explicit include/exclude paths first
        config = selection.config
        
        # Check if path is explicitly included
        for include_path in config.include_paths:
            try:
                path.relative_to(include_path)
                # Path is within an include path
                break
            except ValueError:
                continue
        else:
            # Path is not within any include path
            if config.include_paths:
                return SelectionDecision(
                    include=False,
                    confidence=1.0,
                    applied_rules=[],
                    precedence_explanation="Path not within any include path"
                )
        
        # Check if path is explicitly excluded
        for exclude_path in config.exclude_paths:
            try:
                path.relative_to(exclude_path)
                # Path is within an exclude path
                return SelectionDecision(
                    include=False,
                    confidence=1.0,
                    applied_rules=[],
                    precedence_explanation=f"Path within excluded path: {exclude_path}"
                )
            except ValueError:
                continue
        
        # Evaluate patterns if they exist
        if selection.compiled_patterns:
            # Match against patterns
            match_result = self.pattern_engine.match_path(path, selection.compiled_patterns)
            
            if match_result.matched:
                # Create rule matches
                matches = []
                for compiled_pattern in match_result.matching_patterns:
                    # Determine if this is an include or exclude pattern
                    is_include = compiled_pattern.original_rule in config.include_patterns
                    match_type = "include" if is_include else "exclude"
                    
                    matches.append(RuleMatch(
                        rule=compiled_pattern.original_rule,
                        path=path,
                        match_type=match_type,
                        confidence=1.0
                    ))
                
                # Resolve precedence if there are conflicts
                if matches:
                    return selection.precedence_resolver.resolve_selection_conflicts(
                        path,
                        matches
                    )
        
        # Default: include if within include paths, exclude otherwise
        if config.include_paths:
            return SelectionDecision(
                include=True,
                confidence=0.8,
                applied_rules=[],
                precedence_explanation="Default inclusion (within include path, no patterns matched)"
            )
        else:
            return SelectionDecision(
                include=False,
                confidence=0.8,
                applied_rules=[],
                precedence_explanation="Default exclusion (no include paths specified)"
            )
    
    async def estimate_selection_size(
        self,
        selection: DataSelection,
        base_paths: List[Path]
    ) -> SizeEstimate:
        """
        Estimate the size of files that would be selected.
        
        Args:
            selection: Data selection
            base_paths: Base paths to estimate
            
        Returns:
            SizeEstimate with size information
        """
        start_time = time.time()
        
        logger.info(f"Estimating selection size for {len(base_paths)} base path(s)")
        
        total_size = 0
        file_count = 0
        directory_count = 0
        inaccessible_paths = []
        
        try:
            # Evaluate selection to get included paths
            result = await self.evaluate_selection(selection, base_paths)
            
            # Calculate sizes
            for path in result.included_paths:
                try:
                    if path.is_file():
                        total_size += path.stat().st_size
                        file_count += 1
                    elif path.is_dir():
                        directory_count += 1
                except (PermissionError, OSError) as e:
                    inaccessible_paths.append(path)
                    logger.warning(f"Cannot access {path}: {e}")
            
            estimation_time = time.time() - start_time
            
            # Calculate accuracy (100% if no inaccessible paths)
            total_paths = len(result.included_paths)
            accuracy = 1.0 - (len(inaccessible_paths) / total_paths) if total_paths > 0 else 1.0
            
            estimate = SizeEstimate(
                total_size_bytes=total_size,
                file_count=file_count,
                directory_count=directory_count,
                estimation_accuracy=accuracy,
                inaccessible_paths=inaccessible_paths,
                estimation_time_seconds=estimation_time
            )
            
            logger.info(
                f"Size estimate: {total_size / (1024**3):.2f} GB, "
                f"{file_count} files, {directory_count} directories "
                f"(accuracy: {accuracy:.1%})"
            )
            
            return estimate
            
        except Exception as e:
            logger.error(f"Size estimation failed: {e}")
            raise SelectionError(f"Size estimation failed: {e}")
    
    async def preview_selection(
        self,
        selection: DataSelection,
        base_paths: List[Path],
        limit: int = 1000
    ) -> PreviewResult:
        """
        Generate a preview of selection results.
        
        Args:
            selection: Data selection
            base_paths: Base paths to preview
            limit: Maximum number of files to include in preview
            
        Returns:
            PreviewResult with sample files
        """
        start_time = time.time()
        
        logger.info(f"Generating selection preview (limit: {limit})")
        
        try:
            # Evaluate selection
            result = await self.evaluate_selection(selection, base_paths)
            
            # Sample results
            sample_included = result.included_paths[:limit]
            sample_excluded = result.excluded_paths[:limit]
            truncated = (
                len(result.included_paths) > limit or
                len(result.excluded_paths) > limit
            )
            
            preview_time = time.time() - start_time
            
            # Generate summary
            summary = (
                f"Preview: {len(sample_included)} included (of {len(result.included_paths)}), "
                f"{len(sample_excluded)} excluded (of {len(result.excluded_paths)})"
            )
            
            preview = PreviewResult(
                sample_included_files=sample_included,
                sample_excluded_files=sample_excluded,
                total_estimated_files=len(result.included_paths) + len(result.excluded_paths),
                preview_generation_time=preview_time,
                truncated=truncated,
                selection_summary=summary
            )
            
            logger.info(f"Preview generated in {preview_time:.2f}s: {summary}")
            
            return preview
            
        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            raise SelectionError(f"Preview generation failed: {e}")
    
    async def validate_selection(self, selection: DataSelection) -> ValidationResult:
        """
        Validate a data selection.
        
        Args:
            selection: Data selection to validate
            
        Returns:
            ValidationResult with validation details
        """
        self._stats['validations_performed'] += 1
        
        logger.info("Validating data selection")
        
        return await self.validation_service.validate_selection_config(selection.config)
    
    async def test_pattern_match(
        self,
        pattern: str,
        test_paths: List[str]
    ) -> Dict[str, Any]:
        """
        Test a pattern against sample paths.
        
        Args:
            pattern: Pattern string to test
            test_paths: List of path strings to test against
            
        Returns:
            Dictionary with match results
        """
        logger.info(f"Testing pattern '{pattern}' against {len(test_paths)} paths")
        
        from .selection_models import PatternSyntax, PathComponent
        
        # Create a pattern rule
        pattern_rule = PatternRule(
            pattern=pattern,
            syntax=PatternSyntax.GLOB,  # Default to GLOB
            case_sensitive=False,
            applies_to=PathComponent.FULL_PATH
        )
        
        # Compile pattern
        try:
            compiled_patterns = self.pattern_engine.compile_patterns([pattern_rule])
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'matches': []
            }
        
        # Test against paths
        matches = []
        for path_str in test_paths:
            path = Path(path_str)
            result = self.pattern_engine.match_path(path, compiled_patterns)
            if result.matched:
                matches.append(path_str)
        
        return {
            'success': True,
            'pattern': pattern,
            'total_paths': len(test_paths),
            'matched_count': len(matches),
            'matches': matches
        }
    
    def get_effective_precedence_rules(
        self,
        selection: DataSelection
    ) -> PrecedenceConfig:
        """
        Get the effective precedence rules for a selection.
        
        Args:
            selection: Data selection
            
        Returns:
            PrecedenceConfig: Effective precedence configuration
        """
        return selection.config.precedence_config
    
    async def optimize_selection_for_performance(
        self,
        selection: DataSelection,
        estimated_file_count: Optional[int] = None
    ) -> OptimizedSelection:
        """
        Optimize a selection for better performance.
        
        Args:
            selection: Data selection to optimize
            estimated_file_count: Optional estimated file count
            
        Returns:
            OptimizedSelection with optimizations applied
        """
        self._stats['optimizations_applied'] += 1
        
        logger.info("Optimizing selection for performance")
        
        if estimated_file_count is None:
            # Use a default estimate
            estimated_file_count = 10000
        
        optimized = await self.performance_optimizer.optimize_selection_for_size(
            selection.config,
            estimated_file_count
        )
        
        # Update selection's last_optimized timestamp
        selection.last_optimized = time.time()
        
        logger.info(
            f"Selection optimized: {len(optimized.optimization_applied)} optimizations applied, "
            f"estimated gain: {optimized.estimated_performance_gain:.1f}x"
        )
        
        return optimized
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get selection manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            **self._stats,
            'template_count': len(self.template_manager.templates_cache),
            'pattern_engine_stats': self.pattern_engine.get_cache_statistics()
        }
