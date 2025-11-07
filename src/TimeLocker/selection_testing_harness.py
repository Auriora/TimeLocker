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
from typing import Any, Callable, Dict, List, Optional, Tuple

from .pattern_engine import PatternEngine
from .precedence_resolver import PrecedenceResolver
from .selection_debugger import SelectionDebugger, SelectionReport
from .selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    SelectionConfig
)
from .selection_validation_service import SelectionValidationService

logger = logging.getLogger(__name__)


@dataclass
class TestScenario:
    """
    A test scenario for selection configuration testing.
    
    Attributes:
        name: Name of the test scenario
        description: Description of what is being tested
        selection_config: Selection configuration to test
        test_paths: Paths to test against the configuration
        expected_results: Expected inclusion/exclusion results
        tags: Tags for categorizing scenarios
    """
    name: str
    description: str
    selection_config: SelectionConfig
    test_paths: List[Path]
    expected_results: Dict[Path, bool]  # Path -> should_include
    tags: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """
    Result of running a test scenario.
    
    Attributes:
        scenario_name: Name of the scenario tested
        passed: Whether the test passed
        total_paths: Total number of paths tested
        correct_decisions: Number of correct decisions
        incorrect_decisions: Number of incorrect decisions
        accuracy: Accuracy percentage
        execution_time_ms: Execution time in milliseconds
        failures: List of failed path evaluations
        performance_metrics: Performance metrics
    """
    scenario_name: str
    passed: bool
    total_paths: int
    correct_decisions: int
    incorrect_decisions: int
    accuracy: float
    execution_time_ms: float
    failures: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class PerformanceBenchmarkResult:
    """
    Result of a performance benchmark.
    
    Attributes:
        scenario_name: Name of the scenario benchmarked
        total_paths: Total number of paths evaluated
        total_time_ms: Total execution time in milliseconds
        average_time_per_path_ms: Average time per path
        paths_per_second: Throughput in paths per second
        memory_usage_mb: Estimated memory usage
        pattern_count: Number of patterns in configuration
        performance_rating: Performance rating
    """
    scenario_name: str
    total_paths: int
    total_time_ms: float
    average_time_per_path_ms: float
    paths_per_second: float
    memory_usage_mb: float
    pattern_count: int
    performance_rating: str


@dataclass
class ValidationTestResult:
    """
    Result of validation testing.
    
    Attributes:
        scenario_name: Name of the scenario
        validation_passed: Whether validation passed
        errors_found: Number of errors found
        warnings_found: Number of warnings found
        conflicts_detected: Number of conflicts detected
        validation_time_ms: Validation execution time
        error_details: Details of errors found
        warning_details: Details of warnings found
    """
    scenario_name: str
    validation_passed: bool
    errors_found: int
    warnings_found: int
    conflicts_detected: int
    validation_time_ms: float
    error_details: List[str] = field(default_factory=list)
    warning_details: List[str] = field(default_factory=list)


class SelectionTestingHarness:
    """
    Comprehensive testing harness for selection configurations.
    
    Provides utilities for testing selection configurations against
    expected results, performance benchmarking, and validation testing.
    """
    
    def __init__(
        self,
        pattern_engine: PatternEngine,
        precedence_resolver: PrecedenceResolver,
        validation_service: SelectionValidationService
    ):
        """
        Initialize the testing harness.
        
        Args:
            pattern_engine: PatternEngine instance
            precedence_resolver: PrecedenceResolver instance
            validation_service: SelectionValidationService instance
        """
        self.pattern_engine = pattern_engine
        self.precedence_resolver = precedence_resolver
        self.validation_service = validation_service
        self.debugger = SelectionDebugger(pattern_engine, precedence_resolver)
        self.test_scenarios: List[TestScenario] = []
        self.test_results: List[TestResult] = []
    
    def add_test_scenario(self, scenario: TestScenario) -> None:
        """
        Add a test scenario to the harness.
        
        Args:
            scenario: Test scenario to add
        """
        self.test_scenarios.append(scenario)
        logger.info(f"Added test scenario: {scenario.name}")
    
    def run_test_scenario(self, scenario: TestScenario) -> TestResult:
        """
        Run a single test scenario.
        
        Args:
            scenario: Test scenario to run
            
        Returns:
            TestResult with results
        """
        logger.info(f"Running test scenario: {scenario.name}")
        start_time = time.time()
        
        correct = 0
        incorrect = 0
        failures = []
        
        for test_path in scenario.test_paths:
            expected_include = scenario.expected_results.get(test_path, False)
            
            # Test the path
            debug_result = self.debugger.test_path_selection(
                test_path,
                scenario.selection_config
            )
            
            actual_include = debug_result.decision.include
            
            if actual_include == expected_include:
                correct += 1
            else:
                incorrect += 1
                failures.append({
                    'path': str(test_path),
                    'expected': expected_include,
                    'actual': actual_include,
                    'confidence': debug_result.decision.confidence,
                    'explanation': debug_result.decision.precedence_explanation
                })
        
        execution_time_ms = (time.time() - start_time) * 1000
        total_paths = len(scenario.test_paths)
        accuracy = (correct / total_paths * 100) if total_paths > 0 else 0.0
        
        result = TestResult(
            scenario_name=scenario.name,
            passed=(incorrect == 0),
            total_paths=total_paths,
            correct_decisions=correct,
            incorrect_decisions=incorrect,
            accuracy=accuracy,
            execution_time_ms=execution_time_ms,
            failures=failures,
            performance_metrics={
                'paths_per_second': total_paths / (execution_time_ms / 1000) if execution_time_ms > 0 else 0.0,
                'average_time_per_path_ms': execution_time_ms / total_paths if total_paths > 0 else 0.0
            }
        )
        
        self.test_results.append(result)
        
        logger.info(
            f"Test scenario '{scenario.name}' completed: "
            f"{correct}/{total_paths} correct ({accuracy:.1f}%)"
        )
        
        return result
    
    def run_all_scenarios(self, tags: Optional[List[str]] = None) -> List[TestResult]:
        """
        Run all test scenarios, optionally filtered by tags.
        
        Args:
            tags: Optional list of tags to filter scenarios
            
        Returns:
            List of TestResult objects
        """
        scenarios_to_run = self.test_scenarios
        
        if tags:
            scenarios_to_run = [
                s for s in self.test_scenarios
                if any(tag in s.tags for tag in tags)
            ]
        
        logger.info(f"Running {len(scenarios_to_run)} test scenarios...")
        
        results = []
        for scenario in scenarios_to_run:
            result = self.run_test_scenario(scenario)
            results.append(result)
        
        return results
    
    def benchmark_performance(
        self,
        scenario: TestScenario,
        iterations: int = 3
    ) -> PerformanceBenchmarkResult:
        """
        Benchmark performance of a selection configuration.
        
        Args:
            scenario: Test scenario to benchmark
            iterations: Number of iterations to run
            
        Returns:
            PerformanceBenchmarkResult
        """
        logger.info(
            f"Benchmarking scenario '{scenario.name}' "
            f"with {iterations} iterations..."
        )
        
        total_times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            for test_path in scenario.test_paths:
                self.debugger.test_path_selection(
                    test_path,
                    scenario.selection_config
                )
            
            iteration_time_ms = (time.time() - start_time) * 1000
            total_times.append(iteration_time_ms)
        
        # Calculate statistics
        avg_total_time_ms = sum(total_times) / len(total_times)
        total_paths = len(scenario.test_paths)
        avg_time_per_path_ms = avg_total_time_ms / total_paths if total_paths > 0 else 0.0
        paths_per_second = 1000.0 / avg_time_per_path_ms if avg_time_per_path_ms > 0 else 0.0
        
        # Estimate memory usage (simplified)
        pattern_count = (
            len(scenario.selection_config.include_patterns) +
            len(scenario.selection_config.exclude_patterns)
        )
        estimated_memory_mb = (pattern_count * 0.1) + (total_paths * 0.001)
        
        # Determine performance rating
        if paths_per_second >= 10000:
            rating = 'excellent'
        elif paths_per_second >= 5000:
            rating = 'good'
        elif paths_per_second >= 1000:
            rating = 'fair'
        else:
            rating = 'poor'
        
        result = PerformanceBenchmarkResult(
            scenario_name=scenario.name,
            total_paths=total_paths,
            total_time_ms=avg_total_time_ms,
            average_time_per_path_ms=avg_time_per_path_ms,
            paths_per_second=paths_per_second,
            memory_usage_mb=estimated_memory_mb,
            pattern_count=pattern_count,
            performance_rating=rating
        )
        
        logger.info(
            f"Benchmark complete: {paths_per_second:.0f} paths/sec "
            f"(rating: {rating})"
        )
        
        return result
    
    def validate_scenario(self, scenario: TestScenario) -> ValidationTestResult:
        """
        Validate a test scenario configuration.
        
        Args:
            scenario: Test scenario to validate
            
        Returns:
            ValidationTestResult
        """
        logger.info(f"Validating scenario: {scenario.name}")
        start_time = time.time()
        
        # Validate the selection configuration (synchronous wrapper for async method)
        try:
            import asyncio
            validation_result = asyncio.run(
                self.validation_service.validate_selection_config(
                    scenario.selection_config
                )
            )
            
            # Detect conflicts
            conflicts = asyncio.run(
                self.validation_service.detect_selection_conflicts(
                    scenario.selection_config
                )
            )
        except RuntimeError:
            # If we're already in an event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                validation_result = loop.run_until_complete(
                    self.validation_service.validate_selection_config(
                        scenario.selection_config
                    )
                )
                conflicts = loop.run_until_complete(
                    self.validation_service.detect_selection_conflicts(
                        scenario.selection_config
                    )
                )
            finally:
                loop.close()
        
        validation_time_ms = (time.time() - start_time) * 1000
        
        result = ValidationTestResult(
            scenario_name=scenario.name,
            validation_passed=validation_result.is_valid,
            errors_found=len(validation_result.errors),
            warnings_found=len(validation_result.warnings),
            conflicts_detected=len(conflicts),
            validation_time_ms=validation_time_ms,
            error_details=[str(e) for e in validation_result.errors],
            warning_details=[str(w) for w in validation_result.warnings]
        )
        
        logger.info(
            f"Validation complete: "
            f"{'PASSED' if result.validation_passed else 'FAILED'} "
            f"({result.errors_found} errors, {result.warnings_found} warnings)"
        )
        
        return result
    
    def generate_test_report(self) -> str:
        """
        Generate a comprehensive test report.
        
        Returns:
            Formatted test report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("SELECTION TESTING HARNESS REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        if not self.test_results:
            lines.append("No test results available.")
            return "\n".join(lines)
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests
        
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total scenarios: {total_tests}")
        lines.append(f"Passed: {passed_tests}")
        lines.append(f"Failed: {failed_tests}")
        lines.append(f"Success rate: {(passed_tests / total_tests * 100):.1f}%")
        lines.append("")
        
        # Individual results
        lines.append("DETAILED RESULTS")
        lines.append("-" * 80)
        
        for result in self.test_results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"\n[{status}] {result.scenario_name}")
            lines.append(f"  Accuracy: {result.accuracy:.1f}%")
            lines.append(f"  Correct: {result.correct_decisions}/{result.total_paths}")
            lines.append(f"  Execution time: {result.execution_time_ms:.2f} ms")
            lines.append(f"  Throughput: {result.performance_metrics.get('paths_per_second', 0):.0f} paths/sec")
            
            if result.failures:
                lines.append(f"  Failures: {len(result.failures)}")
                for failure in result.failures[:5]:  # Show first 5 failures
                    lines.append(f"    - {failure['path']}")
                    lines.append(f"      Expected: {'INCLUDE' if failure['expected'] else 'EXCLUDE'}")
                    lines.append(f"      Actual: {'INCLUDE' if failure['actual'] else 'EXCLUDE'}")
                
                if len(result.failures) > 5:
                    lines.append(f"    ... and {len(result.failures) - 5} more")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def create_standard_test_scenarios(self) -> List[TestScenario]:
        """
        Create a set of standard test scenarios for common use cases.
        
        Returns:
            List of standard test scenarios
        """
        scenarios = []
        
        # Scenario 1: Simple include/exclude
        scenarios.append(TestScenario(
            name="simple_include_exclude",
            description="Basic include and exclude patterns",
            selection_config=SelectionConfig(
                include_paths=[Path("/home/user")],
                exclude_paths=[],
                include_patterns=[],
                exclude_patterns=[
                    PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False,
                performance_hints={}
            ),
            test_paths=[
                Path("/home/user/document.txt"),
                Path("/home/user/temp.tmp"),
                Path("/home/user/app.log"),
                Path("/home/user/data.csv")
            ],
            expected_results={
                Path("/home/user/document.txt"): True,
                Path("/home/user/temp.tmp"): False,
                Path("/home/user/app.log"): False,
                Path("/home/user/data.csv"): True
            },
            tags=["basic", "patterns"]
        ))
        
        # Scenario 2: Complex hierarchical selection
        scenarios.append(TestScenario(
            name="hierarchical_selection",
            description="Include directory, exclude subdirectory, re-include specific file",
            selection_config=SelectionConfig(
                include_paths=[Path("/home/user")],
                exclude_paths=[Path("/home/user/temp")],
                include_patterns=[
                    PatternRule("important.txt", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 200)
                ],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=True,
                performance_hints={}
            ),
            test_paths=[
                Path("/home/user/document.txt"),
                Path("/home/user/temp/cache.dat"),
                Path("/home/user/temp/important.txt"),
                Path("/home/user/data/file.txt")
            ],
            expected_results={
                Path("/home/user/document.txt"): True,
                Path("/home/user/temp/cache.dat"): False,
                Path("/home/user/temp/important.txt"): True,
                Path("/home/user/data/file.txt"): True
            },
            tags=["hierarchical", "precedence"]
        ))
        
        # Scenario 3: Regex patterns
        scenarios.append(TestScenario(
            name="regex_patterns",
            description="Using regex patterns for complex matching",
            selection_config=SelectionConfig(
                include_paths=[Path("/var/log")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule(r".*\.log\.\d{4}-\d{2}-\d{2}$", PatternSyntax.REGEX, True, PathComponent.FILENAME, 100)
                ],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=True,
                performance_hints={}
            ),
            test_paths=[
                Path("/var/log/app.log.2024-01-15"),
                Path("/var/log/app.log"),
                Path("/var/log/system.log.2024-02-20"),
                Path("/var/log/debug.txt")
            ],
            expected_results={
                Path("/var/log/app.log.2024-01-15"): True,
                Path("/var/log/app.log"): False,
                Path("/var/log/system.log.2024-02-20"): True,
                Path("/var/log/debug.txt"): False
            },
            tags=["regex", "advanced"]
        ))
        
        logger.info(f"Created {len(scenarios)} standard test scenarios")
        return scenarios


class PerformanceTestSuite:
    """
    Specialized test suite for performance testing.
    """
    
    def __init__(self, harness: SelectionTestingHarness):
        """
        Initialize the performance test suite.
        
        Args:
            harness: SelectionTestingHarness instance
        """
        self.harness = harness
    
    def test_large_file_set(
        self,
        selection_config: SelectionConfig,
        file_count: int = 10000
    ) -> PerformanceBenchmarkResult:
        """
        Test performance with a large number of files.
        
        Args:
            selection_config: Selection configuration to test
            file_count: Number of test files to generate
            
        Returns:
            PerformanceBenchmarkResult
        """
        logger.info(f"Generating {file_count} test paths...")
        
        # Generate test paths
        test_paths = []
        for i in range(file_count):
            # Mix of different file types and depths
            if i % 4 == 0:
                test_paths.append(Path(f"/data/documents/file_{i}.txt"))
            elif i % 4 == 1:
                test_paths.append(Path(f"/data/temp/cache_{i}.tmp"))
            elif i % 4 == 2:
                test_paths.append(Path(f"/data/logs/app_{i}.log"))
            else:
                test_paths.append(Path(f"/data/media/image_{i}.jpg"))
        
        scenario = TestScenario(
            name=f"large_file_set_{file_count}",
            description=f"Performance test with {file_count} files",
            selection_config=selection_config,
            test_paths=test_paths,
            expected_results={},  # Not checking correctness, just performance
            tags=["performance", "large"]
        )
        
        return self.harness.benchmark_performance(scenario, iterations=3)
    
    def test_complex_patterns(
        self,
        pattern_count: int = 100
    ) -> PerformanceBenchmarkResult:
        """
        Test performance with many complex patterns.
        
        Args:
            pattern_count: Number of patterns to test
            
        Returns:
            PerformanceBenchmarkResult
        """
        logger.info(f"Testing with {pattern_count} patterns...")
        
        # Generate complex patterns
        patterns = []
        for i in range(pattern_count):
            if i % 3 == 0:
                patterns.append(PatternRule(
                    f"*.{i:03d}",
                    PatternSyntax.GLOB,
                    False,
                    PathComponent.FILENAME,
                    100
                ))
            elif i % 3 == 1:
                patterns.append(PatternRule(
                    f".*file_{i}.*",
                    PatternSyntax.REGEX,
                    True,
                    PathComponent.FILENAME,
                    100
                ))
            else:
                patterns.append(PatternRule(
                    f"data_{i}.txt",
                    PatternSyntax.LITERAL,
                    True,
                    PathComponent.FILENAME,
                    100
                ))
        
        selection_config = SelectionConfig(
            include_paths=[Path("/data")],
            exclude_paths=[],
            include_patterns=[],
            exclude_patterns=patterns,
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False,
            performance_hints={}
        )
        
        # Generate test paths
        test_paths = [Path(f"/data/file_{i}.txt") for i in range(1000)]
        
        scenario = TestScenario(
            name=f"complex_patterns_{pattern_count}",
            description=f"Performance test with {pattern_count} patterns",
            selection_config=selection_config,
            test_paths=test_paths,
            expected_results={},
            tags=["performance", "patterns"]
        )
        
        return self.harness.benchmark_performance(scenario, iterations=3)


class ValidationTestSuite:
    """
    Specialized test suite for validation testing.
    """
    
    def __init__(self, harness: SelectionTestingHarness):
        """
        Initialize the validation test suite.
        
        Args:
            harness: SelectionTestingHarness instance
        """
        self.harness = harness
    
    def test_invalid_patterns(self) -> List[ValidationTestResult]:
        """
        Test validation of invalid pattern configurations.
        
        Returns:
            List of ValidationTestResult objects
        """
        results = []
        
        # Test 1: Invalid regex pattern - expect exception
        scenario1 = TestScenario(
            name="invalid_regex",
            description="Invalid regex pattern syntax",
            selection_config=SelectionConfig(
                include_paths=[Path("/data")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule("[invalid(regex", PatternSyntax.REGEX, True, PathComponent.FILENAME, 100)
                ],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=True,
                performance_hints={}
            ),
            test_paths=[],
            expected_results={},
            tags=["validation", "error"]
        )
        
        # This should raise an exception due to invalid regex
        try:
            result = self.harness.validate_scenario(scenario1)
            results.append(result)
        except Exception as e:
            # Create a result indicating validation failed due to exception
            results.append(ValidationTestResult(
                scenario_name=scenario1.name,
                validation_passed=False,
                errors_found=1,
                warnings_found=0,
                conflicts_detected=0,
                validation_time_ms=0.0,
                error_details=[str(e)],
                warning_details=[]
            ))
        
        # Test 2: No include paths
        scenario2 = TestScenario(
            name="no_include_paths",
            description="Configuration with no include paths",
            selection_config=SelectionConfig(
                include_paths=[],
                exclude_paths=[],
                include_patterns=[],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False,
                performance_hints={}
            ),
            test_paths=[],
            expected_results={},
            tags=["validation", "warning"]
        )
        
        results.append(self.harness.validate_scenario(scenario2))
        
        return results
    
    def test_conflict_scenarios(self) -> List[ValidationTestResult]:
        """
        Test detection of conflicting patterns.
        
        Returns:
            List of ValidationTestResult objects
        """
        results = []
        
        # Test: Overlapping include/exclude patterns
        scenario = TestScenario(
            name="overlapping_patterns",
            description="Overlapping include and exclude patterns",
            selection_config=SelectionConfig(
                include_paths=[Path("/data")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                exclude_patterns=[
                    PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False,
                performance_hints={}
            ),
            test_paths=[],
            expected_results={},
            tags=["validation", "conflict"]
        )
        
        results.append(self.harness.validate_scenario(scenario))
        
        return results
