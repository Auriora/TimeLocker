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
from datetime import datetime

from TimeLocker.selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent,
    SelectionConfig,
    PrecedenceConfig,
    PrecedenceStrategy,
    ConflictResolution,
    SelectionTemplate,
    RuleMatch,
    SelectionDecision,
    ValidationError,
    ValidationWarning,
    ValidationResult
)
from TimeLocker.file_selections import FileSelection, SelectionType


@pytest.mark.backup
@pytest.mark.unit
def test_pattern_rule_creation():
    """Test creating a PatternRule"""
    rule = PatternRule(
        pattern="*.txt",
        syntax=PatternSyntax.GLOB,
        case_sensitive=False,
        applies_to=PathComponent.FILENAME,
        priority=100
    )
    
    assert rule.pattern == "*.txt"
    assert rule.syntax == PatternSyntax.GLOB
    assert rule.case_sensitive is False
    assert rule.applies_to == PathComponent.FILENAME
    assert rule.priority == 100


@pytest.mark.backup
@pytest.mark.unit
def test_pattern_rule_validation():
    """Test PatternRule validation"""
    # Empty pattern should raise error
    with pytest.raises(ValueError, match="Pattern cannot be empty"):
        PatternRule(pattern="", syntax=PatternSyntax.GLOB)
    
    # Negative priority should raise error
    with pytest.raises(ValueError, match="Priority must be non-negative"):
        PatternRule(pattern="*.txt", priority=-1)


@pytest.mark.backup
@pytest.mark.unit
def test_precedence_config_creation():
    """Test creating a PrecedenceConfig"""
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
        specificity_weight=0.8,
        explicit_override_weight=0.9,
        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
    )
    
    assert config.default_strategy == PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE
    assert config.specificity_weight == 0.8
    assert config.explicit_override_weight == 0.9
    assert config.conflict_resolution == ConflictResolution.WARN_ON_CONFLICT


@pytest.mark.backup
@pytest.mark.unit
def test_precedence_config_validation():
    """Test PrecedenceConfig validation"""
    # Invalid specificity_weight
    with pytest.raises(ValueError, match="specificity_weight must be between 0.0 and 1.0"):
        PrecedenceConfig(specificity_weight=1.5)
    
    # Invalid explicit_override_weight
    with pytest.raises(ValueError, match="explicit_override_weight must be between 0.0 and 1.0"):
        PrecedenceConfig(explicit_override_weight=-0.1)


@pytest.mark.backup
@pytest.mark.unit
def test_selection_config_creation():
    """Test creating a SelectionConfig"""
    config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        exclude_paths=[Path("/home/user/documents/temp")],
        include_patterns=[
            PatternRule("*.txt", PatternSyntax.GLOB),
            PatternRule("*.pdf", PatternSyntax.GLOB)
        ],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB)
        ],
        pattern_groups=["office_documents"],
        case_sensitive=False
    )
    
    assert len(config.include_paths) == 1
    assert len(config.exclude_paths) == 1
    assert len(config.include_patterns) == 2
    assert len(config.exclude_patterns) == 1
    assert "office_documents" in config.pattern_groups


@pytest.mark.backup
@pytest.mark.unit
def test_selection_config_path_conversion():
    """Test that SelectionConfig converts string paths to Path objects"""
    config = SelectionConfig(
        include_paths=["/home/user/documents", Path("/home/user/downloads")],
        exclude_paths=["/tmp"]
    )
    
    # All paths should be Path objects
    assert all(isinstance(p, Path) for p in config.include_paths)
    assert all(isinstance(p, Path) for p in config.exclude_paths)


@pytest.mark.backup
@pytest.mark.unit
def test_selection_template_creation():
    """Test creating a SelectionTemplate"""
    config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        include_patterns=[PatternRule("*.txt", PatternSyntax.GLOB)]
    )
    
    template = SelectionTemplate(
        id="template_001",
        name="Documents Backup",
        description="Backup all documents",
        selection_config=config,
        tags=["documents", "personal"]
    )
    
    assert template.id == "template_001"
    assert template.name == "Documents Backup"
    assert template.description == "Backup all documents"
    assert len(template.tags) == 2
    assert template.usage_count == 0
    assert template.is_system_template is False


@pytest.mark.backup
@pytest.mark.unit
def test_selection_template_validation():
    """Test SelectionTemplate validation"""
    config = SelectionConfig()
    
    # Empty ID should raise error
    with pytest.raises(ValueError, match="Template ID cannot be empty"):
        SelectionTemplate(id="", name="Test", description=None, selection_config=config)
    
    # Empty name should raise error
    with pytest.raises(ValueError, match="Template name cannot be empty"):
        SelectionTemplate(id="test_001", name="", description=None, selection_config=config)


@pytest.mark.backup
@pytest.mark.unit
def test_file_selection_with_config():
    """Test creating FileSelection from SelectionConfig"""
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
    
    selection = FileSelection(selection_config=config)
    
    # Check that paths were added
    assert Path("/home/user/documents") in selection.includes
    assert Path("/home/user/documents/temp") in selection.excludes
    
    # Check that pattern rules were added
    include_rules = selection.get_pattern_rules(SelectionType.INCLUDE)
    exclude_rules = selection.get_pattern_rules(SelectionType.EXCLUDE)
    
    assert len(include_rules) == 1
    assert len(exclude_rules) == 1
    assert include_rules[0].pattern == "*.txt"
    assert exclude_rules[0].pattern == "*.tmp"


@pytest.mark.backup
@pytest.mark.unit
def test_file_selection_add_pattern_rule():
    """Test adding PatternRule to FileSelection"""
    selection = FileSelection()
    
    rule = PatternRule("*.log", PatternSyntax.GLOB, priority=150)
    selection.add_pattern_rule(rule, SelectionType.EXCLUDE)
    
    exclude_rules = selection.get_pattern_rules(SelectionType.EXCLUDE)
    assert len(exclude_rules) == 1
    assert exclude_rules[0].pattern == "*.log"
    assert exclude_rules[0].priority == 150


@pytest.mark.backup
@pytest.mark.unit
def test_file_selection_remove_pattern_rule():
    """Test removing PatternRule from FileSelection"""
    selection = FileSelection()
    
    rule = PatternRule("*.log", PatternSyntax.GLOB)
    selection.add_pattern_rule(rule, SelectionType.EXCLUDE)
    
    # Verify it was added
    assert len(selection.get_pattern_rules(SelectionType.EXCLUDE)) == 1
    
    # Remove it
    selection.remove_pattern_rule(rule, SelectionType.EXCLUDE)
    
    # Verify it was removed
    assert len(selection.get_pattern_rules(SelectionType.EXCLUDE)) == 0


@pytest.mark.backup
@pytest.mark.unit
def test_file_selection_precedence_config():
    """Test setting and getting precedence config"""
    selection = FileSelection()
    
    config = PrecedenceConfig(
        default_strategy=PrecedenceStrategy.MOST_SPECIFIC_WINS,
        conflict_resolution=ConflictResolution.FAIL_ON_CONFLICT
    )
    
    selection.set_precedence_config(config)
    retrieved_config = selection.get_precedence_config()
    
    assert retrieved_config.default_strategy == PrecedenceStrategy.MOST_SPECIFIC_WINS
    assert retrieved_config.conflict_resolution == ConflictResolution.FAIL_ON_CONFLICT


@pytest.mark.backup
@pytest.mark.unit
def test_file_selection_to_selection_config():
    """Test converting FileSelection to SelectionConfig"""
    selection = FileSelection()
    selection.add_path("/home/user/documents", SelectionType.INCLUDE)
    selection.add_path("/tmp", SelectionType.EXCLUDE)
    selection.add_pattern_rule(PatternRule("*.txt", PatternSyntax.GLOB), SelectionType.INCLUDE)
    
    config = selection.to_selection_config()
    
    assert len(config.include_paths) == 1
    assert len(config.exclude_paths) == 1
    assert len(config.include_patterns) == 1
    assert Path("/home/user/documents") in config.include_paths
    assert Path("/tmp") in config.exclude_paths


@pytest.mark.backup
@pytest.mark.unit
def test_file_selection_from_selection_config():
    """Test creating FileSelection from SelectionConfig"""
    config = SelectionConfig(
        include_paths=[Path("/home/user/documents")],
        exclude_paths=[Path("/tmp")],
        include_patterns=[PatternRule("*.txt", PatternSyntax.GLOB)]
    )
    
    selection = FileSelection.from_selection_config(config)
    
    assert Path("/home/user/documents") in selection.includes
    assert Path("/tmp") in selection.excludes
    assert len(selection.get_pattern_rules(SelectionType.INCLUDE)) == 1


@pytest.mark.backup
@pytest.mark.unit
def test_file_selection_supported_syntaxes():
    """Test checking supported pattern syntaxes"""
    selection = FileSelection()
    
    assert selection.supports_pattern_syntax(PatternSyntax.GLOB)
    assert selection.supports_pattern_syntax(PatternSyntax.LITERAL)
    
    supported = selection.get_supported_pattern_syntaxes()
    assert PatternSyntax.GLOB in supported
    assert PatternSyntax.LITERAL in supported


@pytest.mark.backup
@pytest.mark.unit
def test_rule_match_validation():
    """Test RuleMatch validation"""
    rule = PatternRule("*.txt", PatternSyntax.GLOB)
    path = Path("/home/user/test.txt")
    
    # Valid match
    match = RuleMatch(rule=rule, path=path, match_type="include", confidence=0.9)
    assert match.confidence == 0.9
    
    # Invalid match_type
    with pytest.raises(ValueError, match="match_type must be 'include' or 'exclude'"):
        RuleMatch(rule=rule, path=path, match_type="invalid")
    
    # Invalid confidence
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        RuleMatch(rule=rule, path=path, match_type="include", confidence=1.5)


@pytest.mark.backup
@pytest.mark.unit
def test_selection_decision_validation():
    """Test SelectionDecision validation"""
    rule = PatternRule("*.txt", PatternSyntax.GLOB)
    path = Path("/home/user/test.txt")
    match = RuleMatch(rule=rule, path=path, match_type="include")
    
    # Valid decision
    decision = SelectionDecision(
        include=True,
        confidence=0.95,
        applied_rules=[match],
        precedence_explanation="Include pattern matched"
    )
    assert decision.include is True
    assert decision.confidence == 0.95
    
    # Invalid confidence
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        SelectionDecision(
            include=True,
            confidence=2.0,
            applied_rules=[],
            precedence_explanation=""
        )


@pytest.mark.backup
@pytest.mark.unit
def test_validation_warning_severity():
    """Test ValidationWarning severity validation"""
    # Valid severities
    for severity in ["low", "medium", "high"]:
        warning = ValidationWarning(
            warning_type="test",
            message="Test warning",
            severity=severity
        )
        assert warning.severity == severity
    
    # Invalid severity
    with pytest.raises(ValueError, match="severity must be 'low', 'medium', or 'high'"):
        ValidationWarning(
            warning_type="test",
            message="Test warning",
            severity="critical"
        )
