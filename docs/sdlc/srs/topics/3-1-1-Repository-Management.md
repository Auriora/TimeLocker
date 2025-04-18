# 3.1.1 Repository Management

| ID            | Requirement                                                                                               | Priority    | Rationale                                                     |
|---------------|-----------------------------------------------------------------------------------------------------------|-------------|---------------------------------------------------------------|
| <a id="frRm001">**FR‑RM‑001**</a> | Support multiple repository types identified by *repo\_type* (local, SFTP, S3, SMB, etc.).                | Must‑have   | Core capability to address diverse storage back‑ends.         |
| <a id="frRm002">**FR‑RM‑002**</a> | Allow dynamic registration of repository implementations via plugin architecture.                         | Should‑have | Enables community extensions and future storage options.      |
| <a id="frRm003">**FR‑RM‑003**</a> | Provide UI to add, edit, and remove repositories with credential management.                              | Must‑have   | Essential for configuration and security.                     |
| <a id="frRm004">**FR‑RM‑004**</a> | Allow users to restrict repository region to EEA/UK and warn if chosen region is outside.                 | Should‑have | GDPR Ch. V international transfers.                           |
| <a id="frRm005">**FR‑RM‑005**</a> | Validate repository endpoint region at configuration and runtime; abort or warn according to user policy. | Must‑have   | Ensures ongoing compliance if bucket is moved or DNS changes. |