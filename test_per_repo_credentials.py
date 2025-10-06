#!/usr/bin/env python3
"""
Test script for per-repository backend credentials feature.

This script tests:
1. Adding S3 repository with credentials
2. Storing per-repository backend credentials
3. Retrieving per-repository backend credentials
4. Creating repository instances that use per-repository credentials
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from TimeLocker.config.configuration_schema import RepositoryConfig
from TimeLocker.security.credential_manager import CredentialManager
from TimeLocker.services.repository_factory import RepositoryFactory
from TimeLocker.restic.Repositories.s3 import S3ResticRepository


def test_repository_config_schema():
    """Test that RepositoryConfig has the has_backend_credentials field."""
    print("Testing RepositoryConfig schema...")
    
    repo = RepositoryConfig(
        name="test-repo",
        location="s3:minio.local/test-bucket",
        has_backend_credentials=True
    )
    
    assert hasattr(repo, 'has_backend_credentials'), "RepositoryConfig missing has_backend_credentials field"
    assert repo.has_backend_credentials == True, "has_backend_credentials not set correctly"
    
    # Test default value
    repo2 = RepositoryConfig(
        name="test-repo2",
        location="s3:minio.local/test-bucket2"
    )
    assert repo2.has_backend_credentials == False, "has_backend_credentials default should be False"
    
    print("✅ RepositoryConfig schema test passed")


def test_credential_manager_per_repo_methods():
    """Test CredentialManager per-repository backend credential methods."""
    print("\nTesting CredentialManager per-repository methods...")
    
    # Create temporary credential directory
    temp_dir = tempfile.mkdtemp()
    try:
        cred_manager = CredentialManager(config_dir=Path(temp_dir))

        # Unlock with auto-unlock
        if not cred_manager.auto_unlock():
            # If auto-unlock fails, use a test password
            cred_manager.unlock("test-password-123")

        # Verify the credential manager is actually unlocked
        if cred_manager.is_locked():
            raise RuntimeError("Failed to unlock credential manager for testing")
        
        # Test storing S3 credentials
        s3_creds = {
            "access_key_id": "test-access-key",
            "secret_access_key": "test-secret-key",
            "region": "us-east-1"
        }
        
        cred_manager.store_repository_backend_credentials("minio1", "s3", s3_creds)
        print("  ✓ Stored S3 credentials for minio1")
        
        # Test retrieving credentials
        retrieved_creds = cred_manager.get_repository_backend_credentials("minio1", "s3")
        assert retrieved_creds == s3_creds, "Retrieved credentials don't match stored credentials"
        print("  ✓ Retrieved S3 credentials for minio1")
        
        # Test has_repository_backend_credentials
        assert cred_manager.has_repository_backend_credentials("minio1", "s3"), "Should have credentials"
        assert not cred_manager.has_repository_backend_credentials("minio2", "s3"), "Should not have credentials"
        print("  ✓ has_repository_backend_credentials works correctly")
        
        # Test storing credentials for another repository
        s3_creds2 = {
            "access_key_id": "test-access-key-2",
            "secret_access_key": "test-secret-key-2",
            "region": "eu-west-1"
        }
        cred_manager.store_repository_backend_credentials("minio2", "s3", s3_creds2)
        print("  ✓ Stored S3 credentials for minio2")
        
        # Verify isolation - minio1 credentials should be unchanged
        retrieved_creds1 = cred_manager.get_repository_backend_credentials("minio1", "s3")
        assert retrieved_creds1 == s3_creds, "minio1 credentials were affected by minio2"
        print("  ✓ Credential isolation verified")
        
        # Test B2 credentials
        b2_creds = {
            "account_id": "test-account-id",
            "account_key": "test-account-key"
        }
        cred_manager.store_repository_backend_credentials("b2-repo", "b2", b2_creds)
        retrieved_b2 = cred_manager.get_repository_backend_credentials("b2-repo", "b2")
        assert retrieved_b2 == b2_creds, "B2 credentials don't match"
        print("  ✓ B2 credentials work correctly")
        
        # Test removing credentials
        removed = cred_manager.remove_repository_backend_credentials("minio1", "s3")
        assert removed, "Should have removed credentials"
        assert not cred_manager.has_repository_backend_credentials("minio1", "s3"), "Credentials should be removed"
        print("  ✓ Credential removal works correctly")
        
        print("✅ CredentialManager per-repository methods test passed")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_s3_repository_credential_resolution():
    """Test that S3ResticRepository uses per-repository credentials."""
    print("\nTesting S3ResticRepository credential resolution...")

    # Create temporary credential directory
    temp_dir = tempfile.mkdtemp()
    try:
        cred_manager = CredentialManager(config_dir=Path(temp_dir))

        # Unlock
        if not cred_manager.auto_unlock():
            cred_manager.unlock("test-password-123")

        # Verify the credential manager is actually unlocked
        if cred_manager.is_locked():
            raise RuntimeError("Failed to unlock credential manager for testing")

        # Store credentials for a repository
        s3_creds = {
            "access_key_id": "per-repo-access-key",
            "secret_access_key": "per-repo-secret-key",
            "region": "us-west-2"
        }
        cred_manager.store_repository_backend_credentials("test-s3-repo", "s3", s3_creds)

        # Use unittest.mock.patch for better test isolation and automatic cleanup
        with patch.object(S3ResticRepository, 'validate', lambda self: None):
            # Create S3 repository with repository_name
            repo = S3ResticRepository(
                location="s3:minio.local/test-bucket",
                credential_manager=cred_manager,
                repository_name="test-s3-repo"
            )

            # Verify credentials were loaded
            assert repo.aws_access_key_id == "per-repo-access-key", "Access key not loaded from credential manager"
            assert repo.aws_secret_access_key == "per-repo-secret-key", "Secret key not loaded from credential manager"
            assert repo.aws_default_region == "us-west-2", "Region not loaded from credential manager"
            print("  ✓ S3ResticRepository loaded per-repository credentials")

            # Test fallback to environment variables
            os.environ["AWS_ACCESS_KEY_ID"] = "env-access-key"
            os.environ["AWS_SECRET_ACCESS_KEY"] = "env-secret-key"

            repo2 = S3ResticRepository(
                location="s3:minio.local/test-bucket2",
                credential_manager=cred_manager,
                repository_name="non-existent-repo"
            )

            assert repo2.aws_access_key_id == "env-access-key", "Should fall back to environment variable"
            assert repo2.aws_secret_access_key == "env-secret-key", "Should fall back to environment variable"
            print("  ✓ S3ResticRepository falls back to environment variables")

            # Cleanup environment
            del os.environ["AWS_ACCESS_KEY_ID"]
            del os.environ["AWS_SECRET_ACCESS_KEY"]

        print("✅ S3ResticRepository credential resolution test passed")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_repository_factory_integration():
    """Test that RepositoryFactory passes repository_name correctly."""
    print("\nTesting RepositoryFactory integration...")

    # Create temporary credential directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Use unittest.mock.patch for better test isolation and automatic cleanup
        with patch.object(S3ResticRepository, 'validate', lambda self: None):
            # Create factory
            factory = RepositoryFactory()

            # Get credential manager and unlock
            cred_manager = factory._get_credential_manager()
            if cred_manager.is_locked():
                if not cred_manager.auto_unlock():
                    cred_manager.unlock("test-password-123")

            # Verify the credential manager is actually unlocked
            if cred_manager.is_locked():
                raise RuntimeError("Failed to unlock credential manager for testing")

            # Store credentials
            s3_creds = {
                "access_key_id": "factory-test-key",
                "secret_access_key": "factory-test-secret",
                "region": "ap-southeast-1"
            }
            cred_manager.store_repository_backend_credentials("factory-test-repo", "s3", s3_creds)

            # Create repository through factory with repository_name
            repo = factory.create_repository(
                uri="s3://minio.local/test-bucket",
                repository_name="factory-test-repo"
            )

            # Verify credentials were loaded
            assert isinstance(repo, S3ResticRepository), "Should create S3ResticRepository"
            assert repo.aws_access_key_id == "factory-test-key", "Factory didn't pass repository_name correctly"
            print("  ✓ RepositoryFactory passes repository_name correctly")

            print("✅ RepositoryFactory integration test passed")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing Per-Repository Backend Credentials Implementation")
    print("=" * 70)
    
    try:
        test_repository_config_schema()
        test_credential_manager_per_repo_methods()
        test_s3_repository_credential_resolution()
        test_repository_factory_integration()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

