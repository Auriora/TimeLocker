# TimeLocker Developer Guidelines

This document provides concise guidance for new developers working on the TimeLocker project.

## Project Overview

TimeLocker is a high-level Python interface for backup operations, primarily using the Restic backup tool. It simplifies backup operations through an object-oriented API that handles repository management, file selection patterns, and backup configurations across multiple storage backends.

## Tech Stack

- **Python 3.12+**: Core programming language
- **Restic**: Underlying backup tool
- **pytest**: Testing framework
- **boto3**: AWS SDK for S3 storage backend
- **b2sdk**: Backblaze B2 SDK for B2 storage backend
- **plantuml**: For generating UML diagrams

## Project Structure

```
.
├── src/                      # Source code
│   ├── TimeLocker/           # Main package
│   │   ├── command_builder/  # Command-line builder utilities
│   │   └── restic/           # Restic-specific implementations
│   ├── json2command_definition/ # JSON to command converter
│   └── man2json/             # Man page to JSON converter
├── tests/                    # Test suite
│   ├── TimeLocker/           # Tests for main package
│   ├── json2command_definition/ # Tests for JSON converter
│   └── man2json/             # Tests for man page converter
└── docs/                     # Documentation
```

## Development Workflow

### Setting Up Your Environment

1. Clone the repository
2. Install Python 3.12+
3. Install dependencies: `pip install -r requirements.txt`
4. Install Restic backup tool and ensure it's in your PATH

### Code Organization

- Follow the existing package structure
- Place new modules in the appropriate package
- Keep related functionality together
- Use abstract base classes for interfaces
- Implement concrete classes for specific backends

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/TimeLocker/backup/test_backup_manager.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src
```

### Executing Scripts

The project doesn't have standalone scripts. Instead, it provides a Python API for integration into other applications.

Example usage:
```python
from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection

# Initialize backup manager
manager = BackupManager()

# Create and use repository
repo = manager.from_uri("local:/path/to/repo", password="your-password")
```

## Best Practices

1. **Type Annotations**: Use Python type hints for all functions and methods
2. **Error Handling**: Use custom exceptions from the appropriate module
3. **Testing**: Write tests for all new functionality
4. **Documentation**: Document all public APIs with docstrings
5. **Code Style**: Follow PEP 8 guidelines
6. **Commits**: Write clear commit messages describing the changes

## Documentation

- Update documentation when changing APIs
- Keep the README.md up to date
- Use docstrings for all public functions and classes
- Refer to the docs/ directory for detailed documentation

## Development Process

TimeLocker follows an iterative and incremental development model with the following stages:

1. **Inception**: Requirements gathering and analysis
2. **Elaboration**: UX/UI design and technical design
3. **Construction**: Implementation and testing
4. **Transition**: Deployment and initial maintenance
5. **Operations**: Ongoing maintenance and improvement

Each stage may involve multiple iterations with feedback loops for refinement.

### Key Process Activities

- **Requirements Management**: Document and prioritize requirements using the prioritization matrix
- **Design Reviews**: Conduct design reviews before implementation
- **Code Reviews**: Follow the code review process for all changes
- **Testing**: Write tests for all new functionality and run existing tests
- **Documentation**: Update documentation when changing APIs or functionality

### Requirements Documentation

The Software Requirements Specification (SRS) in `docs/SDLC/SRS/` contains:

- Functional requirements for repository management, backup operations, security, etc.
- Non-functional requirements for performance, reliability, usability, etc.
- Use cases that describe specific user interactions with the system
- Compliance mappings for standards like GDPR, ASVS, and WCAG

Refer to the SRS when implementing new features to ensure compliance with requirements.

## Getting Help

- Check the README.md for basic information
- Refer to CONTRIBUTING.md for contribution guidelines
- See SUPPORT.md for getting help with issues
