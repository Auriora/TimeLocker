# BackupManager Test Suite
Tags: backup, manager
Meta: component = TimeLocker, module = backup

## S1 Initialization Tests
* C1 Test initialization creates empty repository factories
Tags: init
    * Create a new BackupManager instance
    * Verify that _repository_factories is an empty dictionary

## S2 Sensitive Information Handling
* C1 Test redacting sensitive info from URL without username
Tags: security, redaction
    * Call redact_sensitive_info with a URL that has no username
    * Verify the URL is returned unchanged
* C2 Test redacting username and password from URL
Tags: security, redaction
    * Call redact_sensitive_info with a URL containing username and password
    * Verify the username and password are redacted in the returned URL

## S3 Repository Factory Management
* C1 Test getting nonexistent repository factory
Tags: factory
    * Call get_repository_factory with nonexistent name and type
    * Verify None is returned
* C2 Test getting nonexistent repository type from existing factory
Tags: factory
    * Register a repository factory
    * Call get_repository_factory with existing name but nonexistent type
    * Verify None is returned
* C3 Test registering a new repository factory
Tags: factory, registration
    * Register a new repository factory
    * Verify the factory is correctly stored in _repository_factories
    * Register another factory with the same name and type
    * Verify the factory is overwritten
* C4 Test warning when overwriting existing repository factory
Tags: factory, registration, warning
    * Register a repository factory
    * Register the same factory again
    * Verify a warning message is displayed

## S4 Backend Listing
* C1 Test listing registered backends and their types
Tags: backend, listing
    * Register multiple backends with different types
    * Call list_registered_backends
    * Verify the returned dictionary contains all registered backends and their types
* C2 Test listing backends when none are registered
Tags: backend, listing
    * Create a new BackupManager instance
    * Call list_registered_backends
    * Verify an empty dictionary is returned

## S5 Repository Creation
* C1 Test creating repository from supported URI scheme
Tags: uri, creation
    * Mock the repo_classes dictionary
    * Call from_uri with a supported URI scheme
    * Verify the correct repository type is created with the correct parameters
* C2 Test error when using unsupported URI scheme
Tags: uri, creation, error
    * Call from_uri with an unsupported URI scheme
    * Verify a BackupManagerError is raised with the correct message