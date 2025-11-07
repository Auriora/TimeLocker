# Implementation Plan

- [x] 1. Create Repository Manager Core
  - Implement central RepositoryManager class with CRUD operations for repository lifecycle management
  - Add existing repository detection and connection handling with user choice prompts
  - Implement safe repository re-initialization with data loss confirmation mechanisms
  - Add repository state management with validation and audit logging
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [x] 1.1 Implement RepositoryManager class
  - Create core RepositoryManager with async CRUD operations (create, get, list, update, delete)
  - Add repository validation and configuration backup before risky operations
  - Implement exclusive locking for repository operations to prevent concurrent modification
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 10.1, 10.6_

- [x] 1.2 Add existing repository detection and handling
  - Implement detect_existing_repository method with metadata extraction
  - Add connect_to_existing_repository with credential prompting
  - Create reinitialize_repository with explicit "DELETE ALL DATA" confirmation
  - Add detailed data loss warnings with repository size and modification date
  - _Requirements: 1.4, 1.5, 1.6, 10.3, 10.4_

- [x] 1.3 Implement repository state management
  - Create RepositoryStateManager for controlled state transitions
  - Add audit logging for all state changes with correlation IDs
  - Implement repository status tracking (active, inactive, error, validating)
  - _Requirements: 10.5, 10.6_

- [ ]* 1.4 Write unit tests for RepositoryManager
  - Test CRUD operations with various repository configurations
  - Test existing repository detection and handling scenarios
  - Test state management and audit logging functionality
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] 2. Enhance Repository Configuration and Validation
  - Extend current RepositoryConfig with new fields for engine selection and metadata
  - Enhance ValidationService with comprehensive repository URI and configuration validation
  - Add performance monitoring and threshold checking for desktop usage
  - Implement configuration backup and recovery mechanisms
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.7_

- [x] 2.1 Extend RepositoryConfig data model
  - Add engine field for backup engine selection (restic, rsync, rclone)
  - Add metadata field for repository descriptions and custom properties
  - Add engine_config field for engine-specific configuration
  - Add status and validation tracking fields
  - _Requirements: 4.1, 4.2, 6.1, 6.2_

- [x] 2.2 Enhance ValidationService for repositories
  - Add comprehensive repository URI validation for all supported schemes
  - Implement configuration validation with detailed error messages
  - Add connectivity testing with timeout handling for network repositories
  - Add performance threshold validation (15s network, 3s local)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 9.2, 9.3, 9.5_

- [x] 2.3 Implement configuration backup manager
  - Create ConfigurationBackupManager for automatic backups before risky operations
  - Implement backup cleanup (keep last 5 backups per repository)
  - Add configuration restoration from backup functionality
  - _Requirements: 10.1, 10.2, 10.7_

- [ ]* 2.4 Write unit tests for enhanced configuration
  - Test RepositoryConfig extensions and validation
  - Test ValidationService repository validation methods
  - Test configuration backup and recovery functionality
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Implement Plugin Architecture for Backup Engines
  - Create plugin registry system for extensible backup engine support
  - Implement BackupEnginePlugin interface for consistent engine operations
  - Add built-in engine plugins for Restic, Rsync, and Rclone
  - Integrate plugin system with repository creation and management
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 3.1 Create plugin registry and interface
  - Implement PluginRegistry for backup engine discovery and management
  - Create BackupEnginePlugin abstract interface with required methods
  - Add plugin validation and feature capability reporting
  - _Requirements: 4.1, 4.2, 4.4, 4.5_

- [x] 3.2 Implement built-in engine plugins
  - Create ResticEnginePlugin wrapping existing Restic functionality
  - Implement RsyncEnginePlugin for simple file synchronization
  - Add RcloneEnginePlugin for cloud storage synchronization
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 3.3 Integrate plugins with repository management
  - Update RepositoryFactory to use plugin system for engine selection
  - Add engine availability checking during repository creation
  - Implement engine-specific configuration validation
  - _Requirements: 4.1, 4.2, 4.4, 4.5_

- [ ]* 3.4 Write unit tests for plugin architecture
  - Test plugin registry and engine discovery
  - Test built-in engine plugins functionality
  - Test plugin integration with repository operations
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4. Enhance Repository Credential Management
  - Integrate repository management with Security Services for per-repository credentials
  - Implement credential resolution order (stored, environment, interactive)
  - Add credential rotation support without repository re-initialization
  - Enhance S3-compatible service configuration with custom endpoints
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 4.1 Integrate with Security Services
  - Update RepositoryCredentialManager to use Security Services as backend
  - Implement per-repository credential storage using repository identifiers as keys
  - Add credential resolution with fallback to environment variables and interactive prompts
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 4.2 Implement credential rotation
  - Add rotate_credentials method supporting password and key updates
  - Ensure credential rotation works without repository re-initialization
  - Add audit logging for all credential operations
  - _Requirements: 8.4, 8.5_

- [x] 4.3 Enhance S3-compatible service support
  - Add S3Config data model with endpoint, region, and TLS configuration
  - Implement support for MinIO, Wasabi, Backblaze B2, and DigitalOcean Spaces
  - Add custom endpoint specification with protocol validation
  - Add TLS verification options with appropriate warnings for insecure connections
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ]* 4.4 Write unit tests for credential management
  - Test Security Services integration for credential storage
  - Test credential resolution order and rotation functionality
  - Test S3-compatible service configuration and validation
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 5. Implement Named Repository Management
  - Add repository alias system for human-friendly names
  - Implement default repository selection and management
  - Add repository metadata and description support
  - Enhance repository listing with status and usage information
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 5.1 Implement repository alias system
  - Add named repository support with URI mapping
  - Implement repository name validation and uniqueness checking
  - Add automatic repository type detection from URI patterns
  - _Requirements: 6.1, 6.4, 6.5_

- [x] 5.2 Add default repository management
  - Implement set_default_repository and get_default_repository methods
  - Update CLI commands to use default repository when none specified
  - Add default repository indication in repository listings
  - _Requirements: 6.3_

- [x] 5.3 Enhance repository metadata support
  - Add description and custom metadata fields to repository configuration
  - Implement metadata persistence in structured format
  - Add metadata display in repository listings and details
  - _Requirements: 6.2, 6.5_

- [ ]* 5.4 Write unit tests for named repository management
  - Test repository alias system and name validation
  - Test default repository selection and management
  - Test metadata storage and retrieval functionality
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6. Implement Performance Monitoring and Desktop Optimization
  - Add performance monitoring for repository operations with desktop-appropriate thresholds
  - Implement concurrent operation management (up to 3 parallel validations)
  - Add caching for repository metadata and status information
  - Optimize for desktop usage (up to 20 repositories, <2s listing, responsive operations)
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 6.1 Create performance monitoring system
  - Implement RepositoryPerformanceMonitor with operation tracking
  - Add performance threshold checking (15s network validation, 3s local validation, 2s listing)
  - Implement performance warnings with specific suggestions for improvements
  - _Requirements: 9.2, 9.3, 9.5_

- [x] 6.2 Add concurrent operation management
  - Implement RepositoryConcurrencyManager with semaphore-based limiting
  - Add exclusive locking for repository operations to prevent conflicts
  - Support up to 3 parallel validation operations for desktop usage
  - _Requirements: 9.3_

- [x] 6.3 Implement caching and optimization
  - Add repository metadata caching with TTL for frequently accessed data
  - Implement lazy loading for repository details to minimize startup time
  - Optimize repository listing for responsive performance (<2s for typical desktop usage)
  - _Requirements: 9.1, 9.4_

- [ ]* 6.4 Write unit tests for performance monitoring
  - Test performance monitoring and threshold checking
  - Test concurrent operation management and locking
  - Test caching effectiveness and optimization features
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 7. Enhance CLI Repository Commands
  - Extend existing repository CLI commands with new functionality
  - Add repository creation with existing repository detection and handling
  - Implement repository validation commands with detailed reporting
  - Add repository management commands for metadata and configuration updates
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 7.1 Enhance repository creation commands
  - Update repos add command with existing repository detection
  - Add interactive prompts for connection vs re-initialization choices
  - Implement engine selection during repository creation
  - Add comprehensive error handling with user-friendly messages
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 4.1, 4.2_

- [ ] 7.2 Add repository validation commands
  - Implement repos validate command for connectivity and integrity checking
  - Add repos validate-all command for batch validation with progress reporting
  - Include performance metrics and recommendations in validation output
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 7.3 Enhance repository management commands
  - Update repos show command with detailed status and metadata display
  - Add repos update command for configuration and metadata changes
  - Enhance repos list command with status indicators and performance information
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 7.4 Write integration tests for CLI commands
  - Test enhanced repository creation with existing repository handling
  - Test validation commands with various repository states
  - Test repository management commands with metadata and configuration updates
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 8. Implement Configuration Integration and Backup Support
  - Integrate repository configurations with TimeLocker configuration backup system
  - Add cross-platform compatibility for repository URIs and paths
  - Implement configuration restoration and migration support
  - Add security considerations for credential exclusion from backups
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 8.1 Integrate with Configuration Management
  - Update configuration backup to include repository configurations by default
  - Implement secure credential exclusion from configuration backups
  - Add structured configuration format for cross-platform compatibility
  - _Requirements: 11.1, 11.2, 11.4_

- [ ] 8.2 Add cross-platform compatibility
  - Implement platform-specific path handling for repository URIs
  - Add platform-specific credential store integration through Security Services
  - Ensure consistent repository operations across Windows, macOS, and Linux
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 8.3 Implement configuration restoration
  - Add configuration compatibility validation during restoration
  - Implement credential re-entry prompts during configuration restoration
  - Add optional exclusion of TimeLocker configuration from backups
  - _Requirements: 11.3, 11.5, 12.5_

- [ ]* 8.4 Write integration tests for configuration support
  - Test configuration backup inclusion and credential exclusion
  - Test cross-platform compatibility for repository operations
  - Test configuration restoration with credential re-entry
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 9. Integration and End-to-End Testing
  - Create comprehensive integration tests for repository lifecycle management
  - Test multi-backend repository management scenarios
  - Validate performance requirements under desktop usage conditions
  - Test error handling and recovery scenarios
  - _Requirements: All requirements validation_

- [ ] 9.1 Create repository lifecycle integration tests
  - Test complete repository lifecycle: create → validate → use → update → delete
  - Test existing repository detection and handling workflows
  - Test repository state management and audit logging
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [ ] 9.2 Test multi-backend scenarios
  - Test repository management across local, S3, and B2 backends
  - Test credential management for different storage backends
  - Test plugin system with multiple backup engines
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 9.3 Validate performance requirements
  - Test desktop scalability (20+ repositories, concurrent operations)
  - Validate performance thresholds (15s network, 3s local, 2s listing)
  - Test concurrent validation limits (3 parallel operations)
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 9.4 Test error handling and recovery
  - Test network failure scenarios and timeout handling
  - Test credential error recovery and fallback mechanisms
  - Test configuration corruption detection and recovery
  - _Requirements: All error handling requirements_