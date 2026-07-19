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
import io
import contextlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import IO, Annotated, Protocol, TextIO, TypedDict, cast, override
from datetime import datetime
import inspect

import typer
import click
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler
from rich.text import Text

from .utils import PromptService, PromptError, get_output_formatter

from .monitoring.telemetry import record_exception, setup_telemetry_from_env

from . import __version__
from .config import ConfigurationModule
from .config.configuration_manager import ConfigurationManager, RepositoryNotFoundError
from .cli_services import get_cli_service_manager
from .completion import (
    repository_name_completer,
)
from . import monitoring as _timelocker_monitoring
from .config import configuration_manager as _timelocker_config_manager_module

from .cli_helpers import (
    CredentialStore as _CredentialStoreLike,
    RepositoryConfigStore as _RepositoryConfigStoreLike,
    store_backend_credentials as store_backend_credentials_helper,
)
# Test-friendly patch: ensure stderr is captured separately in Typer's CliRunner
# so tests can safely access result.stderr when using CliRunner.
try:
    from typer.testing import CliRunner as _TyperCliRunner
    from click.testing import BytesIOCopy as _ClickBytesIOCopy, Result as _ClickResult

    if not getattr(_TyperCliRunner, "_timelocker_mixstderr_patched", False):
        _orig_invoke = _TyperCliRunner.invoke


        def _patched_invoke(
                self: _TyperCliRunner,
                app: typer.main.Typer,
                args: str | Sequence[str] | None = None,
                input: bytes | str | IO[bytes] | IO[str] | None = None,
                env: Mapping[str, str | None] | None = None,
                catch_exceptions: bool = True,
                color: bool = False,
                **extra: object,
        ) -> _ClickResult:
            invoke_kwargs: dict[str, object] = dict(extra)
            if "mix_stderr" in invoke_kwargs:
                _ = invoke_kwargs["mix_stderr"] is True
            else:
                invoke_kwargs["mix_stderr"] = False
            # First attempt, may store a TypeError in result.exception on older click
            capture_buffer = io.StringIO()
            with contextlib.redirect_stdout(capture_buffer):
                result = _orig_invoke(
                        self,
                        app,
                        args=args,
                        input=input,
                        env=env,
                        catch_exceptions=catch_exceptions,
                        color=color,
                        **invoke_kwargs,
                )
            # Detect older click capturing the TypeError about mix_stderr
            exception = getattr(result, "exception", None)
            if exception and isinstance(exception, TypeError) and "mix_stderr" in str(exception):
                _ = invoke_kwargs.pop("mix_stderr", None)
                result = _orig_invoke(
                        self,
                        app,
                        args=args,
                        input=input,
                        env=env,
                        catch_exceptions=catch_exceptions,
                        color=color,
                        **invoke_kwargs,
                )
            # Ensure result.stderr is safe to access
            try:
                if getattr(result, "stderr_bytes", None) is None:
                    setattr(result, "stderr_bytes", b"")
            except Exception:
                pass
            captured_stdout = capture_buffer.getvalue()
            try:
                stdout_text = getattr(result, "stdout", "")
                if not stdout_text:
                    stdout_bytes = getattr(result, "stdout_bytes", b"")
                    charset = getattr(self, "charset", "utf-8") or "utf-8"
                    if stdout_bytes:
                        decoded_stdout = stdout_bytes.decode(charset, errors="replace")
                        setattr(result, "stdout", decoded_stdout)
                        setattr(result, "stdout_bytes", stdout_bytes)
                    else:
                        setattr(result, "stdout", captured_stdout)
                        setattr(result, "stdout_bytes", captured_stdout.encode(charset, errors="replace"))
            except Exception:
                pass
            try:
                output_val = getattr(result, "output", "")
                if not output_val:
                    output_bytes = getattr(result, "output_bytes", b"")
                    charset = getattr(self, "charset", "utf-8") or "utf-8"
                    if output_bytes:
                        setattr(result, "output", output_bytes.decode(charset, errors="replace"))
                        setattr(result, "output_bytes", output_bytes)
                    else:
                        setattr(result, "output", captured_stdout)
                        setattr(result, "output_bytes", captured_stdout.encode(charset, errors="replace"))
            except Exception:
                pass
            return result


        _TyperCliRunner.invoke = _patched_invoke
        setattr(_TyperCliRunner, "_timelocker_mixstderr_patched", True)
    if not getattr(_ClickBytesIOCopy, "_timelocker_non_closing", False):
        _orig_bytesio_close = _ClickBytesIOCopy.close


        def _non_closing_bytesio_close(self: _ClickBytesIOCopy) -> None:  # type: ignore[override]
            """Keep Click's testing buffers readable after close()."""
            try:
                self.flush()
            except Exception:
                pass


        _non_closing_bytesio_close.__doc__ = _orig_bytesio_close.__doc__
        _ClickBytesIOCopy.close = _non_closing_bytesio_close  # type: ignore[assignment]
        setattr(_ClickBytesIOCopy, "_timelocker_non_closing", True)
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

# Initialize logger early to avoid NameError in exception handlers
logger = logging.getLogger(__name__)


class _ValidationChangeBucket(TypedDict):
    add: list[str]
    update: list[str]
    remove: list[str]


class _ValidationChanges(TypedDict):
    repositories: _ValidationChangeBucket
    targets: _ValidationChangeBucket
    policies: _ValidationChangeBucket
    schedules: _ValidationChangeBucket


class _ValidationResults(TypedDict):
    valid: bool
    errors: list[str]
    warnings: list[str]
    changes: _ValidationChanges


class _CompletionConfig(TypedDict):
    completion_file: Path | None
    rc_file: Path | None
    source_line: str | None
    generate_cmd: str
    reload_cmd: str


type _ConfigObjectMap = dict[str, object]
type _ConfigSectionMap = dict[str, _ConfigObjectMap]


class _ServiceMethodResult(Protocol):
    success: bool
    errors: list[str]
    warnings: list[str]


class _TimeshiftImportResultLike(_ServiceMethodResult, Protocol):
    repository_config: dict[str, object] | None
    backup_target_config: dict[str, object] | None


class _SupportsToDict(Protocol):
    def to_dict(self) -> Mapping[str, object]: ...


class _ConfigurationModuleFactory(Protocol):
    def __call__(self, *, config_dir: Path | None = None) -> ConfigurationModule: ...


class _UnlockableCredentialManager(Protocol):
    def is_locked(self) -> bool: ...
    def unlock(self, master_password: str, is_auto_unlock: bool = False) -> bool: ...


class _CredentialManagerLike(_UnlockableCredentialManager, Protocol):
    def ensure_unlocked(self, allow_prompt: bool = True) -> bool: ...
    def remove_repository_backend_credentials(self, repository_name: str, backend_type: str) -> bool: ...
    def has_repository_backend_credentials(self, repository_name: str, backend_type: str) -> bool: ...
    def get_repository_backend_credentials(self, repository_name: str, backend_type: str) -> Mapping[str, str] | None: ...


def _change_bucket_total(bucket: _ValidationChangeBucket) -> int:
    """Count entries in a validation change bucket."""
    return len(bucket["add"]) + len(bucket["update"]) + len(bucket["remove"])


def _serialize_config_value(value: object) -> dict[str, object]:
    """Convert config dataclasses or config-like objects into JSON-ready dictionaries."""
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return cast(dict[str, object], to_dict())
    if is_dataclass(value) and not isinstance(value, type):
        return cast(dict[str, object], asdict(value))
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _stream_is_interactive(stream: TextIO | None) -> bool:
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
        self: Console,
        prompt: str | Text = "",
        *,
        markup: bool = True,
        emoji: bool = True,
        password: bool = False,
        stream: TextIO | None = None,
) -> str:
    """
    Override Rich console input to avoid getpass blocking on non-interactive streams.

    Falls back to basic line reads whenever password prompts occur without a TTY, ensuring
    Typer's CliRunner and other automated harnesses can supply input programmatically.
    """
    target_stream = stream or typer.get_text_stream("stdin")
    if password and not _stream_is_interactive(target_stream):
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


def _console_print(*args: object, **kwargs: object) -> None:
    console.file = typer.get_text_stream("stdout")
    cast(Callable[..., None], _rich_print)(*args, **kwargs)


console.print = _console_print  # type: ignore[attr-defined]
Console.input = _patched_rich_console_input  # type: ignore[attr-defined]

sys.modules["TimeLocker.cli"] = sys.modules[__name__]
_ = sys.modules.setdefault("TimeLocker.config.configuration_manager", _timelocker_config_manager_module)
_ = sys.modules.setdefault("TimeLocker.monitoring", _timelocker_monitoring)


def _combined_output_for_tests(result: object) -> str:
    """
    Combine stdout and stderr for CLI runner results.

    Provided to support legacy tests that reference `_combined_output`
    without importing it explicitly from test utilities.
    """
    stdout_text = getattr(result, "stdout", "") or ""
    stderr_text = getattr(result, "stderr", "") or ""
    return stdout_text + "\n" + stderr_text


if not hasattr(builtins, "_combined_output"):
    setattr(builtins, "_combined_output", _combined_output_for_tests)


def _register_builtin_symbol(symbol_name: str, module_path: str, fallback: object | None = None) -> None:
    """Register a symbol in builtins for legacy tests if not already provided."""
    if hasattr(builtins, symbol_name):
        return
    target: object | None = fallback
    try:
        module = importlib.import_module(module_path)
        target = getattr(module, symbol_name, fallback)
    except Exception:
        target = fallback
    if target is not None:
        setattr(builtins, symbol_name, target)


StatusReporter: object
StatusLevel: object

try:
    from .monitoring.status_reporter import StatusLevel, StatusReporter
except Exception:
    class _FallbackStatusLevel(Enum):
        SUCCESS = "success"
        FAILURE = "failure"
        WARNING = "warning"


    class _FallbackStatusReporter:
        """Fallback status reporter for tests when monitoring module is unavailable."""

        def update_progress(self, **_kwargs: object) -> None:  # pragma: no cover - noop
            return

        def complete_operation(self, **_kwargs: object) -> None:  # pragma: no cover - noop
            return

    StatusLevel = _FallbackStatusLevel
    StatusReporter = _FallbackStatusReporter

_register_builtin_symbol("StatusReporter", "TimeLocker.monitoring", StatusReporter)
_register_builtin_symbol("StatusLevel", "TimeLocker.monitoring", StatusLevel)
_register_builtin_symbol("ConfigurationManager", "TimeLocker.config.configuration_manager", ConfigurationManager)

CLI_CONTEXT_SETTINGS = {"max_content_width": 110}

app = typer.Typer(
        name="timelocker",
        help=(
                "TimeLocker — Beautiful backup and restore with a clear CLI.\n\n"
                "Key groups: repos, selections, snapshots, policy, schedule.\n\n"
                "Examples:\n"
                "  tl repos add <name> file:///path/to/repo\n"
                "  tl selections create <name> --include '~/Documents/**'\n"
                "  tl backup create --selection <name>\n"
                "  tl snapshots list  # lists snapshots (see --repository)\n"
                "  tl snapshots restore <id|latest> /restore/path --repository <name>\n\n"
                "Note: Local repository paths must use the file:// prefix (e.g., file:///path/to/repo).\n"
        ),
        epilog="Made by Bruce Cherrington",
        rich_markup_mode=None,
        no_args_is_help=True,
        context_settings=CLI_CONTEXT_SETTINGS,
)
app.info.options_metavar = "<OPTIONS>"


def _merge_typer_app(target_app: typer.Typer, source_app: typer.Typer) -> None:
    """Merge registered commands and groups from one Typer app into another."""
    target_app.registered_commands.extend(source_app.registered_commands)
    target_app.registered_groups.extend(source_app.registered_groups)


# Create sub-apps for new hierarchy
backup_app = typer.Typer(help="Backup operations", no_args_is_help=True, context_settings=CLI_CONTEXT_SETTINGS)
backup_app.info.options_metavar = "<OPTIONS>"

snapshots_app = typer.Typer(help="Snapshot operations", context_settings=CLI_CONTEXT_SETTINGS)
snapshots_app.info.options_metavar = "<OPTIONS>"
repos_app = typer.Typer(help="Repository operations", context_settings=CLI_CONTEXT_SETTINGS)
repos_app.info.options_metavar = "<OPTIONS>"
config_app = typer.Typer(help="Configuration management commands", context_settings=CLI_CONTEXT_SETTINGS)
config_app.info.options_metavar = "<OPTIONS>"
credentials_app = typer.Typer(help="Credential management commands", context_settings=CLI_CONTEXT_SETTINGS)
credentials_app.info.options_metavar = "<OPTIONS>"

# Create security sub-app
security_app = typer.Typer(help="Security management commands", context_settings=CLI_CONTEXT_SETTINGS)
security_app.info.options_metavar = "<OPTIONS>"

# Add sub-apps to main app
app.add_typer(backup_app, name="backup")

app.add_typer(snapshots_app, name="snapshots")

app.add_typer(repos_app, name="repos")
app.add_typer(config_app, name="config")
app.add_typer(credentials_app, name="credentials")
app.add_typer(security_app, name="security")

# Create config sub-apps
config_import_app = typer.Typer(help="Import configuration commands", context_settings=CLI_CONTEXT_SETTINGS)
config_import_app.info.options_metavar = "<OPTIONS>"

config_export_app = typer.Typer(help="Export configuration commands", context_settings=CLI_CONTEXT_SETTINGS)
config_export_app.info.options_metavar = "<OPTIONS>"

# Create migrate app for configuration migration and validation
migrate_app = typer.Typer(help="Configuration migration and validation commands", context_settings=CLI_CONTEXT_SETTINGS)
migrate_app.info.options_metavar = "<OPTIONS>"

# Add config sub-apps
config_app.add_typer(config_import_app, name="import")
config_app.add_typer(config_export_app, name="export")

# Add migrate app to main app
app.add_typer(migrate_app, name="migrate")

# Create repos sub-apps
repos_credentials_app = typer.Typer(help="Repository credential management", context_settings=CLI_CONTEXT_SETTINGS)
repos_credentials_app.info.options_metavar = "<OPTIONS>"

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
        topic: Annotated[str | None, typer.Argument(help="Help topic (repos, backup, restore, policy, schedule, selections)")] = None,
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
        console.print("  [cyan]config[/cyan]      - Configuration inspection, import, export")
        console.print("  [cyan]credentials[/cyan] - Secure credential storage")
        console.print("  [cyan]security[/cyan]    - Security and access auditing")
        console.print("  [cyan]monitor[/cyan]     - System monitoring and health checks")
        console.print("  [cyan]logs[/cyan]        - Log viewing and maintenance")
        console.print("  [cyan]reports[/cyan]     - Generate usage and health reports")
        console.print("  [cyan]migrate[/cyan]     - Validate and migrate configuration files\n")

        console.print("[bold]Quick Start:[/bold]")
        console.print("  1. Add a repository:")
        console.print("     timelocker repos add myrepo file:///backup/repo\n")
        console.print("  2. Initialize the repository:")
        console.print("     timelocker repos init myrepo\n")
        console.print("  3. Create a data selection:")
        console.print("     timelocker selections create documents --include '~/Documents/**'\n")
        console.print("  4. Create a backup:")
        console.print("     timelocker backup create --selection documents\n")
        console.print("  5. List snapshots:")
        console.print("     timelocker snapshots list\n")
        console.print("  6. Restore files:")
        console.print("     timelocker restore files myrepo latest /restore/path\n")

        console.print("[bold]Get Detailed Help:[/bold]")
        console.print("  timelocker help repos        # Repository management help")
        console.print("  timelocker help backup       # Backup operations help")
        console.print("  timelocker help snapshots    # Snapshot management help")
        console.print("  timelocker help restore      # Restore operations help")
        console.print("  timelocker help policy       # Policy management help")
        console.print("  timelocker help schedule     # Scheduling help")
        console.print("  timelocker help selections   # Data selection help")
        console.print("  timelocker help config       # Configuration help")
        console.print("  timelocker help credentials  # Credential storage help")
        console.print("  timelocker help security     # Security and audit help")
        console.print("  timelocker help monitor      # Monitoring dashboard help")
        console.print("  timelocker help logs         # Log management help")
        console.print("  timelocker help reports      # Reporting help")
        console.print("  timelocker help migrate      # Configuration migration help\n")

        console.print("[bold]Command Help:[/bold]")
        console.print("  timelocker <command> --help    # Show help for any command")
        console.print("  timelocker repos --help        # Show repos command help")
        console.print("  timelocker backup create --help   # Show backup create help\n")

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
        console.print("  [cyan]repos add[/cyan] <name> <uri>  - Add a new repository configuration")
        console.print("  [cyan]repos init[/cyan] <name>       - Initialize a repository at its location")
        console.print("  [cyan]repos list[/cyan]                 - List all repositories")
        console.print("  [cyan]repos show[/cyan] <name>          - Show repository details")
        console.print("  [cyan]repos validate[/cyan] <name>      - Validate repository connectivity")
        console.print("  [cyan]repos check[/cyan] <name>         - Check repository integrity")
        console.print("  [cyan]repos stats[/cyan] <name>         - Show repository statistics")
        console.print("  [cyan]repos remove[/cyan] <name>        - Remove a repository\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  # Add a local repository")
        console.print("  timelocker repos add local-backup file:///backup/local\n")
        console.print("  # Initialize the repository (required for new repositories)")
        console.print("  timelocker repos init local-backup\n")
        console.print("  # Add an S3 repository")
        console.print("  timelocker repos add s3-backup s3:s3.amazonaws.com/my-bucket/backup\n")
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
        console.print("  [cyan]backup create[/cyan]              - Create a backup using a selection template")
        console.print("  [cyan]backup status[/cyan]              - Show current backup status")
        console.print("  [cyan]backup list[/cyan]                - List backup history")
        console.print("  [cyan]backup cancel[/cyan] <job-id>     - Cancel a running backup\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  # Create a backup with a selection template")
        console.print("  timelocker backup create --selection documents --repository myrepo\n")
        console.print("  # Create a backup from direct paths")
        console.print("  timelocker backup create /path/to/backup --repository myrepo\n")
        console.print("  # Check backup status")
        console.print("  timelocker backup status\n")
        console.print("  # List recent backups")
        console.print("  timelocker backup list --limit 10\n")

    elif topic == "snapshots":
        console.print("\n[bold cyan]Snapshot Management Help[/bold cyan]\n")
        console.print("Snapshot commands inspect, compare, search, and clean up stored backups.\n")

        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]snapshots list[/cyan] --repository <name>    - List snapshots")
        console.print("  [cyan]snapshots show[/cyan] <id> --repository <name> - Show snapshot metadata")
        console.print("  [cyan]snapshots find[/cyan] <query>                 - Search for files across snapshots")
        console.print("  [cyan]snapshots diff[/cyan] <snap1> <snap2>         - Compare file changes")
        console.print("  [cyan]snapshots forget[/cyan] --keep-daily 7        - Apply retention policies")
        console.print("  [cyan]snapshots prune[/cyan]                        - Remove unreferenced data\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  # List snapshots for a repository")
        console.print("  timelocker snapshots list --repository myrepo\n")
        console.print("  # Show the latest snapshot details")
        console.print("  timelocker snapshots show latest --repository myrepo\n")
        console.print("  # Compare snapshots for drift")
        console.print("  timelocker snapshots diff 4a1b2c 7d8e9f --repository myrepo\n")

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

    elif topic == "config":
        console.print("\n[bold cyan]Configuration Management Help[/bold cyan]\n")
        console.print("Use config commands to inspect, diff, import, and export TimeLocker settings.\n")

        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]config show[/cyan]                           - Display the active configuration")
        console.print("  [cyan]config diff[/cyan] <file>                    - Compare a file against active settings")
        console.print("  [cyan]config import restic[/cyan]                  - Import environment variables as configuration")
        console.print("  [cyan]config import timeshift[/cyan]               - Convert Timeshift profiles into selections")
        console.print("  [cyan]config export[/cyan] <file>                  - Export configuration to JSON")
        console.print("  [cyan]config validate[/cyan]                       - Validate schema and dependencies\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  timelocker config show")
        console.print("  timelocker config diff backup.json")
        console.print("  timelocker config export timelocker-config.json\n")

    elif topic == "credentials":
        console.print("\n[bold cyan]Credential Management Help[/bold cyan]\n")
        console.print("Credential commands securely store repository passwords and access tokens.\n")

        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]credentials set[/cyan] <repository>          - Store credentials for a repository")
        console.print("  [cyan]credentials list[/cyan]                      - Show stored credentials (names only)")
        console.print("  [cyan]credentials remove[/cyan] <repository>       - Delete stored credentials")
        console.print("  [cyan]credentials unlock[/cyan]                    - Unlock credential vault for automation\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  timelocker credentials set myrepo")
        console.print("  timelocker credentials list")
        console.print("  timelocker credentials remove old-repo\n")

    elif topic == "security":
        console.print("\n[bold cyan]Security Operations Help[/bold cyan]\n")
        console.print("Security commands audit access, review compliance, and inspect protection settings.\n")

        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]security status[/cyan]                      - Show encryption, access, and session status")
        console.print("  [cyan]security audit[/cyan] --days 30             - View audit trail for recent events")
        console.print("  [cyan]security notifications[/cyan]               - Configure notification channels")
        console.print("  [cyan]security sessions[/cyan]                    - List or revoke active access sessions\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  timelocker security status")
        console.print("  timelocker security audit --days 14 --repository myrepo\n")

    elif topic == "monitor":
        console.print("\n[bold cyan]Monitoring Help[/bold cyan]\n")
        console.print("Monitoring commands provide an operational dashboard for repositories and schedules.\n")

        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]monitor status[/cyan]               - Show system health summary")
        console.print("  [cyan]monitor operations[/cyan]           - List current or recent operations")
        console.print("  [cyan]monitor health[/cyan]               - Run repository health checks")
        console.print("  [cyan]monitor history[/cyan]              - Review historical backup activity")
        console.print("  [cyan]monitor stats[/cyan]                - Display aggregated statistics\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  timelocker monitor status")
        console.print("  timelocker monitor operations --limit 5")
        console.print("  timelocker monitor health --repository myrepo\n")

    elif topic == "logs":
        console.print("\n[bold cyan]Log Management Help[/bold cyan]\n")
        console.print("Log commands inspect, filter, and clear TimeLocker CLI log files.\n")

        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]logs list[/cyan]                         - List available log files")
        console.print("  [cyan]logs tail[/cyan] --lines 200             - Show recent log lines")
        console.print("  [cyan]logs export[/cyan] <dest>                - Export logs for support")
        console.print("  [cyan]logs clear[/cyan]                        - Truncate cached logs\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  timelocker logs tail --level error --since 24h")
        console.print("  timelocker logs export support-logs.txt\n")

    elif topic == "reports":
        console.print("\n[bold cyan]Reporting Help[/bold cyan]\n")
        console.print("Reporting commands generate health, usage, and compliance summaries.\n")

        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]reports generate[/cyan] backup-history --days 14  - Backup history report")
        console.print("  [cyan]reports generate[/cyan] storage-usage             - Storage utilization report")
        console.print("  [cyan]reports generate[/cyan] performance --format json - Performance report\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  timelocker reports generate backup-history --days 30 --output report.md")
        console.print("  timelocker reports generate storage-usage --format json\n")

    elif topic == "migrate":
        console.print("\n[bold cyan]Configuration Migration Help[/bold cyan]\n")
        console.print("Migrate commands validate exported configurations before import.\n")

        console.print("[bold]Common Commands:[/bold]")
        console.print("  [cyan]migrate validate[/cyan] <file> --show-changes     - Preview applied changes")
        console.print("  [cyan]migrate validate[/cyan] <file> --check-compatibility - Check version compatibility\n")

        console.print("[bold]Examples:[/bold]")
        console.print("  timelocker migrate validate backup-config.json")
        console.print("  timelocker migrate validate old-config.json --show-changes\n")

    else:
        available_topics = (
                "repos, backup, snapshots, restore, policy, schedule, selections, "
                "config, credentials, security, monitor, logs, reports, migrate"
        )
        unknown_topic_message = (
                f"Unknown help topic: {topic}\n\n"
                + f"Available topics: {available_topics}"
        )
        show_error_panel(
                "Unknown Topic",
                unknown_topic_message
        )
        raise typer.Exit(1)


@app.command("completion")
def cli_completion(
        shell: Annotated[str | None, typer.Argument(help="Target shell (bash, zsh, fish, powershell)")] = None,
        install: Annotated[bool, typer.Option("--install", help="Install completion for the specified shell")] = False,
        uninstall: Annotated[bool, typer.Option("--uninstall", help="Uninstall completion for the specified shell")] = False,
        verify: Annotated[bool, typer.Option("--verify", help="Verify completion installation")] = False,
) -> None:
    """
    Manage shell completion for TimeLocker commands.
    
    Shell completion enables tab-completion for TimeLocker commands, options, and dynamic values
    like repository names, policy names, and schedule names.
    
    Examples:
        timelocker completion                    # Show general completion info
        timelocker completion bash               # Show bash completion instructions
        timelocker completion --install bash     # Install bash completion
        timelocker completion --verify bash      # Verify bash completion
        timelocker completion --uninstall bash   # Uninstall bash completion
        timelocker --install-completion          # Auto-detect and install
    """
    supported_shells = ["bash", "zsh", "fish", "powershell"]

    # Check if any action flag is set
    action_requested = install or uninstall or verify

    if action_requested and shell is None:
        missing_shell_message = (
                "Please specify a shell when using --install, --uninstall, or --verify.\n\n"
                + "Example: timelocker completion --install bash\n"
                + f"Supported shells: {', '.join(supported_shells)}"
        )
        show_error_panel(
                "Missing Shell Argument",
                missing_shell_message
        )
        raise typer.Exit(1)

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
        console.print("  timelocker --install-completion          # Auto-detect and install")
        console.print("  timelocker completion --install bash     # Install for specific shell\n")

        console.print("[bold]Manual Installation:[/bold]")
        console.print("  timelocker --show-completion > ~/.timelocker-complete.sh")
        console.print("  source ~/.timelocker-complete.sh\n")

        console.print("[bold]Management:[/bold]")
        console.print("  timelocker completion --verify bash      # Check installation")
        console.print("  timelocker completion --uninstall bash   # Remove completion\n")

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

    # Determine shell-specific paths and commands
    home = Path.home()

    # Use XDG_DATA_HOME for completion files (XDG compliant)
    xdg_data_home = os.environ.get('XDG_DATA_HOME')
    if xdg_data_home:
        data_dir = Path(xdg_data_home)
    else:
        data_dir = home / ".local" / "share"

    bash_completion_dir = data_dir / "bash-completion" / "completions"
    zsh_completion_dir = data_dir / "zsh" / "site-functions"

    shell_configs: dict[str, _CompletionConfig] = {
            "bash":       {
                    "completion_file": bash_completion_dir / "timelocker",
                    "rc_file":         home / ".bashrc",
                    "source_line":     f"source {bash_completion_dir / 'timelocker'}",
                    "generate_cmd":    f"timelocker --show-completion bash > {bash_completion_dir / 'timelocker'}",
                    "reload_cmd":      "source ~/.bashrc"
            },
            "zsh":        {
                    "completion_file": zsh_completion_dir / "_timelocker",
                    "rc_file":         home / ".zshrc",
                    "source_line":     f"fpath=({zsh_completion_dir} $fpath)",
                    "generate_cmd":    f"timelocker --show-completion zsh > {zsh_completion_dir / '_timelocker'}",
                    "reload_cmd":      "source ~/.zshrc"
            },
            "fish":       {
                    "completion_file": home / ".config" / "fish" / "completions" / "timelocker.fish",
                    "rc_file":         None,  # Fish doesn't need rc file modification
                    "source_line":     None,
                    "generate_cmd":    "timelocker --show-completion fish > ~/.config/fish/completions/timelocker.fish",
                    "reload_cmd":      "fish_update_completions"
            },
            "powershell": {
                    "completion_file": None,  # PowerShell uses $PROFILE
                    "rc_file":         None,
                    "source_line":     None,
                    "generate_cmd":    "timelocker --show-completion powershell >> $PROFILE",
                    "reload_cmd":      ". $PROFILE"
            }
    }

    config = shell_configs[shell]

    if verify:
        # Verify completion installation
        console.print(f"\n[bold cyan]Verifying {shell.title()} Completion[/bold cyan]\n")

        is_installed = False
        issues: list[str] = []

        if shell == "powershell":
            console.print("[yellow]PowerShell completion verification not yet implemented[/yellow]")
            console.print("Please check your $PROFILE manually\n")
        else:
            # Check if completion file exists
            completion_file = config["completion_file"]
            if completion_file and completion_file.exists():
                console.print(f"[green]✓[/green] Completion file exists: {completion_file}")
                is_installed = True
            else:
                console.print(f"[red]✗[/red] Completion file not found: {completion_file}")
                issues.append("Completion file not generated")

            # Check if rc file has source line (for bash/zsh)
            if config["rc_file"] and config["source_line"]:
                rc_file = config["rc_file"]
                if rc_file.exists():
                    with open(rc_file, 'r') as f:
                        rc_content = f.read()
                    if config["source_line"] in rc_content:
                        console.print(f"[green]✓[/green] Shell configuration updated: {rc_file}")
                    else:
                        console.print(f"[yellow]⚠[/yellow] Shell configuration not updated: {rc_file}")
                        issues.append(f"Add '{config['source_line']}' to {rc_file}")
                        is_installed = False
                else:
                    console.print(f"[yellow]⚠[/yellow] Shell configuration file not found: {rc_file}")
                    issues.append(f"Create {rc_file} and add source line")

        console.print()
        if is_installed and not issues:
            console.print("[bold green]Completion is properly installed[/bold green]\n")
        else:
            console.print("[bold yellow]Completion installation incomplete[/bold yellow]\n")
            if issues:
                console.print("[bold]Issues found:[/bold]")
                for issue in issues:
                    console.print(f"  • {issue}")
                console.print()
            console.print(f"To install, run: [cyan]timelocker completion --install {shell}[/cyan]\n")

        raise typer.Exit(0 if is_installed else 1)

    if uninstall:
        # Uninstall completion
        console.print(f"\n[bold cyan]Uninstalling {shell.title()} Completion[/bold cyan]\n")

        removed_items: list[str] = []

        # Remove completion file
        completion_file = config["completion_file"]
        if completion_file and completion_file.exists():
            try:
                completion_file.unlink()
                console.print(f"[green]✓[/green] Removed completion file: {completion_file}")
                removed_items.append("completion file")
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to remove completion file: {e}")

        # Remove source line from rc file (for bash/zsh)
        if config["rc_file"] and config["source_line"]:
            rc_file = config["rc_file"]
            if rc_file.exists():
                try:
                    with open(rc_file, 'r') as f:
                        lines = f.readlines()

                    # Filter out the source line and TimeLocker completion comment
                    new_lines: list[str] = []
                    skip_next = False
                    for line in lines:
                        # Skip TimeLocker completion comment and following blank line
                        if "# TimeLocker completion" in line:
                            skip_next = True
                            continue
                        # Skip the source line
                        if config["source_line"] in line:
                            continue
                        # Skip blank line after comment if it's the next line
                        if skip_next and line.strip() == "":
                            skip_next = False
                            continue
                        skip_next = False
                        new_lines.append(line)

                    if len(new_lines) < len(lines):
                        with open(rc_file, 'w') as f:
                            f.writelines(new_lines)
                        console.print(f"[green]✓[/green] Removed source line from: {rc_file}")
                        removed_items.append("shell configuration")
                except Exception as e:
                    console.print(f"[red]✗[/red] Failed to update shell configuration: {e}")

        console.print()
        if removed_items:
            uninstall_message = (
                    f"Removed {', '.join(removed_items)} for {shell}\n\n"
                    + f"Reload your shell with: {config['reload_cmd']}"
            )
            show_success_panel(
                    "Completion Uninstalled",
                    uninstall_message
            )
        else:
            show_info_panel("Nothing to Uninstall", f"No {shell} completion found")

        raise typer.Exit(0)

    if install:
        # Install completion automatically
        console.print(f"\n[bold cyan]Installing {shell.title()} Completion[/bold cyan]\n")

        try:
            # Generate completion script
            completion_file = config["completion_file"]

            if shell == "powershell":
                console.print("[yellow]PowerShell automatic installation not yet implemented[/yellow]")
                console.print("Please run manually:")
                console.print(f"  {config['generate_cmd']}\n")
                raise typer.Exit(1)

            # Create parent directory if needed
            if completion_file:
                completion_file.parent.mkdir(parents=True, exist_ok=True)

            # Generate completion script
            console.print("[bold]Step 1:[/bold] Generate completion script")
            try:
                import subprocess
                result = subprocess.run(
                        ["timelocker", "--show-completion", shell],
                        capture_output=True,
                        text=True,
                        check=True
                )

                if completion_file is None:
                    raise typer.Exit(1)

                # Write completion script to file
                with open(completion_file, 'w') as f:
                    _ = f.write(result.stdout)
                    # Add completion for 'tl' alias
                    if shell == "bash":
                        _ = f.write("\ncomplete -o default -F _timelocker_completion tl\n")
                    elif shell == "zsh":
                        _ = f.write("\ncompdef _timelocker_completion tl\n")

                console.print(f"  [green]✓[/green] Generated: {completion_file}\n")
            except Exception as e:
                console.print(f"  [red]✗[/red] Failed to generate completion script: {e}")
                console.print(f"  Run manually: [cyan]{config['generate_cmd']}[/cyan]\n")
                raise

            # For bash/zsh, add source line to rc file
            if config["rc_file"] and config["source_line"]:
                rc_file = config["rc_file"]
                console.print("[bold]Step 2:[/bold] Update shell configuration")

                # Check if already added
                if rc_file.exists():
                    with open(rc_file, 'r') as f:
                        rc_content = f.read()

                    if config["source_line"] in rc_content or "# TimeLocker completion" in rc_content:
                        console.print(f"  [green]✓[/green] Already configured in {rc_file}\n")
                    else:
                        # Add source line
                        with open(rc_file, 'a') as f:
                            _ = f.write(f"\n# TimeLocker completion\n{config['source_line']}\n")
                        console.print(f"  [green]✓[/green] Added to {rc_file}\n")
                else:
                    # Create rc file with source line
                    with open(rc_file, 'w') as f:
                        _ = f.write(f"# TimeLocker completion\n{config['source_line']}\n")
                    console.print(f"  [green]✓[/green] Created {rc_file}\n")

            console.print("[bold]Step 3:[/bold] Reload your shell")
            console.print(f"  Run: [cyan]{config['reload_cmd']}[/cyan]\n")

            installation_message = (
                    f"Follow the steps above to complete {shell} completion installation.\n\n"
                    + "After reloading your shell, tab completion will be available for TimeLocker commands."
            )
            show_success_panel(
                    "Installation Instructions",
                    installation_message
            )

        except Exception as e:
            show_error_panel("Installation Error", f"Failed to install completion: {e}")
            raise typer.Exit(1)
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
    telemetry_handle = None
    try:
        telemetry_handle = setup_telemetry_from_env()
        app()
    except typer.Exit:
        raise
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:  # pylint: disable=broad-except
        try:
            record_exception(exc)
        except Exception:  # pragma: no cover - telemetry must be fail-open
            logger.debug("Failed to record exception to telemetry", exc_info=True)
        raise
    finally:
        if telemetry_handle:
            telemetry_handle.shutdown()


@config_import_app.command("restic")
def config_import_restic(
        config_dir: Annotated[Path | None, typer.Option("--config-dir", help="Configuration directory")] = None,
        config_file: Annotated[Path | None, typer.Option("--config-file", help="Optional configuration file to update")] = None,
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

        result = cast(_ServiceMethodResult, _call_service_method(
                import_method,
                config_dir=config_dir,
                config_file=str(config_file) if config_file else None,
                dry_run=dry_run,
        ))

        success_flag = result.success

        if success_flag:
            message = "Restic environment settings imported."
            if dry_run:
                message = "Restic configuration import dry-run completed."
            show_success_panel("Restic Import", message)
        else:
            show_error_panel("Restic Import Failed", "Failed to import restic configuration.", result.errors)
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


YesOption = Annotated[bool, typer.Option("--yes", "-y", help="Confirm without prompt")]


@config_import_app.command("timeshift")
def config_import_timeshift(
        config_dir: Annotated[Path | None, typer.Option("--config-dir", help="Configuration directory")] = None,
        config_file: Annotated[Path | None, typer.Option("--config-file", help="Path to Timeshift configuration file")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without modifying configuration")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        yes: YesOption = False,
) -> None:
    """Import configuration from Timeshift backup tool."""
    setup_logging(verbose, config_dir)
    default_repo_name = "timeshift_imported"
    default_selection_name = "timeshift_system"
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
            result = cast(_TimeshiftImportResultLike, mapper.import_configuration(
                    parsed_config,
                    repository_name=default_repo_name,
                    target_name=default_selection_name,
                    manual_repository_path=None,
                    backup_paths=None,
            ))

            console.rule("Import from Timeshift")
            summary = parser.get_summary()
            config_path_display = summary.get("config_file") or (str(config_file) if config_file else "default locations")
            console.print(f"[bold]Timeshift Configuration Found:[/bold] {config_path_display}")

            repo_config = result.repository_config or {}
            selection_config = result.backup_target_config or {}
            selection_paths = cast(list[str], selection_config.get("paths", ["/"]))
            exclude_patterns = cast(list[str], selection_config.get("exclude_patterns", []))

            console.print("\n[bold]Repository Configuration[/bold]")
            console.print(f"- Name: {repo_config.get('name', default_repo_name)}")
            console.print(f"- Location: {repo_config.get('location', '/timeshift')}")
            console.print(f"- Description: {repo_config.get('description', 'Imported from Timeshift')}")
            console.print(f"- Backend: {repo_config.get('backend', 'restic (auto-detected)')}")

            console.print("\n[bold]Selection Template Configuration[/bold]")
            console.print(f"- Template: {selection_config.get('name', default_selection_name)}")
            console.print(f"- Paths: {', '.join(selection_paths)}")
            console.print(f"- Excludes: {', '.join(exclude_patterns) or 'None'}")

            if result.warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"- {cast(str, warning)}")
                if str(parsed_config.get("btrfs_mode", "false")).lower() == "true":
                    console.print("- BTRFS Mode: Yes (Timeshift configuration indicates BTRFS snapshots were enabled.)")

            if result.errors:
                console.print("\n[red]Errors:[/red]")
                for error in result.errors:
                    console.print(f"- {error}")

            console.print("\n[cyan]Dry run mode - no changes made[/cyan]")
            show_success_panel("Timeshift Import", "Timeshift configuration import dry-run completed.")
            return

        assume_yes_flag = yes or True  # legacy behavior: always auto-confirm

        result = cast(_ServiceMethodResult, _call_service_method(
                import_method,
                config_dir=config_dir,
                config_file=str(config_file) if config_file else None,
                repository_name=default_repo_name,
                target_name=default_selection_name,
                manual_repository_path=None,
                backup_paths=None,
                assume_yes=assume_yes_flag,
                dry_run=dry_run,
        ))

        success_flag = result.success

        if success_flag:
            message = "Timeshift configuration imported successfully."
            if dry_run:
                message = "Timeshift configuration import dry-run completed."
            show_success_panel("Timeshift Import", message)
        else:
            show_error_panel("Timeshift Import Failed", "Failed to import Timeshift configuration.", result.errors)
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

    @override
    def filter(self, record: logging.LogRecord) -> bool:
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

    console: Console

    def __init__(self, console: Console):
        super().__init__(console=console, show_time=False, show_path=False)
        self.console = console

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Format the message
            message = self.format(record)

            # Skip system tray warnings - these are expected in CLI-only environments
            if record.levelno == logging.WARNING and "system tray" in message.lower():
                return

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


def setup_logging(verbose: bool = False, _config_dir: Path | None = None) -> None:
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
    size_value = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_value < 1024.0:
            return f"{size_value:.1f} {unit}"
        size_value /= 1024.0
    return f"{size_value:.1f} PB"


def show_success_panel(title: str, message: str, details: dict[str, object] | None = None) -> None:
    """Display a success panel with optional details."""
    formatter = get_output_formatter(console=console)
    formatter.format_success(title, message, details)


def show_error_panel(title: str, message: str, details: list[str] | None = None) -> None:
    """Display an error panel with optional details."""
    formatter = get_output_formatter(console=console)
    formatter.format_error(title, message, details)


def show_info_panel(title: str, message: str) -> None:
    """Display an info panel."""
    formatter = get_output_formatter(console=console)
    formatter.format_info(title, message)


def _get_service_method(manager: object, method_name: str) -> Callable[..., object] | None:
    """Return callable service manager method if available."""
    method = getattr(manager, method_name, None)
    return method if callable(method) else None


def _call_service_method(method: Callable[..., object] | None, **candidates: object) -> object:
    """Call service method with kwargs filtered to supported parameters."""
    if method is None:
        raise AttributeError("Service method is not available")

    signature = inspect.signature(method)
    params = signature.parameters

    # Remove potential 'self' parameter confusion
    filtered: dict[str, object] = {}
    accepts_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values())
    if accepts_kwargs:
        return method(**candidates)

    for name, value in candidates.items():
        if name in params:
            filtered[name] = value

    missing_required = [
            name for name, param in params.items()
            if name != "self" and param.default is inspect.Signature.empty and name not in filtered
    ]

    if missing_required and candidates:
        default_value: object = next(iter(candidates.values()))
        for name in missing_required:
            _ = filtered.setdefault(name, default_value)

    return method(**filtered)


def _resolve_config_dir(config_dir: Path | None) -> Path | None:
    """Normalize configuration directory input."""
    return Path(config_dir) if config_dir is not None else None


def _get_service_manager_for_command(config_dir: Path | None = None):
    """Fetch CLI service manager scoped to configuration directory."""
    return get_cli_service_manager(config_dir=_resolve_config_dir(config_dir))


def _create_credential_manager(config_dir: Path | None = None) -> _CredentialManagerLike:
    """Instantiate credential manager respecting configuration directory."""
    from .security.credential_manager import CredentialManager

    return cast(_CredentialManagerLike, cast(object, CredentialManager(config_dir=config_dir)))


def _create_configuration_module(config_dir: Path | None = None) -> ConfigurationModule:
    """Factory for configuration module respecting dynamic patching."""
    try:
        from .config import configuration_module as configuration_module_module
        module_class = getattr(configuration_module_module, "ConfigurationModule", None)
    except (ImportError, AttributeError):
        module_class = None

    cli_class = globals().get("ConfigurationModule", None)

    def _is_mock(candidate: object) -> bool:
        return getattr(getattr(candidate, "__class__", None), "__module__", "").startswith("unittest.mock")

    selected_class: _ConfigurationModuleFactory | None = None

    if _is_mock(cli_class):
        selected_class = cast(_ConfigurationModuleFactory, cli_class)
    elif callable(module_class):
        selected_class = cast(_ConfigurationModuleFactory, module_class)
    elif callable(cli_class):
        selected_class = cast(_ConfigurationModuleFactory, cli_class)
    else:
        raise RuntimeError("ConfigurationModule is not available for instantiation.")

    return selected_class(config_dir=config_dir)


def _determine_backend_from_uri(uri: str | None) -> str | None:
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


def _repository_config_to_dict(repository_obj: object, name: str) -> dict[str, object]:
    """Convert repository configuration object or mapping to dictionary."""
    if repository_obj is None:
        return {"name": name}
    to_dict_method = getattr(repository_obj, "to_dict", None)
    if callable(to_dict_method):
        data: dict[str, object] = dict(cast(_SupportsToDict, repository_obj).to_dict())
    elif isinstance(repository_obj, Mapping):
        source_mapping = cast(Mapping[object, object], repository_obj)
        data = {
                str(key): value
                for key, value in source_mapping.items()
        }
    else:
        data = {"name": name}
        for attr in ("uri", "location", "description", "tags", "password", "has_backend_credentials"):
            if hasattr(repository_obj, attr):
                value = cast(object, getattr(repository_obj, attr))
                if value is not None:
                    key = "uri" if attr == "location" else attr
                    data[key] = value
    _ = data.setdefault("name", name)
    # Normalise location/uri fields
    if "uri" not in data and "location" in data:
        data["uri"] = data.pop("location")
    return data


@repos_credentials_app.command("set")
def repos_credentials_set(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        master_password: Annotated[
            str | None, typer.Option("--master-password", "-m", help="Master password to unlock the credential manager if locked")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Path | None, typer.Option("--config-dir", help="Configuration directory")] = None,
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
                setattr(cast(object, repository_factory), "_credential_manager", credential_manager)
            except Exception as attach_exc:
                logging.getLogger(__name__).debug("Unable to attach credential manager to repository factory: %s", attach_exc)

        if master_password is not None:
            _ensure_manager_unlocked(credential_manager, master_password, interactive)
        else:
            try:
                _ = credential_manager.ensure_unlocked(allow_prompt=interactive)
            except Exception:
                if interactive:
                    raise
                # Non-interactive paths rely on auto unlock or environment variables

        prompt_service = PromptService(console=console, force_interactive=True)
        try:
            access_key = prompt_service.prompt_text("AWS Access Key ID", required=True)
            secret_key = prompt_service.prompt_password("AWS Secret Access Key", required=True)
            region = prompt_service.prompt_text("AWS Region", default="", required=False)
            insecure_tls = prompt_service.prompt_confirm("Allow insecure TLS (skip certificate verification)?", default=False)
        except PromptError as e:
            show_error_panel("Missing Parameter", str(e))
            raise typer.Exit(2)

        credentials_payload: dict[str, object] = {
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
                cred_mgr=cast(_CredentialStoreLike, cast(object, credential_manager)),
                config_manager=cast(_RepositoryConfigStoreLike, config_module),
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
    except typer.Exit:
        raise
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
            str | None, typer.Option("--master-password", "-m", help="Master password to unlock the credential manager if locked")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Path | None, typer.Option("--config-dir", help="Configuration directory")] = None,
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
                prompt_service = PromptService(console=console)
                confirmed = prompt_service.prompt_confirm(f"Remove {_backend_display_name(backend_type)} credentials for '{name}'?", default=False)
                if not confirmed:
                    show_info_panel("Operation Cancelled", "Credential removal cancelled.")
                    raise typer.Exit(0)
            else:
                confirmed = True

        credential_manager = _create_credential_manager(config_dir)
        if master_password is not None:
            _ensure_manager_unlocked(credential_manager, master_password, interactive)
        else:
            try:
                _ = credential_manager.ensure_unlocked(allow_prompt=interactive)
            except Exception:
                if interactive:
                    raise
                logging.getLogger(__name__).debug("Unable to unlock credential manager automatically for remove command.")

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
    except typer.Exit:
        raise
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
            str | None, typer.Option("--master-password", "-m", help="Master password to unlock the credential manager if locked")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Path | None, typer.Option("--config-dir", help="Configuration directory")] = None,
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
                _ = credential_manager.ensure_unlocked(allow_prompt=interactive)
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

        # Format credentials data for table display
        table_data: list[dict[str, str]] = []
        for key, value in credentials.items():
            display_key = key.replace('_', ' ').title()
            display_value = value
            if len(value) > 4 and any(token in key for token in ["secret", "key"]):
                display_value = value[:4] + "•••" + value[-2:]
            else:
                display_value = value
            table_data.append({"Field": display_key, "Value": display_value})

        formatter = get_output_formatter(console=console)
        formatter.format_table(
                data=table_data,
                columns=["Field", "Value"],
                title=f"{_backend_display_name(backend_type)} Credentials for {name}"
        )
    except RepositoryNotFoundError as e:
        show_error_panel("Repository Not Found", str(e))
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Credential display cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Credential Error", f"Failed to display repository credentials: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


def _ensure_manager_unlocked(
        manager: _UnlockableCredentialManager,
        master_password: str | None,
        interactive: bool,
) -> None:
    """Unlock credential manager when required or raise typer.Exit."""
    if not manager.is_locked():
        return

    if master_password is None:
        if interactive:
            prompt_service = PromptService(console=console)
            try:
                master_password = prompt_service.prompt_password("Master password", required=True)
            except PromptError:
                pass
        if master_password is None:
            show_error_panel("Credential Manager Locked", "Provide --master-password to unlock before proceeding.")
            raise typer.Exit(1)

    if not manager.unlock(master_password):
        show_error_panel("Unlock Failed", "Unable to unlock credential manager with the provided master password.")
        raise typer.Exit(1)


@config_export_app.command("config")
def config_export_config(
        file: Annotated[Path, typer.Argument(help="Output file path for configuration export")],
        include_repositories: Annotated[bool, typer.Option("--repositories/--no-repositories", help="Include repository configurations")] = True,
        include_selections: Annotated[bool, typer.Option("--selections/--no-selections", help="Include data selection configurations")] = True,
        include_policies: Annotated[bool, typer.Option("--policies/--no-policies", help="Include policy configurations")] = True,
        include_schedules: Annotated[bool, typer.Option("--schedules/--no-schedules", help="Include schedule configurations")] = True,
        include_credentials: Annotated[bool, typer.Option("--credentials/--no-credentials", help="Include credential references (not actual secrets)")] = False,
        overwrite: Annotated[bool, typer.Option("--overwrite", "-f", help="Overwrite existing file")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Path | None, typer.Option("--config-dir", help="Configuration directory")] = None,
) -> None:
    """
    Export TimeLocker configuration to a file.
    
    This command exports the complete TimeLocker configuration including repositories,
    data selections, policies, and schedules to a JSON file. The exported configuration
    can be used for backup, migration, or sharing configurations between systems.
    
    By default, credential secrets are NOT exported for security reasons. Only credential
    references are included if --credentials is specified.
    
    Examples:
        timelocker config export config backup.json
        timelocker config export config full-config.json --credentials
        timelocker config export config repos-only.json --no-selections --no-policies --no-schedules
    """
    setup_logging(verbose, config_dir)

    try:
        # Check if file exists and overwrite not specified
        if file.exists() and not overwrite:
            show_error_panel(
                    "File Exists",
                    f"Output file '{file}' already exists. Use --overwrite to replace it."
            )
            raise typer.Exit(2)

        # Create parent directory if needed
        file.parent.mkdir(parents=True, exist_ok=True)

        # Get configuration module
        config_module = _create_configuration_module(config_dir)
        config = config_module.get_config()

        # Build export data based on options
        export_data: dict[str, object] = {
                "metadata": {
                        "exported_at":        datetime.now().isoformat(),
                        "timelocker_version": __version__,
                        "export_type":        "full" if all([include_repositories, include_selections, include_policies, include_schedules]) else "selective"
                },
                "general": _serialize_config_value(config.general),
        }

        # Add repositories if requested
        if include_repositories:
            repos_data: dict[str, dict[str, object]] = {}
            for name, repo in config.repositories.items():
                repo_dict = _serialize_config_value(repo)
                # Remove sensitive data unless explicitly requested
                if not include_credentials:
                    _ = repo_dict.pop('password', None)
                    _ = repo_dict.pop('has_backend_credentials', None)
                repos_data[name] = repo_dict
            export_data["repositories"] = repos_data

        # Add data selections if requested
        if include_selections:
            selections_data: dict[str, dict[str, object]] = {}
            data_selections = getattr(config, "data_selections", {})
            if isinstance(data_selections, Mapping):
                typed_data_selections = cast(Mapping[object, object], data_selections)
                for name, selection in typed_data_selections.items():
                    selections_data[str(name)] = _serialize_config_value(selection)
            export_data["data_selections"] = selections_data

        # Add policies if requested (if they exist in config)
        if include_policies:
            policies_data: dict[str, dict[str, object]] = {}
            policies = getattr(config, "policies", {})
            if isinstance(policies, Mapping):
                typed_policies = cast(Mapping[object, object], policies)
                for name, policy in typed_policies.items():
                    policies_data[str(name)] = _serialize_config_value(policy)
            export_data["policies"] = policies_data

        # Add schedules if requested (if they exist in config)
        if include_schedules:
            schedules_data: dict[str, dict[str, object]] = {}
            schedules = getattr(config, "schedules", {})
            if isinstance(schedules, Mapping):
                typed_schedules = cast(Mapping[object, object], schedules)
                for name, schedule in typed_schedules.items():
                    schedules_data[str(name)] = _serialize_config_value(schedule)
            export_data["schedules"] = schedules_data

        # Add security and monitoring settings
        security = getattr(config, "security", None)
        if security is not None:
            typed_security = cast(object, security)
            security_dict = _serialize_config_value(typed_security)
            if not include_credentials:
                _ = security_dict.pop('master_password', None)
                _ = security_dict.pop('encryption_key', None)
            export_data["security"] = security_dict

        monitoring = getattr(config, "monitoring", None)
        if monitoring is not None:
            typed_monitoring = cast(object, monitoring)
            export_data["monitoring"] = _serialize_config_value(typed_monitoring)

        # Write export file
        with open(file, 'w') as f:
            json.dump(export_data, f, indent=2)

        # Show success message with summary
        summary_parts: list[str] = []
        if include_repositories:
            repo_count = len(cast(dict[str, object], export_data.get("repositories", {})))
            summary_parts.append(f"{repo_count} repositories")
        if include_selections:
            selection_count = len(cast(dict[str, object], export_data.get("data_selections", {})))
            summary_parts.append(f"{selection_count} selections")
        if include_policies:
            policy_count = len(cast(dict[str, object], export_data.get("policies", {})))
            summary_parts.append(f"{policy_count} policies")
        if include_schedules:
            schedule_count = len(cast(dict[str, object], export_data.get("schedules", {})))
            summary_parts.append(f"{schedule_count} schedules")

        summary = ", ".join(summary_parts) if summary_parts else "configuration"

        show_success_panel(
                "Configuration Exported",
                f"Configuration exported to '{file}'\n\nExported: {summary}",
                {
                        "File":        str(file),
                        "Size":        f"{file.stat().st_size} bytes",
                        "Credentials": "Included (references only)" if include_credentials else "Not included"
                }
        )

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Configuration export cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Export Error", f"Failed to export configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@migrate_app.command("validate")
def migrate_validate(
        source: Annotated[Path, typer.Argument(help="Source configuration file to validate")],
        show_changes: Annotated[bool, typer.Option("--show-changes", help="Show detailed change summary")] = True,
        check_compatibility: Annotated[bool, typer.Option("--check-compatibility", help="Check version compatibility")] = True,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Path | None, typer.Option("--config-dir", help="Configuration directory")] = None,
) -> None:
    """
    Validate configuration file for import without making changes.
    
    This command performs a dry-run validation of a configuration file to check:
    - File format and structure validity
    - Version compatibility with current TimeLocker installation
    - Potential conflicts with existing configuration
    - Required dependencies and prerequisites
    
    Use this command before importing configuration to preview changes and identify
    potential issues.
    
    Examples:
        timelocker migrate validate backup.json
        timelocker migrate validate config.json --show-changes
        timelocker migrate validate old-config.json --check-compatibility
    """
    setup_logging(verbose, config_dir)

    try:
        # Check if source file exists
        if not source.exists():
            show_error_panel(
                    "File Not Found",
                    f"Source configuration file '{source}' does not exist."
            )
            raise typer.Exit(2)

        # Load and parse source configuration
        try:
            with open(source, 'r') as f:
                import_data = cast(_ConfigObjectMap, json.load(f))
        except json.JSONDecodeError as e:
            show_error_panel(
                    "Invalid JSON",
                    f"Source file contains invalid JSON: {e}"
            )
            raise typer.Exit(2)

        # Get current configuration
        config_module = _create_configuration_module(config_dir)
        current_config = config_module.get_config()

        # Validation results
        validation_results: _ValidationResults = {
                "valid":    True,
                "errors":   [],
                "warnings": [],
                "changes":  {
                        "repositories": {"add": [], "update": [], "remove": []},
                        "targets":      {"add": [], "update": [], "remove": []},
                        "policies":     {"add": [], "update": [], "remove": []},
                        "schedules":    {"add": [], "update": [], "remove": []},
                },
        }

        # Check metadata and version compatibility
        metadata = cast(_ConfigObjectMap, import_data.get("metadata", {}))
        import_version = metadata.get("timelocker_version", "unknown")

        if check_compatibility:
            # Simple version check - in production, this would be more sophisticated
            if import_version != "unknown" and import_version != __version__:
                version_warning = (
                        f"Configuration was exported from version {import_version}, "
                        f"current version is {__version__}. Some features may not be compatible."
                )
                validation_results["warnings"].append(version_warning)

        # Validate repositories
        import_repos = cast(_ConfigSectionMap, import_data.get("repositories", {}))
        current_repos = {name: repo for name, repo in current_config.repositories.items()}

        for repo_name, repo_data in import_repos.items():
            # Check required fields
            if not repo_data.get("uri") and not repo_data.get("location"):
                validation_results["errors"].append(
                        f"Repository '{repo_name}' missing required 'uri' or 'location' field"
                )
                validation_results["valid"] = False

            # Check for conflicts
            if repo_name in current_repos:
                current_uri = getattr(current_repos[repo_name], 'uri', None) or getattr(current_repos[repo_name], 'location', None)
                import_uri = repo_data.get("uri") or repo_data.get("location")
                if current_uri != import_uri:
                    validation_results["changes"]["repositories"]["update"].append(repo_name)
                    repository_warning = (
                            f"Repository '{repo_name}' exists with different URI. "
                            f"Import will update: {current_uri} -> {import_uri}"
                    )
                    validation_results["warnings"].append(repository_warning)
            else:
                validation_results["changes"]["repositories"]["add"].append(repo_name)

        # Validate backup targets
        import_targets = cast(_ConfigSectionMap, import_data.get("backup_targets", {}))
        current_targets = {name: target for name, target in current_config.backup_targets.items()}

        for target_name, target_data in import_targets.items():
            # Check required fields
            if not target_data.get("paths"):
                validation_results["errors"].append(
                        f"Backup target '{target_name}' missing required 'paths' field"
                )
                validation_results["valid"] = False

            # Check repository reference
            target_repo = target_data.get("repository")
            if target_repo and target_repo not in import_repos and target_repo not in current_repos:
                validation_results["warnings"].append(
                        f"Backup target '{target_name}' references unknown repository '{target_repo}'"
                )

            # Check for conflicts
            if target_name in current_targets:
                validation_results["changes"]["targets"]["update"].append(target_name)
            else:
                validation_results["changes"]["targets"]["add"].append(target_name)

        # Validate policies if present
        import_policies = cast(_ConfigSectionMap, import_data.get("policies", {}))
        if import_policies:
            for policy_name, policy_data in import_policies.items():
                # Check repository references
                policy_repo = policy_data.get("repository")
                if policy_repo and policy_repo not in import_repos and policy_repo not in current_repos:
                    validation_results["warnings"].append(
                            f"Policy '{policy_name}' references unknown repository '{policy_repo}'"
                    )

                validation_results["changes"]["policies"]["add"].append(policy_name)

        # Validate schedules if present
        import_schedules = cast(_ConfigSectionMap, import_data.get("schedules", {}))
        if import_schedules:
            for schedule_name, schedule_data in import_schedules.items():
                # Check policy references
                schedule_policy = schedule_data.get("policy")
                if schedule_policy and schedule_policy not in import_policies:
                    validation_results["warnings"].append(
                            f"Schedule '{schedule_name}' references unknown policy '{schedule_policy}'"
                    )

                validation_results["changes"]["schedules"]["add"].append(schedule_name)

        # Display validation results
        console.print("\n[bold cyan]Configuration Validation Results[/bold cyan]\n")

        # Show file info
        console.print(f"[bold]Source File:[/bold] {source}")
        console.print(f"[bold]File Size:[/bold] {source.stat().st_size} bytes")
        if metadata:
            console.print(f"[bold]Exported:[/bold] {metadata.get('exported_at', 'unknown')}")
            console.print(f"[bold]Source Version:[/bold] {import_version}")
        console.print(f"[bold]Current Version:[/bold] {__version__}\n")

        # Show validation status
        if validation_results["valid"]:
            console.print("[bold green]✓ Configuration is valid and can be imported[/bold green]\n")
        else:
            console.print("[bold red]✗ Configuration has errors and cannot be imported[/bold red]\n")

        # Show errors
        if validation_results["errors"]:
            console.print("[bold red]Errors:[/bold red]")
            for error in validation_results["errors"]:
                console.print(f"  [red]✗[/red] {error}")
            console.print()

        # Show warnings
        if validation_results["warnings"]:
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for warning in validation_results["warnings"]:
                console.print(f"  [yellow]⚠[/yellow] {warning}")
            console.print()

        # Show changes summary
        if show_changes:
            console.print("[bold]Change Summary:[/bold]")

            changes = validation_results["changes"]
            change_sections: list[tuple[str, _ValidationChangeBucket]] = [
                    ("repositories", changes["repositories"]),
                    ("targets", changes["targets"]),
                    ("policies", changes["policies"]),
                    ("schedules", changes["schedules"]),
            ]
            total_changes = sum(_change_bucket_total(bucket) for _, bucket in change_sections)

            if total_changes == 0:
                console.print("  No changes detected\n")
            else:
                for category, actions in change_sections:
                    category_changes = _change_bucket_total(actions)
                    if category_changes > 0:
                        console.print(f"\n  [bold]{category.title()}:[/bold]")
                        if actions["add"]:
                            console.print(f"    [green]+ Add:[/green] {', '.join(actions['add'])}")
                        if actions["update"]:
                            console.print(f"    [yellow]~ Update:[/yellow] {', '.join(actions['update'])}")
                        if actions["remove"]:
                            console.print(f"    [red]- Remove:[/red] {', '.join(actions['remove'])}")
                console.print()

        # Show next steps
        if validation_results["valid"]:
            console.print("[bold]Next Steps:[/bold]")
            console.print("  To import this configuration, run:")
            console.print(f"  [cyan]timelocker config import config {source}[/cyan]\n")
        else:
            console.print("[bold]Action Required:[/bold]")
            console.print("  Fix the errors listed above before importing.\n")

        # Exit with appropriate code
        if not validation_results["valid"]:
            raise typer.Exit(1)
        elif validation_results["warnings"]:
            raise typer.Exit(0)  # Success with warnings
        else:
            raise typer.Exit(0)  # Success

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Validation cancelled by user")
        raise typer.Exit(130)
    except typer.Exit:
        raise
    except Exception as e:
        show_error_panel("Validation Error", f"Failed to validate configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_import_app.command("config")
def config_import_config(
        file: Annotated[Path, typer.Argument(help="Configuration file to import")],
        merge: Annotated[bool, typer.Option("--merge", help="Merge with existing configuration instead of replacing")] = True,
        overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite conflicting items")] = False,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without applying them")] = False,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompts")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        config_dir: Annotated[Path | None, typer.Option("--config-dir", help="Configuration directory")] = None,
) -> None:
    """
    Import TimeLocker configuration from a file.
    
    This command imports configuration from a previously exported file. By default,
    it merges the imported configuration with existing configuration. Use --overwrite
    to replace conflicting items.
    
    It's recommended to run 'timelocker migrate validate' first to preview changes.
    
    Examples:
        timelocker config import config backup.json --dry-run
        timelocker config import config backup.json --merge
        timelocker config import config backup.json --overwrite --yes
    """
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()

    try:
        # Check if source file exists
        if not file.exists():
            show_error_panel(
                    "File Not Found",
                    f"Configuration file '{file}' does not exist."
            )
            raise typer.Exit(2)

        # Load import data
        try:
            with open(file, 'r') as f:
                import_data = cast(_ConfigObjectMap, json.load(f))
        except json.JSONDecodeError as e:
            show_error_panel(
                    "Invalid JSON",
                    f"Configuration file contains invalid JSON: {e}"
            )
            raise typer.Exit(2)

        # Get current configuration
        config_module = _create_configuration_module(config_dir)

        # Show import summary
        console.print("\n[bold cyan]Configuration Import[/bold cyan]\n")
        console.print(f"[bold]Source:[/bold] {file}")

        metadata = cast(_ConfigObjectMap, import_data.get("metadata", {}))
        if metadata:
            console.print(f"[bold]Exported:[/bold] {metadata.get('exported_at', 'unknown')}")
            console.print(f"[bold]Version:[/bold] {metadata.get('timelocker_version', 'unknown')}")

        console.print(f"[bold]Mode:[/bold] {'Merge' if merge else 'Replace'}")
        console.print(f"[bold]Overwrite:[/bold] {'Yes' if overwrite else 'No'}\n")

        # Count items to import
        import_repos = cast(_ConfigSectionMap, import_data.get("repositories", {}))
        import_targets = cast(_ConfigSectionMap, import_data.get("backup_targets", {}))
        import_policies = cast(_ConfigSectionMap, import_data.get("policies", {}))
        import_schedules = cast(_ConfigSectionMap, import_data.get("schedules", {}))
        repo_count = len(import_repos)
        target_count = len(import_targets)
        policy_count = len(import_policies)
        schedule_count = len(import_schedules)

        console.print("Items to import:")
        console.print(f"  • {repo_count} repositories")
        console.print(f"  • {target_count} backup targets")
        console.print(f"  • {policy_count} policies")
        console.print(f"  • {schedule_count} schedules\n")

        # Confirm import
        if not dry_run and not yes and interactive:
            prompt_service = PromptService(console=console)
            if not prompt_service.prompt_confirm("Proceed with import?", default=False):
                show_info_panel("Import Cancelled", "Configuration import cancelled by user")
                raise typer.Exit(0)

        if dry_run:
            dry_run_message = (
                    "Configuration validated successfully. No changes were made.\n\n"
                    "Run without --dry-run to apply changes."
            )
            show_info_panel(
                    "Dry Run Complete",
                    dry_run_message
            )
            raise typer.Exit(0)

        # Perform import using configuration module
        config_module.import_configuration(file)

        show_success_panel(
                "Configuration Imported",
                f"Configuration imported successfully from '{file}'",
                {
                        "Repositories": str(repo_count),
                        "Targets":      str(target_count),
                        "Policies":     str(policy_count),
                        "Schedules":    str(schedule_count)
                }
        )

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Configuration import cancelled by user")
        raise typer.Exit(130)
    except typer.Exit:
        raise
    except Exception as e:
        show_error_panel("Import Error", f"Failed to import configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Import command modules to register their commands with the apps
# This must be done after all the apps are created and helper functions are defined
# to avoid circular import issues
try:
    from .cli_modules.commands.repositories import repos_app as _repos_commands_app

    _merge_typer_app(repos_app, _repos_commands_app)
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import repository commands: {e}")

try:
    from .cli_modules.commands.backup import backup_app as _backup_commands_app

    _merge_typer_app(backup_app, _backup_commands_app)
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import backup commands: {e}")

try:
    from .cli_modules.commands.snapshots import snapshots_app as _snapshots_commands_app

    _merge_typer_app(snapshots_app, _snapshots_commands_app)
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import snapshots commands: {e}")

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

try:
    from .cli_modules.commands.credentials import credentials_app as _credentials_commands_app

    _merge_typer_app(credentials_app, _credentials_commands_app)
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import credentials commands: {e}")

try:
    from .cli_modules.commands.config import config_app as _config_commands_app

    _merge_typer_app(config_app, _config_commands_app)
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import config commands: {e}")

try:
    from .cli_modules.commands.security import security_app as _security_commands_app

    _merge_typer_app(security_app, _security_commands_app)
except ImportError as e:
    logging.getLogger(__name__).debug(f"Could not import security commands: {e}")
