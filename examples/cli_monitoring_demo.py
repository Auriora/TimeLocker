#!/usr/bin/env python3
"""
CLI Monitoring Integration Demo

This script demonstrates the CLI monitoring integration functionality,
showing how to access monitoring data, logs, and status information
through the CLI service manager.

Requirements addressed: 8.1, 8.2, 8.3
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.cli_services import get_cli_service_manager
from TimeLocker.cli_modules.monitoring_integration import CLIMonitoringIntegration, CLIMonitoringFilters


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_system_status():
    """Demonstrate system status retrieval."""
    print_section("System Status")
    
    try:
        service_manager = get_cli_service_manager()
        status = service_manager.get_system_monitoring_status()
        
        print(f"Health Status: {status.get('health_status', 'unknown')}")
        print(f"Current Operations: {status.get('current_operations', 0)}")
        print(f"Recent Operations (24h): {status.get('recent_operations_24h', 0)}")
        
        status_counts = status.get('status_counts', {})
        if status_counts:
            print("\nStatus Breakdown:")
            for status_type, count in status_counts.items():
                print(f"  {status_type}: {count}")
        
        print(f"\nTimestamp: {status.get('timestamp', 'N/A')}")
        
    except Exception as e:
        print(f"Error getting system status: {e}")


def demo_current_operations():
    """Demonstrate current operations retrieval."""
    print_section("Current Operations")
    
    try:
        service_manager = get_cli_service_manager()
        operations = service_manager.get_cli_current_operations()
        
        if not operations:
            print("No operations currently running")
            return
        
        print(f"Found {len(operations)} current operation(s):\n")
        
        for op in operations:
            print(f"Operation ID: {op['operation_id']}")
            print(f"  Type: {op['operation_type']}")
            print(f"  Status: {op['status']}")
            print(f"  Message: {op['message']}")
            
            if op.get('progress') is not None:
                print(f"  Progress: {op['progress']}%")
            
            if op.get('repository_id'):
                print(f"  Repository: {op['repository_id']}")
            
            print()
        
    except Exception as e:
        print(f"Error getting current operations: {e}")


def demo_monitoring_logs():
    """Demonstrate monitoring logs retrieval with filtering."""
    print_section("Monitoring Logs")
    
    try:
        service_manager = get_cli_service_manager()
        
        # Get recent logs (last 24 hours, limit to 10)
        logs = service_manager.get_cli_monitoring_logs(
            hours=24,
            limit=10
        )
        
        if not logs:
            print("No logs found")
            return
        
        print(f"Found {len(logs)} log entries:\n")
        
        # Get monitoring integration for formatting
        monitoring_integration = service_manager.get_monitoring_integration()
        
        for log in logs[:5]:  # Show first 5
            if monitoring_integration:
                formatted = monitoring_integration.format_log_entry_cli(log, verbose=False)
                print(formatted)
            else:
                # Fallback formatting
                timestamp = log.get('timestamp', 'N/A')
                level = log.get('level', 'INFO').upper()
                message = log.get('message', '')
                print(f"[{level}] {timestamp} - {message}")
            
            print()
        
        if len(logs) > 5:
            print(f"... and {len(logs) - 5} more entries")
        
    except Exception as e:
        print(f"Error getting monitoring logs: {e}")


def demo_log_search():
    """Demonstrate log search functionality."""
    print_section("Log Search")
    
    try:
        service_manager = get_cli_service_manager()
        
        # Search for "backup" in logs
        search_query = "backup"
        logs = service_manager.search_monitoring_logs(
            query=search_query,
            days=7,
            limit=5
        )
        
        if not logs:
            print(f"No logs found matching '{search_query}'")
            return
        
        print(f"Found {len(logs)} log entries matching '{search_query}':\n")
        
        for log in logs:
            timestamp = log.get('timestamp', 'N/A')
            level = log.get('level', 'INFO').upper()
            message = log.get('message', '')
            print(f"[{level}] {timestamp} - {message}")
            print()
        
    except Exception as e:
        print(f"Error searching logs: {e}")


def demo_backup_history():
    """Demonstrate backup history retrieval."""
    print_section("Backup History")
    
    try:
        service_manager = get_cli_service_manager()
        
        # Get backup history for last 7 days
        history = service_manager.get_cli_backup_history(
            days=7,
            limit=10
        )
        
        if not history:
            print("No backup history found")
            return
        
        print(f"Found {len(history)} backup operations:\n")
        
        for record in history[:5]:  # Show first 5
            print(f"Operation: {record['operation_id']}")
            print(f"  Repository: {record['repository_id']}")
            print(f"  Status: {record['status']}")
            print(f"  Start Time: {record['start_time']}")
            print(f"  Files: {record['files_processed']}")
            print(f"  Data: {record['bytes_transferred_formatted']}")
            print(f"  Duration: {record['duration']}")
            print(f"  Throughput: {record['throughput_mbps']} MB/s")
            print()
        
        if len(history) > 5:
            print(f"... and {len(history) - 5} more operations")
        
    except Exception as e:
        print(f"Error getting backup history: {e}")


def demo_monitoring_integration_direct():
    """Demonstrate direct use of CLIMonitoringIntegration."""
    print_section("Direct Monitoring Integration")
    
    try:
        # Create monitoring integration directly
        integration = CLIMonitoringIntegration()
        
        # Get system status
        status = integration.get_system_status()
        print(f"System Health: {status.get('health_status', 'unknown')}")
        
        # Get recent logs with filters
        filters = CLIMonitoringFilters(
            hours=24,
            log_level='error',
            limit=5
        )
        
        logs = integration.get_recent_logs(filters)
        print(f"\nFound {len(logs)} error logs in last 24 hours")
        
        # Get current operations
        operations = integration.get_current_operations()
        print(f"Current operations: {len(operations)}")
        
    except Exception as e:
        print(f"Error with direct monitoring integration: {e}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("  CLI Monitoring Integration Demo")
    print("=" * 60)
    print("\nThis demo shows the CLI monitoring integration capabilities")
    print("including status, logs, operations, and backup history.\n")
    
    try:
        # Run demonstrations
        demo_system_status()
        demo_current_operations()
        demo_monitoring_logs()
        demo_log_search()
        demo_backup_history()
        demo_monitoring_integration_direct()
        
        print_section("Demo Complete")
        print("All monitoring integration features demonstrated successfully!")
        print("\nFor CLI usage, try:")
        print("  timelocker monitor status")
        print("  timelocker monitor operations")
        print("  timelocker monitor history")
        print("  timelocker logs search 'backup'")
        print("  timelocker logs recent --level error")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
