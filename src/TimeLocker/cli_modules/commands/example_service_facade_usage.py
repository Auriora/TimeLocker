"""
Example command demonstrating ServiceFacade usage.

This module shows how to use the ServiceFacade to simplify service access
in CLI commands, reducing code duplication and providing consistent error handling.
"""

from typing import Optional, Annotated
from pathlib import Path

import typer
from rich.table import Table

from .base import (
    CommandBase,
    create_typer_app,
    show_success_panel,
    show_error_panel,
    console,
    VerboseOption,
    ConfigDirOption,
)

from TimeLocker.utils.service_facade import ServiceAccessError, ServiceInitializationError

# Create Typer app
example_app = create_typer_app(
    name="example",
    help_text="Example commands using ServiceFacade"
)


@example_app.command("health")
def health_check(
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Check health status of all services using ServiceFacade.
    
    This example demonstrates:
    - Using CommandBase.setup_with_facade() for simplified setup
    - Accessing service health check through the facade
    - Consistent error handling with ServiceFacade exceptions
    """
    try:
        # Setup using ServiceFacade - single line replaces multiple service initializations
        facade = CommandBase.setup_with_facade(verbose, config_dir)
        
        # Get health status - no need to access service manager directly
        health_status = facade.health_check()
        
        # Display results
        table = Table(title="Service Health Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        
        for service_name, is_healthy in health_status.items():
            status = "✓ Healthy" if is_healthy else "✗ Unhealthy"
            style = "green" if is_healthy else "red"
            table.add_row(service_name, f"[{style}]{status}[/{style}]")
        
        console.print(table)
        
        # Check if all services are healthy
        all_healthy = all(health_status.values())
        if all_healthy:
            show_success_panel("Health Check", "All services are healthy")
        else:
            show_error_panel("Health Check", "Some services are unhealthy")
            raise typer.Exit(1)
            
    except ServiceInitializationError as e:
        show_error_panel("Initialization Error", str(e))
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Health Check Failed")


@example_app.command("repo-stats")
def repository_stats(
    repository: Annotated[str, typer.Argument(help="Repository name or URI")],
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Get repository statistics using ServiceFacade.
    
    This example demonstrates:
    - Accessing repository service through the facade
    - Using repository resolver for consistent repository handling
    - Simplified error handling
    """
    try:
        # Setup using ServiceFacade
        facade = CommandBase.setup_with_facade(verbose, config_dir)
        
        # Get repository service - no need to check if it exists or handle initialization
        repo_service = facade.get_repository_service()
        
        # Get repository factory for creating repository instance
        repo_factory = facade.get_repository_factory()
        
        # Create repository instance
        repo_instance = repo_factory.create_repository(repository)
        
        # Get statistics
        with console.status(f"[bold green]Getting statistics for {repository}..."):
            stats = repo_service.get_repository_stats(repo_instance)
        
        # Display results
        table = Table(title=f"Repository Statistics: {repository}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            if isinstance(value, int) and key.endswith('_size'):
                # Format size values
                value = _format_size(value)
            table.add_row(key.replace('_', ' ').title(), str(value))
        
        console.print(table)
        show_success_panel("Statistics", f"Retrieved statistics for {repository}")
        
    except ServiceAccessError as e:
        show_error_panel("Service Access Error", str(e))
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Repository Stats Failed")


@example_app.command("config-info")
def configuration_info(
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Display configuration information using ServiceFacade.
    
    This example demonstrates:
    - Accessing configuration service through the facade
    - Fallback to config module if service not available
    - Consistent error handling
    """
    try:
        # Setup using ServiceFacade
        facade = CommandBase.setup_with_facade(verbose, config_dir)
        
        # Get configuration service - facade handles fallback to config module
        config_service = facade.get_configuration_service()
        
        # Get repositories
        repositories = []
        if hasattr(config_service, 'get_repositories'):
            repositories = config_service.get_repositories()
        elif hasattr(config_service, 'list_repositories'):
            repositories = config_service.list_repositories()
        
        # Display results
        table = Table(title="Configuration Information")
        table.add_column("Repository", style="cyan")
        table.add_column("URI", style="green")
        
        for repo in repositories:
            name = repo.get('name', 'Unknown') if isinstance(repo, dict) else getattr(repo, 'name', 'Unknown')
            uri = repo.get('uri', 'Unknown') if isinstance(repo, dict) else getattr(repo, 'uri', 'Unknown')
            table.add_row(name, uri)
        
        console.print(table)
        show_success_panel("Configuration", f"Found {len(repositories)} repositories")
        
    except ServiceAccessError as e:
        show_error_panel("Service Access Error", str(e))
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Configuration Info Failed")


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes is None:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


# Comparison: Old way vs New way with ServiceFacade
"""
OLD WAY (without ServiceFacade):
================================

@example_app.command("health")
def health_check_old(verbose: bool = False, config_dir: Optional[Path] = None):
    try:
        # Multiple initialization steps
        setup_logging(verbose, config_dir)
        service_manager = _get_service_manager_for_command(config_dir)
        
        # Check if service manager exists
        if not service_manager:
            show_error_panel("Error", "Service manager not available")
            raise typer.Exit(1)
        
        # Initialize services
        if hasattr(service_manager, 'initialize_services'):
            service_manager.initialize_services()
        
        # Get health status with error checking
        health_status = {}
        if hasattr(service_manager, 'get_service_health'):
            health_status = service_manager.get_service_health()
        else:
            # Fallback: check individual services
            if hasattr(service_manager, 'repository_service'):
                repo_service = service_manager.repository_service
                if repo_service and hasattr(repo_service, 'health_check'):
                    health_status['repository'] = repo_service.health_check()
            # ... repeat for each service
        
        # Display results (same as new way)
        ...
        
    except Exception as e:
        show_error_panel("Error", str(e))
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


NEW WAY (with ServiceFacade):
==============================

@example_app.command("health")
def health_check(verbose: bool = False, config_dir: Optional[Path] = None):
    try:
        # Single line setup
        facade = CommandBase.setup_with_facade(verbose, config_dir)
        
        # Direct access with automatic error handling
        health_status = facade.health_check()
        
        # Display results
        ...
        
    except ServiceInitializationError as e:
        show_error_panel("Initialization Error", str(e))
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


BENEFITS:
=========
1. Reduced code: ~15 lines → ~3 lines for setup and service access
2. Consistent error handling: ServiceFacade exceptions are specific and informative
3. Automatic initialization: No need to check if services exist or are initialized
4. Fallback handling: ServiceFacade handles fallbacks (e.g., config_module vs config_service)
5. Caching: Services are cached after first access for better performance
6. Type safety: ServiceFacade provides clear method signatures
7. Maintainability: Changes to service initialization only need to be made in ServiceFacade
"""
