#!/usr/bin/env python3
"""
Pattern Engine Demo

Demonstrates the advanced pattern matching capabilities of the PatternEngine
and BatchPatternMatcher classes.

Copyright ©  Bruce Cherrington
Licensed under GPL v3
"""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

from TimeLocker.pattern_engine import PatternEngine, BatchPatternMatcher
from TimeLocker.selection_models import PatternRule, PatternSyntax, PathComponent


def demo_basic_pattern_matching():
    """Demonstrate basic pattern matching with different syntaxes."""
    print("=" * 70)
    print("DEMO 1: Basic Pattern Matching")
    print("=" * 70)
    
    engine = PatternEngine()
    
    # Create patterns with different syntaxes
    patterns = [
        # GLOB patterns
        PatternRule('*.txt', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('*.py', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('test_*.py', PatternSyntax.GLOB, False, PathComponent.FILENAME, 150),
        
        # LITERAL patterns (exact match)
        PatternRule('README.md', PatternSyntax.LITERAL, True, PathComponent.FILENAME, 200),
        PatternRule('LICENSE', PatternSyntax.LITERAL, True, PathComponent.FILENAME, 200),
        
        # REGEX patterns
        PatternRule(r'.*\.log$', PatternSyntax.REGEX, False, PathComponent.FILENAME, 100),
        PatternRule(r'^config.*\.json$', PatternSyntax.REGEX, False, PathComponent.FILENAME, 150),
    ]
    
    # Compile patterns
    compiled = engine.compile_patterns(patterns)
    print(f"\n✓ Compiled {compiled.pattern_count} patterns in {compiled.compilation_time_ms:.2f}ms")
    print(f"  Total complexity: {compiled.total_complexity:.1f}")
    
    # Test paths
    test_paths = [
        Path('/home/user/document.txt'),
        Path('/home/user/script.py'),
        Path('/home/user/test_module.py'),
        Path('/home/user/README.md'),
        Path('/home/user/LICENSE'),
        Path('/home/user/app.log'),
        Path('/home/user/config_prod.json'),
        Path('/home/user/image.jpg'),
        Path('/home/user/data.csv'),
    ]
    
    print("\nPattern Matching Results:")
    print("-" * 70)
    for path in test_paths:
        result = engine.match_path(path, compiled)
        if result.matched:
            matching_patterns = [p.original_rule.pattern for p in result.matching_patterns]
            print(f"✓ MATCH: {path.name:25} | Patterns: {', '.join(matching_patterns)}")
        else:
            print(f"✗ NO MATCH: {path.name}")


def demo_pattern_statistics():
    """Demonstrate pattern statistics and complexity analysis."""
    print("\n" + "=" * 70)
    print("DEMO 2: Pattern Statistics and Complexity Analysis")
    print("=" * 70)
    
    engine = PatternEngine()
    batch_matcher = BatchPatternMatcher(engine)
    
    # Create a mix of patterns with varying complexity
    patterns = [
        # Simple patterns
        PatternRule('*.txt', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('README.md', PatternSyntax.LITERAL, True, PathComponent.FILENAME, 200),
        
        # Medium complexity
        PatternRule('test_*.py', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule(r'.*\.log$', PatternSyntax.REGEX, False, PathComponent.FILENAME, 100),
        
        # Higher complexity
        PatternRule('**/*.tmp', PatternSyntax.GLOB, False, PathComponent.FULL_PATH, 50),
        PatternRule(r'^[a-z]+_\d{4}_\d{2}_\d{2}\.backup$', PatternSyntax.REGEX, False, PathComponent.FILENAME, 100),
    ]
    
    # Compile and get statistics
    compiled = engine.compile_patterns(patterns)
    stats = engine.get_pattern_statistics(compiled)
    
    print("\nPattern Statistics:")
    print("-" * 70)
    print(f"Total patterns:      {stats.total_patterns}")
    print(f"  - GLOB patterns:   {stats.glob_patterns}")
    print(f"  - REGEX patterns:  {stats.regex_patterns}")
    print(f"  - LITERAL patterns: {stats.literal_patterns}")
    print(f"Average complexity:  {stats.average_complexity:.2f}")
    print(f"Max complexity:      {stats.max_complexity:.2f}")
    print(f"Compilation time:    {stats.compilation_time_ms:.2f}ms")
    
    # Analyze complexity
    analysis = batch_matcher.analyze_pattern_complexity(patterns)
    
    print("\nComplexity Analysis:")
    print("-" * 70)
    perf = analysis['performance_estimate']
    print(f"Estimated rate:      {perf['estimated_paths_per_second']:.0f} paths/sec")
    print(f"Performance rating:  {perf['performance_rating'].upper()}")
    print(f"Complexity factor:   {perf['complexity_factor']:.2f}")
    print(f"Count factor:        {perf['count_factor']:.2f}")
    print(f"Regex factor:        {perf['regex_factor']:.2f}")
    
    if analysis['warnings']:
        print("\nWarnings:")
        for warning in analysis['warnings']:
            print(f"  ⚠ [{warning['severity'].upper()}] {warning['message']}")
    
    if analysis['recommendations']:
        print("\nRecommendations:")
        for rec in analysis['recommendations']:
            print(f"  💡 {rec}")


def demo_batch_processing():
    """Demonstrate batch processing with performance metrics."""
    print("\n" + "=" * 70)
    print("DEMO 3: Batch Processing")
    print("=" * 70)
    
    engine = PatternEngine()
    batch_matcher = BatchPatternMatcher(engine)
    
    # Create patterns
    patterns = [
        PatternRule('*.py', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('*.txt', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('*.md', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('test_*', PatternSyntax.GLOB, False, PathComponent.FILENAME, 150),
    ]
    
    # Generate test paths
    test_paths = []
    for i in range(1000):
        if i % 4 == 0:
            test_paths.append(Path(f'/project/module_{i}.py'))
        elif i % 4 == 1:
            test_paths.append(Path(f'/project/doc_{i}.txt'))
        elif i % 4 == 2:
            test_paths.append(Path(f'/project/README_{i}.md'))
        else:
            test_paths.append(Path(f'/project/test_case_{i}.py'))
    
    print(f"\nProcessing {len(test_paths)} paths...")
    
    # Batch process
    results = batch_matcher.batch_match_optimized(test_paths, patterns, batch_size=100)
    
    # Count matches
    matched_count = sum(1 for r in results if r.matched)
    
    print(f"\nBatch Processing Results:")
    print("-" * 70)
    print(f"Total paths:         {len(test_paths)}")
    print(f"Matched paths:       {matched_count}")
    print(f"Unmatched paths:     {len(test_paths) - matched_count}")
    
    # Get batch statistics
    batch_stats = batch_matcher.get_batch_statistics()
    print(f"\nBatch Statistics:")
    print(f"Total batches:       {batch_stats['total_batches']}")
    print(f"Total paths:         {batch_stats['total_paths']}")
    print(f"Total time:          {batch_stats['total_time_ms']:.2f}ms")
    print(f"Average batch size:  {batch_stats['average_batch_size']:.0f}")
    
    # Calculate throughput
    if batch_stats['total_time_ms'] > 0:
        throughput = batch_stats['total_paths'] / (batch_stats['total_time_ms'] / 1000)
        print(f"Throughput:          {throughput:.0f} paths/sec")


def demo_pattern_optimization():
    """Demonstrate pattern ordering optimization."""
    print("\n" + "=" * 70)
    print("DEMO 4: Pattern Ordering Optimization")
    print("=" * 70)
    
    engine = PatternEngine()
    
    # Create patterns with different priorities and complexities
    patterns = [
        PatternRule('*.tmp', PatternSyntax.GLOB, False, PathComponent.FILENAME, 50),
        PatternRule('README.md', PatternSyntax.LITERAL, True, PathComponent.FILENAME, 200),
        PatternRule('**/*.log', PatternSyntax.GLOB, False, PathComponent.FULL_PATH, 75),
        PatternRule(r'^test_.*\.py$', PatternSyntax.REGEX, False, PathComponent.FILENAME, 100),
        PatternRule('*.py', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('config.json', PatternSyntax.LITERAL, True, PathComponent.FILENAME, 200),
    ]
    
    print("\nOriginal Pattern Order:")
    print("-" * 70)
    for i, pattern in enumerate(patterns, 1):
        print(f"{i}. [{pattern.syntax.value:7}] {pattern.pattern:20} (priority: {pattern.priority})")
    
    # Optimize pattern order
    optimized = engine.optimize_pattern_order(patterns)
    
    print("\nOptimized Pattern Order:")
    print("-" * 70)
    for i, pattern in enumerate(optimized, 1):
        print(f"{i}. [{pattern.syntax.value:7}] {pattern.pattern:20} (priority: {pattern.priority})")
    
    print("\nOptimization Strategy:")
    print("-" * 70)
    print("1. Higher priority patterns evaluated first")
    print("2. Lower complexity patterns within same priority")
    print("3. More specific patterns before general ones")


def demo_pattern_validation():
    """Demonstrate pattern syntax validation."""
    print("\n" + "=" * 70)
    print("DEMO 5: Pattern Syntax Validation")
    print("=" * 70)
    
    engine = PatternEngine()
    
    # Test various patterns
    test_cases = [
        ('*.txt', PatternSyntax.GLOB, True),
        ('', PatternSyntax.GLOB, False),  # Empty pattern
        (r'.*\.log$', PatternSyntax.REGEX, True),
        (r'[invalid(regex', PatternSyntax.REGEX, False),  # Invalid regex
        ('README.md', PatternSyntax.LITERAL, True),
        ('**/**/***', PatternSyntax.GLOB, True),  # Valid but may have warnings
    ]
    
    print("\nValidation Results:")
    print("-" * 70)
    
    for pattern, syntax, expected_valid in test_cases:
        result = engine.validate_pattern_syntax(pattern, syntax)
        status = "✓ VALID" if result.is_valid else "✗ INVALID"
        print(f"\n{status}: [{syntax.value:7}] '{pattern}'")
        
        if result.errors:
            for error in result.errors:
                print(f"  ✗ Error: {error.message}")
                if error.suggested_fix:
                    print(f"    Fix: {error.suggested_fix}")
        
        if result.warnings:
            for warning in result.warnings:
                print(f"  ⚠ Warning [{warning.severity}]: {warning.message}")


def demo_cache_performance():
    """Demonstrate caching performance benefits."""
    print("\n" + "=" * 70)
    print("DEMO 6: Cache Performance")
    print("=" * 70)
    
    engine = PatternEngine()
    
    patterns = [
        PatternRule('*.py', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('*.txt', PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule('test_*', PatternSyntax.GLOB, False, PathComponent.FILENAME, 150),
    ]
    
    print("\nCompiling patterns multiple times to demonstrate caching...")
    
    # First compilation (cache miss)
    compiled1 = engine.compile_patterns(patterns)
    print(f"\n1st compilation: {compiled1.compilation_time_ms:.2f}ms (cache miss)")
    
    # Second compilation (cache hit)
    compiled2 = engine.compile_patterns(patterns)
    print(f"2nd compilation: {compiled2.compilation_time_ms:.2f}ms (cache hit)")
    
    # Third compilation (cache hit)
    compiled3 = engine.compile_patterns(patterns)
    print(f"3rd compilation: {compiled3.compilation_time_ms:.2f}ms (cache hit)")
    
    # Get cache statistics
    cache_stats = engine.get_cache_statistics()
    
    print("\nCache Statistics:")
    print("-" * 70)
    print(f"Cache size:          {cache_stats['cache_size']}/{cache_stats['cache_capacity']}")
    print(f"Cache hits:          {cache_stats['cache_hits']}")
    print(f"Cache misses:        {cache_stats['cache_misses']}")
    print(f"Hit ratio:           {cache_stats['hit_ratio']:.2%}")
    print(f"Total compilations:  {cache_stats['total_compilations']}")
    
    if cache_stats['total_matches'] > 0:
        print(f"Total matches:       {cache_stats['total_matches']}")
        print(f"Avg match time:      {cache_stats['average_match_time_ms']:.2f}ms")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PATTERN ENGINE DEMONSTRATION" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        demo_basic_pattern_matching()
        demo_pattern_statistics()
        demo_batch_processing()
        demo_pattern_optimization()
        demo_pattern_validation()
        demo_cache_performance()
        
        print("\n" + "=" * 70)
        print("✅ All demos completed successfully!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
