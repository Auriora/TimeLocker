# Design Document

## Overview

The Repository Management design implements a layered architecture that provides secure, flexible, and extensible repository lifecycle management for desktop backup scenarios. The design centers around a Repository Manager that coordinates between backup engines, credential management, and validation services while supporting multiple backup strategies through a plugin architecture.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Repository Management                    │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │   Repository    │ │   Credential    │ │   Validation    │ │
│ │    Manager      │ │    Manager      │ │    Service      │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │   Configuration │  │    Plugin       │                   │
│  │     Store       │  │    Registry     │                   │
│  └─────────────────┘  └─────────────────┘                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │     Restic      │  │     Rsync       │  │     Rclone      │ │
│  │    Engine       │  │     Engine      │  │     Engine      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Relationships

- **Repository Manager**: Central orchestrator for all repository operations
- **Credential Manager**: Secure credential storage and resolution (integrates with Security Services)
- **Validation Service**: Repository connectivity and integrity validation
- **Configuration Store**: Simple persistent storage for repository metadata and settings
- **Plugin Registry**: Extensible backup engine support through plugin architecture
- **Backup Engines**: Pluggable implementations for different backup strategies (Restic, Rsync, Rclone)

## Components and Interfaces

### Repository Manager

**Purpose**: Central coordinator for repository lifecycle operations

**Interface**:
```python
class RepositoryManager:
    async def create_repository(self, config: RepositoryConfig) -> Repository
    async def detect_existing_repository(self, uri: str) -> Optional[ExistingRepositoryInfo]
    async def connect_to_existing_repository(self, uri: str, credentials: Optional[Dict] = None) -> Repository
    async def reinitialize_repository(self, uri: str, config: RepositoryConfig, force_confirm: bool = False) -> Repository
    async def get_repository(self, name: str) -> Repository
    async def list_repositories(self, filters: Optional[Dict] = None) -> List[Repository]
    async def update_repository(self, name: str, updates: Dict) -> Repository
    async def delete_repository(self, name: str, force: bool = False) -> bool
    async def validate_repository(self, name: str) -> ValidationResult
    async def set_default_repository(self, name: str) -> bool
```

**Key Responsibilities**:
- Repository CRUD operations with validation
- Existing repository detection and connection handling
- Safe repository re-initialization with data loss protection
- Coordination with credential and validation services
- Backup engine selection and initialization
- Desktop-appropriate concurrent operation management (up to 3 parallel operations)
- Repository lifecycle management for typical desktop usage (up to 20 repositories)
- Transaction-like operations for repository creation with rollback capability

### Credential Manager Integration

**Purpose**: Secure credential management for repository access

**Interface**:
```python
class RepositoryCredentialManager:
    async def store_credentials(self, repo_id: str, credentials: Dict) -> bool
    async def retrieve_credentials(self, repo_id: str) -> Optional[Dict]
    async def rotate_credentials(self, repo_id: str, new_credentials: Dict) -> bool
    async def remove_credentials(self, repo_id: str) -> bool
    def resolve_credentials(self, repo_id: str) -> Dict
```

**Integration Points**:
- Uses Security Services for encryption and secure storage
- Implements credential resolution order: stored → environment → interactive
- Provides audit logging for all credential operations

### Validation Service

**Purpose**: Repository connectivity and integrity validation

**Interface**:
```python
class RepositoryValidationService:
    async def validate_connectivity(self, repo: Repository) -> ConnectivityResult
    async def validate_integrity(self, repo: Repository) -> IntegrityResult
    async def validate_configuration(self, config: RepositoryConfig) -> ConfigValidationResult
    async def batch_validate(self, repos: List[Repository]) -> List[ValidationResult]
```

**Performance Requirements**:
- Network repository validation: ≤15 seconds
- Local repository validation: ≤3 seconds
- Concurrent validations: up to 3 parallel operations for desktop usage
- Timeout handling with desktop-appropriate limits

### Configuration Store

**Purpose**: Persistent storage for repository metadata and configuration

**Data Schema**:
```python
@dataclass
class RepositoryConfig:
    name: str
    uri: str
    engine: BackupEngine
    type: RepositoryType
    description: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_default: bool
    engine_config: Dict[str, Any]
    
@dataclass
class Repository:
    config: RepositoryConfig
    status: RepositoryStatus
    last_validated: Optional[datetime]
    validation_result: Optional[ValidationResult]
    usage_stats: Optional[UsageStats]

@dataclass
class ExistingRepositoryInfo:
    uri: str
    engine_type: BackupEngine
    requires_credentials: bool
    repository_id: Optional[str]
    metadata: Dict[str, Any]
    last_modified: Optional[datetime]
    estimated_size: Optional[int]
    
@dataclass
class RepositoryCreationOptions:
    connect_if_exists: bool = False
    reinitialize_if_exists: bool = False
    require_confirmation_for_reinit: bool = True
    backup_existing_config: bool = True
```

**Storage Implementation**:
- JSON-based configuration files for simplicity and portability
- Simple file-based storage appropriate for desktop usage
- Basic backup/restore capability for configuration safety
- File locking for concurrent access protection



### Plugin Registry

**Purpose**: Extensible backup engine support through plugin architecture

**Plugin Interface**:
```python
class BackupEnginePlugin:
    @property
    def engine_name(self) -> str
    
    @property
    def engine_version(self) -> str
    
    def is_available(self) -> bool
    def validate_configuration(self, config: Dict) -> ValidationResult
    def create_repository(self, uri: str, config: RepositoryConfig) -> BackupRepository
    def supports_storage_type(self, storage_type: str) -> bool
    def get_supported_features(self) -> List[str]
    def get_storage_backends(self) -> List[str]
```

**Built-in Engines**:
- **ResticEngine**: Encrypted, deduplicated backup with snapshots (current implementation)
- **RsyncEngine**: Simple file synchronization without encryption or deduplication
- **RcloneEngine**: Cloud storage synchronization with many provider integrations

## Data Models

### Repository Configuration Model

```python
class BackupEngine(Enum):
    RESTIC = "restic"
    RSYNC = "rsync"
    RCLONE = "rclone"

class RepositoryType(Enum):
    LOCAL = "local"
    S3 = "s3"
    B2 = "b2"
    SFTP = "sftp"
    SMB = "smb"
    NFS = "nfs"

class RepositoryStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    VALIDATING = "validating"

class ValidationResult:
    success: bool
    timestamp: datetime
    connectivity_status: ConnectivityStatus
    integrity_status: IntegrityStatus
    error_details: Optional[List[str]]
    performance_metrics: Dict[str, float]
    recommendations: List[str]
```

### URI Pattern Recognition

```python
URI_PATTERNS = {
    'local': re.compile(r'^file://(.+)$'),
    's3': re.compile(r'^s3:(?:https?://)?([^/]+)/(.+)$'),
    'b2': re.compile(r'^b2:([^/]+)/(.+)$'),
    'sftp': re.compile(r'^sftp://([^@]+@)?([^:]+)(?::(\d+))?/(.+)$'),
    'smb': re.compile(r'^smb://([^/]+)/(.+)$'),
    'nfs': re.compile(r'^nfs://([^/]+)/(.+)$'),
}
```

### Backup Engine Configuration

```python
@dataclass
class ResticEngineConfig:
    compression: str = "auto"
    pack_size: Optional[int] = None
    cache_dir: Optional[str] = None
    exclude_caches: bool = True
    one_file_system: bool = False

@dataclass
class RsyncEngineConfig:
    archive_mode: bool = True
    compress: bool = True
    delete_excluded: bool = False
    preserve_permissions: bool = True
    preserve_times: bool = True
    dry_run: bool = False

@dataclass
class RcloneEngineConfig:
    config_file: Optional[str] = None
    transfers: int = 4
    checkers: int = 8
    buffer_size: str = "16M"
    use_mmap: bool = False

ENGINE_CONFIGURATIONS = {
    BackupEngine.RESTIC: ResticEngineConfig,
    BackupEngine.RSYNC: RsyncEngineConfig,
    BackupEngine.RCLONE: RcloneEngineConfig,
}
```

### S3-Compatible Service Configuration

```python
@dataclass
class S3Config:
    endpoint: str
    region: Optional[str]
    access_key_id: str
    secret_access_key: str
    bucket: str
    path_prefix: Optional[str]
    use_ssl: bool = True
    verify_ssl: bool = True
    connection_timeout: int = 30
    read_timeout: int = 300

S3_COMPATIBLE_SERVICES = {
    'minio': {'default_port': 9000, 'supports_regions': False},
    'wasabi': {'endpoint_template': 's3.{region}.wasabisys.com'},
    'backblaze': {'endpoint_template': 's3.{region}.backblazeb2.com'},
    'digitalocean': {'endpoint_template': '{region}.digitaloceanspaces.com'},
}
```

## Repository Creation Workflow

### Existing Repository Detection and Handling

The repository creation process includes sophisticated handling for existing repositories to prevent data loss and provide flexible connection options.

#### Detection Process

```python
async def create_repository_with_detection(self, config: RepositoryConfig, options: RepositoryCreationOptions) -> Repository:
    """
    Enhanced repository creation with existing repository detection and handling.
    
    Workflow:
    1. Validate configuration and credentials
    2. Check for existing repository at URI
    3. If exists: offer connection or re-initialization options
    4. If not exists: proceed with normal creation
    5. Handle user choice and execute appropriate action
    """
    
    # Step 1: Pre-validation
    validation_result = await self.validate_configuration(config)
    if not validation_result.success:
        raise RepositoryValidationError(validation_result.errors)
    
    # Step 2: Existing repository detection
    existing_info = await self.detect_existing_repository(config.uri)
    
    if existing_info:
        return await self._handle_existing_repository(config, existing_info, options)
    else:
        return await self._create_new_repository(config)
```

#### Existing Repository Handling Options

```python
class ExistingRepositoryHandler:
    async def handle_existing_repository(self, config: RepositoryConfig, 
                                       existing_info: ExistingRepositoryInfo,
                                       user_choice: str) -> Repository:
        """
        Handle existing repository based on user choice.
        
        Choices:
        - 'connect': Connect to existing repository (preserve data)
        - 'reinitialize': Re-initialize repository (data loss)
        - 'abort': Cancel operation
        """
        
        if user_choice == 'connect':
            return await self._connect_to_existing(config, existing_info)
        elif user_choice == 'reinitialize':
            return await self._reinitialize_existing(config, existing_info)
        else:
            raise RepositoryError("Operation cancelled by user")
    
    async def _connect_to_existing(self, config: RepositoryConfig, 
                                 existing_info: ExistingRepositoryInfo) -> Repository:
        """Connect to existing repository with credential handling."""
        
        if existing_info.requires_credentials:
            credentials = await self._prompt_for_credentials(config.uri)
            if not credentials:
                raise CredentialError("Credentials required to unlock existing repository")
        
        # Validate access to existing repository
        validation_result = await self.validation_service.validate_connectivity(
            Repository(config=config, status=RepositoryStatus.VALIDATING)
        )
        
        if not validation_result.success:
            raise RepositoryValidationError(f"Cannot connect to existing repository: {validation_result.error_details}")
        
        # Update configuration with existing repository metadata
        config.metadata.update(existing_info.metadata)
        return Repository(config=config, status=RepositoryStatus.ACTIVE)
    
    async def _reinitialize_existing(self, config: RepositoryConfig,
                                   existing_info: ExistingRepositoryInfo) -> Repository:
        """Re-initialize existing repository with safety checks."""
        
        # Require explicit confirmation for data loss
        confirmation = await self._require_data_loss_confirmation(existing_info)
        if not confirmation:
            raise DataLossConfirmationError("User confirmation required for repository re-initialization")
        
        # Optional: Backup existing repository metadata
        if config.metadata.get('backup_before_reinit', True):
            await self._backup_existing_metadata(existing_info)
        
        # Proceed with re-initialization
        return await self._create_new_repository(config, force_reinit=True)
```

#### Safety and Confirmation Mechanisms

```python
class RepositorySafetyManager:
    async def require_data_loss_confirmation(self, existing_info: ExistingRepositoryInfo) -> bool:
        """
        Require explicit user confirmation for operations that cause data loss.
        
        Provides detailed information about what will be lost:
        - Repository size and last modified date
        - Number of snapshots/backups (if detectable)
        - Estimated data loss impact
        """
        
        warning_message = self._generate_data_loss_warning(existing_info)
        confirmation_prompt = (
            f"{warning_message}\n\n"
            "Type 'DELETE ALL DATA' to confirm re-initialization: "
        )
        
        user_input = await self._prompt_user(confirmation_prompt)
        return user_input.strip() == "DELETE ALL DATA"
    
    def _generate_data_loss_warning(self, existing_info: ExistingRepositoryInfo) -> str:
        """Generate detailed warning about data loss."""
        
        size_info = f"Size: {self._format_size(existing_info.estimated_size)}" if existing_info.estimated_size else "Size: Unknown"
        modified_info = f"Last modified: {existing_info.last_modified}" if existing_info.last_modified else "Last modified: Unknown"
        
        return (
            "⚠️  WARNING: REPOSITORY RE-INITIALIZATION WILL PERMANENTLY DELETE ALL DATA ⚠️\n"
            f"Repository URI: {existing_info.uri}\n"
            f"Engine: {existing_info.engine_type.value}\n"
            f"{size_info}\n"
            f"{modified_info}\n"
            "\nThis action cannot be undone. All backup data will be permanently lost."
        )
```

## Error Handling

### Error Classification

```python
class RepositoryError(Exception):
    """Base exception for repository operations"""
    pass

class RepositoryNotFoundError(RepositoryError):
    """Repository does not exist"""
    pass

class RepositoryAlreadyExistsError(RepositoryError):
    """Repository already exists at specified location"""
    def __init__(self, uri: str, existing_info: ExistingRepositoryInfo):
        self.uri = uri
        self.existing_info = existing_info
        super().__init__(f"Repository already exists at {uri}")

class RepositoryValidationError(RepositoryError):
    """Repository validation failed"""
    pass

class CredentialError(RepositoryError):
    """Credential-related errors"""
    pass

class BackendError(RepositoryError):
    """Storage backend errors"""
    pass

class RepositoryLockError(RepositoryError):
    """Repository is locked by another process"""
    pass

class DataLossConfirmationError(RepositoryError):
    """User confirmation required for data loss operation"""
    pass
```

### Error Recovery Strategies

1. **Transient Network Errors**: Exponential backoff retry (3 attempts)
2. **Credential Errors**: Fallback to environment variables, then interactive prompt
3. **Configuration Errors**: Detailed validation messages with suggestions
4. **Backend Unavailability**: Graceful degradation with cached data
5. **Concurrent Access**: Lock-based coordination with timeout handling

### Error Reporting

```python
@dataclass
class ErrorReport:
    error_code: str
    message: str
    context: Dict[str, Any]
    suggested_actions: List[str]
    recovery_options: List[str]
    timestamp: datetime
```

## Testing Strategy

### Unit Testing

**Repository Manager Tests**:
- CRUD operations with various configurations
- Concurrent operation handling
- Error condition simulation
- Cache behavior validation
- Plugin integration testing

**Validation Service Tests**:
- Connectivity testing with mock backends
- Timeout and retry logic validation
- Performance requirement verification
- Error handling and reporting

**Backend Plugin Tests**:
- URI pattern recognition
- Configuration validation
- Feature capability testing
- Error condition handling

### Integration Testing

**End-to-End Repository Lifecycle**:
- Create → Validate → Use → Update → Delete workflows
- Multi-backend repository management
- Credential rotation scenarios
- Performance under concurrent load

**Storage Backend Integration**:
- Real backend connectivity (MinIO, local filesystem)
- Authentication and authorization
- Network failure simulation
- Large-scale repository management (1000+ repositories)

### Performance Testing

**Scalability Tests**:
- 1000+ repository management
- Concurrent validation (10-50 parallel)
- Cache effectiveness measurement
- Memory usage under load

**Performance Benchmarks**:
- Repository listing: <2s for 1000 repositories
- Validation: <30s network, <5s local
- Configuration updates: <1s
- Cache hit ratios: >80% for metadata

### Security Testing

**Credential Security**:
- Encryption verification
- Audit log integrity
- Access control validation
- Credential exposure prevention

**Configuration Security**:
- File permission validation
- Concurrent access safety
- Backup/restore integrity
- Schema validation

## Implementation Notes

### Repository State Management

```python
class RepositoryStateManager:
    """Manages repository state transitions and consistency."""
    
    async def transition_state(self, repo: Repository, new_state: RepositoryStatus, 
                             context: Optional[Dict] = None) -> bool:
        """
        Safely transition repository state with validation and logging.
        
        State transitions:
        - INACTIVE -> VALIDATING -> ACTIVE/ERROR
        - ACTIVE -> VALIDATING -> ACTIVE/ERROR
        - ERROR -> VALIDATING -> ACTIVE/ERROR
        - Any -> INACTIVE (for deletion/deactivation)
        """
        
        if not self._is_valid_transition(repo.status, new_state):
            raise RepositoryError(f"Invalid state transition: {repo.status} -> {new_state}")
        
        # Log state transition
        await self.audit_logger.log_state_transition(
            repo.config.name, repo.status, new_state, context
        )
        
        repo.status = new_state
        repo.config.updated_at = datetime.utcnow()
        
        return await self.config_store.update_repository(repo)
```

### Concurrent Operation Management

```python
class RepositoryConcurrencyManager:
    """Manages concurrent repository operations for desktop usage."""
    
    def __init__(self, max_concurrent_validations: int = 3):
        self.validation_semaphore = asyncio.Semaphore(max_concurrent_validations)
        self.operation_locks: Dict[str, asyncio.Lock] = {}
    
    async def acquire_repository_lock(self, repo_name: str) -> asyncio.Lock:
        """Acquire exclusive lock for repository operations."""
        if repo_name not in self.operation_locks:
            self.operation_locks[repo_name] = asyncio.Lock()
        return self.operation_locks[repo_name]
    
    async def validate_with_concurrency_limit(self, repos: List[Repository]) -> List[ValidationResult]:
        """Validate repositories with desktop-appropriate concurrency limits."""
        
        async def validate_single(repo: Repository) -> ValidationResult:
            async with self.validation_semaphore:
                return await self.validation_service.validate_repository(repo)
        
        tasks = [validate_single(repo) for repo in repos]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

### Configuration Backup and Recovery

```python
class ConfigurationBackupManager:
    """Manages configuration backup and recovery for safety."""
    
    async def backup_configuration(self, repo_name: str) -> str:
        """Create backup of repository configuration before risky operations."""
        
        config = await self.config_store.get_repository_config(repo_name)
        backup_id = f"{repo_name}_{datetime.utcnow().isoformat()}"
        backup_path = self.backup_dir / f"{backup_id}.json"
        
        await self._write_backup(backup_path, config)
        
        # Keep only last 5 backups per repository
        await self._cleanup_old_backups(repo_name, keep_count=5)
        
        return backup_id
    
    async def restore_configuration(self, backup_id: str) -> bool:
        """Restore repository configuration from backup."""
        
        backup_path = self.backup_dir / f"{backup_id}.json"
        if not backup_path.exists():
            raise RepositoryError(f"Backup {backup_id} not found")
        
        config = await self._read_backup(backup_path)
        return await self.config_store.update_repository_config(config)
```

### Performance Monitoring and Optimization

```python
class RepositoryPerformanceMonitor:
    """Monitors repository operation performance for desktop optimization."""
    
    def __init__(self):
        self.operation_metrics: Dict[str, List[float]] = defaultdict(list)
        self.performance_thresholds = {
            'validation_network': 15.0,  # seconds
            'validation_local': 3.0,     # seconds
            'listing': 2.0,              # seconds
            'configuration_update': 1.0   # seconds
        }
    
    async def monitor_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Monitor operation performance and provide warnings."""
        
        start_time = time.time()
        try:
            result = await operation_func(*args, **kwargs)
            duration = time.time() - start_time
            
            self.operation_metrics[operation_name].append(duration)
            
            # Check performance thresholds
            if operation_name in self.performance_thresholds:
                threshold = self.performance_thresholds[operation_name]
                if duration > threshold:
                    await self._log_performance_warning(operation_name, duration, threshold)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            await self._log_operation_failure(operation_name, duration, str(e))
            raise
    
    async def _log_performance_warning(self, operation: str, duration: float, threshold: float):
        """Log performance warning with suggestions."""
        
        suggestions = {
            'validation_network': [
                "Check network connectivity",
                "Consider increasing timeout settings",
                "Verify repository endpoint is accessible"
            ],
            'validation_local': [
                "Check disk I/O performance",
                "Verify repository path is accessible",
                "Consider repository integrity check"
            ],
            'listing': [
                "Consider reducing number of repositories",
                "Check configuration file size",
                "Verify disk performance"
            ]
        }
        
        logger.warning(
            f"Performance warning: {operation} took {duration:.2f}s (threshold: {threshold:.2f}s). "
            f"Suggestions: {', '.join(suggestions.get(operation, ['Check system performance']))}"
        )
```

### Desktop Optimizations

1. **Lazy Loading**: Repository details loaded on-demand to minimize startup time
2. **Simple Configuration**: JSON-based configuration appropriate for desktop usage
3. **Responsive Operations**: Quick validation and status checks for small repository counts
4. **Engine Detection**: Automatic detection of available backup engines on system
5. **Smart Caching**: Cache frequently accessed repository metadata with TTL
6. **Background Validation**: Optional background validation for inactive repositories

### Desktop Considerations

1. **Resource Efficiency**: Minimal memory footprint for desktop usage (target: <50MB for 20 repositories)
2. **User Experience**: Fast startup (<2s) and responsive operations
3. **Simple Management**: Easy configuration and maintenance for non-technical users
4. **Engine Flexibility**: Support for different backup strategies based on user needs
5. **Offline Capability**: Basic operations work without network connectivity
6. **Progress Feedback**: Real-time progress updates for long-running operations

### Security Considerations

1. **Credential Isolation**: Per-repository credential encryption with unique keys
2. **Audit Logging**: All operations logged with correlation IDs and timestamps
3. **Access Control**: Integration with RBAC system for multi-user scenarios
4. **Secure Defaults**: Conservative security settings by default
5. **Configuration Protection**: Repository configurations encrypted at rest
6. **Secure Communication**: TLS verification for all network operations (with opt-out warnings)
7. **Credential Rotation**: Support for credential updates without repository re-initialization

### Extensibility and Plugin Architecture

1. **Plugin Discovery**: Automatic detection of backup engine plugins
2. **Version Compatibility**: Plugin version checking and compatibility validation
3. **Feature Negotiation**: Dynamic feature detection based on available plugins
4. **Graceful Degradation**: Fallback behavior when plugins are unavailable
5. **Plugin Configuration**: Per-plugin configuration management
6. **Plugin Lifecycle**: Plugin loading, unloading, and update management

This design provides a robust, flexible, and secure foundation for repository management that meets desktop backup requirements while maintaining extensibility for different backup engines and strategies. The enhanced error handling, safety mechanisms, and performance monitoring ensure reliable operation in typical desktop environments.
+h