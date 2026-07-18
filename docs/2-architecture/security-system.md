---
title: "Architecture Document: Security System"
id: "arch-security-system"
type: [ architecture ]
status: [ approved ]
owner: "Security Team"
last_reviewed: "13-11-2025"
tags: [architecture, security, credentials, encryption, access-control]
links:
    tooling: []
---

# Architecture Document: Security System

- **Owner**: Security Team
- **Status**: Approved
- **Created Date**: 13-11-2025
- **Last Updated**: 13-11-2025
- **Audience**: Engineering Teams, Security Engineers, Operations

## 1. Context

The Security System provides essential security controls for TimeLocker, implementing data encryption, secure credential management, and access protection
suitable for personal and small business desktop environments. The design emphasizes simplicity and user-friendliness while maintaining strong security
practices through platform-native security features and robust encryption.

The system leverages platform-specific credential stores (Windows Credential Manager, macOS Keychain, Linux Secret Service) and integrates with backup tool
encryption capabilities to provide defense-in-depth protection for backup data and credentials.

## 2. Architecture

### 2.1 Component Overview

The Security System consists of three primary subsystems:

1. **Credential Management**: Secure storage and retrieval of repository credentials
2. **Access Control**: User authentication, session management, and authorization
3. **Security Logging**: Audit trails and security event monitoring

### 2.2 Implementation Location

- **Base Directory**: `/src/TimeLocker/security/`
- **CLI Integration**: `/src/TimeLocker/cli_modules/commands/security.py`

### 2.3 Core Components

#### Security Service (`security_service.py`)

Central coordinator for all security operations providing unified interface:

- Authentication and authorization coordination
- Security session management
- Integration with backup operations
- Security event logging orchestration

**Key Methods**:

- `authenticate_user()` - User authentication
- `validate_session()` - Session validation
- `get_repository_credentials()` - Secure credential retrieval
- `authorize_operation()` - Operation authorization
- `log_security_event()` - Security event logging

#### Credential Manager (`credential_manager.py`)

Secure storage, retrieval, and management of repository credentials with per-repository isolation:

**Responsibilities**:

- Encrypt and store repository credentials
- Implement credential resolution precedence
- Integrate with platform credential stores
- Provide credential lifecycle management

**Key Methods**:

- `store_credentials()` - Store encrypted credentials
- `retrieve_credentials()` - Retrieve and decrypt credentials
- `remove_credentials()` - Secure credential deletion
- `list_stored_repositories()` - List repositories with stored credentials
- `validate_credentials()` - Test credential validity

**Storage Strategy**:

- Uses Fernet (AES-128 + HMAC-SHA256) for encryption
- Per-repository encryption keys derived from repository hash
- Platform keystore integration for master key storage
- XDG-compliant storage in `~/.config/timelocker/credentials/`

#### Access Manager (`access_manager.py`)

Handles user authentication, session management, and access control:

**Responsibilities**:

- Manage user sessions with configurable timeout
- Enforce file system permissions
- Provide user account isolation
- Handle authentication state

**Key Methods**:

- `create_session()` - Create authenticated session
- `validate_session()` - Validate session token
- `extend_session()` - Extend session timeout
- `terminate_session()` - End session
- `check_file_permissions()` - Verify file access rights

#### Security Logger (`security_logger.py`)

Records security events for troubleshooting and audit purposes:

**Responsibilities**:

- Log authentication and access events
- Provide log viewing and filtering interface
- Maintain log retention and cleanup
- Generate user notifications for security issues

**Key Methods**:

- `log_event()` - Record security event
- `get_events()` - Query events with filtering
- `cleanup_old_logs()` - Remove expired logs
- `export_logs()` - Export logs for analysis

#### Repository Protection (`repository_protection.py`)

Additional security layers for repository access:

- Repository encryption validation
- Access pattern monitoring
- Integrity verification
- Secure repository initialization

#### Data Privacy Manager (`data_privacy_manager.py`)

GDPR compliance and data privacy features:

- Data minimization controls
- User consent management
- Data retention policies
- Secure data deletion

### 2.4 Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security System                          │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Security        │  │ Credential     │  │ Access       │ │
│  │ Service         │  │ Manager        │  │ Manager      │ │
│  └─────────────────┘  └────────────────┘  └──────────────┘ │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Security        │  │ Repository     │  │ Data Privacy │ │
│  │ Logger          │  │ Protection     │  │ Manager      │ │
│  └─────────────────┘  └────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Platform Security Integration                  │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Windows         │  │ macOS          │  │ Linux        │ │
│  │ Credential Mgr  │  │ Keychain       │  │ Secret Svc   │ │
│  │ + DPAPI         │  │ Services       │  │ (libsecret)  │ │
│  └─────────────────┘  └────────────────┘  └──────────────┘ │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ NTFS ACLs       │  │ POSIX + XAttr  │  │ POSIX        │ │
│  │ File Perms      │  │ File Perms     │  │ + SELinux    │ │
│  └─────────────────┘  └────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Protected Resources                            │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Repository      │  │ Backup         │  │ Configuration│ │
│  │ Credentials     │  │ Data           │  │ Files        │ │
│  └─────────────────┘  └────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 3. Data Models

### Security Event

```python
@dataclass
class SecurityEvent:
    timestamp: datetime
    event_type: SecurityEventType  # AUTH, ACCESS, CREDENTIAL, ERROR
    user_id: str
    repository_id: Optional[str]
    operation: str
    result: EventResult  # SUCCESS, FAILURE, DENIED
    details: Dict[str, Any]
    ip_address: Optional[str] = None
```

### User Session

```python
@dataclass
class Session:
    session_id: str
    user_id: str
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    is_active: bool
```

### Encrypted Credentials

```python
@dataclass
class EncryptedCredentials:
    repository_id: str
    encrypted_data: bytes
    encryption_key_id: str
    created_at: datetime
    last_modified: datetime
```

### Security Configuration

```python
@dataclass
class SecurityConfig:
    session_timeout_minutes: int = 30
    log_retention_days: int = 30
    max_failed_attempts: int = 3
    lockout_duration_minutes: int = 15
    enable_notifications: bool = True
    credential_store_path: str = "~/.config/timelocker/credentials"
```

## 4. Encryption Implementation

### Credential Encryption

**Algorithm**: Fernet (AES-128-CBC + HMAC-SHA256)

- Authenticated encryption for credentials
- Unique encryption keys per repository
- Master key stored in platform keystore
- PBKDF2 key derivation with salt

**Key Management**:

- Automatic key generation on first use
- Secure key storage using platform keystores
- Key rotation capability
- Key backup and recovery procedures

### Platform Integration

#### Windows

- **Credential Storage**: Windows Credential Manager
- **Additional Layer**: DPAPI for encryption
- **File Protection**: NTFS ACLs with user isolation
- **Logging**: Windows Event Log integration

#### macOS

- **Credential Storage**: Keychain Services
- **File Protection**: POSIX permissions + extended attributes
- **Logging**: Console.app integration
- **Compliance**: Sandbox-ready for App Store

#### Linux

- **Credential Storage**: Secret Service API (libsecret)
- **Fallback**: GNOME Keyring or KDE Wallet
- **File Protection**: POSIX permissions with proper umask
- **Logging**: systemd journal integration
- **Compliance**: SELinux/AppArmor policy support

## 5. Security Features

### Confirmation Dialogs (`confirmation_dialogs.py`)

Interactive security confirmations for sensitive operations:

- Repository deletion confirmation
- Credential modification confirmation
- Security setting changes
- Destructive operation warnings

### Security Configuration CLI (`security_configuration_cli.py`)

CLI interface for security settings:

- Session timeout configuration
- Log retention settings
- Notification preferences
- Credential store location

### Privacy CLI (`privacy_cli.py`)

GDPR compliance and privacy management:

- View stored personal data
- Export user data
- Delete personal data
- Consent management

## 6. Error Handling

### Error Hierarchy

```python
class SecurityError(Exception):
    """Base class for security-related errors"""

class AuthenticationError(SecurityError):
    """Authentication failed"""

class AuthorizationError(SecurityError):
    """Operation not authorized"""

class CredentialError(SecurityError):
    """Credential management error"""

class SessionError(SecurityError):
    """Session management error"""

class EncryptionError(SecurityError):
    """Encryption/decryption failed"""
```

### Error Recovery Strategies

1. **Authentication Errors**: Clear user prompts with retry
2. **Credential Errors**: Fallback to interactive prompts
3. **Session Errors**: Automatic re-authentication
4. **Encryption Errors**: Secure failure with logging
5. **Platform Errors**: Graceful degradation to file-based fallback

## 7. Testing Strategy

### Unit Testing

- Credential encryption/decryption
- Session management and timeout
- File permission validation
- Event logging and retrieval
- Platform keystore integration (mocked)

### Integration Testing

- End-to-end authentication flow
- Credential resolution across sources
- Session management during operations
- Platform security integration
- Error propagation and handling

### Security Testing

- Encryption strength validation
- Key derivation testing
- Secure deletion verification
- Memory protection during operations
- Session hijacking prevention
- Privilege escalation prevention

## 8. Performance Considerations

### Credential Caching

- In-memory encrypted credential cache
- Configurable cache timeout (default 5 minutes)
- Automatic invalidation on changes
- Memory protection for cached data

### Session Management

- Lightweight session tokens
- Efficient session validation
- Automatic cleanup of expired sessions
- Minimal storage overhead

### Logging Efficiency

- Asynchronous log writing
- Batch log operations
- Efficient log rotation
- Indexed queries for UI display

## 9. Threat Model

### Desktop Environment Threats

1. **Malicious Software**: File system isolation and encryption
2. **Physical Access**: Session timeouts and credential protection
3. **User Account Compromise**: Strong encryption with platform keystore
4. **Accidental Exposure**: Clear separation and secure defaults

### Mitigation Strategies

- File system permissions for credential protection
- Session timeouts for unattended access
- Secure credential storage with encryption
- Clear separation of user data
- Audit logging for incident response

## 10. CLI Integration

Accessible through `security` command namespace:

```bash
# Manage credentials
timelocker credentials store <repository-id>
timelocker credentials show <repository-id>
timelocker credentials remove <repository-id>
timelocker credentials list

# Security configuration
timelocker security config --session-timeout 60
timelocker security config --log-retention 90

# Audit logs
timelocker security logs --last-week
timelocker security logs --export audit.json

# Privacy management
timelocker privacy export
timelocker privacy delete-all --confirm
```

## 11. Design Principles

- **Security First**: Strong encryption and secure defaults
- **User Friendly**: Simple interface with clear security prompts
- **Platform Native**: Leverage OS security features
- **Defense in Depth**: Multiple security layers
- **Privacy Aware**: GDPR compliance and data minimization
- **Audit Ready**: Comprehensive security event logging

## 12. Future Enhancements

### Advanced Authentication

- Multi-factor authentication (TOTP)
- Hardware token support (YubiKey)
- Biometric authentication
- Smart card integration

### Enhanced Monitoring

- Security dashboard with trends
- Anomaly detection
- Integration with SIEM systems
- Advanced threat detection

### Enterprise Features

- Centralized policy management
- Role-based access control (RBAC)
- Remote credential management
- Compliance reporting tools

## References

- [CLI Security Commands](../3-implementation/cli-modules.md)
- [Repository Management](../guides/user/repository-management-guide.md)
