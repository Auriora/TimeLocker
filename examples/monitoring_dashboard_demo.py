#!/usr/bin/env python3
"""
Monitoring Dashboard Demo

Demonstrates the comprehensive monitoring dashboard with all widgets:
- Health overview widget
- Backup history widget
- Storage usage widget
- Performance trends widget
- Troubleshooting widget

Requirements: 7.1, 7.2, 7.3, 7.5, 9.1, 9.2
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.monitoring import (
    MonitoringService,
    MonitoringDashboard,
    BackupEvent,
    StatusLevel,
    HistoryFilters,
    BackupStatus
)
from TimeLocker.backup_repository import BackupRepository


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_widget_data(widget_name: str, data: dict):
    """Print widget data in formatted JSON"""
    print(f"\n{widget_name}:")
    print(json.dumps(data, indent=2, default=str))


def main():
    """Demonstrate monitoring dashboard functionality"""
    print_section("Monitoring Dashboard Demo")
    
    # Initialize monitoring service
    config_dir = Path.home() / ".config" / "timelocker-demo" / "monitoring"
    monitoring_service = MonitoringService(config_dir)
    
    # Initialize dashboard
    dashboard = MonitoringDashboard(monitoring_service)
    
    print("✓ Monitoring dashboard initialized")
    
    # Simulate some backup events for demonstration
    print("\nSimulating backup events...")
    
    # Create mock repositories
    repositories = []
    for i in range(3):
        repo = BackupRepository(
            name=f"test-repo-{i+1}",
            uri=f"/tmp/test-repo-{i+1}",
            password="test-password"
        )
        repositories.append(repo)
    
    # Simulate backup events
    for i, repo in enumerate(repositories):
        event = BackupEvent(
            event_id=f"event_{i}",
            event_type="backup_completed",
            timestamp=datetime.now() - timedelta(hours=i),
            repository_id=repo.name,
            operation_id=f"op_{i}",
            message=f"Backup completed successfully for {repo.name}",
            details={
                'files_processed': 1000 + (i * 100),
                'bytes_processed': 1024 * 1024 * (100 + i * 10),
                'start_time': (datetime.now() - timedelta(hours=i, minutes=30)).isoformat(),
                'end_time': (datetime.now() - timedelta(hours=i)).isoformat(),
                'duration': 1800
            },
            severity=StatusLevel.SUCCESS
        )
        monitoring_service.handle_backup_event(event)
    
    print("✓ Simulated backup events")
    
    # Demo 1: Health Overview Widget
    print_section("1. Health Overview Widget")
    print("Displays system health, repository status, and recent activity")
    
    health_widget = dashboard.render_health_overview(repositories)
    print_widget_data("Health Overview", health_widget.to_dict())
    
    # Demo 2: Backup History Widget
    print_section("2. Backup History Widget")
    print("Shows backup history with filtering and search capabilities")
    
    # Show all backups
    history_widget = dashboard.render_backup_history(limit=10)
    print_widget_data("Backup History (All)", history_widget.to_dict())
    
    # Show filtered backups
    filters = HistoryFilters(
        repository_id="test-repo-1",
        status=BackupStatus.SUCCESS,
        limit=5
    )
    filtered_widget = dashboard.render_backup_history(filters)
    print_widget_data("Backup History (Filtered)", filtered_widget.to_dict())
    
    # Demo 3: Storage Usage Widget
    print_section("3. Storage Usage Widget")
    print("Visualizes storage usage across all repositories")
    
    storage_widget = dashboard.render_storage_usage(repositories)
    print_widget_data("Storage Usage", storage_widget.to_dict())
    
    # Demo 4: Performance Trends Widget
    print_section("4. Performance Trends Widget")
    print("Shows performance trends and optimization recommendations")
    
    performance_widget = dashboard.render_performance_trends(repositories, days=30)
    print_widget_data("Performance Trends", performance_widget.to_dict())
    
    # Demo 5: Troubleshooting Widget
    print_section("5. Troubleshooting Widget")
    print("Displays detected issues and troubleshooting guidance")
    
    troubleshooting_widget = dashboard.render_troubleshooting_panel(time_window_days=7)
    print_widget_data("Troubleshooting", troubleshooting_widget.to_dict())
    
    # Demo 6: Navigation Links
    print_section("6. Navigation Links")
    print("Easy navigation between dashboard views")
    
    nav_links = dashboard.get_navigation_links()
    for view, description in nav_links.items():
        print(f"  {view:20s} - {description}")
    
    # Summary
    print_section("Dashboard Demo Complete")
    print("The monitoring dashboard provides comprehensive visibility into:")
    print("  ✓ System health and repository status")
    print("  ✓ Backup history with filtering")
    print("  ✓ Storage usage and capacity warnings")
    print("  ✓ Performance trends and anomalies")
    print("  ✓ Issue detection and troubleshooting guidance")
    print("  ✓ Easy navigation between views")
    print("\nAll widgets support:")
    print("  • Real-time data from monitoring service")
    print("  • User-friendly formatting")
    print("  • Actionable recommendations")
    print("  • Integration with existing monitoring components")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
