"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import click
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .security_service import SecurityService
from .credential_manager import CredentialManager
from .data_privacy_manager import DataPrivacyManager
from ..file_selections import FileSelection


@click.group(name="privacy")
def privacy_cli():
    """Privacy and data protection commands"""
    pass


@privacy_cli.command()
@click.option('--format', 'output_format', default='text', 
              type=click.Choice(['text', 'json']),
              help='Output format')
def info(output_format: str):
    """Display privacy information and current settings"""
    try:
        # Initialize security service
        credential_manager = CredentialManager()
        security_service = SecurityService(credential_manager)
        
        privacy_info = security_service.get_privacy_info()
        
        if output_format == 'json':
            click.echo(json.dumps(privacy_info, indent=2, default=str))
        else:
            click.echo("=== TimeLocker Privacy Information ===\n")
            
            click.echo(f"Privacy Level: {privacy_info.get('privacy_level', 'unknown').upper()}")
            click.echo(f"Encryption Status: {privacy_info.get('encryption_status', 'Unknown')}")
            click.echo(f"Secure Deletion: {'Enabled' if privacy_info.get('secure_deletion_enabled') else 'Disabled'}")
            
            retention_hours = privacy_info.get('retention_period_hours')
            if retention_hours:
                click.echo(f"Temp File Retention: {retention_hours} hours")
            
            last_cleanup = privacy_info.get('last_cleanup')
            if last_cleanup:
                click.echo(f"Last Cleanup: {last_cleanup}")
            else:
                click.echo("Last Cleanup: Never")
            
            click.echo(f"Temp Files Location: {privacy_info.get('temporary_files_location', 'Unknown')}")
            
            data_types = privacy_info.get('data_types_processed', [])
            if data_types:
                click.echo(f"Data Types Being Processed: {', '.join(data_types)}")
            
            click.echo(f"\nPrivacy Policy Summary:")
            click.echo(privacy_info.get('privacy_policy_summary', 'No summary available'))
            
    except Exception as e:
        click.echo(f"Error getting privacy information: {e}", err=True)
        raise click.Abort()


@privacy_cli.command()
@click.option('--max-age', default=1, type=int,
              help='Maximum age of temporary files to keep (hours)')
@click.option('--dry-run', is_flag=True,
              help='Show what would be deleted without actually deleting')
def cleanup(max_age: int, dry_run: bool):
    """Clean up temporary files and cached data"""
    try:
        credential_manager = CredentialManager()
        security_service = SecurityService(credential_manager)
        
        if dry_run:
            click.echo(f"DRY RUN: Would clean up temporary files older than {max_age} hours")
            # For dry run, we'd need to implement a preview method
            click.echo("Use --no-dry-run to perform actual cleanup")
        else:
            click.echo(f"Cleaning up temporary files older than {max_age} hours...")
            stats = security_service.cleanup_temporary_files(max_age)
            
            click.echo(f"Cleanup completed:")
            click.echo(f"  Registered files deleted: {stats.get('registered_files_deleted', 0)}")
            click.echo(f"  Old files deleted: {stats.get('old_files_deleted', 0)}")
            click.echo(f"  Errors: {stats.get('errors', 0)}")
            
    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
        raise click.Abort()


@privacy_cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def check_sensitivity(file_path: str):
    """Check if a file contains potentially sensitive data"""
    try:
        credential_manager = CredentialManager()
        security_service = SecurityService(credential_manager)
        
        sensitivity = security_service.check_file_sensitivity(Path(file_path))
        
        if sensitivity:
            click.echo(f"File '{file_path}' is potentially sensitive:")
            click.echo(f"  Description: {sensitivity['description']}")
            click.echo(f"  Privacy Level: {sensitivity['privacy_level'].upper()}")
            click.echo(f"  Recommended Action: {sensitivity['recommended_action']}")
            click.echo(f"  Pattern: {sensitivity['pattern']}")
        else:
            click.echo(f"File '{file_path}' does not match sensitive file patterns")
            
    except Exception as e:
        click.echo(f"Error checking file sensitivity: {e}", err=True)
        raise click.Abort()


@privacy_cli.command()
def patterns():
    """List sensitive file patterns used for privacy protection"""
    try:
        credential_manager = CredentialManager()
        security_service = SecurityService(credential_manager)
        
        patterns = security_service.get_sensitive_file_patterns()
        
        click.echo("=== Sensitive File Patterns ===\n")
        
        for name, pattern_info in patterns.items():
            click.echo(f"{name.upper()}:")
            click.echo(f"  Description: {pattern_info['description']}")
            click.echo(f"  Privacy Level: {pattern_info['privacy_level'].upper()}")
            click.echo(f"  Recommended Action: {pattern_info['recommended_action']}")
            click.echo(f"  Pattern: {pattern_info['pattern']}")
            click.echo()
            
    except Exception as e:
        click.echo(f"Error getting sensitive file patterns: {e}", err=True)
        raise click.Abort()


@privacy_cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--confirm', is_flag=True,
              help='Confirm deletion without prompting')
def secure_delete(file_path: str, confirm: bool):
    """Securely delete a file with multiple overwrites"""
    try:
        if not confirm:
            if not click.confirm(f"Are you sure you want to securely delete '{file_path}'? This cannot be undone."):
                click.echo("Deletion cancelled.")
                return
        
        credential_manager = CredentialManager()
        security_service = SecurityService(credential_manager)
        
        click.echo(f"Securely deleting '{file_path}'...")
        success = security_service.secure_delete_file(Path(file_path))
        
        if success:
            click.echo("File securely deleted.")
        else:
            click.echo("Failed to securely delete file.", err=True)
            raise click.Abort()
            
    except Exception as e:
        click.echo(f"Error during secure deletion: {e}", err=True)
        raise click.Abort()


@privacy_cli.command()
@click.option('--days', default=7, type=int,
              help='Number of days to include in statistics')
@click.option('--format', 'output_format', default='text',
              type=click.Choice(['text', 'json']),
              help='Output format')
def stats(days: int, output_format: str):
    """Show privacy cleanup statistics"""
    try:
        credential_manager = CredentialManager()
        security_service = SecurityService(credential_manager)
        
        statistics = security_service.get_privacy_cleanup_statistics(days)
        
        if output_format == 'json':
            click.echo(json.dumps(statistics, indent=2, default=str))
        else:
            click.echo(f"=== Privacy Cleanup Statistics ({days} days) ===\n")
            
            click.echo(f"Total Cleanups: {statistics.get('total_cleanups', 0)}")
            click.echo(f"Files Deleted: {statistics.get('files_deleted', 0)}")
            click.echo(f"Directories Deleted: {statistics.get('directories_deleted', 0)}")
            click.echo(f"Errors: {statistics.get('errors', 0)}")
            
            last_cleanup = statistics.get('last_cleanup')
            if last_cleanup:
                if isinstance(last_cleanup, str):
                    click.echo(f"Last Cleanup: {last_cleanup}")
                else:
                    click.echo(f"Last Cleanup: {last_cleanup.isoformat()}")
            else:
                click.echo("Last Cleanup: Never")
                
    except Exception as e:
        click.echo(f"Error getting cleanup statistics: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    privacy_cli()