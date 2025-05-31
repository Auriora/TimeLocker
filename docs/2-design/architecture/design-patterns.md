# Design Patterns

## Creational Patterns

### Factory Method

- **Usage**: Create repository instances based on repository type
- **Benefits**: Encapsulates repository creation logic
- **Requirements**: FR-RM-001, FR-RM-002

### Builder

- **Usage**: Construct complex backup configurations
- **Benefits**: Separates construction from representation
- **Requirements**: FR-BK-001, FR-BK-002, FR-BK-003

## Structural Patterns

### Adapter

- **Usage**: Adapt Restic commands to TimeLocker operations
- **Benefits**: Allows integration with external tools
- **Requirements**: FR-BK-001, FR-BK-002, FR-BK-004

### Facade

- **Usage**: Simplify complex backup operations
- **Benefits**: Provides a unified interface
- **Requirements**: FR-BK-001, FR-BK-002, FR-BK-003, FR-BK-004

### Proxy

- **Usage**: Control access to repositories
- **Benefits**: Adds security and validation
- **Requirements**: FR-SEC-003, FR-SEC-004

## Behavioral Patterns

### Observer

- **Usage**: Notify users of backup events
- **Benefits**: Decouples event generation from handling
- **Requirements**: FR-MON-002

### Strategy

- **Usage**: Apply different backup strategies
- **Benefits**: Allows switching algorithms at runtime
- **Requirements**: FR-BK-001, FR-BK-002

### Command

- **Usage**: Encapsulate backup operations
- **Benefits**: Supports undo, queuing, and logging
- **Requirements**: FR-BK-001, FR-BK-002, FR-BK-003