#!/usr/bin/env python3
"""
Validate extracted restic configuration by testing repository connection
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any


class ConfigValidator:
    """Validate extracted restic configuration"""

    def __init__(self, config_file: str):
        self.config_file = Path(config_file)
        self.config = {}

    def load_config(self) -> bool:
        """Load the extracted configuration"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            print(f"✅ Loaded configuration from {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return False

    def validate_config_structure(self) -> bool:
        """Validate the configuration structure"""
        required_sections = ['repositories', 'backup_targets', 'credentials']

        for section in required_sections:
            if section not in self.config:
                print(f"❌ Missing required section: {section}")
                return False

        # Check repositories
        repos = self.config.get('repositories', {})
        if not repos:
            print("❌ No repositories found in configuration")
            return False

        for repo_name, repo_config in repos.items():
            required_repo_fields = ['type', 'uri']
            for field in required_repo_fields:
                if field not in repo_config:
                    print(f"❌ Repository {repo_name} missing required field: {field}")
                    return False

        # Check credentials
        credentials = self.config.get('credentials', {})
        required_creds = ['repository_password']
        for cred in required_creds:
            if cred not in credentials or not credentials[cred]:
                print(f"❌ Missing required credential: {cred}")
                return False

        print("✅ Configuration structure is valid")
        return True

    def test_restic_installation(self) -> bool:
        """Test if restic is installed and accessible"""
        try:
            result = subprocess.run(['restic', 'version'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ Restic found: {version}")
                return True
            else:
                print(f"❌ Restic command failed: {result.stderr}")
                return False
        except FileNotFoundError:
            print("❌ Restic not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            print("❌ Restic command timed out")
            return False
        except Exception as e:
            print(f"❌ Error testing restic: {e}")
            return False

    def test_repository_connection(self) -> bool:
        """Test connection to the repository"""
        try:
            # Get repository and credentials
            repos = self.config.get('repositories', {})
            if not repos:
                print("❌ No repositories to test")
                return False

            credentials = self.config.get('credentials', {})

            # Test each repository
            for repo_name, repo_config in repos.items():
                print(f"🔍 Testing repository: {repo_name}")

                repo_uri = repo_config.get('uri', '')
                if not repo_uri:
                    print(f"❌ No URI for repository {repo_name}")
                    continue

                # Set up environment
                env = os.environ.copy()

                # Set repository password
                repo_password = credentials.get('repository_password')
                if repo_password:
                    env['RESTIC_PASSWORD'] = repo_password

                # Set AWS credentials if present
                aws_access_key = credentials.get('aws_access_key_id')
                aws_secret_key = credentials.get('aws_secret_access_key')
                aws_region = repo_config.get('aws_region')

                if aws_access_key:
                    env['AWS_ACCESS_KEY_ID'] = aws_access_key
                if aws_secret_key:
                    env['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
                if aws_region:
                    env['AWS_DEFAULT_REGION'] = aws_region

                # Test repository access
                try:
                    print(f"   📡 Testing connection to: {repo_uri}")

                    # Try to list snapshots (this will test authentication and access)
                    result = subprocess.run([
                            'restic', '-r', repo_uri, 'snapshots', '--latest', '1', '--json'
                    ], env=env, capture_output=True, text=True, timeout=30)

                    if result.returncode == 0:
                        # Parse the JSON output to get snapshot info
                        try:
                            snapshots = json.loads(result.stdout)
                            if snapshots:
                                latest = snapshots[0]
                                snapshot_time = latest.get('time', 'unknown')
                                snapshot_id = latest.get('short_id', 'unknown')
                                print(f"   ✅ Repository accessible - Latest snapshot: {snapshot_id} ({snapshot_time})")
                            else:
                                print(f"   ✅ Repository accessible - No snapshots found")
                        except json.JSONDecodeError:
                            print(f"   ✅ Repository accessible - Could not parse snapshot info")

                        return True
                    else:
                        print(f"   ❌ Repository connection failed: {result.stderr.strip()}")
                        return False

                except subprocess.TimeoutExpired:
                    print(f"   ❌ Repository connection timed out")
                    return False
                except Exception as e:
                    print(f"   ❌ Error testing repository: {e}")
                    return False

            return True

        except Exception as e:
            print(f"❌ Error in repository connection test: {e}")
            return False

    def validate_backup_paths(self) -> bool:
        """Validate that backup paths exist and are accessible"""
        try:
            backup_targets = self.config.get('backup_targets', {})

            for target_name, target_config in backup_targets.items():
                print(f"📁 Validating backup target: {target_name}")

                paths = target_config.get('paths', [])
                if not paths:
                    print(f"   ⚠️  No paths defined for target {target_name}")
                    continue

                accessible_paths = 0
                for path in paths:
                    path_obj = Path(path)
                    if path_obj.exists():
                        if path_obj.is_dir():
                            print(f"   ✅ Directory accessible: {path}")
                        else:
                            print(f"   ✅ File accessible: {path}")
                        accessible_paths += 1
                    else:
                        print(f"   ⚠️  Path not found: {path}")

                print(f"   📊 {accessible_paths}/{len(paths)} paths accessible")

            return True

        except Exception as e:
            print(f"❌ Error validating backup paths: {e}")
            return False

    def display_configuration_summary(self):
        """Display a summary of the configuration"""
        print("\n📊 Configuration Summary:")
        print("=" * 50)

        # Repositories
        repos = self.config.get('repositories', {})
        print(f"🗂️  Repositories: {len(repos)}")
        for name, repo in repos.items():
            print(f"   📍 {name}:")
            print(f"      Type: {repo.get('type', 'unknown')}")
            print(f"      URI: {repo.get('uri', 'N/A')}")
            print(f"      Region: {repo.get('aws_region', 'N/A')}")

        # Backup targets
        targets = self.config.get('backup_targets', {})
        print(f"\n📂 Backup Targets: {len(targets)}")
        for name, target in targets.items():
            paths = target.get('paths', [])
            excludes = target.get('patterns', {}).get('exclude', [])
            print(f"   📁 {name}:")
            print(f"      Paths: {len(paths)}")
            print(f"      Excludes: {len(excludes)}")

        # Backup settings
        backup = self.config.get('backup', {})
        if backup:
            print(f"\n⚙️  Backup Settings:")
            print(f"   Compression: {backup.get('compression', 'auto')}")
            print(f"   One file system: {backup.get('one_file_system', False)}")
            print(f"   Retention - Last: {backup.get('retention_keep_last', 'N/A')}")
            print(f"   Retention - Daily: {backup.get('retention_keep_daily', 'N/A')}")
            print(f"   Retention - Weekly: {backup.get('retention_keep_weekly', 'N/A')}")
            print(f"   Retention - Monthly: {backup.get('retention_keep_monthly', 'N/A')}")

        # Metadata
        metadata = self.config.get('extraction_metadata', {})
        if metadata:
            print(f"\n📋 Extraction Metadata:")
            print(f"   Extracted at: {metadata.get('extracted_at', 'N/A')}")
            print(f"   Original cron: {metadata.get('original_cron_schedule', 'N/A')}")
            print(f"   NPBackup version: {metadata.get('npbackup_version', 'N/A')}")

    def validate(self) -> bool:
        """Run all validation tests"""
        print("🔍 Validating extracted restic configuration...")
        print("=" * 50)

        success = True

        # Load configuration
        if not self.load_config():
            return False

        # Display summary
        self.display_configuration_summary()

        print("\n🧪 Running validation tests...")
        print("-" * 30)

        # Validate structure
        success &= self.validate_config_structure()

        # Test restic installation
        success &= self.test_restic_installation()

        # Validate backup paths
        success &= self.validate_backup_paths()

        # Test repository connection
        success &= self.test_repository_connection()

        print("\n" + "=" * 50)
        if success:
            print("✅ All validation tests passed!")
            print("\n🎉 Configuration is ready for import into TimeLocker")
        else:
            print("❌ Some validation tests failed!")
            print("\n⚠️  Please review the issues above before importing")

        return success


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Validate extracted restic configuration")
    parser.add_argument("config_file", help="Path to extracted configuration JSON file")

    args = parser.parse_args()

    validator = ConfigValidator(args.config_file)

    if validator.validate():
        print("\n📋 Next steps:")
        print("1. Import configuration into TimeLocker using import_to_timelocker.py")
        print("2. Test backup operations with TimeLocker")
        print("3. Consider migrating from cron to TimeLocker scheduling")
        sys.exit(0)
    else:
        print("\n💡 Suggestions:")
        print("1. Check repository credentials and network connectivity")
        print("2. Verify restic installation and version")
        print("3. Review backup paths and permissions")
        sys.exit(1)


if __name__ == "__main__":
    main()
