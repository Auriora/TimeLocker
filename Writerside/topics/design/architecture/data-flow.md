# Data Flow

The TimeLocker system processes data through the following sequence of operations:

1. **User** interacts with one of the interfaces (GUI, CLI, or REST API)
2. **Core Services** process the request and coordinate the necessary operations
3. **Infrastructure Layer** executes the operations using the Restic engine and manages resources
4. **Storage Backends** store or retrieve the backup data
5. **Monitoring & Reporting** tracks the operations and provides feedback to the user

This flow ensures that user requests are properly processed, executed, and monitored throughout the system, with appropriate feedback provided to the user.