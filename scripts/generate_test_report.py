#!/usr/bin/env python3
"""
Test Report Generator for TimeLocker v1.0.0

Generates comprehensive test reports including coverage, performance metrics,
and validation status for release documentation.
"""

import sys
import subprocess
import json
import time
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class TestReportGenerator:
    """Generates comprehensive test reports for TimeLocker"""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("test-results")
        self.output_dir.mkdir(exist_ok=True)

        self.report_data = {
                'generation_time':     datetime.now().isoformat(),
                'platform_info':       {
                        'system':              platform.system(),
                        'release':             platform.release(),
                        'python_version':      sys.version,
                        'python_version_info': list(sys.version_info[:3])
                },
                'test_results':        {},
                'coverage_data':       {},
                'performance_metrics': {},
                'validation_status':   {}
        }

    def run_test_suite(self, name: str, test_path: str, markers: str = None) -> Dict[str, Any]:
        """Run a test suite and collect results"""
        print(f"Running {name}...")

        cmd = [
                sys.executable, "-m", "pytest",
                test_path,
                "-v",
                "--tb=short",
                "--json-report",
                f"--json-report-file={self.output_dir / f'{name.lower().replace(' ', '_')}_report.json'}"
        ]

        if markers:
            cmd.extend(["-m", markers])

        start_time = time.time()
        try:
            result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=1800  # 30 minutes
            )

            duration = time.time() - start_time

            # Load JSON report if available
            json_report_file = self.output_dir / f'{name.lower().replace(" ", "_")}_report.json'
            json_data = {}
            if json_report_file.exists():
                try:
                    with open(json_report_file, 'r') as f:
                        json_data = json.load(f)
                except json.JSONDecodeError:
                    pass

            return {
                    'name':            name,
                    'status':          'PASSED' if result.returncode == 0 else 'FAILED',
                    'duration':        duration,
                    'return_code':     result.returncode,
                    'tests_collected': json_data.get('summary', {}).get('collected', 0),
                    'tests_passed':    json_data.get('summary', {}).get('passed', 0),
                    'tests_failed':    json_data.get('summary', {}).get('failed', 0),
                    'tests_skipped':   json_data.get('summary', {}).get('skipped', 0),
                    'json_report':     json_data
            }

        except subprocess.TimeoutExpired:
            return {
                    'name':        name,
                    'status':      'TIMEOUT',
                    'duration':    time.time() - start_time,
                    'return_code': -1,
                    'error':       'Test suite timed out'
            }
        except Exception as e:
            return {
                    'name':     name,
                    'status':   'ERROR',
                    'duration': time.time() - start_time,
                    'error':    str(e)
            }

    def run_coverage_analysis(self) -> Dict[str, Any]:
        """Run coverage analysis"""
        print("Running coverage analysis...")

        cmd = [
                sys.executable, "-m", "pytest",
                "tests/",
                "--cov=TimeLocker",
                "--cov-report=json",
                f"--cov-report=json:{self.output_dir / 'coverage.json'}",
                "--cov-report=html",
                f"--cov-report=html:{self.output_dir / 'coverage_html'}",
                "-q"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            # Load coverage data
            coverage_file = self.output_dir / 'coverage.json'
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)

                return {
                        'status':           'SUCCESS',
                        'overall_coverage': coverage_data.get('totals', {}).get('percent_covered', 0),
                        'lines_covered':    coverage_data.get('totals', {}).get('covered_lines', 0),
                        'lines_total':      coverage_data.get('totals', {}).get('num_statements', 0),
                        'files_analyzed':   len(coverage_data.get('files', {})),
                        'detailed_data':    coverage_data
                }
            else:
                return {
                        'status': 'FAILED',
                        'error':  'Coverage report not generated'
                }

        except Exception as e:
            return {
                    'status': 'ERROR',
                    'error':  str(e)
            }

    def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics from test runs"""
        print("Collecting performance metrics...")

        # Run performance benchmarks
        cmd = [
                sys.executable, "-m", "pytest",
                "tests/TimeLocker/performance/",
                "-v",
                "--benchmark-json",
                f"{self.output_dir / 'benchmark_results.json'}"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

            # Load benchmark data
            benchmark_file = self.output_dir / 'benchmark_results.json'
            if benchmark_file.exists():
                with open(benchmark_file, 'r') as f:
                    benchmark_data = json.load(f)

                return {
                        'status':         'SUCCESS',
                        'benchmark_data': benchmark_data,
                        'machine_info':   benchmark_data.get('machine_info', {}),
                        'commit_info':    benchmark_data.get('commit_info', {})
                }
            else:
                return {
                        'status':  'NO_BENCHMARKS',
                        'message': 'No benchmark data available'
                }

        except Exception as e:
            return {
                    'status': 'ERROR',
                    'error':  str(e)
            }

    def generate_comprehensive_report(self) -> None:
        """Generate comprehensive test report"""
        print("🚀 Generating TimeLocker v1.0.0 Test Report")
        print(f"Start time: {datetime.now()}")

        # Define test suites to analyze
        test_suites = [
                {
                        'name':    'Unit Tests',
                        'path':    'tests/',
                        'markers': 'unit and not slow'
                },
                {
                        'name':    'Integration Tests',
                        'path':    'tests/TimeLocker/integration/',
                        'markers': 'integration and not slow'
                },
                {
                        'name':    'Security Tests',
                        'path':    'tests/TimeLocker/security/',
                        'markers': 'security'
                },
                {
                        'name':    'Performance Tests',
                        'path':    'tests/TimeLocker/performance/',
                        'markers': 'performance'
                },
                {
                        'name':    'Cross-Platform Tests',
                        'path':    'tests/TimeLocker/platform/',
                        'markers': None
                },
                {
                        'name':    'Regression Tests',
                        'path':    'tests/TimeLocker/regression/',
                        'markers': 'regression'
                },
                {
                        'name':    'Final E2E Validation',
                        'path':    'tests/TimeLocker/integration/test_final_e2e_validation.py',
                        'markers': None
                }
        ]

        # Run test suites
        for suite in test_suites:
            result = self.run_test_suite(
                    suite['name'],
                    suite['path'],
                    suite['markers']
            )
            self.report_data['test_results'][suite['name']] = result

        # Run coverage analysis
        self.report_data['coverage_data'] = self.run_coverage_analysis()

        # Collect performance metrics
        self.report_data['performance_metrics'] = self.collect_performance_metrics()

        # Generate validation status
        self.generate_validation_status()

        # Save comprehensive report
        self.save_reports()

    def generate_validation_status(self) -> None:
        """Generate overall validation status"""
        test_results = self.report_data['test_results']

        total_suites = len(test_results)
        passed_suites = sum(1 for result in test_results.values() if result['status'] == 'PASSED')

        total_tests = sum(result.get('tests_collected', 0) for result in test_results.values())
        passed_tests = sum(result.get('tests_passed', 0) for result in test_results.values())
        failed_tests = sum(result.get('tests_failed', 0) for result in test_results.values())

        coverage_percent = self.report_data['coverage_data'].get('overall_coverage', 0)

        # Determine overall status
        if passed_suites == total_suites and failed_tests == 0 and coverage_percent >= 80:
            overall_status = 'READY_FOR_RELEASE'
        elif passed_suites >= total_suites * 0.9 and coverage_percent >= 70:
            overall_status = 'MOSTLY_READY'
        else:
            overall_status = 'NEEDS_WORK'

        self.report_data['validation_status'] = {
                'overall_status':     overall_status,
                'test_suite_summary': {
                        'total_suites':  total_suites,
                        'passed_suites': passed_suites,
                        'failed_suites': total_suites - passed_suites,
                        'success_rate':  (passed_suites / total_suites * 100) if total_suites > 0 else 0
                },
                'test_summary':       {
                        'total_tests':  total_tests,
                        'passed_tests': passed_tests,
                        'failed_tests': failed_tests,
                        'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
                },
                'coverage_summary':   {
                        'overall_coverage': coverage_percent,
                        'coverage_status':  'GOOD' if coverage_percent >= 80 else 'NEEDS_IMPROVEMENT'
                }
        }

    def save_reports(self) -> None:
        """Save all generated reports"""
        # Save JSON report
        json_report_file = self.output_dir / 'comprehensive_test_report.json'
        with open(json_report_file, 'w') as f:
            json.dump(self.report_data, f, indent=2)

        # Generate markdown report
        self.generate_markdown_report()

        # Generate HTML summary
        self.generate_html_summary()

        print(f"\n📊 Reports generated:")
        print(f"  - JSON Report: {json_report_file}")
        print(f"  - Markdown Report: {self.output_dir / 'test_report.md'}")
        print(f"  - HTML Summary: {self.output_dir / 'test_summary.html'}")

    def generate_markdown_report(self) -> None:
        """Generate markdown test report"""
        report_file = self.output_dir / 'test_report.md'

        with open(report_file, 'w') as f:
            f.write("# TimeLocker v1.0.0 Comprehensive Test Report\n\n")
            f.write(f"**Generated:** {self.report_data['generation_time']}\n")
            f.write(f"**Platform:** {self.report_data['platform_info']['system']}\n")
            f.write(f"**Python:** {'.'.join(map(str, self.report_data['platform_info']['python_version_info']))}\n\n")

            # Overall status
            status = self.report_data['validation_status']['overall_status']
            status_emoji = "✅" if status == "READY_FOR_RELEASE" else "⚠️" if status == "MOSTLY_READY" else "❌"
            f.write(f"## Overall Status: {status_emoji} {status.replace('_', ' ')}\n\n")

            # Test suite results
            f.write("## Test Suite Results\n\n")
            for name, result in self.report_data['test_results'].items():
                status_icon = "✅" if result['status'] == 'PASSED' else "❌"
                f.write(f"- {status_icon} **{name}**: {result['status']} ")
                f.write(f"({result.get('tests_passed', 0)}/{result.get('tests_collected', 0)} tests, ")
                f.write(f"{result['duration']:.1f}s)\n")

            # Coverage summary
            coverage = self.report_data['coverage_data']
            if coverage.get('status') == 'SUCCESS':
                f.write(f"\n## Code Coverage\n\n")
                f.write(f"- **Overall Coverage:** {coverage['overall_coverage']:.1f}%\n")
                f.write(f"- **Lines Covered:** {coverage['lines_covered']}/{coverage['lines_total']}\n")
                f.write(f"- **Files Analyzed:** {coverage['files_analyzed']}\n")

            # Validation summary
            validation = self.report_data['validation_status']
            f.write(f"\n## Validation Summary\n\n")
            f.write(f"- **Test Suites:** {validation['test_suite_summary']['passed_suites']}/{validation['test_suite_summary']['total_suites']} passed\n")
            f.write(f"- **Individual Tests:** {validation['test_summary']['passed_tests']}/{validation['test_summary']['total_tests']} passed\n")
            f.write(f"- **Success Rate:** {validation['test_summary']['success_rate']:.1f}%\n")

    def generate_html_summary(self) -> None:
        """Generate HTML summary report"""
        html_file = self.output_dir / 'test_summary.html'

        status = self.report_data['validation_status']['overall_status']
        status_color = "#28a745" if status == "READY_FOR_RELEASE" else "#ffc107" if status == "MOSTLY_READY" else "#dc3545"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>TimeLocker v1.0.0 Test Summary</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .status {{ padding: 20px; border-radius: 5px; background-color: {status_color}; color: white; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>TimeLocker v1.0.0 Test Summary</h1>
    <div class="status">
        <h2>Status: {status.replace('_', ' ')}</h2>
        <p>Generated: {self.report_data['generation_time']}</p>
    </div>
    
    <h2>Test Results</h2>
    <table>
        <tr><th>Test Suite</th><th>Status</th><th>Tests</th><th>Duration</th></tr>
"""

        for name, result in self.report_data['test_results'].items():
            status_class = "passed" if result['status'] == 'PASSED' else "failed"
            html_content += f"""
        <tr>
            <td>{name}</td>
            <td class="{status_class}">{result['status']}</td>
            <td>{result.get('tests_passed', 0)}/{result.get('tests_collected', 0)}</td>
            <td>{result['duration']:.1f}s</td>
        </tr>
"""

        html_content += """
    </table>
</body>
</html>
"""

        with open(html_file, 'w') as f:
            f.write(html_content)


def main():
    """Main entry point"""
    if not Path("src/TimeLocker").exists():
        print("❌ Error: Must be run from TimeLocker project root directory")
        sys.exit(1)

    generator = TestReportGenerator()
    generator.generate_comprehensive_report()

    # Print summary
    validation = generator.report_data['validation_status']
    print(f"\n📋 Test Report Summary:")
    print(f"  Overall Status: {validation['overall_status']}")
    print(f"  Test Suites: {validation['test_suite_summary']['passed_suites']}/{validation['test_suite_summary']['total_suites']} passed")
    print(f"  Individual Tests: {validation['test_summary']['passed_tests']}/{validation['test_summary']['total_tests']} passed")
    print(f"  Coverage: {validation['coverage_summary']['overall_coverage']:.1f}%")


if __name__ == "__main__":
    main()
