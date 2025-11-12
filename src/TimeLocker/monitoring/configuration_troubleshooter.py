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

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from .troubleshooting_service import (
    IssueType,
    IssueSeverity,
    TroubleshootingStep,
    TroubleshootingGuide,
    ProactiveRecommendation
)

logger = logging.getLogger(__name__)


@dataclass
class ConfigurationIssue:
    """Represents a configuration-related issue"""
    issue_type: str
    severity: IssueSeverity
    description: str
    affected_section: str
    current_value: Optional[Any] = None
    recommended_value: Optional[Any] = None
    validation_error: Optional[str] = None


class ConfigurationTroubleshooter:
    """
    Provides configuration-specific troubleshooting guidance.
    
    Integrates with Configuration Management to provide:
    - Configuration validation and troubleshooting
    - Common setup issue detection
    - Step-by-step configuration guides
    
    Requirements: 9.4, 9.5
    """
    
    def __init__(self, config_module=None):
        """
        Initialize configuration troubleshooter.
        
        Args:
            config_module: Optional ConfigurationModule instance for validation
        """
        self.config_module = config_module
        logger.info("ConfigurationTroubleshooter initialized")
    
    def validate_configuration(self) -> List[ConfigurationIssue]:
        """
        Validate current configuration and identify issues.
        
        Returns:
            List of configuration issues found
            
        Requirements: 9.4
        """
        issues = []
        
        if not self.config_module:
            logger.warning("No configuration module provided, skipping validation")
            return issues
        
        try:
            # Get current configuration
            config = self.config_module.get_config()
            
            # Validate repositories
            if not config.repositories:
                issues.append(ConfigurationIssue(
                    issue_type="missing_repositories",
                    severity=IssueSeverity.HIGH,
                    description="No backup repositories configured",
                    affected_section="repositories",
                    recommended_value="At least one repository should be configured"
                ))
            else:
                # Check each repository
                for repo_name, repo_config in config.repositories.items():
                    repo_issues = self._validate_repository(repo_name, repo_config)
                    issues.extend(repo_issues)
            
            # Validate default repository
            default_repo = config.general.default_repository
            if default_repo and default_repo not in config.repositories:
                issues.append(ConfigurationIssue(
                    issue_type="invalid_default_repository",
                    severity=IssueSeverity.MEDIUM,
                    description=f"Default repository '{default_repo}' does not exist",
                    affected_section="general.default_repository",
                    current_value=default_repo,
                    recommended_value="Set to an existing repository name or None"
                ))
            
            # Validate backup targets
            if config.backup_targets:
                for target_name, target_config in config.backup_targets.items():
                    target_issues = self._validate_backup_target(target_name, target_config)
                    issues.extend(target_issues)
            
            logger.info(f"Configuration validation found {len(issues)} issue(s)")
            
        except Exception as e:
            logger.error(f"Failed to validate configuration: {e}")
            issues.append(ConfigurationIssue(
                issue_type="validation_error",
                severity=IssueSeverity.CRITICAL,
                description=f"Configuration validation failed: {str(e)}",
                affected_section="unknown",
                validation_error=str(e)
            ))
        
        return issues
    
    def _validate_repository(self, name: str, repo_config) -> List[ConfigurationIssue]:
        """
        Validate a repository configuration.
        
        Args:
            name: Repository name
            repo_config: Repository configuration object
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check for required fields
        if not hasattr(repo_config, 'location') or not repo_config.location:
            issues.append(ConfigurationIssue(
                issue_type="missing_repository_location",
                severity=IssueSeverity.HIGH,
                description=f"Repository '{name}' has no location configured",
                affected_section=f"repositories.{name}.location",
                recommended_value="Valid repository URI (e.g., s3://bucket/path, /local/path)"
            ))
        else:
            # Validate location format
            location = repo_config.location
            if not self._is_valid_repository_location(location):
                issues.append(ConfigurationIssue(
                    issue_type="invalid_repository_location",
                    severity=IssueSeverity.MEDIUM,
                    description=f"Repository '{name}' has invalid location format",
                    affected_section=f"repositories.{name}.location",
                    current_value=location,
                    recommended_value="Valid URI format (s3://, sftp://, /path, etc.)"
                ))
        
        return issues
    
    def _validate_backup_target(self, name: str, target_config) -> List[ConfigurationIssue]:
        """
        Validate a backup target configuration (deprecated - use data selection templates).
        
        Args:
            name: Target name
            target_config: Target configuration object
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check for required fields
        if not hasattr(target_config, 'paths') or not target_config.paths:
            issues.append(ConfigurationIssue(
                issue_type="missing_target_paths",
                severity=IssueSeverity.MEDIUM,
                description=f"Backup target '{name}' has no paths configured (deprecated - use data selection templates)",
                affected_section=f"backup_targets.{name}.paths",
                recommended_value="Migrate to data selection templates using 'timelocker selections create'"
            ))
        else:
            # Validate paths exist
            for path in target_config.paths:
                if not Path(path).exists():
                    issues.append(ConfigurationIssue(
                        issue_type="target_path_not_found",
                        severity=IssueSeverity.LOW,
                        description=f"Backup target '{name}' path does not exist: {path} (deprecated - use data selection templates)",
                        affected_section=f"backup_targets.{name}.paths",
                        current_value=path,
                        recommended_value="Migrate to data selection templates using 'timelocker selections create'"
                    ))
        
        return issues
    
    def _is_valid_repository_location(self, location: str) -> bool:
        """
        Check if repository location has valid format.
        
        Args:
            location: Repository location string
            
        Returns:
            True if format appears valid
        """
        if not location:
            return False
        
        # Check for common URI schemes
        valid_schemes = ['s3://', 'sftp://', 'rest://', 'file://', 'b2://']
        if any(location.startswith(scheme) for scheme in valid_schemes):
            return True
        
        # Check for absolute path
        if location.startswith('/'):
            return True
        
        # Check for Windows path
        if len(location) >= 3 and location[1] == ':' and location[2] in ['/', '\\']:
            return True
        
        return False
    
    def get_configuration_troubleshooting_guide(
        self,
        issue_type: str
    ) -> TroubleshootingGuide:
        """
        Get troubleshooting guide for configuration issues.
        
        Args:
            issue_type: Type of configuration issue
            
        Returns:
            Troubleshooting guide
            
        Requirements: 9.4, 9.5
        """
        guides = {
            'missing_repositories': self._create_missing_repositories_guide(),
            'invalid_repository_location': self._create_invalid_repository_guide(),
            'invalid_default_repository': self._create_invalid_default_guide(),
            'missing_target_paths': self._create_missing_paths_guide(),
            'target_path_not_found': self._create_path_not_found_guide()
        }
        
        return guides.get(issue_type, self._create_generic_config_guide())
    
    def get_setup_recommendations(self) -> List[ProactiveRecommendation]:
        """
        Get proactive recommendations for configuration setup.
        
        Returns:
            List of setup recommendations
            
        Requirements: 9.4, 9.5
        """
        recommendations = []
        
        if not self.config_module:
            return recommendations
        
        try:
            config = self.config_module.get_config()
            
            # Recommend setting default repository if not set
            if not config.general.default_repository and config.repositories:
                recommendations.append(ProactiveRecommendation(
                    recommendation_id="set_default_repository",
                    title="Set Default Repository",
                    description="Setting a default repository simplifies backup commands",
                    priority=IssueSeverity.LOW,
                    action_items=[
                        "Choose your primary backup repository",
                        "Run: timelocker config set-default-repository <name>",
                        "Verify with: timelocker config show"
                    ],
                    estimated_impact="Simplified backup operations"
                ))
            
            # Recommend configuring data selection templates
            if not config.backup_targets:
                recommendations.append(ProactiveRecommendation(
                    recommendation_id="configure_data_selections",
                    title="Configure Data Selection Templates",
                    description="Define data selection templates to organize what gets backed up",
                    priority=IssueSeverity.MEDIUM,
                    action_items=[
                        "Identify directories to backup",
                        "Create data selection template configurations",
                        "Test backup with: timelocker backup create --selection <template_name>"
                    ],
                    estimated_impact="Organized and repeatable backups"
                ))
            
            # Recommend testing backups
            if config.repositories:
                recommendations.append(ProactiveRecommendation(
                    recommendation_id="test_backup_restore",
                    title="Test Backup and Restore",
                    description="Verify your backup configuration works correctly",
                    priority=IssueSeverity.HIGH,
                    action_items=[
                        "Run a test backup of a small directory",
                        "Verify backup appears in snapshots",
                        "Test restore to a temporary location",
                        "Verify restored files match originals"
                    ],
                    estimated_impact="Confidence in backup reliability"
                ))
            
        except Exception as e:
            logger.error(f"Failed to generate setup recommendations: {e}")
        
        return recommendations
    
    def _create_missing_repositories_guide(self) -> TroubleshootingGuide:
        """Create guide for missing repositories issue"""
        return TroubleshootingGuide(
            issue_type=IssueType.CONFIGURATION_ERROR,
            title="No Repositories Configured",
            description="At least one backup repository must be configured before backups can be performed.",
            possible_causes=[
                "Fresh installation with no configuration",
                "Configuration file was reset or corrupted",
                "All repositories were removed"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Add a backup repository",
                    command="timelocker repository add <name> <location>",
                    expected_result="Repository is added to configuration",
                    additional_info="Example: timelocker repository add mybackup /mnt/backup"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Initialize the repository",
                    command="timelocker repository init <name>",
                    expected_result="Repository is initialized and ready for use"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Set as default repository (optional)",
                    command="timelocker config set-default-repository <name>",
                    expected_result="Repository is set as default"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Verify configuration",
                    command="timelocker repository list",
                    expected_result="Shows configured repository"
                )
            ],
            additional_resources=[
                "Repository configuration guide",
                "Getting started documentation"
            ],
            prevention_tips=[
                "Keep configuration backups",
                "Document repository locations",
                "Test configuration after changes"
            ]
        )
    
    def _create_invalid_repository_guide(self) -> TroubleshootingGuide:
        """Create guide for invalid repository location"""
        return TroubleshootingGuide(
            issue_type=IssueType.CONFIGURATION_ERROR,
            title="Invalid Repository Location",
            description="The repository location format is invalid or not recognized.",
            possible_causes=[
                "Typo in repository URI",
                "Unsupported repository type",
                "Incorrect URI format",
                "Missing required URI components"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Check repository location format",
                    command="timelocker repository show <name>",
                    expected_result="Displays current repository configuration"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Update repository location with correct format",
                    command="timelocker repository update <name> --location <new_location>",
                    expected_result="Repository location is updated",
                    additional_info="Valid formats: s3://bucket/path, sftp://host/path, /local/path"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Test repository connectivity",
                    command="timelocker repository check <name>",
                    expected_result="Repository is accessible"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Verify configuration",
                    command="timelocker config validate",
                    expected_result="Configuration is valid"
                )
            ],
            additional_resources=[
                "Repository URI format documentation",
                "Supported repository types"
            ],
            prevention_tips=[
                "Use repository URI examples as templates",
                "Validate configuration after changes",
                "Test repository connectivity after setup"
            ]
        )
    
    def _create_invalid_default_guide(self) -> TroubleshootingGuide:
        """Create guide for invalid default repository"""
        return TroubleshootingGuide(
            issue_type=IssueType.CONFIGURATION_ERROR,
            title="Invalid Default Repository",
            description="The configured default repository does not exist.",
            possible_causes=[
                "Repository was removed but default not updated",
                "Repository name was changed",
                "Configuration inconsistency"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="List available repositories",
                    command="timelocker repository list",
                    expected_result="Shows all configured repositories"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Set default to an existing repository",
                    command="timelocker config set-default-repository <existing_name>",
                    expected_result="Default repository is updated"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Verify configuration",
                    command="timelocker config show",
                    expected_result="Shows updated default repository"
                )
            ],
            additional_resources=[
                "Configuration management guide"
            ],
            prevention_tips=[
                "Update default before removing repositories",
                "Verify configuration after repository changes"
            ]
        )
    
    def _create_missing_paths_guide(self) -> TroubleshootingGuide:
        """Create guide for missing data selection template paths"""
        return TroubleshootingGuide(
            issue_type=IssueType.CONFIGURATION_ERROR,
            title="Missing Data Selection Template Paths",
            description="Data selection template has no paths configured.",
            possible_causes=[
                "Incomplete selection template configuration",
                "Paths were removed",
                "Configuration error"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Add paths to data selection template",
                    command="timelocker selections create <name> --include <path>",
                    expected_result="Selection template is created with configured paths",
                    additional_info="Can add multiple include/exclude patterns to same template"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Verify selection template configuration",
                    command="timelocker selections show <name>",
                    expected_result="Shows selection template with configured paths"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Test backup with selection template",
                    command="timelocker backup create --selection <selection_name>",
                    expected_result="Backup runs successfully"
                )
            ],
            additional_resources=[
                "Data selection template configuration guide"
            ],
            prevention_tips=[
                "Verify selection template configuration before first use",
                "Document data selection template purposes"
            ]
        )
    
    def _create_path_not_found_guide(self) -> TroubleshootingGuide:
        """Create guide for path not found issues"""
        return TroubleshootingGuide(
            issue_type=IssueType.CONFIGURATION_ERROR,
            title="Backup Path Not Found",
            description="A configured backup path does not exist on the system.",
            possible_causes=[
                "Path was moved or deleted",
                "Typo in path configuration",
                "Mount point not available",
                "Network drive not connected"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Verify the path exists",
                    command="ls -la <path>",
                    expected_result="Path exists and is accessible"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="If path was moved, update selection template",
                    command="timelocker selections update <name> --include <new_path>",
                    expected_result="Path is updated in selection template"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="If path no longer needed, remove from template",
                    command="timelocker selections update <name> --remove-include <path>",
                    expected_result="Path is removed from selection template"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Verify selection template configuration",
                    command="timelocker selections show <name>",
                    expected_result="Shows updated selection template configuration"
                )
            ],
            additional_resources=[
                "Data selection template management guide"
            ],
            prevention_tips=[
                "Use stable paths for data selection templates",
                "Document path dependencies",
                "Review configuration when moving files"
            ]
        )
    
    def _create_generic_config_guide(self) -> TroubleshootingGuide:
        """Create generic configuration troubleshooting guide"""
        return TroubleshootingGuide(
            issue_type=IssueType.CONFIGURATION_ERROR,
            title="Configuration Issue",
            description="A configuration problem has been detected.",
            possible_causes=[
                "Invalid configuration syntax",
                "Missing required settings",
                "Inconsistent configuration"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Validate configuration",
                    command="timelocker config validate",
                    expected_result="Reports any configuration errors"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Review configuration",
                    command="timelocker config show",
                    expected_result="Displays current configuration"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Check configuration file syntax",
                    additional_info="Ensure JSON syntax is valid if editing manually"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="If needed, restore from backup",
                    additional_info="Configuration backups are in the config directory"
                )
            ],
            additional_resources=[
                "Configuration reference documentation",
                "Configuration examples"
            ],
            prevention_tips=[
                "Validate after making changes",
                "Keep configuration backups",
                "Use CLI commands instead of manual editing"
            ]
        )
