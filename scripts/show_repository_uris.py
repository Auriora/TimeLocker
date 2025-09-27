#!/usr/bin/env python3
"""
Show repository URIs from TimeLocker configuration
"""

import json
import os
from pathlib import Path


def show_repository_uris():
    """Display repository URIs from various sources"""
    print("🔍 Repository URIs - All Sources")
    print("=" * 50)

    # 1. From TimeLocker configuration
    config_file = Path.home() / ".timelocker" / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            repos = config.get("repositories", {})
            if repos:
                print("📁 From TimeLocker Configuration:")
                print("-" * 30)
                for name, repo in repos.items():
                    uri = repo.get("uri", "N/A")
                    repo_type = repo.get("type", "unknown")
                    region = repo.get("aws_region", "")
                    print(f"   📍 {name}")
                    print(f"      URI: {uri}")
                    print(f"      Type: {repo_type}")
                    if region:
                        print(f"      Region: {region}")
                    print()
            else:
                print("📁 TimeLocker Configuration: No repositories found")
                print()
        except Exception as e:
            print(f"❌ Error reading TimeLocker config: {e}")
            print()
    else:
        print("📁 TimeLocker Configuration: Not found")
        print()

    # 2. From environment variables
    print("🌍 From Environment Variables:")
    print("-" * 30)

    env_vars = {
            'RESTIC_REPOSITORY':     'Repository URI',
            'RESTIC_PASSWORD':       'Repository Password',
            'AWS_ACCESS_KEY_ID':     'AWS Access Key',
            'AWS_SECRET_ACCESS_KEY': 'AWS Secret Key',
            'AWS_DEFAULT_REGION':    'AWS Region'
    }

    env_found = False
    for var, description in env_vars.items():
        value = os.getenv(var)
        if value:
            env_found = True
            if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                # Mask sensitive values
                masked = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                print(f"   ✅ {var}: {masked}")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: Not set")

    if not env_found:
        print("   💡 Set environment variables with: source extracted_configs/set_environment.sh")
    print()

    # 3. From extracted configuration
    extracted_config = Path("extracted_configs/restic_config.json")
    if extracted_config.exists():
        try:
            with open(extracted_config, 'r') as f:
                config = json.load(f)

            repos = config.get("repositories", {})
            if repos:
                print("📄 From Extracted Configuration:")
                print("-" * 30)
                for name, repo in repos.items():
                    uri = repo.get("uri", "N/A")
                    repo_type = repo.get("type", "unknown")
                    region = repo.get("aws_region", "")
                    print(f"   📍 {name}")
                    print(f"      URI: {uri}")
                    print(f"      Type: {repo_type}")
                    if region:
                        print(f"      Region: {region}")
                    print()
            else:
                print("📄 Extracted Configuration: No repositories found")
                print()
        except Exception as e:
            print(f"❌ Error reading extracted config: {e}")
            print()
    else:
        print("📄 Extracted Configuration: Not found")
        print()

    # 4. Usage examples
    print("💡 Usage Examples:")
    print("-" * 30)

    # Get the first repository URI we can find
    example_uri = None

    # Try TimeLocker config first
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            repos = config.get("repositories", {})
            if repos:
                example_uri = list(repos.values())[0].get("uri")
        except:
            pass

    # Try environment variable
    if not example_uri:
        example_uri = os.getenv('RESTIC_REPOSITORY')

    # Try extracted config
    if not example_uri and extracted_config.exists():
        try:
            with open(extracted_config, 'r') as f:
                config = json.load(f)
            repos = config.get("repositories", {})
            if repos:
                example_uri = list(repos.values())[0].get("uri")
        except:
            pass

    if example_uri:
        print(f"Using repository URI: {example_uri}")
        print()
        print("📋 TimeLocker Commands:")
        print(f"   # List snapshots")
        print(f"   cd src && python3 -m TimeLocker.cli list -r \"{example_uri}\"")
        print()
        print(f"   # Create backup")
        print(f"   cd src && python3 -m TimeLocker.cli backup -r \"{example_uri}\" /path/to/backup")
        print()
        print("📋 Direct Restic Commands:")
        print(f"   # List snapshots")
        print(f"   restic -r \"{example_uri}\" snapshots")
        print()
        print(f"   # Check repository")
        print(f"   restic -r \"{example_uri}\" check")
    else:
        print("❌ No repository URI found")
        print("💡 Import a repository first:")
        print("   cd src && python3 -m TimeLocker.cli config import-restic")


def main():
    """Main function"""
    show_repository_uris()


if __name__ == "__main__":
    main()
