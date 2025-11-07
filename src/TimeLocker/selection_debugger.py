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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pattern_engine import CompiledPatternSet, PatternEngine
from .precedence_resolver import PrecedenceExplanation, PrecedenceResolver
from .selection_models import (
    PatternRule,
    RuleMatch,
    SelectionConfig,
    SelectionDecision
)

logger = logging.getLogger(__name__)


@dataclass
class SelectionDebugResult:
    """
    Result of debugging a selection for a specific path.
    
    Attributes:
        path: Path that was tested
        decision: Final selection decision
        matching_rules: All rules that matched the path
        precedence_explanation: Detailed precedence explanation
        trace_log: Step-by-step trace of evaluation
        performance_metrics: Performance metrics for the evaluation
        recommendations: Recommendations for improving the selection
    """
    path: Path
    decision: SelectionDecision
    matching_rules: List[RuleMatch]
    precedence_explanation: PrecedenceExplanation
    trace_log: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PatternAnalysis:
    """
    Analysis of pattern configuration.
    
    Attributes:
        total_patterns: Total number of patterns
        include_patterns: Number of include patterns
        exclude_patterns: Number of exclude patterns
        pattern_complexity: Average pattern complexity
        potential_conflicts: Number of potential conflicts detected
        optimization_opportunities: List of optimization suggestions
    """
    total_patterns: int = 0
    include_patterns: int = 0
    exclude_patterns: int = 0
    pattern_complexity: float = 0.0
    potential_conflicts: int = 0
    optimization_opportunities: List[str] = field(default_factory=list)


@dataclass
class SelectionReport:
    """
    Comprehensive report for a selection configuration.
    
    Attributes:
        selection_config: The selection configuration analyzed
        test_results: Results from testing sample paths
        pattern_analysis: Analysis of pattern configuration
        conflict_summary: Summary of conflicts detected
        performance_summary: Performance analysis
        recommendations: Overall recommendations
        generated_at: When the report was generated
    """
    selection_config: SelectionConfig
    test_results: List[SelectionDebugResult] = field(default_factory=list)
    pattern_analysis: Optional[PatternAnalysis] = None
    conflict_summary: Dict[str, Any] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)


class SelectionDebugger:
    """
    Comprehensive debugging tools for selection configurations.
    
    Provides detailed tracing, explanation, and analysis of selection
    rule evaluation to help troubleshoot complex configurations.
    """
    
    def __init__(
        self,
        pattern_engine: PatternEngine,
        precedence_resolver: PrecedenceResolver
    ):
        """
        Initialize the selection debugger.
        
        Args:
            pattern_engine: PatternEngine instance for pattern matching
            precedence_resolver: PrecedenceResolver for conflict resolution
        """
        self.pattern_engine = pattern_engine
        self.precedence_resolver = precedence_resolver
        self.trace_enabled = False
        self.trace_log: List[str] = []
        self.verbose_logging = False
    
    def enable_tracing(self, verbose: bool = False) -> None:
        """
        Enable detailed tracing of selection evaluation.
        
        Args:
            verbose: Whether to enable verbose logging
        """
        self.trace_enabled = True
        self.verbose_logging = verbose
        self.trace_log.clear()
        logger.info("Selection tracing enabled" + (" (verbose)" if verbose else ""))
    
    def disable_tracing(self) -> None:
        """Disable tracing."""
        self.trace_enabled = False
        self.verbose_logging = False
        logger.info("Selection tracing disabled")
    
    def test_path_selection(
        self,
        test_path: Path,
        selection_config: SelectionConfig
    ) -> SelectionDebugResult:
        """
        Test selection logic against a specific path with detailed debugging.
        
        Args:
            test_path: Path to test
            selection_config: Selection configuration to test
            
        Returns:
            SelectionDebugResult with detailed information
        """
        start_time = time.time()
        
        if self.trace_enabled:
            self._log_trace(f"=== Testing path: {test_path} ===")
        
        # Compile patterns
        include_compiled = self.pattern_engine.compile_patterns(selection_config.include_patterns)
        exclude_compiled = self.pattern_engine.compile_patterns(selection_config.exclude_patterns)
        
        if self.trace_enabled:
            self._log_trace(f"Compiled {len(selection_config.include_patterns)} include patterns")
            self._log_trace(f"Compiled {len(selection_config.exclude_patterns)} exclude patterns")
        
        # Match against include patterns
        include_matches = self._find_matching_patterns(
            test_path,
            include_compiled,
            "include"
        )
        
        # Match against exclude patterns
        exclude_matches = self._find_matching_patterns(
            test_path,
            exclude_compiled,
            "exclude"
        )
        
        if self.trace_enabled:
            self._log_trace(f"Include patterns matched: {len(include_matches)}")
            for match in include_matches:
                self._log_trace(f"  - {match.rule.pattern} ({match.rule.syntax.value})")
            
            self._log_trace(f"Exclude patterns matched: {len(exclude_matches)}")
            for match in exclude_matches:
                self._log_trace(f"  - {match.rule.pattern} ({match.rule.syntax.value})")
        
        # Resolve precedence
        all_matches = include_matches + exclude_matches
        
        if all_matches:
            decision = self.precedence_resolver.resolve_selection_conflicts(
                test_path,
                all_matches
            )
            
            # Get detailed explanation
            precedence_explanation = self.precedence_resolver.get_precedence_explanation(
                test_path,
                include_matches,
                exclude_matches
            )
        else:
            # No matches - default to exclude
            decision = SelectionDecision(
                include=False,
                confidence=1.0,
                applied_rules=[],
                precedence_explanation="No patterns matched - default to exclude"
            )
            
            precedence_explanation = PrecedenceExplanation(
                path=test_path,
                decision=False,
                strategy_used=selection_config.precedence_config.default_strategy,
                evaluation_steps=["No patterns matched"],
                conflicting_rules=[],
                winning_rule=None,
                confidence=1.0
            )
        
        if self.trace_enabled:
            self._log_trace(f"Final decision: {'INCLUDE' if decision.include else 'EXCLUDE'}")
            self._log_trace(f"Confidence: {decision.confidence:.2f}")
            self._log_trace(f"Explanation: {decision.precedence_explanation}")
        
        # Calculate performance metrics
        evaluation_time_ms = (time.time() - start_time) * 1000
        performance_metrics = {
            'evaluation_time_ms': evaluation_time_ms,
            'patterns_evaluated': len(selection_config.include_patterns) + len(selection_config.exclude_patterns),
            'patterns_matched': len(all_matches)
        }
        
        # Generate recommendations
        recommendations = self._generate_path_recommendations(
            test_path,
            decision,
            include_matches,
            exclude_matches,
            selection_config
        )
        
        return SelectionDebugResult(
            path=test_path,
            decision=decision,
            matching_rules=all_matches,
            precedence_explanation=precedence_explanation,
            trace_log=self.trace_log.copy() if self.trace_enabled else [],
            performance_metrics=performance_metrics,
            recommendations=recommendations
        )
    
    def _find_matching_patterns(
        self,
        path: Path,
        compiled_patterns: CompiledPatternSet,
        match_type: str
    ) -> List[RuleMatch]:
        """
        Find all patterns that match a path.
        
        Args:
            path: Path to match
            compiled_patterns: Compiled pattern set
            match_type: Type of match ("include" or "exclude")
            
        Returns:
            List of RuleMatch objects
        """
        matches = []
        
        for compiled_pattern in compiled_patterns.patterns:
            if compiled_pattern.matches(path):
                match = RuleMatch(
                    rule=compiled_pattern.original_rule,
                    path=path,
                    match_type=match_type,
                    confidence=1.0
                )
                matches.append(match)
                
                if self.verbose_logging:
                    self._log_trace(
                        f"  Pattern '{compiled_pattern.original_rule.pattern}' matched "
                        f"(type: {match_type}, syntax: {compiled_pattern.original_rule.syntax.value})"
                    )
        
        return matches
    
    def _log_trace(self, message: str) -> None:
        """
        Log a trace message.
        
        Args:
            message: Message to log
        """
        self.trace_log.append(message)
        if self.verbose_logging:
            logger.debug(f"[TRACE] {message}")
    
    def _generate_path_recommendations(
        self,
        path: Path,
        decision: SelectionDecision,
        include_matches: List[RuleMatch],
        exclude_matches: List[RuleMatch],
        config: SelectionConfig
    ) -> List[str]:
        """
        Generate recommendations for a specific path evaluation.
        
        Args:
            path: Path that was evaluated
            decision: Selection decision
            include_matches: Include rules that matched
            exclude_matches: Exclude rules that matched
            config: Selection configuration
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check for conflicts
        if len(include_matches) > 0 and len(exclude_matches) > 0:
            recommendations.append(
                f"Path has {len(include_matches)} include and {len(exclude_matches)} exclude "
                f"rules - consider making rules more specific to avoid conflicts"
            )
        
        # Check for low confidence
        if decision.confidence < 0.8:
            recommendations.append(
                f"Decision confidence is low ({decision.confidence:.2f}) - "
                f"review conflicting rules and consider adjusting precedence strategy"
            )
        
        # Check for many matching rules
        total_matches = len(include_matches) + len(exclude_matches)
        if total_matches > 5:
            recommendations.append(
                f"Path matches {total_matches} rules - consider simplifying pattern set "
                f"to improve performance"
            )
        
        # Check for warnings
        if decision.warnings:
            recommendations.append(
                f"Decision generated {len(decision.warnings)} warning(s) - "
                f"review warnings for potential issues"
            )
        
        return recommendations
    
    def test_pattern_against_paths(
        self,
        pattern: PatternRule,
        test_paths: List[Path]
    ) -> Dict[str, Any]:
        """
        Test a single pattern against multiple paths.
        
        Args:
            pattern: Pattern to test
            test_paths: List of paths to test against
            
        Returns:
            Dictionary with test results
        """
        start_time = time.time()
        
        # Compile pattern
        compiled = self.pattern_engine.compile_patterns([pattern])
        
        # Test against each path
        matches = []
        non_matches = []
        
        for path in test_paths:
            match_result = self.pattern_engine.match_path(path, compiled)
            
            if match_result.matched:
                matches.append(path)
            else:
                non_matches.append(path)
        
        evaluation_time_ms = (time.time() - start_time) * 1000
        
        return {
            'pattern': pattern.pattern,
            'syntax': pattern.syntax.value,
            'total_paths_tested': len(test_paths),
            'matches': len(matches),
            'non_matches': len(non_matches),
            'match_ratio': len(matches) / len(test_paths) if test_paths else 0.0,
            'matching_paths': matches,
            'non_matching_paths': non_matches,
            'evaluation_time_ms': evaluation_time_ms,
            'paths_per_second': len(test_paths) / (evaluation_time_ms / 1000) if evaluation_time_ms > 0 else 0.0
        }
    
    def generate_selection_report(
        self,
        selection_config: SelectionConfig,
        sample_paths: Optional[List[Path]] = None
    ) -> SelectionReport:
        """
        Generate comprehensive report for a selection configuration.
        
        Args:
            selection_config: Selection configuration to analyze
            sample_paths: Optional sample paths to test
            
        Returns:
            SelectionReport with comprehensive analysis
        """
        logger.info("Generating selection report...")
        
        report = SelectionReport(
            selection_config=selection_config
        )
        
        # Analyze patterns
        report.pattern_analysis = self._analyze_patterns(selection_config)
        
        # Test sample paths if provided
        if sample_paths:
            logger.info(f"Testing {len(sample_paths)} sample paths...")
            for path in sample_paths:
                result = self.test_path_selection(path, selection_config)
                report.test_results.append(result)
        
        # Analyze conflicts
        report.conflict_summary = self._analyze_conflicts(report.test_results)
        
        # Analyze performance
        report.performance_summary = self._analyze_performance(
            selection_config,
            report.test_results
        )
        
        # Generate overall recommendations
        report.recommendations = self._generate_overall_recommendations(
            selection_config,
            report.pattern_analysis,
            report.conflict_summary,
            report.performance_summary
        )
        
        logger.info("Selection report generated")
        
        return report
    
    def _analyze_patterns(self, config: SelectionConfig) -> PatternAnalysis:
        """
        Analyze pattern configuration.
        
        Args:
            config: Selection configuration
            
        Returns:
            PatternAnalysis
        """
        analysis = PatternAnalysis(
            total_patterns=len(config.include_patterns) + len(config.exclude_patterns),
            include_patterns=len(config.include_patterns),
            exclude_patterns=len(config.exclude_patterns)
        )
        
        # Calculate average complexity
        if analysis.total_patterns > 0:
            all_patterns = config.include_patterns + config.exclude_patterns
            compiled = self.pattern_engine.compile_patterns(all_patterns)
            stats = self.pattern_engine.get_pattern_statistics(compiled)
            analysis.pattern_complexity = stats.average_complexity
        
        # Check for optimization opportunities
        if analysis.include_patterns == 0:
            analysis.optimization_opportunities.append(
                "No include patterns defined - consider adding explicit include patterns"
            )
        
        if analysis.exclude_patterns == 0:
            analysis.optimization_opportunities.append(
                "No exclude patterns defined - all included paths will be selected"
            )
        
        if analysis.total_patterns > 100:
            analysis.optimization_opportunities.append(
                f"Large number of patterns ({analysis.total_patterns}) - "
                f"consider using pattern groups to organize patterns"
            )
        
        if analysis.pattern_complexity > 50.0:
            analysis.optimization_opportunities.append(
                f"High average pattern complexity ({analysis.pattern_complexity:.1f}) - "
                f"consider simplifying patterns for better performance"
            )
        
        return analysis
    
    def _analyze_conflicts(
        self,
        test_results: List[SelectionDebugResult]
    ) -> Dict[str, Any]:
        """
        Analyze conflicts from test results.
        
        Args:
            test_results: List of test results
            
        Returns:
            Dictionary with conflict analysis
        """
        if not test_results:
            return {
                'total_conflicts': 0,
                'conflict_ratio': 0.0,
                'high_severity_conflicts': 0,
                'low_confidence_decisions': 0
            }
        
        total_conflicts = 0
        low_confidence = 0
        
        for result in test_results:
            # Check if there were both include and exclude matches
            include_count = sum(1 for m in result.matching_rules if m.match_type == "include")
            exclude_count = sum(1 for m in result.matching_rules if m.match_type == "exclude")
            
            if include_count > 0 and exclude_count > 0:
                total_conflicts += 1
            
            if result.decision.confidence < 0.8:
                low_confidence += 1
        
        return {
            'total_conflicts': total_conflicts,
            'conflict_ratio': total_conflicts / len(test_results),
            'low_confidence_decisions': low_confidence,
            'paths_tested': len(test_results)
        }
    
    def _analyze_performance(
        self,
        config: SelectionConfig,
        test_results: List[SelectionDebugResult]
    ) -> Dict[str, Any]:
        """
        Analyze performance characteristics.
        
        Args:
            config: Selection configuration
            test_results: List of test results
            
        Returns:
            Dictionary with performance analysis
        """
        if not test_results:
            return {
                'average_evaluation_time_ms': 0.0,
                'total_patterns': len(config.include_patterns) + len(config.exclude_patterns),
                'estimated_paths_per_second': 0.0
            }
        
        # Calculate average evaluation time
        total_time = sum(
            r.performance_metrics.get('evaluation_time_ms', 0.0)
            for r in test_results
        )
        avg_time_ms = total_time / len(test_results)
        
        # Estimate paths per second
        paths_per_second = 1000.0 / avg_time_ms if avg_time_ms > 0 else 0.0
        
        return {
            'average_evaluation_time_ms': avg_time_ms,
            'total_patterns': len(config.include_patterns) + len(config.exclude_patterns),
            'estimated_paths_per_second': paths_per_second,
            'paths_tested': len(test_results),
            'performance_rating': self._get_performance_rating(paths_per_second)
        }
    
    def _get_performance_rating(self, paths_per_second: float) -> str:
        """
        Get performance rating.
        
        Args:
            paths_per_second: Estimated paths per second
            
        Returns:
            Performance rating string
        """
        if paths_per_second >= 10000:
            return 'excellent'
        elif paths_per_second >= 5000:
            return 'good'
        elif paths_per_second >= 1000:
            return 'fair'
        else:
            return 'poor'
    
    def _generate_overall_recommendations(
        self,
        config: SelectionConfig,
        pattern_analysis: PatternAnalysis,
        conflict_summary: Dict[str, Any],
        performance_summary: Dict[str, Any]
    ) -> List[str]:
        """
        Generate overall recommendations for the selection configuration.
        
        Args:
            config: Selection configuration
            pattern_analysis: Pattern analysis results
            conflict_summary: Conflict analysis results
            performance_summary: Performance analysis results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Pattern recommendations
        recommendations.extend(pattern_analysis.optimization_opportunities)
        
        # Conflict recommendations
        conflict_ratio = conflict_summary.get('conflict_ratio', 0.0)
        if conflict_ratio > 0.3:
            recommendations.append(
                f"High conflict ratio ({conflict_ratio:.1%}) - review and simplify "
                f"include/exclude patterns to reduce conflicts"
            )
        
        # Performance recommendations
        perf_rating = performance_summary.get('performance_rating', 'unknown')
        if perf_rating in ('fair', 'poor'):
            recommendations.append(
                f"Performance rating is {perf_rating} - consider optimizing patterns "
                f"or using pattern groups"
            )
        
        # Precedence strategy recommendations
        if config.precedence_config.conflict_resolution == 'silent':
            recommendations.append(
                "Silent conflict resolution is enabled - consider using 'warn' mode "
                "to be notified of conflicts during development"
            )
        
        # General recommendations
        if not recommendations:
            recommendations.append(
                "Configuration looks good - no major issues detected"
            )
        
        return recommendations
    
    def get_trace_log(self) -> List[str]:
        """
        Get the current trace log.
        
        Returns:
            List of trace log messages
        """
        return self.trace_log.copy()
    
    def clear_trace_log(self) -> None:
        """Clear the trace log."""
        self.trace_log.clear()
    
    def format_report_as_text(self, report: SelectionReport) -> str:
        """
        Format a selection report as human-readable text.
        
        Args:
            report: Selection report to format
            
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("SELECTION CONFIGURATION REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Pattern analysis
        if report.pattern_analysis:
            lines.append("PATTERN ANALYSIS")
            lines.append("-" * 80)
            lines.append(f"Total patterns: {report.pattern_analysis.total_patterns}")
            lines.append(f"  Include patterns: {report.pattern_analysis.include_patterns}")
            lines.append(f"  Exclude patterns: {report.pattern_analysis.exclude_patterns}")
            lines.append(f"Average complexity: {report.pattern_analysis.pattern_complexity:.2f}")
            lines.append("")
        
        # Test results
        if report.test_results:
            lines.append("TEST RESULTS")
            lines.append("-" * 80)
            lines.append(f"Paths tested: {len(report.test_results)}")
            
            included = sum(1 for r in report.test_results if r.decision.include)
            excluded = len(report.test_results) - included
            
            lines.append(f"  Included: {included}")
            lines.append(f"  Excluded: {excluded}")
            lines.append("")
        
        # Conflict summary
        if report.conflict_summary:
            lines.append("CONFLICT SUMMARY")
            lines.append("-" * 80)
            lines.append(f"Total conflicts: {report.conflict_summary.get('total_conflicts', 0)}")
            lines.append(f"Conflict ratio: {report.conflict_summary.get('conflict_ratio', 0.0):.1%}")
            lines.append(f"Low confidence decisions: {report.conflict_summary.get('low_confidence_decisions', 0)}")
            lines.append("")
        
        # Performance summary
        if report.performance_summary:
            lines.append("PERFORMANCE SUMMARY")
            lines.append("-" * 80)
            lines.append(f"Average evaluation time: {report.performance_summary.get('average_evaluation_time_ms', 0.0):.2f} ms")
            lines.append(f"Estimated throughput: {report.performance_summary.get('estimated_paths_per_second', 0.0):.0f} paths/sec")
            lines.append(f"Performance rating: {report.performance_summary.get('performance_rating', 'unknown')}")
            lines.append("")
        
        # Recommendations
        if report.recommendations:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 80)
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
