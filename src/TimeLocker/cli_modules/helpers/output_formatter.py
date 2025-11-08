"""
Output formatting utilities for CLI commands.

This module provides consistent output formatting for both human-readable
and machine-readable (JSON) output formats, supporting the requirements
for comprehensive JSON output and non-interactive mode.
"""

import json
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class OutputFormat(Enum):
    """Supported output formats."""
    HUMAN = "human"
    JSON = "json"


class ExitCode(Enum):
    """Standard exit codes for CLI commands."""
    SUCCESS = 0
    WARNING = 1
    ERROR = 2
    VALIDATION_ERROR = 2
    OPERATION_ERROR = 1
    CANCELLED = 130


class OutputFormatter:
    """
    Handles output formatting for CLI commands.
    
    Provides consistent formatting for both human-readable (Rich panels/tables)
    and machine-readable (JSON) output formats.
    """
    
    def __init__(
        self,
        format: OutputFormat = OutputFormat.HUMAN,
        quiet: bool = False,
        console: Optional[Console] = None
    ):
        """
        Initialize output formatter.
        
        Args:
            format: Output format (human or json)
            quiet: Suppress human-readable output (only essential data)
            console: Rich console instance (created if not provided)
        """
        self.format = format
        self.quiet = quiet
        self.console = console or Console()
        self._json_buffer: List[Dict[str, Any]] = []
    
    def is_json_mode(self) -> bool:
        """Check if JSON output mode is active."""
        return self.format == OutputFormat.JSON
    
    def is_quiet_mode(self) -> bool:
        """Check if quiet mode is active."""
        return self.quiet
    
    def success(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        title: str = "Success",
        command: Optional[str] = None
    ) -> None:
        """
        Output a success message.
        
        Args:
            message: Success message
            data: Optional data to include
            title: Title for human-readable output
            command: Command name for JSON output
        """
        if self.is_json_mode():
            self._output_json(
                success=True,
                message=message,
                data=data,
                command=command
            )
        else:
            if not self.quiet:
                content = f"✅ {message}"
                if data:
                    content += "\n\n"
                    for key, value in data.items():
                        content += f"[bold]{key}:[/bold] {value}\n"
                
                panel = Panel(
                    content.strip(),
                    title=f"[bold green]{title}[/bold green]",
                    border_style="green",
                    padding=(1, 2)
                )
                self.console.print(panel)
    
    def error(
        self,
        message: str,
        details: Optional[List[str]] = None,
        error_type: str = "Error",
        title: str = "Error",
        command: Optional[str] = None,
        code: Optional[str] = None
    ) -> None:
        """
        Output an error message.
        
        Args:
            message: Error message
            details: Optional error details
            error_type: Type of error for JSON output
            title: Title for human-readable output
            command: Command name for JSON output
            code: Error code for JSON output
        """
        if self.is_json_mode():
            self._output_json(
                success=False,
                message=message,
                error_type=error_type,
                error_details=details,
                error_code=code,
                command=command
            )
        else:
            # Escape Rich markup in message
            safe_message = message.replace("[", "\\[").replace("]", "\\]")
            content = f"❌ {safe_message}"
            
            if details:
                content += "\n\n[bold]Details:[/bold]\n"
                for detail in details:
                    safe_detail = detail.replace("[", "\\[").replace("]", "\\]")
                    content += f"• {safe_detail}\n"
            
            panel = Panel(
                content.strip(),
                title=f"[bold red]{title}[/bold red]",
                border_style="red",
                padding=(1, 2),
                width=100
            )
            self.console.print(panel)
    
    def info(
        self,
        message: str,
        title: str = "Info",
        data: Optional[Dict[str, Any]] = None,
        command: Optional[str] = None
    ) -> None:
        """
        Output an informational message.
        
        Args:
            message: Info message
            title: Title for human-readable output
            data: Optional data to include
            command: Command name for JSON output
        """
        if self.is_json_mode():
            self._output_json(
                success=True,
                message=message,
                data=data,
                command=command
            )
        else:
            if not self.quiet:
                panel = Panel(
                    f"ℹ️  {message}",
                    title=f"[bold blue]{title}[/bold blue]",
                    border_style="blue",
                    padding=(1, 2)
                )
                self.console.print(panel)
    
    def warning(
        self,
        message: str,
        title: str = "Warning",
        command: Optional[str] = None
    ) -> None:
        """
        Output a warning message.
        
        Args:
            message: Warning message
            title: Title for human-readable output
            command: Command name for JSON output
        """
        if self.is_json_mode():
            self._output_json(
                success=True,
                message=message,
                warning=True,
                command=command
            )
        else:
            if not self.quiet:
                panel = Panel(
                    f"⚠️  {message}",
                    title=f"[bold yellow]{title}[/bold yellow]",
                    border_style="yellow",
                    padding=(1, 2)
                )
                self.console.print(panel)
    
    def table(
        self,
        data: List[Dict[str, Any]],
        title: Optional[str] = None,
        columns: Optional[List[str]] = None,
        command: Optional[str] = None
    ) -> None:
        """
        Output tabular data.
        
        Args:
            data: List of dictionaries representing rows
            title: Table title
            columns: Column names (auto-detected if not provided)
            command: Command name for JSON output
        """
        if self.is_json_mode():
            self._output_json(
                success=True,
                data={"items": data, "total_count": len(data)},
                command=command
            )
        else:
            if not self.quiet and data:
                # Auto-detect columns if not provided
                if columns is None and data:
                    columns = list(data[0].keys())
                
                table = Table(title=title)
                
                # Add columns
                for col in columns:
                    table.add_column(col.replace("_", " ").title(), style="cyan")
                
                # Add rows
                for row in data:
                    table.add_row(*[str(row.get(col, "")) for col in columns])
                
                self.console.print(table)
            elif self.is_json_mode():
                # In JSON mode, always output even if empty
                self._output_json(
                    success=True,
                    data={"items": [], "total_count": 0},
                    command=command
                )
    
    def data(
        self,
        data: Any,
        message: Optional[str] = None,
        command: Optional[str] = None
    ) -> None:
        """
        Output raw data.
        
        Args:
            data: Data to output
            message: Optional message
            command: Command name for JSON output
        """
        if self.is_json_mode():
            self._output_json(
                success=True,
                message=message,
                data=data,
                command=command
            )
        else:
            if not self.quiet:
                if message:
                    self.console.print(f"[bold]{message}[/bold]")
                self.console.print(data)
    
    def _output_json(
        self,
        success: bool,
        message: Optional[str] = None,
        data: Optional[Any] = None,
        error_type: Optional[str] = None,
        error_details: Optional[List[str]] = None,
        error_code: Optional[str] = None,
        command: Optional[str] = None,
        warning: bool = False
    ) -> None:
        """
        Output JSON formatted response.
        
        Args:
            success: Whether operation was successful
            message: Response message
            data: Response data
            error_type: Type of error (if applicable)
            error_details: Error details (if applicable)
            error_code: Error code (if applicable)
            command: Command that generated this output
            warning: Whether this is a warning
        """
        response: Dict[str, Any] = {
            "success": success,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if command:
            response["command"] = command
        
        if message:
            response["message"] = message
        
        if warning:
            response["warning"] = True
        
        if data is not None:
            response["data"] = self._serialize_data(data)
        
        if not success:
            error_info: Dict[str, Any] = {}
            if error_type:
                error_info["type"] = error_type
            if message:
                error_info["message"] = message
            if error_details:
                error_info["details"] = error_details
            if error_code:
                error_info["code"] = error_code
            response["error"] = error_info
        
        # Output to stdout
        print(json.dumps(response, indent=2, default=str))
    
    def _serialize_data(self, data: Any) -> Any:
        """
        Serialize data for JSON output.
        
        Handles Path objects, datetime objects, and other non-JSON types.
        
        Args:
            data: Data to serialize
            
        Returns:
            JSON-serializable data
        """
        if isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif isinstance(data, Path):
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._serialize_data(item) for item in data]
        elif isinstance(data, Enum):
            return data.value
        elif hasattr(data, "to_dict"):
            return self._serialize_data(data.to_dict())
        elif hasattr(data, "__dict__"):
            return self._serialize_data(data.__dict__)
        else:
            return str(data)


def create_formatter(
    json_output: bool = False,
    quiet: bool = False,
    console: Optional[Console] = None
) -> OutputFormatter:
    """
    Create an output formatter based on command options.
    
    Args:
        json_output: Whether to use JSON output format
        quiet: Whether to suppress non-essential output
        console: Rich console instance
        
    Returns:
        Configured OutputFormatter instance
    """
    format = OutputFormat.JSON if json_output else OutputFormat.HUMAN
    return OutputFormatter(format=format, quiet=quiet, console=console)


# Convenience functions for backward compatibility
def format_success_json(
    message: str,
    data: Optional[Dict[str, Any]] = None,
    command: Optional[str] = None
) -> str:
    """Format a success response as JSON string."""
    response = {
        "success": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": message
    }
    if command:
        response["command"] = command
    if data:
        response["data"] = data
    return json.dumps(response, indent=2, default=str)


def format_error_json(
    message: str,
    error_type: str = "Error",
    details: Optional[List[str]] = None,
    code: Optional[str] = None,
    command: Optional[str] = None
) -> str:
    """Format an error response as JSON string."""
    response = {
        "success": False,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error": {
            "type": error_type,
            "message": message
        }
    }
    if command:
        response["command"] = command
    if details:
        response["error"]["details"] = details
    if code:
        response["error"]["code"] = code
    return json.dumps(response, indent=2, default=str)


__all__ = [
    "OutputFormatter",
    "OutputFormat",
    "ExitCode",
    "create_formatter",
    "format_success_json",
    "format_error_json",
]
