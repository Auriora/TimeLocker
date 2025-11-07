#!/usr/bin/env python3
"""
Demonstration of the PrecedenceResolver and SelectionDebugger functionality.

This example shows how to:
1. Configure precedence resolution strategies
2. Resolve conflicts between include and exclude rules
3. Use the debugger to understand selection decisions
4. Generate detailed reports
"""

from pathlib import Path
from TimeLocker.pattern_engine import PatternEngine
from TimeLocker.precedence_resolver import PrecedenceResolver
from TimeLocker.selection_debugger import SelectionDebugger
from TimeLocker.selection_models import (
    ConflictResolution,
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    PrecedenceStrategy,
    RuleMatch,
    SelectionConfig
)


def demo_basic_precedence():
    """Demonstrate basic precedence resolution."""
    print("=" * 80)
    print("DEMO 1: Basic Precedence Resolution")
    print("=" * 80)
    print()
    
    # Create precedence resolver with default config
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    resolver = PrecedenceResolver(config)
    
    # Create some test rules
    test_path = Path("/home/user/documents/report.pdf")
    
    include_rule = RuleMatch(
        rule=PatternRule(
            pattern="/home/user/documents/*",
            syntax=PatternSyntax.GLOB,
            priority=100
        ),
        path=test_path,
        match_type="include"
    )
    
    exclude_rule = RuleMatch(
        rule=PatternRule(
            pattern="*.pdf",
            syntax=PatternSyntax.GLOB,
            priority=100
        ),
        path=test_path,
        match_type="exclude"
    )
    
    # Resolve conflict
    decision = resolver.resolve_selection_conflicts(
        test_path,
        [include_rule, exclude_rule]
    )
    
    print(f"Path: {test_path}")
    print(f"Include rule: {include_rule.rule.pattern}")
    print(f"Exclude rule: {exclude_rule.rule.pattern}")
    print(f"Strategy: {config.default_strategy.value}")
    print()
    print(f"Decision: {'INCLUDE' if decision.include else 'EXCLUDE'}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Explanation: {decision.precedence_explanation}")
    print()


def demo_specificity_resolution():
    """Demonstrate specificity-based resolution."""
    print("=" * 80)
    print("DEMO 2: Specificity-Based Resolution")
    print("=" * 80)
    print()
    
    # Create resolver with specificity strategy
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.MOST_SPECIFIC_WINS,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    resolver = PrecedenceResolver(config)
    
    test_path = Path("/home/user/temp/important.txt")
    
    # General include rule
    general_include = RuleMatch(
        rule=PatternRule(
            pattern="/home/user/*",
            syntax=PatternSyntax.GLOB,
            priority=100
        ),
        path=test_path,
        match_type="include"
    )
    
    # Specific exclude rule
    specific_exclude = RuleMatch(
        rule=PatternRule(
            pattern="/home/user/temp/*",
            syntax=PatternSyntax.GLOB,
            priority=100
        ),
        path=test_path,
        match_type="exclude"
    )
    
    # Very specific include rule
    very_specific_include = RuleMatch(
        rule=PatternRule(
            pattern="/home/user/temp/important.txt",
            syntax=PatternSyntax.LITERAL,
            priority=100
        ),
        path=test_path,
        match_type="include"
    )
    
    # Resolve conflict
    decision = resolver.resolve_selection_conflicts(
        test_path,
        [general_include, specific_exclude, very_specific_include]
    )
    
    print(f"Path: {test_path}")
    print(f"Rules:")
    print(f"  1. Include: {general_include.rule.pattern} (GLOB)")
    print(f"  2. Exclude: {specific_exclude.rule.pattern} (GLOB)")
    print(f"  3. Include: {very_specific_include.rule.pattern} (LITERAL)")
    print(f"Strategy: {config.default_strategy.value}")
    print()
    print(f"Decision: {'INCLUDE' if decision.include else 'EXCLUDE'}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Explanation: {decision.precedence_explanation}")
    print()


def demo_layered_evaluation():
    """Demonstrate layered evaluation strategy."""
    print("=" * 80)
    print("DEMO 3: Layered Evaluation")
    print("=" * 80)
    print()
    
    # Create resolver with layered strategy
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.LAYERED_EVALUATION,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    resolver = PrecedenceResolver(config)
    
    test_path = Path("/home/user/temp/important.txt")
    
    # Layer 1: Include home directory
    layer1 = RuleMatch(
        rule=PatternRule(
            pattern="/home/user",
            syntax=PatternSyntax.LITERAL,
            priority=100
        ),
        path=test_path,
        match_type="include"
    )
    
    # Layer 2: Exclude temp directory
    layer2 = RuleMatch(
        rule=PatternRule(
            pattern="/home/user/temp",
            syntax=PatternSyntax.LITERAL,
            priority=100
        ),
        path=test_path,
        match_type="exclude"
    )
    
    # Layer 3: Re-include specific file
    layer3 = RuleMatch(
        rule=PatternRule(
            pattern="/home/user/temp/important.txt",
            syntax=PatternSyntax.LITERAL,
            priority=100
        ),
        path=test_path,
        match_type="include"
    )
    
    # Resolve with layered evaluation
    decision = resolver.resolve_selection_conflicts(
        test_path,
        [layer1, layer2, layer3]
    )
    
    print(f"Path: {test_path}")
    print(f"Layered rules (least to most specific):")
    print(f"  Layer 1: Include {layer1.rule.pattern}")
    print(f"  Layer 2: Exclude {layer2.rule.pattern}")
    print(f"  Layer 3: Include {layer3.rule.pattern}")
    print(f"Strategy: {config.default_strategy.value}")
    print()
    print(f"Decision: {'INCLUDE' if decision.include else 'EXCLUDE'}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Explanation: {decision.precedence_explanation}")
    
    if decision.warnings:
        print()
        print("Evaluation steps:")
        for warning in decision.warnings:
            print(f"  {warning}")
    print()


def demo_debugger():
    """Demonstrate the selection debugger."""
    print("=" * 80)
    print("DEMO 4: Selection Debugger")
    print("=" * 80)
    print()
    
    # Create pattern engine and precedence resolver
    pattern_engine = PatternEngine()
    
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.MOST_SPECIFIC_WINS,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    precedence_resolver = PrecedenceResolver(config)
    
    # Create debugger
    debugger = SelectionDebugger(pattern_engine, precedence_resolver)
    
    # Enable tracing
    debugger.enable_tracing(verbose=True)
    
    # Create selection configuration
    selection_config = SelectionConfig(
        include_patterns=[
            PatternRule(
                pattern="/home/user/documents/*",
                syntax=PatternSyntax.GLOB,
                priority=100
            ),
            PatternRule(
                pattern="*.txt",
                syntax=PatternSyntax.GLOB,
                priority=90
            )
        ],
        exclude_patterns=[
            PatternRule(
                pattern="*.tmp",
                syntax=PatternSyntax.GLOB,
                priority=100
            ),
            PatternRule(
                pattern="/home/user/documents/private/*",
                syntax=PatternSyntax.GLOB,
                priority=110
            )
        ],
        precedence_config=config
    )
    
    # Test a path
    test_path = Path("/home/user/documents/report.txt")
    
    result = debugger.test_path_selection(test_path, selection_config)
    
    print(f"Testing path: {test_path}")
    print()
    print(f"Decision: {'INCLUDE' if result.decision.include else 'EXCLUDE'}")
    print(f"Confidence: {result.decision.confidence:.2f}")
    print(f"Matching rules: {len(result.matching_rules)}")
    print()
    
    print("Trace log:")
    for line in result.trace_log:
        print(f"  {line}")
    print()
    
    if result.recommendations:
        print("Recommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")
        print()


def demo_selection_report():
    """Demonstrate generating a selection report."""
    print("=" * 80)
    print("DEMO 5: Selection Report")
    print("=" * 80)
    print()
    
    # Create pattern engine and precedence resolver
    pattern_engine = PatternEngine()
    
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    precedence_resolver = PrecedenceResolver(config)
    
    # Create debugger
    debugger = SelectionDebugger(pattern_engine, precedence_resolver)
    
    # Create selection configuration
    selection_config = SelectionConfig(
        include_patterns=[
            PatternRule(pattern="/home/user/*", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.pdf", syntax=PatternSyntax.GLOB)
        ],
        exclude_patterns=[
            PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.log", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="/home/user/temp/*", syntax=PatternSyntax.GLOB)
        ],
        precedence_config=config
    )
    
    # Sample paths to test
    sample_paths = [
        Path("/home/user/documents/report.txt"),
        Path("/home/user/documents/report.pdf"),
        Path("/home/user/temp/data.txt"),
        Path("/home/user/logs/app.log"),
        Path("/home/user/backup.tmp")
    ]
    
    # Generate report
    report = debugger.generate_selection_report(selection_config, sample_paths)
    
    # Format and print report
    formatted_report = debugger.format_report_as_text(report)
    print(formatted_report)


def demo_precedence_explanation():
    """Demonstrate detailed precedence explanation."""
    print("=" * 80)
    print("DEMO 6: Detailed Precedence Explanation")
    print("=" * 80)
    print()
    
    # Create resolver
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.EXPLICIT_PRIORITY,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    resolver = PrecedenceResolver(config)
    
    test_path = Path("/home/user/documents/report.pdf")
    
    # Create rules with different priorities
    high_priority_exclude = RuleMatch(
        rule=PatternRule(
            pattern="*.pdf",
            syntax=PatternSyntax.GLOB,
            priority=200
        ),
        path=test_path,
        match_type="exclude"
    )
    
    medium_priority_include = RuleMatch(
        rule=PatternRule(
            pattern="/home/user/documents/*",
            syntax=PatternSyntax.GLOB,
            priority=150
        ),
        path=test_path,
        match_type="include"
    )
    
    low_priority_include = RuleMatch(
        rule=PatternRule(
            pattern="/home/user/*",
            syntax=PatternSyntax.GLOB,
            priority=100
        ),
        path=test_path,
        match_type="include"
    )
    
    # Get detailed explanation
    explanation = resolver.get_precedence_explanation(
        test_path,
        [medium_priority_include, low_priority_include],
        [high_priority_exclude]
    )
    
    print(f"Path: {explanation.path}")
    print(f"Strategy: {explanation.strategy_used.value}")
    print(f"Decision: {'INCLUDE' if explanation.decision else 'EXCLUDE'}")
    print(f"Confidence: {explanation.confidence:.2f}")
    print()
    
    print("Evaluation steps:")
    for step in explanation.evaluation_steps:
        print(f"  {step}")
    print()
    
    if explanation.winning_rule:
        print(f"Winning rule: {explanation.winning_rule.rule.pattern}")
        print(f"  Type: {explanation.winning_rule.match_type}")
        print(f"  Priority: {explanation.winning_rule.rule.priority}")
    print()
    
    if explanation.warnings:
        print("Warnings:")
        for warning in explanation.warnings:
            print(f"  - {warning}")
        print()


def demo_statistics():
    """Demonstrate precedence resolver statistics."""
    print("=" * 80)
    print("DEMO 7: Precedence Resolver Statistics")
    print("=" * 80)
    print()
    
    # Create resolver
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.MOST_SPECIFIC_WINS,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    resolver = PrecedenceResolver(config)
    
    # Perform several resolutions
    test_paths = [
        Path("/home/user/documents/report.txt"),
        Path("/home/user/temp/data.txt"),
        Path("/home/user/logs/app.log"),
        Path("/home/user/backup.tmp"),
        Path("/home/user/documents/private/secret.txt")
    ]
    
    for path in test_paths:
        include_rule = RuleMatch(
            rule=PatternRule(pattern="/home/user/*", syntax=PatternSyntax.GLOB),
            path=path,
            match_type="include"
        )
        
        exclude_rule = RuleMatch(
            rule=PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB),
            path=path,
            match_type="exclude"
        )
        
        resolver.resolve_selection_conflicts(path, [include_rule, exclude_rule])
    
    # Get statistics
    stats = resolver.get_statistics()
    
    print("Precedence Resolver Statistics:")
    print(f"  Total resolutions: {stats['total_resolutions']}")
    print(f"  Conflicts detected: {stats['conflicts_detected']}")
    print(f"  Conflict ratio: {stats['conflict_ratio']:.1%}")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Cache hit ratio: {stats['cache_hit_ratio']:.1%}")
    print(f"  Cache size: {stats['cache_size']}")
    print(f"  Conflict reports: {stats['conflict_reports']}")
    print()
    
    print("Strategy usage:")
    for strategy, count in stats['strategy_usage'].items():
        if count > 0:
            print(f"  {strategy.value}: {count}")
    print()


def main():
    """Run all demonstrations."""
    print()
    print("PRECEDENCE RESOLVER AND DEBUGGER DEMONSTRATIONS")
    print()
    
    demo_basic_precedence()
    demo_specificity_resolution()
    demo_layered_evaluation()
    demo_debugger()
    demo_selection_report()
    demo_precedence_explanation()
    demo_statistics()
    
    print("=" * 80)
    print("All demonstrations completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
