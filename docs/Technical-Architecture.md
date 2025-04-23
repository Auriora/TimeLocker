# TimeLocker Technical Architecture

## 1. Overview

TimeLocker is a high-level Python interface for backup operations, primarily using the Restic backup tool. It simplifies backup operations through an object-oriented API that handles repository management, file selection patterns, and backup configurations across multiple storage backends.

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Application                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       TimeLocker API Layer                       │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │  BackupManager  │  │ BackupTarget   │  │  FileSelection   │  │
│  └────────┬────────┘  └────────────────┘  └──────────────────┘  │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                             │
│  │BackupRepository │                                             │
│  └────────┬────────┘                                             │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                             │
│  │ BackupSnapshot  │                                             │
│  └─────────────────┘                                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Repository Implementations                    │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ResticRepository │  │ Local Storage  │  │  Cloud Storage   │  │
│  └────────┬────────┘  └────────┬───────┘  └────────┬─────────┘  │
│           │                    │                    │            │
│           └────────────────────┼────────────────────┘            │
│                                │                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Command Builder Layer                      │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ CommandBuilder  │  │CommandParameter│  │CommandDefinition │  │
│  └─────────────────┘  └────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Restic CLI Tool                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Storage Backends                           │
│                                                                 │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │   Local Files   │  │  Amazon S3     │  │   Backblaze B2   │  │
│  └─────────────────┘  └────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Component Breakdown

### 3.1 Core Components

#### BackupManager
- **Purpose**: Central manager for backup operations and plugin registration
- **Responsibilities**:
  - Register repository implementations
  - Create repositories from URIs
  - Manage repository factories
- **Relationships**:
  - Creates and manages BackupRepository instances

#### BackupRepository
- **Purpose**: Abstract interface for backup repositories
- **Responsibilities**:
  - Initialize repositories
  - Perform backup operations
  - Manage snapshots
  - Apply retention policies
- **Relationships**:
  - Used by BackupManager
  - Creates and manages BackupSnapshot instances

#### BackupSnapshot
- **Purpose**: Represents a point-in-time backup
- **Responsibilities**:
  - Provide metadata about backups
  - Support restore operations
  - Support file listing and searching
- **Relationships**:
  - Created by BackupRepository
  - References its parent BackupRepository

#### BackupTarget
- **Purpose**: Defines what to backup
- **Responsibilities**:
  - Manage file selections
  - Associate tags with backups
- **Relationships**:
  - Used by BackupRepository
  - Contains FileSelection instances

#### FileSelection
- **Purpose**: Defines file selection patterns
- **Responsibilities**:
  - Manage include/exclude paths and patterns
  - Support pattern groups for common file types
- **Relationships**:
  - Used by BackupTarget

### 3.2 Repository Implementations

#### ResticRepository
- **Purpose**: Base implementation for Restic-based repositories
- **Responsibilities**:
  - Translate TimeLocker operations to Restic commands
  - Verify Restic executable and version
  - Handle Restic output and events
- **Relationships**:
  - Extends BackupRepository
  - Uses CommandBuilder

#### Repository Type Implementations
- **Local Repository**: Implements local file system storage
- **S3 Repository**: Implements Amazon S3 storage
- **B2 Repository**: Implements Backblaze B2 storage

### 3.3 Command Builder

#### CommandBuilder
- **Purpose**: Builds command-line commands
- **Responsibilities**:
  - Construct command-line arguments
  - Handle parameter styles and formatting
- **Relationships**:
  - Used by ResticRepository
  - Uses CommandDefinition and CommandParameter

#### CommandDefinition
- **Purpose**: Defines a command with parameters and subcommands
- **Responsibilities**:
  - Define command structure
  - Specify parameter requirements
- **Relationships**:
  - Used by CommandBuilder
  - Contains CommandParameter instances

#### CommandParameter
- **Purpose**: Represents a command parameter
- **Responsibilities**:
  - Define parameter properties
  - Specify parameter style and formatting
- **Relationships**:
  - Used by CommandDefinition

## 4. Design Patterns

### 4.1 Creational Patterns

#### Factory Method
- **Usage**: BackupManager uses factory methods to create repository instances
- **Benefits**: Allows dynamic registration of repository implementations

#### Abstract Factory
- **Usage**: Repository factories create specific repository types
- **Benefits**: Encapsulates repository creation logic

### 4.2 Structural Patterns

#### Adapter
- **Usage**: ResticRepository adapts the Restic CLI tool to the BackupRepository interface
- **Benefits**: Allows integration with external tools without modifying their interface

#### Composite
- **Usage**: FileSelection composes multiple file patterns
- **Benefits**: Treats individual patterns and pattern groups uniformly

### 4.3 Behavioral Patterns

#### Command
- **Usage**: CommandBuilder constructs command objects
- **Benefits**: Encapsulates command execution details

#### Strategy
- **Usage**: Different repository implementations provide different storage strategies
- **Benefits**: Allows switching storage backends without changing client code

## 5. Data Flow

1. **Client Application** interacts with the TimeLocker API
2. **BackupManager** creates and manages repository instances
3. **BackupRepository** implementations handle backup operations
4. **CommandBuilder** constructs Restic commands
5. **Restic CLI Tool** executes commands against storage backends

## 6. Security Considerations

- **Password Management**: Passwords can be provided explicitly or via environment variables
- **Sensitive Information**: URI credentials are redacted in logs
- **Validation**: Repository configurations are validated before use

## 7. Scalability and Performance

- **Plugin Architecture**: Allows adding new repository types without modifying core code
- **Command Caching**: Reuses command builders for improved performance
- **Asynchronous Operations**: Support for event handling during long-running operations

## 8. Future Enhancements

- **Additional Storage Backends**: Support for more cloud storage providers
- **Enhanced Monitoring**: Improved progress reporting and statistics
- **Web Interface**: Graphical user interface for backup management
- **Scheduled Backups**: Support for automated backup scheduling