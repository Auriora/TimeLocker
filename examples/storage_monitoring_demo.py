#!/usr/bin/env python3
"""
Storage Monitoring Demo

This example demonstrates the storage monitoring capabilities of TimeLocker,
including usage tracking, capacity warnings, deduplication/compression reporting,
and optimization recommendations.

Copyright ©  Bruce Cherrington
Licensed under GPL v3.0
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.monitoring import StorageMonitor, WarningLevel
from TimeLocker.backup_repository import BackupRepository
from TimeLocker.restic.restic_repository import ResticRepository


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def demo_storage_usage(storage_monitor: StorageMonitor, repository: BackupRepository):
    """Demonstrate storage usage tracking"""
    print_section("Storage Usage Tracking")
    
    try:
        usage = storage_monitor.get_repository_usage(repository)
        
        print(f"Repository: {usage.repository_id}")
        print(f"Used Space: {storage_monitor._format_bytes(usage.used_bytes)}")
        
        if usage.available_bytes:
            print(f"Available Space: {storage_monitor._format_bytes(usage.available_bytes)}")
        
        if usage.total_bytes:
            print(f"Total Space: {storage_monitor._format_bytes(usage.total_bytes)}")
        
        if usage.usage_percentage:
            print(f"Usage: {usage.usage_percentage:.1%}")
        
        if usage.deduplication_ratio:
            print(f"Deduplication Ratio: {usage.deduplication_ratio:.2f}x")
        
        if usage.compression_ratio:
            print(f"Compression Ratio: {usage.compression_ratio:.2f}x")
        
        print(f"Last Updated: {usage.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"Error getting storage usage: {e}")


def demo_capacity_warnings(storage_monitor: StorageMonitor, repositories: list):
    """Demonstrate capacity warning detection"""
    print_section("Capacity Warnings")
    
    try:
        warnings = storage_monitor.check_capacity_warnings(repositories)
        
        if warnings:
            print(f"Found {len(warnings)} capacity warning(s):\n")
            for warning in warnings:
                level_symbol = "⚠️" if warning.level == WarningLevel.WARNING else "🔴"
                print(f"{level_symbol} {warning.level.value.upper()}: {warning.message}")
                print(f"   Usage: {warning.usage_percentage:.1%}")
                print(f"   Used: {storage_monitor._format_bytes(warning.used_bytes)}")
                if warning.available_bytes:
                    print(f"   Available: {storage_monitor._format_bytes(warning.available_bytes)}")
                print()
        else:
            print("✓ No capacity warnings detected. All repositories have adequate space.")
        
    except Exception as e:
        print(f"Error checking capacity warnings: {e}")


def demo_storage_trends(storage_monitor: StorageMonitor, repository: BackupRepository):
    """Demonstrate storage growth trend analysis"""
    print_section("Storage Growth Trends (30 days)")
    
    try:
        trends = storage_monitor.get_storage_trends(repository, days=30)
        
        print(f"Repository: {trends.repository_id}")
        print(f"Analysis Period: {trends.start_date.strftime('%Y-%m-%d')} to {trends.end_date.strftime('%Y-%m-%d')}")
        print(f"Data Points: {len(trends.data_points)}")
        
        if trends.average_daily_growth_bytes > 0:
            daily_growth = storage_monitor._format_bytes(int(trends.average_daily_growth_bytes))
            monthly_growth = storage_monitor._format_bytes(int(trends.average_daily_growth_bytes * 30))
            print(f"Average Daily Growth: {daily_growth}")
            print(f"Estimated Monthly Growth: {monthly_growth}")
            
            if trends.projected_full_date:
                days_until_full = (trends.projected_full_date - trends.end_date).days
                print(f"Projected Full Date: {trends.projected_full_date.strftime('%Y-%m-%d')} ({days_until_full} days)")
        else:
            print("No significant growth detected in the analysis period.")
        
        if trends.data_points:
            print("\nRecent Data Points:")
            for point in trends.data_points[-5:]:  # Show last 5 points
                date_str = point['date'].strftime('%Y-%m-%d')
                size_str = storage_monitor._format_bytes(point['used_bytes'])
                print(f"  {date_str}: {size_str}")
        
    except Exception as e:
        print(f"Error analyzing storage trends: {e}")


def demo_deduplication_report(storage_monitor: StorageMonitor, repository: BackupRepository):
    """Demonstrate deduplication reporting"""
    print_section("Deduplication Report")
    
    try:
        report = storage_monitor.get_deduplication_report(repository)
        
        if 'error' in report:
            print(f"Error: {report['error']}")
            return
        
        print(f"Repository: {report['repository_id']}")
        print(f"Total Size: {report['formatted_total_size']}")
        
        if report.get('deduplication_ratio'):
            print(f"\nDeduplication:")
            print(f"  Ratio: {report['deduplication_ratio']:.2f}x")
            if 'deduplication_savings_formatted' in report:
                print(f"  Savings: {report['deduplication_savings_formatted']}")
                print(f"  Efficiency: {report['deduplication_efficiency']}")
        
        if report.get('compression_ratio'):
            print(f"\nCompression:")
            print(f"  Ratio: {report['compression_ratio']:.2f}x")
            if 'compression_savings_formatted' in report:
                print(f"  Savings: {report['compression_savings_formatted']}")
                print(f"  Efficiency: {report['compression_efficiency']}")
        
        if 'interpretation' in report:
            print(f"\nInterpretation:")
            print(f"  {report['interpretation']}")
        
    except Exception as e:
        print(f"Error generating deduplication report: {e}")


def demo_compression_report(storage_monitor: StorageMonitor, repository: BackupRepository):
    """Demonstrate compression reporting"""
    print_section("Compression Report")
    
    try:
        report = storage_monitor.get_compression_report(repository)
        
        if 'error' in report:
            print(f"Error: {report['error']}")
            return
        
        print(f"Repository: {report['repository_id']}")
        print(f"Compressed Size: {report['formatted_total_size']}")
        
        if report.get('compression_ratio'):
            print(f"Compression Ratio: {report['compression_ratio']:.2f}x")
            
            if 'uncompressed_size_formatted' in report:
                print(f"Uncompressed Size: {report['uncompressed_size_formatted']}")
                print(f"Savings: {report['compression_savings_formatted']}")
                print(f"Efficiency: {report['compression_efficiency']}")
        
        if 'interpretation' in report:
            print(f"\nInterpretation:")
            print(f"  {report['interpretation']}")
        
    except Exception as e:
        print(f"Error generating compression report: {e}")


def demo_optimization_recommendations(storage_monitor: StorageMonitor, repository: BackupRepository):
    """Demonstrate optimization recommendations"""
    print_section("Optimization Recommendations")
    
    try:
        recommendations = storage_monitor.get_optimization_recommendations(repository)
        
        if recommendations:
            print(f"Found {len(recommendations)} recommendation(s):\n")
            
            for i, rec in enumerate(recommendations, 1):
                priority_symbol = {
                    'low': 'ℹ️',
                    'medium': '⚠️',
                    'high': '🔴'
                }.get(rec.priority, '•')
                
                print(f"{i}. {priority_symbol} {rec.title} [{rec.priority.upper()}]")
                print(f"   Type: {rec.recommendation_type}")
                print(f"   {rec.description}")
                print(f"   Action: {rec.action_required}")
                
                if rec.estimated_savings_bytes:
                    savings = storage_monitor._format_bytes(rec.estimated_savings_bytes)
                    print(f"   Estimated Savings: {savings}")
                
                print()
        else:
            print("✓ No optimization recommendations at this time.")
        
    except Exception as e:
        print(f"Error generating recommendations: {e}")


def main():
    """Main demo function"""
    print("\n" + "=" * 80)
    print("  TimeLocker Storage Monitoring Demo")
    print("=" * 80)
    
    # Initialize storage monitor
    storage_monitor = StorageMonitor()
    
    # Example: Create a repository instance
    # In a real scenario, you would load this from configuration
    print("\nNote: This demo requires a configured repository.")
    print("Please ensure you have a repository set up before running this demo.\n")
    
    # Example repository configuration
    # Uncomment and modify for your environment:
    """
    repository = ResticRepository(
        name="demo-repo",
        location="/path/to/repository",
        password="your-password"
    )
    
    repositories = [repository]
    
    # Run demonstrations
    demo_storage_usage(storage_monitor, repository)
    demo_capacity_warnings(storage_monitor, repositories)
    demo_storage_trends(storage_monitor, repository)
    demo_deduplication_report(storage_monitor, repository)
    demo_compression_report(storage_monitor, repository)
    demo_optimization_recommendations(storage_monitor, repository)
    """
    
    print("\nDemo completed!")
    print("\nTo use this demo with your repository:")
    print("1. Uncomment the repository configuration section")
    print("2. Update the repository path and credentials")
    print("3. Run the demo again")


if __name__ == "__main__":
    main()
