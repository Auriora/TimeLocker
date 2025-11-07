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

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class PatternSyntax(Enum):
    """Pattern matching syntax types"""
    GLOB = "glob"
    REGEX = "regex"
    LITERAL = "literal"


class PathComponent(Enum):
    """Path component to apply pattern matching to"""
    FULL_PATH = "full_path"
    FILENAME = "filename"
    DIRECTORY = "directory"


class PrecedenceStrategy(Enum):
    """Strategy for resolving precedence conflicts"""
    INCLUDE_OVERRIDES_EXCLUDE = "include_first"
    EXCLUDE_OVERRIDES_INCLUDE = "exclude_first"
    MOST_SPECIFIC_WINS = "specificity"
    EXPLICIT_PRIORITY = "priority"
    LAYERED_EVALUATION = "layered"


class ConflictResolution(Enum):
    """How to handle precedence conflicts"""
    FAIL_ON_CONFLICT = "fail"
    WARN_ON_CONFLICT = "warn"
    SILENT_RESOLUTION = "silent"


@dataclass
class PatternRule:
    """
    Represents a single pattern matching rule for file selection.
    
    Attributes:
        pattern: The pattern string (e.g., "*.txt", ".*\\.log$", "README.md")
        syntax: The pattern syntax type (GLOB, REGEX, or LITERAL)
        case_sensitive: Whether pattern matching is case-sensitive
        applies_to: Which path component to match against
        priority: Priority for rule evaluation (higher = evaluated first)
        metadata: Additional metadata for the rule
    """
    pattern: str
    syntax: PatternSyntax = PatternSyntax.GLOB
    case_sensitive: bool = False
    applies_to: PathComponent = PathComponent.FULL_PATH
    priority: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate pattern rule after initialization"""
        if not self.pattern:
            raise ValueError("Pattern cannot be empty")
        if self.priority < 0:
            raise ValueError("Priority must be non-negative")


@dataclass
class PrecedenceConfig:
    """
    Configuration for precedence rule evaluation.
    
    Attributes:
        default_strategy: Default strategy for resolving conflicts
        path_specific_rules: Path-specific precedence strategies
        specificity_weight: Weight for specificity in conflict resolution (0.0-1.0)
        explicit_override_weight: Weight for explicit priority values (0.0-1.0)
        pattern_type_priority: Priority mapping for different pattern syntaxes
        conflict_resolution: How to handle unresolvable conflicts
    """
    default_strategy: PrecedenceStrategy = PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE
    path_specific_rules: Dict[str, PrecedenceStrategy] = field(default_factory=dict)
    specificity_weight: float = 1.0
    explicit_override_weight: float = 1.0
    pattern_type_priority: Dict[PatternSyntax, int] = field(default_factory=lambda: {
        PatternSyntax.LITERAL: 300,
        PatternSyntax.GLOB: 200,
        PatternSyntax.REGEX: 100
    })
    conflict_resolution: ConflictResolution = ConflictResolution.WARN_ON_CONFLICT
    
    def __post_init__(self):
        """Validate precedence configuration"""
        if not 0.0 <= self.specificity_weight <= 1.0:
            raise ValueError("specificity_weight must be between 0.0 and 1.0")
        if not 0.0 <= self.explicit_override_weight <= 1.0:
            raise ValueError("explicit_override_weight must be between 0.0 and 1.0")


@dataclass
class SelectionConfig:
    """
    Complete configuration for data selection.
    
    Attributes:
        include_paths: List of paths to explicitly include
        exclude_paths: List of paths to explicitly exclude
        include_patterns: List of pattern rules for inclusion
        exclude_patterns: List of pattern rules for exclusion
        pattern_groups: List of pattern group names to apply
        precedence_config: Configuration for precedence resolution
        case_sensitive: Default case sensitivity for patterns
        performance_hints: Hints for performance optimization
    """
    include_paths: List[Path] = field(default_factory=list)
    exclude_paths: List[Path] = field(default_factory=list)
    include_patterns: List[PatternRule] = field(default_factory=list)
    exclude_patterns: List[PatternRule] = field(default_factory=list)
    pattern_groups: List[str] = field(default_factory=list)
    precedence_config: PrecedenceConfig = field(default_factory=PrecedenceConfig)
    case_sensitive: bool = False
    performance_hints: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate selection configuration"""
        # Convert string paths to Path objects
        self.include_paths = [Path(p) if isinstance(p, str) else p for p in self.include_paths]
        self.exclude_paths = [Path(p) if isinstance(p, str) else p for p in self.exclude_paths]


@dataclass
class SelectionTemplate:
    """
    A reusable selection configuration template.
    
    Attributes:
        id: Unique identifier for the template
        name: Human-readable name
        description: Description of the template's purpose
        selection_config: The selection configuration
        created_at: When the template was created
        updated_at: When the template was last updated
        created_by: User who created the template
        tags: Tags for categorization
        usage_count: Number of times template has been used
        is_system_template: Whether this is a system-provided template
        metadata: Additional metadata
    """
    id: str
    name: str
    description: Optional[str]
    selection_config: SelectionConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    is_system_template: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate template after initialization"""
        if not self.id:
            raise ValueError("Template ID cannot be empty")
        if not self.name:
            raise ValueError("Template name cannot be empty")


@dataclass
class RuleMatch:
    """
    Represents a matched rule during selection evaluation.
    
    Attributes:
        rule: The pattern rule that matched
        path: The path that was matched
        match_type: Type of match (include or exclude)
        confidence: Confidence score for the match (0.0-1.0)
        metadata: Additional match metadata
    """
    rule: PatternRule
    path: Path
    match_type: str  # "include" or "exclude"
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate rule match"""
        if self.match_type not in ("include", "exclude"):
            raise ValueError("match_type must be 'include' or 'exclude'")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class SelectionDecision:
    """
    Decision about whether to include a path.
    
    Attributes:
        include: Whether to include the path
        confidence: Confidence in the decision (0.0-1.0)
        applied_rules: Rules that were applied to make the decision
        precedence_explanation: Explanation of precedence resolution
        warnings: Any warnings generated during evaluation
    """
    include: bool
    confidence: float
    applied_rules: List[RuleMatch]
    precedence_explanation: str
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate selection decision"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class ValidationError:
    """
    Represents a validation error.
    
    Attributes:
        error_type: Type of validation error
        message: Error message
        context: Additional context about the error
        suggested_fix: Suggested fix for the error
    """
    error_type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: Optional[str] = None


@dataclass
class ValidationWarning:
    """
    Represents a validation warning.
    
    Attributes:
        warning_type: Type of validation warning
        message: Warning message
        context: Additional context about the warning
        severity: Severity level (low, medium, high)
    """
    warning_type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"
    
    def __post_init__(self):
        """Validate warning"""
        if self.severity not in ("low", "medium", "high"):
            raise ValueError("severity must be 'low', 'medium', or 'high'")


@dataclass
class PerformanceEstimate:
    """
    Performance estimation for selection operations.
    
    Attributes:
        estimated_files_per_second: Estimated processing rate
        estimated_memory_mb: Estimated memory usage in MB
        estimated_duration_seconds: Estimated duration in seconds
        optimization_opportunities: List of optimization suggestions
        bottlenecks: Identified performance bottlenecks
    """
    estimated_files_per_second: float
    estimated_memory_mb: float
    estimated_duration_seconds: float
    optimization_opportunities: List[str] = field(default_factory=list)
    bottlenecks: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """
    Result of selection validation.
    
    Attributes:
        is_valid: Whether the selection is valid
        errors: List of validation errors
        warnings: List of validation warnings
        suggestions: List of improvement suggestions
        estimated_performance: Performance estimate
    """
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    estimated_performance: Optional[PerformanceEstimate] = None


@dataclass
class EvaluationStats:
    """
    Statistics from selection evaluation.
    
    Attributes:
        files_evaluated: Number of files evaluated
        files_included: Number of files included
        files_excluded: Number of files excluded
        evaluation_time_seconds: Time taken for evaluation
        cache_hits: Number of cache hits
        cache_misses: Number of cache misses
    """
    files_evaluated: int = 0
    files_included: int = 0
    files_excluded: int = 0
    evaluation_time_seconds: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for selection operations.
    
    Attributes:
        files_per_second: Processing rate
        memory_usage_mb: Memory usage in MB
        cache_hit_ratio: Cache hit ratio (0.0-1.0)
        pattern_compilation_time_ms: Time to compile patterns
        evaluation_time_ms: Time for evaluation
    """
    files_per_second: float = 0.0
    memory_usage_mb: float = 0.0
    cache_hit_ratio: float = 0.0
    pattern_compilation_time_ms: float = 0.0
    evaluation_time_ms: float = 0.0


@dataclass
class SelectionResult:
    """
    Result of selection evaluation.
    
    Attributes:
        included_paths: List of included paths
        excluded_paths: List of excluded paths
        evaluation_stats: Statistics from evaluation
        warnings: Any warnings generated
        performance_metrics: Performance metrics
    """
    included_paths: List[Path] = field(default_factory=list)
    excluded_paths: List[Path] = field(default_factory=list)
    evaluation_stats: EvaluationStats = field(default_factory=EvaluationStats)
    warnings: List[str] = field(default_factory=list)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)


@dataclass
class SizeEstimate:
    """
    Size estimation for selected files.
    
    Attributes:
        total_size_bytes: Total size in bytes
        file_count: Number of files
        directory_count: Number of directories
        estimation_accuracy: Accuracy of estimation (0.0-1.0)
        inaccessible_paths: Paths that couldn't be accessed
        estimation_time_seconds: Time taken for estimation
    """
    total_size_bytes: int = 0
    file_count: int = 0
    directory_count: int = 0
    estimation_accuracy: float = 1.0
    inaccessible_paths: List[Path] = field(default_factory=list)
    estimation_time_seconds: float = 0.0


@dataclass
class PreviewResult:
    """
    Preview of selection results.
    
    Attributes:
        sample_included_files: Sample of included files
        sample_excluded_files: Sample of excluded files
        total_estimated_files: Total estimated file count
        preview_generation_time: Time to generate preview
        truncated: Whether results were truncated
        selection_summary: Summary of selection
    """
    sample_included_files: List[Path] = field(default_factory=list)
    sample_excluded_files: List[Path] = field(default_factory=list)
    total_estimated_files: int = 0
    preview_generation_time: float = 0.0
    truncated: bool = False
    selection_summary: Optional[str] = None


class PatternCategory(Enum):
    """Categories for pattern groups"""
    DOCUMENT_TYPES = "documents"
    MEDIA_FILES = "media"
    TEMPORARY_FILES = "temporary"
    SOURCE_CODE = "source"
    SYSTEM_FILES = "system"
    APPLICATION_DATA = "application"
    CUSTOM = "custom"


@dataclass
class PatternGroup:
    """
    A named collection of related file patterns.
    
    Attributes:
        id: Unique identifier for the pattern group
        name: Human-readable name
        description: Description of the pattern group's purpose
        patterns: List of pattern rules in the group
        category: Category for the pattern group
        is_system_group: Whether this is a system-provided group
        created_at: When the group was created
        usage_count: Number of times group has been used
        metadata: Additional metadata
    """
    id: str
    name: str
    description: str
    patterns: List[PatternRule]
    category: PatternCategory = PatternCategory.CUSTOM
    is_system_group: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    usage_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate pattern group after initialization"""
        if not self.id:
            raise ValueError("Pattern group ID cannot be empty")
        if not self.name:
            raise ValueError("Pattern group name cannot be empty")
        if not self.patterns:
            raise ValueError("Pattern group must contain at least one pattern")


class ApplicationCategory(Enum):
    """Categories for application presets"""
    DATABASE = "database"
    WEB_SERVER = "web_server"
    DEVELOPMENT = "development"
    OFFICE_SUITE = "office"
    MEDIA_PRODUCTION = "media"
    SYSTEM_ADMIN = "system"
    CUSTOM = "custom"


@dataclass
class ApplicationPreset:
    """
    Pre-configured selection for common applications.
    
    Attributes:
        id: Unique identifier for the preset
        name: Human-readable name
        description: Description of the preset's purpose
        application_name: Name of the application
        selection_template: The selection template for this preset
        category: Category for the preset
        platform_specific: Platform-specific configurations (OS -> SelectionConfig)
        version_compatibility: List of compatible application versions
        installation_paths: Common installation paths for the application
        is_system_preset: Whether this is a system-provided preset
        metadata: Additional metadata
    """
    id: str
    name: str
    description: str
    application_name: str
    selection_template: SelectionTemplate
    category: ApplicationCategory = ApplicationCategory.CUSTOM
    platform_specific: Dict[str, SelectionConfig] = field(default_factory=dict)
    version_compatibility: List[str] = field(default_factory=list)
    installation_paths: List[str] = field(default_factory=list)
    is_system_preset: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate application preset after initialization"""
        if not self.id:
            raise ValueError("Application preset ID cannot be empty")
        if not self.name:
            raise ValueError("Application preset name cannot be empty")
        if not self.application_name:
            raise ValueError("Application name cannot be empty")
