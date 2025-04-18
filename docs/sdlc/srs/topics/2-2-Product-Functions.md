# 2.2 Product Functions

The TimeLocker is a cross‑platform desktop application (initially Linux, with Windows and macOS support on the roadmap) that provides an intuitive interface for configuring, executing, monitoring, and restoring file‑system backups. The product **will**:

- Support multiple repository/storage back‑ends (local disk, external drive, SFTP, S3‑compatible object storage, network shares, etc.).
- Offer full, incremental, and scheduled backup operations using Restic as the core engine.
- Provide point‑in‑time and partial restore capabilities.
- Enforce backup policies (retention, frequency, prioritisation, life‑cycle).
- Implement encryption, and audit logging.

The product **will not**:

- Provide enterprise‑level centralised backup server functionality (future work).
- Replace native OS file‑history or snapshotting tools.

The main functions of the TimeLocker include:

1. **Repository Management** – create, register, edit, and delete backup repositories of various types.
2. **Backup Operations** – execute full/incremental backups manually or on schedule, with integrity validation.
3. **Recovery Operations** – browse snapshots and restore full or partial data to original or alternate locations.
4. **Policy Management** – define retention, frequency, tagging, and prioritisation rules.
5. **Security** – encryption, vault locking, secure credential storage.
6. **Monitoring & Reporting** – real‑time status, notifications, logs, audit reports, performance metrics.
7. **Error & Resource Management** – graceful handling of failures, retries, pruning, and cleanup.
8. **Integration** – CLI interface for scripting and orchestration.