# Design Document

## Overview

The Data Selection and Selection Management design implements a flexible, high-performance system for defining and managing file selection criteria for backup operations. The design centers around a Selection Manager that coordinates between pattern engines, template storage, and validation services while supporting complex hierarchical selection rules with configurable precedence. The architecture emphasizes performance optimization for large file systems and provides comprehensive testing and debugging capabilities.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Data Selection Management                 │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │   Selection     │ │   Template      │ │   Validation    │ │
│ │    Manager      │ │    Manager      │ │    Service      │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Pattern       │  │   Precedence    │  │   Performance   │ │
│  │   Engine        │  │   Resolver      │  │   Optimizer     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Pattern       │  │   Application   │  │   Testing &     │ │
│  │   Groups        │  │   Presets       │  │   Debugging     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Relationships

- **Selection Manager**: Central orchestrator for all data selection operations
- **Template Manager**: Persistent storage and management of reusable selection configurations
- **Validation Service**: Selection rule validation, conflict detection, and preview functionality
- **Pattern Engine**: High-performance pattern matching with compiled regex and glob support
- **Precedence Resolver**: Configurable rule evaluation for complex hierarchical selections
- **Performance Optimizer**: Caching, streaming, and optimization for large file systems
- **Pattern Groups**: Predefined and custom pattern collections for common file types
- **Application Presets**: Pre-configured selections for common applications and use cases
- **Testing & Debugging**: Tools for troubleshooting and validating selection configurations

## Components and Interfaces

### Selection Manager

**Purpose**: Central coordinator for data selection operations and rule evaluation

**Interface**:
```python
class SelectionManager:
    async def create_selection(self, config: SelectionConfig) -> DataSelection
    async def evaluate_selection(self, selection: DataSelection, base_paths: List[Path]) -> SelectionResult
    async def estimate_selection_size(self, selection: DataSelection, base_paths: List[Path]) -> SizeEstimate
    async def preview_selection(self, selection: DataSelection, base_paths: List[Path], limit: int = 1000) -> PreviewResult
    async def validate_selection(self, selection: DataSelection) -> ValidationResult
    async def test_pattern_match(self, pattern: str, test_paths: List[str]) -> MatchResult
    def get_effective_precedence_rules(self, selection: DataSelection) -> PrecedenceConfig
    async def optimize_selection_for_performance(self, selection: DataSelection) -> OptimizedSelection
```

**Key Responsibilities**:
- Selection rule compilation and optimization
- File system traversal with selection rule application
- Performance monitoring and optimization
- Integration with template and pattern management
- Precedence rule evaluation and conflict resolution
- Size estimation and preview generation
- Testing and debugging support

### Template Manager

**Purpose**: Persistent storage and management of reusable selection configurations

**Interface**:
```python
class SelectionTemplateManager:
    async def create_template(self, template: SelectionTemplate) -> str
    async def get_template(self, template_id: str) -> SelectionTemplate
    async def list_templates(self, filters: Optional[Dict] = None) -> List[SelectionTemplate]
    async def update_template(self, template_id: str, updates: Dict) -> SelectionTemplate
    async def delete_template(self, template_id: str) -> bool
    async def duplicate_template(self, template_id: str, new_name: str) -> SelectionTemplate
    async def export_templates(self, template_ids: List[str], format: str = "json") -> str
    async def import_templates(self, data: str, format: str = "json", merge_strategy: str = "skip") -> ImportResult
    async def get_template_usage(self, template_id: str) -> UsageInfo
```

**Storage Schema**:
```python
@dataclass
class SelectionTemplate:
    id: str
    name: str
    description: Optional[str]
    selection_config: SelectionConfig
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    tags: List[str]
    usage_count: int
    is_system_template: bool
    metadata: Dict[str, Any]

@dataclass
class SelectionConfig:
    include_paths: List[Path]
    exclude_paths: List[Path]
    include_patterns: List[PatternRule]
    exclude_patterns: List[PatternRule]
    pattern_groups: List[str]
    precedence_config: PrecedenceConfig
    case_sensitive: bool
    performance_hints: Dict[str, Any]
```

### Pattern Engine

**Purpose**: High-performance pattern matching with multiple syntax support

**Interface**:
```python
class PatternEngine:
    def compile_patterns(self, patterns: List[PatternRule]) -> CompiledPatternSet
    def match_path(self, path: Path, compiled_patterns: CompiledPatternSet) -> MatchResult
    def batch_match_paths(self, paths: List[Path], compiled_patterns: CompiledPatternSet) -> List[MatchResult]
    def get_pattern_statistics(self, compiled_patterns: CompiledPatternSet) -> PatternStats
    def optimize_pattern_order(self, patterns: List[PatternRule]) -> List[PatternRule]
    def validate_pattern_syntax(self, pattern: str, syntax_type: PatternSyntax) -> ValidationResult

@dataclass
class PatternRule:
    pattern: str
    syntax: PatternSyntax  # GLOB, REGEX, LITERAL
    case_sensitive: bool
    applies_to: PathComponent  # FULL_PATH, FILENAME, DIRECTORY
    priority: int
    metadata: Dict[str, Any]

class PatternSyntax(Enum):
    GLOB = "glob"
    REGEX = "regex"
    LITERAL = "literal"

class PathComponent(Enum):
    FULL_PATH = "full_path"
    FILENAME = "filename"
    DIRECTORY = "directory"
```

**Performance Optimizations**:
- Compiled pattern caching with LRU eviction
- Pattern ordering optimization for early termination
- Batch processing for multiple path evaluation
- Memory-efficient streaming for large file sets
- Pattern complexity analysis and warnings

### Precedence Resolver

**Purpose**: Configurable rule evaluation for complex hierarchical selections

**Interface**:
```python
class PrecedenceResolver:
    def resolve_selection_conflicts(self, path: Path, matches: List[RuleMatch]) -> SelectionDecision
    def configure_precedence_rules(self, config: PrecedenceConfig) -> bool
    def get_precedence_explanation(self, path: Path, selection: DataSelection) -> PrecedenceExplanation
    def validate_precedence_configuration(self, config: PrecedenceConfig) -> ValidationResult

@dataclass
class PrecedenceConfig:
    default_strategy: PrecedenceStrategy
    path_specific_rules: Dict[str, PrecedenceStrategy]
    specificity_weight: float
    explicit_override_weight: float
    pattern_type_priority: Dict[PatternSyntax, int]
    conflict_resolution: ConflictResolution

class PrecedenceStrategy(Enum):
    INCLUDE_OVERRIDES_EXCLUDE = "include_first"
    EXCLUDE_OVERRIDES_INCLUDE = "exclude_first"
    MOST_SPECIFIC_WINS = "specificity"
    EXPLICIT_PRIORITY = "priority"
    LAYERED_EVALUATION = "layered"

class ConflictResolution(Enum):
    FAIL_ON_CONFLICT = "fail"
    WARN_ON_CONFLICT = "warn"
    SILENT_RESOLUTION = "silent"

@dataclass
class SelectionDecision:
    include: bool
    confidence: float
    applied_rules: List[RuleMatch]
    precedence_explanation: str
    warnings: List[str]
```

**Precedence Evaluation Examples**:
```python
# Example 1: Layered evaluation (include home, exclude temp, re-include specific files)
precedence_config = PrecedenceConfig(
    default_strategy=PrecedenceStrategy.LAYERED_EVALUATION,
    conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
)

# Evaluation order:
# 1. Include: /home/user (base inclusion)
# 2. Exclude: /home/user/temp/* (exclude temp directory)
# 3. Include: /home/user/temp/important.txt (re-include specific file)
# Result: important.txt is included despite being in excluded temp directory

# Example 2: Specificity-based resolution
precedence_config = PrecedenceConfig(
    default_strategy=PrecedenceStrategy.MOST_SPECIFIC_WINS,
    specificity_weight=1.0
)

# More specific paths/patterns override less specific ones
# /home/user/documents/*.pdf (exclude) overrides /home/user/documents (include)
```

### Validation Service

**Purpose**: Selection rule validation, conflict detection, and preview functionality

**Interface**:
```python
class SelectionValidationService:
    async def validate_selection_config(self, config: SelectionConfig) -> ValidationResult
    async def detect_selection_conflicts(self, selection: DataSelection) -> List[ConflictReport]
    async def generate_selection_preview(self, selection: DataSelection, base_paths: List[Path], 
                                       options: PreviewOptions) -> PreviewResult
    async def validate_pattern_syntax(self, patterns: List[PatternRule]) -> List[PatternValidationResult]
    async def check_path_accessibility(self, paths: List[Path]) -> List[AccessibilityResult]
    async def estimate_performance_impact(self, selection: DataSelection) -> PerformanceEstimate

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    suggestions: List[str]
    estimated_performance: PerformanceEstimate

@dataclass
class ConflictReport:
    conflict_type: ConflictType
    affected_paths: List[Path]
    conflicting_rules: List[RuleMatch]
    suggested_resolution: str
    severity: ConflictSeverity

class ConflictType(Enum):
    INCLUDE_EXCLUDE_OVERLAP = "include_exclude"
    PATTERN_CONTRADICTION = "pattern_conflict"
    PATH_INACCESSIBLE = "access_denied"
    CIRCULAR_DEPENDENCY = "circular"
    PERFORMANCE_CONCERN = "performance"
```

### Performance Optimizer

**Purpose**: Optimization strategies for large file system operations

**Interface**:
```python
class SelectionPerformanceOptimizer:
    async def optimize_selection_for_size(self, selection: DataSelection, 
                                        estimated_file_count: int) -> OptimizedSelection
    def create_streaming_evaluator(self, selection: DataSelection) -> StreamingEvaluator
    async def benchmark_selection_performance(self, selection: DataSelection, 
                                            test_paths: List[Path]) -> PerformanceBenchmark
    def get_optimization_recommendations(self, selection: DataSelection) -> List[OptimizationHint]

@dataclass
class OptimizedSelection:
    original_selection: DataSelection
    optimized_patterns: List[PatternRule]
    optimization_applied: List[str]
    estimated_performance_gain: float
    cache_strategy: CacheStrategy

class StreamingEvaluator:
    async def evaluate_path_stream(self, path_stream: AsyncIterator[Path]) -> AsyncIterator[SelectionResult]
    def get_evaluation_statistics(self) -> EvaluationStats
    async def cancel_evaluation(self) -> bool

@dataclass
class PerformanceBenchmark:
    files_per_second: float
    memory_usage_mb: float
    cache_hit_ratio: float
    optimization_opportunities: List[str]
    bottlenecks: List[str]
```

## Data Models

### Core Selection Models

```python
@dataclass
class DataSelection:
    config: SelectionConfig
    compiled_patterns: Optional[CompiledPatternSet]
    precedence_resolver: PrecedenceResolver
    performance_optimizer: Optional[SelectionPerformanceOptimizer]
    metadata: Dict[str, Any]
    created_at: datetime
    last_optimized: Optional[datetime]

@dataclass
class SelectionResult:
    included_paths: List[Path]
    excluded_paths: List[Path]
    evaluation_stats: EvaluationStats
    warnings: List[str]
    performance_metrics: PerformanceMetrics

@dataclass
class SizeEstimate:
    total_size_bytes: int
    file_count: int
    directory_count: int
    estimation_accuracy: float
    inaccessible_paths: List[Path]
    estimation_time_seconds: float

@dataclass
class PreviewResult:
    sample_included_files: List[Path]
    sample_excluded_files: List[Path]
    total_estimated_files: int
    preview_generation_time: float
    truncated: bool
    selection_summary: SelectionSummary
```

### Pattern Group Models

```python
@dataclass
class PatternGroup:
    id: str
    name: str
    description: str
    patterns: List[PatternRule]
    category: PatternCategory
    is_system_group: bool
    created_at: datetime
    usage_count: int
    metadata: Dict[str, Any]

class PatternCategory(Enum):
    DOCUMENT_TYPES = "documents"
    MEDIA_FILES = "media"
    TEMPORARY_FILES = "temporary"
    SOURCE_CODE = "source"
    SYSTEM_FILES = "system"
    APPLICATION_DATA = "application"
    CUSTOM = "custom"

# Predefined system pattern groups
SYSTEM_PATTERN_GROUPS = {
    "office_documents": PatternGroup(
        id="system_office_docs",
        name="Office Documents",
        description="Common office document formats",
        patterns=[
            PatternRule("*.doc", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.docx", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.xls", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.xlsx", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.ppt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.pptx", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.pdf", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.odt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.ods", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.odp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        category=PatternCategory.DOCUMENT_TYPES,
        is_system_group=True,
        created_at=datetime.utcnow(),
        usage_count=0,
        metadata={"version": "1.0", "maintainer": "system"}
    ),
    
    "temporary_files": PatternGroup(
        id="system_temp_files",
        name="Temporary Files",
        description="Temporary and cache files that can be safely excluded",
        patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.temp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("~*", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.bak", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.swp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.cache", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("__pycache__/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 100),
            PatternRule("*.pyc", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("node_modules/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 100),
            PatternRule(".DS_Store", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 100),
            PatternRule("Thumbs.db", PatternSyntax.LITERAL, False, PathComponent.FILENAME, 100),
        ],
        category=PatternCategory.TEMPORARY_FILES,
        is_system_group=True,
        created_at=datetime.utcnow(),
        usage_count=0,
        metadata={"version": "1.0", "maintainer": "system"}
    ),
    
    "media_files": PatternGroup(
        id="system_media_files",
        name="Media Files",
        description="Common image, audio, and video file formats",
        patterns=[
            # Images
            PatternRule("*.jpg", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.jpeg", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.png", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.gif", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.bmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.tiff", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.webp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            # Audio
            PatternRule("*.mp3", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.wav", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.flac", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.aac", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            # Video
            PatternRule("*.mp4", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.avi", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.mov", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.mkv", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.wmv", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        category=PatternCategory.MEDIA_FILES,
        is_system_group=True,
        created_at=datetime.utcnow(),
        usage_count=0,
        metadata={"version": "1.0", "maintainer": "system"}
    ),
    
    "source_code": PatternGroup(
        id="system_source_code",
        name="Source Code",
        description="Common programming language source files",
        patterns=[
            PatternRule("*.py", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("*.java", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("*.cpp", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("*.c", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("*.h", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("*.js", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("*.ts", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("*.html", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.css", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.sql", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.xml", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.json", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.yaml", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.yml", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        category=PatternCategory.SOURCE_CODE,
        is_system_group=True,
        created_at=datetime.utcnow(),
        usage_count=0,
        metadata={"version": "1.0", "maintainer": "system"}
    )
}
```

### Application Preset Models

```python
@dataclass
class ApplicationPreset:
    id: str
    name: str
    description: str
    application_name: str
    selection_template: SelectionTemplate
    category: ApplicationCategory
    platform_specific: Dict[str, SelectionConfig]  # OS-specific configurations
    version_compatibility: List[str]
    installation_paths: List[str]
    is_system_preset: bool
    metadata: Dict[str, Any]

class ApplicationCategory(Enum):
    DATABASE = "database"
    WEB_SERVER = "web_server"
    DEVELOPMENT = "development"
    OFFICE_SUITE = "office"
    MEDIA_PRODUCTION = "media"
    SYSTEM_ADMIN = "system"
    CUSTOM = "custom"

# Example application presets
APPLICATION_PRESETS = {
    "postgresql_data": ApplicationPreset(
        id="preset_postgresql",
        name="PostgreSQL Database",
        description="PostgreSQL data directory and configuration files",
        application_name="PostgreSQL",
        selection_template=SelectionTemplate(
            id="template_postgresql",
            name="PostgreSQL Backup",
            description="Complete PostgreSQL installation backup",
            selection_config=SelectionConfig(
                include_paths=[
                    Path("/var/lib/postgresql"),
                    Path("/etc/postgresql"),
                ],
                exclude_paths=[
                    Path("/var/lib/postgresql/*/main/pg_log"),
                ],
                include_patterns=[
                    PatternRule("*.conf", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.sql", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                exclude_patterns=[
                    PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("postmaster.pid", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 100),
                ],
                pattern_groups=["temporary_files"],
                precedence_config=PrecedenceConfig(
                    default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                    conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                ),
                case_sensitive=True,
                performance_hints={"skip_large_logs": True}
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["database", "postgresql", "system"],
            is_system_template=True,
            metadata={"preset_id": "preset_postgresql"}
        ),
        category=ApplicationCategory.DATABASE,
        platform_specific={
            "windows": SelectionConfig(
                include_paths=[Path("C:/Program Files/PostgreSQL")],
                exclude_paths=[],
                include_patterns=[],
                exclude_patterns=[],
                pattern_groups=["temporary_files"],
                precedence_config=PrecedenceConfig(
                    default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                    conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                ),
                case_sensitive=False,
                performance_hints={}
            )
        },
        version_compatibility=["9.x", "10.x", "11.x", "12.x", "13.x", "14.x", "15.x"],
        installation_paths=[
            "/var/lib/postgresql",
            "/usr/lib/postgresql",
            "C:/Program Files/PostgreSQL"
        ],
        is_system_preset=True,
        metadata={"maintainer": "system", "version": "1.0"}
    ),
    
    "web_development": ApplicationPreset(
        id="preset_web_dev",
        name="Web Development Project",
        description="Typical web development project structure",
        application_name="Web Development",
        selection_template=SelectionTemplate(
            id="template_web_dev",
            name="Web Development Backup",
            description="Web development project with dependencies excluded",
            selection_config=SelectionConfig(
                include_paths=[Path(".")],  # Current directory
                exclude_paths=[],
                include_patterns=[
                    PatternRule("*.html", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.css", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.js", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.ts", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.json", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.md", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                exclude_patterns=[
                    PatternRule("node_modules/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                    PatternRule("dist/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                    PatternRule("build/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                    PatternRule(".git/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                    PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                pattern_groups=["temporary_files", "source_code"],
                precedence_config=PrecedenceConfig(
                    default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                    conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                ),
                case_sensitive=True,
                performance_hints={"skip_node_modules": True}
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["development", "web", "javascript", "typescript"],
            is_system_template=True,
            metadata={"preset_id": "preset_web_dev"}
        ),
        category=ApplicationCategory.DEVELOPMENT,
        platform_specific={},
        version_compatibility=["*"],
        installation_paths=[],
        is_system_preset=True,
        metadata={"maintainer": "system", "version": "1.0"}
    )
}
```

## Error Handling

### Error Classification

```python
class SelectionError(Exception):
    """Base exception for data selection operations"""
    pass

class PatternSyntaxError(SelectionError):
    """Invalid pattern syntax"""
    def __init__(self, pattern: str, syntax_type: PatternSyntax, details: str):
        self.pattern = pattern
        self.syntax_type = syntax_type
        self.details = details
        super().__init__(f"Invalid {syntax_type.value} pattern '{pattern}': {details}")

class SelectionValidationError(SelectionError):
    """Selection configuration validation failed"""
    pass

class PrecedenceConflictError(SelectionError):
    """Unresolvable precedence conflict"""
    pass

class TemplateNotFoundError(SelectionError):
    """Selection template not found"""
    pass

class PatternGroupNotFoundError(SelectionError):
    """Pattern group not found"""
    pass

class PerformanceThresholdExceededError(SelectionError):
    """Selection operation exceeded performance thresholds"""
    pass

class PathAccessError(SelectionError):
    """Path access denied or not found"""
    pass
```

### Error Recovery Strategies

1. **Pattern Compilation Errors**: Fallback to literal matching with warnings
2. **Path Access Errors**: Continue with accessible paths, report inaccessible ones
3. **Performance Threshold Exceeded**: Switch to streaming evaluation mode
4. **Template/Group Not Found**: Provide suggestions for similar names
5. **Precedence Conflicts**: Apply default resolution strategy with warnings

## Testing Strategy

### Unit Testing

**Selection Manager Tests**:
- Pattern compilation and caching
- Precedence rule evaluation
- Performance optimization
- Error handling and recovery
- Template integration

**Pattern Engine Tests**:
- Glob pattern matching accuracy
- Regex pattern compilation
- Performance benchmarking
- Syntax validation
- Batch processing efficiency

**Precedence Resolver Tests**:
- Complex hierarchical scenarios
- Configuration validation
- Conflict detection and resolution
- Explanation generation

### Integration Testing

**End-to-End Selection Workflows**:
- Template creation → Selection evaluation → Size estimation
- Pattern group usage across multiple selections
- Application preset deployment and customization
- Import/export functionality with various formats

**Performance Testing**:
- Large file system evaluation (1M+ files)
- Pattern matching performance benchmarks
- Memory usage under load
- Streaming evaluation efficiency

### Functional Testing

**Real-World Scenarios**:
- Home directory backup with complex exclusions
- Development project backup with dependency exclusion
- Media library organization with type-based selection
- System backup with security-sensitive exclusions

**Cross-Platform Testing**:
- Path separator handling (Windows vs Unix)
- Case sensitivity differences
- File system permission variations
- Performance characteristics across platforms

## Implementation Notes

### Performance Optimizations

```python
class SelectionPerformanceOptimizer:
    """Advanced performance optimization strategies."""
    
    def __init__(self):
        self.pattern_cache = LRUCache(maxsize=1000)
        self.path_cache = LRUCache(maxsize=10000)
        self.statistics = PerformanceStatistics()
    
    async def optimize_for_large_filesystem(self, selection: DataSelection, 
                                          estimated_files: int) -> OptimizedSelection:
        """Optimize selection for large file systems."""
        
        if estimated_files > 100000:
            # Use streaming evaluation for very large file systems
            return self._create_streaming_optimized_selection(selection)
        elif estimated_files > 10000:
            # Use batch processing with optimized pattern ordering
            return self._create_batch_optimized_selection(selection)
        else:
            # Use standard in-memory evaluation
            return self._create_standard_selection(selection)
    
    def _optimize_pattern_order(self, patterns: List[PatternRule]) -> List[PatternRule]:
        """Order patterns for optimal evaluation performance."""
        
        # Sort by specificity and expected match frequency
        def pattern_priority(pattern: PatternRule) -> tuple:
            specificity = self._calculate_pattern_specificity(pattern)
            frequency = self._estimate_match_frequency(pattern)
            return (-specificity, frequency)  # High specificity, low frequency first
        
        return sorted(patterns, key=pattern_priority)
    
    def _calculate_pattern_specificity(self, pattern: PatternRule) -> float:
        """Calculate pattern specificity for optimization."""
        
        if pattern.syntax == PatternSyntax.LITERAL:
            return 1.0
        elif pattern.syntax == PatternSyntax.GLOB:
            # Count wildcards - fewer wildcards = more specific
            wildcard_count = pattern.pattern.count('*') + pattern.pattern.count('?')
            return 1.0 / (1.0 + wildcard_count)
        else:  # REGEX
            # Estimate regex complexity
            complexity = len(pattern.pattern) / 100.0  # Simple heuristic
            return min(0.9, complexity)
```

### Streaming Evaluation

```python
class StreamingSelectionEvaluator:
    """Memory-efficient streaming evaluation for large file systems."""
    
    def __init__(self, selection: DataSelection, batch_size: int = 1000):
        self.selection = selection
        self.batch_size = batch_size
        self.compiled_patterns = selection.compiled_patterns
        self.statistics = EvaluationStatistics()
    
    async def evaluate_path_stream(self, path_iterator: AsyncIterator[Path]) -> AsyncIterator[SelectionResult]:
        """Evaluate paths in streaming fashion."""
        
        batch = []
        async for path in path_iterator:
            batch.append(path)
            
            if len(batch) >= self.batch_size:
                results = await self._evaluate_batch(batch)
                for result in results:
                    yield result
                batch.clear()
                
                # Update statistics and check for cancellation
                self.statistics.update_progress(len(batch))
                if self.statistics.should_cancel():
                    break
        
        # Process remaining paths
        if batch:
            results = await self._evaluate_batch(batch)
            for result in results:
                yield result
    
    async def _evaluate_batch(self, paths: List[Path]) -> List[SelectionResult]:
        """Evaluate a batch of paths efficiently."""
        
        results = []
        for path in paths:
            decision = self.selection.precedence_resolver.resolve_selection_conflicts(
                path, self._get_matching_rules(path)
            )
            
            results.append(SelectionResult(
                path=path,
                included=decision.include,
                confidence=decision.confidence,
                applied_rules=decision.applied_rules
            ))
        
        return results
```

### Caching Strategy

```python
class SelectionCacheManager:
    """Intelligent caching for selection operations."""
    
    def __init__(self):
        self.pattern_cache = LRUCache(maxsize=1000)
        self.path_evaluation_cache = LRUCache(maxsize=10000)
        self.template_cache = LRUCache(maxsize=100)
        self.cache_statistics = CacheStatistics()
    
    def get_cached_pattern_compilation(self, patterns: List[PatternRule]) -> Optional[CompiledPatternSet]:
        """Get cached compiled patterns."""
        
        cache_key = self._generate_pattern_cache_key(patterns)
        compiled_patterns = self.pattern_cache.get(cache_key)
        
        if compiled_patterns:
            self.cache_statistics.record_hit('pattern_compilation')
        else:
            self.cache_statistics.record_miss('pattern_compilation')
        
        return compiled_patterns
    
    def cache_pattern_compilation(self, patterns: List[PatternRule], 
                                compiled_patterns: CompiledPatternSet) -> None:
        """Cache compiled patterns."""
        
        cache_key = self._generate_pattern_cache_key(patterns)
        self.pattern_cache[cache_key] = compiled_patterns
    
    def _generate_pattern_cache_key(self, patterns: List[PatternRule]) -> str:
        """Generate cache key for pattern list."""
        
        # Create deterministic key based on pattern content
        pattern_strings = []
        for pattern in sorted(patterns, key=lambda p: (p.pattern, p.syntax.value)):
            pattern_strings.append(f"{pattern.syntax.value}:{pattern.pattern}:{pattern.case_sensitive}")
        
        return hashlib.sha256('|'.join(pattern_strings).encode()).hexdigest()[:16]
```

### Debugging and Testing Tools

```python
class SelectionDebugger:
    """Comprehensive debugging tools for selection configurations."""
    
    def __init__(self, selection: DataSelection):
        self.selection = selection
        self.trace_enabled = False
        self.trace_log = []
    
    def enable_tracing(self) -> None:
        """Enable detailed tracing of selection evaluation."""
        self.trace_enabled = True
        self.trace_log.clear()
    
    def test_path_selection(self, test_path: Path) -> SelectionDebugResult:
        """Test selection logic against a specific path."""
        
        if self.trace_enabled:
            self.trace_log.append(f"Testing path: {test_path}")
        
        # Get all matching rules
        matching_rules = self._get_all_matching_rules(test_path)
        
        if self.trace_enabled:
            self.trace_log.append(f"Matching rules: {len(matching_rules)}")
            for rule in matching_rules:
                self.trace_log.append(f"  - {rule.pattern} ({rule.syntax.value})")
        
        # Resolve precedence
        decision = self.selection.precedence_resolver.resolve_selection_conflicts(
            test_path, matching_rules
        )
        
        if self.trace_enabled:
            self.trace_log.append(f"Final decision: {'INCLUDE' if decision.include else 'EXCLUDE'}")
            self.trace_log.append(f"Confidence: {decision.confidence:.2f}")
        
        return SelectionDebugResult(
            path=test_path,
            decision=decision,
            matching_rules=matching_rules,
            trace_log=self.trace_log.copy() if self.trace_enabled else [],
            performance_metrics=self._get_performance_metrics()
        )
    
    def generate_selection_report(self, sample_paths: List[Path]) -> SelectionReport:
        """Generate comprehensive report for selection configuration."""
        
        report = SelectionReport(
            selection_config=self.selection.config,
            test_results=[],
            pattern_analysis=self._analyze_patterns(),
            performance_analysis=self._analyze_performance(),
            recommendations=[]
        )
        
        # Test sample paths
        for path in sample_paths:
            result = self.test_path_selection(path)
            report.test_results.append(result)
        
        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)
        
        return report

@dataclass
class SelectionDebugResult:
    path: Path
    decision: SelectionDecision
    matching_rules: List[RuleMatch]
    trace_log: List[str]
    performance_metrics: Dict[str, float]

@dataclass
class SelectionReport:
    selection_config: SelectionConfig
    test_results: List[SelectionDebugResult]
    pattern_analysis: PatternAnalysis
    performance_analysis: PerformanceAnalysis
    recommendations: List[str]
```

This design provides a comprehensive, high-performance, and flexible foundation for data selection management that meets the requirements while maintaining excellent performance characteristics and debugging capabilities. The layered architecture supports complex selection scenarios while providing clear interfaces for testing, optimization, and troubleshooting.

<function_calls>
<invoke name="userInput">
<parameter name="question">**Does the design look good? If so, we can move on to the implementation plan.**