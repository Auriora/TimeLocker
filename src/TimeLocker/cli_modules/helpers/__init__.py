"""CLI helper utilities."""

from .display import show_success_panel, show_error_panel, show_info_panel, format_file_size
from .logging_setup import setup_logging, UserFacingLogFilter, CLILogHandler
from .service_helpers import (
    _get_service_method,
    _call_service_method,
    _resolve_config_dir,
    _get_service_manager_for_command,
    _create_credential_manager,
    _create_security_manager,
    _create_configuration_module,
)
from .auth_helpers import (
    _authenticate_user_session,
    _validate_session_for_operation,
    _ensure_manager_unlocked,
)
from .repository_helpers import (
    _determine_backend_from_uri,
    _backend_display_name,
    _repository_config_to_dict,
)
from .interactive import (
    is_interactive,
    prompt_for_value,
    prompt_for_int,
    prompt_for_bool,
    prompt_for_path,
    prompt_for_list,
    display_current_config,
    prompt_to_keep_or_change,
    validate_repository_name,
    validate_uri,
    show_help_text,
    ValidationError,
)
from .wizards import (
    repository_creation_wizard,
    policy_creation_wizard,
    schedule_creation_wizard,
    WizardCancelled,
)
from .command_integration import (
    with_interactive_fallback,
    ensure_repository_exists,
    ensure_policy_exists,
    validate_configuration_dependencies,
    prompt_for_missing_parameters,
)

__all__ = [
    # Display
    "show_success_panel",
    "show_error_panel",
    "show_info_panel",
    "format_file_size",
    # Logging
    "setup_logging",
    "UserFacingLogFilter",
    "CLILogHandler",
    # Service helpers
    "_get_service_method",
    "_call_service_method",
    "_resolve_config_dir",
    "_get_service_manager_for_command",
    "_create_credential_manager",
    "_create_security_manager",
    "_create_configuration_module",
    # Auth helpers
    "_authenticate_user_session",
    "_validate_session_for_operation",
    "_ensure_manager_unlocked",
    # Repository helpers
    "_determine_backend_from_uri",
    "_backend_display_name",
    "_repository_config_to_dict",
    # Interactive prompts
    "is_interactive",
    "prompt_for_value",
    "prompt_for_int",
    "prompt_for_bool",
    "prompt_for_path",
    "prompt_for_list",
    "display_current_config",
    "prompt_to_keep_or_change",
    "validate_repository_name",
    "validate_uri",
    "show_help_text",
    "ValidationError",
    # Wizards
    "repository_creation_wizard",
    "policy_creation_wizard",
    "schedule_creation_wizard",
    "WizardCancelled",
    # Command integration
    "with_interactive_fallback",
    "ensure_repository_exists",
    "ensure_policy_exists",
    "validate_configuration_dependencies",
    "prompt_for_missing_parameters",
]
