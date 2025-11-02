# Requirements Document

## Introduction

The CLI Interface feature provides a comprehensive command-line interface for TimeLocker that enables scriptable automation of all backup operations. This system mirrors GUI functionality through command-line tools, supports batch workflows, scheduler integration, and provides machine-readable output formats for integration with external systems and automation frameworks. For comprehensive scheduling capabilities, see the Scheduling/Automation specification. For configuration migration, see the Migration/Import specification.

## Glossary

- **Command-Line Interface (CLI)**: A text-based interface for interacting with TimeLocker through terminal commands
- **Scriptable Automation**: The ability to execute TimeLocker operations through scripts and automated workflows
- **Batch Operations**: Execution of multiple operations in sequence or parallel through command-line scripts
- **Machine-Readable Output**: Structured output formats (JSON, XML, CSV) that can be processed by other programs
- **Non-Interactive Mode**: CLI operation mode that doesn't require user input during execution
- **Command Hierarchy**: Organized structure of CLI commands and subcommands for different functional areas
- **Auto-Completion**: Shell feature that automatically completes command names, options, and arguments
- **Shell Completion Scripts**: Generated scripts that enable auto-completion for specific shells
- **Wrapper Script**: Generated shell script that handles environment setup, execution, and error handling for automated operations
- **Automation Template**: Pre-configured script template for different scheduling systems and environments
- **Timeshift Import**: Functionality to migrate configuration from Timeshift backup system to TimeLocker
- **Dry-Run Mode**: Execution mode that shows what would happen without making actual changes
- **TimeLocker System**: The backup orchestration platform built on Restic
- **Exit Codes**: Numeric codes returned by CLI commands to indicate success or failure status

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want a comprehensive CLI that mirrors GUI functionality, so that I can perform all backup operations from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide CLI commands for all repository management operations including create, configure, validate, and delete
2. WHEN executing backup operations, THE TimeLocker System SHALL support CLI commands for job creation, scheduling, execution, and monitoring
3. THE TimeLocker System SHALL provide CLI commands for recovery operations including snapshot browsing, file selection, and restoration
4. THE TimeLocker System SHALL support CLI commands for policy management including creation, assignment, and enforcement
5. WHERE GUI functionality exists, THE TimeLocker System SHALL provide equivalent CLI commands with the same capabilities

### Requirement 2

**User Story:** As a DevOps engineer, I want CLI commands to support batch operations, so that I can automate complex workflows involving multiple repositories and operations.

#### Acceptance Criteria

1. THE TimeLocker System SHALL support batch execution of multiple CLI commands through script files
2. WHEN running batch operations, THE TimeLocker System SHALL provide options for parallel execution where appropriate
3. THE TimeLocker System SHALL support command chaining with conditional execution based on previous command results
4. THE TimeLocker System SHALL provide progress reporting for long-running batch operations
5. WHERE batch operations fail, THE TimeLocker System SHALL provide detailed error reporting and rollback options where applicable

### Requirement 3

**User Story:** As an automation engineer, I want CLI commands to produce machine-readable output, so that I can integrate TimeLocker with monitoring and orchestration systems.

#### Acceptance Criteria

1. THE TimeLocker System SHALL support multiple output formats including JSON, XML, and CSV for all CLI commands
2. WHEN producing structured output, THE TimeLocker System SHALL ensure consistent schema across all commands
3. THE TimeLocker System SHALL provide quiet mode options that suppress human-readable messages and output only essential data
4. THE TimeLocker System SHALL support filtering and field selection in output to reduce data volume for specific use cases
5. WHERE commands produce large datasets, THE TimeLocker System SHALL support pagination and streaming output options

### Requirement 4

**User Story:** As a system administrator, I want CLI commands to support non-interactive operation, so that they can run in automated environments without user input.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide non-interactive modes for all CLI commands that typically require user input
2. WHEN running in non-interactive mode, THE TimeLocker System SHALL accept all required parameters through command-line arguments or configuration files
3. THE TimeLocker System SHALL support credential input through environment variables and secure configuration files
4. THE TimeLocker System SHALL provide default behaviors for optional parameters when running non-interactively
5. WHERE non-interactive execution encounters errors, THE TimeLocker System SHALL fail gracefully with appropriate exit codes and error messages

### Requirement 5

**User Story:** As a system administrator, I want comprehensive CLI help and documentation, so that I can discover and use CLI features effectively.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide built-in help for all CLI commands including usage examples and parameter descriptions
2. WHEN requesting help, THE TimeLocker System SHALL display command syntax, available options, and practical examples
3. THE TimeLocker System SHALL support command discovery through tab completion and command listing
4. THE TimeLocker System SHALL provide man pages or equivalent documentation for offline reference
5. WHERE commands have complex parameter combinations, THE TimeLocker System SHALL provide guided help and validation messages

### Requirement 6

**User Story:** As a DevOps engineer, I want CLI commands to integrate with schedulers and monitoring systems, so that backup operations can be fully automated and monitored.

#### Acceptance Criteria

1. THE TimeLocker System SHALL return appropriate exit codes for success, warning, and error conditions
2. WHEN integrating with schedulers, THE TimeLocker System SHALL support timeout configurations and graceful termination
3. THE TimeLocker System SHALL provide status and progress information that can be consumed by monitoring systems
4. THE TimeLocker System SHALL support webhook notifications and external system integration through CLI parameters
5. WHERE CLI operations are monitored, THE TimeLocker System SHALL provide metrics and health check endpoints accessible via CLI

### Requirement 7

**User Story:** As a security administrator, I want CLI operations to maintain security standards, so that command-line access doesn't compromise system security.

#### Acceptance Criteria

1. THE TimeLocker System SHALL enforce the same authentication and authorization requirements for CLI as for GUI operations
2. WHEN handling credentials in CLI, THE TimeLocker System SHALL never expose them in process lists or command history
3. THE TimeLocker System SHALL support secure credential input methods including environment variables and encrypted configuration files
4. THE TimeLocker System SHALL log all CLI operations with user identity and command details for audit purposes
5. WHERE CLI commands access sensitive data, THE TimeLocker System SHALL apply the same encryption and access controls as other interfaces

### Requirement 8

**User Story:** As a system administrator, I want CLI auto-completion support, so that I can efficiently discover and use commands without memorizing syntax.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide shell completion scripts for Bash, Zsh, and Fish shells
2. WHEN using auto-completion, THE TimeLocker System SHALL complete repository names, snapshot IDs, and target names
3. THE TimeLocker System SHALL support both automatic installation and manual installation of completion scripts
4. THE TimeLocker System SHALL provide completion for both `timelocker` and `tl` command aliases
5. WHERE completion requires authentication, THE TimeLocker System SHALL use available credentials to provide dynamic completions

### Requirement 9

**User Story:** As a system administrator migrating from Timeshift, I want to import existing configurations, so that I can preserve backup settings and exclude patterns.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide Timeshift configuration import functionality with automatic path detection
2. WHEN importing Timeshift configs, THE TimeLocker System SHALL convert backup paths, exclude patterns, and repository mappings
3. THE TimeLocker System SHALL support dry-run mode to preview import changes before applying them
4. THE TimeLocker System SHALL resolve device UUIDs to mount paths and provide manual override options
5. WHERE Timeshift settings cannot be directly converted, THE TimeLocker System SHALL provide clear mapping documentation and alternative configuration guidance

### Requirement 10

**User Story:** As a system administrator, I want CLI-generated automation scripts and templates, so that I can quickly set up scheduled backups with proper configuration and error handling.

#### Acceptance Criteria

1. THE TimeLocker System SHALL generate wrapper scripts for systemd timer integration with proper service unit configuration
2. WHEN creating automation scripts, THE TimeLocker System SHALL include environment variable management, error handling, and logging
3. THE TimeLocker System SHALL provide script templates for different scheduling systems including cron and container-based automation
4. THE TimeLocker System SHALL validate generated scripts for syntax, permissions, and executability
5. WHERE automation scripts are generated, THE TimeLocker System SHALL provide installation guidance and verification commands

### Requirement 11

**User Story:** As a system administrator, I want CLI commands to provide detailed error handling and debugging information, so that I can troubleshoot issues effectively.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide verbose logging modes for CLI commands to aid in troubleshooting
2. WHEN errors occur, THE TimeLocker System SHALL provide specific error messages with suggested remediation steps
3. THE TimeLocker System SHALL support debug modes that provide detailed execution information without compromising security
4. THE TimeLocker System SHALL validate command parameters and provide clear validation error messages
5. WHERE CLI operations fail, THE TimeLocker System SHALL provide sufficient context information to enable effective problem resolution