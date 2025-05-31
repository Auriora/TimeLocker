#!/usr/bin/env python3
"""
TimeLocker Repository Management Demo

This script demonstrates the completed Phase 1 functionality:
- Repository creation and configuration
- Secure credential management
- Repository validation
"""

import tempfile
import shutil
from pathlib import Path

# Add src to path for demo
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.backup_manager import BackupManager
from TimeLocker.security import CredentialManager
from TimeLocker.restic.Repositories.local import LocalResticRepository


def main():
    """Demonstrate repository management functionality"""
    print("=== TimeLocker Repository Management Demo ===\n")

    # Create temporary directories for demo
    temp_dir = Path(tempfile.mkdtemp())
    repo_path = temp_dir / "demo_repository"
    credential_path = temp_dir / "credentials"

    try:
        # 1. Demonstrate Credential Manager
        print("1. Setting up secure credential management...")
        credential_manager = CredentialManager(config_dir=credential_path)
        master_password = "demo_master_password_123"

        # Unlock credential store
        credential_manager.unlock(master_password)
        print("   ✓ Credential store unlocked")

        # 2. Create repository with credential management
        print("\n2. Creating local repository with credential management...")
        repo_password = "secure_repo_password_456"

        # Create repository instance
        repository = LocalResticRepository(
                location=str(repo_path),
                password=repo_password,
                credential_manager=credential_manager
        )

        print(f"   ✓ Repository created at: {repository.location()}")
        print(f"   ✓ Repository ID: {repository.repository_id()}")

        # Store password in credential manager
        stored = repository.store_password(repo_password)
        print(f"   ✓ Password stored securely: {stored}")

        # 3. Demonstrate repository validation
        print("\n3. Validating repository configuration...")

        # Create repository directory
        created = repository.create_repository_directory()
        print(f"   ✓ Repository directory created: {created}")
        print(f"   ✓ Directory exists: {repo_path.exists()}")

        # 4. Demonstrate password retrieval priority
        print("\n4. Testing password retrieval priority...")

        # Create new repository instance (simulating restart)
        repository2 = LocalResticRepository(
                location=str(repo_path),
                credential_manager=credential_manager
        )

        retrieved_password = repository2.password()
        print(f"   ✓ Password retrieved from credential manager: {retrieved_password == repo_password}")

        # 5. Demonstrate BackupManager integration
        print("\n5. Testing BackupManager integration...")

        # Create repository via BackupManager
        uri = f"local:{repo_path}"
        repository3 = BackupManager.from_uri(uri, password=repo_password)
        print(f"   ✓ Repository created via BackupManager: {type(repository3).__name__}")
        print(f"   ✓ Repository location: {repository3.location()}")

        # 6. Demonstrate credential persistence
        print("\n6. Testing credential persistence...")

        # Lock and unlock credential manager
        credential_manager.lock()
        print("   ✓ Credential store locked")

        credential_manager.unlock(master_password)
        print("   ✓ Credential store unlocked")

        # List stored repositories
        repositories = credential_manager.list_repositories()
        print(f"   ✓ Stored repositories: {len(repositories)}")
        for repo_id in repositories:
            stored_password = credential_manager.get_repository_password(repo_id)
            print(f"     - {repo_id}: {'✓' if stored_password else '✗'}")

        print("\n=== Demo completed successfully! ===")
        print("\nPhase 1 (Repository Management) features demonstrated:")
        print("✓ Secure credential storage with encryption")
        print("✓ Repository creation and validation")
        print("✓ Password management with priority handling")
        print("✓ BackupManager integration")
        print("✓ Credential persistence across sessions")

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
