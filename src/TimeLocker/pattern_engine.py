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

import fnmatch
import hashlib
import logging
import re
import time
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple

from .selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent,
    ValidationError,
    ValidationWarning,
    ValidationResult,
    PerformanceMetrics,
    RuleMatch
)

logger = logging.getLogger(__name__)


class PatternSyntaxError(Exception):
    """Exception raised for invalid pattern syntax"""
    
    def __init__(self, pattern: str, syntax_type: PatternSyntax, details: str):
        self.pattern = pattern
        self.syntax_type = syntax_type
        self.details = details
        super().__init__(f"Invalid {syntax_type.value} pattern '{pattern}': {details}")


@dataclass
class CompiledPattern:
    """
    Represents a compiled pattern for efficient matching.
    
    Attributes:
        original_rule: The original pattern rule
        compiled_regex: Compiled regex pattern (if applicable)
        literal_value: Literal string value (for LITERAL syntax)
        case_sensitive: Whether matching is case-sensitive
        applies_to: Which path component to match
        priority: Priority for evaluation
        complexity_score: Estimated complexity of the pattern
    """
    original_rule: PatternRule
    compiled_regex: Optional[Pattern] = None
    literal_value: Optional[str] = None
    case_sensitive: bool = False
    applies_to: PathComponent = PathComponent.FULL_PATH
    priority: int = 100
    complexity_score: float = 0.0
    
    def matches(self, path: Path) -> bool:
        """
        Check if this pattern matches the given path.
        
        Args:
            path: Path to check
            
        Returns:
            True if pattern matches
        """
        # Get the appropriate path component
        if self.applies_to == PathComponent.FILENAME:
            test_str = path.name
        elif self.applies_to == PathComponent.DIRECTORY:
            test_str = str(path.parent)
        else:  # FULL_PATH
            test_str = str(path)
        
        # Apply case sensitivity
        if not self.case_sensitive:
            test_str = test_str.lower()
        
        # Match based on pattern type
        if self.literal_value is not None:
            # Literal matching
            compare_value = self.literal_value if self.case_sensitive else self.literal_value.lower()
            return test_str == compare_value
        elif self.compiled_regex is not None:
            # Regex matching
            return self.compiled_regex.match(test_str) is not None
        
        return False


@dataclass
class CompiledPatternSet:
    """
    A set of compiled patterns with metadata.
    
    Attributes:
        patterns: List of compiled patterns
        cache_key: Unique key for caching
        compilation_time_ms: Time taken to compile patterns
        total_complexity: Total complexity score
        pattern_count: Number of patterns
        metadata: Additional metadata
    """
    patterns: List[CompiledPattern]
    cache_key: str
    compilation_time_ms: float
    total_complexity: float
    pattern_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternStats:
    """
    Statistics about compiled patterns.
    
    Attributes:
        total_patterns: Total number of patterns
        glob_patterns: Number of GLOB patterns
        regex_patterns: Number of REGEX patterns
        literal_patterns: Number of LITERAL patterns
        average_complexity: Average complexity score
        max_complexity: Maximum complexity score
        compilation_time_ms: Total compilation time
    """
    total_patterns: int = 0
    glob_patterns: int = 0
    regex_patterns: int = 0
    literal_patterns: int = 0
    average_complexity: float = 0.0
    max_complexity: float = 0.0
    compilation_time_ms: float = 0.0


@dataclass
class MatchResult:
    """
    Result of pattern matching operation.
    
    Attributes:
        matched: Whether the path matched
        matching_patterns: List of patterns that matched
        evaluation_time_ms: Time taken for evaluation
        cache_hit: Whether result came from cache
    """
    matched: bool
    matching_patterns: List[CompiledPattern] = field(default_factory=list)
    evaluation_time_ms: float = 0.0
    cache_hit: bool = False


class PatternEngine:
    """
    High-performance pattern matching engine with compilation and caching.
    
    Supports GLOB, REGEX, and LITERAL pattern syntaxes with optimized
    compilation, caching, and batch processing capabilities.
    """
    
    # LRU cache size for compiled pattern sets
    PATTERN_CACHE_SIZE = 1000
    # LRU cache size for individual path evaluations
    PATH_CACHE_SIZE = 10000
    
    def __init__(self, cache_size: Optional[int] = None):
        """
        Initialize the pattern engine.
        
        Args:
            cache_size: Optional custom cache size for pattern sets
        """
        self._cache_size = cache_size or self.PATTERN_CACHE_SIZE
        self._pattern_cache: Dict[str, CompiledPatternSet] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_compilations = 0
        
        # Statistics
        self._stats = {
            'total_matches': 0,
            'total_match_time_ms': 0.0,
            'cache_hit_ratio': 0.0
        }
    
    def compile_patterns(self, patterns: List[PatternRule]) -> CompiledPatternSet:
        """
        Compile a list of pattern rules into an optimized pattern set.
        
        Args:
            patterns: List of pattern rules to compile
            
        Returns:
            CompiledPatternSet with compiled patterns
            
        Raises:
            PatternSyntaxError: If any pattern has invalid syntax
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(patterns)
        
        # Check cache
        if cache_key in self._pattern_cache:
            self._cache_hits += 1
            logger.debug(f"Pattern cache hit for key {cache_key[:8]}...")
            return self._pattern_cache[cache_key]
        
        self._cache_misses += 1
        self._total_compilations += 1
        
        # Compile patterns
        compiled_patterns = []
        total_complexity = 0.0
        
        for rule in patterns:
            try:
                compiled = self._compile_single_pattern(rule)
                compiled_patterns.append(compiled)
                total_complexity += compiled.complexity_score
            except Exception as e:
                raise PatternSyntaxError(
                    rule.pattern,
                    rule.syntax,
                    str(e)
                )
        
        compilation_time_ms = (time.time() - start_time) * 1000
        
        # Create compiled pattern set
        pattern_set = CompiledPatternSet(
            patterns=compiled_patterns,
            cache_key=cache_key,
            compilation_time_ms=compilation_time_ms,
            total_complexity=total_complexity,
            pattern_count=len(compiled_patterns),
            metadata={
                'original_rules': patterns,
                'compiled_at': time.time()
            }
        )
        
        # Cache the result (with LRU eviction)
        self._cache_pattern_set(cache_key, pattern_set)
        
        logger.debug(
            f"Compiled {len(patterns)} patterns in {compilation_time_ms:.2f}ms "
            f"(complexity: {total_complexity:.2f})"
        )
        
        return pattern_set
    
    def _compile_single_pattern(self, rule: PatternRule) -> CompiledPattern:
        """
        Compile a single pattern rule.
        
        Args:
            rule: Pattern rule to compile
            
        Returns:
            CompiledPattern
            
        Raises:
            ValueError: If pattern syntax is invalid
        """
        compiled = CompiledPattern(
            original_rule=rule,
            case_sensitive=rule.case_sensitive,
            applies_to=rule.applies_to,
            priority=rule.priority
        )

        if self._should_default_to_filename(rule):
            compiled.applies_to = PathComponent.FILENAME
        
        if rule.syntax == PatternSyntax.LITERAL:
            # Literal pattern - direct string comparison
            compiled.literal_value = rule.pattern
            compiled.complexity_score = 1.0
            
        elif rule.syntax == PatternSyntax.GLOB:
            # GLOB pattern - convert to regex
            try:
                regex_pattern = fnmatch.translate(rule.pattern)
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                compiled.compiled_regex = re.compile(regex_pattern, flags)
                # Complexity based on wildcard count
                wildcard_count = rule.pattern.count('*') + rule.pattern.count('?')
                compiled.complexity_score = 10.0 + (wildcard_count * 5.0)
            except re.error as e:
                raise ValueError(f"Invalid GLOB pattern: {e}")
                
        elif rule.syntax == PatternSyntax.REGEX:
            # REGEX pattern - compile directly
            try:
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                compiled.compiled_regex = re.compile(rule.pattern, flags)
                # Complexity based on pattern length and special chars
                special_chars = sum(1 for c in rule.pattern if c in r'.*+?[]{}()|^$\\')
                compiled.complexity_score = 20.0 + (len(rule.pattern) * 0.5) + (special_chars * 2.0)
            except re.error as e:
                raise ValueError(f"Invalid REGEX pattern: {e}")
        else:
            raise ValueError(f"Unsupported pattern syntax: {rule.syntax}")
        
        return compiled

    @staticmethod
    def _should_default_to_filename(rule: PatternRule) -> bool:
        """
        Determine whether a pattern should default to filename matching.

        For legacy behavior we treat patterns without explicit path separators as filename
        matches even when applies_to isn't provided (defaults to FULL_PATH).
        """
        if rule.applies_to != PathComponent.FULL_PATH:
            return False

        separators = {os.sep}
        if os.altsep:
            separators.add(os.altsep)
        separators.add('/')

        pattern = rule.pattern or ""
        return not any(sep in pattern for sep in separators)
    
    def match_path(self, path: Path, compiled_patterns: CompiledPatternSet) -> MatchResult:
        """
        Check if a path matches any pattern in the compiled set.
        
        Args:
            path: Path to check
            compiled_patterns: Compiled pattern set
            
        Returns:
            MatchResult with matching information
        """
        start_time = time.time()
        
        matching_patterns = []
        
        # Evaluate patterns in priority order
        sorted_patterns = sorted(
            compiled_patterns.patterns,
            key=lambda p: p.priority,
            reverse=True
        )
        
        for pattern in sorted_patterns:
            if pattern.matches(path):
                matching_patterns.append(pattern)
        
        evaluation_time_ms = (time.time() - start_time) * 1000
        
        # Update statistics
        self._stats['total_matches'] += 1
        self._stats['total_match_time_ms'] += evaluation_time_ms
        
        return MatchResult(
            matched=len(matching_patterns) > 0,
            matching_patterns=matching_patterns,
            evaluation_time_ms=evaluation_time_ms,
            cache_hit=False
        )
    
    def batch_match_paths(
        self,
        paths: List[Path],
        compiled_patterns: CompiledPatternSet
    ) -> List[MatchResult]:
        """
        Efficiently match multiple paths against compiled patterns.
        
        Args:
            paths: List of paths to check
            compiled_patterns: Compiled pattern set
            
        Returns:
            List of MatchResult for each path
        """
        results = []
        
        for path in paths:
            result = self.match_path(path, compiled_patterns)
            results.append(result)
        
        return results
    
    def get_pattern_statistics(self, compiled_patterns: CompiledPatternSet) -> PatternStats:
        """
        Get statistics about a compiled pattern set.
        
        Args:
            compiled_patterns: Compiled pattern set
            
        Returns:
            PatternStats with statistics
        """
        stats = PatternStats(
            total_patterns=compiled_patterns.pattern_count,
            compilation_time_ms=compiled_patterns.compilation_time_ms
        )
        
        # Count pattern types and calculate complexity
        complexities = []
        for pattern in compiled_patterns.patterns:
            complexities.append(pattern.complexity_score)
            
            if pattern.original_rule.syntax == PatternSyntax.GLOB:
                stats.glob_patterns += 1
            elif pattern.original_rule.syntax == PatternSyntax.REGEX:
                stats.regex_patterns += 1
            elif pattern.original_rule.syntax == PatternSyntax.LITERAL:
                stats.literal_patterns += 1
        
        if complexities:
            stats.average_complexity = sum(complexities) / len(complexities)
            stats.max_complexity = max(complexities)
        
        return stats
    
    def optimize_pattern_order(self, patterns: List[PatternRule]) -> List[PatternRule]:
        """
        Optimize pattern order for better performance.
        
        Patterns are ordered by:
        1. Higher priority first
        2. Lower complexity first (within same priority)
        3. More specific patterns first
        
        Args:
            patterns: List of pattern rules
            
        Returns:
            Optimized list of pattern rules
        """
        # Compile patterns to get complexity scores
        compiled_set = self.compile_patterns(patterns)
        
        # Create mapping of rules to complexity
        complexity_map = {
            id(cp.original_rule): cp.complexity_score
            for cp in compiled_set.patterns
        }
        
        # Sort by priority (desc), then complexity (asc), then specificity
        def sort_key(rule: PatternRule) -> Tuple[int, float, float]:
            complexity = complexity_map.get(id(rule), 0.0)
            specificity = self._calculate_specificity(rule)
            return (-rule.priority, complexity, -specificity)
        
        return sorted(patterns, key=sort_key)
    
    def _calculate_specificity(self, rule: PatternRule) -> float:
        """
        Calculate specificity score for a pattern rule.
        
        Higher scores indicate more specific patterns.
        
        Args:
            rule: Pattern rule
            
        Returns:
            Specificity score
        """
        if rule.syntax == PatternSyntax.LITERAL:
            return 1.0
        elif rule.syntax == PatternSyntax.GLOB:
            # Fewer wildcards = more specific
            wildcard_count = rule.pattern.count('*') + rule.pattern.count('?')
            return 1.0 / (1.0 + wildcard_count)
        else:  # REGEX
            # Estimate based on pattern length and anchors
            score = len(rule.pattern) / 100.0
            if rule.pattern.startswith('^'):
                score += 0.2
            if rule.pattern.endswith('$'):
                score += 0.2
            return min(0.9, score)
    
    def validate_pattern_syntax(
        self,
        pattern: str,
        syntax_type: PatternSyntax
    ) -> ValidationResult:
        """
        Validate pattern syntax without compiling.
        
        Args:
            pattern: Pattern string to validate
            syntax_type: Pattern syntax type
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        suggestions = []
        
        if not pattern:
            errors.append(ValidationError(
                error_type="empty_pattern",
                message="Pattern cannot be empty",
                context={"pattern": pattern, "syntax": syntax_type.value}
            ))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
        
        try:
            # Try to compile the pattern
            test_rule = PatternRule(
                pattern=pattern,
                syntax=syntax_type,
                case_sensitive=False
            )
            self._compile_single_pattern(test_rule)
            
            # Check for common issues
            if syntax_type == PatternSyntax.GLOB:
                if '**' in pattern:
                    warnings.append(ValidationWarning(
                        warning_type="double_wildcard",
                        message="Double wildcard '**' may have unexpected behavior",
                        context={"pattern": pattern},
                        severity="low"
                    ))
                
                if pattern.count('*') > 5:
                    warnings.append(ValidationWarning(
                        warning_type="many_wildcards",
                        message="Pattern has many wildcards, may impact performance",
                        context={"pattern": pattern, "wildcard_count": pattern.count('*')},
                        severity="medium"
                    ))
            
            elif syntax_type == PatternSyntax.REGEX:
                if len(pattern) > 100:
                    warnings.append(ValidationWarning(
                        warning_type="complex_regex",
                        message="Complex regex pattern may impact performance",
                        context={"pattern": pattern, "length": len(pattern)},
                        severity="medium"
                    ))
            
            return ValidationResult(
                is_valid=True,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except Exception as e:
            errors.append(ValidationError(
                error_type="syntax_error",
                message=str(e),
                context={"pattern": pattern, "syntax": syntax_type.value},
                suggested_fix="Check pattern syntax and try again"
            ))
            
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
    
    def _generate_cache_key(self, patterns: List[PatternRule]) -> str:
        """
        Generate a unique cache key for a list of patterns.
        
        Args:
            patterns: List of pattern rules
            
        Returns:
            Cache key string
        """
        # Create deterministic key based on pattern content
        pattern_strings = []
        for pattern in sorted(patterns, key=lambda p: (p.pattern, p.syntax.value, p.priority)):
            pattern_strings.append(
                f"{pattern.syntax.value}:{pattern.pattern}:"
                f"{pattern.case_sensitive}:{pattern.applies_to.value}:{pattern.priority}"
            )
        
        key_data = '|'.join(pattern_strings).encode('utf-8')
        return hashlib.sha256(key_data).hexdigest()[:16]
    
    def _cache_pattern_set(self, cache_key: str, pattern_set: CompiledPatternSet) -> None:
        """
        Cache a compiled pattern set with LRU eviction.
        
        Args:
            cache_key: Cache key
            pattern_set: Compiled pattern set to cache
        """
        # Implement simple LRU by removing oldest if cache is full
        if len(self._pattern_cache) >= self._cache_size:
            # Remove oldest entry (first in dict)
            oldest_key = next(iter(self._pattern_cache))
            del self._pattern_cache[oldest_key]
            logger.debug(f"Evicted pattern cache entry {oldest_key[:8]}...")
        
        self._pattern_cache[cache_key] = pattern_set
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_ratio = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'cache_size': len(self._pattern_cache),
            'cache_capacity': self._cache_size,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_ratio': hit_ratio,
            'total_compilations': self._total_compilations,
            'total_matches': self._stats['total_matches'],
            'average_match_time_ms': (
                self._stats['total_match_time_ms'] / self._stats['total_matches']
                if self._stats['total_matches'] > 0 else 0.0
            )
        }
    
    def clear_cache(self) -> None:
        """Clear the pattern cache."""
        self._pattern_cache.clear()
        logger.info("Pattern cache cleared")



class BatchPatternMatcher:
    """
    Optimized batch pattern matching with performance analysis.
    
    Provides efficient batch processing of paths with pattern ordering
    optimization and complexity analysis.
    """
    
    def __init__(self, pattern_engine: PatternEngine):
        """
        Initialize batch matcher.
        
        Args:
            pattern_engine: PatternEngine instance to use
        """
        self.pattern_engine = pattern_engine
        self._batch_stats = {
            'total_batches': 0,
            'total_paths': 0,
            'total_time_ms': 0.0,
            'average_batch_size': 0.0
        }
    
    def batch_match_optimized(
        self,
        paths: List[Path],
        patterns: List[PatternRule],
        batch_size: int = 1000
    ) -> List[MatchResult]:
        """
        Match paths in optimized batches.
        
        Args:
            paths: List of paths to match
            patterns: List of pattern rules
            batch_size: Size of each batch
            
        Returns:
            List of MatchResult for each path
        """
        start_time = time.time()
        
        # Optimize pattern order first
        optimized_patterns = self.pattern_engine.optimize_pattern_order(patterns)
        
        # Compile patterns once
        compiled_patterns = self.pattern_engine.compile_patterns(optimized_patterns)
        
        # Process in batches
        results = []
        for i in range(0, len(paths), batch_size):
            batch = paths[i:i + batch_size]
            batch_results = self.pattern_engine.batch_match_paths(batch, compiled_patterns)
            results.extend(batch_results)
        
        # Update statistics
        total_time_ms = (time.time() - start_time) * 1000
        self._batch_stats['total_batches'] += 1
        self._batch_stats['total_paths'] += len(paths)
        self._batch_stats['total_time_ms'] += total_time_ms
        self._batch_stats['average_batch_size'] = (
            self._batch_stats['total_paths'] / self._batch_stats['total_batches']
        )
        
        logger.info(
            f"Batch matched {len(paths)} paths in {total_time_ms:.2f}ms "
            f"({len(paths) / (total_time_ms / 1000):.0f} paths/sec)"
        )
        
        return results
    
    def analyze_pattern_complexity(
        self,
        patterns: List[PatternRule]
    ) -> Dict[str, Any]:
        """
        Analyze pattern complexity and provide warnings.
        
        Args:
            patterns: List of pattern rules to analyze
            
        Returns:
            Dictionary with complexity analysis
        """
        # Compile patterns to get complexity scores
        compiled_set = self.pattern_engine.compile_patterns(patterns)
        stats = self.pattern_engine.get_pattern_statistics(compiled_set)
        
        warnings = []
        recommendations = []
        
        # Check for high complexity
        if stats.average_complexity > 50.0:
            warnings.append({
                'type': 'high_average_complexity',
                'message': f'Average pattern complexity is high ({stats.average_complexity:.1f})',
                'severity': 'medium'
            })
            recommendations.append(
                'Consider simplifying patterns or using more literal patterns'
            )
        
        if stats.max_complexity > 100.0:
            warnings.append({
                'type': 'very_high_complexity',
                'message': f'Maximum pattern complexity is very high ({stats.max_complexity:.1f})',
                'severity': 'high'
            })
            recommendations.append(
                'Review the most complex patterns and consider breaking them down'
            )
        
        # Check for too many regex patterns
        if stats.regex_patterns > 20:
            warnings.append({
                'type': 'many_regex_patterns',
                'message': f'Large number of regex patterns ({stats.regex_patterns})',
                'severity': 'medium'
            })
            recommendations.append(
                'Consider using GLOB patterns where possible for better performance'
            )
        
        # Check pattern count
        if stats.total_patterns > 100:
            warnings.append({
                'type': 'many_patterns',
                'message': f'Large number of patterns ({stats.total_patterns})',
                'severity': 'low'
            })
            recommendations.append(
                'Consider grouping related patterns or using pattern groups'
            )
        
        return {
            'statistics': {
                'total_patterns': stats.total_patterns,
                'glob_patterns': stats.glob_patterns,
                'regex_patterns': stats.regex_patterns,
                'literal_patterns': stats.literal_patterns,
                'average_complexity': stats.average_complexity,
                'max_complexity': stats.max_complexity,
                'compilation_time_ms': stats.compilation_time_ms
            },
            'warnings': warnings,
            'recommendations': recommendations,
            'performance_estimate': self._estimate_performance(stats)
        }
    
    def _estimate_performance(self, stats: PatternStats) -> Dict[str, Any]:
        """
        Estimate performance based on pattern statistics.
        
        Args:
            stats: Pattern statistics
            
        Returns:
            Performance estimate dictionary
        """
        # Simple heuristic-based estimation
        base_rate = 10000.0  # Base paths per second
        
        # Adjust for complexity
        complexity_factor = 1.0 / (1.0 + (stats.average_complexity / 50.0))
        
        # Adjust for pattern count
        count_factor = 1.0 / (1.0 + (stats.total_patterns / 100.0))
        
        # Adjust for regex patterns (slower than glob)
        regex_factor = 1.0 - (stats.regex_patterns / stats.total_patterns * 0.3) if stats.total_patterns > 0 else 1.0
        
        estimated_rate = base_rate * complexity_factor * count_factor * regex_factor
        
        return {
            'estimated_paths_per_second': estimated_rate,
            'complexity_factor': complexity_factor,
            'count_factor': count_factor,
            'regex_factor': regex_factor,
            'performance_rating': self._get_performance_rating(estimated_rate)
        }
    
    def _get_performance_rating(self, paths_per_second: float) -> str:
        """
        Get performance rating based on estimated rate.
        
        Args:
            paths_per_second: Estimated paths per second
            
        Returns:
            Performance rating string
        """
        if paths_per_second >= 8000:
            return 'excellent'
        elif paths_per_second >= 5000:
            return 'good'
        elif paths_per_second >= 2000:
            return 'fair'
        else:
            return 'poor'
    
    def get_batch_statistics(self) -> Dict[str, Any]:
        """
        Get batch processing statistics.
        
        Returns:
            Dictionary with batch statistics
        """
        return self._batch_stats.copy()
    
    def optimize_for_large_dataset(
        self,
        patterns: List[PatternRule],
        estimated_path_count: int
    ) -> List[PatternRule]:
        """
        Optimize patterns for large dataset processing.
        
        Args:
            patterns: List of pattern rules
            estimated_path_count: Estimated number of paths to process
            
        Returns:
            Optimized list of pattern rules
        """
        # For large datasets, prioritize:
        # 1. Literal patterns (fastest)
        # 2. Simple glob patterns
        # 3. Complex patterns last
        
        optimized = self.pattern_engine.optimize_pattern_order(patterns)
        
        # If dataset is very large, add additional optimizations
        if estimated_path_count > 100000:
            logger.info(
                f"Applying large dataset optimizations for {estimated_path_count} paths"
            )
            
            # Group patterns by type for better cache locality
            literal_patterns = [p for p in optimized if p.syntax == PatternSyntax.LITERAL]
            glob_patterns = [p for p in optimized if p.syntax == PatternSyntax.GLOB]
            regex_patterns = [p for p in optimized if p.syntax == PatternSyntax.REGEX]
            
            # Reorder: literals first, then globs, then regex
            optimized = literal_patterns + glob_patterns + regex_patterns
        
        return optimized
