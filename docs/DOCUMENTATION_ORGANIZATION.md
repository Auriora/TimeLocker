# Documentation Organization Guidelines

## Introduction

This document outlines the best practices for organizing documentation in the TimeLocker project. It explains which documentation should be stored in the root directory and which should be stored in the `docs/` directory.

## Best Practices

### Root Directory Documentation

The root directory should contain high-level project documentation that users and contributors need immediate access to:

- **README.md**: The main entry point for project documentation, providing an overview, quick start guide, and links to more detailed documentation.
- **LICENSE**: The project's license file.
- **CONTRIBUTING.md**: Guidelines for contributing to the project.
- **CODE_OF_CONDUCT.md**: Code of conduct for the project community.
- **CHANGELOG.md**: Project changelog documenting notable changes in each version.
- **SECURITY.md**: Security policy and vulnerability reporting information.
- **SUPPORT.md**: Support information and how to get help.

These files are placed in the root directory because:
1. They are the first files that users and contributors look for when exploring a project.
2. GitHub and other platforms automatically recognize and provide links to these files when they are in the root directory.
3. They provide essential information needed before diving deeper into the project.

### Docs Directory Documentation

The `docs/` directory should contain more detailed documentation and resources:

- **Installation guides**: Detailed instructions for installing the project (e.g., `INSTALLATION.md`).
- **Component documentation**: Documentation for specific components (e.g., `command_builder.md`).
- **Technical documentation**: Detailed technical information about the project architecture and implementation.
- **User guides**: Comprehensive guides for using the project.
- **API documentation**: Documentation for APIs and interfaces.
- **Development documentation**: Information for developers working on the project (e.g., SDLC documentation).
- **Resources**: Images, diagrams, and other resources used in documentation.

These files are placed in the `docs/` directory because:
1. They contain more detailed information that not all users need immediately.
2. Organizing them in a separate directory keeps the root directory clean and focused.
3. It allows for a more structured organization with subdirectories for different types of documentation.

## Current Project Structure

The TimeLocker project follows these best practices with:

### Root Directory Documentation
- README.md
- LICENSE
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md
- CHANGELOG.md
- SECURITY.md
- SUPPORT.md

### Docs Directory Documentation
- INSTALLATION.md
- command_builder.md
- SDLC/ (Software Development Lifecycle documentation)
- compliance/ (Compliance documentation)
- resources/ (Documentation resources)

## Recommendations

1. **Maintain the current structure**: The current documentation organization follows best practices and should be maintained.
2. **New documentation**: 
   - Add high-level project documentation to the root directory.
   - Add detailed documentation, guides, and resources to the `docs/` directory.
3. **Linking**: Always use relative links to reference documentation files (e.g., `[Installation Guide](docs/INSTALLATION.md)`).

## Conclusion

Following these guidelines ensures that documentation is organized in a way that is both accessible to users and maintainable for contributors. The current structure of the TimeLocker project aligns well with these best practices.