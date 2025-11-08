"""
Configuration wizards for CLI commands.

This module provides step-by-step wizards for complex entity creation including
repositories, policies, and schedules with guided configuration flows.

Requirements addressed:
- 3.2: Configuration wizards for complex entity creation
- 18.3: Guided configuration flows with help text and examples
"""

import sys
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from .interactive import (
    prompt_for_value,
    prompt_for_bool,
    prompt_for_path,
    prompt_for_list,
    prompt_for_int,
    display_current_config,
    validate_repository_name,
    validate_uri,
    show_help_text,
    is_interactive,
    ValidationError
)

console = Console(width=100)


class WizardCancelled(Exception):
    """Raised when user cancels a wizard."""
    pass


def show_wizard_header(title: str, description: str) -> None:
    """
    Display wizard header with title and description.
    
    Args:
        title: Wizard title
        description: Wizard description
    """
    panel = Panel(
        f"[bold]{title}[/bold]\n\n{description}",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(panel)
    console.print()


def show_wizard_step(step_number: int, total_steps: int, step_title: str) -> None:
    """
    Display wizard step header.
    
    Args:
        step_number: Current step number
        total_steps: Total number of steps
        step_title: Title for this step
    """
    console.print(f"\n[bold cyan]Step {step_number}/{total_steps}: {step_title}[/bold cyan]")
    console.print()


def repository_creation_wizard(
    config_module: Any,
    credential_manager: Optional[Any] = None,
    name: Optional[str] = None,
    uri: Optional[str] = None
) -> Dict[str, Any]:
    """
    Interactive wizard for creating a new repository.
    
    Args:
        config_module: Configuration module instance
        credential_manager: Optional credential manager for storing credentials
        name: Optional pre-filled repository name
        uri: Optional pre-filled repository URI
        
    Returns:
        Dictionary with repository configuration
        
    Raises:
        WizardCancelled: If user cancels the wizard
        ValidationError: If validation fails in non-interactive mode
    """
    if not is_interactive():
        if not name or not uri:
            raise ValidationError("Repository name and URI are required in non-interactive mode")
        return {"name": name, "uri": uri}
    
    show_wizard_header(
        "Repository Creation Wizard",
        "This wizard will guide you through creating a new backup repository.\n"
        "You can press Ctrl+C at any time to cancel."
    )
    
    try:
        # Step 1: Repository name
        show_wizard_step(1, 5, "Repository Name")
        show_help_text(
            "Choose a unique name for this repository. Use letters, numbers, dashes, "
            "underscores, or dots.\n\nExamples: 'local-backup', 'cloud-s3', 'offsite.backup'"
        )
        
        repo_name = name
        while not repo_name:
            repo_name = prompt_for_value(
                "Repository name",
                required=True,
                validator=validate_repository_name
            )
            
            # Check if name already exists
            try:
                existing = config_module.get_repository(repo_name)
                if existing:
                    console.print(f"[yellow]Repository '{repo_name}' already exists. Please choose a different name.[/yellow]")
                    repo_name = None
            except Exception:
                # Repository doesn't exist, which is what we want
                pass
        
        # Step 2: Repository URI
        show_wizard_step(2, 5, "Repository Location")
        show_help_text(
            "Specify where the repository will be stored.\n\n"
            "Examples:\n"
            "  Local:  file:///backup/repo\n"
            "  S3:     s3:s3.amazonaws.com/bucket-name\n"
            "  B2:     b2:bucket-name\n"
            "  Azure:  azure:container-name\n"
            "  GCS:    gs:bucket-name/"
        )
        
        repo_uri = uri or prompt_for_value(
            "Repository URI",
            required=True,
            validator=validate_uri
        )
        
        # Step 3: Description
        show_wizard_step(3, 5, "Description (Optional)")
        description = prompt_for_value(
            "Repository description",
            default="",
            required=False
        )
        
        # Step 4: Backend credentials (if cloud storage)
        backend_type = _determine_backend_from_uri(repo_uri)
        needs_credentials = backend_type in ['s3', 'b2', 'azure', 'gcs']
        
        store_credentials = False
        credentials = {}
        
        if needs_credentials and credential_manager:
            show_wizard_step(4, 5, "Backend Credentials")
            show_help_text(
                f"This repository uses {_backend_display_name(backend_type)} storage.\n"
                "You can store credentials now or add them later using:\n"
                f"  timelocker repos credentials set {repo_name}"
            )
            
            store_credentials = prompt_for_bool(
                "Store backend credentials now?",
                default=True
            )
            
            if store_credentials:
                credentials = _prompt_for_backend_credentials(backend_type)
        
        # Step 5: Initialize repository
        show_wizard_step(5, 5, "Repository Initialization")
        show_help_text(
            "The repository needs to be initialized before it can be used.\n"
            "This creates the necessary structure in the storage location."
        )
        
        initialize = prompt_for_bool(
            "Initialize repository now?",
            default=True
        )
        
        # Build configuration
        config = {
            "name": repo_name,
            "uri": repo_uri,
            "description": description or "",
            "initialize": initialize,
            "store_credentials": store_credentials,
            "credentials": credentials
        }
        
        # Show summary
        console.print("\n[bold green]Repository Configuration Summary:[/bold green]")
        display_current_config("", {
            "Name": repo_name,
            "URI": repo_uri,
            "Description": description or "(none)",
            "Backend": _backend_display_name(backend_type) if backend_type else "Local",
            "Store Credentials": "Yes" if store_credentials else "No",
            "Initialize": "Yes" if initialize else "No"
        })
        
        if not Confirm.ask("\nCreate repository with this configuration?", default=True):
            raise WizardCancelled("Repository creation cancelled by user")
        
        return config
        
    except KeyboardInterrupt:
        raise WizardCancelled("Repository creation cancelled by user")


def policy_creation_wizard(
    config_module: Any,
    name: Optional[str] = None,
    repository_name: Optional[str] = None,
    selection_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Interactive wizard for creating a new backup policy.
    
    Args:
        config_module: Configuration module instance
        name: Optional pre-filled policy name
        repository_name: Optional pre-filled repository name
        selection_name: Optional pre-filled selection name
        
    Returns:
        Dictionary with policy configuration
        
    Raises:
        WizardCancelled: If user cancels the wizard
        ValidationError: If validation fails in non-interactive mode
    """
    if not is_interactive():
        if not name or not repository_name:
            raise ValidationError("Policy name and repository are required in non-interactive mode")
        return {"name": name, "repository": repository_name, "selection": selection_name}
    
    show_wizard_header(
        "Backup Policy Creation Wizard",
        "This wizard will guide you through creating a new backup policy.\n"
        "A policy defines what to backup, where to store it, and how often."
    )
    
    try:
        # Step 1: Policy name
        show_wizard_step(1, 4, "Policy Name")
        policy_name = name or prompt_for_value(
            "Policy name",
            required=True,
            validator=validate_repository_name
        )
        
        # Step 2: Repository selection (with branching)
        show_wizard_step(2, 4, "Repository Selection")
        repository = _select_or_create_repository(config_module, repository_name)
        
        # Step 3: Data selection (with branching)
        show_wizard_step(3, 4, "Data Selection")
        selection = _select_or_create_selection(config_module, selection_name)
        
        # Step 4: Additional settings
        show_wizard_step(4, 4, "Additional Settings")
        
        tags = prompt_for_list(
            "Tags (optional)",
            required=False
        )
        
        # Build configuration
        config = {
            "name": policy_name,
            "repository": repository,
            "selection": selection,
            "tags": tags
        }
        
        # Show summary
        console.print("\n[bold green]Policy Configuration Summary:[/bold green]")
        display_current_config("", {
            "Name": policy_name,
            "Repository": repository,
            "Selection": selection or "(default)",
            "Tags": ", ".join(tags) if tags else "(none)"
        })
        
        if not Confirm.ask("\nCreate policy with this configuration?", default=True):
            raise WizardCancelled("Policy creation cancelled by user")
        
        return config
        
    except KeyboardInterrupt:
        raise WizardCancelled("Policy creation cancelled by user")


def schedule_creation_wizard(
    config_module: Any,
    name: Optional[str] = None,
    policy_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Interactive wizard for creating a new backup schedule.
    
    Args:
        config_module: Configuration module instance
        name: Optional pre-filled schedule name
        policy_name: Optional pre-filled policy name
        
    Returns:
        Dictionary with schedule configuration
        
    Raises:
        WizardCancelled: If user cancels the wizard
        ValidationError: If validation fails in non-interactive mode
    """
    if not is_interactive():
        if not name or not policy_name:
            raise ValidationError("Schedule name and policy are required in non-interactive mode")
        return {"name": name, "policy": policy_name}
    
    show_wizard_header(
        "Backup Schedule Creation Wizard",
        "This wizard will guide you through creating an automated backup schedule."
    )
    
    try:
        # Step 1: Schedule name
        show_wizard_step(1, 3, "Schedule Name")
        schedule_name = name or prompt_for_value(
            "Schedule name",
            required=True,
            validator=validate_repository_name
        )
        
        # Step 2: Policy selection (with branching)
        show_wizard_step(2, 3, "Policy Selection")
        policy = _select_or_create_policy(config_module, policy_name)
        
        # Step 3: Schedule timing
        show_wizard_step(3, 3, "Schedule Timing")
        show_help_text(
            "Choose how often the backup should run.\n\n"
            "Options:\n"
            "  hourly  - Every hour\n"
            "  daily   - Once per day\n"
            "  weekly  - Once per week\n"
            "  monthly - Once per month"
        )
        
        frequency = prompt_for_value(
            "Frequency",
            choices=["hourly", "daily", "weekly", "monthly"],
            required=True
        )
        
        # Build configuration
        config = {
            "name": schedule_name,
            "policy": policy,
            "frequency": frequency
        }
        
        # Show summary
        console.print("\n[bold green]Schedule Configuration Summary:[/bold green]")
        display_current_config("", {
            "Name": schedule_name,
            "Policy": policy,
            "Frequency": frequency
        })
        
        if not Confirm.ask("\nCreate schedule with this configuration?", default=True):
            raise WizardCancelled("Schedule creation cancelled by user")
        
        return config
        
    except KeyboardInterrupt:
        raise WizardCancelled("Schedule creation cancelled by user")


# Helper functions for configuration branching

def _select_or_create_repository(
    config_module: Any,
    default_name: Optional[str] = None
) -> str:
    """
    Allow user to select existing repository or create new one.
    
    Args:
        config_module: Configuration module instance
        default_name: Optional default repository name
        
    Returns:
        Selected or created repository name
    """
    # Get list of existing repositories
    try:
        config = config_module.get_config()
        repositories = list(config.repositories.keys()) if hasattr(config, 'repositories') else []
    except Exception:
        repositories = []
    
    if not repositories:
        console.print("[yellow]No repositories configured yet.[/yellow]")
        if Confirm.ask("Create a new repository now?", default=True):
            from .interactive import ValidationError
            try:
                repo_config = repository_creation_wizard(config_module)
                return repo_config["name"]
            except (WizardCancelled, ValidationError):
                raise
        else:
            raise WizardCancelled("Repository selection cancelled")
    
    # Show existing repositories
    console.print("\n[bold]Existing Repositories:[/bold]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Name", style="green")
    table.add_column("URI", style="blue")
    
    for idx, repo_name in enumerate(repositories, 1):
        try:
            repo = config_module.get_repository(repo_name)
            uri = getattr(repo, 'uri', None) or getattr(repo, 'location', '(unknown)')
            table.add_row(str(idx), repo_name, uri)
        except Exception:
            table.add_row(str(idx), repo_name, "(error loading)")
    
    console.print(table)
    console.print()
    
    # Prompt for selection
    choice = prompt_for_value(
        "Select repository number or 'new' to create one",
        default=default_name if default_name in repositories else None
    )
    
    if choice and choice.lower() == 'new':
        repo_config = repository_creation_wizard(config_module)
        return repo_config["name"]
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(repositories):
            return repositories[idx]
    except (ValueError, IndexError):
        pass
    
    # If choice matches a repository name, use it
    if choice in repositories:
        return choice
    
    console.print("[yellow]Invalid selection. Using first repository.[/yellow]")
    return repositories[0]


def _select_or_create_selection(
    config_module: Any,
    default_name: Optional[str] = None
) -> Optional[str]:
    """
    Allow user to select existing selection or create new one.
    
    Args:
        config_module: Configuration module instance
        default_name: Optional default selection name
        
    Returns:
        Selected or created selection name, or None for default
    """
    # For now, return None (default selection) as selection management
    # is implemented in a separate task
    console.print("[blue]Using default file selection (all files)[/blue]")
    return None


def _select_or_create_policy(
    config_module: Any,
    default_name: Optional[str] = None
) -> str:
    """
    Allow user to select existing policy or create new one.
    
    Args:
        config_module: Configuration module instance
        default_name: Optional default policy name
        
    Returns:
        Selected or created policy name
    """
    # For now, prompt for policy name as policy management
    # is implemented in a separate task
    return prompt_for_value(
        "Policy name",
        default=default_name,
        required=True
    )


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
        "s3": "AWS S3",
        "b2": "Backblaze B2",
        "azure": "Azure Blob Storage",
        "gcs": "Google Cloud Storage"
    }
    return mapping.get(backend, backend.upper())


def _prompt_for_backend_credentials(backend_type: str) -> Dict[str, Any]:
    """
    Prompt for backend-specific credentials.
    
    Args:
        backend_type: Type of backend (s3, b2, azure, gcs)
        
    Returns:
        Dictionary with credentials
    """
    credentials = {}
    
    if backend_type == "s3":
        credentials["access_key_id"] = prompt_for_value(
            "AWS Access Key ID",
            required=True
        )
        credentials["secret_access_key"] = prompt_for_value(
            "AWS Secret Access Key",
            required=True,
            password=True
        )
        region = prompt_for_value(
            "AWS Region (optional)",
            default="",
            required=False
        )
        if region:
            credentials["region"] = region
    
    elif backend_type == "b2":
        credentials["account_id"] = prompt_for_value(
            "B2 Account ID",
            required=True
        )
        credentials["application_key"] = prompt_for_value(
            "B2 Application Key",
            required=True,
            password=True
        )
    
    elif backend_type == "azure":
        credentials["account_name"] = prompt_for_value(
            "Azure Account Name",
            required=True
        )
        credentials["account_key"] = prompt_for_value(
            "Azure Account Key",
            required=True,
            password=True
        )
    
    elif backend_type == "gcs":
        credentials["project_id"] = prompt_for_value(
            "GCS Project ID",
            required=True
        )
        credentials["credentials_file"] = prompt_for_path(
            "Path to GCS credentials JSON file",
            required=True,
            must_exist=True,
            must_be_file=True
        )
    
    return credentials


__all__ = [
    'repository_creation_wizard',
    'policy_creation_wizard',
    'schedule_creation_wizard',
    'WizardCancelled',
]
