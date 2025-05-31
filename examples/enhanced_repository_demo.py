#!/usr/bin/env python3
"""
Enhanced LocalResticRepository Demo

This script demonstrates the completed enhanced repository management functionality:
- Enhanced repository initialization with error handling
- Comprehensive repository health validation
- Configuration management and repository information
- Secure credential integration
- Error diagnosis and recovery suggestions
"""

import tempfile
import shutil
import json
from pathlib import Path

# Add src to path for demo
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.security import CredentialManager
from TimeLocker.restic.Repositories.local import LocalResticRepository


def main():
    """Demonstrate enhanced repository management features"""

    # Create temporary directories for demo
    temp_dir = Path(tempfile.mkdtemp())
    repo_path = temp_dir / "enhanced_demo_repo"
    credential_path = temp_dir / "credentials"

    print("🔧 Enhanced LocalResticRepository Demo")
    print("=" * 50)

    try:
        # 1. Demonstrate Enhanced Credential Management
        print("\n1. Setting up enhanced credential management...")
        credential_manager = CredentialManager(config_dir=credential_path)
        master_password = "demo_master_password_123"

        # Unlock credential store
        credential_manager.unlock(master_password)
        print("   ✓ Credential store unlocked")

        # 2. Create repository with enhanced initialization
        print("\n2. Creating repository with enhanced initialization...")
        repo_password = "secure_repo_password_456"

        # Create repository instance
        repository = LocalResticRepository(
                location=str(repo_path),
                credential_manager=credential_manager
        )

        print(f"   ✓ Repository created at: {repository.location()}")
        print(f"   ✓ Repository ID: {repository.repository_id()}")

        # 3. Demonstrate repository health validation (before setup)
        print("\n3. Initial repository health check...")
        health = repository.validate_repository_health()
        print(f"   Repository healthy: {health['healthy']}")
        print(f"   Issues found: {len(health['issues'])}")
        for issue in health['issues']:
            print(f"     - {issue}")
        print(f"   Warnings: {len(health['warnings'])}")
        for warning in health['warnings']:
            print(f"     - {warning}")

        # 4. Demonstrate enhanced repository setup
        print("\n4. Setting up repository with enhanced error handling...")

        # Mock the actual restic commands for demo purposes
        def mock_initialize():
            # Create config file to simulate successful initialization
            repo_path.mkdir(parents=True, exist_ok=True)
            (repo_path / "config").write_text(json.dumps({
                    "version":            2,
                    "id":                 "demo-repository-id",
                    "chunker_polynomial": "25b468838dcb75"
            }))
            return True

        def mock_check():
            return True

        # Temporarily replace methods for demo
        original_initialize = repository.initialize
        original_check = repository.check
        repository.initialize = mock_initialize
        repository.check = mock_check

        try:
            setup_result = repository.setup_repository_with_credentials(repo_password)
            print(f"   ✓ Repository setup successful: {setup_result}")
        finally:
            # Restore original methods
            repository.initialize = original_initialize
            repository.check = original_check

        # 5. Demonstrate repository information gathering
        print("\n5. Gathering detailed repository information...")
        info = repository.get_repository_info()
        print(f"   Location: {info['location']}")
        print(f"   Type: {info['type']}")
        print(f"   Repository ID: {info['repository_id']}")
        print(f"   Initialized: {info['initialized']}")
        print(f"   Directory exists: {info['directory_exists']}")
        print(f"   Writable: {info['writable']}")
        print(f"   Size: {info['size_bytes']} bytes")
        print(f"   Config available: {'config' in info and bool(info['config'])}")

        # 6. Demonstrate health validation after setup
        print("\n6. Repository health check after setup...")
        health = repository.validate_repository_health()
        print(f"   Repository healthy: {health['healthy']}")
        print("   Health checks:")
        for check_name, result in health['checks'].items():
            status = "✓" if result else "✗"
            print(f"     {status} {check_name}: {result}")

        if health['issues']:
            print("   Issues:")
            for issue in health['issues']:
                print(f"     - {issue}")

        # 7. Demonstrate credential management integration
        print("\n7. Testing credential management integration...")

        # Test password retrieval
        retrieved_password = repository.password()
        print(f"   ✓ Password retrieved: {'***' if retrieved_password else 'None'}")

        # Test credential storage
        stored = repository.store_password(repo_password)
        print(f"   ✓ Password stored in credential manager: {stored}")

        # List stored repositories
        stored_repos = credential_manager.list_repositories()
        print(f"   ✓ Repositories in credential store: {len(stored_repos)}")

        # 8. Demonstrate error diagnosis
        print("\n8. Repository error diagnosis and solutions...")
        common_issues = repository.get_common_repository_issues()
        print(f"   Available issue solutions: {len(common_issues)}")
        print("   Common issues and solutions:")
        for issue, solution in list(common_issues.items())[:3]:  # Show first 3
            print(f"     Issue: {issue}")
            print(f"     Solution: {solution}")
            print()

        # 9. Demonstrate repository state checking
        print("\n9. Repository state verification...")
        print(f"   Repository initialized: {repository.is_repository_initialized()}")
        print(f"   Directory created: {repo_path.exists()}")
        print(f"   Config file exists: {(repo_path / 'config').exists()}")

        # 10. Demonstrate multiple repository management
        print("\n10. Multiple repository management...")

        # Create second repository
        repo2_path = temp_dir / "second_repo"
        repo2 = LocalResticRepository(
                location=str(repo2_path),
                credential_manager=credential_manager
        )

        # Setup second repository
        repo2_password = "second_repo_password_789"

        # Mock setup for second repo
        def mock_initialize2():
            repo2_path.mkdir(parents=True, exist_ok=True)
            (repo2_path / "config").write_text(json.dumps({
                    "version": 2,
                    "id":      "second-repository-id"
            }))
            return True

        original_initialize2 = repo2.initialize
        original_check2 = repo2.check
        repo2.initialize = mock_initialize2
        repo2.check = mock_check

        try:
            setup2_result = repo2.setup_repository_with_credentials(repo2_password)
            print(f"   ✓ Second repository setup: {setup2_result}")
        finally:
            repo2.initialize = original_initialize2
            repo2.check = original_check2

        # Verify both repositories are managed
        stored_repos = credential_manager.list_repositories()
        print(f"   ✓ Total repositories managed: {len(stored_repos)}")
        print(f"   ✓ Repository IDs: {[repo_id[:8] + '...' for repo_id in stored_repos]}")

        print("\n✅ Enhanced repository management demo completed successfully!")
        print("\nKey features demonstrated:")
        print("  • Enhanced repository initialization with error handling")
        print("  • Comprehensive health validation and diagnostics")
        print("  • Detailed repository information gathering")
        print("  • Secure credential management integration")
        print("  • Multiple repository management")
        print("  • Error diagnosis and recovery suggestions")
        print("  • Repository state verification")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up temporary directory: {temp_dir}")


if __name__ == "__main__":
    main()
