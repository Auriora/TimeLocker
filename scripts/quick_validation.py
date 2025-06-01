#!/usr/bin/env python3
"""
Quick Validation Script for TimeLocker v1.0.0

Runs the most critical tests to validate release readiness.
"""

import sys
import subprocess
import time
from pathlib import Path


def run_test_suite(name, test_path, timeout=300):
    """Run a specific test suite"""
    print(f"\n{'=' * 60}")
    print(f"Running {name}")
    print(f"{'=' * 60}")

    cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "-x"  # Stop on first failure
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ {name}: PASSED ({duration:.1f}s)")
            return True
        else:
            print(f"❌ {name}: FAILED ({duration:.1f}s)")
            print("Error output:")
            print(result.stderr[-500:])  # Last 500 chars
            return False

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"⏰ {name}: TIMEOUT after {duration:.1f}s")
        return False

    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 {name}: ERROR - {e}")
        return False


def main():
    """Run quick validation"""
    print("🚀 TimeLocker v1.0.0 Quick Validation")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Critical test suites
    test_suites = [
            {
                    'name':    'Core Unit Tests',
                    'path':    'tests/TimeLocker/backup/test_enhanced_backup_operations.py',
                    'timeout': 120
            },
            {
                    'name':    'Security Validation',
                    'path':    'tests/TimeLocker/security/test_final_security_validation.py::TestFinalSecurityValidation::test_encryption_end_to_end_validation',
                    'timeout': 60
            },
            {
                    'name':    'E2E Memory Test',
                    'path':    'tests/TimeLocker/integration/test_final_e2e_validation.py::TestFinalE2EValidation::test_memory_usage_monitoring',
                    'timeout': 120
            },
            {
                    'name':    'Cross-Platform Test',
                    'path':    'tests/TimeLocker/platform/test_cross_platform_validation.py::TestCrossPlatformValidation::test_file_path_handling_cross_platform',
                    'timeout': 60
            },
            {
                    'name':    'Integration Service',
                    'path':    'tests/TimeLocker/integration/test_integration_service.py::TestIntegrationService::test_initialization',
                    'timeout': 60
            }
    ]

    # Run test suites
    results = []
    for suite in test_suites:
        success = run_test_suite(
                suite['name'],
                suite['path'],
                suite['timeout']
        )
        results.append((suite['name'], success))

    # Generate summary
    print(f"\n{'=' * 60}")
    print("QUICK VALIDATION SUMMARY")
    print(f"{'=' * 60}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")

    print(f"\nOverall: {passed}/{total} test suites passed")

    if passed == total:
        print("🎉 QUICK VALIDATION: PASSED")
        print("TimeLocker v1.0.0 is ready for release!")
        return 0
    else:
        print("⚠️  QUICK VALIDATION: FAILED")
        print("Some critical tests failed. Review before release.")
        return 1


if __name__ == "__main__":
    # Check if we're in the right directory
    if not Path("src/TimeLocker").exists():
        print("❌ Error: Must be run from TimeLocker project root directory")
        sys.exit(1)

    sys.exit(main())
