#!/usr/bin/env python3
"""
Display a comprehensive summary of the restic configuration extraction
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime


def check_file_exists(file_path: Path) -> bool:
    """Check if a file exists and is readable"""
    return file_path.exists() and file_path.is_file()


def get_file_info(file_path: Path) -> dict:
    """Get file information"""
    if not file_path.exists():
        return {"exists": False}

    stat = file_path.stat()
    return {
            "exists":      True,
            "size":        stat.st_size,
            "modified":    datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:]
    }


def check_restic_version() -> str:
    """Get restic version"""
    try:
        result = subprocess.run(['restic', 'version'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "Error: " + result.stderr.strip()
    except FileNotFoundError:
        return "Not found in PATH"
    except Exception as e:
        return f"Error: {e}"


def load_extracted_config(config_file: Path) -> dict:
    """Load the extracted configuration"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def main():
    """Display extraction summary"""
    print("🔧 Restic Configuration Extraction Summary")
    print("=" * 60)

    # Project paths
    project_dir = Path(__file__).parent.parent
    extracted_config = project_dir / "extracted_configs" / "restic_config.json"
    readme_file = project_dir / "extracted_configs" / "README.md"

    print(f"📁 Project Directory: {project_dir}")
    print(f"📄 Configuration File: {extracted_config}")
    print()

    # Check extraction files
    print("📋 Extraction Status:")
    print("-" * 30)

    config_info = get_file_info(extracted_config)
    if config_info["exists"]:
        print(f"✅ Configuration file: {extracted_config.name}")
        print(f"   Size: {config_info['size']:,} bytes")
        print(f"   Modified: {config_info['modified']}")
        print(f"   Permissions: {config_info['permissions']}")
    else:
        print(f"❌ Configuration file not found: {extracted_config}")
        return

    readme_info = get_file_info(readme_file)
    if readme_info["exists"]:
        print(f"✅ Documentation: {readme_file.name}")
    else:
        print(f"⚠️  Documentation not found: {readme_file}")

    print()

    # Load and display configuration
    print("📊 Configuration Details:")
    print("-" * 30)

    config = load_extracted_config(extracted_config)
    if "error" in config:
        print(f"❌ Error loading configuration: {config['error']}")
        return

    # Repository information
    repos = config.get("repositories", {})
    print(f"🗂️  Repositories: {len(repos)}")
    for name, repo in repos.items():
        print(f"   📍 {name}:")
        print(f"      Type: {repo.get('type', 'unknown')}")
        print(f"      URI: {repo.get('uri', 'N/A')}")
        print(f"      Region: {repo.get('aws_region', 'N/A')}")
        print(f"      Encryption: {repo.get('encryption', False)}")

    # Backup targets
    targets = config.get("backup_targets", {})
    print(f"\n📂 Backup Targets: {len(targets)}")
    for name, target in targets.items():
        paths = target.get("paths", [])
        excludes = target.get("patterns", {}).get("exclude", [])
        print(f"   📁 {name}:")
        print(f"      Paths: {len(paths)}")
        for path in paths[:3]:  # Show first 3 paths
            print(f"        - {path}")
        if len(paths) > 3:
            print(f"        ... and {len(paths) - 3} more")
        print(f"      Exclude patterns: {len(excludes)}")

    # Backup settings
    backup = config.get("backup", {})
    if backup:
        print(f"\n⚙️  Backup Settings:")
        print(f"   Compression: {backup.get('compression', 'auto')}")
        print(f"   One file system: {backup.get('one_file_system', False)}")
        print(f"   Retention:")
        print(f"     Last: {backup.get('retention_keep_last', 'N/A')}")
        print(f"     Daily: {backup.get('retention_keep_daily', 'N/A')}")
        print(f"     Weekly: {backup.get('retention_keep_weekly', 'N/A')}")
        print(f"     Monthly: {backup.get('retention_keep_monthly', 'N/A')}")

    # Credentials (without showing actual values)
    credentials = config.get("credentials", {})
    print(f"\n🔐 Credentials:")
    cred_fields = ["aws_access_key_id", "aws_secret_access_key", "repository_password"]
    for field in cred_fields:
        if field in credentials and credentials[field]:
            value = credentials[field]
            masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
            print(f"   {field}: {masked}")
        else:
            print(f"   {field}: ❌ Missing")

    # Extraction metadata
    metadata = config.get("extraction_metadata", {})
    if metadata:
        print(f"\n📋 Extraction Metadata:")
        print(f"   Extracted at: {metadata.get('extracted_at', 'N/A')}")
        print(f"   Original cron: {metadata.get('original_cron_schedule', 'N/A')}")
        print(f"   NPBackup version: {metadata.get('npbackup_version', 'N/A')}")
        source_files = metadata.get('source_files', [])
        if source_files:
            print(f"   Source files:")
            for source in source_files:
                print(f"     - {source}")

    print()

    # System information
    print("🖥️  System Information:")
    print("-" * 30)

    restic_version = check_restic_version()
    print(f"Restic: {restic_version}")

    # Check if original files still exist
    original_files = [
            "/var/restic/.resticrc",
            "/var/restic/.config/npbackup/npbackup.conf"
    ]

    print("\n📁 Original Configuration Files:")
    for file_path in original_files:
        try:
            path = Path(file_path)
            if path.exists():
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} (not found)")
        except PermissionError:
            print(f"   🔒 {file_path} (permission denied - run with sudo to check)")
        except Exception as e:
            print(f"   ❌ {file_path} (error: {e})")

    # Check backup directory
    backup_dirs = list(Path("/tmp").glob("restic_config_backup_*"))
    if backup_dirs:
        latest_backup = max(backup_dirs, key=lambda p: p.stat().st_mtime)
        print(f"\n💾 Latest Backup: {latest_backup}")
        backup_files = list(latest_backup.glob("*"))
        print(f"   Files backed up: {len(backup_files)}")
    else:
        print(f"\n⚠️  No backup directories found in /tmp")

    print()

    # Next steps
    print("📋 Next Steps:")
    print("-" * 30)
    print("1. 🧪 Validate configuration:")
    print(f"   python3 scripts/validate_extracted_config.py {extracted_config}")
    print()
    print("2. 📥 Import into TimeLocker:")
    print(f"   python3 scripts/import_to_timelocker.py {extracted_config}")
    print()
    print("3. 🔧 Set environment variables:")
    print("   export AWS_ACCESS_KEY_ID='...'")
    print("   export AWS_SECRET_ACCESS_KEY='...'")
    print("   export AWS_DEFAULT_REGION='af-south-1'")
    print("   export RESTIC_PASSWORD='...'")
    print()
    print("4. 🧪 Test repository connection:")
    print("   restic -r s3:s3.af-south-1.amazonaws.com/5560-restic snapshots --latest 1")
    print()
    print("5. 📅 Consider scheduling migration:")
    print("   - Current: Root cron job at 17:30 daily")
    print("   - Option: Migrate to TimeLocker scheduling")

    print()
    print("🎉 Configuration extraction completed successfully!")
    print(f"📖 See {readme_file} for detailed documentation")


if __name__ == "__main__":
    main()
