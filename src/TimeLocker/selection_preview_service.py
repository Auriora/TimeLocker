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
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Set

from .pattern_engine import PatternEngine
from .precedence_resolver import PrecedenceResolver
from .selection_models import (
    PreviewResult,
    RuleMatch,
    SelectionConfig,
    SizeEstimate
)

logger = logging.getLogger(__name__)


class SelectionPreviewError(Exception):
    """Exception raised for preview operation failures"""
    pass


@dataclass
class PreviewOptions:
    """
    Options for preview generation.
    
    Attributes:
        max_samples: Maximum number of sample files to include
        include_excluded_samples: Whether to include samples of excluded files
        max_depth: Maximum directory depth to traverse (None for unlimited)
        follow_symlinks: Whether to follow symbolic links
        timeout_seconds: Timeout for preview generation (None for no timeout)
        show_progress: Whether to show progress during generation
    """
    max_samples: int = 1000
    include_excluded_samples: bool = True
    max_depth: Optional[int] = None
    follow_symlinks: bool = False
    timeout_seconds: Optional[float] = None
    show_progress: bool = False


@dataclass
class ProgressInfo:
    """
    Progress information for long-running operations.
    
    Attributes:
        files_processed: Number of files processed so far
        directories_processed: Number of directories processed
        bytes_processed: Number of bytes processed
        elapsed_seconds: Elapsed time in seconds
        estimated_total_files: Estimated total number of files
        estimated_completion_seconds: Estimated time to completion
        current_path: Current path being processed
    """
    files_processed: int = 0
    directories_processed: int = 0
    bytes_processed: int = 0
    elapsed_seconds: float = 0.0
    estimated_total_files: Optional[int] = None
    estimated_completion_seconds: Optional[float] = None
    current_path: Optional[Path] = None


class SelectionPreviewService:
    """
    Service for generating selection previews and size estimates.
    
    Provides file sampling, size estimation with progress reporting,
    and accessible file checking.
    """
    
    def __init__(
        self,
        pattern_engine: Optional[PatternEngine] = None,
        precedence_resolver: Optional[PrecedenceResolver] = None
    ):
        """
        Initialize the preview service.
        
        Args:
            pattern_engine: PatternEngine instance (creates new if None)
            precedence_resolver: PrecedenceResolver instance (creates new if None)
        """
        self.pattern_engine = pattern_engine or PatternEngine()
        self.precedence_resolver = precedence_resolver or PrecedenceResolver()
        
        # Cancellation support
        self._cancelled = False
        
        # Statistics
        self._stats = {
            'total_previews': 0,
            'total_estimates': 0,
            'total_files_scanned': 0,
            'total_bytes_scanned': 0
        }
    
    async def generate_selection_preview(
        self,
        config: SelectionConfig,
        base_paths: List[Path],
        options: Optional[PreviewOptions] = None
    ) -> PreviewResult:
        """
        Generate a preview of selection results.
        
        Args:
            config: Selection configuration
            base_paths: Base paths to start traversal from
            options: Preview options (uses defaults if None)
            
        Returns:
            PreviewResult with sample files and summary
            
        Raises:
            SelectionPreviewError: If preview generation fails
        """
        self._stats['total_previews'] += 1
        self._cancelled = False
        
        options = options or PreviewOptions()
        start_time = time.time()
        
        logger.info(f"Generating selection preview for {len(base_paths)} base path(s)")
        
        try:
            # Compile patterns
            include_patterns = self.pattern_engine.compile_patterns(config.include_patterns)
            exclude_patterns = self.pattern_engine.compile_patterns(config.exclude_patterns)
            
            # Collect samples
            included_samples: List[Path] = []
            excluded_samples: List[Path] = []
            total_files_seen = 0
            
            # Traverse file system
            async for path, is_included in self._traverse_and_evaluate(
                base_paths,
                config,
                include_patterns,
                exclude_patterns,
                options
            ):
                if self._cancelled:
                    logger.info("Preview generation cancelled")
                    break
                
                total_files_seen += 1
                
                if is_included:
                    if len(included_samples) < options.max_samples:
                        included_samples.append(path)
                else:
                    if options.include_excluded_samples and len(excluded_samples) < options.max_samples:
                        excluded_samples.append(path)
                
                # Check if we have enough samples
                if (len(included_samples) >= options.max_samples and
                    (not options.include_excluded_samples or len(excluded_samples) >= options.max_samples)):
                    break
            
            generation_time = time.time() - start_time
            
            # Generate summary
            summary = self._generate_summary(
                included_samples,
                excluded_samples,
                total_files_seen,
                config
            )
            
            truncated = (
                len(included_samples) >= options.max_samples or
                (options.include_excluded_samples and len(excluded_samples) >= options.max_samples)
            )
            
            logger.info(
                f"Preview generated in {generation_time:.2f}s: "
                f"{len(included_samples)} included, {len(excluded_samples)} excluded samples"
            )
            
            return PreviewResult(
                sample_included_files=included_samples,
                sample_excluded_files=excluded_samples,
                total_estimated_files=total_files_seen,
                preview_generation_time=generation_time,
                truncated=truncated,
                selection_summary=summary
            )
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            raise SelectionPreviewError(f"Failed to generate preview: {e}") from e
    
    async def estimate_selection_size(
        self,
        config: SelectionConfig,
        base_paths: List[Path],
        progress_callback: Optional[callable] = None
    ) -> SizeEstimate:
        """
        Estimate size and file count for selection.
        
        Args:
            config: Selection configuration
            base_paths: Base paths to start traversal from
            progress_callback: Optional callback for progress updates
            
        Returns:
            SizeEstimate with size and count information
            
        Raises:
            SelectionPreviewError: If estimation fails
        """
        self._stats['total_estimates'] += 1
        self._cancelled = False
        
        start_time = time.time()
        
        logger.info(f"Estimating selection size for {len(base_paths)} base path(s)")
        
        try:
            # Compile patterns
            include_patterns = self.pattern_engine.compile_patterns(config.include_patterns)
            exclude_patterns = self.pattern_engine.compile_patterns(config.exclude_patterns)
            
            # Accumulate statistics
            total_size = 0
            file_count = 0
            directory_count = 0
            inaccessible_paths: List[Path] = []
            
            # Traverse file system
            options = PreviewOptions(
                max_samples=float('inf'),  # No limit for estimation
                include_excluded_samples=False,
                follow_symlinks=False
            )
            
            async for path, is_included in self._traverse_and_evaluate(
                base_paths,
                config,
                include_patterns,
                exclude_patterns,
                options
            ):
                if self._cancelled:
                    logger.info("Size estimation cancelled")
                    break
                
                if is_included:
                    try:
                        if path.is_file():
                            stat_info = path.stat()
                            total_size += stat_info.st_size
                            file_count += 1
                            self._stats['total_bytes_scanned'] += stat_info.st_size
                        elif path.is_dir():
                            directory_count += 1
                        
                        self._stats['total_files_scanned'] += 1
                        
                        # Report progress
                        if progress_callback and file_count % 100 == 0:
                            progress = ProgressInfo(
                                files_processed=file_count,
                                directories_processed=directory_count,
                                bytes_processed=total_size,
                                elapsed_seconds=time.time() - start_time,
                                current_path=path
                            )
                            progress_callback(progress)
                        
                    except (PermissionError, OSError) as e:
                        logger.debug(f"Cannot access {path}: {e}")
                        inaccessible_paths.append(path)
            
            estimation_time = time.time() - start_time
            
            # Calculate accuracy (100% if we scanned everything, lower if cancelled)
            accuracy = 0.9 if not self._cancelled else 0.5
            
            logger.info(
                f"Size estimation complete in {estimation_time:.2f}s: "
                f"{file_count} files, {total_size} bytes, "
                f"{len(inaccessible_paths)} inaccessible"
            )
            
            return SizeEstimate(
                total_size_bytes=total_size,
                file_count=file_count,
                directory_count=directory_count,
                estimation_accuracy=accuracy,
                inaccessible_paths=inaccessible_paths,
                estimation_time_seconds=estimation_time
            )
            
        except Exception as e:
            logger.error(f"Error estimating size: {e}")
            raise SelectionPreviewError(f"Failed to estimate size: {e}") from e
    
    async def _traverse_and_evaluate(
        self,
        base_paths: List[Path],
        config: SelectionConfig,
        include_patterns,
        exclude_patterns,
        options: PreviewOptions
    ) -> AsyncIterator[tuple[Path, bool]]:
        """
        Traverse file system and evaluate each path.
        
        Args:
            base_paths: Base paths to start from
            config: Selection configuration
            include_patterns: Compiled include patterns
            exclude_patterns: Compiled exclude patterns
            options: Preview options
            
        Yields:
            Tuples of (path, is_included)
        """
        visited: Set[Path] = set()
        
        for base_path in base_paths:
            if not base_path.exists():
                logger.warning(f"Base path does not exist: {base_path}")
                continue
            
            async for path, is_included in self._traverse_path(
                base_path,
                config,
                include_patterns,
                exclude_patterns,
                options,
                visited,
                depth=0
            ):
                yield path, is_included
    
    async def _traverse_path(
        self,
        path: Path,
        config: SelectionConfig,
        include_patterns,
        exclude_patterns,
        options: PreviewOptions,
        visited: Set[Path],
        depth: int
    ) -> AsyncIterator[tuple[Path, bool]]:
        """
        Recursively traverse a path.
        
        Args:
            path: Path to traverse
            config: Selection configuration
            include_patterns: Compiled include patterns
            exclude_patterns: Compiled exclude patterns
            options: Preview options
            visited: Set of already visited paths
            depth: Current depth
            
        Yields:
            Tuples of (path, is_included)
        """
        # Check cancellation
        if self._cancelled:
            return
        
        # Check depth limit
        if options.max_depth is not None and depth > options.max_depth:
            return
        
        # Avoid cycles
        try:
            resolved_path = path.resolve()
            if resolved_path in visited:
                return
            visited.add(resolved_path)
        except (OSError, RuntimeError):
            # Can't resolve path, skip it
            return
        
        # Check if path should be included
        is_included = self._evaluate_path(
            path,
            config,
            include_patterns,
            exclude_patterns
        )
        
        # Yield current path
        yield path, is_included
        
        # If it's a directory and included (or we want to check subdirectories),
        # traverse its contents
        if path.is_dir():
            # Skip excluded directories unless we need to check for re-inclusions
            if not is_included and config.precedence_config.default_strategy.value != "layered":
                return
            
            try:
                # List directory contents
                entries = list(path.iterdir())
                
                # Process entries
                for entry in entries:
                    # Check symlinks
                    if entry.is_symlink() and not options.follow_symlinks:
                        continue
                    
                    # Recursively traverse
                    async for sub_path, sub_included in self._traverse_path(
                        entry,
                        config,
                        include_patterns,
                        exclude_patterns,
                        options,
                        visited,
                        depth + 1
                    ):
                        yield sub_path, sub_included
                    
                    # Yield control periodically
                    if len(visited) % 100 == 0:
                        await asyncio.sleep(0)
                
            except (PermissionError, OSError) as e:
                logger.debug(f"Cannot access directory {path}: {e}")
    
    def _evaluate_path(
        self,
        path: Path,
        config: SelectionConfig,
        include_patterns,
        exclude_patterns
    ) -> bool:
        """
        Evaluate whether a path should be included.
        
        Args:
            path: Path to evaluate
            config: Selection configuration
            include_patterns: Compiled include patterns
            exclude_patterns: Compiled exclude patterns
            
        Returns:
            True if path should be included
        """
        # Check explicit paths first
        for include_path in config.include_paths:
            try:
                path.relative_to(include_path)
                # Path is within an include path
                
                # Check if it's explicitly excluded
                for exclude_path in config.exclude_paths:
                    if path == exclude_path or path.is_relative_to(exclude_path):
                        return False
                
                # Check patterns
                return self._evaluate_patterns(
                    path,
                    include_patterns,
                    exclude_patterns,
                    config
                )
            except ValueError:
                continue
        
        # Not in any include path, check patterns only
        return self._evaluate_patterns(
            path,
            include_patterns,
            exclude_patterns,
            config
        )
    
    def _evaluate_patterns(
        self,
        path: Path,
        include_patterns,
        exclude_patterns,
        config: SelectionConfig
    ) -> bool:
        """
        Evaluate path against patterns.
        
        Args:
            path: Path to evaluate
            include_patterns: Compiled include patterns
            exclude_patterns: Compiled exclude patterns
            config: Selection configuration
            
        Returns:
            True if path should be included
        """
        # Match against patterns
        include_matches = []
        exclude_matches = []
        
        # Check include patterns
        include_result = self.pattern_engine.match_path(path, include_patterns)
        if include_result.matched:
            for pattern in include_result.matching_patterns:
                include_matches.append(RuleMatch(
                    rule=pattern.original_rule,
                    path=path,
                    match_type="include",
                    confidence=1.0
                ))
        
        # Check exclude patterns
        exclude_result = self.pattern_engine.match_path(path, exclude_patterns)
        if exclude_result.matched:
            for pattern in exclude_result.matching_patterns:
                exclude_matches.append(RuleMatch(
                    rule=pattern.original_rule,
                    path=path,
                    match_type="exclude",
                    confidence=1.0
                ))
        
        # No matches - default to exclude
        if not include_matches and not exclude_matches:
            return False
        
        # Only include matches
        if include_matches and not exclude_matches:
            return True
        
        # Only exclude matches
        if exclude_matches and not include_matches:
            return False
        
        # Both types of matches - resolve precedence
        all_matches = include_matches + exclude_matches
        decision = self.precedence_resolver.resolve_selection_conflicts(path, all_matches)
        
        return decision.include
    
    def _generate_summary(
        self,
        included_samples: List[Path],
        excluded_samples: List[Path],
        total_files_seen: int,
        config: SelectionConfig
    ) -> str:
        """
        Generate a summary of the selection preview.
        
        Args:
            included_samples: Sample of included files
            excluded_samples: Sample of excluded files
            total_files_seen: Total number of files seen
            config: Selection configuration
            
        Returns:
            Summary string
        """
        summary_parts = []
        
        summary_parts.append(f"Selection Preview Summary")
        summary_parts.append(f"=" * 50)
        summary_parts.append(f"Total files scanned: {total_files_seen}")
        summary_parts.append(f"Included samples: {len(included_samples)}")
        summary_parts.append(f"Excluded samples: {len(excluded_samples)}")
        summary_parts.append("")
        
        summary_parts.append(f"Configuration:")
        summary_parts.append(f"  Include paths: {len(config.include_paths)}")
        summary_parts.append(f"  Exclude paths: {len(config.exclude_paths)}")
        summary_parts.append(f"  Include patterns: {len(config.include_patterns)}")
        summary_parts.append(f"  Exclude patterns: {len(config.exclude_patterns)}")
        summary_parts.append(f"  Precedence strategy: {config.precedence_config.default_strategy.value}")
        
        if included_samples:
            summary_parts.append("")
            summary_parts.append(f"Sample included files (showing up to 10):")
            for path in included_samples[:10]:
                summary_parts.append(f"  + {path}")
        
        if excluded_samples:
            summary_parts.append("")
            summary_parts.append(f"Sample excluded files (showing up to 10):")
            for path in excluded_samples[:10]:
                summary_parts.append(f"  - {path}")
        
        return "\n".join(summary_parts)
    
    def cancel(self) -> None:
        """Cancel ongoing preview or estimation operation."""
        self._cancelled = True
        logger.info("Preview/estimation operation cancelled")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get preview service statistics.
        
        Returns:
            Dictionary with statistics
        """
        return self._stats.copy()
    
    def clear_statistics(self) -> None:
        """Clear preview service statistics."""
        self._stats = {
            'total_previews': 0,
            'total_estimates': 0,
            'total_files_scanned': 0,
            'total_bytes_scanned': 0
        }
