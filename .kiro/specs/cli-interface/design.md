# Design Document

## Overview

The CLI Interface design provides a comprehensive command-line interface for TimeLocker that enables both interactive and automated backup operations. The design follows modern CLI best practices with a hierarchical command structure, consistent output formats, and robust error handling. The interface serves as the primary user interaction point for the desktop backup application, integrating with all functional areas including repository management, data selection, policy management, backup operations, recovery operations, scheduling automation, security services, and monitoring/reporting.

## Architecture

### Command Hierarchy

The CLI follows a hierarchical structure with main command groups and subcommands:

```
timelocker (tl)
├── repos                    # Repository management
│   ├── create <name> [uri]
│   ├── list
│   ├── edit <name>
│   ├── validate <name>
│   ├── delete <name>
│   ├── unlock <name>
│   ├── init <name>
│   ├── check <name>
│   ├── stats <name>
│   ├── prune <name>
│   └── migrate <name>
├── selections               # Data selection management
│   ├── create <name>
│   ├── list
│   ├── edit <name>
│   ├── test <name> [path]
│   ├── export <name>
│   ├── import <file>
│   └── delete <name>
├── policies                 # Policy management
│   ├── create <name>
│   ├── list
│   ├── edit <name>
│   ├── assign <policy> <target>
│   └── simulate <name>
├── retention                # Retention policy management
│   ├── create <name>
│   └── edit <name>
├── backup                   # Backup operations
│   ├── run <policy>
│   ├── status
│   ├── list
│   ├── cancel <job-id>
│   └── retry <job-id>
├── restore                  # Recovery operations
│   ├── browse <repository> <snapshot-id>
│   ├── files <repository> <snapshot-id> <paths>
│   ├── full <repository> <snapshot-id> <target>
│   ├── mount <repository> <snapshot-id> <mountpoint>
│   ├── find <repository> <query>
│   ├── diff <repository> <snapshot-a> <snapshot-b>
│   ├── list <repository>
│   └── verify <target>
├── schedule                 # Scheduling automation
│   ├── create <name> [policy]
│   ├── list
│   ├── edit <name>
│   ├── enable <name>
│   ├── disable <name>
│   ├── generate-scripts <name>
│   └── test <name>
├── credentials              # Security services
│   ├── set <repository>
│   ├── show <repository>
│   └── remove <repository>
├── security                 # Security status
│   ├── status
│   └── audit
├── status                   # System status
├── logs                     # Log management
│   └── view
├── reports                  # Reporting
│   └── generate <type>
├── monitor                  # System monitoring
│   ├── health
│   └── stats
├── notifications            # Notification configuration
│   └── configure
├── import                   # Configuration import
│   ├── timeshift
│   └── config <file>
├── export                   # Configuration export
│   └── config <file>
├── migrate                  # Migration operations
│   └── validate <source>
├── completion               # Shell completion
│   └── install <shell>
├── version                  # Version information
└── completion               # Completion help
```

### Core Components

#### 1. Command Parser and Router
- **Typer-based CLI framework** for type-safe command definitions
- **Hierarchical command routing** with sub-applications for each functional area
- **Automatic help generation** with usage examples and parameter descriptions
- **Shell completion support** for commands, options, and dynamic values

#### 2. Interactive Mode Handler
- **Default interactive mode** with prompts for missing parameters
- **Configuration wizards** for complex entity creation
- **Configuration branching** allowing creation of dependencies during setup
- **Current value display** during edit operations for user reference

#### 3. Non-Interactive Mode Handler
- **Batch mode operation** with `--non-interactive` flag
- **Parameter validation** with clear error messages for missing required values
- **Exit code management** (0=success, 1=warnings, 2+=errors)
- **Structured error output** in JSON format when requested

#### 4. Output Formatter
- **JSON output support** with `--format json` option for all commands
- **Consistent schema** across all commands with standardized field names
- **Quiet mode** with `--quiet` flag to suppress human-readable messages
- **Rich terminal output** with panels, tables, and progress indicators for interactive use

#### 5. Service Integration Layer
- **CLI Service Manager** bridging legacy and modern architectures
- **Dependency injection** for service components
- **Configuration resolution** for repository names, URIs, and credentials
- **Error handling and translation** from service layer to user-friendly messages

## Components and Interfaces

### CLI Service Manager

The `CLIServiceManager` serves as the primary integration point between the CLI and the underlying service architecture:

```python
class CLIServiceManager:
    def __init__(self, config_dir: Optional[Path] = None)
    
    # Core service access
    @property
    def repository_factory(self) -> IRepositoryFactory
    @property
    def snapshot_service(self) -> SnapshotService
    @property
    def repository_service(self) -> RepositoryService
    @property
    def configuration_service(self) -> IConfigurationProvider
    @property
    def backup_orchestrator(self) -> IBackupOrchestrator
    
    # Repository operations
    def list_repositories(self) -> List[Dict[str, Any]]
    def get_repository_by_name(self, name: str) -> Dict[str, Any]
    def add_repository(self, name: str, uri: str, description: str = "", password: Optional[str] = None)
    def initialize_repository(self, name: str, **kwargs) -> Dict[str, Any]
    def check_repository(self, name: str, **kwargs) -> Dict[str, Any]
    def get_repository_stats(self, name: str, **kwargs) -> Dict[str, Any]
    
    # Backup operations
    def execute_backup_from_cli(self, request: CLIBackupRequest) -> BackupResult
    def verify_backup_integrity(self, repository_input: str, snapshot_id: Optional[str] = None) -> bool
```

### Command Implementation Pattern

Each command follows a consistent implementation pattern:

```python
@command_app.command("command-name")
def command_function(
    # Required parameters
    param: Annotated[str, typer.Argument(help="Parameter description")],
    
    # Optional parameters with defaults
    option: Annotated[Optional[str], typer.Option("--option", help="Option description")] = None,
    
    # Global options
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format")] = False,
    config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
) -> None:
    """Command description."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    
    try:
        # Parameter validation and interactive prompts
        if not param and interactive:
            param = Prompt.ask("Parameter prompt")
        elif not param:
            show_error_panel("Missing Parameter", "Parameter is required in non-interactive mode")
            raise typer.Exit(2)
        
        # Service manager initialization
        manager = _get_service_manager_for_command(config_dir)
        
        # Service method execution
        result = manager.service_method(param, **kwargs)
        
        # Output formatting
        if json_output:
            console.print_json(data=result)
        else:
            # Rich formatted output
            show_success_panel("Operation Complete", f"Successfully processed {param}")
            
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Operation Error", f"Failed to process: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
```

### Interactive Configuration Flows

The CLI supports sophisticated interactive configuration with branching capabilities:

#### Policy Creation Flow
```
1. Prompt for policy name
2. Display existing repositories → Select existing OR create new
   2a. If create new: Branch to repository creation wizard
   2b. Return to policy creation with new repository selected
3. Display existing selections → Select existing OR create new
   3a. If create new: Branch to selection creation wizard
   3b. Return to policy creation with new selection selected
4. Configure schedule, retention, and other policy settings
5. Save complete policy configuration
```

#### Repository Creation Flow
```
1. Prompt for repository name
2. Prompt for repository URI with validation
3. Detect backend type from URI
4. If cloud backend: Prompt for credential storage
   4a. Interactive credential collection
   4b. Secure credential storage via credential manager
5. Initialize repository if requested
6. Set as default repository if requested
```

## Data Models

### CLI Request Models

```python
@dataclass
class CLIBackupRequest:
    sources: List[Path]
    repository_uri: str
    password: Optional[str] = None
    target_name: Optional[str] = None
    backup_name: Optional[str] = None
    tags: List[str] = None
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    dry_run: bool = False
```

### Configuration Models

The CLI integrates with existing configuration models from the Configuration Management system:

- **Repository Configuration**: Name, URI, description, credentials, backend settings
- **Selection Configuration**: Name, include/exclude patterns, pattern groups, precedence rules
- **Policy Configuration**: Name, repository references, selection references, schedule, retention
- **Schedule Configuration**: Name, policy reference, timing, platform-specific settings

### Output Models

#### JSON Output Schema

All commands support consistent JSON output with standardized schemas:

```json
{
  "success": true,
  "timestamp": "2024-01-01T12:00:00Z",
  "command": "repos list",
  "data": {
    "repositories": [
      {
        "name": "local-backup",
        "uri": "file:///backup/repo",
        "description": "Local backup repository",
        "status": "healthy",
        "last_check": "2024-01-01T11:00:00Z"
      }
    ]
  },
  "metadata": {
    "total_count": 1,
    "execution_time_ms": 150
  }
}
```

#### Error Response Schema

```json
{
  "success": false,
  "timestamp": "2024-01-01T12:00:00Z",
  "command": "repos create",
  "error": {
    "type": "ValidationError",
    "message": "Repository name contains invalid characters",
    "details": [
      "Repository name must contain only letters, numbers, dashes, underscores, or dots"
    ],
    "code": "INVALID_REPO_NAME"
  }
}
```

## Error Handling

### Error Categories

1. **Validation Errors** (Exit Code 2)
   - Invalid parameters
   - Missing required arguments in non-interactive mode
   - Configuration validation failures

2. **Operation Errors** (Exit Code 1)
   - Service operation failures
   - Repository connectivity issues
   - Backup/restore operation failures

3. **System Errors** (Exit Code 1)
   - Configuration file access issues
   - Credential manager failures
   - Unexpected system errors

4. **User Cancellation** (Exit Code 130)
   - Keyboard interrupt (Ctrl+C)
   - Interactive operation cancellation

### Error Display

#### Interactive Mode
- **Rich panels** with colored borders and icons
- **Detailed error messages** with suggested remediation steps
- **Context information** to help users understand and resolve issues

#### Non-Interactive Mode
- **Structured JSON error output** when `--format json` is specified
- **Plain text error messages** for script consumption
- **Appropriate exit codes** for automation and monitoring

### Logging Integration

- **File logging** to `~/.cache/timelocker/logs/timelocker.log` with rotation
- **User-facing log filtering** to show only relevant messages in CLI
- **Verbose mode** for detailed debugging information
- **Audit logging** for security-related operations

## Testing Strategy

### Unit Testing
- **Command function testing** with mocked service dependencies
- **Interactive flow testing** using Typer's CliRunner with input simulation
- **Output format testing** for both human-readable and JSON formats
- **Error handling testing** for all error categories and exit codes

### Integration Testing
- **Service integration testing** with real service implementations
- **Configuration integration testing** with actual configuration files
- **End-to-end workflow testing** for complex multi-step operations

### CLI-Specific Testing
- **Shell completion testing** for all supported shells
- **Non-interactive mode testing** with various parameter combinations
- **Interactive prompt testing** with different user input scenarios
- **Output format consistency testing** across all commands

### Performance Testing
- **Command startup time** measurement and optimization
- **Large dataset handling** for list and stats commands
- **Memory usage** monitoring for long-running operations
- **Concurrent operation** testing for multi-repository commands

The CLI design provides a robust, user-friendly interface that scales from simple interactive use to complex automated workflows while maintaining consistency and reliability across all functional areas of the TimeLocker system.