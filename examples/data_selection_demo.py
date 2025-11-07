#!/usr/bin/env python3
"""
Demo script showing the new data selection models and enhanced FileSelection class.

This demonstrates the core functionality implemented in task 1 of the data-selection spec.
"""

from pathlib import Path
from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent,
    SelectionConfig,
    PrecedenceConfig,
    PrecedenceStrategy,
    ConflictResolution,
    SelectionTemplate
)


def demo_pattern_rules():
    """Demonstrate creating and using PatternRule objects"""
    print("=" * 60)
    print("Demo 1: Pattern Rules")
    print("=" * 60)
    
    # Create pattern rules with different syntaxes
    glob_rule = PatternRule(
        pattern="*.txt",
        syntax=PatternSyntax.GLOB,
        case_sensitive=False,
        applies_to=PathComponent.FILENAME,
        priority=100
    )
    
    literal_rule = PatternRule(
        pattern="README.md",
        syntax=PatternSyntax.LITERAL,
        case_sensitive=True,
        applies_to=PathComponent.FILENAME,
        priority=200
    )
    
    print(f"GLOB Rule: {glob_rule.pattern} (priority: {glob_rule.priority})")
    print(f"LITERAL Rule: {literal_rule.pattern} (priority: {literal_rule.priority})")
    print()


def demo_precedence_config():
    """Demonstrate precedence configuration"""
    print("=" * 60)
    print("Demo 2: Precedence Configuration")
    print("=" * 60)
    
    # Create precedence config with custom settings
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.MOST_SPECIFIC_WINS,
        specificity_weight=0.8,
        explicit_override_weight=0.9,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    
    print(f"Strategy: {config.default_strategy.value}")
    print(f"Specificity Weight: {config.specificity_weight}")
    print(f"Conflict Resolution: {config.conflict_resolution.value}")
    print()


def demo_selection_config():
    """Demonstrate creating a complete selection configuration"""
    print("=" * 60)
    print("Demo 3: Selection Configuration")
    print("=" * 60)
    
    # Create a complete selection config
    config = SelectionConfig(
        include_paths=[
            Path("/home/user/documents"),
            Path("/home/user/projects")
        ],
        exclude_paths=[
            Path("/home/user/documents/temp")
        ],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB, priority=100),
            PatternRule("*.pdf", PatternSyntax.GLOB, priority=100),
            PatternRule("*.md", PatternSyntax.GLOB, priority=100)
        ],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, priority=200),
            PatternRule("*.log", PatternSyntax.GLOB, priority=200)
        ],
        pattern_groups=["office_documents"],
        precedence_config=PrecedenceConfig(
            default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE
        ),
        case_sensitive=False
    )
    
    print(f"Include Paths: {len(config.include_paths)}")
    print(f"Exclude Paths: {len(config.exclude_paths)}")
    print(f"Include Patterns: {len(config.include_patterns)}")
    print(f"Exclude Patterns: {len(config.exclude_patterns)}")
    print(f"Pattern Groups: {config.pattern_groups}")
    print()


def demo_selection_template():
    """Demonstrate creating a selection template"""
    print("=" * 60)
    print("Demo 4: Selection Template")
    print("=" * 60)
    
    # Create a selection config
    config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB),
            PatternRule("*.pdf", PatternSyntax.GLOB)
        ],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB)
        ]
    )
    
    # Create a template
    template = SelectionTemplate(
        id="template_documents",
        name="Documents Backup",
        description="Backup all document files excluding temporary files",
        selection_config=config,
        tags=["documents", "personal", "backup"]
    )
    
    print(f"Template ID: {template.id}")
    print(f"Template Name: {template.name}")
    print(f"Description: {template.description}")
    print(f"Tags: {', '.join(template.tags)}")
    print(f"Usage Count: {template.usage_count}")
    print()


def demo_file_selection_integration():
    """Demonstrate FileSelection integration with new models"""
    print("=" * 60)
    print("Demo 5: FileSelection Integration")
    print("=" * 60)
    
    # Create a selection config
    config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        exclude_paths=[Path("/home/user/documents/temp")],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB, priority=100)
        ],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, priority=200)
        ]
    )
    
    # Create FileSelection from config
    selection = FileSelection.from_selection_config(config)
    
    print("FileSelection created from SelectionConfig:")
    print(f"  Include Paths: {len(selection.includes)}")
    print(f"  Exclude Paths: {len(selection.excludes)}")
    print(f"  Include Pattern Rules: {len(selection.get_pattern_rules(SelectionType.INCLUDE))}")
    print(f"  Exclude Pattern Rules: {len(selection.get_pattern_rules(SelectionType.EXCLUDE))}")
    
    # Add a pattern rule directly
    new_rule = PatternRule("*.log", PatternSyntax.GLOB, priority=150)
    selection.add_pattern_rule(new_rule, SelectionType.EXCLUDE)
    
    print(f"\nAfter adding *.log exclude rule:")
    print(f"  Exclude Pattern Rules: {len(selection.get_pattern_rules(SelectionType.EXCLUDE))}")
    
    # Convert back to SelectionConfig
    new_config = selection.to_selection_config()
    print(f"\nConverted back to SelectionConfig:")
    print(f"  Include Patterns: {len(new_config.include_patterns)}")
    print(f"  Exclude Patterns: {len(new_config.exclude_patterns)}")
    print()


def demo_backward_compatibility():
    """Demonstrate backward compatibility with existing API"""
    print("=" * 60)
    print("Demo 6: Backward Compatibility")
    print("=" * 60)
    
    # Use FileSelection the old way (without SelectionConfig)
    selection = FileSelection()
    
    # Add paths using the existing API
    selection.add_path("/home/user/documents", SelectionType.INCLUDE)
    selection.add_path("/tmp", SelectionType.EXCLUDE)
    
    # Add patterns using the existing API
    selection.add_pattern("*.txt", SelectionType.INCLUDE)
    selection.add_pattern("*.tmp", SelectionType.EXCLUDE)
    
    # Add pattern group using the existing API
    selection.add_pattern_group("office_documents", SelectionType.INCLUDE)
    
    print("FileSelection created using legacy API:")
    print(f"  Include Paths: {len(selection.includes)}")
    print(f"  Exclude Paths: {len(selection.excludes)}")
    print(f"  Include Patterns: {len(selection.include_patterns)}")
    print(f"  Exclude Patterns: {len(selection.exclude_patterns)}")
    
    # Can still convert to new SelectionConfig
    config = selection.to_selection_config()
    print(f"\nCan convert to SelectionConfig:")
    print(f"  Include Paths: {len(config.include_paths)}")
    print(f"  Pattern Groups: {config.pattern_groups}")
    print()


def main():
    """Run all demos"""
    print("\n")
    print("*" * 60)
    print("* Data Selection Models Demo")
    print("* Task 1: Enhanced Core Data Models and Interfaces")
    print("*" * 60)
    print()
    
    demo_pattern_rules()
    demo_precedence_config()
    demo_selection_config()
    demo_selection_template()
    demo_file_selection_integration()
    demo_backward_compatibility()
    
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
