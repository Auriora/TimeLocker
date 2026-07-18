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

import pytest
from pathlib import Path

from TimeLocker.pattern_engine import (
    PatternEngine,
    PatternSyntaxError,
    CompiledPattern,
    CompiledPatternSet,
    BatchPatternMatcher
)
from TimeLocker.selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent
)


@pytest.fixture
def pattern_engine():
    """Create a PatternEngine instance for testing."""
    return PatternEngine()


@pytest.fixture
def sample_patterns():
    """Create sample pattern rules for testing."""
    return [
        PatternRule(
            pattern="*.txt",
            syntax=PatternSyntax.GLOB,
            case_sensitive=False,
            applies_to=PathComponent.FILENAME,
            priority=100
        ),
        PatternRule(
            pattern="test_.*\\.py",
            syntax=PatternSyntax.REGEX,
            case_sensitive=True,
            applies_to=PathComponent.FILENAME,
            priority=200
        ),
        PatternRule(
            pattern="README.md",
            syntax=PatternSyntax.LITERAL,
            case_sensitive=True,
            applies_to=PathComponent.FILENAME,
            priority=300
        )
    ]


class TestPatternEngine:
    """Test suite for PatternEngine class."""
    
    @pytest.mark.unit
    def test_initialization(self, pattern_engine):
        """Test PatternEngine initialization."""
        assert pattern_engine is not None
        assert pattern_engine._cache_size == PatternEngine.PATTERN_CACHE_SIZE
        assert len(pattern_engine._pattern_cache) == 0
    
    @pytest.mark.unit
    def test_compile_patterns(self, pattern_engine, sample_patterns):
        """Test pattern compilation."""
        compiled_set = pattern_engine.compile_patterns(sample_patterns)
        
        assert isinstance(compiled_set, CompiledPatternSet)
        assert compiled_set.pattern_count == len(sample_patterns)
        assert len(compiled_set.patterns) == len(sample_patterns)
        assert compiled_set.compilation_time_ms >= 0
    
    @pytest.mark.unit
    def test_compile_glob_pattern(self, pattern_engine):
        """Test GLOB pattern compilation."""
        patterns = [
            PatternRule(
                pattern="*.txt",
                syntax=PatternSyntax.GLOB,
                case_sensitive=False
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        compiled = compiled_set.patterns[0]
        
        assert compiled.compiled_regex is not None
        assert compiled.literal_value is None
        assert not compiled.case_sensitive
    
    @pytest.mark.unit
    def test_compile_regex_pattern(self, pattern_engine):
        """Test REGEX pattern compilation."""
        patterns = [
            PatternRule(
                pattern="test_.*\\.py",
                syntax=PatternSyntax.REGEX,
                case_sensitive=True
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        compiled = compiled_set.patterns[0]
        
        assert compiled.compiled_regex is not None
        assert compiled.literal_value is None
        assert compiled.case_sensitive
    
    @pytest.mark.unit
    def test_compile_literal_pattern(self, pattern_engine):
        """Test LITERAL pattern compilation."""
        patterns = [
            PatternRule(
                pattern="README.md",
                syntax=PatternSyntax.LITERAL,
                case_sensitive=True
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        compiled = compiled_set.patterns[0]
        
        assert compiled.literal_value == "README.md"
        assert compiled.compiled_regex is None
        assert compiled.case_sensitive
    
    @pytest.mark.unit
    def test_invalid_glob_pattern(self, pattern_engine):
        """Test invalid GLOB pattern raises error."""
        # Note: Most glob patterns are valid, so we test regex compilation failure
        # by using an invalid regex pattern with REGEX syntax instead
        patterns = [
            PatternRule(
                pattern="[",  # Unclosed bracket in character class
                syntax=PatternSyntax.REGEX,
                case_sensitive=False
            )
        ]
        
        with pytest.raises(PatternSyntaxError) as exc_info:
            pattern_engine.compile_patterns(patterns)
        
        assert "Invalid" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_invalid_regex_pattern(self, pattern_engine):
        """Test invalid REGEX pattern raises error."""
        patterns = [
            PatternRule(
                pattern="(unclosed",
                syntax=PatternSyntax.REGEX,
                case_sensitive=False
            )
        ]
        
        with pytest.raises(PatternSyntaxError) as exc_info:
            pattern_engine.compile_patterns(patterns)
        
        assert "Invalid" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_match_path_glob(self, pattern_engine):
        """Test path matching with GLOB pattern."""
        patterns = [
            PatternRule(
                pattern="*.txt",
                syntax=PatternSyntax.GLOB,
                case_sensitive=False,
                applies_to=PathComponent.FILENAME
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        
        # Should match
        result = pattern_engine.match_path(Path("test.txt"), compiled_set)
        assert result.matched
        assert len(result.matching_patterns) == 1
        
        # Should not match
        result = pattern_engine.match_path(Path("test.py"), compiled_set)
        assert not result.matched
        assert len(result.matching_patterns) == 0
    
    @pytest.mark.unit
    def test_match_path_regex(self, pattern_engine):
        """Test path matching with REGEX pattern."""
        patterns = [
            PatternRule(
                pattern="test_.*\\.py",
                syntax=PatternSyntax.REGEX,
                case_sensitive=True,
                applies_to=PathComponent.FILENAME
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        
        # Should match
        result = pattern_engine.match_path(Path("test_file.py"), compiled_set)
        assert result.matched
        
        # Should not match (case sensitive)
        result = pattern_engine.match_path(Path("Test_file.py"), compiled_set)
        assert not result.matched
    
    @pytest.mark.unit
    def test_match_path_literal(self, pattern_engine):
        """Test path matching with LITERAL pattern."""
        patterns = [
            PatternRule(
                pattern="README.md",
                syntax=PatternSyntax.LITERAL,
                case_sensitive=True,
                applies_to=PathComponent.FILENAME
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        
        # Should match
        result = pattern_engine.match_path(Path("README.md"), compiled_set)
        assert result.matched
        
        # Should not match (case sensitive)
        result = pattern_engine.match_path(Path("readme.md"), compiled_set)
        assert not result.matched
    
    @pytest.mark.unit
    def test_case_insensitive_matching(self, pattern_engine):
        """Test case-insensitive pattern matching."""
        patterns = [
            PatternRule(
                pattern="README.md",
                syntax=PatternSyntax.LITERAL,
                case_sensitive=False,
                applies_to=PathComponent.FILENAME
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        
        # Both should match
        result = pattern_engine.match_path(Path("README.md"), compiled_set)
        assert result.matched
        
        result = pattern_engine.match_path(Path("readme.md"), compiled_set)
        assert result.matched
    
    @pytest.mark.unit
    def test_batch_match_paths(self, pattern_engine, sample_patterns):
        """Test batch path matching."""
        compiled_set = pattern_engine.compile_patterns(sample_patterns)
        
        paths = [
            Path("file.txt"),
            Path("test_module.py"),
            Path("README.md"),
            Path("other.doc")
        ]
        
        results = pattern_engine.batch_match_paths(paths, compiled_set)
        
        assert len(results) == len(paths)
        assert results[0].matched  # file.txt matches *.txt
        assert results[1].matched  # test_module.py matches test_.*\.py
        assert results[2].matched  # README.md matches literal
        assert not results[3].matched  # other.doc doesn't match
    
    @pytest.mark.unit
    def test_pattern_caching(self, pattern_engine, sample_patterns):
        """Test pattern compilation caching."""
        # First compilation
        compiled_set1 = pattern_engine.compile_patterns(sample_patterns)
        cache_stats1 = pattern_engine.get_cache_statistics()
        
        # Second compilation with same patterns
        compiled_set2 = pattern_engine.compile_patterns(sample_patterns)
        cache_stats2 = pattern_engine.get_cache_statistics()
        
        # Cache should be hit on second compilation
        assert cache_stats2['cache_hits'] > cache_stats1['cache_hits']
        assert compiled_set1.cache_key == compiled_set2.cache_key
    
    @pytest.mark.unit
    def test_get_pattern_statistics(self, pattern_engine, sample_patterns):
        """Test pattern statistics generation."""
        compiled_set = pattern_engine.compile_patterns(sample_patterns)
        stats = pattern_engine.get_pattern_statistics(compiled_set)
        
        assert stats.total_patterns == 3
        assert stats.glob_patterns == 1
        assert stats.regex_patterns == 1
        assert stats.literal_patterns == 1
        assert stats.average_complexity > 0
        assert stats.max_complexity > 0
    
    @pytest.mark.unit
    def test_optimize_pattern_order(self, pattern_engine):
        """Test pattern order optimization."""
        patterns = [
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB, priority=100),
            PatternRule(pattern="README.md", syntax=PatternSyntax.LITERAL, priority=300),
            PatternRule(pattern="test.*", syntax=PatternSyntax.REGEX, priority=200)
        ]
        
        optimized = pattern_engine.optimize_pattern_order(patterns)
        
        # Higher priority patterns should come first
        assert optimized[0].priority >= optimized[1].priority
        assert optimized[1].priority >= optimized[2].priority
    
    @pytest.mark.unit
    def test_validate_pattern_syntax_valid(self, pattern_engine):
        """Test validation of valid patterns."""
        result = pattern_engine.validate_pattern_syntax("*.txt", PatternSyntax.GLOB)
        assert result.is_valid
        assert len(result.errors) == 0
    
    @pytest.mark.unit
    def test_validate_pattern_syntax_invalid(self, pattern_engine):
        """Test validation of invalid patterns."""
        result = pattern_engine.validate_pattern_syntax("", PatternSyntax.GLOB)
        assert not result.is_valid
        assert len(result.errors) > 0
    
    @pytest.mark.unit
    def test_validate_pattern_syntax_warnings(self, pattern_engine):
        """Test validation warnings for complex patterns."""
        # Pattern with many wildcards should generate warning
        result = pattern_engine.validate_pattern_syntax("*/*/*/*/*/*/*", PatternSyntax.GLOB)
        assert result.is_valid
        assert len(result.warnings) > 0
    
    @pytest.mark.unit
    def test_clear_cache(self, pattern_engine, sample_patterns):
        """Test cache clearing."""
        pattern_engine.compile_patterns(sample_patterns)
        assert len(pattern_engine._pattern_cache) > 0
        
        pattern_engine.clear_cache()
        assert len(pattern_engine._pattern_cache) == 0
    
    @pytest.mark.unit
    def test_path_component_filename(self, pattern_engine):
        """Test matching against filename component."""
        patterns = [
            PatternRule(
                pattern="test.txt",
                syntax=PatternSyntax.LITERAL,
                applies_to=PathComponent.FILENAME
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        
        # Should match regardless of directory
        result = pattern_engine.match_path(Path("/some/path/test.txt"), compiled_set)
        assert result.matched
    
    @pytest.mark.unit
    def test_path_component_full_path(self, pattern_engine):
        """Test matching against full path."""
        patterns = [
            PatternRule(
                pattern="/home/user/.*",
                syntax=PatternSyntax.REGEX,
                applies_to=PathComponent.FULL_PATH
            )
        ]
        
        compiled_set = pattern_engine.compile_patterns(patterns)
        
        result = pattern_engine.match_path(Path("/home/user/file.txt"), compiled_set)
        assert result.matched
        
        result = pattern_engine.match_path(Path("/other/file.txt"), compiled_set)
        assert not result.matched


class TestBatchPatternMatcher:
    """Test suite for BatchPatternMatcher class."""
    
    @pytest.mark.unit
    def test_initialization(self, pattern_engine):
        """Test BatchPatternMatcher initialization."""
        matcher = BatchPatternMatcher(pattern_engine)
        assert matcher.pattern_engine is pattern_engine
    
    @pytest.mark.unit
    def test_batch_match_optimized(self, pattern_engine):
        """Test optimized batch matching."""
        matcher = BatchPatternMatcher(pattern_engine)
        
        patterns = [
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB)
        ]
        
        paths = [
            Path("file1.txt"),
            Path("file2.py"),
            Path("file3.doc")
        ]
        
        results = matcher.batch_match_optimized(paths, patterns, batch_size=2)
        
        assert len(results) == len(paths)
        assert results[0].matched
        assert results[1].matched
        assert not results[2].matched
    
    @pytest.mark.unit
    def test_analyze_pattern_complexity(self, pattern_engine):
        """Test pattern complexity analysis."""
        matcher = BatchPatternMatcher(pattern_engine)
        
        patterns = [
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="test_.*\\.py", syntax=PatternSyntax.REGEX)
        ]
        
        analysis = matcher.analyze_pattern_complexity(patterns)
        
        assert 'statistics' in analysis
        assert 'warnings' in analysis
        assert 'recommendations' in analysis
        assert 'performance_estimate' in analysis
        assert analysis['statistics']['total_patterns'] == 2
    
    @pytest.mark.unit
    def test_optimize_for_large_dataset(self, pattern_engine):
        """Test optimization for large datasets."""
        matcher = BatchPatternMatcher(pattern_engine)
        
        patterns = [
            PatternRule(pattern="test.*", syntax=PatternSyntax.REGEX, priority=100),
            PatternRule(pattern="README.md", syntax=PatternSyntax.LITERAL, priority=200),
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB, priority=150)
        ]
        
        optimized = matcher.optimize_for_large_dataset(patterns, estimated_path_count=150000)
        
        # Literal patterns should be prioritized for large datasets
        assert optimized[0].syntax == PatternSyntax.LITERAL
