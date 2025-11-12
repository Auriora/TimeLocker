"""
Centralized output formatting service for CLI operations.

This module provides a unified interface for output formatting with consistent
styling, JSON output support, and reusable templates for common patterns.

Requirements addressed:
- Requirement 5: Standardized output formatting through OutputFormatter
- 5.1: Provide standardized formatting for tables, panels, JSON, and error messages
- 5.2: Apply consistent styling and formatting rules
- 5.3: Support JSON output mode for all formatted data structures
- 5.4: Reduce output formatting code by at least 70 lines across 35 commands
- 5.5: Gracefully degrade to plain text output on formatting failures
"""

import json
import logging
import sys
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.markup import escape

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Output format types."""
    RICH = "rich"  # Rich formatted output with colors and styling
    JSON = "json"  # JSON formatted output
    PLAIN = "plain"  # Plain text output


class OutputFormatter:
    """
    Centralized service for output formatting with consistent behavior.
    
    This service provides a unified interface for all CLI output, handling:
    - Table formatting with consistent styling
    - Panel creation for messages and information
    - JSON output for machine-readable data
    - Error message formatting
    - Graceful degradation to plain text
    
    Requirements addressed:
    - 5.1: Standardized formatting for tables, panels, JSON, and error messages
    - 5.2: Consistent styling and formatting rules
    - 5.3: JSON output support
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        output_format: OutputFormat = OutputFormat.RICH,
        json_indent: int = 2
    ):
        """
        Initialize the output formatter.
        
        Args:
            console: Optional Rich console instance. If None, creates a new one.
            output_format: Output format to use (RICH, JSON, or PLAIN)
            json_indent: Indentation level for JSON output
        """
        self._console = console or Console(width=100)
        self._output_format = output_format
        self._json_indent = json_indent
        logger.debug(f"OutputFormatter initialized with format: {output_format.value}")
    
    def set_format(self, output_format: OutputFormat) -> None:
        """
        Set the output format.
        
        Args:
            output_format: Output format to use
        """
        self._output_format = output_format
        logger.debug(f"Output format changed to: {output_format.value}")
    
    def get_format(self) -> OutputFormat:
        """
        Get the current output format.
        
        Returns:
            Current output format
        """
        return self._output_format
    
    def format_table(
        self,
        data: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
        title: Optional[str] = None,
        show_header: bool = True,
        show_lines: bool = False
    ) -> None:
        """
        Format and display data as a table.
        
        Args:
            data: List of dictionaries containing row data
            columns: Optional list of column names to display (in order).
                    If None, uses all keys from first row.
            title: Optional table title
            show_header: Whether to show column headers
            show_lines: Whether to show lines between rows
            
        Requirements addressed:
        - 5.1: Standardized table formatting
        - 5.2: Consistent styling
        - 5.3: JSON output support
        """
        if not data:
            if self._output_format == OutputFormat.JSON:
                self._print_json([])
            else:
                self._console.print("[dim]No data to display[/dim]")
            return
        
        try:
            if self._output_format == OutputFormat.JSON:
                # JSON output - filter columns if specified
                if columns:
                    filtered_data = [
                        {k: row.get(k) for k in columns if k in row}
                        for row in data
                    ]
                    self._print_json(filtered_data)
                else:
                    self._print_json(data)
                return
            
            # Determine columns to display
            if columns is None:
                columns = list(data[0].keys())
            
            # Create Rich table
            table = Table(
                title=title,
                show_header=show_header,
                show_lines=show_lines,
                header_style="bold cyan"
            )
            
            # Add columns
            for col in columns:
                table.add_column(col, style="white")
            
            # Add rows
            for row in data:
                table.add_row(*[str(row.get(col, "")) for col in columns])
            
            self._console.print(table)
            
        except Exception as e:
            logger.error(f"Failed to format table: {e}")
            # Graceful degradation to plain text
            self._format_table_plain(data, columns, title)
    
    def _format_table_plain(
        self,
        data: List[Dict[str, Any]],
        columns: Optional[List[str]],
        title: Optional[str]
    ) -> None:
        """
        Format table as plain text (fallback).
        
        Args:
            data: List of dictionaries containing row data
            columns: Optional list of column names
            title: Optional table title
        """
        if title:
            print(f"\n{title}")
            print("=" * len(title))
        
        if not data:
            print("No data to display")
            return
        
        if columns is None:
            columns = list(data[0].keys())
        
        # Calculate column widths
        widths = {col: len(col) for col in columns}
        for row in data:
            for col in columns:
                widths[col] = max(widths[col], len(str(row.get(col, ""))))
        
        # Print header
        header = " | ".join(col.ljust(widths[col]) for col in columns)
        print(header)
        print("-" * len(header))
        
        # Print rows
        for row in data:
            print(" | ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns))
        print()
    
    def format_panel(
        self,
        content: str,
        title: Optional[str] = None,
        style: str = "white",
        border_style: str = "blue",
        expand: bool = False
    ) -> None:
        """
        Format and display content in a panel.
        
        Args:
            content: Content to display in the panel
            title: Optional panel title
            style: Content text style
            border_style: Border color/style
            expand: Whether to expand panel to full width
            
        Requirements addressed:
        - 5.1: Standardized panel formatting
        - 5.2: Consistent styling
        """
        try:
            if self._output_format == OutputFormat.JSON:
                # JSON output for panels
                self._print_json({
                    "type": "panel",
                    "title": title,
                    "content": content
                })
                return
            
            if self._output_format == OutputFormat.PLAIN:
                # Plain text output
                if title:
                    print(f"\n{title}")
                    print("=" * len(title))
                print(content)
                print()
                return
            
            # Rich panel
            panel = Panel(
                content,
                title=f"[bold {border_style}]{title}[/bold {border_style}]" if title else None,
                style=style,
                border_style=border_style,
                expand=expand
            )
            self._console.print(panel)
            
        except Exception as e:
            logger.error(f"Failed to format panel: {e}")
            # Graceful degradation
            if title:
                print(f"\n{title}")
                print("=" * len(title))
            print(content)
            print()
    
    def format_success(
        self,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Format and display a success message.
        
        Args:
            title: Success message title
            message: Success message content
            details: Optional additional details to display
            
        Requirements addressed:
        - 5.1: Standardized success message formatting
        - 5.2: Consistent styling
        """
        try:
            if self._output_format == OutputFormat.JSON:
                self._print_json({
                    "status": "success",
                    "title": title,
                    "message": message,
                    "details": details or {}
                })
                return
            
            content = f"✅ {message}"
            if details:
                content += "\n\n"
                for key, value in details.items():
                    content += f"[bold]{key}:[/bold] {value}\n"
            
            self.format_panel(
                content.strip(),
                title=title,
                style="green",
                border_style="green"
            )
            
        except Exception as e:
            logger.error(f"Failed to format success message: {e}")
            print(f"✅ {title}: {message}")
            if details:
                for key, value in details.items():
                    print(f"  {key}: {value}")
    
    def format_error(
        self,
        title: str,
        message: str,
        details: Optional[List[str]] = None,
        exception: Optional[Exception] = None
    ) -> None:
        """
        Format and display an error message.
        
        Args:
            title: Error message title
            message: Error message content
            details: Optional list of error details
            exception: Optional exception object
            
        Requirements addressed:
        - 5.1: Standardized error message formatting
        - 5.2: Consistent styling
        """
        try:
            if self._output_format == OutputFormat.JSON:
                error_data = {
                    "status": "error",
                    "title": title,
                    "message": message,
                    "details": details or []
                }
                if exception:
                    error_data["exception"] = {
                        "type": type(exception).__name__,
                        "message": str(exception)
                    }
                self._print_json(error_data)
                return
            
            # Escape Rich markup in message to prevent markup errors
            safe_message = escape(message)
            content = f"❌ {safe_message}"
            
            if details:
                content += "\n\n[bold]Details:[/bold]\n"
                for detail in details:
                    safe_detail = escape(str(detail))
                    content += f"• {safe_detail}\n"
            
            if exception and logger.isEnabledFor(logging.DEBUG):
                content += f"\n[dim]Exception: {type(exception).__name__}: {exception}[/dim]"
            
            self.format_panel(
                content.strip(),
                title=title,
                style="red",
                border_style="red"
            )
            
        except Exception as e:
            logger.error(f"Failed to format error message: {e}")
            print(f"❌ {title}: {message}", file=sys.stderr)
            if details:
                for detail in details:
                    print(f"  • {detail}", file=sys.stderr)
    
    def format_warning(
        self,
        title: str,
        message: str,
        details: Optional[List[str]] = None
    ) -> None:
        """
        Format and display a warning message.
        
        Args:
            title: Warning message title
            message: Warning message content
            details: Optional list of warning details
            
        Requirements addressed:
        - 5.1: Standardized warning message formatting
        - 5.2: Consistent styling
        """
        try:
            if self._output_format == OutputFormat.JSON:
                self._print_json({
                    "status": "warning",
                    "title": title,
                    "message": message,
                    "details": details or []
                })
                return
            
            content = f"⚠️  {message}"
            if details:
                content += "\n\n[bold]Details:[/bold]\n"
                for detail in details:
                    content += f"• {detail}\n"
            
            self.format_panel(
                content.strip(),
                title=title,
                style="yellow",
                border_style="yellow"
            )
            
        except Exception as e:
            logger.error(f"Failed to format warning message: {e}")
            print(f"⚠️  {title}: {message}")
            if details:
                for detail in details:
                    print(f"  • {detail}")
    
    def format_info(
        self,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Format and display an info message.
        
        Args:
            title: Info message title
            message: Info message content
            details: Optional additional details to display
            
        Requirements addressed:
        - 5.1: Standardized info message formatting
        - 5.2: Consistent styling
        """
        try:
            if self._output_format == OutputFormat.JSON:
                self._print_json({
                    "status": "info",
                    "title": title,
                    "message": message,
                    "details": details or {}
                })
                return
            
            content = f"ℹ️  {message}"
            if details:
                content += "\n\n"
                for key, value in details.items():
                    content += f"[bold]{key}:[/bold] {value}\n"
            
            self.format_panel(
                content.strip(),
                title=title,
                style="blue",
                border_style="blue"
            )
            
        except Exception as e:
            logger.error(f"Failed to format info message: {e}")
            print(f"ℹ️  {title}: {message}")
            if details:
                for key, value in details.items():
                    print(f"  {key}: {value}")
    
    def format_tree(
        self,
        root_label: str,
        data: Dict[str, Any],
        guide_style: str = "blue"
    ) -> None:
        """
        Format and display hierarchical data as a tree.
        
        Args:
            root_label: Label for the root node
            data: Hierarchical data to display
            guide_style: Style for tree guide lines
            
        Requirements addressed:
        - 5.1: Standardized tree formatting
        - 5.2: Consistent styling
        """
        try:
            if self._output_format == OutputFormat.JSON:
                self._print_json({
                    "type": "tree",
                    "root": root_label,
                    "data": data
                })
                return
            
            if self._output_format == OutputFormat.PLAIN:
                # Plain text tree
                print(f"\n{root_label}")
                self._print_tree_plain(data, prefix="  ")
                return
            
            # Rich tree
            tree = Tree(root_label, guide_style=guide_style)
            self._build_tree(tree, data)
            self._console.print(tree)
            
        except Exception as e:
            logger.error(f"Failed to format tree: {e}")
            print(f"\n{root_label}")
            self._print_tree_plain(data, prefix="  ")
    
    def _build_tree(self, parent: Tree, data: Union[Dict, List, Any]) -> None:
        """
        Recursively build a Rich tree structure.
        
        Args:
            parent: Parent tree node
            data: Data to add to the tree
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    branch = parent.add(f"[cyan]{key}[/cyan]")
                    self._build_tree(branch, value)
                else:
                    parent.add(f"[cyan]{key}:[/cyan] {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    branch = parent.add(f"[dim]Item {i}[/dim]")
                    self._build_tree(branch, item)
                else:
                    parent.add(str(item))
        else:
            parent.add(str(data))
    
    def _print_tree_plain(self, data: Union[Dict, List, Any], prefix: str = "") -> None:
        """
        Print tree structure as plain text.
        
        Args:
            data: Data to print
            prefix: Indentation prefix
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    print(f"{prefix}{key}:")
                    self._print_tree_plain(value, prefix + "  ")
                else:
                    print(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    print(f"{prefix}Item {i}:")
                    self._print_tree_plain(item, prefix + "  ")
                else:
                    print(f"{prefix}{item}")
        else:
            print(f"{prefix}{data}")
    
    def format_json(self, data: Any) -> None:
        """
        Format and display data as JSON.
        
        Args:
            data: Data to format as JSON
            
        Requirements addressed:
        - 5.3: JSON output support
        """
        self._print_json(data)
    
    def _print_json(self, data: Any) -> None:
        """
        Print data as formatted JSON.
        
        Args:
            data: Data to print as JSON
        """
        try:
            json_str = json.dumps(data, indent=self._json_indent, default=str)
            print(json_str)
        except Exception as e:
            logger.error(f"Failed to format JSON: {e}")
            # Fallback to simple string representation
            print(str(data))
    
    def print(self, message: str, style: Optional[str] = None) -> None:
        """
        Print a simple message with optional styling.
        
        Args:
            message: Message to print
            style: Optional Rich style string
        """
        try:
            if self._output_format == OutputFormat.JSON:
                self._print_json({"message": message})
                return
            
            if self._output_format == OutputFormat.PLAIN or style is None:
                print(message)
                return
            
            self._console.print(message, style=style)
            
        except Exception as e:
            logger.error(f"Failed to print message: {e}")
            print(message)
    
    def print_separator(self, char: str = "─", length: Optional[int] = None) -> None:
        """
        Print a separator line.
        
        Args:
            char: Character to use for separator
            length: Length of separator (None for console width)
        """
        if self._output_format == OutputFormat.JSON:
            return  # Skip separators in JSON mode
        
        if length is None:
            length = self._console.width if self._output_format == OutputFormat.RICH else 80
        
        print(char * length)


# Singleton instance for convenience
_default_output_formatter: Optional[OutputFormatter] = None


def get_output_formatter(
    console: Optional[Console] = None,
    output_format: OutputFormat = OutputFormat.RICH
) -> OutputFormatter:
    """
    Get the default OutputFormatter instance.
    
    Args:
        console: Optional Rich console instance
        output_format: Output format to use
        
    Returns:
        OutputFormatter instance
    """
    global _default_output_formatter
    if _default_output_formatter is None:
        _default_output_formatter = OutputFormatter(
            console=console,
            output_format=output_format
        )
    return _default_output_formatter


__all__ = [
    'OutputFormatter',
    'OutputFormat',
    'get_output_formatter',
]
