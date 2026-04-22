"""Logging configuration for CLI."""

import logging
import logging.handlers
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler

# Initialize Rich console for consistent output
console = Console(width=100)


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
    from ...config.configuration_path_resolver import ConfigurationPathResolver

    # Determine log level
    level = logging.DEBUG if verbose else logging.INFO

    # Get appropriate XDG directory for log files (cache directory)
    # Logs are temporary/cache data, not configuration or persistent data
    if config_dir is not None:
        log_dir = Path(config_dir) / "cache" / "logs"
    else:
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
