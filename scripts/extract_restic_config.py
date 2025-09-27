#!/usr/bin/env python3
"""
Restic Configuration Extractor for TimeLocker
Extracts and converts restic/npbackup configuration to TimeLocker format
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
import re
from datetime import datetime


class ResticConfigExtractor:
    """Extract and convert restic/npbackup configuration to TimeLocker format"""

    def __init__(self, backup_dir: Optional[str] = None):
        self.backup_dir = Path(backup_dir) if backup_dir else Path("/tmp/restic_config_backup")
        self.restic_home = Path("/var/restic")
        self.npbackup_config = self.restic_home / ".config/npbackup/npbackup.conf"
        self.resticrc_file = self.restic_home / ".resticrc"

    def backup_original_configs(self) -> bool:
        """Backup original configuration files"""
        try:
            print(f"Creating backup directory: {self.backup_dir}")
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup .resticrc
            if self.resticrc_file.exists():
                shutil.copy2(self.resticrc_file, self.backup_dir / ".resticrc")
                print(f"Backed up {self.resticrc_file}")

            # Backup npbackup config directory
            npbackup_dir = self.restic_home / ".config/npbackup"
            if npbackup_dir.exists():
                shutil.copytree(npbackup_dir, self.backup_dir / "npbackup", dirs_exist_ok=True)
                print(f"Backed up {npbackup_dir}")

            # Create timestamp file
            timestamp_file = self.backup_dir / "backup_timestamp.txt"
            timestamp_file.write_text(f"Backup created: {datetime.now().isoformat()}\n")

            return True

        except Exception as e:
            print(f"Error backing up configurations: {e}")
            return False

    def extract_resticrc_config(self) -> Dict[str, str]:
        """Extract configuration from .resticrc file"""
        config = {}

        try:
            if not self.resticrc_file.exists():
                print(f"Warning: {self.resticrc_file} not found")
                return config

            with open(self.resticrc_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()

            print(f"Extracted {len(config)} variables from .resticrc")
            return config

        except Exception as e:
            print(f"Error reading .resticrc: {e}")
            return {}

    def extract_npbackup_config(self) -> Dict[str, Any]:
        """Extract configuration from npbackup.conf"""
        try:
            if not self.npbackup_config.exists():
                print(f"Warning: {self.npbackup_config} not found")
                return {}

            with open(self.npbackup_config, 'r') as f:
                config = yaml.safe_load(f)

            print(f"Loaded npbackup configuration with {len(config)} sections")
            return config

        except Exception as e:
            print(f"Error reading npbackup config: {e}")
            return {}

    def extract_exclude_files(self) -> Dict[str, List[str]]:
        """Extract exclude patterns from exclude files"""
        exclude_files = {
                'generic_excludes':            [],
                'generic_excluded_extensions': [],
                'linux_excludes':              []
        }

        npbackup_dir = self.restic_home / ".config/npbackup"

        for exclude_type in exclude_files.keys():
            exclude_file = npbackup_dir / exclude_type
            if exclude_file.exists():
                try:
                    with open(exclude_file, 'r') as f:
                        patterns = []
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                patterns.append(line)
                        exclude_files[exclude_type] = patterns
                        print(f"Loaded {len(patterns)} patterns from {exclude_type}")
                except Exception as e:
                    print(f"Error reading {exclude_file}: {e}")

        return exclude_files

    def convert_to_timelocker_config(self, resticrc: Dict[str, str],
                                     npbackup: Dict[str, Any],
                                     excludes: Dict[str, List[str]]) -> Dict[str, Any]:
        """Convert extracted configuration to TimeLocker format"""

        # Extract repository information
        repo_uri = resticrc.get('RESTIC_REPOSITORY', '')
        repo_password = resticrc.get('RESTIC_PASSWORD', '')

        # Extract AWS credentials
        aws_access_key = resticrc.get('AWS_ACCESS_KEY_ID', '')
        aws_secret_key = resticrc.get('AWS_SECRET_ACCESS_KEY', '')
        aws_region = resticrc.get('AWS_DEFAULT_REGION', '')

        # Extract backup paths from npbackup
        backup_paths = []
        backup_opts = {}
        retention_policy = {}

        if 'repos' in npbackup and 'default' in npbackup['repos']:
            default_repo = npbackup['repos']['default']
            backup_opts = default_repo.get('backup_opts', {})
            backup_paths = backup_opts.get('paths', [])
            retention_policy = default_repo.get('repo_opts', {}).get('retention_policy', {})

        # Combine all exclude patterns
        all_excludes = []
        for exclude_list in excludes.values():
            all_excludes.extend(exclude_list)

        # Add exclude patterns from npbackup config
        if backup_opts.get('exclude_patterns'):
            all_excludes.extend(backup_opts['exclude_patterns'])

        # Create TimeLocker configuration
        timelocker_config = {
                "repositories":        {
                        "extracted_restic_repo": {
                                "type":                    "s3",
                                "uri":                     repo_uri,
                                "description":             "Extracted from existing restic/npbackup setup",
                                "aws_region":              aws_region,
                                "encryption":              True,
                                "created_from_extraction": True
                        }
                },
                "backup_targets":      {
                        "extracted_backup_target": {
                                "paths":       backup_paths,
                                "repository":  "extracted_restic_repo",
                                "description": "Extracted from npbackup configuration",
                                "patterns":    {
                                        "exclude": all_excludes
                                }
                        }
                },
                "backup":              {
                        "compression":            backup_opts.get('compression', 'auto'),
                        "exclude_caches":         True,
                        "one_file_system":        backup_opts.get('one_file_system', False),
                        "check_before_backup":    True,
                        "verify_after_backup":    True,
                        "retention_keep_last":    retention_policy.get('last', 10),
                        "retention_keep_daily":   retention_policy.get('daily', 7),
                        "retention_keep_weekly":  retention_policy.get('weekly', 4),
                        "retention_keep_monthly": retention_policy.get('monthly', 12)
                },
                "credentials":         {
                        "aws_access_key_id":     aws_access_key,
                        "aws_secret_access_key": aws_secret_key,
                        "repository_password":   repo_password
                },
                "extraction_metadata": {
                        "extracted_at":           datetime.now().isoformat(),
                        "source_files":           [
                                str(self.resticrc_file),
                                str(self.npbackup_config)
                        ],
                        "original_cron_schedule": "30 17 * * *",  # From the cron job we found
                        "npbackup_version":       npbackup.get('conf_version', 'unknown')
                }
        }

        return timelocker_config

    def save_timelocker_config(self, config: Dict[str, Any], output_file: str) -> bool:
        """Save the converted configuration to a file"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"TimeLocker configuration saved to: {output_path}")
            return True

        except Exception as e:
            print(f"Error saving TimeLocker config: {e}")
            return False

    def extract_and_convert(self, output_file: str = "extracted_restic_config.json") -> bool:
        """Main method to extract and convert configuration"""
        print("Starting restic configuration extraction...")

        # Step 1: Backup original configurations
        if not self.backup_original_configs():
            print("Failed to backup original configurations")
            return False

        # Step 2: Extract configurations
        print("\nExtracting configurations...")
        resticrc_config = self.extract_resticrc_config()
        npbackup_config = self.extract_npbackup_config()
        exclude_patterns = self.extract_exclude_files()

        # Step 3: Convert to TimeLocker format
        print("\nConverting to TimeLocker format...")
        timelocker_config = self.convert_to_timelocker_config(
                resticrc_config, npbackup_config, exclude_patterns
        )

        # Step 4: Save converted configuration
        if self.save_timelocker_config(timelocker_config, output_file):
            print(f"\n✅ Configuration extraction completed successfully!")
            print(f"📁 Original configs backed up to: {self.backup_dir}")
            print(f"📄 TimeLocker config saved to: {output_file}")
            return True
        else:
            print("\n❌ Failed to save TimeLocker configuration")
            return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract restic/npbackup configuration for TimeLocker")
    parser.add_argument("-o", "--output", default="extracted_restic_config.json",
                        help="Output file for TimeLocker configuration")
    parser.add_argument("-b", "--backup-dir", default="/tmp/restic_config_backup",
                        help="Directory to backup original configurations")

    args = parser.parse_args()

    extractor = ResticConfigExtractor(backup_dir=args.backup_dir)

    if extractor.extract_and_convert(args.output):
        print("\n🎉 Ready to integrate with TimeLocker!")
        print("\nNext steps:")
        print("1. Review the generated configuration file")
        print("2. Test repository connection")
        print("3. Import into TimeLocker")
        sys.exit(0)
    else:
        print("\n💥 Extraction failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
