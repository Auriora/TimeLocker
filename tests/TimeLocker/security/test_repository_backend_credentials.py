"""Tests for per-repository backend credential management in CredentialManager.

Focus:
- store_repository_backend_credentials
- get_repository_backend_credentials
- remove_repository_backend_credentials
- has_repository_backend_credentials
- Encryption at rest (no plaintext secrets in stored file)
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from TimeLocker.security import CredentialManager, CredentialManagerError


@pytest.mark.security
class TestRepositoryBackendCredentials:
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cm = CredentialManager(config_dir=self.temp_dir)
        self.master_password = "test_master_password_repo_backend"
        self.cm.unlock(self.master_password)

    def teardown_method(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.unit
    def test_store_and_retrieve_repository_backend_credentials(self):
        repo_id = "repoA"
        backend_type = "s3"
        creds = {
                "access_key_id":     "AKIAEXAMPLE123456",
                "secret_access_key": "secret_example_key_value_1234567890",
                "region":            "us-east-1",
                "insecure_tls":      False,
        }

        # Store
        self.cm.store_repository_backend_credentials(repo_id, backend_type, creds)

        # Retrieve
        retrieved = self.cm.get_repository_backend_credentials(repo_id, backend_type)
        assert retrieved == creds

        # has_repository_backend_credentials should be True
        assert self.cm.has_repository_backend_credentials(repo_id, backend_type) is True

    @pytest.mark.unit
    def test_access_tracking_for_repository_backend_credentials(self):
        repo_id = "repoTrack"
        backend_type = "s3"
        creds = {"access_key_id": "AKIATRACK", "secret_access_key": "secret_track", "region": "us-west-2"}
        self.cm.store_repository_backend_credentials(repo_id, backend_type, creds)

        # Access multiple times
        for _ in range(3):
            self.cm.get_repository_backend_credentials(repo_id, backend_type)

        # Inspect internal metadata to confirm access_count incremented
        internal = self.cm._load_credentials()  # noqa: SLF001 (accessing protected member for test insight)
        backend_meta = internal["repository_backends"][repo_id][backend_type]
        assert backend_meta["access_count"] == 3
        assert "last_accessed" in backend_meta

    @pytest.mark.unit
    def test_remove_repository_backend_credentials(self):
        repo_id = "repoRemove"
        # Store two backend credential sets
        self.cm.store_repository_backend_credentials(repo_id, "s3", {"access_key_id": "A", "secret_access_key": "B"})
        self.cm.store_repository_backend_credentials(repo_id, "b2", {"account_id": "id", "account_key": "key"})

        # Remove one (should still have the repo entry for remaining backend)
        removed = self.cm.remove_repository_backend_credentials(repo_id, "s3")
        assert removed is True
        assert self.cm.get_repository_backend_credentials(repo_id, "s3") == {}
        assert self.cm.has_repository_backend_credentials(repo_id, "b2") is True

        # Remove second (repository entry should be cleaned up)
        removed2 = self.cm.remove_repository_backend_credentials(repo_id, "b2")
        assert removed2 is True
        internal = self.cm._load_credentials()
        assert repo_id not in internal.get("repository_backends", {})

        # Removing non-existent returns False
        assert self.cm.remove_repository_backend_credentials(repo_id, "s3") is False

    @pytest.mark.unit
    def test_has_repository_backend_credentials_locked_behavior(self):
        repo_id = "repoLockState"
        self.cm.store_repository_backend_credentials(repo_id, "s3", {"access_key_id": "A", "secret_access_key": "B"})
        assert self.cm.has_repository_backend_credentials(repo_id, "s3") is True

        # Lock manager - has_repository_backend_credentials should return False (no exception)
        self.cm.lock()
        assert self.cm.has_repository_backend_credentials(repo_id, "s3") is False

    @pytest.mark.unit
    def test_get_repository_backend_credentials_when_locked_raises(self):
        repo_id = "repoLocked"
        self.cm.store_repository_backend_credentials(repo_id, "s3", {"access_key_id": "A", "secret_access_key": "B"})
        self.cm.lock()
        with pytest.raises(CredentialManagerError):
            self.cm.get_repository_backend_credentials(repo_id, "s3")

    @pytest.mark.unit
    def test_store_repository_backend_credentials_validation(self):
        with pytest.raises(CredentialManagerError):
            self.cm.store_repository_backend_credentials("", "s3", {})
        with pytest.raises(CredentialManagerError):
            self.cm.store_repository_backend_credentials("repo", "", {})

    @pytest.mark.unit
    def test_retrieving_nonexistent_repository_backend_credentials(self):
        assert self.cm.get_repository_backend_credentials("no_repo", "s3") == {}
        assert self.cm.has_repository_backend_credentials("no_repo", "s3") is False

    @pytest.mark.unit
    def test_encryption_at_rest_for_repository_backend_credentials(self):
        repo_id = "repoEnc"
        backend_type = "s3"
        secret_value = "super_secret_value_at_rest_123"
        creds = {"access_key_id": "ACCESSKEYREST", "secret_access_key": secret_value, "region": "eu-central-1"}
        self.cm.store_repository_backend_credentials(repo_id, backend_type, creds)

        # Ensure file exists
        enc_file = self.cm.credentials_file
        assert enc_file.exists()
        raw_bytes = enc_file.read_bytes()

        # Plaintext secret should not appear in encrypted file
        assert secret_value.encode() not in raw_bytes
        assert creds["access_key_id"].encode() not in raw_bytes

        # Lock and unlock again to ensure retrieval still works (persistence + encryption)
        self.cm.lock()
        self.cm.unlock(self.master_password)
        retrieved = self.cm.get_repository_backend_credentials(repo_id, backend_type)
        assert retrieved == creds

    @pytest.mark.unit
    def test_multiple_backend_types_independence(self):
        repo_id = "repoMulti"
        s3_creds = {"access_key_id": "AKIA123", "secret_access_key": "S3SECRET", "region": "us-east-2"}
        b2_creds = {"account_id": "B2ID", "account_key": "B2KEY"}
        self.cm.store_repository_backend_credentials(repo_id, "s3", s3_creds)
        self.cm.store_repository_backend_credentials(repo_id, "b2", b2_creds)

        assert self.cm.get_repository_backend_credentials(repo_id, "s3") == s3_creds
        assert self.cm.get_repository_backend_credentials(repo_id, "b2") == b2_creds

        # Removing one should not affect the other
        self.cm.remove_repository_backend_credentials(repo_id, "s3")
        assert self.cm.get_repository_backend_credentials(repo_id, "s3") == {}
        assert self.cm.get_repository_backend_credentials(repo_id, "b2") == b2_creds
