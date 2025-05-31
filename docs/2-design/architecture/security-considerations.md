# Security Considerations

TimeLocker implements several security measures to ensure data protection and privacy:

- **Data Encryption**: All data is encrypted both in transit (TLS) and at rest (Restic encryption)
- **Credential Security**: Repository credentials are stored securely in the OS key-ring
- **Access Control**: Role-based access control with predefined roles
- **GDPR Compliance**: Features for data portability, right to erasure, and privacy by design
- **Audit Trail**: Tamper-proof audit logging with verification capabilities
- **Vault Locking**: Prevents concurrent conflicting writes to repositories

These security measures ensure that backup data remains protected throughout its lifecycle, from creation to storage to retrieval, while also complying with
relevant privacy regulations.