---
type:        "always_apply"
name:        "Coding Standards for AI-Generated Code"
priority:    100
scope:       "src/**"
description: "Mandatory coding standards and principles for all AI-generated or modified code."
cross_reference: []
apply_when:   "always"
---

# AI Agent Rule/Guide: Coding Standards for AI-Generated Code

- **Type**: always_apply
- **Priority**: 100
- **Scope**: src/**
- **Description**: Mandatory coding standards and principles for all AI-generated or modified code.
- **Cross-Reference**:
- **Apply When**: always

## 1. Purpose

This document outlines the mandatory coding standards and principles that all AI-generated or modified code in the `admin-assistant` project must adhere to. The
purpose is to ensure maintainability, clarity, quality, and consistency across the codebase, aligning with established software engineering best practices.

## 2. Rule/Guideline Details

### 2.1. General Principles

- **All classes must follow SOLID principles**: Ensure code is modular, extensible, and easy to maintain.
- **Accessibility**: Where applicable, ensure user-facing features are accessible.
- **Comprehensive documentation**: Every class, method, and function must include docstrings explaining its purpose, parameters, and return values.
- **Consistent naming conventions**: Use `snake_case` for variables and functions, `PascalCase` for classes, and `UPPER_CASE` for constants.
- **Documentation as code**: All code must be self-documenting and include comprehensive docstrings and comments where necessary.
- **Don't Repeat Yourself (DRY)**: Avoid code duplication by abstracting common functionality into reusable components, functions, and classes.
- **Error handling**: Implement robust error handling and logging. Avoid silent failures.
- **Extensibility**: Design code to be easily extended for future features.
- **No magic numbers or literals**: All such values must be defined as named constants with clear, descriptive names.
- **Performance awareness**: Write efficient code and avoid unnecessary computations or memory usage.
- **Prioritise Off-The-Shelf (OTS)**: Use established libraries and frameworks (like Flask, SQLAlchemy, etc.) rather than creating custom solutions when
  appropriate functionality already exists.
- **Security best practices**: Never log or expose sensitive information (e.g., credentials, tokens). Use environment variables for secrets.
- **Separation of concerns**: Keep business logic, data access, and presentation layers separate.
- **Single source of truth**: Avoid duplication of logic or configuration.
- **Testability**: Code should be written to facilitate unit and integration testing. Avoid hard-coded dependencies; use dependency injection where appropriate.
- **Type annotations**: All functions and methods must include type hints for parameters and return values.
- **Observability**: All new code must use OpenTelemetry for distributed tracing. Follow the guidelines in `docs/guidelines/logging.md` for best practices.

### 2.2. Exception Handling

- All exceptions must be handled explicitly and logged with context.
- Use custom exceptions and exception chaining (`from e`).
- Never mask, suppress, or silently swallow errors.
- Add context to exceptions as they propagate (use `add_note` where available).
- Handle exceptions at the appropriate layer (repository, service, orchestration) and always test error scenarios.

## 3. Examples

```python
# Example of a well-documented function with type hints and error handling
def calculate_total(price: float, quantity: int) -> float:
    """
    Calculates the total price for a given item.

    Args:
        price: The unit price of the item.
        quantity: The number of items.

    Returns:
        The total price.

    Raises:
        ValueError: If price or quantity are negative.
    """
    if price < 0 or quantity < 0:
        raise ValueError("Price and quantity must be non-negative.")
    return price * quantity

# Example of using a named constant instead of a magic number
MAX_RETRIES = 3
def fetch_data_with_retries(url: str) -> dict:
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                raise
    return {}
```

## 4. Rationale / Justification

Adherence to these coding standards is paramount for maintaining a high-quality, scalable, and secure codebase. Consistent application of these principles
reduces technical debt, improves collaboration, and facilitates easier debugging and feature development. For AI agents, these guidelines ensure that generated
code seamlessly integrates with existing project standards.

## 5. Related Information

- **SRS and Design Alignment**: All AI-generated code and documentation must align with the current Software Requirements Specification (SRS) in
  `docs/1-requirements/` and the design documentation in `docs/2-architecture/`. Any generated code must directly support and not contradict these authoritative
  documents.

# References

- [General Preferences](./AGENT-GUIDE-General-Preferences.md)
- [HLD: Observability Design](../../2-architecture/ARCH-002-Observability.md) (for logging best practices)
- `docs/1-requirements/` (for SRS documentation)
- `docs/2-architecture/` (for design documentation)