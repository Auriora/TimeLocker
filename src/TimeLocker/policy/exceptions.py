"""
Policy management exception classes.

This module defines the exception hierarchy for policy-related errors,
following the project's exception handling patterns.
"""


class PolicyError(Exception):
    """Base exception for all policy-related errors."""
    
    def __init__(self, message: str, policy_id: str = None, **context):
        """
        Initialize policy error with context.
        
        Args:
            message: Error message
            policy_id: Optional policy identifier
            **context: Additional context information
        """
        super().__init__(message)
        self.policy_id = policy_id
        self.context = context


class PolicyValidationError(PolicyError):
    """
    Raised when policy configuration is invalid.
    
    This exception indicates that a policy configuration does not meet
    validation requirements, such as missing required fields, invalid
    values, or inconsistent settings.
    """
    
    def __init__(self, message: str, policy_id: str = None, validation_errors: list = None, **context):
        """
        Initialize validation error with specific validation failures.
        
        Args:
            message: Error message
            policy_id: Optional policy identifier
            validation_errors: List of specific validation errors
            **context: Additional context information
        """
        super().__init__(message, policy_id, **context)
        self.validation_errors = validation_errors or []


class PolicyCompatibilityError(PolicyError):
    """
    Raised when policy is incompatible with target system.
    
    This exception indicates that a policy cannot be applied to a target
    due to incompatibility with the backup tool, repository type, or
    other system constraints.
    """
    
    def __init__(self, message: str, policy_id: str = None, target_id: str = None, 
                 incompatibility_reasons: list = None, **context):
        """
        Initialize compatibility error with incompatibility details.
        
        Args:
            message: Error message
            policy_id: Optional policy identifier
            target_id: Optional target identifier
            incompatibility_reasons: List of specific incompatibility reasons
            **context: Additional context information
        """
        super().__init__(message, policy_id, **context)
        self.target_id = target_id
        self.incompatibility_reasons = incompatibility_reasons or []


class PolicyEnforcementError(PolicyError):
    """
    Raised when policy enforcement fails.
    
    This exception indicates that an attempt to enforce a policy failed
    during execution, such as errors during snapshot pruning or backup
    operations.
    """
    
    def __init__(self, message: str, policy_id: str = None, target_id: str = None,
                 enforcement_type: str = None, partial_results: dict = None, **context):
        """
        Initialize enforcement error with execution details.
        
        Args:
            message: Error message
            policy_id: Optional policy identifier
            target_id: Optional target identifier
            enforcement_type: Type of enforcement that failed
            partial_results: Partial results if enforcement partially succeeded
            **context: Additional context information
        """
        super().__init__(message, policy_id, **context)
        self.target_id = target_id
        self.enforcement_type = enforcement_type
        self.partial_results = partial_results or {}


class ComplianceViolationError(PolicyError):
    """
    Raised when operation would violate compliance requirements.
    
    This exception indicates that an operation cannot proceed because it
    would violate compliance rules defined in the policy, such as deleting
    snapshots within a compliance retention period.
    """
    
    def __init__(self, message: str, policy_id: str = None, violations: list = None, **context):
        """
        Initialize compliance violation error with violation details.
        
        Args:
            message: Error message
            policy_id: Optional policy identifier
            violations: List of specific compliance violations
            **context: Additional context information
        """
        super().__init__(message, policy_id, **context)
        self.violations = violations or []


class PolicyNotFoundError(PolicyError):
    """
    Raised when a requested policy does not exist.
    
    This exception indicates that a policy lookup failed because the
    specified policy ID does not exist in the system.
    """
    
    def __init__(self, message: str, policy_id: str = None, **context):
        """
        Initialize not found error.
        
        Args:
            message: Error message
            policy_id: Policy identifier that was not found
            **context: Additional context information
        """
        super().__init__(message, policy_id, **context)


class PolicyAssignmentError(PolicyError):
    """
    Raised when policy assignment operation fails.
    
    This exception indicates that assigning a policy to a target failed,
    such as due to conflicts with existing assignments or invalid target
    references.
    """
    
    def __init__(self, message: str, policy_id: str = None, target_id: str = None,
                 assignment_conflicts: list = None, **context):
        """
        Initialize assignment error with conflict details.
        
        Args:
            message: Error message
            policy_id: Optional policy identifier
            target_id: Optional target identifier
            assignment_conflicts: List of conflicting assignments
            **context: Additional context information
        """
        super().__init__(message, policy_id, **context)
        self.target_id = target_id
        self.assignment_conflicts = assignment_conflicts or []


class PolicyStorageError(PolicyError):
    """
    Raised when policy storage operations fail.
    
    This exception indicates that reading from or writing to policy storage
    failed, such as file system errors or database connection issues.
    """
    
    def __init__(self, message: str, policy_id: str = None, operation: str = None, **context):
        """
        Initialize storage error with operation details.
        
        Args:
            message: Error message
            policy_id: Optional policy identifier
            operation: Storage operation that failed (e.g., 'save', 'load', 'delete')
            **context: Additional context information
        """
        super().__init__(message, policy_id, **context)
        self.operation = operation


class PolicySerializationError(PolicyError):
    """
    Raised when policy serialization or deserialization fails.
    
    This exception indicates that converting a policy to or from its
    storage format failed, such as due to invalid data or schema changes.
    """
    
    def __init__(self, message: str, policy_id: str = None, data_format: str = None, **context):
        """
        Initialize serialization error with format details.
        
        Args:
            message: Error message
            policy_id: Optional policy identifier
            data_format: Data format being used (e.g., 'json', 'yaml')
            **context: Additional context information
        """
        super().__init__(message, policy_id, **context)
        self.data_format = data_format
