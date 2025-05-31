# TimeLocker Roadmap

This document outlines the planned features and enhancements for future implementation in the TimeLocker backup management system.

## Feature Ideas

### Plug-in Architecture

- **Plug-in architecture for repository types**: Allow new repository types to be added through a plugin system
- **Plug-in architecture for backup target selection**: Enable extensible backup target selection through plugins
- **Plugin marketplace**: Create a central repository for community-developed plugins with ratings and reviews

### Backup Targets

#### Database Backup

- Database backup targets which can select which databases to dump before backup:
    - MySQL
    - PostgreSQL
    - MongoDB
    - Oracle
    - Microsoft SQL Server
    - SQLite
    - Other database systems

#### Container and Virtualization

- Backup target for containers, volumes, and images
- Backup target for full system backup
- Backup target for VM backup
- Backup target for VM disk backup with selective file recovery from disk images
- Bare-metal recovery capability for complete system restoration

#### System Configuration

- Backup target for system state backup:
    - Installed packages
    - Configuration settings
    - Systemd unit state
    - Mounts
    - Other system configuration
- Backup target for network device configurations (routers, switches, firewalls)

#### Application-Specific Backup

- Backup target for applications with unique data structures needing data export before backup:
    - Outlook email
    - Other applications with proprietary data formats

#### Cloud Services Backup

- Backup targets for cloud services:
    - Dropbox
    - Box
    - OneDrive
    - Google Drive
    - Google Workspace (Gmail, Docs, Sheets, etc.)
    - Microsoft 365 (Exchange Online, SharePoint, Teams)
    - Xero
    - Outlook.com
    - GitHub/GitLab repositories
    - Other cloud services

#### Mobile Device Backup

- Backup target for iOS devices (iPhone, iPad) using idevices library
- Backup target for Android devices
- Backup target for wearable devices (Apple Watch, Fitbit, etc.)

### Advanced Features

#### Intelligent Backup Management

- **Anomaly detection**: Identify unusual changes in backup size or content that might indicate ransomware or data corruption
- **Smart file selection recommendations**: Analyze file change frequency and usage patterns to suggest optimal backup selections

#### Enhanced Security

- **Zero-knowledge encryption**: Client-side encryption where only the user holds the encryption keys. (Note: Restic already supports this. Move this to the SRS
  document.)

#### Performance Optimization

- **Bandwidth throttling**: Intelligent bandwidth management based on network usage patterns
- **System resource throttling**: Dynamically adjust backup process resource usage based on system load to minimize impact during user activity and maximize
  speed when the system is idle

#### Extensibility and Integration

- **Pre/post scripts execution**: Run custom scripts before and after various stages of the backup process to enable custom actions and integrations
- **Filesystem snapshot integration**: Support backing up from filesystem snapshots on filesystems that support it (LVM, ZFS, Btrfs, etc.) for consistent
  point-in-time backups

## Implementation Priority

The implementation priority will be determined based on user needs and development resources. This roadmap will be updated as features are implemented or as
priorities change.

## Contributing Ideas

To suggest new feature ideas for the roadmap, please submit an issue or pull request with the details of your proposed feature.
