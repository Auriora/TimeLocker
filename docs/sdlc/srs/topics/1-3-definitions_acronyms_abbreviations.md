# 1.3 Definitions, Acronyms, and Abbreviations

| Term                   | Definition                                                                                         |
|------------------------|----------------------------------------------------------------------------------------------------|
| **Snapshot**           | A point‑in‑time copy of selected files/folders stored in a repository.                             |
| **Repository**         | Storage location that contains backup snapshots and metadata.                                      |
| **Retention Policy**   | Rules governing how long snapshots are kept before pruning.                                        |
| **Pattern Group**      | A set of glob patterns defining inclusion/exclusion rules.                                         |
| **DBA**                | Desktop Backup Application (this product).                                                         |
| **Restic**             | Open‑source backup program used as underlying engine.                                              |
| **MTBF**               | Mean Time Between Failures.                                                                        |
| **Encryption**         | The process of converting data into a form that can only be read by authorized parties.            |
| **Backup Schedule**    | A predefined routine specifying when and how backups are automatically created.                    |
| **Pruning**            | The process of deleting old or unnecessary backup snapshots based on the retention policy.         |
| **Metadata**           | Data that describes other data, such as information about snapshots, file versions, and structure. |
| **Incremental Backup** | A backup that includes only the changes made since the last backup, reducing size and time.        |
| **Glob Patterns**      | Text patterns used to match file or folder names, often in inclusion/exclusion rules.              |
| **CLI**                | Command-Line Interface used to interact with software via text-based commands.                     |
| **Bare-Metal Recovery**| The process of restoring a complete system (operating system, files, etc.) after a critical failure.|
| **Audit Log**          | A record of events and system activities for tracking and verifying actions.                       |
| **Disaster Recovery**  | A process aimed at restoring system functionality after significant data loss or corruption.        |
| **Integrity Check**    | A method of ensuring consistency and correctness, often performed using `restic check`.            |
| **Retention Pruning**  | The deletion of older snapshots based on rules defined in a retention policy.                      |
| **GDPR**               | General Data Protection Regulation that governs personal data protection and privacy in the EU.    |
| **OWASP-ASVS**         | Open Web Application Security Project’s Application Security Verification Standard.                |
| **Audit Verify**       | A process by which the integrity and tamper resistance of backup audit logs are confirmed.         |
| **SRS**                | Software Requirements Specification document outlining project scope and requirements.              |
| **UX/UI**              | User Experience and User Interface design aspects of software.                                     |
| **Power User**         | A highly technical user who utilizes advanced features of the application.                         |
| **Everyday User**      | A typical user who interacts with the application for standard day-to-day functions.               |