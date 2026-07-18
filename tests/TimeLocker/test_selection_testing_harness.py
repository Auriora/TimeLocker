"""
Unit tests for the Selection Testing Harness.

Tests the functionality of the testing harness including:
- Test scenario creation and execution
- Performance benchmarking
- Validation testing
- Report generation
"""

import pytest
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


@pytest.fixture
def pattern_engine():
    """Create a PatternEngine instance."""
    return PatternEngine()


@pytest.fixture
def precedence_resolver():
    """Create a PrecedenceResolver instance."""
    return PrecedenceResolver()


@pytest.fixture
def validation_service(pattern_engine):
    """Create a SelectionValidationService instance."""
    return SelectionValidationService(pattern_engine)


@pytest.fixture
def testing_harness(pattern_engine, precedence_resolver, validation_service):
    """Create a SelectionTestingHarness instance."""
    return SelectionTestingHarness(
        pattern_engine,
        precedence_resolver,
        validation_service
    )


@pytest.fixture
def simple_test_scenario():
    """Create a simple test scenario."""
    return TestScenario(
        name="simple_test",
        description="Simple include/exclude test",
        selection_config=SelectionConfig(
            include_paths=[Path("/data")],
            exclude_paths=[],
            include_patterns=[
                PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
            ],
            exclude_patterns=[
                PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
            ],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False,
            performance_hints={}
        ),
        test_paths=[
            Path("/data/file.txt"),
            Path("/data/temp.tmp"),
        ],
        expected_results={
            Path("/data/file.txt"): True,
            Path("/data/temp.tmp"): False,
        },
        tags=["simple"]
    )


class TestSelectionTestingHarness:
    """Tests for SelectionTestingHarness class."""
    
    def test_initialization(self, testing_harness):
        """Test harness initialization."""
        assert testing_harness is not None
        assert testing_harness.pattern_engine is not None
        assert testing_harness.precedence_resolver is not None
        assert testing_harness.validation_service is not None
        assert testing_harness.debugger is not None
        assert len(testing_harness.test_scenarios) == 0
        assert len(testing_harness.test_results) == 0
    
    def test_add_test_scenario(self, testing_harness, simple_test_scenario):
        """Test adding a test scenario."""
        testing_harness.add_test_scenario(simple_test_scenario)
        
        assert len(testing_harness.test_scenarios) == 1
        assert testing_harness.test_scenarios[0].name == "simple_test"
    
    def test_run_test_scenario(self, testing_harness, simple_test_scenario):
        """Test running a test scenario."""
        result = testing_harness.run_test_scenario(simple_test_scenario)
        
        assert result is not None
        assert result.scenario_name == "simple_test"
        assert result.total_paths == 2
        assert result.passed is True
        assert result.accuracy == 100.0
        assert result.correct_decisions == 2
        assert result.incorrect_decisions == 0
        assert len(result.failures) == 0
        assert result.execution_time_ms > 0
    
    def test_run_test_scenario_with_failures(self, testing_harness):
        """Test running a scenario that should fail."""
        # Create a scenario with incorrect expected results
        scenario = TestScenario(
            name="failing_test",
            description="Test with incorrect expectations",
            selection_config=SelectionConfig(
                include_paths=[Path("/data")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                exclude_patterns=[
                    PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False,
                performance_hints={}
            ),
            test_paths=[
                Path("/data/file.txt"),
                Path("/data/temp.tmp"),
            ],
            expected_results={
                Path("/data/file.txt"): False,  # Wrong expectation
                Path("/data/temp.tmp"): True,   # Wrong expectation
            },
            tags=["failing"]
        )
        
        result = testing_harness.run_test_scenario(scenario)
        
        assert result.passed is False
        assert result.accuracy == 0.0
        assert result.correct_decisions == 0
        assert result.incorrect_decisions == 2
        assert len(result.failures) == 2
    
    def test_run_all_scenarios(self, testing_harness):
        """Test running all scenarios."""
        # Add multiple scenarios
        scenarios = testing_harness.create_standard_test_scenarios()
        for scenario in scenarios:
            testing_harness.add_test_scenario(scenario)
        
        results = testing_harness.run_all_scenarios()
        
        assert len(results) == len(scenarios)
        assert all(r.scenario_name in [s.name for s in scenarios] for r in results)
    
    def test_run_scenarios_with_tag_filter(self, testing_harness):
        """Test running scenarios filtered by tags."""
        # Add scenarios with different tags
        scenario1 = TestScenario(
            name="test1",
            description="Test 1",
            selection_config=SelectionConfig(
                include_paths=[Path("/data")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False,
                performance_hints={}
            ),
            test_paths=[Path("/data/file.txt")],
            expected_results={Path("/data/file.txt"): True},
            tags=["tag1"]
        )
        
        scenario2 = TestScenario(
            name="test2",
            description="Test 2",
            selection_config=SelectionConfig(
                include_paths=[Path("/data")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False,
                performance_hints={}
            ),
            test_paths=[Path("/data/file.txt")],
            expected_results={Path("/data/file.txt"): True},
            tags=["tag2"]
        )
        
        testing_harness.add_test_scenario(scenario1)
        testing_harness.add_test_scenario(scenario2)
        
        # Run only scenarios with tag1
        results = testing_harness.run_all_scenarios(tags=["tag1"])
        
        assert len(results) == 1
        assert results[0].scenario_name == "test1"
    
    def test_benchmark_performance(self, testing_harness, simple_test_scenario):
        """Test performance benchmarking."""
        result = testing_harness.benchmark_performance(simple_test_scenario, iterations=2)
        
        assert result is not None
        assert result.scenario_name == "simple_test"
        assert result.total_paths == 2
        assert result.total_time_ms > 0
        assert result.average_time_per_path_ms > 0
        assert result.paths_per_second > 0
        assert result.memory_usage_mb > 0
        assert result.pattern_count == 2  # 1 include + 1 exclude
        assert result.performance_rating in ['excellent', 'good', 'fair', 'poor']
    
    def test_validate_scenario(self, testing_harness, simple_test_scenario):
        """Test scenario validation."""
        result = testing_harness.validate_scenario(simple_test_scenario)
        
        assert result is not None
        assert result.scenario_name == "simple_test"
        assert result.validation_time_ms > 0
    
    def test_generate_test_report(self, testing_harness, simple_test_scenario):
        """Test report generation."""
        # Run a test to generate results
        testing_harness.run_test_scenario(simple_test_scenario)
        
        report = testing_harness.generate_test_report()
        
        assert report is not None
        assert isinstance(report, str)
        assert "SELECTION TESTING HARNESS REPORT" in report
        assert "SUMMARY" in report
        assert "simple_test" in report
    
    def test_create_standard_test_scenarios(self, testing_harness):
        """Test creation of standard test scenarios."""
        scenarios = testing_harness.create_standard_test_scenarios()
        
        assert len(scenarios) > 0
        assert all(isinstance(s, TestScenario) for s in scenarios)
        assert all(s.name for s in scenarios)
        assert all(s.description for s in scenarios)
        assert all(s.selection_config for s in scenarios)


class TestPerformanceTestSuite:
    """Tests for PerformanceTestSuite class."""
    
    def test_initialization(self, testing_harness):
        """Test performance test suite initialization."""
        suite = PerformanceTestSuite(testing_harness)
        
        assert suite is not None
        assert suite.harness is testing_harness
    
    def test_large_file_set(self, testing_harness):
        """Test large file set performance testing."""
        suite = PerformanceTestSuite(testing_harness)
        
        selection_config = SelectionConfig(
            include_paths=[Path("/data")],
            exclude_paths=[],
            include_patterns=[],
            exclude_patterns=[
                PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
            ],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False,
            performance_hints={}
        )
        
        result = suite.test_large_file_set(selection_config, file_count=100)
        
        assert result is not None
        assert result.total_paths == 100
        assert result.total_time_ms > 0
        assert result.paths_per_second > 0
    
    def test_complex_patterns(self, testing_harness):
        """Test complex patterns performance testing."""
        suite = PerformanceTestSuite(testing_harness)
        
        result = suite.test_complex_patterns(pattern_count=10)
        
        assert result is not None
        assert result.pattern_count == 10
        assert result.total_paths == 1000
        assert result.total_time_ms > 0


class TestValidationTestSuite:
    """Tests for ValidationTestSuite class."""
    
    def test_initialization(self, testing_harness):
        """Test validation test suite initialization."""
        suite = ValidationTestSuite(testing_harness)
        
        assert suite is not None
        assert suite.harness is testing_harness
    
    def test_invalid_patterns(self, testing_harness):
        """Test validation of invalid patterns."""
        suite = ValidationTestSuite(testing_harness)
        
        results = suite.test_invalid_patterns()
        
        assert len(results) > 0
        assert all(isinstance(r, type(results[0])) for r in results)
    
    def test_conflict_scenarios(self, testing_harness):
        """Test conflict detection."""
        suite = ValidationTestSuite(testing_harness)
        
        results = suite.test_conflict_scenarios()
        
        assert len(results) > 0
        assert all(r.conflicts_detected >= 0 for r in results)


class TestTestScenario:
    """Tests for TestScenario dataclass."""
    
    def test_creation(self):
        """Test creating a test scenario."""
        scenario = TestScenario(
            name="test",
            description="Test scenario",
            selection_config=SelectionConfig(
                include_paths=[Path("/data")],
                exclude_paths=[],
                include_patterns=[],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False,
                performance_hints={}
            ),
            test_paths=[Path("/data/file.txt")],
            expected_results={Path("/data/file.txt"): True},
            tags=["test"]
        )
        
        assert scenario.name == "test"
        assert scenario.description == "Test scenario"
        assert len(scenario.test_paths) == 1
        assert len(scenario.expected_results) == 1
        assert "test" in scenario.tags


class TestIntegration:
    """Integration tests for the testing harness."""
    
    def test_complete_workflow(self, testing_harness):
        """Test complete workflow from scenario creation to reporting."""
        # Create scenario
        scenario = TestScenario(
            name="integration_test",
            description="Integration test scenario",
            selection_config=SelectionConfig(
                include_paths=[Path("/data")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.jpg", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                exclude_patterns=[
                    PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100)
                ],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False,
                performance_hints={}
            ),
            test_paths=[
                Path("/data/document.txt"),
                Path("/data/temp.tmp"),
                Path("/data/image.jpg"),
            ],
            expected_results={
                Path("/data/document.txt"): True,
                Path("/data/temp.tmp"): False,
                Path("/data/image.jpg"): True,
            },
            tags=["integration"]
        )
        
        # Add scenario
        testing_harness.add_test_scenario(scenario)
        
        # Run test
        test_result = testing_harness.run_test_scenario(scenario)
        assert test_result.passed is True
        
        # Validate
        validation_result = testing_harness.validate_scenario(scenario)
        assert validation_result is not None
        
        # Benchmark
        perf_result = testing_harness.benchmark_performance(scenario, iterations=2)
        assert perf_result.paths_per_second > 0
        
        # Generate report
        report = testing_harness.generate_test_report()
        assert "integration_test" in report
