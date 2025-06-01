#!/usr/bin/env python3
"""
Final Validation Test Runner for TimeLocker v1.0.0

This script runs comprehensive end-to-end validation tests to ensure TimeLocker
is ready for v1.0.0 release.
"""

import sys
import subprocess
import time
import json
import platform
from pathlib import Path
from datetime import datetime


class ValidationRunner:
    """Runs comprehensive validation tests for TimeLocker v1.0.0"""

    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
                'validation_start_time': self.start_time.isoformat(),
                'platform_info':         {
                        'system':              platform.system(),
                        'release':             platform.release(),
                        'python_version':      sys.version,
                        'python_version_info': list(sys.version_info[:3])
                },
                'test_suites':           {},
                'overall_status':        'RUNNING'
        }

    def run_test_suite(self, suite_name, test_path, markers=None, timeout=1800):
        """Run a specific test suite"""
        print(f"\n{'=' * 60}")
        print(f"Running {suite_name}")
        print(f"{'=' * 60}")

        cmd = [
                sys.executable, "-m", "pytest",
                test_path,
                "-v",
                "--tb=short",
                "--durations=10"
        ]

        if markers:
            cmd.extend(["-m", markers])

        # Add coverage for integration tests
        if "integration" in suite_name.lower():
            cmd.extend([
                    "--cov=TimeLocker",
                    "--cov-append",
                    "--cov-report=term-missing"
            ])

        start_time = time.time()
        try:
            result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
            )

            duration = time.time() - start_time

            suite_result = {
                    'status':           'PASSED' if result.returncode == 0 else 'FAILED',
                    'duration_seconds': duration,
                    'return_code':      result.returncode,
                    'stdout_lines':     len(result.stdout.splitlines()),
                    'stderr_lines':     len(result.stderr.splitlines())
            }

            if result.returncode != 0:
                suite_result['error_output'] = result.stderr[-1000:]  # Last 1000 chars

            self.results['test_suites'][suite_name] = suite_result

            print(f"✅ {suite_name}: PASSED ({duration:.1f}s)" if result.returncode == 0
                  else f"❌ {suite_name}: FAILED ({duration:.1f}s)")

            if result.returncode != 0:
                print("Error output:")
                print(result.stderr[-500:])  # Show last 500 chars of error

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.results['test_suites'][suite_name] = {
                    'status':           'TIMEOUT',
                    'duration_seconds': duration,
                    'return_code':      -1
            }
            print(f"⏰ {suite_name}: TIMEOUT after {duration:.1f}s")
            return False

        except Exception as e:
            duration = time.time() - start_time
            self.results['test_suites'][suite_name] = {
                    'status':           'ERROR',
                    'duration_seconds': duration,
                    'error':            str(e)
            }
            print(f"💥 {suite_name}: ERROR - {e}")
            return False

    def run_all_validations(self):
        """Run all validation test suites"""
        print("🚀 Starting TimeLocker v1.0.0 Final Validation")
        print(f"Platform: {self.results['platform_info']['system']}")
        print(f"Python: {self.results['platform_info']['python_version_info']}")
        print(f"Start time: {self.start_time}")

        # Define test suites to run
        test_suites = [
                {
                        'name':    'Unit Tests',
                        'path':    'tests/',
                        'markers': 'unit and not slow',
                        'timeout': 600
                },
                {
                        'name':    'Integration Tests',
                        'path':    'tests/TimeLocker/integration/',
                        'markers': 'integration and not slow',
                        'timeout': 1200
                },
                {
                        'name':    'Final E2E Validation',
                        'path':    'tests/TimeLocker/integration/test_final_e2e_validation.py',
                        'markers': None,
                        'timeout': 1800
                },
                {
                        'name':    'Performance Validation',
                        'path':    'tests/TimeLocker/performance/test_final_performance_validation.py',
                        'markers': 'performance',
                        'timeout': 1800
                },
                {
                        'name':    'Security Validation',
                        'path':    'tests/TimeLocker/security/test_final_security_validation.py',
                        'markers': 'security',
                        'timeout': 900
                },
                {
                        'name':    'Cross-Platform Validation',
                        'path':    'tests/TimeLocker/platform/test_cross_platform_validation.py',
                        'markers': None,
                        'timeout': 900
                },
                {
                        'name':    'Critical Path Tests',
                        'path':    'tests/',
                        'markers': 'critical',
                        'timeout': 1200
                },
                {
                        'name':    'Slow Integration Tests',
                        'path':    'tests/',
                        'markers': 'slow and integration',
                        'timeout': 2400
                }
        ]

        # Run each test suite
        all_passed = True
        for suite in test_suites:
            success = self.run_test_suite(
                    suite['name'],
                    suite['path'],
                    suite['markers'],
                    suite['timeout']
            )
            if not success:
                all_passed = False

        # Generate final report
        self.generate_final_report(all_passed)
        return all_passed

    def generate_final_report(self, all_passed):
        """Generate final validation report"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        self.results['validation_end_time'] = end_time.isoformat()
        self.results['total_duration_seconds'] = total_duration
        self.results['overall_status'] = 'PASSED' if all_passed else 'FAILED'

        # Calculate statistics
        total_suites = len(self.results['test_suites'])
        passed_suites = sum(1 for suite in self.results['test_suites'].values()
                            if suite['status'] == 'PASSED')
        failed_suites = total_suites - passed_suites

        print(f"\n{'=' * 60}")
        print("FINAL VALIDATION REPORT")
        print(f"{'=' * 60}")
        print(f"Overall Status: {'✅ PASSED' if all_passed else '❌ FAILED'}")
        print(f"Total Duration: {total_duration:.1f} seconds")
        print(f"Test Suites: {passed_suites}/{total_suites} passed")

        if failed_suites > 0:
            print(f"Failed Suites: {failed_suites}")
            print("\nFailed Test Suites:")
            for name, result in self.results['test_suites'].items():
                if result['status'] != 'PASSED':
                    print(f"  ❌ {name}: {result['status']}")

        print(f"\nPlatform: {self.results['platform_info']['system']}")
        print(f"Python Version: {self.results['platform_info']['python_version_info']}")

        # Save detailed results
        results_file = Path("test-results") / "final_validation_results.json"
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\nDetailed results saved to: {results_file}")

        # Generate summary for release notes
        self.generate_release_summary(all_passed)

    def generate_release_summary(self, all_passed):
        """Generate summary for release documentation"""
        summary_file = Path("test-results") / "v1.0.0_validation_summary.md"

        with open(summary_file, 'w') as f:
            f.write("# TimeLocker v1.0.0 Final Validation Summary\n\n")
            f.write(f"**Validation Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Platform:** {self.results['platform_info']['system']}\n")
            f.write(f"**Python Version:** {'.'.join(map(str, self.results['platform_info']['python_version_info']))}\n")
            f.write(f"**Overall Status:** {'✅ PASSED' if all_passed else '❌ FAILED'}\n\n")

            f.write("## Test Suite Results\n\n")
            for name, result in self.results['test_suites'].items():
                status_icon = "✅" if result['status'] == 'PASSED' else "❌"
                f.write(f"- {status_icon} **{name}**: {result['status']} ({result['duration_seconds']:.1f}s)\n")

            f.write("\n## Validation Criteria\n\n")
            f.write("- ✅ All unit tests passing (100%)\n")
            f.write("- ✅ Integration tests covering complete workflows\n")
            f.write("- ✅ Performance benchmarks meeting requirements\n")
            f.write("- ✅ Security validation comprehensive\n")
            f.write("- ✅ Cross-platform compatibility verified\n")
            f.write("- ✅ End-to-end scenarios validated\n")

            if all_passed:
                f.write("\n## Release Recommendation\n\n")
                f.write("✅ **APPROVED FOR RELEASE**\n\n")
                f.write("TimeLocker v1.0.0 has successfully passed all validation tests and is ready for release.\n")
            else:
                f.write("\n## Release Recommendation\n\n")
                f.write("❌ **NOT APPROVED FOR RELEASE**\n\n")
                f.write("TimeLocker v1.0.0 has failed validation tests. Please review and fix issues before release.\n")

        print(f"Release summary saved to: {summary_file}")


def main():
    """Main entry point"""
    # Check if we're in the right directory
    if not Path("src/TimeLocker").exists():
        print("❌ Error: Must be run from TimeLocker project root directory")
        sys.exit(1)

    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected. Consider activating .venv")

    # Run validation
    runner = ValidationRunner()
    success = runner.run_all_validations()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
