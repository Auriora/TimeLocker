"""
Security Configuration CLI for TimeLocker.

This module provides command-line interface for security configuration
management, including validation, recommendations, and settings management.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import click

logger = logging.getLogger(__name__)


class SecurityConfigurationCLI:
    """
    Command-line interface for security configuration management.
    
    This class provides CLI commands for managing security configuration,
    following the Single Responsibility Principle by focusing on CLI operations.
    """

    def __init__(self, config_module: Optional['ConfigurationModule'] = None):
        """
        Initialize security configuration CLI.
        
        Args:
            config_module: Optional configuration module instance
        """
        self.config_module = config_module
        
    def _get_config_module(self):
        """Get configuration module instance"""
        if not self.config_module:
            from ..config import ConfigurationModule
            self.config_module = ConfigurationModule()
        return self.config_module

    def show_security_status(self, verbose: bool = False) -> None:
        """
        Show security configuration status.
        
        Args:
            verbose: Show detailed information
        """
        try:
            config_module = self._get_config_module()
            status = config_module.get_security_configuration_status()
            
            if "error" in status:
                click.echo(f"Error: {status['error']}", err=True)
                return
                
            # Display status
            click.echo("Security Configuration Status")
            click.echo("=" * 40)
            
            # Security level with color coding
            level = status.get("security_level", "unknown")
            level_colors = {
                "high": "green",
                "medium": "yellow", 
                "low": "red",
                "unknown": "red"
            }
            click.echo(f"Security Level: ", nl=False)
            click.secho(level.title(), fg=level_colors.get(level, "red"))
            
            # Compliance score
            score = status.get("compliance_score", 0.0)
            score_percentage = int(score * 100)
            score_color = "green" if score >= 0.8 else "yellow" if score >= 0.6 else "red"
            click.echo(f"Compliance Score: ", nl=False)
            click.secho(f"{score_percentage}%", fg=score_color)
            
            # Issues and warnings
            issues = status.get("issues_count", 0)
            warnings = status.get("warnings_count", 0)
            
            if issues > 0:
                click.secho(f"Security Issues: {issues}", fg="red")
            else:
                click.secho("Security Issues: None", fg="green")
                
            if warnings > 0:
                click.secho(f"Warnings: {warnings}", fg="yellow")
            else:
                click.secho("Warnings: None", fg="green")
                
            # Last validated
            last_validated = status.get("last_validated", "")
            if last_validated:
                click.echo(f"Last Validated: {last_validated}")
                
            # Recommendations count
            recommendations = status.get("recommendations", [])
            if recommendations:
                click.echo(f"Recommendations: {len(recommendations)} available")
                
            if verbose:
                click.echo("\nDetailed Information:")
                click.echo("-" * 20)
                
                # Show recommendations
                if recommendations:
                    click.echo("\nRecommendations:")
                    for i, rec in enumerate(recommendations, 1):
                        click.echo(f"  {i}. {rec}")
                        
        except Exception as e:
            click.echo(f"Error showing security status: {e}", err=True)

    def validate_security_configuration(self, level: str = "moderate", fix: bool = False) -> None:
        """
        Validate security configuration.
        
        Args:
            level: Validation level (strict, moderate, permissive)
            fix: Attempt to fix issues automatically
        """
        try:
            config_module = self._get_config_module()
            result = config_module.validate_security_configuration(level)
            
            click.echo("Security Configuration Validation")
            click.echo("=" * 40)
            
            if result.is_valid:
                click.secho("✓ Configuration is valid", fg="green")
            else:
                click.secho("✗ Configuration has issues", fg="red")
                
            # Show errors
            if result.errors:
                click.echo("\nErrors:")
                for error in result.errors:
                    click.secho(f"  • {error}", fg="red")
                    
            # Show warnings
            if result.warnings:
                click.echo("\nWarnings:")
                for warning in result.warnings:
                    click.secho(f"  • {warning}", fg="yellow")
                    
            # Attempt fixes if requested
            if fix and not result.is_valid:
                click.echo("\nAttempting to fix issues...")
                
                # Get and apply recommendations
                recommendations = config_module.get_security_recommendations()
                if recommendations:
                    critical_recs = [rec["setting"] for rec in recommendations if rec["priority"] == "critical"]
                    if critical_recs:
                        fix_result = config_module.apply_security_recommendations(critical_recs)
                        if fix_result.is_valid:
                            click.secho("✓ Critical issues fixed", fg="green")
                        else:
                            click.secho("✗ Failed to fix some issues", fg="red")
                            for error in fix_result.errors:
                                click.echo(f"  • {error}")
                                
        except Exception as e:
            click.echo(f"Error validating security configuration: {e}", err=True)

    def show_security_recommendations(self, priority: Optional[str] = None, apply: bool = False) -> None:
        """
        Show security recommendations.
        
        Args:
            priority: Filter by priority (critical, high, medium, low)
            apply: Apply recommendations interactively
        """
        try:
            config_module = self._get_config_module()
            recommendations = config_module.get_security_recommendations()
            
            if not recommendations:
                click.secho("No security recommendations available", fg="green")
                return
                
            # Filter by priority if specified
            if priority:
                recommendations = [rec for rec in recommendations if rec.get("priority") == priority]
                
            if not recommendations:
                click.echo(f"No {priority} priority recommendations found")
                return
                
            click.echo("Security Recommendations")
            click.echo("=" * 40)
            
            # Group by priority
            priority_colors = {
                "critical": "red",
                "high": "yellow",
                "medium": "blue",
                "low": "cyan"
            }
            
            recommendations_by_priority = {}
            for rec in recommendations:
                rec_priority = rec.get("priority", "medium")
                if rec_priority not in recommendations_by_priority:
                    recommendations_by_priority[rec_priority] = []
                recommendations_by_priority[rec_priority].append(rec)
                
            # Display recommendations
            for priority_level in ["critical", "high", "medium", "low"]:
                if priority_level in recommendations_by_priority:
                    recs = recommendations_by_priority[priority_level]
                    color = priority_colors.get(priority_level, "white")
                    
                    click.secho(f"\n{priority_level.title()} Priority:", fg=color, bold=True)
                    
                    for i, rec in enumerate(recs, 1):
                        click.echo(f"  {i}. {rec.get('title', 'Unknown')}")
                        click.echo(f"     {rec.get('description', '')}")
                        click.echo(f"     Action: {rec.get('action', '')}")
                        if rec.get("setting"):
                            click.echo(f"     Setting: {rec['setting']}")
                        click.echo()
                        
            # Interactive application
            if apply:
                self._apply_recommendations_interactively(recommendations)
                
        except Exception as e:
            click.echo(f"Error showing security recommendations: {e}", err=True)

    def _apply_recommendations_interactively(self, recommendations: List[Dict[str, Any]]) -> None:
        """Apply recommendations interactively"""
        try:
            config_module = self._get_config_module()
            
            click.echo("Apply Recommendations")
            click.echo("=" * 20)
            
            selected_settings = []
            
            for rec in recommendations:
                setting = rec.get("setting", "")
                if not setting:
                    continue
                    
                title = rec.get("title", "Unknown")
                description = rec.get("description", "")
                
                if click.confirm(f"Apply '{title}'?\n  {description}"):
                    selected_settings.append(setting)
                    
            if selected_settings:
                click.echo(f"\nApplying {len(selected_settings)} recommendations...")
                
                result = config_module.apply_security_recommendations(selected_settings)
                
                if result.is_valid:
                    click.secho("✓ Recommendations applied successfully", fg="green")
                else:
                    click.secho("✗ Some recommendations failed to apply", fg="red")
                    for error in result.errors:
                        click.echo(f"  • {error}")
            else:
                click.echo("No recommendations selected")
                
        except Exception as e:
            click.echo(f"Error applying recommendations: {e}", err=True)

    def update_security_setting(self, setting: str, value: str, validate: bool = True) -> None:
        """
        Update a security configuration setting.
        
        Args:
            setting: Setting name to update
            value: New value for the setting
            validate: Whether to validate before applying
        """
        try:
            config_module = self._get_config_module()
            
            # Convert value to appropriate type
            converted_value = self._convert_setting_value(setting, value)
            
            updates = {setting: converted_value}
            result = config_module.update_security_configuration(updates, validate)
            
            if result.is_valid:
                click.secho(f"✓ Updated {setting} = {converted_value}", fg="green")
            else:
                click.secho(f"✗ Failed to update {setting}", fg="red")
                for error in result.errors:
                    click.echo(f"  • {error}")
                    
        except Exception as e:
            click.echo(f"Error updating security setting: {e}", err=True)

    def _convert_setting_value(self, setting: str, value: str) -> Any:
        """Convert string value to appropriate type for setting"""
        # Boolean settings
        boolean_settings = [
            "encryption_enabled", "audit_logging", "password_strength_check", 
            "require_password_confirmation"
        ]
        
        if setting in boolean_settings:
            return value.lower() in ("true", "1", "yes", "on", "enabled")
            
        # Integer settings
        integer_settings = [
            "credential_timeout", "max_failed_attempts", "lockout_duration"
        ]
        
        if setting in integer_settings:
            return int(value)
            
        # Default to string
        return value

    def export_security_configuration(self, output_path: str, include_sensitive: bool = False) -> None:
        """
        Export security configuration to file.
        
        Args:
            output_path: Path to export file
            include_sensitive: Whether to include sensitive settings
        """
        try:
            config_module = self._get_config_module()
            output_file = Path(output_path)
            
            success = config_module.export_security_configuration(output_file, include_sensitive)
            
            if success:
                click.secho(f"✓ Security configuration exported to {output_path}", fg="green")
            else:
                click.secho(f"✗ Failed to export security configuration", fg="red")
                
        except Exception as e:
            click.echo(f"Error exporting security configuration: {e}", err=True)

    def import_security_configuration(self, import_path: str, validate: bool = True) -> None:
        """
        Import security configuration from file.
        
        Args:
            import_path: Path to import file
            validate: Whether to validate imported configuration
        """
        try:
            config_module = self._get_config_module()
            import_file = Path(import_path)
            
            if not import_file.exists():
                click.secho(f"✗ Import file not found: {import_path}", fg="red")
                return
                
            result = config_module.import_security_configuration(import_file, validate)
            
            if result.is_valid:
                click.secho(f"✓ Security configuration imported from {import_path}", fg="green")
            else:
                click.secho(f"✗ Failed to import security configuration", fg="red")
                for error in result.errors:
                    click.echo(f"  • {error}")
                    
        except Exception as e:
            click.echo(f"Error importing security configuration: {e}", err=True)

    def reset_security_configuration(self, confirm: bool = False) -> None:
        """
        Reset security configuration to defaults.
        
        Args:
            confirm: Skip confirmation prompt
        """
        try:
            if not confirm:
                if not click.confirm("Reset security configuration to defaults? This cannot be undone."):
                    click.echo("Reset cancelled")
                    return
                    
            config_module = self._get_config_module()
            result = config_module.reset_security_configuration()
            
            if result.is_valid:
                click.secho("✓ Security configuration reset to defaults", fg="green")
            else:
                click.secho("✗ Failed to reset security configuration", fg="red")
                for error in result.errors:
                    click.echo(f"  • {error}")
                    
        except Exception as e:
            click.echo(f"Error resetting security configuration: {e}", err=True)

    def show_security_summary(self, format_type: str = "table") -> None:
        """
        Show security configuration summary.
        
        Args:
            format_type: Output format (table, json)
        """
        try:
            config_module = self._get_config_module()
            summary = config_module.get_security_configuration_summary()
            
            if "error" in summary:
                click.echo(f"Error: {summary['error']}", err=True)
                return
                
            if format_type == "json":
                click.echo(json.dumps(summary, indent=2))
            else:
                # Table format
                click.echo("Security Configuration Summary")
                click.echo("=" * 40)
                
                # Basic settings
                click.echo(f"Encryption Enabled: {summary.get('encryption_enabled', 'Unknown')}")
                click.echo(f"Audit Logging: {summary.get('audit_logging', 'Unknown')}")
                click.echo(f"Credential Timeout: {summary.get('credential_timeout_minutes', 'Unknown')} minutes")
                click.echo(f"Max Failed Attempts: {summary.get('max_failed_attempts', 'Unknown')}")
                click.echo(f"Lockout Duration: {summary.get('lockout_duration_minutes', 'Unknown')} minutes")
                click.echo(f"Password Strength Check: {summary.get('password_strength_check', 'Unknown')}")
                click.echo(f"Require Password Confirmation: {summary.get('require_password_confirmation', 'Unknown')}")
                
                # Status information
                click.echo(f"\nSecurity Level: {summary.get('security_level', 'Unknown').title()}")
                click.echo(f"Compliance Score: {int(summary.get('compliance_score', 0) * 100)}%")
                click.echo(f"Issues: {summary.get('issues_count', 0)}")
                click.echo(f"Warnings: {summary.get('warnings_count', 0)}")
                click.echo(f"Recommendations: {summary.get('recommendations_count', 0)}")
                
        except Exception as e:
            click.echo(f"Error showing security summary: {e}", err=True)