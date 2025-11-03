"""
Security Configuration UI Components for TimeLocker.

This module provides user interface components for security configuration
management, including forms, validation displays, and interactive elements.
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class UIComponentType(Enum):
    """UI component types"""
    FORM = "form"
    DISPLAY = "display"
    VALIDATION = "validation"
    RECOMMENDATION = "recommendation"
    STATUS = "status"


class UIValidationState(Enum):
    """UI validation states"""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class UIComponent:
    """Base UI component definition"""
    component_id: str
    component_type: UIComponentType
    title: str
    description: str
    is_visible: bool = True
    is_enabled: bool = True
    css_classes: List[str] = None
    
    def __post_init__(self):
        if self.css_classes is None:
            self.css_classes = []


@dataclass
class UIFormField:
    """UI form field definition"""
    field_id: str
    field_type: str  # text, number, boolean, select, etc.
    label: str
    description: str
    value: Any = None
    default_value: Any = None
    is_required: bool = False
    is_readonly: bool = False
    validation_state: UIValidationState = UIValidationState.VALID
    validation_message: str = ""
    options: List[Dict[str, Any]] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    placeholder: str = ""
    help_text: str = ""
    
    def __post_init__(self):
        if self.options is None:
            self.options = []


@dataclass
class UIValidationDisplay:
    """UI validation display component"""
    validation_id: str
    state: UIValidationState
    title: str
    message: str
    details: List[str] = None
    actions: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = []
        if self.actions is None:
            self.actions = []


@dataclass
class UIRecommendation:
    """UI recommendation component"""
    recommendation_id: str
    priority: str  # critical, high, medium, low
    category: str
    title: str
    description: str
    action_text: str
    is_applied: bool = False
    can_apply: bool = True
    estimated_impact: str = ""
    
    
@dataclass
class UIStatusIndicator:
    """UI status indicator component"""
    status_id: str
    label: str
    value: str
    state: UIValidationState
    icon: str = ""
    tooltip: str = ""


class SecurityConfigurationUI:
    """
    Security configuration UI components manager.
    
    This class provides methods to generate and manage UI components
    for security configuration, following the Single Responsibility Principle.
    """

    def __init__(self, security_config_manager: Optional['SecurityConfigurationManager'] = None):
        """
        Initialize security configuration UI.
        
        Args:
            security_config_manager: Optional security configuration manager instance
        """
        self.security_config_manager = security_config_manager
        self._component_registry = {}
        self._event_handlers = {}
        
    def create_security_configuration_form(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create security configuration form components.
        
        Args:
            current_config: Current security configuration
            
        Returns:
            Dict: Form component definitions
        """
        try:
            form_fields = []
            
            # Encryption settings
            form_fields.append(UIFormField(
                field_id="encryption_enabled",
                field_type="boolean",
                label="Enable Encryption",
                description="Encrypt all backup data using industry-standard encryption",
                value=current_config.get("encryption_enabled", True),
                default_value=True,
                is_required=True,
                help_text="Disabling encryption is not recommended for security reasons"
            ))
            
            # Audit logging
            form_fields.append(UIFormField(
                field_id="audit_logging",
                field_type="boolean",
                label="Enable Audit Logging",
                description="Log security events for monitoring and troubleshooting",
                value=current_config.get("audit_logging", True),
                default_value=True,
                help_text="Audit logging helps track security events and diagnose issues"
            ))
            
            # Credential timeout
            form_fields.append(UIFormField(
                field_id="credential_timeout",
                field_type="number",
                label="Credential Timeout (minutes)",
                description="How long credentials remain valid without re-authentication",
                value=current_config.get("credential_timeout", 3600) // 60,  # Convert to minutes
                default_value=60,
                min_value=5,
                max_value=240,
                help_text="Shorter timeouts are more secure but less convenient"
            ))
            
            # Max failed attempts
            form_fields.append(UIFormField(
                field_id="max_failed_attempts",
                field_type="number",
                label="Maximum Failed Attempts",
                description="Number of failed authentication attempts before lockout",
                value=current_config.get("max_failed_attempts", 3),
                default_value=3,
                min_value=1,
                max_value=10,
                help_text="Lower values provide better protection against brute force attacks"
            ))
            
            # Lockout duration
            form_fields.append(UIFormField(
                field_id="lockout_duration",
                field_type="number",
                label="Lockout Duration (minutes)",
                description="How long to lock out after maximum failed attempts",
                value=current_config.get("lockout_duration", 300) // 60,  # Convert to minutes
                default_value=5,
                min_value=1,
                max_value=60,
                help_text="Balance security with user convenience"
            ))
            
            # Password strength checking
            form_fields.append(UIFormField(
                field_id="password_strength_check",
                field_type="boolean",
                label="Enable Password Strength Checking",
                description="Validate password strength when setting passwords",
                value=current_config.get("password_strength_check", True),
                default_value=True,
                help_text="Helps ensure strong passwords are used"
            ))
            
            # Password confirmation
            form_fields.append(UIFormField(
                field_id="require_password_confirmation",
                field_type="boolean",
                label="Require Password Confirmation",
                description="Require password confirmation for sensitive operations",
                value=current_config.get("require_password_confirmation", True),
                default_value=True,
                help_text="Adds an extra layer of security for critical operations"
            ))
            
            # Create form component
            form_component = UIComponent(
                component_id="security_configuration_form",
                component_type=UIComponentType.FORM,
                title="Security Configuration",
                description="Configure security settings for TimeLocker",
                css_classes=["security-form", "config-form"]
            )
            
            return {
                "component": form_component,
                "fields": [field.__dict__ for field in form_fields],
                "validation_rules": self._get_form_validation_rules(),
                "help_sections": self._get_form_help_sections()
            }
            
        except Exception as e:
            logger.error(f"Failed to create security configuration form: {e}")
            return {"error": str(e)}

    def create_security_status_display(self, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create security status display components.
        
        Args:
            status_data: Security status information
            
        Returns:
            Dict: Status display component definitions
        """
        try:
            status_indicators = []
            
            # Overall security level
            security_level = status_data.get("security_level", "unknown")
            level_state = UIValidationState.VALID if security_level == "high" else \
                         UIValidationState.WARNING if security_level == "medium" else \
                         UIValidationState.ERROR
                         
            status_indicators.append(UIStatusIndicator(
                status_id="security_level",
                label="Security Level",
                value=security_level.title(),
                state=level_state,
                icon=self._get_security_level_icon(security_level),
                tooltip=f"Overall security assessment: {security_level}"
            ))
            
            # Compliance score
            compliance_score = status_data.get("compliance_score", 0.0)
            compliance_percentage = int(compliance_score * 100)
            compliance_state = UIValidationState.VALID if compliance_score >= 0.8 else \
                              UIValidationState.WARNING if compliance_score >= 0.6 else \
                              UIValidationState.ERROR
                              
            status_indicators.append(UIStatusIndicator(
                status_id="compliance_score",
                label="Compliance Score",
                value=f"{compliance_percentage}%",
                state=compliance_state,
                icon="percentage",
                tooltip=f"Security configuration compliance: {compliance_percentage}%"
            ))
            
            # Issues count
            issues_count = status_data.get("issues_count", 0)
            issues_state = UIValidationState.VALID if issues_count == 0 else UIValidationState.ERROR
            
            status_indicators.append(UIStatusIndicator(
                status_id="issues_count",
                label="Security Issues",
                value=str(issues_count),
                state=issues_state,
                icon="alert-triangle" if issues_count > 0 else "check-circle",
                tooltip=f"{issues_count} security issues found"
            ))
            
            # Warnings count
            warnings_count = status_data.get("warnings_count", 0)
            warnings_state = UIValidationState.VALID if warnings_count == 0 else UIValidationState.WARNING
            
            status_indicators.append(UIStatusIndicator(
                status_id="warnings_count",
                label="Warnings",
                value=str(warnings_count),
                state=warnings_state,
                icon="alert-circle" if warnings_count > 0 else "check-circle",
                tooltip=f"{warnings_count} security warnings found"
            ))
            
            # Encryption status
            encryption_enabled = status_data.get("encryption_enabled", False)
            encryption_state = UIValidationState.VALID if encryption_enabled else UIValidationState.ERROR
            
            status_indicators.append(UIStatusIndicator(
                status_id="encryption_status",
                label="Encryption",
                value="Enabled" if encryption_enabled else "Disabled",
                state=encryption_state,
                icon="shield" if encryption_enabled else "shield-off",
                tooltip="Data encryption status"
            ))
            
            # Audit logging status
            audit_logging = status_data.get("audit_logging", False)
            audit_state = UIValidationState.VALID if audit_logging else UIValidationState.WARNING
            
            status_indicators.append(UIStatusIndicator(
                status_id="audit_logging_status",
                label="Audit Logging",
                value="Enabled" if audit_logging else "Disabled",
                state=audit_state,
                icon="file-text" if audit_logging else "file-x",
                tooltip="Security event logging status"
            ))
            
            # Create status display component
            status_component = UIComponent(
                component_id="security_status_display",
                component_type=UIComponentType.STATUS,
                title="Security Status",
                description="Current security configuration status",
                css_classes=["security-status", "status-grid"]
            )
            
            return {
                "component": status_component,
                "indicators": [indicator.__dict__ for indicator in status_indicators],
                "last_updated": status_data.get("last_validated", ""),
                "refresh_interval": 300  # 5 minutes
            }
            
        except Exception as e:
            logger.error(f"Failed to create security status display: {e}")
            return {"error": str(e)}

    def create_validation_display(self, validation_result: 'ValidationResult') -> Dict[str, Any]:
        """
        Create validation display components.
        
        Args:
            validation_result: Validation result to display
            
        Returns:
            Dict: Validation display component definitions
        """
        try:
            validation_displays = []
            
            # Overall validation status
            overall_state = UIValidationState.VALID if validation_result.is_valid else UIValidationState.ERROR
            
            validation_displays.append(UIValidationDisplay(
                validation_id="overall_validation",
                state=overall_state,
                title="Configuration Validation",
                message="Valid configuration" if validation_result.is_valid else "Configuration has issues",
                details=validation_result.errors + validation_result.warnings,
                actions=[
                    {"id": "fix_issues", "label": "Fix Issues", "type": "primary"},
                    {"id": "ignore_warnings", "label": "Ignore Warnings", "type": "secondary"}
                ] if not validation_result.is_valid else []
            ))
            
            # Error details
            if validation_result.errors:
                validation_displays.append(UIValidationDisplay(
                    validation_id="validation_errors",
                    state=UIValidationState.ERROR,
                    title="Configuration Errors",
                    message=f"{len(validation_result.errors)} errors found",
                    details=validation_result.errors,
                    actions=[
                        {"id": "auto_fix_errors", "label": "Auto-Fix Errors", "type": "primary"},
                        {"id": "reset_to_defaults", "label": "Reset to Defaults", "type": "secondary"}
                    ]
                ))
                
            # Warning details
            if validation_result.warnings:
                validation_displays.append(UIValidationDisplay(
                    validation_id="validation_warnings",
                    state=UIValidationState.WARNING,
                    title="Configuration Warnings",
                    message=f"{len(validation_result.warnings)} warnings found",
                    details=validation_result.warnings,
                    actions=[
                        {"id": "apply_recommendations", "label": "Apply Recommendations", "type": "primary"},
                        {"id": "dismiss_warnings", "label": "Dismiss", "type": "secondary"}
                    ]
                ))
                
            # Create validation component
            validation_component = UIComponent(
                component_id="security_validation_display",
                component_type=UIComponentType.VALIDATION,
                title="Security Validation",
                description="Security configuration validation results",
                css_classes=["security-validation", "validation-panel"]
            )
            
            return {
                "component": validation_component,
                "displays": [display.__dict__ for display in validation_displays],
                "summary": {
                    "is_valid": validation_result.is_valid,
                    "error_count": len(validation_result.errors),
                    "warning_count": len(validation_result.warnings)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create validation display: {e}")
            return {"error": str(e)}

    def create_recommendations_display(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create recommendations display components.
        
        Args:
            recommendations: List of security recommendations
            
        Returns:
            Dict: Recommendations display component definitions
        """
        try:
            recommendation_components = []
            
            # Group recommendations by priority
            recommendations_by_priority = {}
            for rec in recommendations:
                priority = rec.get("priority", "medium")
                if priority not in recommendations_by_priority:
                    recommendations_by_priority[priority] = []
                recommendations_by_priority[priority].append(rec)
                
            # Create recommendation components
            priority_order = ["critical", "high", "medium", "low"]
            for priority in priority_order:
                if priority in recommendations_by_priority:
                    for rec in recommendations_by_priority[priority]:
                        recommendation_components.append(UIRecommendation(
                            recommendation_id=rec.get("setting", ""),
                            priority=priority,
                            category=rec.get("category", "general"),
                            title=rec.get("title", ""),
                            description=rec.get("description", ""),
                            action_text=rec.get("action", ""),
                            can_apply=True,
                            estimated_impact=self._get_recommendation_impact(priority)
                        ))
                        
            # Create recommendations component
            recommendations_component = UIComponent(
                component_id="security_recommendations_display",
                component_type=UIComponentType.RECOMMENDATION,
                title="Security Recommendations",
                description="Recommended security configuration improvements",
                css_classes=["security-recommendations", "recommendations-list"]
            )
            
            return {
                "component": recommendations_component,
                "recommendations": [rec.__dict__ for rec in recommendation_components],
                "summary": {
                    "total_count": len(recommendations),
                    "critical_count": len(recommendations_by_priority.get("critical", [])),
                    "high_count": len(recommendations_by_priority.get("high", [])),
                    "medium_count": len(recommendations_by_priority.get("medium", [])),
                    "low_count": len(recommendations_by_priority.get("low", []))
                },
                "actions": [
                    {"id": "apply_all_critical", "label": "Apply All Critical", "type": "primary"},
                    {"id": "apply_selected", "label": "Apply Selected", "type": "secondary"},
                    {"id": "dismiss_all", "label": "Dismiss All", "type": "tertiary"}
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to create recommendations display: {e}")
            return {"error": str(e)}

    def create_security_dashboard(self, security_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive security dashboard.
        
        Args:
            security_data: Complete security information
            
        Returns:
            Dict: Dashboard component definitions
        """
        try:
            dashboard_sections = []
            
            # Status section
            if "status" in security_data:
                status_display = self.create_security_status_display(security_data["status"])
                dashboard_sections.append({
                    "section_id": "status",
                    "title": "Security Status",
                    "component": status_display,
                    "order": 1
                })
                
            # Configuration section
            if "configuration" in security_data:
                form_display = self.create_security_configuration_form(security_data["configuration"])
                dashboard_sections.append({
                    "section_id": "configuration",
                    "title": "Security Configuration",
                    "component": form_display,
                    "order": 2
                })
                
            # Validation section
            if "validation" in security_data:
                validation_display = self.create_validation_display(security_data["validation"])
                dashboard_sections.append({
                    "section_id": "validation",
                    "title": "Configuration Validation",
                    "component": validation_display,
                    "order": 3
                })
                
            # Recommendations section
            if "recommendations" in security_data:
                recommendations_display = self.create_recommendations_display(security_data["recommendations"])
                dashboard_sections.append({
                    "section_id": "recommendations",
                    "title": "Security Recommendations",
                    "component": recommendations_display,
                    "order": 4
                })
                
            # Create dashboard component
            dashboard_component = UIComponent(
                component_id="security_dashboard",
                component_type=UIComponentType.DISPLAY,
                title="Security Dashboard",
                description="Comprehensive security configuration management",
                css_classes=["security-dashboard", "dashboard-grid"]
            )
            
            return {
                "component": dashboard_component,
                "sections": dashboard_sections,
                "navigation": self._create_dashboard_navigation(dashboard_sections),
                "actions": [
                    {"id": "export_config", "label": "Export Configuration", "type": "secondary"},
                    {"id": "import_config", "label": "Import Configuration", "type": "secondary"},
                    {"id": "reset_config", "label": "Reset to Defaults", "type": "tertiary"}
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to create security dashboard: {e}")
            return {"error": str(e)}

    def _get_form_validation_rules(self) -> Dict[str, Any]:
        """Get form validation rules"""
        return {
            "credential_timeout": {
                "min": 5,
                "max": 240,
                "message": "Credential timeout must be between 5 and 240 minutes"
            },
            "max_failed_attempts": {
                "min": 1,
                "max": 10,
                "message": "Max failed attempts must be between 1 and 10"
            },
            "lockout_duration": {
                "min": 1,
                "max": 60,
                "message": "Lockout duration must be between 1 and 60 minutes"
            }
        }

    def _get_form_help_sections(self) -> List[Dict[str, Any]]:
        """Get form help sections"""
        return [
            {
                "title": "Encryption Settings",
                "content": "Encryption protects your backup data from unauthorized access. It is strongly recommended to keep encryption enabled.",
                "fields": ["encryption_enabled"]
            },
            {
                "title": "Authentication Settings",
                "content": "These settings control how user authentication works, including timeouts and failed attempt handling.",
                "fields": ["credential_timeout", "max_failed_attempts", "lockout_duration"]
            },
            {
                "title": "Password Security",
                "content": "Password strength checking and confirmation requirements help ensure strong security practices.",
                "fields": ["password_strength_check", "require_password_confirmation"]
            },
            {
                "title": "Monitoring Settings",
                "content": "Audit logging helps track security events and troubleshoot issues. It is recommended for security monitoring.",
                "fields": ["audit_logging"]
            }
        ]

    def _get_security_level_icon(self, level: str) -> str:
        """Get icon for security level"""
        icons = {
            "high": "shield-check",
            "medium": "shield",
            "low": "shield-alert",
            "unknown": "shield-off"
        }
        return icons.get(level, "shield-off")

    def _get_recommendation_impact(self, priority: str) -> str:
        """Get estimated impact for recommendation priority"""
        impacts = {
            "critical": "High security impact",
            "high": "Significant security improvement",
            "medium": "Moderate security enhancement",
            "low": "Minor security improvement"
        }
        return impacts.get(priority, "Unknown impact")

    def _create_dashboard_navigation(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create dashboard navigation"""
        navigation = []
        for section in sorted(sections, key=lambda x: x["order"]):
            navigation.append({
                "id": section["section_id"],
                "label": section["title"],
                "icon": self._get_section_icon(section["section_id"]),
                "order": section["order"]
            })
        return navigation

    def _get_section_icon(self, section_id: str) -> str:
        """Get icon for dashboard section"""
        icons = {
            "status": "activity",
            "configuration": "settings",
            "validation": "check-circle",
            "recommendations": "lightbulb"
        }
        return icons.get(section_id, "circle")

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register UI event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def handle_ui_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle UI event"""
        try:
            if event_type in self._event_handlers:
                results = []
                for handler in self._event_handlers[event_type]:
                    try:
                        result = handler(event_data)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error in UI event handler: {e}")
                        results.append({"error": str(e)})
                return {"results": results}
            else:
                return {"error": f"No handlers registered for event type: {event_type}"}
        except Exception as e:
            logger.error(f"Failed to handle UI event {event_type}: {e}")
            return {"error": str(e)}