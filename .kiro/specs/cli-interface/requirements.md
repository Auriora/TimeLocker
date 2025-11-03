# Requirements Document

## Introduction

The CLI Interface feature provides a comprehensive command-line interface for TimeLocker that enables scriptable automation of all backup operations. This system supports batch workflows, scheduler integration, and provides machine-readable JSON output for integration with external systems and automation frameworks. This specification defines the complete CLI command hierarchy and syntax for all TimeLocker functional areas including repository management, data selection, policy management, backup operations, recovery operations, scheduling automation, security services, and monitoring/reporting. For comprehensive scheduling capabilities, see the Scheduling/Automation specification. For configuration migration, see the Migration/Import specification.

## Glossary

- **Command-Line Interface (CLI)**: A text-based interface for interacting with TimeLocker through terminal commands
- **Scriptable Automation**: The ability to execute TimeLocker operations through scripts and automated workflows
- **Batch Operations**: Execution of multiple operations in sequence or parallel through command-line scripts
- **Machine-Readable Output**: Structured JSON output format that can be processed by other programs

- **Command Hierarchy**: Organized structure of CLI commands and subcommands for different functional areas
- **Auto-Completion**: Shell feature that automatically completes command names, options, and arguments
- **Shell Completion Scripts**: Generated scripts that enable auto-completion for specific shells
- **Wrapper Script**: Generated shell script that handles environment setup, execution, and error handling for automated operations
- **Automation Template**: Pre-configured script template for different scheduling systems and environments
- **Timeshift Import**: Functionality to migrate configuration from Timeshift backup system to TimeLocker
- **Dry-Run Mode**: Execution mode that shows what would happen without making actual changes
- **TimeLocker System**: The backup orchestration platform built on Restic
- **Exit Codes**: Numeric codes returned by CLI commands to indicate success or failure status
- **Command Aliases**: Short alternative names for commands (e.g., `tl` for `timelocker`)
- **Global Options**: Command-line flags that apply to all commands (e.g., `--verbose`, `--format`)
- **Subcommand**: A secondary command that operates within a main command context (e.g., `create` in `repos create`)
- **Command Abbreviation**: Shortened form of command names that can be used when unambiguous
- **Shell Completion**: Auto-completion functionality for command names, options, and arguments in terminal shells
- **Interactive Mode**: Default CLI operation mode that prompts users for missing information and provides configuration wizards
- **Non-Interactive Mode**: CLI operation mode for scripting that exits with error codes when required parameters are missing
- **Configuration Wizard**: Interactive flow that guides users through complex configuration setup
- **Configuration Branching**: Ability to create or select related entities during interactive configuration flows
- **Current Value Display**: Showing existing configuration values during edit operations for user reference

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want a comprehensive CLI for all backup operations, so that I can manage TimeLocker entirely from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide CLI commands for all repository management operations including create, edit, validate, and delete
2. THE TimeLocker System SHALL provide CLI commands for backup policy creation, execution, and monitoring
3. THE TimeLocker System SHALL provide CLI commands for recovery operations including snapshot browsing, file selection, and restoration
4. THE TimeLocker System SHALL provide CLI commands for retention policy management including creation, assignment, and enforcement
5. THE TimeLocker System SHALL provide CLI commands for data selection, scheduling, security, and monitoring operations

### Requirement 2

**User Story:** As an automation engineer, I want CLI commands to produce machine-readable JSON output, so that I can integrate TimeLocker with monitoring and orchestration systems.

#### Acceptance Criteria

1. THE TimeLocker System SHALL support JSON output format for all CLI commands using `--format json` option
2. THE TimeLocker System SHALL provide consistent JSON schema across all commands with standardized field names and structures
3. THE TimeLocker System SHALL support quiet mode options that suppress human-readable messages and output only essential data using `--quiet` option
4. THE TimeLocker System SHALL provide filtering and field selection in JSON output to reduce data volume for specific use cases
5. WHERE commands produce large datasets, THE TimeLocker System SHALL support pagination options in JSON format

### Requirement 3

**User Story:** As a system administrator, I want interactive and non-interactive CLI modes, so that I can use the CLI both for manual operations with guidance and for automated scripting.

#### Acceptance Criteria

1. THE TimeLocker System SHALL operate in interactive mode by default, prompting users for missing required parameters and providing configuration wizards
2. THE TimeLocker System SHALL support `--non-interactive` mode that exits with appropriate exit codes (0 for success, 1 for warnings, 2+ for errors) when required parameters are missing
3. WHEN using interactive mode, THE TimeLocker System SHALL display current configuration values and allow users to branch into related configuration flows (e.g., creating repositories or selections during policy creation)
4. WHEN operating in non-interactive mode, THE TimeLocker System SHALL accept all required parameters through command-line arguments, configuration files, or environment variables
5. WHERE interactive mode encounters configuration dependencies, THE TimeLocker System SHALL offer to create missing entities (repositories, selections) or select from existing ones with current values displayed for reference

### Requirement 4

**User Story:** As a system administrator, I want comprehensive CLI help and documentation, so that I can discover and use CLI features effectively.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide built-in help for all CLI commands including usage examples and parameter descriptions
2. WHEN requesting help, THE TimeLocker System SHALL display command syntax, available options, and practical examples
3. THE TimeLocker System SHALL support command discovery through tab completion and command listing
4. THE TimeLocker System SHALL provide man pages or equivalent documentation for offline reference
5. WHERE commands have complex parameter combinations, THE TimeLocker System SHALL provide guided help and validation messages

### Requirement 5

**User Story:** As a system administrator, I want CLI auto-completion support, so that I can efficiently discover and use commands without memorizing syntax.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide shell completion scripts for Bash, Zsh, and Fish shells
2. WHEN using auto-completion, THE TimeLocker System SHALL complete repository names, snapshot IDs, and target names
3. THE TimeLocker System SHALL support both automatic installation and manual installation of completion scripts
4. THE TimeLocker System SHALL provide completion for both `timelocker` and `tl` command aliases
5. WHERE completion requires authentication, THE TimeLocker System SHALL use available credentials to provide dynamic completions

### Requirement 6

**User Story:** As a security administrator, I want CLI operations to integrate with Security Services, so that command-line access maintains consistent security standards across the system.

#### Acceptance Criteria

1. THE TimeLocker System SHALL integrate CLI operations with Security Services for all authentication and credential management
2. THE TimeLocker System SHALL use Security Services session management for CLI operations requiring authentication
3. THE TimeLocker System SHALL delegate all credential operations to Security Services and never implement independent credential handling
4. THE TimeLocker System SHALL integrate with Security Services audit logging for all security-related CLI operations
5. WHERE CLI commands access sensitive data, THE TimeLocker System SHALL use Security Services authorization and access control mechanisms

### Requirement 7

**User Story:** As a system administrator, I want CLI commands to provide detailed error handling and debugging information, so that I can troubleshoot issues effectively.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide verbose logging modes for CLI commands using `--verbose` option
2. WHEN errors occur, THE TimeLocker System SHALL provide specific error messages with suggested remediation steps
3. THE TimeLocker System SHALL support debug modes that provide detailed execution information without compromising security
4. THE TimeLocker System SHALL validate command parameters and provide clear validation error messages
5. WHERE CLI operations fail, THE TimeLocker System SHALL provide sufficient context information to enable effective problem resolution

### Requirement 8

**User Story:** As a backup administrator, I want specific CLI commands for repository management operations, so that I can create, configure, and manage backup repositories from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker repos create <name> [uri]` command for creating new repositories with interactive prompts for missing parameters or wizard mode
2. THE TimeLocker System SHALL provide `timelocker repos list` command to display all configured repositories with status, type, and last access information
3. THE TimeLocker System SHALL provide `timelocker repos edit <name>` command for modifying existing repository settings with current values displayed for reference
4. THE TimeLocker System SHALL provide `timelocker repos validate <name>` command to test repository connectivity and integrity
5. THE TimeLocker System SHALL provide `timelocker repos delete <name>` command with safety confirmations for repository removal
6. THE TimeLocker System SHALL provide `timelocker repos unlock <name>` command for removing repository locks when backup processes fail to unlock properly
7. THE TimeLocker System SHALL provide `timelocker repos init <name>` command for initializing repositories that exist but are not yet configured

### Requirement 9

**User Story:** As a backup administrator, I want specific CLI commands for repository maintenance operations, so that I can keep repositories healthy and optimized.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker repos check <name>` command for verifying repository integrity and consistency
2. THE TimeLocker System SHALL provide `timelocker repos stats <name>` command to display repository statistics including size, snapshot count, and deduplication ratios
3. THE TimeLocker System SHALL provide `timelocker repos prune <name>` command for removing unreferenced data and optimizing storage
4. THE TimeLocker System SHALL provide `timelocker repos migrate <name>` command for upgrading repository formats when needed

### Requirement 10

**User Story:** As a backup administrator, I want specific CLI commands for data selection management, so that I can define and manage file selection rules from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker selections create <name>` command for creating named selection templates with interactive pattern configuration
2. THE TimeLocker System SHALL provide `timelocker selections list` command to display all configured selection templates with descriptions and pattern counts
3. THE TimeLocker System SHALL provide `timelocker selections edit <name>` command for modifying existing selection templates with current patterns displayed for reference
4. THE TimeLocker System SHALL provide `timelocker selections test <name> [path]` command to preview which files would be selected by a template
5. THE TimeLocker System SHALL provide `timelocker selections export <name>` and `timelocker selections import <file>` commands for configuration backup and sharing
6. THE TimeLocker System SHALL provide `timelocker selections delete <name>` command for removing selection templates

### Requirement 11

**User Story:** As a backup administrator, I want specific CLI commands for policy management operations, so that I can create and manage backup and retention policies from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker policies create <name>` command for creating backup policies with interactive configuration including repository selection or creation and data selection configuration
2. THE TimeLocker System SHALL provide `timelocker policies list` command to display all configured policies with status and assignment information
3. THE TimeLocker System SHALL provide `timelocker policies edit <name>` command for modifying existing policies with current configuration displayed for reference
4. THE TimeLocker System SHALL provide `timelocker policies assign <policy> <target>` command for assigning policies to repositories or backup operations
5. THE TimeLocker System SHALL provide `timelocker policies simulate <name>` command to preview policy effects before enforcement
6. THE TimeLocker System SHALL provide `timelocker retention create <name>` and `timelocker retention edit <name>` commands for retention policy management

### Requirement 12

**User Story:** As a backup administrator, I want specific CLI commands for backup operations, so that I can execute and monitor backup jobs from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker backup run <policy>` command for executing backup operations with optional dry-run mode
2. THE TimeLocker System SHALL provide `timelocker backup status` command to display current and recent backup operation status
3. THE TimeLocker System SHALL provide `timelocker backup list` command to show backup history with filtering by repository and date range
4. THE TimeLocker System SHALL provide `timelocker backup cancel <job-id>` command for stopping running backup operations
5. THE TimeLocker System SHALL provide `timelocker backup retry <job-id>` command for restarting failed backup operations

### Requirement 13

**User Story:** As a backup administrator, I want specific CLI commands for recovery operations, so that I can browse snapshots and restore data from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker restore browse <repository> <snapshot-id>` command for exploring snapshot contents
2. THE TimeLocker System SHALL provide `timelocker restore files <repository> <snapshot-id> <paths>` command for selective file restoration
3. THE TimeLocker System SHALL provide `timelocker restore full <repository> <snapshot-id> <target>` command for complete snapshot restoration
4. THE TimeLocker System SHALL provide `timelocker restore mount <repository> <snapshot-id> <mountpoint>` command for mounting snapshots as filesystems
5. THE TimeLocker System SHALL provide `timelocker restore find <repository> <query>` command for searching files across snapshots
6. THE TimeLocker System SHALL provide `timelocker restore diff <repository> <snapshot-a> <snapshot-b>` command for comparing snapshots
7. THE TimeLocker System SHALL provide `timelocker restore list <repository>` command to display available snapshots with metadata
8. THE TimeLocker System SHALL provide `timelocker restore verify <target>` command for validating restored data integrity

### Requirement 13

**User Story:** As a system administrator, I want specific CLI commands for scheduling automation, so that I can configure and manage automated backup schedules from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker schedule create <name> [policy]` command for setting up automated backup execution with interactive policy selection if not specified
2. THE TimeLocker System SHALL provide `timelocker schedule list` command to display all configured schedules with next run times and status
3. THE TimeLocker System SHALL provide `timelocker schedule edit <name>` command for modifying existing schedules with current configuration displayed for reference
4. THE TimeLocker System SHALL provide `timelocker schedule enable <name>` and `timelocker schedule disable <name>` commands for schedule management
5. THE TimeLocker System SHALL provide `timelocker schedule generate-scripts <name>` command for creating platform-specific automation scripts
6. THE TimeLocker System SHALL provide `timelocker schedule test <name>` command for validating schedule configuration and dependencies

### Requirement 15

**User Story:** As a security administrator, I want specific CLI commands for security services, so that I can manage credentials and security settings from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker credentials set <repository>` command for securely storing repository authentication information
2. THE TimeLocker System SHALL provide `timelocker credentials show <repository>` command to display credential status without exposing sensitive data
3. THE TimeLocker System SHALL provide `timelocker credentials remove <repository>` command for deleting stored credentials
4. THE TimeLocker System SHALL provide `timelocker security status` command to display overall security configuration and health
5. THE TimeLocker System SHALL provide `timelocker security audit` command for reviewing security-related events and configurations

### Requirement 16

**User Story:** As a system administrator, I want specific CLI commands for monitoring and reporting, so that I can track system status and generate reports from the command line.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker status` command to display overall system health and recent activity summary
2. THE TimeLocker System SHALL provide `timelocker logs view` command with filtering options for date range, level, and component
3. THE TimeLocker System SHALL provide `timelocker reports generate <type>` command for creating backup history, storage usage, and performance reports
4. THE TimeLocker System SHALL provide `timelocker monitor health` command for checking system health and connectivity across all repositories
5. THE TimeLocker System SHALL provide `timelocker monitor stats` command for displaying statistics summary across all repositories
6. THE TimeLocker System SHALL provide `timelocker notifications configure` command for setting up desktop and external notifications

### Requirement 17

**User Story:** As a system administrator migrating from other backup systems, I want specific CLI commands for configuration import and migration, so that I can preserve existing backup configurations and settings.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide `timelocker import timeshift` command for importing Timeshift backup configurations with automatic path detection
2. THE TimeLocker System SHALL provide `timelocker import config <file>` command for importing TimeLocker configuration from backup or other systems
3. THE TimeLocker System SHALL provide `timelocker export config <file>` command for backing up complete TimeLocker configuration
4. THE TimeLocker System SHALL provide `timelocker migrate validate <source>` command for dry-run validation of import operations
5. THE TimeLocker System SHALL provide `timelocker completion install <shell>` command for installing shell completion scripts for Bash, Zsh, and Fish

### Requirement 18

**User Story:** As a backup administrator, I want interactive configuration flows with branching capabilities, so that I can efficiently configure complex entities without switching between multiple commands.

#### Acceptance Criteria

1. WHEN creating policies interactively, THE TimeLocker System SHALL allow users to select existing repositories or create new ones within the same configuration flow
2. WHEN configuring backup policies, THE TimeLocker System SHALL allow users to select existing data selections or create new selection templates within the policy creation process
3. THE TimeLocker System SHALL display current configuration values during edit operations and allow users to keep existing values or modify them
4. WHEN creating schedules interactively, THE TimeLocker System SHALL allow users to select existing policies or create new ones within the schedule configuration flow
5. WHERE configuration dependencies exist, THE TimeLocker System SHALL validate relationships and offer to create missing dependencies or select from existing compatible entities

### Requirement 19

**User Story:** As a system administrator, I want CLI command aliases and shortcuts, so that I can use the interface efficiently for common operations.

#### Acceptance Criteria

1. THE TimeLocker System SHALL support `tl` as a short alias for `timelocker` for all commands
2. THE TimeLocker System SHALL provide common command shortcuts including `tl backup` for `tl backup run`, `tl restore` for `tl restore browse`, and `tl repos` for `tl repos list`
3. THE TimeLocker System SHALL support command abbreviation where unambiguous (e.g., `tl repo` for `tl repos`, `tl sel` for `tl selections`)
4. THE TimeLocker System SHALL provide `--help` and `-h` options for all commands and subcommands with usage examples
5. THE TimeLocker System SHALL support global options including `--verbose`, `--quiet`, `--format`, `--non-interactive`, and `--config` across all commands

### Requirement 20

**User Story:** As a CLI user, I want responsive command performance, so that CLI operations provide good user experience and don't cause delays.

#### Acceptance Criteria

1. THE TimeLocker System SHALL complete CLI command startup and initialization within 200ms for simple commands and 500ms for complex commands
2. THE TimeLocker System SHALL respond to help and information commands within 100ms to provide immediate user feedback
3. THE TimeLocker System SHALL provide progress indicators for operations taking longer than 2 seconds with estimated completion times
4. THE TimeLocker System SHALL support command cancellation (Ctrl+C) with graceful cleanup within 1 second
5. WHERE CLI operations exceed expected performance thresholds, THE TimeLocker System SHALL provide performance warnings and optimization suggestions

### Requirement 21

**User Story:** As a CLI user, I want cross-platform CLI compatibility, so that CLI behavior is consistent across different operating systems.

#### Acceptance Criteria

1. THE TimeLocker System SHALL provide consistent CLI behavior across Windows, macOS, and Linux platforms with identical command syntax and output
2. THE TimeLocker System SHALL handle platform-specific paths and file operations transparently through Integration Architecture
3. THE TimeLocker System SHALL integrate with platform-specific features (credential stores, schedulers) through appropriate service interfaces
4. THE TimeLocker System SHALL provide platform-appropriate error messages and help information while maintaining consistent functionality
5. WHERE platform-specific limitations exist, THE TimeLocker System SHALL provide clear capability reporting and alternative approaches