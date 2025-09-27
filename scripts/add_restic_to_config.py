#!/usr/bin/env python3
"""
Simple script to add restic repository to TimeLocker config
"""

import json
import os
from pathlib import Path


def add_restic_repo_to_config():
    """Add restic repository to TimeLocker configuration"""

    # Get environment variables
    repo_uri = os.getenv('RESTIC_REPOSITORY')
    repo_password = os.getenv('RESTIC_PASSWORD')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

    if not repo_uri or not repo_password:
        print("❌ RESTIC_REPOSITORY and RESTIC_PASSWORD must be set")
        return False

    # Load existing config
    config_file = Path.home() / ".timelocker" / "config.json"

    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_file}")
        return False

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        print(f"✅ Loaded configuration from {config_file}")

        # Add repository
        repo_name = "imported_s3_repo"
        config["repositories"][repo_name] = {
                "type":                      "s3",
                "uri":                       repo_uri,
                "description":               "Imported from restic environment",
                "encryption":                True,
                "aws_region":                aws_region,
                "imported_from_environment": True
        }

        # Add backup target
        target_name = "imported_backup"
        config.setdefault("backup_targets", {})[target_name] = {
                "paths":       ["/home", "/etc", "/var", "/srv", "/root", "/nix/var"],
                "repository":  repo_name,
                "description": "Imported backup target from restic environment",
                "patterns":    {
                        "exclude": [
                                "**/.git/**",
                                "**/__pycache__/**",
                                "**/node_modules/**",
                                "**/.DS_Store",
                                "**/Thumbs.db"
                        ]
                }
        }

        # Update settings
        config.setdefault("settings", {})["default_repository"] = repo_name

        # Save configuration
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Repository '{repo_name}' added to configuration")
        print(f"✅ Backup target '{target_name}' created")
        print(f"✅ Configuration saved to {config_file}")

        return True

    except Exception as e:
        print(f"❌ Error updating configuration: {e}")
        return False


def main():
    """Main function"""
    print("🔧 Adding Restic Repository to TimeLocker Configuration")
    print("=" * 60)

    # Check environment variables
    required_vars = ['RESTIC_REPOSITORY', 'RESTIC_PASSWORD']
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Set them with: source extracted_configs/set_environment.sh")
        return False

    # Show what will be added
    repo_uri = os.getenv('RESTIC_REPOSITORY')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

    print(f"📍 Repository URI: {repo_uri}")
    print(f"🌍 AWS Region: {aws_region}")
    print(f"🔐 Password: {'✅ Set' if os.getenv('RESTIC_PASSWORD') else '❌ Not set'}")
    print()

    # Add to configuration
    if add_restic_repo_to_config():
        print("\n🎉 Repository successfully added to TimeLocker!")
        print("\n📋 Next steps:")
        print("1. List configuration: cd src && python3 -m TimeLocker.cli config list")
        print("2. Test repository: cd src && python3 -m TimeLocker.cli list -r", repo_uri)
        return True
    else:
        print("\n❌ Failed to add repository to configuration")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
