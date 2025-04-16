# 3.1.1 Repository Management

| ID            | Requirement                                                                                               | Priority    | Rationale                                                     |
|---------------|-----------------------------------------------------------------------------------------------------------|-------------|---------------------------------------------------------------|
| **FR‑RM‑001** | Support multiple repository types identified by *repo\_type* (local, SFTP, S3, SMB, etc.).                | Must‑have   | Core capability to address diverse storage back‑ends.         |
| **FR‑RM‑002** | Allow dynamic registration of repository implementations via plugin architecture.                         | Should‑have | Enables community extensions and future storage options.      |
| **FR‑RM‑003** | Provide UI to add, edit, and remove repositories with credential management.                              | Must‑have   | Essential for configuration and security.                     |
| **FR‑RM‑004** | Allow users to restrict repository region to EEA/UK and warn if chosen region is outside.                 | Should‑have | GDPR Ch. V international transfers.                           |
| **FR‑RM‑005** | Validate repository endpoint region at configuration and runtime; abort or warn according to user policy. | Must‑have   | Ensures ongoing compliance if bucket is moved or DNS changes. |