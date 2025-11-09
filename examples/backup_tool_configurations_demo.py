#!/usr/bin/env python3
"""
TimeLocker Backup Tool Configurations Demo

This script demonstrates different backup tool configurations and capabilities:
- Restic configuration examples
- Borg configuration examples
- Custom tool integration
- Performance optimization
- Feature comparison
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("=== TimeLocker Backup Tool Configurations Demo ===\n")


def demo_restic_configuration():
    """Demonstrate Restic backup tool configuration."""
    print("1. Restic Configuration")
    print("-" * 50)
    
    # Basic configuration
    basic_config = {
        "tool_type": "restic",
        "tool_path": "/usr/bin/restic",
        "repository_uri": "s3:s3.amazonaws.com/backup-bucket/restic-repo",
        "features": {
            "parallel_operations": 4,
            "compression": "auto",
            "encryption": "AES-256",
            "deduplication": True,
            "integrity_validation": True
        },
        "performance": {
            "pack_size": 16,  # MB
            "cache_size": 512,  # MB
            "connections": 5
        }
    }
    
    print("Basic Restic Configuration:")
    print(f"  Tool: {basic_config['tool_type']}")
    print(f"  Repository: {basic_config['repository_uri']}")
    print(f"  Parallel Operations: {basic_config['features']['parallel_operations']}")
    print(f"  Compression: {basic_config['features']['compression']}")
    print(f"  Pack Size: {basic_config['performance']['pack_size']} MB")
    
    # Advanced configuration
    advanced_config = {
        "tool_type": "restic",
        "repository_uri": "rest:https://backup.example.com/restic",
        "features": {
            "parallel_operations": 8,
            "compression": "max",
            "read_concurrency": 4,
            "exclude_caches": True,
            "exclude_if_present": [".nobackup", "CACHEDIR.TAG"]
        },
        "performance": {
            "pack_size": 32,
            "cache_size": 1024,
            "limit_upload": 10240,  # KB/s
            "limit_download": 10240
        },
        "retry": {
            "max_retries": 5,
            "retry_delay": 2
        }
    }
    
    print("\nAdvanced Restic Configuration:")
    print(f"  Repository: {advanced_config['repository_uri']}")
    print(f"  Parallel Operations: {advanced_config['features']['parallel_operations']}")
    print(f"  Read Concurrency: {advanced_config['features']['read_concurrency']}")
    print(f"  Upload Limit: {advanced_config['performance']['limit_upload']} KB/s")
    print(f"  Cache Size: {advanced_config['performance']['cache_size']} MB")
    
    print("\n✓ Restic configurations demonstrated\n")
    
    return basic_config, advanced_config


def demo_borg_configuration():
    """Demonstrate Borg backup tool configuration."""
    print("2. Borg Configuration")
    print("-" * 50)
    
    # Basic configuration
    basic_config = {
        "tool_type": "borg",
        "tool_path": "/usr/bin/borg",
        "repository_uri": "ssh://backup@server.example.com/~/borg-repo",
        "features": {
            "compression": "lz4",
            "encryption": "repokey-blake2",
            "deduplication": True,
            "checkpoint_interval": 1800  # seconds
        },
        "performance": {
            "upload_buffer": 10,  # MB
            "upload_ratelimit": 0  # unlimited
        }
    }
    
    print("Basic Borg Configuration:")
    print(f"  Tool: {basic_config['tool_type']}")
    print(f"  Repository: {basic_config['repository_uri']}")
    print(f"  Compression: {basic_config['features']['compression']}")
    print(f"  Encryption: {basic_config['features']['encryption']}")
    print(f"  Checkpoint Interval: {basic_config['features']['checkpoint_interval']}s")
    
    # Advanced configuration
    advanced_config = {
        "tool_type": "borg",
        "repository_uri": "ssh://backup@server.example.com/~/borg-repo",
        "features": {
            "compression": "zstd,10",  # zstd level 10
            "encryption": "repokey-blake2",
            "deduplication": True,
            "checkpoint_interval": 900,
            "chunker_params": "19,23,21,4095",
            "exclude_caches": True,
            "one_file_system": True
        },
        "performance": {
            "upload_buffer": 20,
            "upload_ratelimit": 10240,  # KB/s
            "remote_ratelimit": 10240
        },
        "ssh": {
            "command": "ssh -i /path/to/key",
            "compression": True
        }
    }
    
    print("\nAdvanced Borg Configuration:")
    print(f"  Compression: {advanced_config['features']['compression']}")
    print(f"  Chunker Params: {advanced_config['features']['chunker_params']}")
    print(f"  Upload Buffer: {advanced_config['performance']['upload_buffer']} MB")
    print(f"  Rate Limit: {advanced_config['performance']['upload_ratelimit']} KB/s")
    print(f"  SSH Compression: {advanced_config['ssh']['compression']}")
    
    print("\n✓ Borg configurations demonstrated\n")
    
    return basic_config, advanced_config


def demo_performance_optimization():
    """Demonstrate performance optimization strategies."""
    print("3. Performance Optimization")
    print("-" * 50)
    
    scenarios = {
        "Fast Local Backup": {
            "tool": "restic",
            "config": {
                "parallel_operations": 8,
                "compression": "off",
                "pack_size": 64,
                "cache_size": 2048
            },
            "expected_throughput": "500 MB/s",
            "use_case": "Local NVMe storage, CPU-limited"
        },
        "Remote Backup (Limited Bandwidth)": {
            "tool": "restic",
            "config": {
                "parallel_operations": 2,
                "compression": "max",
                "pack_size": 8,
                "limit_upload": 5120,
                "connections": 2
            },
            "expected_throughput": "5 MB/s",
            "use_case": "Remote backup over slow connection"
        },
        "Large Dataset Backup": {
            "tool": "borg",
            "config": {
                "compression": "lz4",
                "checkpoint_interval": 600,
                "upload_buffer": 50,
                "chunker_params": "19,23,21,4095"
            },
            "expected_throughput": "200 MB/s",
            "use_case": "Multi-TB dataset with good deduplication"
        },
        "Memory-Constrained Backup": {
            "tool": "restic",
            "config": {
                "parallel_operations": 1,
                "pack_size": 4,
                "cache_size": 128,
                "read_concurrency": 1
            },
            "expected_throughput": "50 MB/s",
            "use_case": "Low-memory system (< 1GB available)"
        }
    }
    
    for scenario_name, details in scenarios.items():
        print(f"\n{scenario_name}:")
        print(f"  Tool: {details['tool']}")
        print(f"  Use Case: {details['use_case']}")
        print(f"  Expected Throughput: {details['expected_throughput']}")
        print(f"  Configuration:")
        for key, value in details['config'].items():
            print(f"    {key}: {value}")
    
    print("\n✓ Performance optimization strategies demonstrated\n")


def demo_feature_matrix():
    """Demonstrate feature comparison matrix."""
    print("4. Feature Comparison Matrix")
    print("-" * 50)
    
    features = [
        "Parallel Processing",
        "Deduplication",
        "Compression",
        "Encryption",
        "Resume Support",
        "Integrity Validation",
        "Bandwidth Limiting",
        "Progress Reporting",
        "Snapshot Tagging",
        "Incremental Backup"
    ]
    
    tools = {
        "Restic": ["Native", "Native", "Native", "Native", "Native", 
                   "Native", "Wrapper", "Native", "Wrapper", "Native"],
        "Borg": ["Wrapper", "Native", "Native", "Native", "Native",
                 "Native", "Native", "Wrapper", "Wrapper", "Native"],
        "Duplicity": ["None", "None", "Native", "Native", "Native",
                      "Wrapper", "Native", "None", "Wrapper", "Native"]
    }
    
    # Print header
    header = f"{'Feature':<25}"
    for tool in tools.keys():
        header += f" {tool:<12}"
    print(header)
    print("-" * 75)
    
    # Print rows
    for i, feature in enumerate(features):
        row = f"{feature:<25}"
        for tool_features in tools.values():
            support = tool_features[i]
            symbol = "✓" if support == "Native" else "+" if support == "Wrapper" else "✗"
            row += f" {symbol} {support:<10}"
        print(row)
    
    print("\nLegend:")
    print("  ✓ Native  - Natively supported by tool")
    print("  + Wrapper - Provided by TimeLocker wrapper")
    print("  ✗ None    - Not supported")
    
    print("\n✓ Feature matrix displayed\n")


def demo_repository_types():
    """Demonstrate different repository type configurations."""
    print("5. Repository Type Configurations")
    print("-" * 50)
    
    repositories = {
        "Local": {
            "uri": "/mnt/backup/restic-repo",
            "tool": "restic",
            "pros": ["Fast", "No network dependency", "Simple setup"],
            "cons": ["No off-site backup", "Single point of failure"],
            "config": {
                "parallel_operations": 8,
                "compression": "off"
            }
        },
        "S3": {
            "uri": "s3:s3.amazonaws.com/backup-bucket/repo",
            "tool": "restic",
            "pros": ["Durable", "Scalable", "Off-site"],
            "cons": ["Network dependent", "Costs", "Slower"],
            "config": {
                "parallel_operations": 4,
                "connections": 5,
                "pack_size": 16
            }
        },
        "SFTP": {
            "uri": "sftp:backup@server.example.com:/backup/repo",
            "tool": "restic",
            "pros": ["Secure", "Standard protocol", "Flexible"],
            "cons": ["Network dependent", "SSH overhead"],
            "config": {
                "parallel_operations": 2,
                "connections": 3
            }
        },
        "REST Server": {
            "uri": "rest:https://backup.example.com/repo",
            "tool": "restic",
            "pros": ["HTTP-based", "Firewall-friendly", "Efficient"],
            "cons": ["Requires REST server", "Network dependent"],
            "config": {
                "parallel_operations": 6,
                "connections": 8
            }
        },
        "SSH (Borg)": {
            "uri": "ssh://backup@server.example.com/~/borg-repo",
            "tool": "borg",
            "pros": ["Secure", "Efficient", "Checkpoint support"],
            "cons": ["SSH required", "Single connection"],
            "config": {
                "compression": "zstd,10",
                "upload_buffer": 20
            }
        }
    }
    
    for repo_type, details in repositories.items():
        print(f"\n{repo_type} Repository:")
        print(f"  URI: {details['uri']}")
        print(f"  Tool: {details['tool']}")
        print(f"  Pros: {', '.join(details['pros'])}")
        print(f"  Cons: {', '.join(details['cons'])}")
        print(f"  Recommended Config:")
        for key, value in details['config'].items():
            print(f"    {key}: {value}")
    
    print("\n✓ Repository types demonstrated\n")


def demo_use_case_recommendations():
    """Demonstrate tool recommendations for different use cases."""
    print("6. Use Case Recommendations")
    print("-" * 50)
    
    use_cases = {
        "Home User - Documents": {
            "recommended_tool": "restic",
            "repository": "Local or Cloud (S3/B2)",
            "configuration": {
                "parallel_operations": 2,
                "compression": "auto",
                "schedule": "Daily"
            },
            "reasoning": "Simple setup, good deduplication, cloud support"
        },
        "Small Business - File Server": {
            "recommended_tool": "borg",
            "repository": "SSH to dedicated backup server",
            "configuration": {
                "compression": "zstd,6",
                "checkpoint_interval": 1800,
                "schedule": "Hourly incremental, daily full"
            },
            "reasoning": "Efficient, reliable, checkpoint support for large datasets"
        },
        "Enterprise - Database Backups": {
            "recommended_tool": "restic",
            "repository": "S3 with versioning",
            "configuration": {
                "parallel_operations": 8,
                "compression": "max",
                "integrity_validation": True,
                "schedule": "Every 4 hours"
            },
            "reasoning": "Parallel processing, integrity checks, cloud durability"
        },
        "Developer - Code Repositories": {
            "recommended_tool": "restic",
            "repository": "Local + Cloud sync",
            "configuration": {
                "parallel_operations": 4,
                "compression": "auto",
                "exclude_patterns": ["node_modules", ".git", "build"],
                "schedule": "On commit (via hook)"
            },
            "reasoning": "Fast, good pattern matching, multiple repository support"
        },
        "Media Production - Large Files": {
            "recommended_tool": "borg",
            "repository": "Local NAS with SSH",
            "configuration": {
                "compression": "lz4",
                "chunker_params": "19,23,21,4095",
                "checkpoint_interval": 600,
                "schedule": "Daily"
            },
            "reasoning": "Efficient for large files, checkpoint support, fast compression"
        }
    }
    
    for use_case, details in use_cases.items():
        print(f"\n{use_case}:")
        print(f"  Recommended Tool: {details['recommended_tool']}")
        print(f"  Repository: {details['repository']}")
        print(f"  Reasoning: {details['reasoning']}")
        print(f"  Configuration:")
        for key, value in details['configuration'].items():
            print(f"    {key}: {value}")
    
    print("\n✓ Use case recommendations provided\n")


def demo_migration_scenarios():
    """Demonstrate migration between backup tools."""
    print("7. Tool Migration Scenarios")
    print("-" * 50)
    
    migrations = {
        "Restic to Borg": {
            "reason": "Need checkpoint support for unreliable connections",
            "steps": [
                "1. Complete final Restic backup",
                "2. Initialize new Borg repository",
                "3. Perform full backup with Borg",
                "4. Verify Borg backup integrity",
                "5. Update backup configuration",
                "6. Keep Restic repository for historical data"
            ],
            "considerations": [
                "No direct repository conversion",
                "Requires full re-backup",
                "Plan for storage during transition"
            ]
        },
        "Borg to Restic": {
            "reason": "Need better cloud storage support and parallel processing",
            "steps": [
                "1. Complete final Borg backup",
                "2. Initialize Restic repository",
                "3. Perform full backup with Restic",
                "4. Test restore operations",
                "5. Update automation scripts",
                "6. Archive Borg repository"
            ],
            "considerations": [
                "Restic has better S3 support",
                "Parallel operations improve speed",
                "Different repository format"
            ]
        }
    }
    
    for migration, details in migrations.items():
        print(f"\n{migration}:")
        print(f"  Reason: {details['reason']}")
        print(f"  Migration Steps:")
        for step in details['steps']:
            print(f"    {step}")
        print(f"  Considerations:")
        for consideration in details['considerations']:
            print(f"    • {consideration}")
    
    print("\n✓ Migration scenarios outlined\n")


def main():
    """Run complete demonstration."""
    try:
        # 1. Restic configurations
        demo_restic_configuration()
        
        # 2. Borg configurations
        demo_borg_configuration()
        
        # 3. Performance optimization
        demo_performance_optimization()
        
        # 4. Feature comparison
        demo_feature_matrix()
        
        # 5. Repository types
        demo_repository_types()
        
        # 6. Use case recommendations
        demo_use_case_recommendations()
        
        # 7. Migration scenarios
        demo_migration_scenarios()
        
        # Summary
        print("=" * 50)
        print("DEMO SUMMARY")
        print("=" * 50)
        print("\nBackup Tool Configuration Topics Covered:")
        print("  ✓ Restic configuration options")
        print("  ✓ Borg configuration options")
        print("  ✓ Performance optimization strategies")
        print("  ✓ Feature comparison matrix")
        print("  ✓ Repository type configurations")
        print("  ✓ Use case recommendations")
        print("  ✓ Tool migration scenarios")
        
        print("\nKey Takeaways:")
        print("  • Choose tool based on specific requirements")
        print("  • Optimize configuration for your use case")
        print("  • Consider repository type carefully")
        print("  • Plan for performance and reliability")
        print("  • Test configurations before production use")
        
        print("\n✓ Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
