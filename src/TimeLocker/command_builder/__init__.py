"""
Command Builder Package

This package provides utilities for building command-line commands with various parameter styles.
"""

from .core import (
    ParameterStyle,
    CommandParameter,
    CommandDefinition,
    CommandBuilder,
)

__all__ = [
    "ParameterStyle",
    "CommandParameter",
    "CommandDefinition",
    "CommandBuilder",
]