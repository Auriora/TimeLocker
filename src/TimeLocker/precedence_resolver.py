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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .selection_models import (
    ConflictResolution,
    PatternRule,
    PatternSyntax,
    PrecedenceConfig,
    PrecedenceStrategy,
    RuleMatch,
    SelectionDecision,
    ValidationError,
    ValidationResult,
    ValidationWarning
)

logger = logging.getLogger(__name__)


class PrecedenceConflictError(Exception):
    """Exception raised when precedence conflicts cannot be resolved"""
    
    def __init__(self, path: Path, conflicts: List[RuleMatch], message: str):
        self.path = path
        self.conflicts = conflicts
        super().__init__(message)


@dataclass
class PrecedenceExplanation:
    """
    Detailed explanation of precedence resolution.
    
    Attributes:
        path: Path that was evaluated
        decision: Final decision (include or exclude)
        strategy_used: Precedence strategy that was applied
        evaluation_steps: Step-by-step evaluation process
        conflicting_rules: Rules that conflicted
        winning_rule: Rule that won the conflict
        confidence: Confidence in the decision (0.0-1.0)
        warnings: Any warnings generated
    """
    path: Path
    decision: bool
    strategy_used: PrecedenceStrategy
    evaluation_steps: List[str] = field(default_factory=list)
    conflicting_rules: List[RuleMatch] = field(default_factory=list)
    winning_rule: Optional[RuleMatch] = None
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConflictReport:
    """
    Report of a precedence conflict.
    
    Attributes:
        path: Path with conflict
        include_rules: Rules that would include the path
        exclude_rules: Rules that would exclude the path
        resolution: How the conflict was resolved
        suggested_fix: Suggested fix for the conflict
        severity: Severity of the conflict
    """
    path: Path
    include_rules: List[RuleMatch]
    exclude_rules: List[RuleMatch]
    resolution: str
    suggested_fix: Optional[str] = None
    severity: str = "medium"


class PrecedenceResolver:
    """
    Configurable precedence resolver for hierarchical file selections.
    
    Handles complex scenarios where include and exclude rules conflict,
    supporting multiple resolution strategies and layered evaluation.
    """
    
    def __init__(self, config: Optional[PrecedenceConfig] = None):
        """
        Initialize the precedence resolver.
        
        Args:
            config: Precedence configuration (uses defaults if None)
        """
        self.config = config or PrecedenceConfig()
        self._resolution_cache: Dict[str, SelectionDecision] = {}
        self._conflict_reports: List[ConflictReport] = []
        
        # Statistics
        self._stats = {
            'total_resolutions': 0,
            'conflicts_detected': 0,
            'cache_hits': 0,
            'strategy_usage': {strategy: 0 for strategy in PrecedenceStrategy}
        }
    
    def resolve_selection_conflicts(
        self,
        path: Path,
        matches: List[RuleMatch]
    ) -> SelectionDecision:
        """
        Resolve precedence conflicts for a path with multiple matching rules.
        
        Args:
            path: Path to evaluate
            matches: List of matching rules (both include and exclude)
            
        Returns:
            SelectionDecision with final decision and explanation
            
        Raises:
            PrecedenceConflictError: If conflict cannot be resolved and
                                    conflict_resolution is FAIL_ON_CONFLICT
        """
        self._stats['total_resolutions'] += 1
        
        # Check cache
        cache_key = self._generate_cache_key(path, matches)
        if cache_key in self._resolution_cache:
            self._stats['cache_hits'] += 1
            return self._resolution_cache[cache_key]
        
        # Separate include and exclude rules
        include_rules = [m for m in matches if m.match_type == "include"]
        exclude_rules = [m for m in matches if m.match_type == "exclude"]
        
        # No conflict if only one type of rule
        if not include_rules:
            decision = self._create_decision(False, exclude_rules, path, "No include rules matched")
            self._cache_decision(cache_key, decision)
            return decision
        
        if not exclude_rules:
            decision = self._create_decision(True, include_rules, path, "No exclude rules matched")
            self._cache_decision(cache_key, decision)
            return decision
        
        # Conflict detected
        self._stats['conflicts_detected'] += 1
        logger.debug(f"Precedence conflict for {path}: {len(include_rules)} include, {len(exclude_rules)} exclude")
        
        # Get applicable strategy
        strategy = self._get_applicable_strategy(path)
        self._stats['strategy_usage'][strategy] += 1
        
        # Resolve based on strategy
        try:
            decision = self._resolve_by_strategy(path, include_rules, exclude_rules, strategy)
            self._cache_decision(cache_key, decision)
            
            # Create conflict report if configured
            if self.config.conflict_resolution == ConflictResolution.WARN_ON_CONFLICT:
                self._create_conflict_report(path, include_rules, exclude_rules, decision)
            
            return decision
            
        except Exception as e:
            if self.config.conflict_resolution == ConflictResolution.FAIL_ON_CONFLICT:
                raise PrecedenceConflictError(
                    path,
                    matches,
                    f"Cannot resolve precedence conflict for {path}: {e}"
                )
            else:
                # Fallback to default strategy
                logger.warning(f"Error resolving conflict for {path}, using fallback: {e}")
                decision = self._resolve_by_strategy(
                    path,
                    include_rules,
                    exclude_rules,
                    PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE
                )
                decision.warnings.append(f"Fallback resolution used due to error: {e}")
                self._cache_decision(cache_key, decision)
                return decision
    
    def _get_applicable_strategy(self, path: Path) -> PrecedenceStrategy:
        """
        Get the applicable precedence strategy for a path.
        
        Args:
            path: Path to check
            
        Returns:
            Applicable PrecedenceStrategy
        """
        # Check for path-specific rules
        path_str = str(path)
        for pattern, strategy in self.config.path_specific_rules.items():
            if Path(path_str).match(pattern):
                logger.debug(f"Using path-specific strategy {strategy} for {path}")
                return strategy
        
        # Use default strategy
        return self.config.default_strategy
    
    def _resolve_by_strategy(
        self,
        path: Path,
        include_rules: List[RuleMatch],
        exclude_rules: List[RuleMatch],
        strategy: PrecedenceStrategy
    ) -> SelectionDecision:
        """
        Resolve conflict using specified strategy.
        
        Args:
            path: Path being evaluated
            include_rules: Include rules that matched
            exclude_rules: Exclude rules that matched
            strategy: Strategy to use
            
        Returns:
            SelectionDecision
        """
        if strategy == PrecedenceStrategy.INCLUDE_OVERRIDES_EXCLUDE:
            return self._resolve_include_first(path, include_rules, exclude_rules)
        
        elif strategy == PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE:
            return self._resolve_exclude_first(path, include_rules, exclude_rules)
        
        elif strategy == PrecedenceStrategy.MOST_SPECIFIC_WINS:
            return self._resolve_by_specificity(path, include_rules, exclude_rules)
        
        elif strategy == PrecedenceStrategy.EXPLICIT_PRIORITY:
            return self._resolve_by_priority(path, include_rules, exclude_rules)
        
        elif strategy == PrecedenceStrategy.LAYERED_EVALUATION:
            return self._resolve_layered(path, include_rules, exclude_rules)
        
        else:
            raise ValueError(f"Unsupported precedence strategy: {strategy}")
    
    def _resolve_include_first(
        self,
        path: Path,
        include_rules: List[RuleMatch],
        exclude_rules: List[RuleMatch]
    ) -> SelectionDecision:
        """
        Resolve with include rules taking precedence.
        
        Args:
            path: Path being evaluated
            include_rules: Include rules
            exclude_rules: Exclude rules
            
        Returns:
            SelectionDecision
        """
        explanation = (
            f"Include rules take precedence: {len(include_rules)} include rule(s) matched, "
            f"overriding {len(exclude_rules)} exclude rule(s)"
        )
        
        return SelectionDecision(
            include=True,
            confidence=0.9,
            applied_rules=include_rules + exclude_rules,
            precedence_explanation=explanation
        )
    
    def _resolve_exclude_first(
        self,
        path: Path,
        include_rules: List[RuleMatch],
        exclude_rules: List[RuleMatch]
    ) -> SelectionDecision:
        """
        Resolve with exclude rules taking precedence.
        
        Args:
            path: Path being evaluated
            include_rules: Include rules
            exclude_rules: Exclude rules
            
        Returns:
            SelectionDecision
        """
        explanation = (
            f"Exclude rules take precedence: {len(exclude_rules)} exclude rule(s) matched, "
            f"overriding {len(include_rules)} include rule(s)"
        )
        
        return SelectionDecision(
            include=False,
            confidence=0.9,
            applied_rules=exclude_rules + include_rules,
            precedence_explanation=explanation
        )

    def _resolve_by_specificity(
        self,
        path: Path,
        include_rules: List[RuleMatch],
        exclude_rules: List[RuleMatch]
    ) -> SelectionDecision:
        """
        Resolve by specificity - more specific rules win.
        
        Args:
            path: Path being evaluated
            include_rules: Include rules
            exclude_rules: Exclude rules
            
        Returns:
            SelectionDecision
        """
        # Calculate specificity scores for all rules
        all_rules = include_rules + exclude_rules
        scored_rules = [
            (rule, self._calculate_rule_specificity(rule, path))
            for rule in all_rules
        ]
        
        # Sort by specificity (highest first)
        scored_rules.sort(key=lambda x: x[1], reverse=True)
        
        # Most specific rule wins
        winning_rule, winning_score = scored_rules[0]
        
        # Check if there are ties
        ties = [r for r, s in scored_rules if s == winning_score]
        
        if len(ties) > 1:
            # Multiple rules with same specificity - use pattern type priority
            winning_rule = self._break_tie_by_pattern_type(ties)
            confidence = 0.7
            warning = f"Multiple rules with same specificity ({winning_score:.2f}), used pattern type priority"
        else:
            confidence = 0.95
            warning = None
        
        explanation = (
            f"Most specific rule wins: {winning_rule.rule.pattern} "
            f"(specificity: {winning_score:.2f}, type: {winning_rule.match_type})"
        )
        
        decision = SelectionDecision(
            include=(winning_rule.match_type == "include"),
            confidence=confidence,
            applied_rules=[winning_rule],
            precedence_explanation=explanation
        )
        
        if warning:
            decision.warnings.append(warning)
        
        return decision
    
    def _resolve_by_priority(
        self,
        path: Path,
        include_rules: List[RuleMatch],
        exclude_rules: List[RuleMatch]
    ) -> SelectionDecision:
        """
        Resolve by explicit priority values.
        
        Args:
            path: Path being evaluated
            include_rules: Include rules
            exclude_rules: Exclude rules
            
        Returns:
            SelectionDecision
        """
        # Combine all rules and sort by priority
        all_rules = include_rules + exclude_rules
        sorted_rules = sorted(all_rules, key=lambda r: r.rule.priority, reverse=True)
        
        # Highest priority rule wins
        winning_rule = sorted_rules[0]
        
        # Check for ties
        max_priority = winning_rule.rule.priority
        ties = [r for r in sorted_rules if r.rule.priority == max_priority]
        
        if len(ties) > 1:
            # Multiple rules with same priority - use specificity as tiebreaker
            winning_rule = max(ties, key=lambda r: self._calculate_rule_specificity(r, path))
            confidence = 0.8
            warning = f"Multiple rules with priority {max_priority}, used specificity as tiebreaker"
        else:
            confidence = 0.95
            warning = None
        
        explanation = (
            f"Highest priority rule wins: {winning_rule.rule.pattern} "
            f"(priority: {winning_rule.rule.priority}, type: {winning_rule.match_type})"
        )
        
        decision = SelectionDecision(
            include=(winning_rule.match_type == "include"),
            confidence=confidence,
            applied_rules=[winning_rule],
            precedence_explanation=explanation
        )
        
        if warning:
            decision.warnings.append(warning)
        
        return decision
    
    def _resolve_layered(
        self,
        path: Path,
        include_rules: List[RuleMatch],
        exclude_rules: List[RuleMatch]
    ) -> SelectionDecision:
        """
        Resolve using layered evaluation.
        
        Evaluates rules in layers from least to most specific, allowing
        more specific rules to override less specific ones.
        
        Args:
            path: Path being evaluated
            include_rules: Include rules
            exclude_rules: Exclude rules
            
        Returns:
            SelectionDecision
        """
        # Combine and sort all rules by specificity (least to most specific)
        all_rules = include_rules + exclude_rules
        sorted_rules = sorted(
            all_rules,
            key=lambda r: self._calculate_rule_specificity(r, path)
        )
        
        # Evaluate in layers
        current_decision = False  # Default to exclude
        applied_rules = []
        evaluation_steps = []
        
        for rule in sorted_rules:
            specificity = self._calculate_rule_specificity(rule, path)
            
            if rule.match_type == "include":
                current_decision = True
                evaluation_steps.append(
                    f"Layer {len(evaluation_steps) + 1}: Include rule '{rule.rule.pattern}' "
                    f"(specificity: {specificity:.2f}) -> INCLUDE"
                )
            else:
                current_decision = False
                evaluation_steps.append(
                    f"Layer {len(evaluation_steps) + 1}: Exclude rule '{rule.rule.pattern}' "
                    f"(specificity: {specificity:.2f}) -> EXCLUDE"
                )
            
            applied_rules.append(rule)
        
        explanation = (
            f"Layered evaluation with {len(sorted_rules)} rule(s): "
            f"Final decision after {len(evaluation_steps)} layer(s) is "
            f"{'INCLUDE' if current_decision else 'EXCLUDE'}"
        )
        
        decision = SelectionDecision(
            include=current_decision,
            confidence=0.9,
            applied_rules=applied_rules,
            precedence_explanation=explanation
        )
        
        # Add evaluation steps as metadata
        decision.warnings.extend(evaluation_steps)
        
        return decision
    
    def _calculate_rule_specificity(self, rule: RuleMatch, path: Path) -> float:
        """
        Calculate specificity score for a rule match.
        
        Higher scores indicate more specific rules.
        
        Args:
            rule: Rule match to score
            path: Path being evaluated
            
        Returns:
            Specificity score (0.0-1.0)
        """
        base_score = 0.0
        
        # Pattern syntax specificity
        syntax_scores = {
            PatternSyntax.LITERAL: 1.0,
            PatternSyntax.GLOB: 0.6,
            PatternSyntax.REGEX: 0.4
        }
        base_score += syntax_scores.get(rule.rule.syntax, 0.5) * 0.3
        
        # Pattern length (longer = more specific)
        pattern_length_score = min(len(rule.rule.pattern) / 100.0, 1.0)
        base_score += pattern_length_score * 0.2
        
        # Wildcard count (fewer = more specific) for GLOB patterns
        if rule.rule.syntax == PatternSyntax.GLOB:
            wildcard_count = rule.rule.pattern.count('*') + rule.rule.pattern.count('?')
            wildcard_score = 1.0 / (1.0 + wildcard_count)
            base_score += wildcard_score * 0.3
        else:
            base_score += 0.3
        
        # Path depth (deeper = more specific)
        path_depth = len(path.parts)
        pattern_depth = rule.rule.pattern.count('/') + rule.rule.pattern.count('\\')
        depth_score = min(pattern_depth / max(path_depth, 1), 1.0)
        base_score += depth_score * 0.2
        
        # Apply configured weights
        base_score *= self.config.specificity_weight
        
        # Add explicit priority weight
        priority_score = min(rule.rule.priority / 1000.0, 1.0)
        base_score += priority_score * self.config.explicit_override_weight * 0.2
        
        # Add pattern type priority from config
        pattern_type_priority = self.config.pattern_type_priority.get(rule.rule.syntax, 100)
        type_score = min(pattern_type_priority / 1000.0, 1.0)
        base_score += type_score * 0.1
        
        return min(base_score, 1.0)
    
    def _break_tie_by_pattern_type(self, tied_rules: List[RuleMatch]) -> RuleMatch:
        """
        Break tie between rules using pattern type priority.
        
        Args:
            tied_rules: Rules with same specificity
            
        Returns:
            Winning rule
        """
        # Sort by pattern type priority
        sorted_rules = sorted(
            tied_rules,
            key=lambda r: self.config.pattern_type_priority.get(r.rule.syntax, 100),
            reverse=True
        )
        
        return sorted_rules[0]
    
    def _create_decision(
        self,
        include: bool,
        rules: List[RuleMatch],
        path: Path,
        explanation: str
    ) -> SelectionDecision:
        """
        Create a selection decision.
        
        Args:
            include: Whether to include the path
            rules: Rules that were applied
            path: Path being evaluated
            explanation: Explanation of the decision
            
        Returns:
            SelectionDecision
        """
        return SelectionDecision(
            include=include,
            confidence=1.0,
            applied_rules=rules,
            precedence_explanation=explanation
        )
    
    def _generate_cache_key(self, path: Path, matches: List[RuleMatch]) -> str:
        """
        Generate cache key for a path and its matches.
        
        Args:
            path: Path being evaluated
            matches: Matching rules
            
        Returns:
            Cache key string
        """
        # Create key from path and sorted rule patterns
        rule_keys = sorted([
            f"{m.match_type}:{m.rule.pattern}:{m.rule.syntax.value}"
            for m in matches
        ])
        
        return f"{path}:{'|'.join(rule_keys)}"
    
    def _cache_decision(self, cache_key: str, decision: SelectionDecision) -> None:
        """
        Cache a selection decision.
        
        Args:
            cache_key: Cache key
            decision: Decision to cache
        """
        # Simple cache without size limit for now
        self._resolution_cache[cache_key] = decision
    
    def _create_conflict_report(
        self,
        path: Path,
        include_rules: List[RuleMatch],
        exclude_rules: List[RuleMatch],
        decision: SelectionDecision
    ) -> None:
        """
        Create a conflict report for warning purposes.
        
        Args:
            path: Path with conflict
            include_rules: Include rules
            exclude_rules: Exclude rules
            decision: Final decision
        """
        # Determine severity based on number of conflicting rules
        total_conflicts = len(include_rules) + len(exclude_rules)
        if total_conflicts > 5:
            severity = "high"
        elif total_conflicts > 2:
            severity = "medium"
        else:
            severity = "low"
        
        # Generate suggested fix
        if decision.include:
            suggested_fix = (
                f"Consider removing or making more specific the {len(exclude_rules)} "
                f"exclude rule(s) that conflict with the include decision"
            )
        else:
            suggested_fix = (
                f"Consider removing or making more specific the {len(include_rules)} "
                f"include rule(s) that conflict with the exclude decision"
            )
        
        report = ConflictReport(
            path=path,
            include_rules=include_rules,
            exclude_rules=exclude_rules,
            resolution=decision.precedence_explanation,
            suggested_fix=suggested_fix,
            severity=severity
        )
        
        self._conflict_reports.append(report)
        
        logger.warning(
            f"Precedence conflict for {path}: {len(include_rules)} include, "
            f"{len(exclude_rules)} exclude rules. Resolution: {decision.precedence_explanation}"
        )
    
    def configure_precedence_rules(self, config: PrecedenceConfig) -> bool:
        """
        Update precedence configuration.
        
        Args:
            config: New precedence configuration
            
        Returns:
            True if configuration was updated successfully
        """
        # Validate configuration
        validation = self.validate_precedence_configuration(config)
        
        if not validation.is_valid:
            logger.error(f"Invalid precedence configuration: {validation.errors}")
            return False
        
        # Clear cache when configuration changes
        self._resolution_cache.clear()
        self._conflict_reports.clear()
        
        self.config = config
        logger.info("Precedence configuration updated")
        
        return True
    
    def get_precedence_explanation(
        self,
        path: Path,
        include_rules: List[RuleMatch],
        exclude_rules: List[RuleMatch]
    ) -> PrecedenceExplanation:
        """
        Get detailed explanation of precedence resolution for a path.
        
        Args:
            path: Path to explain
            include_rules: Include rules that match
            exclude_rules: Exclude rules that match
            
        Returns:
            PrecedenceExplanation with detailed information
        """
        # Get applicable strategy
        strategy = self._get_applicable_strategy(path)
        
        # Resolve the conflict
        all_matches = include_rules + exclude_rules
        decision = self.resolve_selection_conflicts(path, all_matches)
        
        # Build evaluation steps
        evaluation_steps = []
        evaluation_steps.append(f"Path: {path}")
        evaluation_steps.append(f"Strategy: {strategy.value}")
        evaluation_steps.append(f"Include rules matched: {len(include_rules)}")
        evaluation_steps.append(f"Exclude rules matched: {len(exclude_rules)}")
        
        # Add rule details
        for rule in include_rules:
            specificity = self._calculate_rule_specificity(rule, path)
            evaluation_steps.append(
                f"  Include: {rule.rule.pattern} "
                f"(priority: {rule.rule.priority}, specificity: {specificity:.2f})"
            )
        
        for rule in exclude_rules:
            specificity = self._calculate_rule_specificity(rule, path)
            evaluation_steps.append(
                f"  Exclude: {rule.rule.pattern} "
                f"(priority: {rule.rule.priority}, specificity: {specificity:.2f})"
            )
        
        evaluation_steps.append(f"Decision: {'INCLUDE' if decision.include else 'EXCLUDE'}")
        evaluation_steps.append(f"Explanation: {decision.precedence_explanation}")
        
        # Determine winning rule
        winning_rule = decision.applied_rules[0] if decision.applied_rules else None
        
        # Collect warnings
        warnings = decision.warnings.copy()
        if len(include_rules) > 0 and len(exclude_rules) > 0:
            warnings.append(
                f"Conflict detected: {len(include_rules)} include and "
                f"{len(exclude_rules)} exclude rules matched"
            )
        
        return PrecedenceExplanation(
            path=path,
            decision=decision.include,
            strategy_used=strategy,
            evaluation_steps=evaluation_steps,
            conflicting_rules=all_matches,
            winning_rule=winning_rule,
            confidence=decision.confidence,
            warnings=warnings
        )
    
    def validate_precedence_configuration(self, config: PrecedenceConfig) -> ValidationResult:
        """
        Validate a precedence configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        suggestions = []
        
        # Validate weights
        if not 0.0 <= config.specificity_weight <= 1.0:
            errors.append(ValidationError(
                error_type="invalid_weight",
                message="specificity_weight must be between 0.0 and 1.0",
                context={"value": config.specificity_weight},
                suggested_fix="Set specificity_weight to a value between 0.0 and 1.0"
            ))
        
        if not 0.0 <= config.explicit_override_weight <= 1.0:
            errors.append(ValidationError(
                error_type="invalid_weight",
                message="explicit_override_weight must be between 0.0 and 1.0",
                context={"value": config.explicit_override_weight},
                suggested_fix="Set explicit_override_weight to a value between 0.0 and 1.0"
            ))
        
        # Validate pattern type priorities
        if not config.pattern_type_priority:
            warnings.append(ValidationWarning(
                warning_type="missing_priorities",
                message="No pattern type priorities configured, using defaults",
                severity="low"
            ))
        
        # Check for path-specific rules
        if config.path_specific_rules:
            for pattern, strategy in config.path_specific_rules.items():
                if not isinstance(strategy, PrecedenceStrategy):
                    errors.append(ValidationError(
                        error_type="invalid_strategy",
                        message=f"Invalid strategy for path pattern '{pattern}'",
                        context={"pattern": pattern, "strategy": strategy},
                        suggested_fix="Use a valid PrecedenceStrategy value"
                    ))
        
        # Provide suggestions
        if config.default_strategy == PrecedenceStrategy.LAYERED_EVALUATION:
            suggestions.append(
                "Layered evaluation provides the most flexible conflict resolution "
                "but may be slower for large file sets"
            )
        
        if config.conflict_resolution == ConflictResolution.SILENT_RESOLUTION:
            warnings.append(ValidationWarning(
                warning_type="silent_conflicts",
                message="Conflicts will be resolved silently without warnings",
                severity="medium"
            ))
            suggestions.append(
                "Consider using WARN_ON_CONFLICT to be notified of precedence conflicts"
            )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def get_conflict_reports(self) -> List[ConflictReport]:
        """
        Get all conflict reports generated during resolution.
        
        Returns:
            List of ConflictReport objects
        """
        return self._conflict_reports.copy()
    
    def clear_conflict_reports(self) -> None:
        """Clear all conflict reports."""
        self._conflict_reports.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get precedence resolver statistics.
        
        Returns:
            Dictionary with statistics
        """
        cache_hit_ratio = (
            self._stats['cache_hits'] / self._stats['total_resolutions']
            if self._stats['total_resolutions'] > 0 else 0.0
        )
        
        return {
            'total_resolutions': self._stats['total_resolutions'],
            'conflicts_detected': self._stats['conflicts_detected'],
            'conflict_ratio': (
                self._stats['conflicts_detected'] / self._stats['total_resolutions']
                if self._stats['total_resolutions'] > 0 else 0.0
            ),
            'cache_hits': self._stats['cache_hits'],
            'cache_hit_ratio': cache_hit_ratio,
            'cache_size': len(self._resolution_cache),
            'conflict_reports': len(self._conflict_reports),
            'strategy_usage': self._stats['strategy_usage'].copy()
        }
    
    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._resolution_cache.clear()
        logger.info("Precedence resolution cache cleared")
