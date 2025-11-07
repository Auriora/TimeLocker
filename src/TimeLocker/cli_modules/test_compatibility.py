"""Test compatibility patches for CLI testing."""

import sys
import builtins
import importlib
from typing import Any, Optional, TextIO
from enum import Enum

import typer
from rich.console import Console


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


def _combined_output_for_tests(result: Any) -> str:
    """
    Combine stdout and stderr for CLI runner results.

    Provided to support legacy tests that reference `_combined_output`
    without importing it explicitly from test utilities.
    """
    stdout_text = getattr(result, "stdout", "") or ""
    stderr_text = getattr(result, "stderr", "") or ""
    return stdout_text + "\n" + stderr_text


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


def patch_typer_cli_runner():
    """Patch Typer's CliRunner to handle stderr properly in tests."""
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


def patch_rich_console_input(console: Console):
    """Patch Rich Console input to handle non-interactive streams."""
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

    Console.input = _patched_rich_console_input  # type: ignore[attr-defined]


def setup_test_compatibility():
    """Set up all test compatibility patches and fallbacks."""
    # Patch Typer CLI Runner
    patch_typer_cli_runner()
    
    # Register builtin symbols for tests
    if not hasattr(builtins, "_combined_output"):
        builtins._combined_output = _combined_output_for_tests
    
    # Register monitoring fallbacks
    try:
        from .. import monitoring as _timelocker_monitoring
        StatusReporter = getattr(_timelocker_monitoring, "StatusReporter")
        StatusLevel = getattr(_timelocker_monitoring, "StatusLevel")
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
        
        StatusReporter = StatusReporter
        StatusLevel = StatusLevel
    
    _register_builtin_symbol("StatusReporter", "TimeLocker.monitoring", StatusReporter)
    _register_builtin_symbol("StatusLevel", "TimeLocker.monitoring", StatusLevel)
    
    # Register ConfigurationManager
    from ..config.configuration_manager import ConfigurationManager
    _register_builtin_symbol("ConfigurationManager", "TimeLocker.config.configuration_manager", ConfigurationManager)
    
    # Register module aliases
    from .. import monitoring as _timelocker_monitoring
    from ..config import configuration_manager as _timelocker_config_manager_module
    
    sys.modules.setdefault("TimeLocker.monitoring", _timelocker_monitoring)
    sys.modules.setdefault("TimeLocker.config.configuration_manager", _timelocker_config_manager_module)
