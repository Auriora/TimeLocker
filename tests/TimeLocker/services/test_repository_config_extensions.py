"""
Tests for RepositoryConfig Extensions and Validation

This module tests the enhanced RepositoryConfig data model extensions,
including engine selection, metadata, status tracking, and serialization.
"""

import pytest
from datetime import datetime
from pathlib import Path

from TimeLocker.interfaces.repository_management_models import (
    RepositoryConfig, BackupEngine, RepositoryType, RepositoryStatus,
    ResticEngineConfig, RsyncEngineConfig, RcloneEngineConfig,
    S3Config, ENGINE_CONFIGURATIONS, S3_COMPATIBLE_SERVICES
)


class TestRepositoryConfigExtensions:
    """Test RepositoryConfig extensions and enhancements"""

    def test_repository_config_basic_creation(self):
        """Test basic RepositoryConfig creation with required fields"""
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        assert config.name == "test-repo"
        assert config.uri == "file:///tmp/test-repo"
        assert config.engine == BackupEngine.RESTIC
        assert config.type == RepositoryType.LOCAL
        assert config.status == RepositoryStatus.INACTIVE
        assert config.is_default is False
        assert isinstance(config.metadata, dict)
        assert isinstance(config.engine_config, dict)

    def test_repository_config_with_engine_field(self):
        """Test RepositoryConfig with engine selection"""
        # Test Restic engine
        config = RepositoryConfig(
            name="restic-repo",
            uri="s3://bucket/path",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3
        )
        assert config.engine == BackupEngine.RESTIC
        
        # Test Rsync engine
        config = RepositoryConfig(
            name="rsync-repo",
            uri="file:///backup",
            engine=BackupEngine.RSYNC,
            type=RepositoryType.LOCAL
        )
        assert config.engine == BackupEngine.RSYNC
        
        # Test Rclone engine
        config = RepositoryConfig(
            name="rclone-repo",
            uri="s3://bucket/path",
            engine=BackupEngine.RCLONE,
            type=RepositoryType.S3
        )
        assert config.engine == BackupEngine.RCLONE

    def test_repository_config_with_metadata(self):
        """Test RepositoryConfig with metadata field"""
        metadata = {
            "owner": "admin",
            "department": "IT",
            "backup_schedule": "daily",
            "retention_days": 30
        }
        
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            metadata=metadata
        )
        
        assert config.metadata == metadata
        assert config.metadata["owner"] == "admin"
        assert config.metadata["retention_days"] == 30

    def test_repository_config_with_engine_config(self):
        """Test RepositoryConfig with engine-specific configuration"""
        engine_config = {
            "compression": "max",
            "pack_size": 2048,
            "exclude_caches": True
        }
        
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            engine_config=engine_config
        )
        
        assert config.engine_config == engine_config
        assert config.engine_config["compression"] == "max"
        assert config.engine_config["pack_size"] == 2048

    def test_repository_config_status_tracking(self):
        """Test RepositoryConfig status and validation tracking fields"""
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        # Test default status
        assert config.status == RepositoryStatus.INACTIVE
        assert config.last_validated is None
        assert config.validation_errors == []
        assert config.performance_warnings == []
        
        # Test status update
        config.status = RepositoryStatus.ACTIVE
        assert config.status == RepositoryStatus.ACTIVE
        
        # Test validation tracking
        config.last_validated = datetime.utcnow()
        config.validation_errors.append("Connection timeout")
        config.performance_warnings.append("Slow response time")
        
        assert config.last_validated is not None
        assert len(config.validation_errors) == 1
        assert len(config.performance_warnings) == 1

    def test_repository_config_validation_on_init(self):
        """Test RepositoryConfig validation during initialization"""
        # Test empty name validation
        with pytest.raises(ValueError, match="Repository name cannot be empty"):
            RepositoryConfig(
                name="",
                uri="file:///tmp/test-repo",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
        
        # Test empty URI validation
        with pytest.raises(ValueError, match="Repository URI cannot be empty"):
            RepositoryConfig(
                name="test-repo",
                uri="",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )

    def test_repository_config_to_dict(self):
        """Test RepositoryConfig serialization to dictionary"""
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Test repository",
            metadata={"key": "value"},
            engine_config={"compression": "auto"}
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["name"] == "test-repo"
        assert config_dict["uri"] == "file:///tmp/test-repo"
        assert config_dict["engine"] == "restic"
        assert config_dict["type"] == "local"
        assert config_dict["description"] == "Test repository"
        assert config_dict["metadata"] == {"key": "value"}
        assert config_dict["engine_config"] == {"compression": "auto"}
        assert config_dict["status"] == "inactive"
        assert config_dict["is_default"] is False
        assert "created_at" in config_dict
        assert "updated_at" in config_dict

    def test_repository_config_from_dict(self):
        """Test RepositoryConfig deserialization from dictionary"""
        now = datetime.utcnow()
        data = {
            "name": "test-repo",
            "uri": "file:///tmp/test-repo",
            "engine": "restic",
            "type": "local",
            "description": "Test repository",
            "metadata": {"key": "value"},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "is_default": True,
            "engine_config": {"compression": "auto"},
            "status": "active",
            "last_validated": now.isoformat(),
            "validation_errors": ["error1"],
            "performance_warnings": ["warning1"]
        }
        
        config = RepositoryConfig.from_dict(data)
        
        assert config.name == "test-repo"
        assert config.uri == "file:///tmp/test-repo"
        assert config.engine == BackupEngine.RESTIC
        assert config.type == RepositoryType.LOCAL
        assert config.description == "Test repository"
        assert config.metadata == {"key": "value"}
        assert config.is_default is True
        assert config.engine_config == {"compression": "auto"}
        assert config.status == RepositoryStatus.ACTIVE
        assert config.last_validated is not None
        assert config.validation_errors == ["error1"]
        assert config.performance_warnings == ["warning1"]

    def test_repository_config_roundtrip_serialization(self):
        """Test RepositoryConfig serialization roundtrip"""
        original = RepositoryConfig(
            name="test-repo",
            uri="s3://bucket/path",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3,
            description="Test S3 repository",
            metadata={"region": "us-west-2"},
            engine_config={"compression": "max"},
            is_default=True
        )
        
        # Serialize and deserialize
        config_dict = original.to_dict()
        restored = RepositoryConfig.from_dict(config_dict)
        
        # Verify all fields match
        assert restored.name == original.name
        assert restored.uri == original.uri
        assert restored.engine == original.engine
        assert restored.type == original.type
        assert restored.description == original.description
        assert restored.metadata == original.metadata
        assert restored.engine_config == original.engine_config
        assert restored.is_default == original.is_default


class TestEngineConfigurationClasses:
    """Test engine-specific configuration classes"""

    def test_restic_engine_config(self):
        """Test ResticEngineConfig data class"""
        config = ResticEngineConfig(
            compression="max",
            pack_size=2048,
            cache_dir="/tmp/cache",
            exclude_caches=False,
            one_file_system=True
        )
        
        assert config.compression == "max"
        assert config.pack_size == 2048
        assert config.cache_dir == "/tmp/cache"
        assert config.exclude_caches is False
        assert config.one_file_system is True

    def test_restic_engine_config_defaults(self):
        """Test ResticEngineConfig default values"""
        config = ResticEngineConfig()
        
        assert config.compression == "auto"
        assert config.pack_size is None
        assert config.cache_dir is None
        assert config.exclude_caches is True
        assert config.one_file_system is False

    def test_restic_engine_config_serialization(self):
        """Test ResticEngineConfig serialization"""
        config = ResticEngineConfig(compression="max", pack_size=2048)
        
        config_dict = config.to_dict()
        assert config_dict["compression"] == "max"
        assert config_dict["pack_size"] == 2048
        
        restored = ResticEngineConfig.from_dict(config_dict)
        assert restored.compression == config.compression
        assert restored.pack_size == config.pack_size

    def test_rsync_engine_config(self):
        """Test RsyncEngineConfig data class"""
        config = RsyncEngineConfig(
            archive_mode=False,
            compress=False,
            delete_excluded=True,
            preserve_permissions=False,
            preserve_times=False,
            dry_run=True
        )
        
        assert config.archive_mode is False
        assert config.compress is False
        assert config.delete_excluded is True
        assert config.preserve_permissions is False
        assert config.preserve_times is False
        assert config.dry_run is True

    def test_rsync_engine_config_defaults(self):
        """Test RsyncEngineConfig default values"""
        config = RsyncEngineConfig()
        
        assert config.archive_mode is True
        assert config.compress is True
        assert config.delete_excluded is False
        assert config.preserve_permissions is True
        assert config.preserve_times is True
        assert config.dry_run is False

    def test_rsync_engine_config_serialization(self):
        """Test RsyncEngineConfig serialization"""
        config = RsyncEngineConfig(archive_mode=False, compress=False)
        
        config_dict = config.to_dict()
        assert config_dict["archive_mode"] is False
        assert config_dict["compress"] is False
        
        restored = RsyncEngineConfig.from_dict(config_dict)
        assert restored.archive_mode == config.archive_mode
        assert restored.compress == config.compress

    def test_rclone_engine_config(self):
        """Test RcloneEngineConfig data class"""
        config = RcloneEngineConfig(
            config_file="/etc/rclone.conf",
            transfers=8,
            checkers=16,
            buffer_size="32M",
            use_mmap=True
        )
        
        assert config.config_file == "/etc/rclone.conf"
        assert config.transfers == 8
        assert config.checkers == 16
        assert config.buffer_size == "32M"
        assert config.use_mmap is True

    def test_rclone_engine_config_defaults(self):
        """Test RcloneEngineConfig default values"""
        config = RcloneEngineConfig()
        
        assert config.config_file is None
        assert config.transfers == 4
        assert config.checkers == 8
        assert config.buffer_size == "16M"
        assert config.use_mmap is False

    def test_rclone_engine_config_serialization(self):
        """Test RcloneEngineConfig serialization"""
        config = RcloneEngineConfig(transfers=8, buffer_size="32M")
        
        config_dict = config.to_dict()
        assert config_dict["transfers"] == 8
        assert config_dict["buffer_size"] == "32M"
        
        restored = RcloneEngineConfig.from_dict(config_dict)
        assert restored.transfers == config.transfers
        assert restored.buffer_size == config.buffer_size

    def test_engine_configurations_mapping(self):
        """Test ENGINE_CONFIGURATIONS mapping"""
        assert BackupEngine.RESTIC in ENGINE_CONFIGURATIONS
        assert BackupEngine.RSYNC in ENGINE_CONFIGURATIONS
        assert BackupEngine.RCLONE in ENGINE_CONFIGURATIONS
        
        assert ENGINE_CONFIGURATIONS[BackupEngine.RESTIC] == ResticEngineConfig
        assert ENGINE_CONFIGURATIONS[BackupEngine.RSYNC] == RsyncEngineConfig
        assert ENGINE_CONFIGURATIONS[BackupEngine.RCLONE] == RcloneEngineConfig


class TestS3Configuration:
    """Test S3-compatible service configuration"""

    def test_s3_config_creation(self):
        """Test S3Config creation"""
        config = S3Config(
            endpoint="s3.amazonaws.com",
            region="us-west-2",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            bucket="my-bucket",
            path_prefix="backups/",
            use_ssl=True,
            verify_ssl=True,
            connection_timeout=60,
            read_timeout=600
        )
        
        assert config.endpoint == "s3.amazonaws.com"
        assert config.region == "us-west-2"
        assert config.bucket == "my-bucket"
        assert config.path_prefix == "backups/"
        assert config.use_ssl is True
        assert config.verify_ssl is True
        assert config.connection_timeout == 60
        assert config.read_timeout == 600

    def test_s3_config_defaults(self):
        """Test S3Config default values"""
        config = S3Config(endpoint="s3.amazonaws.com")
        
        assert config.region is None
        assert config.access_key_id == ""
        assert config.secret_access_key == ""
        assert config.bucket == ""
        assert config.path_prefix is None
        assert config.use_ssl is True
        assert config.verify_ssl is True
        assert config.connection_timeout == 30
        assert config.read_timeout == 300

    def test_s3_config_serialization_excludes_credentials(self):
        """Test S3Config serialization excludes sensitive data"""
        config = S3Config(
            endpoint="s3.amazonaws.com",
            region="us-west-2",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            bucket="my-bucket"
        )
        
        config_dict = config.to_dict()
        
        # Verify credentials are excluded
        assert "access_key_id" not in config_dict
        assert "secret_access_key" not in config_dict
        
        # Verify other fields are included
        assert config_dict["endpoint"] == "s3.amazonaws.com"
        assert config_dict["region"] == "us-west-2"
        assert config_dict["bucket"] == "my-bucket"

    def test_s3_config_deserialization(self):
        """Test S3Config deserialization"""
        data = {
            "endpoint": "s3.amazonaws.com",
            "region": "us-west-2",
            "bucket": "my-bucket",
            "path_prefix": "backups/",
            "use_ssl": True,
            "verify_ssl": False,
            "connection_timeout": 60,
            "read_timeout": 600
        }
        
        config = S3Config.from_dict(data)
        
        assert config.endpoint == "s3.amazonaws.com"
        assert config.region == "us-west-2"
        assert config.bucket == "my-bucket"
        assert config.path_prefix == "backups/"
        assert config.use_ssl is True
        assert config.verify_ssl is False
        assert config.connection_timeout == 60
        assert config.read_timeout == 600

    def test_s3_compatible_services_configuration(self):
        """Test S3_COMPATIBLE_SERVICES configuration"""
        assert "minio" in S3_COMPATIBLE_SERVICES
        assert "wasabi" in S3_COMPATIBLE_SERVICES
        assert "backblaze" in S3_COMPATIBLE_SERVICES
        assert "digitalocean" in S3_COMPATIBLE_SERVICES
        
        # Test MinIO configuration
        minio_config = S3_COMPATIBLE_SERVICES["minio"]
        assert minio_config["default_port"] == 9000
        assert minio_config["supports_regions"] is False
        
        # Test Wasabi configuration
        wasabi_config = S3_COMPATIBLE_SERVICES["wasabi"]
        assert "endpoint_template" in wasabi_config
        assert "{region}" in wasabi_config["endpoint_template"]
        
        # Test Backblaze configuration
        backblaze_config = S3_COMPATIBLE_SERVICES["backblaze"]
        assert "endpoint_template" in backblaze_config
        
        # Test DigitalOcean configuration
        do_config = S3_COMPATIBLE_SERVICES["digitalocean"]
        assert "endpoint_template" in do_config
