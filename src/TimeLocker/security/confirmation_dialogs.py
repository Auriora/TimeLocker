"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import sys
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Confirm, Prompt
from rich import print as rprint

from .repository_protection import DestructiveOperation, RepositoryInfo

logger = logging.getLogger(__name__)


class ConfirmationError(Exception):
    """Base exception for confirmation dialog errors"""
    pass


class ConfirmationCancelledError(ConfirmationError):
    """Exception raised when user cancels confirmation"""
    pass


class ConfirmationDialogs:
    """
    Confirmation dialog system for TimeLocker destructive operations.
    
    Provides user-friendly confirmation dialogs with repository details
    and explicit confirmation requirements for destructive operations.
    """

    def __init__(self, console: Optional[Console] = None, 
                 interactive_check: Optional[Callable[[], bool]] = None):
        """
        Initialize confirmation dialogs
        
        Args:
            console: Rich console instance (optional)
            interactive_check: Function to check if running in interactive mode (optional)
        """
        self.console = console or Console()
        self.interactive_check = interactive_check or self._default_interactive_check

    def _default_interactive_check(self) -> bool:
        """Default interactive mode check"""
        return sys.stdin.isatty() and sys.stdout.isatty()

    def show_repository_details(self, repository_info: RepositoryInfo) -> None:
        """
        Display repository details in a formatted table
        
        Args:
            repository_info: Repository information to display
        """
        table = Table(title=f"Repository Details: {repository_info.name}")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        table.add_row("Name", repository_info.name)
        table.add_row("Location", repository_info.location)
        table.add_row("Mode", repository_info.mode.value.replace("_", " ").title())

        if repository_info.size_bytes is not None:
            size_str = self._format_size(repository_info.size_bytes)
            table.add_row("Size", size_str)

        if repository_info.snapshot_count is not None:
            table.add_row("Snapshots", str(repository_info.snapshot_count))

        if repository_info.last_backup is not None:
            last_backup_str = repository_info.last_backup.strftime("%Y-%m-%d %H:%M:%S")
            table.add_row("Last Backup", last_backup_str)

        if repository_info.created_at is not None:
            created_str = repository_info.created_at.strftime("%Y-%m-%d %H:%M:%S")
            table.add_row("Created", created_str)

        self.console.print(table)

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def show_destructive_operation_warning(self, operation: DestructiveOperation) -> None:
        """
        Display warning for destructive operation
        
        Args:
            operation: Destructive operation information
        """
        # Determine warning style based on level
        if operation.warning_level == "critical":
            style = "bold red"
            icon = "🚨"
            border_style = "red"
        elif operation.warning_level == "high":
            style = "bold yellow"
            icon = "⚠️"
            border_style = "yellow"
        else:
            style = "bold blue"
            icon = "ℹ️"
            border_style = "blue"

        # Create warning panel
        warning_text = Text()
        warning_text.append(f"{icon} WARNING: {operation.operation_type.upper()}\n\n", style=style)
        warning_text.append(operation.description, style="white")

        if operation.additional_info:
            warning_text.append("\n\nRepository Information:\n", style="bold white")
            for key, value in operation.additional_info.items():
                display_key = key.replace("_", " ").title()
                warning_text.append(f"• {display_key}: {value}\n", style="dim white")

        panel = Panel(
            warning_text,
            title="Destructive Operation Warning",
            border_style=border_style,
            padding=(1, 2)
        )

        self.console.print(panel)

    def confirm_destructive_operation(self, operation: DestructiveOperation,
                                    force: bool = False) -> bool:
        """
        Confirm destructive operation with explicit text confirmation
        
        Args:
            operation: Destructive operation to confirm
            force: Skip confirmation if True (for non-interactive mode)
            
        Returns:
            bool: True if operation is confirmed
            
        Raises:
            ConfirmationCancelledError: If user cancels confirmation
            ConfirmationError: If confirmation fails
        """
        try:
            # Skip confirmation if forced (non-interactive mode)
            if force:
                logger.info(f"Destructive operation confirmed via force flag: {operation.operation_type}")
                return True

            # Check if running in interactive mode
            if not self.interactive_check():
                raise ConfirmationError(
                    "Cannot confirm destructive operation in non-interactive mode. "
                    "Use --yes flag to force confirmation."
                )

            # Show repository details
            self.show_repository_details(operation.repository_info)
            self.console.print()

            # Show warning
            self.show_destructive_operation_warning(operation)
            self.console.print()

            # First confirmation: general yes/no
            initial_confirm = Confirm.ask(
                f"Do you want to proceed with this {operation.operation_type}?",
                default=False
            )

            if not initial_confirm:
                self.console.print("[yellow]Operation cancelled by user.[/yellow]")
                raise ConfirmationCancelledError("User cancelled operation")

            # Second confirmation: explicit text confirmation for critical operations
            if operation.warning_level == "critical":
                self.console.print()
                self.console.print(
                    f"[bold red]To confirm this critical operation, type exactly: "
                    f"[white]{operation.confirmation_text}[/white][/bold red]"
                )

                confirmation_input = Prompt.ask("Confirmation")

                if confirmation_input != operation.confirmation_text:
                    self.console.print("[red]Confirmation text does not match. Operation cancelled.[/red]")
                    raise ConfirmationCancelledError("Confirmation text mismatch")

            # Log successful confirmation
            logger.info(f"Destructive operation confirmed: {operation.operation_type} "
                       f"on repository {operation.repository_info.repository_id}")

            self.console.print("[green]Operation confirmed. Proceeding...[/green]")
            return True

        except (EOFError, KeyboardInterrupt):
            self.console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise ConfirmationCancelledError("User interrupted confirmation")

        except Exception as e:
            logger.error(f"Confirmation error: {e}")
            raise ConfirmationError(f"Confirmation failed: {e}")

    def confirm_repository_deletion(self, repository_info: RepositoryInfo,
                                  force: bool = False) -> bool:
        """
        Confirm repository deletion with explicit "DELETE ALL DATA" confirmation
        
        Args:
            repository_info: Repository information
            force: Skip confirmation if True
            
        Returns:
            bool: True if deletion is confirmed
        """
        operation = DestructiveOperation(
            operation_type="delete_repository",
            repository_info=repository_info,
            description=(
                f"This will permanently delete the entire repository '{repository_info.name}' "
                f"and all its backup data. This action cannot be undone."
            ),
            confirmation_text="DELETE ALL DATA",
            warning_level="critical"
        )

        return self.confirm_destructive_operation(operation, force)

    def confirm_snapshot_deletion(self, repository_info: RepositoryInfo,
                                snapshot_id: str, force: bool = False) -> bool:
        """
        Confirm snapshot deletion
        
        Args:
            repository_info: Repository information
            snapshot_id: Snapshot ID to delete
            force: Skip confirmation if True
            
        Returns:
            bool: True if deletion is confirmed
        """
        operation = DestructiveOperation(
            operation_type="forget_snapshot",
            repository_info=repository_info,
            description=(
                f"This will remove snapshot '{snapshot_id}' from repository '{repository_info.name}'. "
                f"The snapshot data will be marked for deletion and removed during the next prune operation."
            ),
            confirmation_text="DELETE SNAPSHOT",
            warning_level="high",
            additional_info={"snapshot_id": snapshot_id}
        )

        return self.confirm_destructive_operation(operation, force)

    def confirm_repository_prune(self, repository_info: RepositoryInfo,
                               force: bool = False) -> bool:
        """
        Confirm repository prune operation
        
        Args:
            repository_info: Repository information
            force: Skip confirmation if True
            
        Returns:
            bool: True if prune is confirmed
        """
        operation = DestructiveOperation(
            operation_type="prune_repository",
            repository_info=repository_info,
            description=(
                f"This will permanently remove unreferenced data from repository '{repository_info.name}'. "
                f"This operation cannot be undone and may take a long time."
            ),
            confirmation_text="PRUNE DATA",
            warning_level="high"
        )

        return self.confirm_destructive_operation(operation, force)

    def show_operation_cancelled(self, operation_type: str) -> None:
        """
        Show operation cancelled message
        
        Args:
            operation_type: Type of operation that was cancelled
        """
        panel = Panel(
            f"[yellow]{operation_type.replace('_', ' ').title()} operation has been cancelled.[/yellow]",
            title="Operation Cancelled",
            border_style="yellow"
        )
        self.console.print(panel)

    def show_operation_confirmed(self, operation_type: str) -> None:
        """
        Show operation confirmed message
        
        Args:
            operation_type: Type of operation that was confirmed
        """
        panel = Panel(
            f"[green]{operation_type.replace('_', ' ').title()} operation confirmed. Proceeding...[/green]",
            title="Operation Confirmed",
            border_style="green"
        )
        self.console.print(panel)

    def show_protection_status(self, repository_info: RepositoryInfo) -> None:
        """
        Show repository protection status
        
        Args:
            repository_info: Repository information including protection status
        """
        # Determine status color and icon
        if repository_info.mode.value == "locked":
            status_color = "red"
            status_icon = "🔒"
            status_text = "LOCKED"
        elif repository_info.mode.value == "read_only":
            status_color = "yellow"
            status_icon = "👁️"
            status_text = "READ-ONLY"
        else:
            status_color = "green"
            status_icon = "✅"
            status_text = "READ-WRITE"

        panel = Panel(
            f"[{status_color}]{status_icon} Repository is in {status_text} mode[/{status_color}]",
            title=f"Protection Status: {repository_info.name}",
            border_style=status_color
        )
        self.console.print(panel)

    def prompt_repository_mode_change(self, repository_info: RepositoryInfo,
                                    new_mode: str) -> bool:
        """
        Prompt for repository mode change confirmation
        
        Args:
            repository_info: Repository information
            new_mode: New mode to set
            
        Returns:
            bool: True if mode change is confirmed
        """
        try:
            if not self.interactive_check():
                return False

            self.show_repository_details(repository_info)
            self.console.print()

            current_mode = repository_info.mode.value.replace("_", " ").title()
            new_mode_display = new_mode.replace("_", " ").title()

            return Confirm.ask(
                f"Change repository mode from {current_mode} to {new_mode_display}?",
                default=False
            )

        except (EOFError, KeyboardInterrupt):
            return False

    def show_error(self, title: str, message: str) -> None:
        """
        Show error message
        
        Args:
            title: Error title
            message: Error message
        """
        panel = Panel(
            f"[red]{message}[/red]",
            title=f"Error: {title}",
            border_style="red"
        )
        self.console.print(panel)

    def show_info(self, title: str, message: str) -> None:
        """
        Show information message
        
        Args:
            title: Information title
            message: Information message
        """
        panel = Panel(
            f"[blue]{message}[/blue]",
            title=title,
            border_style="blue"
        )
        self.console.print(panel)

    def show_success(self, title: str, message: str) -> None:
        """
        Show success message
        
        Args:
            title: Success title
            message: Success message
        """
        panel = Panel(
            f"[green]{message}[/green]",
            title=title,
            border_style="green"
        )
        self.console.print(panel)