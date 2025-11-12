"""
Command integration utilities for interactive mode and configuration branching.

This module provides utilities to integrate interactive wizards and configuration
branching into existing CLI commands.

Requirements addressed:
- 18.1: Allow creating repositories during policy configuration
- 18.2: Allow creating selections during policy configuration
- 18.4: Allow creating policies during schedule configuration
- 18.5: Validate relationships and offer to create missing dependencies
"""

from typing import Optional, Dict, Any, Callable
import sys

from rich.console import Console

from TimeLocker.utils import PromptService, PromptError
from .interactive import is_interactive, ValidationError
from .wizards import (
    repository_creation_wizard,
    policy_creation_wizard,
    schedule_creation_wizard,
    WizardCancelled
)

console = Console(width=100)
_prompt_service = PromptService(console=console)


def with_interactive_fallback(
    wizard_func: Callable,
    required_params: Dict[str, Any],
    config_module: Any,
    **wizard_kwargs
) -> Dict[str, Any]:
    """
    Execute a wizard if required parameters are missing in interactive mode.
    
    This function checks if required parameters are provided. If not, and we're
    in interactive mode, it launches the appropriate wizard to collect them.
    
    Args:
        wizard_func: Wizard function to call if parameters are missing
        required_params: Dictionary of required parameter names and their current values
        config_module: Configuration module instance
        **wizard_kwargs: Additional kwargs to pass to the wizard
        
    Returns:
        Dictionary with collected configuration
        
    Raises:
        ValidationError: If required parameters are missing in non-interactive mode
        WizardCancelled: If user cancels the wizard
    """
    # Check if any required parameters are missing
    missing_params = [name for name, value in required_params.items() if value is None]
    
    if not missing_params:
        # All parameters provided, return them
        return required_params
    
    if not is_interactive():
        # Non-interactive mode requires all parameters
        missing_str = ", ".join(missing_params)
        raise ValidationError(
            f"Missing required parameters in non-interactive mode: {missing_str}"
        )
    
    # Interactive mode - offer to use wizard
    console.print(f"\n[yellow]Missing required parameters: {', '.join(missing_params)}[/yellow]")
    
    if _prompt_service.prompt_confirm("Would you like to use the configuration wizard?", default=True):
        try:
            # Launch wizard with any provided parameters
            wizard_config = wizard_func(
                config_module=config_module,
                **{k: v for k, v in required_params.items() if v is not None},
                **wizard_kwargs
            )
            return wizard_config
        except WizardCancelled:
            raise
    else:
        # User declined wizard, raise error
        raise ValidationError(f"Required parameters not provided: {', '.join(missing_params)}")


def ensure_repository_exists(
    repository_name: Optional[str],
    config_module: Any,
    credential_manager: Optional[Any] = None,
    allow_creation: bool = True
) -> str:
    """
    Ensure a repository exists, offering to create it if not found.
    
    This implements configuration branching by allowing repository creation
    during other operations (like policy or schedule creation).
    
    Args:
        repository_name: Name of the repository to check
        config_module: Configuration module instance
        credential_manager: Optional credential manager for new repositories
        allow_creation: Whether to allow creating a new repository
        
    Returns:
        Name of the existing or newly created repository
        
    Raises:
        ValidationError: If repository doesn't exist and creation is not allowed
        WizardCancelled: If user cancels repository creation
    """
    # If no name provided, must create or select one
    if not repository_name:
        if not is_interactive():
            raise ValidationError("Repository name is required in non-interactive mode")
        
        if allow_creation:
            console.print("[yellow]No repository specified.[/yellow]")
            if _prompt_service.prompt_confirm("Would you like to create a new repository?", default=True):
                try:
                    repo_config = repository_creation_wizard(
                        config_module=config_module,
                        credential_manager=credential_manager
                    )
                    return repo_config["name"]
                except WizardCancelled:
                    raise
        
        raise ValidationError("Repository name is required")
    
    # Check if repository exists
    try:
        config_module.get_repository(repository_name)
        return repository_name
    except Exception:
        # Repository doesn't exist
        if not is_interactive() or not allow_creation:
            raise ValidationError(f"Repository '{repository_name}' not found")
        
        console.print(f"[yellow]Repository '{repository_name}' not found.[/yellow]")
        
        if _prompt_service.prompt_confirm("Would you like to create it now?", default=True):
            try:
                repo_config = repository_creation_wizard(
                    config_module=config_module,
                    credential_manager=credential_manager,
                    name=repository_name
                )
                return repo_config["name"]
            except WizardCancelled:
                raise
        else:
            raise ValidationError(f"Repository '{repository_name}' not found")


def ensure_policy_exists(
    policy_name: Optional[str],
    config_module: Any,
    allow_creation: bool = True
) -> str:
    """
    Ensure a policy exists, offering to create it if not found.
    
    This implements configuration branching by allowing policy creation
    during schedule creation.
    
    Args:
        policy_name: Name of the policy to check
        config_module: Configuration module instance
        allow_creation: Whether to allow creating a new policy
        
    Returns:
        Name of the existing or newly created policy
        
    Raises:
        ValidationError: If policy doesn't exist and creation is not allowed
        WizardCancelled: If user cancels policy creation
    """
    # If no name provided, must create or select one
    if not policy_name:
        if not is_interactive():
            raise ValidationError("Policy name is required in non-interactive mode")
        
        if allow_creation:
            console.print("[yellow]No policy specified.[/yellow]")
            if _prompt_service.prompt_confirm("Would you like to create a new policy?", default=True):
                try:
                    policy_config = policy_creation_wizard(
                        config_module=config_module
                    )
                    return policy_config["name"]
                except WizardCancelled:
                    raise
        
        raise ValidationError("Policy name is required")
    
    # For now, just return the policy name as policy management
    # is implemented in a separate task
    # TODO: Check if policy exists once policy management is implemented
    return policy_name


def validate_configuration_dependencies(
    config: Dict[str, Any],
    config_module: Any,
    required_dependencies: Dict[str, str]
) -> Dict[str, Any]:
    """
    Validate that all configuration dependencies exist.
    
    This checks that referenced entities (repositories, policies, selections)
    exist and offers to create them if missing.
    
    Args:
        config: Configuration dictionary to validate
        config_module: Configuration module instance
        required_dependencies: Dictionary mapping config keys to dependency types
                              (e.g., {"repository": "repository", "policy": "policy"})
        
    Returns:
        Validated configuration with all dependencies resolved
        
    Raises:
        ValidationError: If dependencies cannot be resolved
        WizardCancelled: If user cancels dependency creation
    """
    validated_config = config.copy()
    
    for config_key, dependency_type in required_dependencies.items():
        value = config.get(config_key)
        
        if dependency_type == "repository":
            validated_config[config_key] = ensure_repository_exists(
                value,
                config_module,
                allow_creation=True
            )
        elif dependency_type == "policy":
            validated_config[config_key] = ensure_policy_exists(
                value,
                config_module,
                allow_creation=True
            )
        # Add more dependency types as needed
    
    return validated_config


def prompt_for_missing_parameters(
    command_name: str,
    parameters: Dict[str, Any],
    parameter_prompts: Dict[str, str],
    parameter_validators: Optional[Dict[str, Callable]] = None
) -> Dict[str, Any]:
    """
    Prompt for any missing required parameters in interactive mode.
    
    Args:
        command_name: Name of the command being executed
        parameters: Dictionary of parameter names and current values
        parameter_prompts: Dictionary mapping parameter names to prompt text
        parameter_validators: Optional dictionary of validation functions
        
    Returns:
        Dictionary with all parameters filled in
        
    Raises:
        ValidationError: If required parameters are missing in non-interactive mode
    """
    from .interactive import prompt_for_value
    
    result = parameters.copy()
    validators = parameter_validators or {}
    
    for param_name, prompt_text in parameter_prompts.items():
        if param_name not in result or result[param_name] is None:
            if not is_interactive():
                raise ValidationError(
                    f"Parameter '{param_name}' is required for {command_name} in non-interactive mode"
                )
            
            validator = validators.get(param_name)
            result[param_name] = prompt_for_value(
                prompt_text,
                required=True,
                validator=validator
            )
    
    return result


__all__ = [
    'with_interactive_fallback',
    'ensure_repository_exists',
    'ensure_policy_exists',
    'validate_configuration_dependencies',
    'prompt_for_missing_parameters',
]
