#!/usr/bin/env python3
"""
Performance optimization script for TimeLocker

This script runs performance benchmarks, identifies bottlenecks, and provides
optimization recommendations.
"""

import sys
import argparse
import logging
from pathlib import Path
import json
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.performance.benchmarks import PerformanceBenchmarks
from TimeLocker.performance.profiler import get_performance_summary
from TimeLocker.performance.metrics import get_global_performance_summary


def setup_logging(verbose: bool = False):
    """Set up logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_performance_benchmarks(output_file: Path = None, verbose: bool = False):
    """Run comprehensive performance benchmarks"""
    print("Running TimeLocker Performance Benchmarks...")
    print("=" * 50)

    with PerformanceBenchmarks() as benchmarks:
        # Run all benchmarks
        start_time = time.time()
        results = benchmarks.run_all_benchmarks()
        total_time = time.time() - start_time

        # Generate report
        report = benchmarks.generate_performance_report(results)
        print(report)

        # Add timing information
        print(f"Total benchmark time: {total_time:.2f} seconds")
        print()

        # Save results if requested
        if output_file:
            results['benchmark_metadata'] = {
                    'total_time': total_time,
                    'timestamp':  time.time()
            }

            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Detailed results saved to: {output_file}")

        return results


def analyze_performance_metrics():
    """Analyze global performance metrics"""
    print("Performance Metrics Analysis")
    print("=" * 30)

    # Get metrics for different operation types
    operation_types = [
            "get_effective_paths",
            "estimate_backup_size",
            "backup_with_retry",
            "large_directory_scan"
    ]

    for op_type in operation_types:
        summary = get_global_performance_summary(op_type)
        if summary:
            print(f"\n{op_type}:")
            print(f"  Operations: {summary.get('operation_count', 0)}")
            print(f"  Avg duration: {summary.get('avg_duration_seconds', 0):.4f}s")
            print(f"  Total files: {summary.get('total_files_processed', 0):,}")
            print(f"  Total bytes: {summary.get('total_bytes_processed', 0):,}")

            if 'avg_throughput_files_per_sec' in summary:
                print(f"  Avg throughput: {summary['avg_throughput_files_per_sec']:.1f} files/sec")
        else:
            print(f"\n{op_type}: No metrics available")


def check_performance_regressions(baseline_file: Path):
    """Check for performance regressions against baseline"""
    if not baseline_file.exists():
        print(f"Baseline file not found: {baseline_file}")
        return False

    print("Checking for Performance Regressions...")
    print("=" * 40)

    # Load baseline
    with open(baseline_file, 'r') as f:
        baseline = json.load(f)

    # Run current benchmarks
    with PerformanceBenchmarks() as benchmarks:
        current = benchmarks.run_all_benchmarks()

    # Compare key metrics
    regressions = []
    improvements = []

    # Pattern matching comparison
    if 'pattern_matching' in baseline and 'pattern_matching' in current:
        baseline_speedup = baseline['pattern_matching'].get('speedup_factor', 1.0)
        current_speedup = current['pattern_matching'].get('speedup_factor', 1.0)

        if current_speedup < baseline_speedup * 0.8:  # 20% regression threshold
            regressions.append(f"Pattern matching speedup decreased: {baseline_speedup:.2f}x -> {current_speedup:.2f}x")
        elif current_speedup > baseline_speedup * 1.2:  # 20% improvement threshold
            improvements.append(f"Pattern matching speedup improved: {baseline_speedup:.2f}x -> {current_speedup:.2f}x")

    # File traversal comparison
    if 'file_traversal' in baseline and 'file_traversal' in current:
        baseline_throughput = baseline['file_traversal'].get('throughput_files_per_sec', 0)
        current_throughput = current['file_traversal'].get('throughput_files_per_sec', 0)

        if current_throughput < baseline_throughput * 0.8:
            regressions.append(f"File traversal throughput decreased: {baseline_throughput:.1f} -> {current_throughput:.1f} files/sec")
        elif current_throughput > baseline_throughput * 1.2:
            improvements.append(f"File traversal throughput improved: {baseline_throughput:.1f} -> {current_throughput:.1f} files/sec")

    # Report results
    if regressions:
        print("⚠️  Performance Regressions Detected:")
        for regression in regressions:
            print(f"  - {regression}")
        print()

    if improvements:
        print("✅ Performance Improvements:")
        for improvement in improvements:
            print(f"  - {improvement}")
        print()

    if not regressions and not improvements:
        print("✅ No significant performance changes detected")

    return len(regressions) == 0


def generate_optimization_recommendations(results: dict):
    """Generate optimization recommendations based on benchmark results"""
    print("Optimization Recommendations")
    print("=" * 30)

    recommendations = []

    # Pattern matching analysis
    pm = results.get('pattern_matching', {})
    if pm.get('speedup_factor', 0) < 2.0:
        recommendations.append(
                "Consider further optimizing pattern matching algorithms. "
                "Current speedup is less than 2x."
        )

    # File traversal analysis
    ft = results.get('file_traversal', {})
    if ft.get('throughput_files_per_sec', 0) < 500:
        recommendations.append(
                "File traversal throughput is below 500 files/sec. "
                "Consider optimizing directory walking or file filtering."
        )

    # Large directory analysis
    ld = results.get('large_directory', {})
    if ld.get('throughput_files_per_sec', 0) < 200:
        recommendations.append(
                "Large directory performance is below 200 files/sec. "
                "Consider implementing parallel processing or better caching."
        )

    # Memory usage analysis
    profiler_summary = results.get('profiler_summary', {})
    if profiler_summary.get('max_peak_memory_mb', 0) > 500:
        recommendations.append(
                "Peak memory usage exceeds 500MB. "
                "Consider implementing streaming or chunked processing."
        )

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print("✅ No specific optimization recommendations at this time.")
        print("   Performance appears to be within acceptable ranges.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="TimeLocker Performance Optimization Tool")
    parser.add_argument('--benchmark', action='store_true',
                        help='Run performance benchmarks')
    parser.add_argument('--analyze', action='store_true',
                        help='Analyze performance metrics')
    parser.add_argument('--check-regression', type=Path,
                        help='Check for regressions against baseline file')
    parser.add_argument('--output', type=Path,
                        help='Output file for benchmark results')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    setup_logging(args.verbose)

    if not any([args.benchmark, args.analyze, args.check_regression]):
        # Default: run benchmarks
        args.benchmark = True

    results = None

    if args.benchmark:
        results = run_performance_benchmarks(args.output, args.verbose)
        print()

    if args.analyze:
        analyze_performance_metrics()
        print()

    if args.check_regression:
        success = check_performance_regressions(args.check_regression)
        if not success:
            sys.exit(1)
        print()

    if results:
        generate_optimization_recommendations(results)


if __name__ == '__main__':
    main()
