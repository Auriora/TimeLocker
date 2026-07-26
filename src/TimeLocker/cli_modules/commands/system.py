"""Authorized machine-level backup and retention commands."""

from typing import Annotated

import typer

from TimeLocker.system_control.action_policy import classify_public_action
from TimeLocker.system_control.client import UnixSocketSystemControlClient
from TimeLocker.system_control.models import BackupActionRequest, RetentionActionRequest

from .base import CommandBase, VerboseOption, create_typer_app, show_success_panel


system_app = create_typer_app(
    name="system",
    help_text="Authorized machine-level backup and retention actions",
)


def _create_system_control_client() -> UnixSocketSystemControlClient:
    return UnixSocketSystemControlClient()


def _require_backend_route(action: str) -> None:
    route = classify_public_action(("system", action))
    if not route.uses_system_backend:
        raise RuntimeError("system action routing policy is invalid")


@system_app.command("backup")
def system_backup(
    target_id: Annotated[
        str,
        typer.Option(
            "--target",
            help="Configured system backup target identifier",
        ),
    ] = "production",
    verbose: VerboseOption = False,
) -> None:
    """Request an allowlisted system backup through the protected backend."""
    try:
        _require_backend_route("backup")
        receipt = _create_system_control_client().request_backup(
            BackupActionRequest(target_id=target_id)
        )
        show_success_panel(
            "System Backup Requested",
            "The protected backend accepted the backup request.",
            {
                "Status": receipt.status,
                "Run ID": str(receipt.run_id) if receipt.run_id else "pending",
            },
        )
    except Exception as error:
        CommandBase.handle_error(error, verbose, "System Backup Error")


@system_app.command("retention")
def system_retention(
    policy_fingerprint: Annotated[
        str,
        typer.Option(
            "--policy-fingerprint",
            help="Exact approved retention policy fingerprint",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Evaluate without removing snapshots"),
    ] = False,
    verbose: VerboseOption = False,
) -> None:
    """Request approved retention through the protected backend."""
    try:
        _require_backend_route("retention")
        receipt = _create_system_control_client().request_retention(
            RetentionActionRequest(
                policy_fingerprint=policy_fingerprint,
                dry_run=dry_run,
            )
        )
        show_success_panel(
            "System Retention Requested",
            "The protected backend accepted the retention request.",
            {
                "Status": receipt.status,
                "Run ID": str(receipt.run_id) if receipt.run_id else "pending",
                "Mode": "dry run" if dry_run else "apply",
            },
        )
    except Exception as error:
        CommandBase.handle_error(error, verbose, "System Retention Error")


__all__ = ["system_app"]
