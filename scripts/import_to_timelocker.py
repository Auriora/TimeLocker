#!/usr/bin/env python3
"""
Import extracted restic configuration into TimeLocker
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Add the src directory to the path so we can import TimeLocker modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from TimeLocker.config.configuration_manager import ConfigurationManager, ConfigSection
    from TimeLocker.security.credential_manager import CredentialManager
    from TimeLocker.restic.Repositories.local import LocalResticRepository
    from TimeLocker.backup_manager import BackupRepository
except ImportError as e:
    print(f"❌ Error importing TimeLocker modules: {e}")
    print("Make sure you're running this from the TimeLocker project directory")
    sys.exit(1)


class TimeLockerImporter:
    """Import extracted restic configuration into TimeLocker"""

    def __init__(self, config_file: str, timelocker_config_dir: Optional[str] = None):
        self.config_file = Path(config_file)
        self.timelocker_config_dir = Path(timelocker_config_dir) if timelocker_config_dir else None

        # Initialize TimeLocker components
        self.config_manager = ConfigurationManager(config_dir=self.timelocker_config_dir)
        self.credential_manager = None

    def load_extracted_config(self) -> Dict[str, Any]:
        """Load the extracted configuration file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            print(f"✅ Loaded extracted configuration from {self.config_file}")
            return config
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return {}

    def setup_credential_manager(self, master_password: str) -> bool:
        """Initialize and unlock the credential manager"""
        try:
            self.credential_manager = CredentialManager(
                    config_dir=self.config_manager.config_dir
            )

            # Try to unlock with provided password, or create new if doesn't exist
            if not self.credential_manager.unlock(master_password):
                print("🔐 Creating new credential store...")
                if not self.credential_manager.create_credential_store(master_password):
                    print("❌ Failed to create credential store")
                    return False
                if not self.credential_manager.unlock(master_password):
                    print("❌ Failed to unlock newly created credential store")
                    return False

            print("✅ Credential manager ready")
            return True

        except Exception as e:
            print(f"❌ Error setting up credential manager: {e}")
            return False

    def import_credentials(self, extracted_config: Dict[str, Any]) -> bool:
        """Import credentials into TimeLocker's credential manager"""
        if not self.credential_manager:
            print("❌ Credential manager not initialized")
            return False

        try:
            credentials = extracted_config.get('credentials', {})

            # Store repository password
            repo_password = credentials.get('repository_password')
            if repo_password:
                # Generate a repository ID for the extracted repo
                repo_info = extracted_config.get('repositories', {}).get('extracted_restic_repo', {})
                repo_uri = repo_info.get('uri', '')

                # Create a simple repository ID from the URI
                repo_id = f"extracted_{hash(repo_uri) % 10000}"

                if self.credential_manager.store_repository_password(repo_id, repo_password):
                    print(f"✅ Stored repository password for {repo_id}")
                else:
                    print(f"❌ Failed to store repository password")
                    return False

            # Store AWS credentials as environment variables in credential manager
            aws_access_key = credentials.get('aws_access_key_id')
            aws_secret_key = credentials.get('aws_secret_access_key')

            if aws_access_key and aws_secret_key:
                # Store AWS credentials (TimeLocker's credential manager might not have direct AWS support,
                # so we'll store them as generic credentials)
                if hasattr(self.credential_manager, 'store_credential'):
                    self.credential_manager.store_credential('aws_access_key_id', aws_access_key)
                    self.credential_manager.store_credential('aws_secret_access_key', aws_secret_key)
                    print("✅ Stored AWS credentials")
                else:
                    print("⚠️  AWS credentials need to be set as environment variables")
                    print(f"   export AWS_ACCESS_KEY_ID='{aws_access_key}'")
                    print(f"   export AWS_SECRET_ACCESS_KEY='{aws_secret_key}'")

            return True

        except Exception as e:
            print(f"❌ Error importing credentials: {e}")
            return False

    def import_repositories(self, extracted_config: Dict[str, Any]) -> bool:
        """Import repository configuration into TimeLocker"""
        try:
            repositories = extracted_config.get('repositories', {})

            for repo_name, repo_config in repositories.items():
                # Add repository to TimeLocker configuration
                repo_section = {
                        'type':                     repo_config.get('type', 's3'),
                        'uri':                      repo_config.get('uri', ''),
                        'description':              repo_config.get('description', ''),
                        'encryption':               repo_config.get('encryption', True),
                        'aws_region':               repo_config.get('aws_region', ''),
                        'imported_from_extraction': True
                }

                # Update TimeLocker configuration
                current_repos = self.config_manager.get_section(ConfigSection.REPOSITORIES)
                current_repos[repo_name] = repo_section
                self.config_manager.set_section(ConfigSection.REPOSITORIES, current_repos)

                print(f"✅ Imported repository: {repo_name}")

            return True

        except Exception as e:
            print(f"❌ Error importing repositories: {e}")
            return False

    def import_backup_settings(self, extracted_config: Dict[str, Any]) -> bool:
        """Import backup settings into TimeLocker"""
        try:
            backup_config = extracted_config.get('backup', {})

            # Update backup defaults
            current_backup = self.config_manager.get_section(ConfigSection.BACKUP)

            # Map extracted settings to TimeLocker format
            if 'compression' in backup_config:
                current_backup['compression'] = backup_config['compression']
            if 'one_file_system' in backup_config:
                current_backup['one_file_system'] = backup_config['one_file_system']
            if 'retention_keep_last' in backup_config:
                current_backup['retention_keep_last'] = backup_config['retention_keep_last']
            if 'retention_keep_daily' in backup_config:
                current_backup['retention_keep_daily'] = backup_config['retention_keep_daily']
            if 'retention_keep_weekly' in backup_config:
                current_backup['retention_keep_weekly'] = backup_config['retention_keep_weekly']
            if 'retention_keep_monthly' in backup_config:
                current_backup['retention_keep_monthly'] = backup_config['retention_keep_monthly']

            self.config_manager.set_section(ConfigSection.BACKUP, current_backup)
            print("✅ Imported backup settings")

            return True

        except Exception as e:
            print(f"❌ Error importing backup settings: {e}")
            return False

    def save_configuration(self) -> bool:
        """Save the updated TimeLocker configuration"""
        try:
            self.config_manager.save_config()
            print("✅ TimeLocker configuration saved")
            return True
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            return False

    def test_repository_connection(self, extracted_config: Dict[str, Any]) -> bool:
        """Test connection to the imported repository"""
        try:
            # Get repository information
            repo_info = extracted_config.get('repositories', {}).get('extracted_restic_repo', {})
            repo_uri = repo_info.get('uri', '')

            if not repo_uri:
                print("❌ No repository URI found")
                return False

            # Set up environment variables for testing
            credentials = extracted_config.get('credentials', {})
            test_env = os.environ.copy()

            if credentials.get('aws_access_key_id'):
                test_env['AWS_ACCESS_KEY_ID'] = credentials['aws_access_key_id']
            if credentials.get('aws_secret_access_key'):
                test_env['AWS_SECRET_ACCESS_KEY'] = credentials['aws_secret_access_key']
            if credentials.get('repository_password'):
                test_env['RESTIC_PASSWORD'] = credentials['repository_password']

            # Set AWS region
            aws_region = repo_info.get('aws_region')
            if aws_region:
                test_env['AWS_DEFAULT_REGION'] = aws_region

            print(f"🔍 Testing connection to repository: {repo_uri}")

            # Try to create a repository instance and validate
            try:
                repo = BackupRepository.from_uri(repo_uri, credentials.get('repository_password'))

                # Set environment for the test
                original_env = os.environ.copy()
                os.environ.update(test_env)

                try:
                    # Test if we can access the repository
                    repo.validate()
                    print("✅ Repository connection test successful")
                    return True
                finally:
                    # Restore original environment
                    os.environ.clear()
                    os.environ.update(original_env)

            except Exception as e:
                print(f"⚠️  Repository connection test failed: {e}")
                print("   This might be normal if credentials need to be set as environment variables")
                return False

        except Exception as e:
            print(f"❌ Error testing repository connection: {e}")
            return False

    def import_configuration(self, master_password: str) -> bool:
        """Main method to import the extracted configuration"""
        print("🚀 Starting TimeLocker configuration import...")

        # Load extracted configuration
        extracted_config = self.load_extracted_config()
        if not extracted_config:
            return False

        # Setup credential manager
        if not self.setup_credential_manager(master_password):
            return False

        # Import components
        success = True
        success &= self.import_credentials(extracted_config)
        success &= self.import_repositories(extracted_config)
        success &= self.import_backup_settings(extracted_config)

        if success:
            success &= self.save_configuration()

        if success:
            print("\n✅ Configuration import completed successfully!")

            # Test repository connection
            print("\n🔍 Testing repository connection...")
            self.test_repository_connection(extracted_config)

            # Display summary
            self.display_import_summary(extracted_config)

        return success

    def display_import_summary(self, extracted_config: Dict[str, Any]):
        """Display a summary of the imported configuration"""
        print("\n📊 Import Summary:")
        print("==================")

        repos = extracted_config.get('repositories', {})
        targets = extracted_config.get('backup_targets', {})
        metadata = extracted_config.get('extraction_metadata', {})

        print(f"🗂️  Repositories imported: {len(repos)}")
        for name, repo in repos.items():
            print(f"   📍 {name}: {repo.get('uri', 'N/A')}")

        print(f"📂 Backup targets: {len(targets)}")
        for name, target in targets.items():
            paths = target.get('paths', [])
            print(f"   📁 {name}: {len(paths)} paths")

        if metadata:
            print(f"⏰ Original extraction: {metadata.get('extracted_at', 'N/A')}")
            print(f"📅 Original cron schedule: {metadata.get('original_cron_schedule', 'N/A')}")

        print(f"\n📁 TimeLocker config directory: {self.config_manager.config_dir}")
        print(f"📄 Configuration file: {self.config_manager.config_file}")


def main():
    """Main entry point"""
    import argparse
    import getpass

    parser = argparse.ArgumentParser(description="Import extracted restic configuration into TimeLocker")
    parser.add_argument("config_file", help="Path to extracted configuration JSON file")
    parser.add_argument("-d", "--config-dir", help="TimeLocker configuration directory")
    parser.add_argument("-p", "--password", help="Master password for credential manager (will prompt if not provided)")

    args = parser.parse_args()

    # Get master password
    if args.password:
        master_password = args.password
    else:
        master_password = getpass.getpass("Enter master password for TimeLocker credential manager: ")

    if not master_password:
        print("❌ Master password is required")
        sys.exit(1)

    # Create importer and run import
    importer = TimeLockerImporter(args.config_file, args.config_dir)

    if importer.import_configuration(master_password):
        print("\n🎉 Import completed successfully!")
        print("\nNext steps:")
        print("1. Verify the imported configuration")
        print("2. Test backup operations")
        print("3. Consider scheduling with TimeLocker instead of cron")
        sys.exit(0)
    else:
        print("\n💥 Import failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
