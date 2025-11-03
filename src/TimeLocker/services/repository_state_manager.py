"""
Repository State Manager for TimeLocker

This module provides controlled repository state transitions with validation,
audit logging, and correlation tracking for repository lifecycle management.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from ..interfaces.repository_management_models import (
    Repository, RepositoryStatus, RepositoryStateTransition,
    RepositoryStateError
)

logger = logging.getLogger(__name__)


class StateTransitionRule:
    """Defines rules for repository state transitions"""
    
    def __init__(self, from_state: RepositoryStatus, to_state: RepositoryStatus,
                 validator: Optional[Callable[[Repository, Dict[str, Any]], bool]] = None,
                 description: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.validator = validator
        self.description = description
    
    def is_valid_transition(self, repository: Repository, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if the transition is valid for the given repository.
        
        Args:
            repository: Repository to check
            context: Optional context for validation
            
        Returns:
            bool: True if transition is valid
        """
        if repository.status != self.from_state:
            return False
        
        if self.validator:
            return self.validator(repository, context or {})
        
        return True


class RepositoryStateManager:
    """
    Manages repository state transitions with validation and audit logging.
    
    Provides controlled state transitions, audit logging with correlation IDs,
    and repository status tracking for operational reliability.
    """
    
    def __init__(self, audit_logger: Optional[logging.Logger] = None):
        """
        Initialize Repository State Manager.
        
        Args:
            audit_logger: Optional logger for audit events
        """
        self._audit_logger = audit_logger or logger
        self._transition_rules: List[StateTransitionRule] = []
        self._state_history: Dict[str, List[RepositoryStateTransition]] = {}
        
        # Initialize default transition rules
        self._setup_default_transition_rules()
        
        logger.debug("RepositoryStateManager initialized")
    
    def _setup_default_transition_rules(self) -> None:
        """Setup default state transition rules"""
        
        # INACTIVE -> VALIDATING (when starting validation)
        self._transition_rules.append(StateTransitionRule(
            from_state=RepositoryStatus.INACTIVE,
            to_state=RepositoryStatus.VALIDATING,
            description="Start validation of inactive repository"
        ))
        
        # ACTIVE -> VALIDATING (when re-validating active repository)
        self._transition_rules.append(StateTransitionRule(
            from_state=RepositoryStatus.ACTIVE,
            to_state=RepositoryStatus.VALIDATING,
            description="Re-validate active repository"
        ))
        
        # ERROR -> VALIDATING (when attempting recovery)
        self._transition_rules.append(StateTransitionRule(
            from_state=RepositoryStatus.ERROR,
            to_state=RepositoryStatus.VALIDATING,
            description="Attempt recovery from error state"
        ))
        
        # VALIDATING -> ACTIVE (when validation succeeds)
        self._transition_rules.append(StateTransitionRule(
            from_state=RepositoryStatus.VALIDATING,
            to_state=RepositoryStatus.ACTIVE,
            validator=self._validate_successful_validation,
            description="Validation completed successfully"
        ))
        
        # VALIDATING -> ERROR (when validation fails)
        self._transition_rules.append(StateTransitionRule(
            from_state=RepositoryStatus.VALIDATING,
            to_state=RepositoryStatus.ERROR,
            validator=self._validate_failed_validation,
            description="Validation failed"
        ))
        
        # Any state -> INACTIVE (for deactivation/deletion)
        for from_state in RepositoryStatus:
            if from_state != RepositoryStatus.INACTIVE:
                self._transition_rules.append(StateTransitionRule(
                    from_state=from_state,
                    to_state=RepositoryStatus.INACTIVE,
                    description=f"Deactivate repository from {from_state.value} state"
                ))
    
    def _validate_successful_validation(self, repository: Repository, context: Dict[str, Any]) -> bool:
        """Validate that repository validation was successful"""
        return (repository.validation_result is not None and 
                repository.validation_result.success)
    
    def _validate_failed_validation(self, repository: Repository, context: Dict[str, Any]) -> bool:
        """Validate that repository validation failed"""
        return (repository.validation_result is not None and 
                not repository.validation_result.success)
    
    async def transition_state(self, repository: Repository, new_state: RepositoryStatus,
                             context: Optional[Dict[str, Any]] = None,
                             user_id: Optional[str] = None) -> bool:
        """
        Safely transition repository state with validation and logging.
        
        Args:
            repository: Repository to transition
            new_state: Target state
            context: Optional context information
            user_id: Optional user identifier for audit
            
        Returns:
            bool: True if transition was successful
            
        Raises:
            RepositoryStateError: If transition is invalid
        """
        current_state = repository.status
        correlation_id = str(uuid.uuid4())
        
        # Check if transition is valid
        if not self._is_valid_transition(repository, new_state, context):
            raise RepositoryStateError(
                f"Invalid state transition: {current_state.value} -> {new_state.value} "
                f"for repository {repository.name}"
            )
        
        try:
            # Create state transition record
            transition = RepositoryStateTransition(
                repository_name=repository.name,
                from_state=current_state,
                to_state=new_state,
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id,
                context=context,
                user_id=user_id
            )
            
            # Log state transition
            await self._log_state_transition(transition)
            
            # Perform the transition
            repository.update_status(new_state)
            
            # Store transition in history
            if repository.name not in self._state_history:
                self._state_history[repository.name] = []
            self._state_history[repository.name].append(transition)
            
            # Limit history size (keep last 100 transitions per repository)
            if len(self._state_history[repository.name]) > 100:
                self._state_history[repository.name] = self._state_history[repository.name][-100:]
            
            logger.info(f"Repository {repository.name} transitioned from {current_state.value} to {new_state.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to transition repository {repository.name} state: {e}")
            raise RepositoryStateError(f"State transition failed: {e}")
    
    def _is_valid_transition(self, repository: Repository, new_state: RepositoryStatus,
                           context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a state transition is valid.
        
        Args:
            repository: Repository to check
            new_state: Target state
            context: Optional context for validation
            
        Returns:
            bool: True if transition is valid
        """
        current_state = repository.status
        
        # Same state is always valid (no-op)
        if current_state == new_state:
            return True
        
        # Check transition rules
        for rule in self._transition_rules:
            if rule.from_state == current_state and rule.to_state == new_state:
                return rule.is_valid_transition(repository, context)
        
        return False
    
    async def _log_state_transition(self, transition: RepositoryStateTransition) -> None:
        """
        Log state transition for audit purposes.
        
        Args:
            transition: State transition to log
        """
        try:
            audit_data = transition.to_dict()
            
            self._audit_logger.info(
                f"Repository state transition: {transition.repository_name} "
                f"{transition.from_state.value} -> {transition.to_state.value}",
                extra={
                    'event_type': 'repository_state_transition',
                    'correlation_id': transition.correlation_id,
                    'repository_name': transition.repository_name,
                    'from_state': transition.from_state.value,
                    'to_state': transition.to_state.value,
                    'timestamp': transition.timestamp.isoformat(),
                    'context': transition.context,
                    'user_id': transition.user_id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log state transition: {e}")
    
    def get_state_history(self, repository_name: str, limit: Optional[int] = None) -> List[RepositoryStateTransition]:
        """
        Get state transition history for a repository.
        
        Args:
            repository_name: Repository name
            limit: Optional limit on number of transitions to return
            
        Returns:
            List[RepositoryStateTransition]: State transition history
        """
        history = self._state_history.get(repository_name, [])
        
        if limit:
            return history[-limit:]
        
        return history.copy()
    
    def get_current_states(self) -> Dict[str, RepositoryStatus]:
        """
        Get current states of all repositories with history.
        
        Returns:
            Dict[str, RepositoryStatus]: Mapping of repository names to current states
        """
        current_states = {}
        
        for repo_name, history in self._state_history.items():
            if history:
                current_states[repo_name] = history[-1].to_state
        
        return current_states
    
    def add_transition_rule(self, rule: StateTransitionRule) -> None:
        """
        Add a custom state transition rule.
        
        Args:
            rule: State transition rule to add
        """
        self._transition_rules.append(rule)
        logger.debug(f"Added transition rule: {rule.from_state.value} -> {rule.to_state.value}")
    
    def remove_transition_rule(self, from_state: RepositoryStatus, to_state: RepositoryStatus) -> bool:
        """
        Remove a state transition rule.
        
        Args:
            from_state: Source state
            to_state: Target state
            
        Returns:
            bool: True if rule was removed
        """
        for i, rule in enumerate(self._transition_rules):
            if rule.from_state == from_state and rule.to_state == to_state:
                del self._transition_rules[i]
                logger.debug(f"Removed transition rule: {from_state.value} -> {to_state.value}")
                return True
        
        return False
    
    def get_valid_transitions(self, repository: Repository) -> List[RepositoryStatus]:
        """
        Get list of valid state transitions for a repository.
        
        Args:
            repository: Repository to check
            
        Returns:
            List[RepositoryStatus]: List of valid target states
        """
        valid_states = []
        current_state = repository.status
        
        for rule in self._transition_rules:
            if rule.from_state == current_state:
                if rule.is_valid_transition(repository):
                    valid_states.append(rule.to_state)
        
        return valid_states
    
    def clear_history(self, repository_name: Optional[str] = None) -> None:
        """
        Clear state transition history.
        
        Args:
            repository_name: Optional repository name to clear specific history,
                           or None to clear all history
        """
        if repository_name:
            if repository_name in self._state_history:
                del self._state_history[repository_name]
                logger.debug(f"Cleared state history for repository: {repository_name}")
        else:
            self._state_history.clear()
            logger.debug("Cleared all state history")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about repository state transitions.
        
        Returns:
            Dict[str, Any]: Statistics about state transitions
        """
        total_transitions = sum(len(history) for history in self._state_history.values())
        repositories_with_history = len(self._state_history)
        
        # Count transitions by type
        transition_counts = {}
        for history in self._state_history.values():
            for transition in history:
                key = f"{transition.from_state.value} -> {transition.to_state.value}"
                transition_counts[key] = transition_counts.get(key, 0) + 1
        
        # Get current state distribution
        current_states = self.get_current_states()
        state_distribution = {}
        for state in current_states.values():
            state_distribution[state.value] = state_distribution.get(state.value, 0) + 1
        
        return {
            'total_transitions': total_transitions,
            'repositories_with_history': repositories_with_history,
            'transition_counts': transition_counts,
            'current_state_distribution': state_distribution,
            'transition_rules_count': len(self._transition_rules)
        }