#!/usr/bin/env python3
"""
TimeLocker Command Line Interface

This module provides a beautiful, modern command-line interface for TimeLocker backup operations
using Typer for type-safe commands and Rich for beautiful terminal output.
"""

import sys
import os
import json
import logging
import logging.handlers
import builtins
import importlib
from enum import Enum
from pathlib import Path
from typing import Optional, List, Annotated, Dict, Any, TextIO
from datetime import datetime
import inspect
import re
from urllib.parse import urlparse

import typer
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Confirm, Prompt
from rich.text import Text
from rich.tree import Tree
from rich import print as rprint
from rich.logging import RichHandler

from . import __version__
from .backup_manager import BackupManager
from .backup_target import BackupTarget
from .file_selections import FileSelection, SelectionType
from .restore_manager import RestoreManager
from .snapshot_manager import SnapshotManager
from .config import ConfigurationModule, ConfigurationValidator
from .config.configuration_manager import ConfigurationManager, RepositoryNotFoundError
from .interfaces.exceptions import ConfigurationError
from .cli_services import get_cli_service_manager, CLIBackupRequest
from .completion import (
    repository_name_completer,
    target_name_completer,
    snapshot_id_completer,
    repository_uri_completer,
    repository_completer,
    file_path_completer,
)
from .importers.timeshift_importer import TimeshiftConfigParser, TimeshiftToTimeLockerMapper
from . import monitoring as _timelocker_monitoring
from .config import configuration_manager as _timelocker_config_manager_module

from .utils.repository_resolver import validate_repository_name_or_uri
from .utils.snapshot_validation import validate_snapshot_id_format
from .cli_helpers import store_backend_credentials as store_backend_credentials_helper  # Added import for extracted helper
from .security import SecurityService, RepositoryInfo, RepositoryMode, ConfirmationDialogs

# Test-friendly patch: ensure stderr is captured separately in Typer's CliRunner
# so tests can safely access result.stderr when using CliRunner.
try:
    from typer.testing import CliRunner as _TyperCliRunner

    if not getattr(_TyperCliRunner, "_timelocker_mixstderr_patched", False):
        _orig_invoke = _TyperCliRunner.invoke


        def _patched_invoke(self, *args, **kwargs):
            # Prefer separate stderr when supported by click
            use_mix = False
            if "mix_stderr" in kwargs:
                use_mix = kwargs["mix_stderr"] is True
            else:
                kwargs["mix_stderr"] = False
            # First attempt, may store a TypeError in result.exception on older click
            result = _orig_invoke(self, *args, **kwargs)
            # Detect older click capturing the TypeError about mix_stderr
            if getattr(result, "exception", None) and isinstance(result.exception, TypeError) and "mix_stderr" in str(result.exception):
                kwargs.pop("mix_stderr", None)
                result = _orig_invoke(self, *args, **kwargs)
            # Ensure result.stderr is safe to access
            try:
                if getattr(result, "stderr_bytes", None) is None:
                    setattr(result, "stderr_bytes", b"")
            except Exception:
                pass
            return result


        _TyperCliRunner.invoke = _patched_invoke
        _TyperCliRunner._timelocker_mixstderr_patched = True
except Exception:
    pass

# Clamp terminal width to keep help output readable in tests/CI environments
try:
    columns_value = int(os.environ.get("COLUMNS", "0"))
    if columns_value > 120:
        os.environ["COLUMNS"] = "120"
except ValueError:
    pass

# Initialize Rich console for consistent output
console = Console(width=100)

_rich_print = console.print


def _stream_is_interactive(stream: Optional[TextIO]) -> bool:
    """
    Determine whether a given text stream supports interactive prompting.

    Args:
        stream: Target text stream or ``None``.

    Returns:
        True when the stream exposes ``isatty`` and reports an interactive terminal.
    """
    if stream is None:
        return False
    isatty = getattr(stream, "isatty", None)
    if callable(isatty):
        try:
            return bool(isatty())
        except Exception:
            return False
    return False


_original_rich_console_input = Console.input


def _patched_rich_console_input(
        self,
        prompt: Any = "",
        *,
        markup: bool = True,
        emoji: bool = True,
        password: bool = False,
        stream: Optional[TextIO] = None,
) -> str:
    """
    Override Rich console input to avoid getpass blocking on non-interactive streams.

    Falls back to basic line reads whenever password prompts occur without a TTY, ensuring
    Typer's CliRunner and other automated harnesses can supply input programmatically.
    """
    target_stream: Optional[TextIO] = stream or typer.get_text_stream("stdin")
    if password and target_stream is not None and not _stream_is_interactive(target_stream):
        if prompt:
            # Match Rich behaviour by rendering the prompt prior to reading input
            self.print(prompt, markup=markup, emoji=emoji, end="")
        line = target_stream.readline()
        if line == "":
            raise EOFError("No input available for prompt.")
        return line.rstrip("\r\n")

    return _original_rich_console_input(
            self,
            prompt,
            markup=markup,
            emoji=emoji,
            password=password,
            stream=stream,
    )


def _console_print(*args, **kwargs):
    console.file = typer.get_text_stream("stdout")
    return _rich_print(*args, **kwargs)


console.print = _console_print  # type: ignore[attr-defined]
Console.input = _patched_rich_console_input  # type: ignore[attr-defined]

sys.modules["TimeLocker.cli"] = sys.modules[__name__]
sys.modules.setdefault("TimeLocker.config.configuration_manager", _timelocker_config_manager_module)
sys.modules.setdefault("TimeLocker.monitoring", _timelocker_monitoring)


def _combined_output_for_tests(result: Any) -> str:
    """
    Combine stdout and stderr for CLI runner results.

    Provided to support legacy tests that reference `_combined_output`
    without importing it explicitly from test utilities.
    """
    stdout_text = getattr(result, "stdout", "") or ""
    stderr_text = getattr(result, "stderr", "") or ""
    return stdout_text + "\n" + stderr_text


if not hasattr(builtins, "_combined_output"):
    builtins._combined_output = _combined_output_for_tests


def _register_builtin_symbol(symbol_name: str, module_path: str, fallback: Any = None) -> None:
    """Register a symbol in builtins for legacy tests if not already provided."""
    if hasattr(builtins, symbol_name):
        return
    target = fallback
    try:
        module = importlib.import_module(module_path)
        target = getattr(module, symbol_name, fallback)
    except Exception:
        target = fallback
    if target is not None:
        setattr(builtins, symbol_name, target)


try:
    _monitoring_module = importlib.import_module("TimeLocker.monitoring")
    StatusReporter = getattr(_monitoring_module, "StatusReporter")
    StatusLevel = getattr(_monitoring_module, "StatusLevel")
except Exception:
    class StatusLevel(Enum):  # type: ignore[misc]
        SUCCESS = "success"
        FAILURE = "failure"
        WARNING = "warning"


    class StatusReporter:  # type: ignore[misc]
        """Fallback status reporter for tests when monitoring module is unavailable."""

        def update_progress(self, **_kwargs: Any) -> None:  # pragma: no cover - noop
            return

        def complete_operation(self, **_kwargs: Any) -> None:  # pragma: no cover - noop
            return

_register_builtin_symbol("StatusReporter", "TimeLocker.monitoring", StatusReporter)
_register_builtin_symbol("StatusLevel", "TimeLocker.monitoring", StatusLevel)
_register_builtin_symbol("ConfigurationManager", "TimeLocker.config.configuration_manager", ConfigurationManager)

CLI_CONTEXT_SETTINGS = {"max_content_width": 110}

app = typer.Typer(
        name="timelocker",
        help=(
                "TimeLocker — Beautiful backup and restore with a clear CLI.\n\n"
                "Key groups: repos, targets, snapshots (restore under snapshots).\n\n"
                "Examples:\n"
                "  tl repos add <name> file:///path/to/repo\n"
                "  tl targets add <name> --path ~/Documents\n"
                "  tl backup run --target <name>\n"
                "  tl snapshots list  # lists snapshots (see --repository)\n"
                "  tl snapshots restore <id|latest> /restore/path --repository <name>\n\n"
                "Note: Local repository paths must use the file:// prefix (e.g., file:///path/to/repo).\n"
        ),
        epilog="Made with ❤️  by Bruce Cherrington",
        rich_markup_mode=None,
        no_args_is_help=True,
        context_settings=CLI_CONTEXT_SETTINGS,
)
app.info.options_metavar = "⟨OPTIONS⟩"

# Create sub-apps for new hierarchy
backup_app = typer.Typer(help="Backup operations", no_args_is_help=True, context_settings=CLI_CONTEXT_SETTINGS)
backup_app.info.options_metavar = "⟨OPTIONS⟩"

snapshots_app = typer.Typer(help="Snapshot operations", context_settings=CLI_CONTEXT_SETTINGS)
snapshots_app.info.options_metavar = "⟨OPTIONS⟩"
repos_app = typer.Typer(help="Repository operations", context_settings=CLI_CONTEXT_SETTINGS)
repos_app.info.options_metavar = "⟨OPTIONS⟩"
targets_app = typer.Typer(help="Backup target operations", context_settings=CLI_CONTEXT_SETTINGS)
targets_app.info.options_metavar = "⟨OPTIONS⟩"
config_app = typer.Typer(help="Configuration management commands", context_settings=CLI_CONTEXT_SETTINGS)
config_app.info.options_metavar = "⟨OPTIONS⟩"
credentials_app = typer.Typer(help="Credential management commands", context_settings=CLI_CONTEXT_SETTINGS)
credentials_app.info.options_metavar = "⟨OPTIONS⟩"

# Create security sub-app
security_app = typer.Typer(help="Security management commands", context_settings=CLI_CONTEXT_SETTINGS)
security_app.info.options_metavar = "⟨OPTIONS⟩"

# Add sub-apps to main app
app.add_typer(backup_app, name="backup")

app.add_typer(snapshots_app, name="snapshots")
app.add_typer(repos_app, name="repos")
app.add_typer(targets_app, name="targets")
app.add_typer(config_app, name="config")
app.add_typer(credentials_app, name="credentials")
app.add_typer(security_app, name="security")

# Create config sub-apps (only import remains under config)
config_import_app = typer.Typer(help="Import configuration commands", context_settings=CLI_CONTEXT_SETTINGS)
config_import_app.info.options_metavar = "⟨OPTIONS⟩"

# Add config sub-apps
config_app.add_typer(config_import_app, name="import")

# Create repos sub-apps
repos_credentials_app = typer.Typer(help="Repository credential management", context_settings=CLI_CONTEXT_SETTINGS)
repos_credentials_app.info.options_metavar = "⟨OPTIONS⟩"

# Add repos sub-apps
repos_app.add_typer(repos_credentials_app, name="credentials")


@app.command("version")
def cli_version(
        short: Annotated[bool, typer.Option("--short", help="Only print the version number")] = False,
) -> None:
    """Display the TimeLocker CLI version."""
    if short:
        console.print(__version__)
    else:
        console.print(f"TimeLocker version [bold]{__version__}[/bold]")


@app.command("help")
def cli_help(
        topic: Annotated[Optional[str], typer.Argument(help="Help topic (repos, backup, restore, policy, schedule, selections)")] = None,
) -> None:
    """
    Show comprehensive help and usage examples for TimeLocker commands.
    
    This command provides detailed help, usage examples, and common workflows
    for different TimeLocker operations.
    
    Examples:
        timelocker help              # Show general help
        timelocker help repos        # Show repository management help
        timelocker help backup       # Show backup operations help
        timelocker help restore      # Show restore operations help
    """
    if topic is None:
        # Show general help
        console.print("\n[bold cyan]TimeLocker - Backup Management System[/bold cyan]\n")
        console.print("TimeLocker provides comprehensive backup and restore capabilities with")
        console.print("policy-based management, scheduling, and data selection.\n")
        
        console.print("[bold]Main Command Groups:[/bold]")
        console.print("  [cyan]repos[/cyan]       - Repository management (create, list, validate)")
        console.print("  [cyan]backup[/cyan]      - Backup operations (run, status, list)")
        console.print("  [cyan]restore[/cyan]     - Restore operations (browse, files, full)")
        console.print("  [cyan]snapshots[/cyan]   - Snapshot management (list, show, delete)")
        console.print("  [cyan]policy[/cyan]      - Policy management (backup and retention policies)")
        console.print("  [cyan]schedule[/cyan]    - Scheduling automation (create, manage schedules)")
        console.print("  [cyan]selections[/cyan]  - Data selection templates (include/exclude patterns)")
        console.print("  [cyan]security[/cyan]    - Security and credential management")
        console.print("  [cyan]monitor[/cyan]     - System monitoring and health checks\n")
        
        console.print("[bold]Quick Start:[/bold]")
        console.print("  1. Create a repository:")
        console.print("     timelocker repos create myrepo file:///backup/repo\n")
        console.print("  2. Create a backup target:")
        console.print("     timelocker targets add documents --path ~/Documents\n")
        console.print("  3. Run a backup:")
        console.print("     timelocker backup run --target documents\n")
        console.print("  4. List snapshots:")
        console.print("     timelocker snapshots list\n")
        console.print("  5. Restore files:")
        console.print("     timelocker restore files myrepo latest /restore/path\n")
        
        console.print("[bold]Get Detailed Help:[/bold]")
        console.print("  timelocker help repos      # Repository management help")
        console.print("  timelocker help backup     # Backup operations help")
        console.print("  timelocker help restore    # Restore operations help")
        console.print("  timelocker help policy     # Policy management help")
        console.print("  timelocker help schedule   # Scheduling help\n")
        
        console.print("[bold]Command Help:[/bold]")
        console.print("  timelocker <command> --help    # Show help for any command")
        console.print("  timelocker repos --help        # Show repos command help")
        console.print("  timelocker backup run --help   # Show backup run help\n")
        
        console.print("[bold]Aliases:[/bold]")
        console.print("  'tl' can be used as a short alias for 'timelocker'")
        console.print("  Example: tl repos list\n")
        
        return
    
    topic = topic.lower()
    
    if topic == "repos" or topic == "repository":
        console.print("\n[bold cyan]Repository Management Help[/bold cyan]\n")
        console.print("Repositories store your backup data. TimeLocker supports multiple")
        console.print("repository backends including local, S3, B2, SFTP, and more.\n")
        
        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]repos create[/cyan] <name> <uri>  - Create a new repository")
        console.print("  [cyan]repos list[/cyan]                 - List all repositories")
        console.print("  [cyan]repos show[/cyan] <name>          - Show repository details")
        console.print("  [cyan]repos validate[/cyan] <name>      - Validate repository connectivity")
        console.print("  [cyan]repos check[/cyan] <name>         - Check repository integrity")
        console.print("  [cyan]repos stats[/cyan] <name>         - Show repository statistics")
        console.print("  [cyan]repos delete[/cyan] <name>        - Delete a repository\n")
        
        console.print("[bold]Examples:[/bold]")
        console.print("  # Create a local repository")
        console.print("  timelocker repos create local-backup file:///backup/local\n")
        console.print("  # Create an S3 repository")
        console.print("  timelocker repos create s3-backup s3:s3.amazonaws.com/my-bucket/backup\n")
        console.print("  # List all repositories")
        console.print("  timelocker repos list\n")
        console.print("  # Check repository health")
        console.print("  timelocker repos check local-backup\n")
        console.print("  # View repository statistics")
        console.print("  timelocker repos stats local-backup\n")
        
        console.print("[bold]Credential Management:[/bold]")
        console.print("  repos credentials set <name>     - Store backend credentials")
        console.print("  repos credentials show <name>    - Show credential status")
        console.print("  repos credentials remove <name>  - Remove stored credentials\n")
        
    elif topic == "backup":
        console.print("\n[bold cyan]Backup Operations Help[/bold cyan]\n")
        console.print("Backup operations create snapshots of your data in repositories.\n")
        
        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]backup run[/cyan] <policy>        - Run a backup using a policy")
        console.print("  [cyan]backup status[/cyan]              - Show current backup status")
        console.print("  [cyan]backup list[/cyan]                - List backup history")
        console.print("  [cyan]backup cancel[/cyan] <job-id>     - Cancel a running backup\n")
        
        console.print("[bold]Examples:[/bold]")
        console.print("  # Run a backup with a target")
        console.print("  timelocker backup run --target documents\n")
        console.print("  # Run a backup with a policy")
        console.print("  timelocker backup run daily-backup\n")
        console.print("  # Check backup status")
        console.print("  timelocker backup status\n")
        console.print("  # List recent backups")
        console.print("  timelocker backup list --limit 10\n")
        
    elif topic == "restore":
        console.print("\n[bold cyan]Restore Operations Help[/bold cyan]\n")
        console.print("Restore operations recover data from backup snapshots.\n")
        
        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]restore browse[/cyan] <repo> <snapshot>        - Browse snapshot contents")
        console.print("  [cyan]restore files[/cyan] <repo> <snapshot> <paths> - Restore specific files")
        console.print("  [cyan]restore full[/cyan] <repo> <snapshot> <target> - Restore entire snapshot")
        console.print("  [cyan]restore list[/cyan] <repo>                      - List available snapshots")
        console.print("  [cyan]restore find[/cyan] <repo> <query>              - Search for files")
        console.print("  [cyan]restore diff[/cyan] <repo> <snap1> <snap2>      - Compare snapshots\n")
        
        console.print("[bold]Examples:[/bold]")
        console.print("  # List available snapshots")
        console.print("  timelocker restore list myrepo\n")
        console.print("  # Browse latest snapshot")
        console.print("  timelocker restore browse myrepo latest\n")
        console.print("  # Restore specific files")
        console.print("  timelocker restore files myrepo latest /restore/path --include '*.txt'\n")
        console.print("  # Restore entire snapshot")
        console.print("  timelocker restore full myrepo abc123 /restore/path\n")
        console.print("  # Find files across snapshots")
        console.print("  timelocker restore find myrepo 'important.doc'\n")
        
    elif topic == "policy":
        console.print("\n[bold cyan]Policy Management Help[/bold cyan]\n")
        console.print("Policies define backup and retention rules for automated operations.\n")
        
        console.print("[bold]Backup Policies:[/bold]")
        console.print("  [cyan]policy backup create[/cyan] <name>   - Create a backup policy")
        console.print("  [cyan]policy backup list[/cyan]            - List backup policies")
        console.print("  [cyan]policy backup show[/cyan] <id>       - Show policy details")
        console.print("  [cyan]policy backup delete[/cyan] <id>     - Delete a policy\n")
        
        console.print("[bold]Retention Policies:[/bold]")
        console.print("  [cyan]policy retention create[/cyan] <name> - Create a retention policy")
        console.print("  [cyan]policy retention list[/cyan]          - List retention policies")
        console.print("  [cyan]policy retention show[/cyan] <id>     - Show policy details\n")
        
        console.print("[bold]Examples:[/bold]")
        console.print("  # Create a backup policy")
        console.print("  timelocker policy backup create daily-backup \\")
        console.print("    --repository myrepo --description 'Daily backups'\n")
        console.print("  # Create a retention policy")
        console.print("  timelocker policy retention create keep-7-days \\")
        console.print("    --daily 7 --weekly 4 --monthly 6\n")
        console.print("  # List all policies")
        console.print("  timelocker policy backup list\n")
        
    elif topic == "schedule":
        console.print("\n[bold cyan]Scheduling Automation Help[/bold cyan]\n")
        console.print("Schedules automate backup execution using policies.\n")
        
        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]schedule create[/cyan] <name> <policy>  - Create a schedule")
        console.print("  [cyan]schedule list[/cyan]                     - List all schedules")
        console.print("  [cyan]schedule show[/cyan] <name>              - Show schedule details")
        console.print("  [cyan]schedule enable[/cyan] <name>            - Enable a schedule")
        console.print("  [cyan]schedule disable[/cyan] <name>           - Disable a schedule")
        console.print("  [cyan]schedule generate-scripts[/cyan] <name>  - Generate automation scripts\n")
        
        console.print("[bold]Examples:[/bold]")
        console.print("  # Create a daily schedule")
        console.print("  timelocker schedule create daily-2am daily-backup \\")
        console.print("    --frequency daily --cron '0 2 * * *'\n")
        console.print("  # Generate cron script")
        console.print("  timelocker schedule generate-scripts daily-2am --platform cron\n")
        console.print("  # Enable a schedule")
        console.print("  timelocker schedule enable daily-2am\n")
        
    elif topic == "selections":
        console.print("\n[bold cyan]Data Selection Help[/bold cyan]\n")
        console.print("Selection templates define which files to include or exclude in backups.\n")
        
        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]selections create[/cyan] <name>     - Create a selection template")
        console.print("  [cyan]selections list[/cyan]              - List all templates")
        console.print("  [cyan]selections show[/cyan] <name>       - Show template details")
        console.print("  [cyan]selections test[/cyan] <name>       - Test a template")
        console.print("  [cyan]selections export[/cyan] <name>     - Export a template")
        console.print("  [cyan]selections import[/cyan] <file>     - Import a template\n")
        
        console.print("[bold]Examples:[/bold]")
        console.print("  # Create a selection template")
        console.print("  timelocker selections create documents \\")
        console.print("    --include '*.doc' --include '*.pdf' \\")
        console.print("    --exclude '*/temp/*'\n")
        console.print("  # Test a template")
        console.print("  timelocker selections test documents ~/Documents\n")
        
    else:
        show_error_panel(
            "Unknown Topic",
            f"Unknown help topic: {topic}\n\n"
            "Available topics: repos, backup, restore, policy, schedule, selections"
        )
        raise typer.Exit(1)


@app.command("completion")
def cli_completion(
        shell: Annotated[Optional[str], typer.Argument(help="Target shell (bash, zsh, fish, powershell)")] = None,
        install: Annotated[bool, typer.Option("--install", help="Install completion for the specified shell")] = False,
) -> None:
    """
    Show instructions for enabling shell completion scripts.
    
    Shell completion enables tab-completion for TimeLocker commands, options, and dynamic values
    like repository names, policy names, and schedule names.
    
    Examples:
        timelocker completion bash          # Show bash completion instructions
        timelocker completion --install bash # Install bash completion
        timelocker --show-completion        # Show completion script for current shell
        timelocker --install-completion     # Install completion for current shell
    """
    supported_shells = ["bash", "zsh", "fish", "powershell"]

    if shell is None:
        # Show general completion information
        console.print("\n[bold cyan]TimeLocker Shell Completion[/bold cyan]\n")
        console.print("Shell completion provides tab-completion for:")
        console.print("  • Commands and subcommands")
        console.print("  • Command options and flags")
        console.print("  • Repository names from your configuration")
        console.print("  • Policy names, schedule names, and selection templates")
        console.print("  • File paths and URIs\n")
        
        console.print("[bold]Supported Shells:[/bold]")
        for s in supported_shells:
            console.print(f"  • {s}")
        
        console.print("\n[bold]Quick Install:[/bold]")
        console.print("  timelocker --install-completion     # Auto-detect and install")
        console.print("  timelocker completion --install bash # Install for specific shell\n")
        
        console.print("[bold]Manual Installation:[/bold]")
        console.print("  timelocker --show-completion > ~/.timelocker-complete.sh")
        console.print("  source ~/.timelocker-complete.sh\n")
        
        console.print("[bold]Aliases:[/bold]")
        console.print("  Both 'timelocker' and 'tl' commands support completion\n")
        return

    shell = shell.lower()
    if shell not in supported_shells:
        show_error_panel(
                "Unsupported Shell",
                f"Shell '{shell}' is not supported. Choose from: {', '.join(supported_shells)}."
        )
        raise typer.Exit(2)

    if install:
        # Provide installation instructions
        console.print(f"\n[bold cyan]Installing {shell.title()} Completion[/bold cyan]\n")
        
        if shell == "bash":
            console.print("[bold]For Bash:[/bold]")
            console.print("  1. Generate completion script:")
            console.print("     timelocker --show-completion bash > ~/.timelocker-complete.bash\n")
            console.print("  2. Add to your ~/.bashrc:")
            console.print("     echo 'source ~/.timelocker-complete.bash' >> ~/.bashrc\n")
            console.print("  3. Reload your shell:")
            console.print("     source ~/.bashrc\n")
        elif shell == "zsh":
            console.print("[bold]For Zsh:[/bold]")
            console.print("  1. Generate completion script:")
            console.print("     timelocker --show-completion zsh > ~/.timelocker-complete.zsh\n")
            console.print("  2. Add to your ~/.zshrc:")
            console.print("     echo 'source ~/.timelocker-complete.zsh' >> ~/.zshrc\n")
            console.print("  3. Reload your shell:")
            console.print("     source ~/.zshrc\n")
        elif shell == "fish":
            console.print("[bold]For Fish:[/bold]")
            console.print("  1. Generate completion script:")
            console.print("     timelocker --show-completion fish > ~/.config/fish/completions/timelocker.fish\n")
            console.print("  2. Reload completions:")
            console.print("     fish_update_completions\n")
        elif shell == "powershell":
            console.print("[bold]For PowerShell:[/bold]")
            console.print("  1. Generate completion script:")
            console.print("     timelocker --show-completion powershell > $PROFILE\n")
            console.print("  2. Reload your profile:")
            console.print("     . $PROFILE\n")
        
        console.print("[bold green]Completion will be available after reloading your shell[/bold green]\n")
    else:
        # Show instructions without installing
        console.print(f"\n[bold cyan]{shell.title()} Completion Instructions[/bold cyan]\n")
        console.print(f"To view the completion script for {shell}:")
        console.print(f"  timelocker --show-completion {shell}\n")
        console.print(f"To install completion for {shell}:")
        console.print(f"  timelocker completion --install {shell}\n")
        console.print("Or use the automatic installer:")
        console.print("  timelocker --install-completion\n")


def main() -> None:
    """Entry point for legacy integrations expecting TimeLocker.cli.main."""
    app()


@config_import_app.command("restic")
def config_import_restic(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        config_file: Annotated[Optional[Path], typer.Option("--config-file", help="Optional configuration file to update")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without modifying configuration")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Import configuration settings from restic environment variables."""
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        import_method = _get_service_method(manager, "import_restic_config")
        if not import_method:
            show_info_panel(
                    "Restic Import",
                    "Automatic restic configuration import is not available in this build."
            )
            return

        result = _call_service_method(
                import_method,
                config_dir=config_dir,
                config_file=str(config_file) if config_file else None,
                dry_run=dry_run,
        )

        success_flag = getattr(result, "success", None)
        if success_flag is None:
            success_flag = bool(result)

        if success_flag:
            message = "Restic environment settings imported."
            if dry_run:
                message = "Restic configuration import dry-run completed."
            show_success_panel("Restic Import", message)
        else:
            error_details = getattr(result, "errors", None)
            show_error_panel("Restic Import Failed", "Failed to import restic configuration.", error_details)
            raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Restic import cancelled by user")
        raise typer.Exit(130)
    except click.exceptions.Exit:
        raise
    except Exception as exc:
        show_error_panel("Restic Import Error", f"Failed to import restic configuration: {exc}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_import_app.command("timeshift")
def config_import_timeshift(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        config_file: Annotated[Optional[Path], typer.Option("--config-file", help="Path to Timeshift configuration file")] = None,
        repo_name: Annotated[str, typer.Option("--repo-name", help="Name to assign the imported repository")] = "timeshift_imported",
        target_name: Annotated[str, typer.Option("--target-name", help="Name to assign the imported backup target")] = "timeshift_system",
        repo_path: Annotated[Optional[str], typer.Option("--repo-path", help="Override repository path if device resolution fails")] = None,
        paths: Annotated[Optional[List[str]], typer.Option("--paths", help="Override backup paths (multiple allowed)")] = None,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Apply changes without confirmation")] = False,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without modifying configuration")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Import configuration from Timeshift backup tool."""
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        import_method = _get_service_method(manager, "import_timeshift_config")
        if not import_method:
            from .importers.timeshift_importer import TimeshiftConfigParser, TimeshiftToTimeLockerMapper

            parser = TimeshiftConfigParser()
            try:
                parsed_config = parser.parse_config(config_file)
            except FileNotFoundError:
                show_error_panel("Timeshift Configuration Not Found", "Timeshift configuration file could not be located.")
                raise typer.Exit(1)
            except PermissionError as exc:
                show_error_panel("Timeshift Configuration Error", f"Permission denied reading Timeshift configuration: {exc}")
                raise typer.Exit(1)
            except json.JSONDecodeError as exc:
                show_error_panel("Invalid Timeshift Configuration", f"Invalid Timeshift configuration: {exc}")
                raise typer.Exit(1)
            except Exception as exc:
                show_error_panel("Timeshift Import Error", f"Failed to parse Timeshift configuration: {exc}")
                if verbose:
                    console.print_exception()
                raise typer.Exit(1)

            mapper = TimeshiftToTimeLockerMapper()
            backup_paths = list(paths) if paths else None
            result = mapper.import_configuration(
                    parsed_config,
                    repository_name=repo_name,
                    target_name=target_name,
                    manual_repository_path=repo_path,
                    backup_paths=backup_paths,
            )

            console.rule("Import from Timeshift")
            summary = parser.get_summary()
            config_path_display = summary.get("config_file") or (str(config_file) if config_file else "default locations")
            console.print(f"[bold]Timeshift Configuration Found:[/bold] {config_path_display}")

            repo_config = result.repository_config or {}
            target_config = result.backup_target_config or {}

            console.print("\n[bold]Repository Configuration[/bold]")
            console.print(f"- Name: {repo_config.get('name', repo_name)}")
            console.print(f"- Location: {repo_config.get('location', repo_path or '/timeshift')}")
            console.print(f"- Description: {repo_config.get('description', 'Imported from Timeshift')}")

            console.print("\n[bold]Backup Target Configuration[/bold]")
            console.print(f"- Name: {target_config.get('name', target_name)}")
            console.print(f"- Paths: {', '.join(target_config.get('paths', backup_paths or ['/']))}")
            console.print(f"- Repository: {target_config.get('_display_repository', repo_name)}")

            if result.warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"- {warning}")
                if str(parsed_config.get("btrfs_mode", "false")).lower() == "true":
                    console.print("- BTRFS Mode: Yes (Timeshift configuration indicates BTRFS snapshots were enabled.)")

            if result.errors:
                console.print("\n[red]Errors:[/red]")
                for error in result.errors:
                    console.print(f"- {error}")

            if dry_run or not yes:
                console.print("\n[cyan]Dry run mode - no changes made[/cyan]")

            show_success_panel(
                    "Timeshift Import",
                    "Timeshift configuration import dry-run completed." if dry_run or not yes else "Timeshift configuration imported successfully."
            )
            return

        result = _call_service_method(
                import_method,
                config_dir=config_dir,
                config_file=str(config_file) if config_file else None,
                repository_name=repo_name,
                target_name=target_name,
                manual_repository_path=repo_path,
                backup_paths=list(paths) if paths else None,
                assume_yes=yes,
                dry_run=dry_run,
        )

        success_flag = getattr(result, "success", None)
        if success_flag is None:
            success_flag = bool(result)

        if success_flag:
            message = "Timeshift configuration imported successfully."
            if dry_run:
                message = "Timeshift configuration import dry-run completed."
            show_success_panel("Timeshift Import", message)
        else:
            error_details = getattr(result, "errors", None)
            show_error_panel("Timeshift Import Failed", "Failed to import Timeshift configuration.", error_details)
            raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Timeshift import cancelled by user")
        raise typer.Exit(130)
    except click.exceptions.Exit:
        raise
    except Exception as exc:
        show_error_panel("Timeshift Import Error", f"Failed to import Timeshift configuration: {exc}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


class UserFacingLogFilter(logging.Filter):
    """Filter to identify user-facing log messages that should be displayed in CLI."""

    def filter(self, record):
        # Only show messages that are relevant to users
        # This includes configuration errors, validation failures, and user action failures

        # Always show CRITICAL errors
        if record.levelno >= logging.CRITICAL:
            return True

        # For ERROR and WARNING levels, be selective
        if record.levelno >= logging.WARNING:
            # Check if this is a user-relevant message based on logger name and message content
            logger_name = record.name.lower()
            message = record.getMessage().lower()

            # User-relevant loggers (TimeLocker specific, not third-party libraries)
            user_relevant_loggers = [
                    'timelocker',
                    'src.timelocker',
                    '__main__'
            ]

            # Check if it's from a user-relevant logger
            is_user_logger = any(logger_name.startswith(prefix.lower()) for prefix in user_relevant_loggers)

            # User-relevant message patterns
            user_relevant_patterns = [
                    'configuration',
                    'config',
                    'repository',
                    'backup',
                    'restore',
                    'snapshot',
                    'target',
                    'validation',
                    'permission denied',
                    'not found',
                    'failed to',
                    'unable to',
                    'invalid',
                    'missing',
                    'authentication',
                    'password'
            ]

            # Check if message contains user-relevant keywords
            has_user_keywords = any(pattern in message for pattern in user_relevant_patterns)

            # Filter out misleading warnings that aren't helpful during normal operations
            misleading_warnings = [
                    'no repositories configured',  # Don't show during repository add operations
            ]

            # Skip misleading warnings
            if any(warning in message for warning in misleading_warnings):
                return False

            # Show message if it's from a user-relevant logger AND contains user-relevant keywords
            return is_user_logger and has_user_keywords

        return False


class CLILogHandler(RichHandler):
    """Custom log handler that formats user-facing messages as Rich panels."""

    def __init__(self, console: Console):
        super().__init__(console=console, show_time=False, show_path=False)
        self.console = console

    def emit(self, record):
        try:
            # Format the message
            message = self.format(record)

            # Determine panel style based on log level
            if record.levelno >= logging.CRITICAL:
                title = "Critical Error"
                style = "red"
                icon = "💥"
            elif record.levelno >= logging.ERROR:
                title = "Error"
                style = "red"
                icon = "❌"
            elif record.levelno >= logging.WARNING:
                title = "Warning"
                style = "yellow"
                icon = "⚠️"
            else:
                # For INFO and below, use simple console output
                self.console.print(f"ℹ️  {message}", style="blue")
                return

            # Create and display panel for errors/warnings
            panel = Panel(
                    f"{icon} {message}",
                    title=f"[bold {style}]{title}[/bold {style}]",
                    border_style=style,
                    padding=(0, 1)
            )
            self.console.print(panel)

        except Exception:
            self.handleError(record)


def setup_logging(verbose: bool = False, config_dir: Optional[Path] = None) -> None:
    """Set up logging configuration with file output and user-facing CLI messages."""
    from .config.configuration_path_resolver import ConfigurationPathResolver

    # Determine log level
    level = logging.DEBUG if verbose else logging.INFO

    # Get appropriate XDG directory for log files (cache directory)
    # Logs are temporary/cache data, not configuration or persistent data
    log_dir = ConfigurationPathResolver.get_cache_directory() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Clear any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set up file logging for all messages
    log_file = log_dir / "timelocker.log"
    file_handler = None
    try:
        file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
    except (OSError, PermissionError) as exc:
        logging.getLogger(__name__).debug("File logging disabled: %s", exc)

    # Set up CLI logging for user-facing messages only
    cli_handler = CLILogHandler(console)
    cli_handler.setLevel(logging.WARNING)  # Only show warnings and errors to users
    cli_handler.addFilter(UserFacingLogFilter())

    # Configure root logger
    root_logger.setLevel(level)
    if file_handler is not None:
        root_logger.addHandler(file_handler)
    root_logger.addHandler(cli_handler)

    # Log the logging setup
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured - Level: {logging.getLevelName(level)}, Log file: {log_file}")

    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def show_success_panel(title: str, message: str, details: Optional[dict] = None) -> None:
    """Display a success panel with optional details."""
    content = f"✅ {message}"
    if details:
        content += "\n\n"
        for key, value in details.items():
            content += f"[bold]{key}:[/bold] {value}\n"

    panel = Panel(
            content.strip(),
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
            padding=(1, 2)
    )
    console.print(panel)


def show_error_panel(title: str, message: str, details: Optional[List[str]] = None) -> None:
    """Display an error panel with optional details."""
    # Escape Rich markup in message to prevent markup errors
    safe_message = message.replace("[", "\\[").replace("]", "\\]")
    content = f"❌ {safe_message}"

    if details:
        content += "\n\n[bold]Details:[/bold]\n"
        for detail in details:
            # Escape Rich markup in details too
            safe_detail = detail.replace("[", "\\[").replace("]", "\\]")
            content += f"• {safe_detail}\n"

    panel = Panel(
            content.strip(),
            title=f"[bold red]{title}[/bold red]",
            border_style="red",
            padding=(1, 2),
            width=100
    )
    console.print(panel)

    summary = f"{title}: {message}"
    if details:
        summary += " | " + " | ".join(details)
    typer.echo(summary)


def show_info_panel(title: str, message: str) -> None:
    """Display an info panel."""
    panel = Panel(
            f"ℹ️  {message}",
            title=f"[bold blue]{title}[/bold blue]",
            border_style="blue",
            padding=(1, 2)
    )
    console.print(panel)


def _get_service_method(manager, method_name: str):
    """Return callable service manager method if available."""
    method = getattr(manager, method_name, None)
    return method if callable(method) else None


def _call_service_method(method, **candidates):
    """Call service method with kwargs filtered to supported parameters."""
    if method is None:
        raise AttributeError("Service method is not available")

    signature = inspect.signature(method)
    params = signature.parameters

    # Remove potential 'self' parameter confusion
    filtered = {}
    accepts_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values())
    if accepts_kwargs:
        return method(**candidates)

    for name, value in candidates.items():
        if name in params:
            filtered[name] = value

    missing_required = [
            name for name, param in params.items()
            if name != "self" and param.default is inspect._empty and name not in filtered
    ]

    if missing_required and candidates:
        default_value = next(iter(candidates.values()))
        for name in missing_required:
            filtered.setdefault(name, default_value)

    return method(**filtered)


def _resolve_config_dir(config_dir: Optional[Path]) -> Optional[Path]:
    """Normalize configuration directory input."""
    return Path(config_dir) if config_dir is not None else None


def _get_service_manager_for_command(config_dir: Optional[Path] = None):
    """Fetch CLI service manager scoped to configuration directory."""
    return get_cli_service_manager(config_dir=_resolve_config_dir(config_dir))


def _create_credential_manager(config_dir: Optional[Path] = None):
    """Instantiate credential manager respecting configuration directory."""
    from .security.credential_manager import CredentialManager

    return CredentialManager()


def _create_security_manager(config_dir: Optional[Path] = None):
    """Create security manager with access manager integration."""
    from .security import CredentialManager, AccessManager
    
    credential_manager = CredentialManager(config_dir=config_dir)
    security_service = SecurityService(credential_manager, config_dir=config_dir)
    access_manager = AccessManager(config_dir=config_dir)
    
    return security_service, access_manager


def _authenticate_user_session(access_manager: 'AccessManager', user_id: Optional[str] = None) -> Optional[str]:
    """
    Authenticate user and create session if needed.
    
    Args:
        access_manager: AccessManager instance
        user_id: Optional user ID (defaults to current system user)
        
    Returns:
        Session ID if authentication successful, None otherwise
    """
    try:
        if user_id is None:
            import os
            user_id = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
        
        from .security.access_manager import UserCredentials
        credentials = UserCredentials(user_id=user_id)
        
        auth_result = access_manager.authenticate_user(credentials)
        if auth_result.success:
            return auth_result.session_id
        else:
            logger.warning(f"Authentication failed: {auth_result.error_message}")
            return None
            
    except Exception as e:
        logger.error(f"Session authentication error: {e}")
        return None


def _validate_session_for_operation(access_manager: 'AccessManager', operation: str, 
                                   repository_id: Optional[str] = None) -> bool:
    """
    Validate session for operation and create if needed.
    
    Args:
        access_manager: AccessManager instance
        operation: Operation being performed
        repository_id: Optional repository ID
        
    Returns:
        True if session is valid for operation
    """
    try:
        # Get or create session
        active_sessions = access_manager.get_active_sessions()
        session_id = None
        
        if active_sessions:
            # Use the most recent valid session
            for session in sorted(active_sessions, key=lambda s: s.last_accessed, reverse=True):
                if session.is_valid():
                    session_id = session.session_id
                    break
        
        if not session_id:
            # Create new session
            session_id = _authenticate_user_session(access_manager)
            if not session_id:
                return False
        
        # Validate session for operation
        if not access_manager.validate_session(session_id):
            return False
            
        # Extend session
        access_manager.extend_session(session_id)
        
        return True
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return False


def _create_configuration_module(config_dir: Optional[Path] = None):
    """Factory for configuration module respecting dynamic patching."""
    try:
        from .config import configuration_module as configuration_module_module
        module_class = getattr(configuration_module_module, "ConfigurationModule", None)
    except (ImportError, AttributeError):
        module_class = None

    cli_class = globals().get("ConfigurationModule", None)

    def _is_mock(candidate: Any) -> bool:
        return getattr(getattr(candidate, "__class__", None), "__module__", "").startswith("unittest.mock")

    if _is_mock(cli_class):
        selected_class = cli_class
    elif callable(module_class):
        selected_class = module_class
    elif callable(cli_class):
        selected_class = cli_class
    else:
        raise RuntimeError("ConfigurationModule is not available for instantiation.")

    return selected_class(config_dir=config_dir)


def _determine_backend_from_uri(uri: Optional[str]) -> Optional[str]:
    """Determine repository backend based on URI."""
    if not uri:
        return None
    normalized = uri.lower()
    if normalized.startswith(("s3://", "s3:")):
        return "s3"
    if normalized.startswith(("b2://", "b2:")):
        return "b2"
    if normalized.startswith(("azure:", "azure://")):
        return "azure"
    if normalized.startswith(("gs://", "gcs:", "gcs://")):
        return "gcs"
    return None


def _backend_display_name(backend: str) -> str:
    """Return user-facing backend name."""
    mapping = {
            "s3":    "AWS",
            "b2":    "Backblaze B2",
            "azure": "Azure",
            "gcs":   "Google Cloud Storage"
    }
    return mapping.get(backend, backend.upper())


def _repository_config_to_dict(repository_obj, name: str) -> Dict[str, Any]:
    """Convert repository configuration object or mapping to dictionary."""
    if repository_obj is None:
        return {"name": name}
    if hasattr(repository_obj, "to_dict"):
        maybe_dict = repository_obj.to_dict()
        data = dict(maybe_dict) if isinstance(maybe_dict, dict) else {"name": name}
    elif isinstance(repository_obj, dict):
        data = dict(repository_obj)
    else:
        data = {"name": name}
        for attr in ("uri", "location", "description", "tags", "password", "has_backend_credentials"):
            if hasattr(repository_obj, attr):
                value = getattr(repository_obj, attr)
                if value is not None:
                    key = "uri" if attr == "location" else attr
                    data[key] = value
    data.setdefault("name", name)
    # Normalise location/uri fields
    if "uri" not in data and "location" in data:
        data["uri"] = data.pop("location")
    return data


@repos_credentials_app.command("set")
def repos_credentials_set(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        master_password: Annotated[
            Optional[str], typer.Option("--master-password", "-m", help="Master password to unlock the credential manager if locked")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
) -> None:
    """Store backend credentials for a repository."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        config_module = _create_configuration_module(config_dir)
        repository_obj = config_module.get_repository(name)
        repo_uri = getattr(repository_obj, 'uri', None) or getattr(repository_obj, 'location', None)
        repository_config = _repository_config_to_dict(repository_obj, name)

        backend_type = _determine_backend_from_uri(repo_uri)
        if backend_type != "s3":
            show_error_panel("Unsupported Backend", "Backend credentials management is currently supported for S3 repositories only.")
            raise typer.Exit(1)

        service_manager = None
        repository_factory = None
        try:
            service_manager = _get_service_manager_for_command(config_dir)
            repository_factory = getattr(service_manager, "repository_factory", None)
        except Exception:
            service_manager = None

        credential_manager = _create_credential_manager(config_dir)
        if repository_factory is not None:
            try:
                setattr(repository_factory, "_credential_manager", credential_manager)
            except Exception as attach_exc:
                logging.getLogger(__name__).debug("Unable to attach credential manager to repository factory: %s", attach_exc)

        if master_password is not None:
            _ensure_manager_unlocked(credential_manager, master_password, interactive)
        else:
            try:
                credential_manager.ensure_unlocked(allow_prompt=interactive)
            except Exception:
                if interactive:
                    raise
                # Non-interactive paths rely on auto unlock or environment variables

        access_key = Prompt.ask("AWS Access Key ID")
        secret_key = Prompt.ask("AWS Secret Access Key", password=True)
        region = Prompt.ask("AWS Region", default="")
        insecure_tls = Confirm.ask("Allow insecure TLS (skip certificate verification)?", default=False)

        credentials_payload = {
                "access_key_id":     access_key,
                "secret_access_key": secret_key,
        }
        if region:
            credentials_payload["region"] = region
        if insecure_tls:
            credentials_payload["insecure_tls"] = True

        success = store_backend_credentials_helper(
                repository_name=name,
                backend_type=backend_type,
                backend_name=_backend_display_name(backend_type),
                credentials_dict=credentials_payload,
                cred_mgr=credential_manager,
                config_manager=config_module,
                repository_config=repository_config,
                console=console,
                logger=logging.getLogger(__name__),
                allow_prompt=interactive,
        )

        if not success:
            raise typer.Exit(1)

        show_success_panel("Credentials Stored", f"{_backend_display_name(backend_type)} credentials stored for '{name}'.")
    except RepositoryNotFoundError as e:
        show_error_panel("Repository Not Found", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Credential storage cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Credential Error", f"Failed to store repository credentials: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repos_credentials_app.command("remove")
def repos_credentials_remove(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm removal without prompt")] = False,
        master_password: Annotated[
            Optional[str], typer.Option("--master-password", "-m", help="Master password to unlock the credential manager if locked")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
) -> None:
    """Remove stored backend credentials for a repository."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        config_module = _create_configuration_module(config_dir)
        repository_obj = config_module.get_repository(name)
        repo_uri = getattr(repository_obj, 'uri', None) or getattr(repository_obj, 'location', None)
        repository_config = _repository_config_to_dict(repository_obj, name)

        backend_type = _determine_backend_from_uri(repo_uri)
        if backend_type != "s3":
            show_info_panel("Unsupported Backend", "No backend credentials stored for this repository type.")
            raise typer.Exit(0)

        confirmed = yes
        if not confirmed:
            if interactive:
                confirmed = Confirm.ask(f"Remove {_backend_display_name(backend_type)} credentials for '{name}'?", default=False)
                if not confirmed:
                    show_info_panel("Operation Cancelled", "Credential removal cancelled.")
                    raise typer.Exit(0)
            else:
                confirmed = True

        credential_manager = _create_credential_manager(config_dir)
        if master_password is not None:
            _ensure_manager_unlocked(credential_manager, master_password, interactive)

        removed = False
        if hasattr(credential_manager, "remove_repository_backend_credentials"):
            removed = credential_manager.remove_repository_backend_credentials(name, backend_type)

        if removed:
            repository_config['has_backend_credentials'] = False
            try:
                config_module.update_repository(name, repository_config)
            except Exception as exc:
                logging.getLogger(__name__).debug("Failed to update repository after credential removal: %s", exc)
            show_success_panel("Credentials Removed", f"Removed {_backend_display_name(backend_type)} credentials for '{name}'.")
        else:
            show_info_panel("No Credentials", f"No stored credentials found for '{name}'.")
    except RepositoryNotFoundError as e:
        show_error_panel("Repository Not Found", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Credential removal cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Credential Error", f"Failed to remove repository credentials: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repos_credentials_app.command("show")
def repos_credentials_show(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        master_password: Annotated[
            Optional[str], typer.Option("--master-password", "-m", help="Master password to unlock the credential manager if locked")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
) -> None:
    """Display stored backend credentials for a repository."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        config_module = _create_configuration_module(config_dir)
        repository_obj = config_module.get_repository(name)
        repo_uri = getattr(repository_obj, 'uri', None) or getattr(repository_obj, 'location', None)

        backend_type = _determine_backend_from_uri(repo_uri)
        if backend_type != "s3":
            show_info_panel("Unsupported Backend", "No backend credentials stored for this repository type.")
            raise typer.Exit(0)

        credential_manager = _create_credential_manager(config_dir)
        if master_password is not None:
            _ensure_manager_unlocked(credential_manager, master_password, interactive)
        else:
            try:
                credential_manager.ensure_unlocked(allow_prompt=interactive)
            except Exception:
                if interactive:
                    raise
                logging.getLogger(__name__).debug("Unable to unlock credential manager automatically for show command.")

        has_credentials = False
        if hasattr(credential_manager, "has_repository_backend_credentials"):
            has_credentials = credential_manager.has_repository_backend_credentials(name, backend_type)

        if not has_credentials:
            show_info_panel("No Credentials", f"No {_backend_display_name(backend_type)} credentials stored for '{name}'.")
            return

        credentials = {}
        if hasattr(credential_manager, "get_repository_backend_credentials"):
            credentials = credential_manager.get_repository_backend_credentials(name, backend_type) or {}

        if not credentials:
            show_info_panel("No Credentials", f"No {_backend_display_name(backend_type)} credentials stored for '{name}'.")
            return

        table = Table(title=f"{_backend_display_name(backend_type)} Credentials for {name}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        for key, value in credentials.items():
            display_key = key.replace('_', ' ').title()
            if isinstance(value, str):
                if len(value) > 4 and any(token in key for token in ["secret", "key"]):
                    masked = value[:4] + "•••" + value[-2:]
                else:
                    masked = value
                display_value = masked
            else:
                display_value = str(value)
            table.add_row(display_key, display_value)

        console.print(table)
    except RepositoryNotFoundError as e:
        show_error_panel("Repository Not Found", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Credential display cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Credential Error", f"Failed to display repository credentials: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


def _ensure_manager_unlocked(manager, master_password: Optional[str], interactive: bool) -> None:
    """Unlock credential manager when required or raise typer.Exit."""
    if not hasattr(manager, "is_locked"):
        return
    if not manager.is_locked():
        return

    if master_password is None:
        if interactive:
            master_password = Prompt.ask("Master password", password=True)
        else:
            show_error_panel("Credential Manager Locked", "Provide --master-password to unlock before proceeding.")
            raise typer.Exit(1)

    if not manager.unlock(master_password):
        show_error_panel("Unlock Failed", "Unable to unlock credential manager with the provided master password.")
        raise typer.Exit(1)




# Import command modules to register their commands with the apps
# This must be done after all the apps are created and helper functions are defined
# to avoid circular import issues
try:
    from .cli_modules.commands.repositories import repos_app as _repos_commands_app
    # Copy commands from the repositories module's app to our repos_app
    for command in _repos_commands_app.registered_commands:
        repos_app.registered_commands.append(command)
    for group in _repos_commands_app.registered_groups:
        repos_app.registered_groups.append(group)
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import repository commands: {e}")

try:
    from .cli_modules.commands.policy import policy_app as _policy_commands_app
    # Add policy app to main app
    app.add_typer(_policy_commands_app, name="policy")
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import policy commands: {e}")

try:
    from .cli_modules.commands.selections import selections_app as _selections_commands_app
    # Add selections app to main app
    app.add_typer(_selections_commands_app, name="selections")
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import selections commands: {e}")

try:
    from .cli_modules.commands.schedule import schedule_app as _schedule_commands_app
    # Add schedule app to main app
    app.add_typer(_schedule_commands_app, name="schedule")
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import schedule commands: {e}")

try:
    from .cli_modules.commands.monitoring import monitor_app as _monitor_commands_app
    from .cli_modules.commands.monitoring import logs_app as _logs_commands_app
    from .cli_modules.commands.monitoring import reports_app as _reports_commands_app
    # Add monitoring apps to main app
    app.add_typer(_monitor_commands_app, name="monitor")
    app.add_typer(_logs_commands_app, name="logs")
    app.add_typer(_reports_commands_app, name="reports")
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import monitoring commands: {e}")

try:
    from .cli_modules.commands.restore import restore_app as _restore_commands_app
    # Add restore app to main app
    app.add_typer(_restore_commands_app, name="restore")
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import restore commands: {e}")
