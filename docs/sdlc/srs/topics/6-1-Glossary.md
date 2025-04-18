# 4.1 Glossary

| Term                       | Definition                                                                                                            |
|----------------------------|-----------------------------------------------------------------------------------------------------------------------|
| **AES-256**                | Advanced Encryption Standard with 256-bit key, a strong encryption algorithm.                                         |
| **ASVS**                   | Application Security Verification Standard.                                                                           |
| **At Rest**                | Data that is stored and not actively being used.                                                                      |
| **Audit Log**              | A record of events and system activities for tracking and verifying actions.                                          |
| **Audit Logs**             | A collection of records documenting system events and activities for security monitoring and compliance verification. |
| **Audit Trails**           | Chronological records of system activities that provide documentary evidence of operations.                           |
| **Audit Verify**           | A process by which the integrity and tamper resistance of backup audit logs are confirmed.                            |
| **Auditability**           | The quality of a system that allows its operations to be independently examined and verified.                         |
| **Auditing**               | The systematic recording and examination of system activities to ensure compliance and security.                      |
| **B2**                     | Backblaze B2 Cloud Storage, a cloud storage service.                                                                  |
| **Backup Operations**      | Activities related to creating, scheduling, and verifying backups.                                                    |
| **Backup Schedule**        | A predefined routine specifying when and how backups are automatically created.                                       |
| **Bandwidth Throttling**   | Limiting network bandwidth usage to control resource consumption.                                                     |
| **Bare-Metal Recovery**    | The process of restoring a complete system (operating system, files, etc.) after a critical failure.                  |
| **CAPTCHA**                | Completely Automated Public Turing test to tell Computers and Humans Apart.                                           |
| **CI/CD**                  | Continuous Integration/Continuous Deployment, automated software development practices.                               |
| **CLI**                    | Command-Line Interface used to interact with software via text-based commands.                                        |
| **Command-line Tools**     | Software utilities operated via text-based interfaces rather than graphical user interfaces.                          |
| **cron/systemd**           | Scheduling mechanisms in Linux used for automated tasks.                                                              |
| **Disaster Recovery**      | A process aimed at restoring system functionality after significant data loss or corruption.                          |
| **Encryption**             | The process of converting data into a form that can only be read by authorized parties.                               |
| **Everyday Users**         | Typical users who interact with the application for standard day-to-day functions.                                    |
| **FR/NFR**                 | Functional Requirements/Non-Functional Requirements.                                                                  |
| **GDPR**                   | General Data Protection Regulation that governs personal data protection and privacy in the EU.                       |
| **Glob Patterns**          | Text patterns used to match file or folder names, often in inclusion/exclusion rules.                                 |
| **HSTS**                   | HTTP Strict Transport Security, a web security policy mechanism.                                                      |
| **In Transit**             | Data that is being transmitted between systems.                                                                       |
| **Incremental Backup**     | A backup that includes only the changes made since the last backup, reducing size and time.                           |
| **Integrity**              | The assurance that data has not been altered or corrupted during storage or transmission.                             |
| **Integrity Check**        | A method of ensuring consistency and correctness, often performed using `restic check`.                               |
| **ISO/IEC 29148**          | A standard for requirements engineering in systems and software.                                                      |
| **JSON-RPC**               | A remote procedure call protocol encoded in JSON.                                                                     |
| **Metadata**               | Data that describes other data, such as information about snapshots, file versions, and structure.                    |
| **MTBF**                   | Mean Time Between Failures.                                                                                           |
| **NFS**                    | Network File System, a distributed file system protocol.                                                              |
| **OWASP-ASVS**             | Open Web Application Security Project's Application Security Verification Standard.                                   |
| **Pattern Group**          | A set of glob patterns defining inclusion/exclusion rules.                                                            |
| **point-in-time restores** | A recovery feature allowing restoration to a specific moment in time.                                                 |
| **Policy Enforcement**     | The automated application and monitoring of backup policies to ensure compliance with defined rules.                  |
| **Policy Management**      | The administration of rules governing backup retention, scheduling, and security.                                     |
| **Power Users**            | Highly technical users who utilize advanced features of the application.                                              |
| **Prune**                  | To remove outdated or unnecessary backup snapshots according to retention policies.                                   |
| **Pruning**                | The process of deleting old or unnecessary backup snapshots based on the retention policy.                            |
| **Repositories**           | Multiple storage locations that contain backup snapshots and metadata.                                                |
| **Repository**             | Storage location that contains backup snapshots and metadata.                                                         |
| **Repository Management**  | The process of creating, configuring, and maintaining backup storage locations.                                       |
| **REST API**               | Representational State Transfer Application Programming Interface.                                                    |
| **Restic**                 | Open-source backup program used as underlying engine.                                                                 |
| **Retention**              | The period of time for which backups are kept before being deleted.                                                   |
| **Retention Policy**       | Rules governing how long snapshots are kept before pruning.                                                           |
| **Retention Pruning**      | The deletion of older snapshots based on rules defined in a retention policy.                                         |
| **S3**                     | Amazon Simple Storage Service, a cloud storage platform.                                                              |
| **Scheduled Backups**      | Backups that are automatically executed according to a predefined schedule.                                           |
| **Scheduling Backups**     | The process of configuring automated backups to run at predetermined times.                                           |
| **Security**               | Measures taken to protect data from unauthorized access, corruption, or theft.                                        |
| **SFTP**                   | SSH File Transfer Protocol, a secure file transfer protocol.                                                          |
| **SMB**                    | Server Message Block, a network file sharing protocol.                                                                |
| **Snapshot**               | A point-in-time copy of selected files/folders stored in a repository.                                                |
| **SRS**                    | Software Requirements Specification document outlining project scope and requirements.                                |
| **TimeLocker**             | The name of the product being developed, a user-friendly backup application.                                          |
| **Usability**              | The ease with which users can learn and use a software application to achieve their goals.                            |
| **User-friendly Design**   | An approach to software design that prioritizes ease of use and intuitive interfaces.                                 |
| **Users**                  | Individuals who interact with the application, including everyday users and power users.                              |
| **UX/UI**                  | User Experience (UX) and User Interface (UI) design aspects of software.                                              |
| **Verification**           | The process of confirming that backups are complete, accurate, and restorable.                                        |
| **WCAG 2.2 AA**            | Web Content Accessibility Guidelines version 2.2, AA compliance level.                                                |