"""
Demo script showing how to use the Selection Testing Harness.

This script demonstrates:
1. Creating test scenarios
2. Running functional tests
3. Performance benchmarking
4. Validation testing
"""

import logging
from pathlib import Path

from TimeLocker.pattern_engine import PatternEngine
from TimeLocker.precedence_resolver import PrecedenceResolver
from TimeLocker.selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    SelectionConfig
)
from TimeLocker.selection_testing_harness import (
    PerformanceTestSuite,
    SelectionTestingHarness,
    TestScenario,
    ValidationTestSuite
)
from TimeLocker.selection_validation_service import SelectionValidationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_functional_testing():
    """Demonstrate functional testing of selection configurations."""
    logger.info("=" * 80)
    logger.info("FUNCTIONAL TESTING DEMO")
    logger.info("=" * 80)
    
    # Initialize components
    pattern_engine = PatternEngine()
    precedence_resolver = PrecedenceResolver()
    validation_service = SelectionValidationService(pattern_engine)
    
    # Create testing harness
    harness = SelectionTestingHarness(
        pattern_engine,
        precedence_resolver,
        validation_service
    )
    
    # Create a custom test scenario
    scenario = TestScenario(
        name="web_development_backup",
        description="Test web development project backup configuration",
        selection_config=SelectionConfig(
            include_paths=[Path("/home/user/projects/webapp")],
            exclude_paths=[],
            include_patterns=[
                PatternRule("*.js", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                PatternRule("*.ts", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                PatternRule("*.html", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                PatternRule("*.css", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            ],
            exclude_patterns=[
                PatternRule("node_modules/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                PatternRule("dist/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            ],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False,
            performance_hints={}
        ),
        test_paths=[
            Path("/home/user/projects/webapp/src/app.js"),
            Path("/home/user/projects/webapp/src/index.html"),
            Path("/home/user/projects/webapp/node_modules/package/index.js"),
            Path("/home/user/projects/webapp/dist/bundle.js"),
            Path("/home/user/projects/webapp/debug.log"),
            Path("/home/user/projects/webapp/README.md"),
        ],
        expected_results={
            Path("/home/user/projects/webapp/src/app.js"): True,
            Path("/home/user/projects/webapp/src/index.html"): True,
            Path("/home/user/projects/webapp/node_modules/package/index.js"): False,
            Path("/home/user/projects/webapp/dist/bundle.js"): False,
            Path("/home/user/projects/webapp/debug.log"): False,
            Path("/home/user/projects/webapp/README.md"): True,
        },
        tags=["web", "development"]
    )
    
    # Add scenario to harness
    harness.add_test_scenario(scenario)
    
    # Run the test
    result = harness.run_test_scenario(scenario)
    
    # Display results
    print(f"\nTest Results for '{result.scenario_name}':")
    print(f"  Status: {'PASSED' if result.passed else 'FAILED'}")
    print(f"  Accuracy: {result.accuracy:.1f}%")
    print(f"  Correct: {result.correct_decisions}/{result.total_paths}")
    print(f"  Execution time: {result.execution_time_ms:.2f} ms")
    print(f"  Throughput: {result.performance_metrics['paths_per_second']:.0f} paths/sec")
    
    if result.failures:
        print(f"\n  Failures:")
        for failure in result.failures:
            print(f"    - {failure['path']}")
            print(f"      Expected: {'INCLUDE' if failure['expected'] else 'EXCLUDE'}")
            print(f"      Actual: {'INCLUDE' if failure['actual'] else 'EXCLUDE'}")
            print(f"      Confidence: {failure['confidence']:.2f}")
    
    # Generate and display full report
    print("\n" + harness.generate_test_report())


def demo_standard_scenarios():
    """Demonstrate running standard test scenarios."""
    logger.info("=" * 80)
    logger.info("STANDARD SCENARIOS DEMO")
    logger.info("=" * 80)
    
    # Initialize components
    pattern_engine = PatternEngine()
    precedence_resolver = PrecedenceResolver()
    validation_service = SelectionValidationService(pattern_engine)
    
    # Create testing harness
    harness = SelectionTestingHarness(
        pattern_engine,
        precedence_resolver,
        validation_service
    )
    
    # Create and add standard scenarios
    standard_scenarios = harness.create_standard_test_scenarios()
    for scenario in standard_scenarios:
        harness.add_test_scenario(scenario)
    
    # Run all scenarios
    results = harness.run_all_scenarios()
    
    # Display summary
    print(f"\nRan {len(results)} standard test scenarios")
    passed = sum(1 for r in results if r.passed)
    print(f"Passed: {passed}/{len(results)}")
    
    # Display full report
    print("\n" + harness.generate_test_report())


def demo_performance_testing():
    """Demonstrate performance benchmarking."""
    logger.info("=" * 80)
    logger.info("PERFORMANCE TESTING DEMO")
    logger.info("=" * 80)
    
    # Initialize components
    pattern_engine = PatternEngine()
    precedence_resolver = PrecedenceResolver()
    validation_service = SelectionValidationService(pattern_engine)
    
    # Create testing harness
    harness = SelectionTestingHarness(
        pattern_engine,
        precedence_resolver,
        validation_service
    )
    
    # Create performance test suite
    perf_suite = PerformanceTestSuite(harness)
    
    # Test 1: Large file set
    print("\nTest 1: Large file set (10,000 files)")
    selection_config = SelectionConfig(
        include_paths=[Path("/data")],
        exclude_paths=[],
        include_patterns=[],
        exclude_patterns=[
            PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.cache", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        pattern_groups=[],
        precedence_config=PrecedenceConfig(),
        case_sensitive=False,
        performance_hints={}
    )
    
    result1 = perf_suite.test_large_file_set(selection_config, file_count=10000)
    
    print(f"  Total paths: {result1.total_paths}")
    print(f"  Total time: {result1.total_time_ms:.2f} ms")
    print(f"  Average time per path: {result1.average_time_per_path_ms:.4f} ms")
    print(f"  Throughput: {result1.paths_per_second:.0f} paths/sec")
    print(f"  Estimated memory: {result1.memory_usage_mb:.2f} MB")
    print(f"  Performance rating: {result1.performance_rating}")
    
    # Test 2: Complex patterns
    print("\nTest 2: Complex patterns (100 patterns)")
    result2 = perf_suite.test_complex_patterns(pattern_count=100)
    
    print(f"  Pattern count: {result2.pattern_count}")
    print(f"  Total paths: {result2.total_paths}")
    print(f"  Total time: {result2.total_time_ms:.2f} ms")
    print(f"  Average time per path: {result2.average_time_per_path_ms:.4f} ms")
    print(f"  Throughput: {result2.paths_per_second:.0f} paths/sec")
    print(f"  Performance rating: {result2.performance_rating}")


def demo_validation_testing():
    """Demonstrate validation testing."""
    logger.info("=" * 80)
    logger.info("VALIDATION TESTING DEMO")
    logger.info("=" * 80)
    
    # Initialize components
    pattern_engine = PatternEngine()
    precedence_resolver = PrecedenceResolver()
    validation_service = SelectionValidationService(pattern_engine)
    
    # Create testing harness
    harness = SelectionTestingHarness(
        pattern_engine,
        precedence_resolver,
        validation_service
    )
    
    # Create validation test suite
    validation_suite = ValidationTestSuite(harness)
    
    # Test invalid patterns
    print("\nTesting invalid pattern configurations...")
    results = validation_suite.test_invalid_patterns()
    
    for result in results:
        print(f"\nScenario: {result.scenario_name}")
        print(f"  Validation: {'PASSED' if result.validation_passed else 'FAILED'}")
        print(f"  Errors: {result.errors_found}")
        print(f"  Warnings: {result.warnings_found}")
        print(f"  Conflicts: {result.conflicts_detected}")
        print(f"  Validation time: {result.validation_time_ms:.2f} ms")
        
        if result.error_details:
            print("  Error details:")
            for error in result.error_details:
                print(f"    - {error}")
        
        if result.warning_details:
            print("  Warning details:")
            for warning in result.warning_details:
                print(f"    - {warning}")
    
    # Test conflict scenarios
    print("\nTesting conflict detection...")
    conflict_results = validation_suite.test_conflict_scenarios()
    
    for result in conflict_results:
        print(f"\nScenario: {result.scenario_name}")
        print(f"  Conflicts detected: {result.conflicts_detected}")
        print(f"  Validation time: {result.validation_time_ms:.2f} ms")


def demo_custom_test_scenario():
    """Demonstrate creating and running a custom test scenario."""
    logger.info("=" * 80)
    logger.info("CUSTOM TEST SCENARIO DEMO")
    logger.info("=" * 80)
    
    # Initialize components
    pattern_engine = PatternEngine()
    precedence_resolver = PrecedenceResolver()
    validation_service = SelectionValidationService(pattern_engine)
    
    # Create testing harness
    harness = SelectionTestingHarness(
        pattern_engine,
        precedence_resolver,
        validation_service
    )
    
    # Create a custom scenario for database backup
    scenario = TestScenario(
        name="postgresql_backup",
        description="PostgreSQL database backup with log exclusion",
        selection_config=SelectionConfig(
            include_paths=[
                Path("/var/lib/postgresql"),
                Path("/etc/postgresql")
            ],
            exclude_paths=[],
            include_patterns=[
                PatternRule("*.conf", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                PatternRule("*.sql", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            ],
            exclude_patterns=[
                PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                PatternRule("postmaster.pid", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 200),
            ],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=True,
            performance_hints={}
        ),
        test_paths=[
            Path("/var/lib/postgresql/data/base/12345/table.dat"),
            Path("/var/lib/postgresql/data/pg_log/postgresql.log"),
            Path("/etc/postgresql/postgresql.conf"),
            Path("/var/lib/postgresql/data/postmaster.pid"),
            Path("/var/lib/postgresql/backup.sql"),
        ],
        expected_results={
            Path("/var/lib/postgresql/data/base/12345/table.dat"): True,
            Path("/var/lib/postgresql/data/pg_log/postgresql.log"): False,
            Path("/etc/postgresql/postgresql.conf"): True,
            Path("/var/lib/postgresql/data/postmaster.pid"): False,
            Path("/var/lib/postgresql/backup.sql"): True,
        },
        tags=["database", "postgresql"]
    )
    
    # Add and run the scenario
    harness.add_test_scenario(scenario)
    result = harness.run_test_scenario(scenario)
    
    # Validate the scenario
    validation_result = harness.validate_scenario(scenario)
    
    # Benchmark performance
    perf_result = harness.benchmark_performance(scenario, iterations=3)
    
    # Display comprehensive results
    print(f"\nTest Results:")
    print(f"  Status: {'PASSED' if result.passed else 'FAILED'}")
    print(f"  Accuracy: {result.accuracy:.1f}%")
    print(f"  Execution time: {result.execution_time_ms:.2f} ms")
    
    print(f"\nValidation Results:")
    print(f"  Validation: {'PASSED' if validation_result.validation_passed else 'FAILED'}")
    print(f"  Errors: {validation_result.errors_found}")
    print(f"  Warnings: {validation_result.warnings_found}")
    
    print(f"\nPerformance Results:")
    print(f"  Throughput: {perf_result.paths_per_second:.0f} paths/sec")
    print(f"  Performance rating: {perf_result.performance_rating}")


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("SELECTION TESTING HARNESS DEMONSTRATION")
    print("=" * 80 + "\n")
    
    # Run demos
    demo_functional_testing()
    print("\n")
    
    demo_standard_scenarios()
    print("\n")
    
    demo_performance_testing()
    print("\n")
    
    demo_validation_testing()
    print("\n")
    
    demo_custom_test_scenario()
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
