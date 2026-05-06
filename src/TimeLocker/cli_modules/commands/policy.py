"""
Policy management operations.

This module contains CLI commands for policy management operations including
policy creation, assignment, enforcement, simulation, and audit reporting.
"""

import sys
import logging
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import json

import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

# Import from base module
from .base import (
    CommandBase,
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    _get_service_method,
    _call_service_method,
    _get_service_manager_for_command,
    _create_config_service,
    ConfigService,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Import from TimeLocker package
from TimeLocker.policy import (
    PolicyManager,
    PolicyType,
    TargetType,
    RetentionType,
    PolicyStatus,
    BackupPolicy,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
)
from TimeLocker.policy.exceptions import PolicyNotFoundError
from TimeLocker.completion import (
    repository_name_completer,
    selection_name_completer,
)

# Create Typer app
policy_app = create_typer_app(
    name="policy",
    help_text="Policy management operations"
)

# Create sub-apps for policy operations
policy_backup_app = create_typer_app(
    name="backup",
    help_text="Backup policy operations"
)

policy_retention_app = create_typer_app(
    name="retention",
    help_text="Retention policy operations"
)

policy_assignment_app = create_typer_app(
    name="assignment",
    help_text="Policy assignment operations"
)

# Add sub-apps to main policy app
policy_app.add_typer(policy_backup_app, name="backup")
policy_app.add_typer(policy_retention_app, name="retention")
policy_app.add_typer(policy_assignment_app, name="assignment")


# Helper functions

def _get_policy_manager(config_dir: Optional[Path] = None) -> PolicyManager:
    """Get or create PolicyManager instance."""
    from TimeLocker.policy.storage import FileSystemPolicyStore
    from TimeLocker.policy.validator import PolicyValidator
    from TimeLocker.policy.engine import PolicyEngine
    from TimeLocker.policy.simulator import PolicySimulator
    from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver
    
    # Get policy storage directory
    policy_dir = ConfigurationPathResolver.get_data_directory() / "policies"
    policy_dir.mkdir(parents=True, exist_ok=True)
    
    # Create components
    policy_store = FileSystemPolicyStore(policy_dir)
    validator = PolicyValidator()
    engine = PolicyEngine()
    simulator = PolicySimulator(engine)
    
    manager = PolicyManager(
        policy_store=policy_store,
        validator=validator,
        engine=engine,
    )
    setattr(manager, "simulator", simulator)
    return manager


def _format_policy_table(policies: List[Any], policy_type: str) -> Table:
    """Format policies as a Rich table."""
    table = Table(title=f"{policy_type} Policies")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="white")
    table.add_column("Created", style="yellow")
    
    for policy in policies:
        created = policy.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(policy, 'created_at') else "N/A"
        table.add_row(
            policy.id[:8],
            policy.name,
            policy.description[:50] + "..." if len(policy.description) > 50 else policy.description,
            created
        )
    
    return table


def _format_assignment_table(assignments: List[PolicyAssignment]) -> Table:
    """Format policy assignments as a Rich table."""
    table = Table(title="Policy Assignments")
    table.add_column("Policy ID", style="cyan")
    table.add_column("Target Type", style="green")
    table.add_column("Target ID", style="yellow")
    table.add_column("Priority", style="white")
    table.add_column("Active", style="magenta")
    
    for assignment in assignments:
        table.add_row(
            assignment.policy_id[:8],
            assignment.target_type.value,
            assignment.target_id,
            str(assignment.priority),
            "✓" if assignment.active else "✗"
        )
    
    return table


# Backup Policy Commands

@policy_backup_app.command("create")
@with_error_handling("Policy Creation Error")
@with_logging
def policy_backup_create(
    name: Annotated[str, typer.Argument(help="Policy name")],
    description: Annotated[str, typer.Option("--description", "-d", help="Policy description")] = "",
    repository: Annotated[Optional[List[str]], typer.Option("--repository", "-r", help="Target repository (can be specified multiple times)", autocompletion=repository_name_completer)] = None,
    backup_tool: Annotated[str, typer.Option("--tool", "-t", help="Backup tool to use")] = "restic",
    selections: Annotated[Optional[List[str]], typer.Option("--selection", "-s", help="Data selection template to include (repeat for multiple)", autocompletion=selection_name_completer)] = None,
    retention_policy: Annotated[Optional[str], typer.Option("--retention", help="Retention policy ID to link")] = None,
    tags: Annotated[Optional[List[str]], typer.Option("--tag", help="Policy tags in key=value format")] = None,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Create a new backup policy."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Parse tags
        tag_dict = {}
        if tags:
            for tag in tags:
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    tag_dict[key.strip()] = value.strip()
        
        from TimeLocker.policy.models import ScheduleConfig
        policy = policy_manager.create_backup_policy(
            name=name,
            description=description,
            data_selection_refs=selections or [],
            target_repositories=repository or [],
            backup_tool=backup_tool,
            schedule=ScheduleConfig(enabled=False),
            execution_params={},
            retention_policy_id=retention_policy,
            tags=tag_dict,
            compliance_requirements=[],
        )
        
        show_success_panel(
            "Backup Policy Created",
            f"Created backup policy '{name}' with ID: {policy.id}",
            details={
                "Policy ID": policy.id,
                "Name": policy.name,
                "Repositories": ", ".join(policy.target_repositories) if policy.target_repositories else "None",
                "Backup Tool": policy.backup_tool,
            }
        )
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Creation Error")


@policy_backup_app.command("list")
@with_error_handling("Policy List Error")
@with_logging
def policy_backup_list(
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """List all backup policies."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        policies = policy_manager.list_backup_policies()
        
        if json_output:
            import json
            policy_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "repositories": p.target_repositories,
                    "tool": p.backup_tool,
                    "created_at": p.created_at.isoformat() if hasattr(p, 'created_at') else None,
                }
                for p in policies
            ]
            console.print(json.dumps(policy_data, indent=2))
        else:
            if not policies:
                show_info_panel("No Policies", "No backup policies found.")
                return
            
            table = _format_policy_table(policies, "Backup")
            console.print(table)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy List Error")


@policy_backup_app.command("show")
@with_error_handling("Policy Show Error")
@with_logging
def policy_backup_show(
    policy_id: Annotated[str, typer.Argument(help="Policy ID")],
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Show details of a backup policy."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        policy = policy_manager.get_backup_policy(policy_id)
        
        if json_output:
            import json
            policy_data = {
                "id": policy.id,
                "name": policy.name,
                "description": policy.description,
                "data_selection_refs": policy.data_selection_refs,
                "target_repositories": policy.target_repositories,
                "backup_tool": policy.backup_tool,
                "retention_policy_id": policy.retention_policy_id,
                "tags": policy.tags,
                "created_at": policy.created_at.isoformat() if hasattr(policy, 'created_at') else None,
            }
            console.print(json.dumps(policy_data, indent=2))
        else:
            console.print(Panel(
                f"[bold]Policy ID:[/bold] {policy.id}\n"
                f"[bold]Name:[/bold] {policy.name}\n"
                f"[bold]Description:[/bold] {policy.description}\n"
                f"[bold]Repositories:[/bold] {', '.join(policy.target_repositories) if policy.target_repositories else 'None'}\n"
                f"[bold]Backup Tool:[/bold] {policy.backup_tool}\n"
                f"[bold]Retention Policy:[/bold] {policy.retention_policy_id or 'None'}\n"
                f"[bold]Tags:[/bold] {', '.join(f'{k}={v}' for k, v in policy.tags.items()) if policy.tags else 'None'}\n"
                f"[bold]Created:[/bold] {policy.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(policy, 'created_at') else 'N/A'}",
                title=f"[bold green]Backup Policy: {policy.name}[/bold green]",
                border_style="green"
            ))
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Show Error")


@policy_backup_app.command("delete")
@with_error_handling("Policy Delete Error")
@with_logging
def policy_backup_delete(
    policy_id: Annotated[str, typer.Argument(help="Policy ID")],
    yes: YesOption = False,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Delete a backup policy."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Get policy details for confirmation
        policy = policy_manager.get_backup_policy(policy_id)
        
        if not yes and CommandBase.is_interactive():
            confirmed = Confirm.ask(
                f"Delete backup policy '{policy.name}' (ID: {policy_id[:8]})?",
                default=False
            )
            if not confirmed:
                show_info_panel("Operation Cancelled", "Policy deletion cancelled.")
                return
        
        policy_manager.delete_backup_policy(policy_id)
        show_success_panel("Policy Deleted", f"Deleted backup policy '{policy.name}'")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Delete Error")


# Retention Policy Commands

@policy_retention_app.command("create")
@with_error_handling("Retention Policy Creation Error")
@with_logging
def policy_retention_create(
    name: Annotated[str, typer.Argument(help="Policy name")],
    description: Annotated[str, typer.Option("--description", "-d", help="Policy description")] = "",
    hourly: Annotated[Optional[int], typer.Option("--hourly", help="Number of hourly snapshots to keep")] = None,
    daily: Annotated[Optional[int], typer.Option("--daily", help="Number of daily snapshots to keep")] = None,
    weekly: Annotated[Optional[int], typer.Option("--weekly", help="Number of weekly snapshots to keep")] = None,
    monthly: Annotated[Optional[int], typer.Option("--monthly", help="Number of monthly snapshots to keep")] = None,
    yearly: Annotated[Optional[int], typer.Option("--yearly", help="Number of yearly snapshots to keep")] = None,
    priority: Annotated[int, typer.Option("--priority", help="Policy priority (higher = more important)")] = 100,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Create a new retention policy."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Build retention rules
        rules = []
        if hourly is not None:
            rules.append(RetentionRule(
                type=RetentionType.HOURLY,
                count=hourly,
                minimum_age=None,
                tag_filters=None
            ))
        if daily is not None:
            rules.append(RetentionRule(
                type=RetentionType.DAILY,
                count=daily,
                minimum_age=None,
                tag_filters=None
            ))
        if weekly is not None:
            rules.append(RetentionRule(
                type=RetentionType.WEEKLY,
                count=weekly,
                minimum_age=None,
                tag_filters=None
            ))
        if monthly is not None:
            rules.append(RetentionRule(
                type=RetentionType.MONTHLY,
                count=monthly,
                minimum_age=None,
                tag_filters=None
            ))
        if yearly is not None:
            rules.append(RetentionRule(
                type=RetentionType.YEARLY,
                count=yearly,
                minimum_age=None,
                tag_filters=None
            ))
        
        if not rules:
            show_error_panel(
                "Invalid Configuration",
                "At least one retention rule must be specified (--hourly, --daily, --weekly, --monthly, or --yearly)"
            )
            raise typer.Exit(1)
        
        policy = policy_manager.create_retention_policy(
            name=name,
            description=description,
            rules=rules,
            priority=priority,
        )
        
        # Format rules for display
        rule_summary = []
        for rule in policy.rules:
            rule_summary.append(f"{rule.type.value}: {rule.count}")
        
        show_success_panel(
            "Retention Policy Created",
            f"Created retention policy '{name}' with ID: {policy.id}",
            details={
                "Policy ID": policy.id,
                "Name": policy.name,
                "Rules": ", ".join(rule_summary),
                "Priority": str(policy.priority),
            }
        )
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Retention Policy Creation Error")


@policy_retention_app.command("list")
@with_error_handling("Retention Policy List Error")
@with_logging
def policy_retention_list(
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """List all retention policies."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        policies = policy_manager.list_retention_policies()
        
        if json_output:
            import json
            policy_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "rules": [{"type": r.type.value, "count": r.count} for r in p.rules],
                    "priority": p.priority,
                    "created_at": p.created_at.isoformat() if hasattr(p, 'created_at') else None,
                }
                for p in policies
            ]
            console.print(json.dumps(policy_data, indent=2))
        else:
            if not policies:
                show_info_panel("No Policies", "No retention policies found.")
                return
            
            table = _format_policy_table(policies, "Retention")
            console.print(table)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Retention Policy List Error")


@policy_retention_app.command("show")
@with_error_handling("Retention Policy Show Error")
@with_logging
def policy_retention_show(
    policy_id: Annotated[str, typer.Argument(help="Policy ID")],
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Show details of a retention policy."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        policy = policy_manager.get_retention_policy(policy_id)
        
        if json_output:
            import json
            policy_data = {
                "id": policy.id,
                "name": policy.name,
                "description": policy.description,
                "rules": [
                    {
                        "type": r.type.value,
                        "count": r.count,
                        "minimum_age": str(r.minimum_age) if r.minimum_age else None,
                    }
                    for r in policy.rules
                ],
                "priority": policy.priority,
                "created_at": policy.created_at.isoformat() if hasattr(policy, 'created_at') else None,
            }
            console.print(json.dumps(policy_data, indent=2))
        else:
            # Format rules
            rules_text = "\n".join([
                f"  • {rule.type.value}: Keep {rule.count}"
                for rule in policy.rules
            ])
            
            console.print(Panel(
                f"[bold]Policy ID:[/bold] {policy.id}\n"
                f"[bold]Name:[/bold] {policy.name}\n"
                f"[bold]Description:[/bold] {policy.description}\n"
                f"[bold]Priority:[/bold] {policy.priority}\n"
                f"[bold]Rules:[/bold]\n{rules_text}\n"
                f"[bold]Created:[/bold] {policy.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(policy, 'created_at') else 'N/A'}",
                title=f"[bold green]Retention Policy: {policy.name}[/bold green]",
                border_style="green"
            ))
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Retention Policy Show Error")


@policy_retention_app.command("delete")
@with_error_handling("Retention Policy Delete Error")
@with_logging
def policy_retention_delete(
    policy_id: Annotated[str, typer.Argument(help="Policy ID")],
    yes: YesOption = False,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Delete a retention policy."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Get policy details for confirmation
        policy = policy_manager.get_retention_policy(policy_id)
        
        if not yes and CommandBase.is_interactive():
            confirmed = Confirm.ask(
                f"Delete retention policy '{policy.name}' (ID: {policy_id[:8]})?",
                default=False
            )
            if not confirmed:
                show_info_panel("Operation Cancelled", "Policy deletion cancelled.")
                return
        
        policy_manager.delete_retention_policy(policy_id)
        show_success_panel("Policy Deleted", f"Deleted retention policy '{policy.name}'")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Retention Policy Delete Error")


# Policy Assignment Commands

@policy_assignment_app.command("create")
@with_error_handling("Policy Assignment Error")
@with_logging
def policy_assignment_create(
    policy_id: Annotated[str, typer.Argument(help="Policy ID to assign")],
    target_id: Annotated[str, typer.Argument(help="Target identifier (e.g., repository name)")],
    target_type: Annotated[str, typer.Option("--target-type", "-t", help="Target type (repository, backup_job, system)")] = "repository",
    priority: Annotated[int, typer.Option("--priority", help="Assignment priority")] = 100,
    active: Annotated[bool, typer.Option("--active/--inactive", help="Whether assignment is active")] = True,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Assign a policy to a target (repository, backup job, or system)."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Parse target type
        normalized_target = (target_type or "").strip().lower()
        try:
            target_type_enum = TargetType(normalized_target)
        except ValueError:
            show_error_panel(
                "Invalid Target Type",
                "Target type must be one of: repository, backup_job, backup_target, system"
            )
            raise typer.Exit(1)
        
        # Determine policy type
        try:
            policy_manager.get_backup_policy(policy_id)
            policy_type = PolicyType.BACKUP
        except PolicyNotFoundError:
            try:
                policy_manager.get_retention_policy(policy_id)
                policy_type = PolicyType.RETENTION
            except PolicyNotFoundError:
                show_error_panel(
                    "Policy Not Found",
                    f"Policy '{policy_id}' does not exist. Use 'tl policy backup list' or "
                    "'tl policy retention list' to view available policies."
                )
                raise typer.Exit(1)

        # Create assignment
        assignment = policy_manager.assign_policy(
            policy_id=policy_id,
            policy_type=policy_type,
            target_type=target_type_enum,
            target_id=target_id,
            priority=priority,
            active=active
        )
        
        show_success_panel(
            "Policy Assigned",
            f"Assigned policy to {target_type} '{target_id}'",
            details={
                "Assignment ID": assignment.id,
                "Policy ID": policy_id[:8],
                "Policy Type": policy_type.value,
                "Target": f"{target_type}: {target_id}",
                "Priority": str(priority),
                "Active": "Yes" if active else "No",
            }
        )
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Assignment Error")


@policy_assignment_app.command("list")
@with_error_handling("Policy Assignment List Error")
@with_logging
def policy_assignment_list(
    policy_id: Annotated[Optional[str], typer.Option("--policy-id", "-p", help="Filter by policy ID")] = None,
    target_id: Annotated[Optional[str], typer.Option("--target-id", "-t", help="Filter by target ID")] = None,
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """List policy assignments."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Get assignments with optional filters
        if policy_id:
            assignments = policy_manager.get_policy_assignments(policy_id)
        elif target_id:
            assignments = policy_manager.get_assignments_for_target(target_id)
        else:
            assignments = policy_manager.list_all_assignments()
        
        if json_output:
            import json
            assignment_data = [
                {
                    "id": a.id,
                    "policy_id": a.policy_id,
                    "policy_type": a.policy_type.value,
                    "target_type": a.target_type.value,
                    "target_id": a.target_id,
                    "priority": a.priority,
                    "active": a.active,
                    "assigned_at": a.assigned_at.isoformat() if hasattr(a, 'assigned_at') else None,
                }
                for a in assignments
            ]
            console.print(json.dumps(assignment_data, indent=2))
        else:
            if not assignments:
                show_info_panel("No Assignments", "No policy assignments found.")
                return
            
            table = _format_assignment_table(assignments)
            console.print(table)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Assignment List Error")


@policy_assignment_app.command("delete")
@with_error_handling("Policy Assignment Delete Error")
@with_logging
def policy_assignment_delete(
    assignment_id: Annotated[str, typer.Argument(help="Assignment ID")],
    yes: YesOption = False,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Delete a policy assignment."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        if not yes and CommandBase.is_interactive():
            confirmed = Confirm.ask(
                f"Delete policy assignment (ID: {assignment_id[:8]})?",
                default=False
            )
            if not confirmed:
                show_info_panel("Operation Cancelled", "Assignment deletion cancelled.")
                return
        
        policy_manager.delete_assignment(assignment_id)
        show_success_panel("Assignment Deleted", f"Deleted policy assignment")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Assignment Delete Error")


# Policy Enforcement Commands

@policy_app.command("enforce")
@with_error_handling("Policy Enforcement Error")
@with_logging
def policy_enforce(
    repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name to enforce policies on", autocompletion=repository_name_completer)],
    policy_id: Annotated[Optional[str], typer.Option("--policy-id", "-p", help="Specific policy ID to enforce (optional)")] = None,
    dry_run: DryRunOption = False,
    yes: YesOption = False,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Enforce retention policies on a repository."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        if not yes and not dry_run and CommandBase.is_interactive():
            confirmed = Confirm.ask(
                f"Enforce policies on repository '{repository}'? This may delete snapshots.",
                default=False
            )
            if not confirmed:
                show_info_panel("Operation Cancelled", "Policy enforcement cancelled.")
                return
        
        # Get repository service for enforcement
        from TimeLocker.services.repository_service import RepositoryService
        from TimeLocker.config.configuration_manager import ConfigurationManager
        
        config_manager = ConfigurationManager(config_dir=config_dir)
        repo_config = config_manager.get_repository(repository)
        repository_uri = repo_config.get('uri') or repo_config.get('location')
        if not repository_uri:
            show_error_panel("Repository Configuration Error", f"Repository '{repository}' has no configured URI or location.")
            raise typer.Exit(1)
        
        # Create enforcement context
        from TimeLocker.policy.engine import EnforcementContext
        context = EnforcementContext(
            repository_id=repository,
            repository_uri=repository_uri,
            policy_ids=[policy_id] if policy_id else None,
            dry_run=dry_run
        )
        
        # Enforce policies
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Enforcing policies on {repository}...",
                total=None
            )
            
            result = policy_manager.enforce_policies(context)
            progress.update(task, completed=True)
        
        # Display results
        if dry_run:
            show_info_panel(
                "Dry Run Complete",
                f"Policy enforcement simulation completed for '{repository}'"
            )
        else:
            show_success_panel(
                "Policy Enforcement Complete",
                f"Enforced policies on repository '{repository}'",
                details={
                    "Snapshots Affected": str(len(result.snapshots_affected)),
                    "Errors": str(len(result.errors)) if hasattr(result, 'errors') else "0",
                }
            )
        
        if hasattr(result, 'errors') and result.errors:
            console.print("\n[yellow]Errors encountered:[/yellow]")
            for error in result.errors:
                console.print(f"  • {error}")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Enforcement Error")


@policy_app.command("simulate")
@with_error_handling("Policy Simulation Error")
@with_logging
def policy_simulate(
    repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name to simulate policies on", autocompletion=repository_name_completer)],
    policy_id: Annotated[Optional[str], typer.Option("--policy-id", "-p", help="Specific policy ID to simulate (optional)")] = None,
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Simulate policy enforcement without making changes."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Get repository configuration
        from TimeLocker.config.configuration_manager import ConfigurationManager
        config_manager = ConfigurationManager(config_dir=config_dir)
        repo_config = config_manager.get_repository(repository)
        repository_uri = repo_config.get('uri') or repo_config.get('location')
        if not repository_uri:
            show_error_panel("Repository Configuration Error", f"Repository '{repository}' has no configured URI or location.")
            raise typer.Exit(1)
        
        # Create simulation target
        from TimeLocker.policy.models import PolicyTarget
        target = PolicyTarget(
            target_type=TargetType.REPOSITORY,
            target_id=repository,
            repository_uri=repository_uri
        )
        
        # Run simulation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Simulating policies on {repository}...",
                total=None
            )
            
            result = policy_manager.simulate_policy(policy_id, target) if policy_id else policy_manager.simulate_all_policies(target)
            progress.update(task, completed=True)
        
        # Display results
        storage_impact = getattr(result, 'storage_impact', None)
        if json_output:
            import json
            simulation_data = {
                "policy_id": result.policy_id if hasattr(result, 'policy_id') else None,
                "target_id": result.target_id if hasattr(result, 'target_id') else repository,
                "snapshots_to_prune": len(result.snapshots_to_prune) if hasattr(result, 'snapshots_to_prune') else 0,
                "snapshots_to_retain": len(result.snapshots_to_retain) if hasattr(result, 'snapshots_to_retain') else 0,
                "storage_impact": {
                    "bytes_freed": storage_impact.estimated_space_freed_bytes,
                } if storage_impact else {},
                "conflicts": [c.description for c in result.conflicts] if hasattr(result, 'conflicts') else [],
                "warnings": result.compliance_warnings if hasattr(result, 'compliance_warnings') else [],
            }
            console.print(json.dumps(simulation_data, indent=2))
        else:
            # Format storage impact
            storage_freed = "N/A"
            if storage_impact:
                bytes_freed = storage_impact.estimated_space_freed_bytes
                storage_freed = _format_size(bytes_freed)
            
            console.print(Panel(
                f"[bold]Repository:[/bold] {repository}\n"
                f"[bold]Snapshots to Prune:[/bold] {len(result.snapshots_to_prune) if hasattr(result, 'snapshots_to_prune') else 0}\n"
                f"[bold]Snapshots to Retain:[/bold] {len(result.snapshots_to_retain) if hasattr(result, 'snapshots_to_retain') else 0}\n"
                f"[bold]Storage to Free:[/bold] {storage_freed}",
                title="[bold blue]Policy Simulation Results[/bold blue]",
                border_style="blue"
            ))
            
            if hasattr(result, 'compliance_warnings') and result.compliance_warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in result.compliance_warnings:
                    console.print(f"  • {warning}")
            
            if hasattr(result, 'conflicts') and result.conflicts:
                console.print("\n[red]Conflicts:[/red]")
                for conflict in result.conflicts:
                    console.print(f"  • {conflict.description}")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Simulation Error")


def _format_size(size_bytes: float) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


# Policy Audit and Status Commands

@policy_app.command("status")
@with_error_handling("Policy Status Error")
@with_logging
def policy_status(
    repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Filter by repository", autocompletion=repository_name_completer)] = None,
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Show policy status and compliance information."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Get policy status
        if repository:
            # Get assignments for specific repository
            assignments = policy_manager.get_assignments_for_target(repository)
            
            if json_output:
                import json
                status_data = {
                    "repository": repository,
                    "active_policies": len([a for a in assignments if a.active]),
                    "total_assignments": len(assignments),
                    "assignments": [
                        {
                            "policy_id": a.policy_id,
                            "policy_type": a.policy_type.value,
                            "active": a.active,
                            "priority": a.priority,
                        }
                        for a in assignments
                    ]
                }
                console.print(json.dumps(status_data, indent=2))
            else:
                active_count = len([a for a in assignments if a.active])
                console.print(Panel(
                    f"[bold]Repository:[/bold] {repository}\n"
                    f"[bold]Active Policies:[/bold] {active_count}\n"
                    f"[bold]Total Assignments:[/bold] {len(assignments)}",
                    title="[bold green]Policy Status[/bold green]",
                    border_style="green"
                ))
                
                if assignments:
                    table = _format_assignment_table(assignments)
                    console.print("\n")
                    console.print(table)
        else:
            # Get overall status
            backup_policies = policy_manager.list_backup_policies()
            retention_policies = policy_manager.list_retention_policies()
            all_assignments = policy_manager.list_all_assignments()
            
            if json_output:
                import json
                status_data = {
                    "backup_policies": len(backup_policies),
                    "retention_policies": len(retention_policies),
                    "total_assignments": len(all_assignments),
                    "active_assignments": len([a for a in all_assignments if a.active]),
                }
                console.print(json.dumps(status_data, indent=2))
            else:
                console.print(Panel(
                    f"[bold]Backup Policies:[/bold] {len(backup_policies)}\n"
                    f"[bold]Retention Policies:[/bold] {len(retention_policies)}\n"
                    f"[bold]Total Assignments:[/bold] {len(all_assignments)}\n"
                    f"[bold]Active Assignments:[/bold] {len([a for a in all_assignments if a.active])}",
                    title="[bold green]Policy Management Status[/bold green]",
                    border_style="green"
                ))
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Status Error")


@policy_app.command("audit")
@with_error_handling("Policy Audit Error")
@with_logging
def policy_audit(
    policy_id: Annotated[Optional[str], typer.Option("--policy-id", "-p", help="Filter by policy ID")] = None,
    repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Filter by repository", autocompletion=repository_name_completer)] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Limit number of records")] = 50,
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Show policy enforcement audit trail."""
    try:
        policy_manager = _get_policy_manager(config_dir)
        
        # Get enforcement records
        records = policy_manager.get_enforcement_history(
            policy_id=policy_id,
            target_id=repository,
            limit=limit
        )
        
        if json_output:
            import json
            audit_data = [
                {
                    "id": r.id,
                    "policy_id": r.policy_id,
                    "target_id": r.target_id,
                    "enforcement_type": r.enforcement_type.value,
                    "execution_time": r.execution_time.isoformat() if hasattr(r, 'execution_time') else None,
                    "snapshots_affected": len(r.snapshots_affected) if hasattr(r, 'snapshots_affected') else 0,
                    "errors": r.errors if hasattr(r, 'errors') else [],
                }
                for r in records
            ]
            console.print(json.dumps(audit_data, indent=2))
        else:
            if not records:
                show_info_panel("No Records", "No enforcement records found.")
                return
            
            table = Table(title="Policy Enforcement Audit Trail")
            table.add_column("Time", style="cyan")
            table.add_column("Policy ID", style="green")
            table.add_column("Target", style="yellow")
            table.add_column("Type", style="white")
            table.add_column("Snapshots", style="magenta")
            table.add_column("Status", style="blue")
            
            for record in records:
                execution_time = record.execution_time.strftime("%Y-%m-%d %H:%M") if hasattr(record, 'execution_time') else "N/A"
                snapshots_count = len(record.snapshots_affected) if hasattr(record, 'snapshots_affected') else 0
                has_errors = len(record.errors) > 0 if hasattr(record, 'errors') else False
                status = "❌ Error" if has_errors else "✓ Success"
                
                table.add_row(
                    execution_time,
                    record.policy_id[:8],
                    record.target_id,
                    record.enforcement_type.value if hasattr(record, 'enforcement_type') else "N/A",
                    str(snapshots_count),
                    status
                )
            
            console.print(table)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Policy Audit Error")
