"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.services.tool_manager import (
    ToolManager,
    ToolCapabilities,
    ToolInfo,
    Feature,
    Limitation,
    PerformanceProfile
)
from TimeLocker.interfaces.data_models import (
    BackupJobConfig,
    BackupJob,
    ExecutionMode,
    ToolConfiguration,
    ExecutionContext
)


class TestToolManager:
    """Test suite for ToolManager"""
    
    def test_initialization(self):
        """Test ToolManager initialization"""
        manager = ToolManager()
        
        assert manager is not None
        assert hasattr(manager, '_capabilities_cache')
        assert hasattr(manager, '_tool_detectors')
        assert 'restic' in manager._tool_detectors
        assert 'borg' in manager._tool_detectors
        assert 'duplicity' in manager._tool_detectors
    
    def test_get_tool_capabilities_restic(self):
        """Test getting Restic capabilities"""
        manager = ToolManager()
        
        capabilities = manager.get_tool_capabilities('restic')
        
        assert capabilities.tool_name == 'restic'
        assert capabilities.version is not None
        assert len(capabilities.native_features) > 0
        assert Feature.INCREMENTAL_BACKUP in capabilities.native_features
        assert Feature.ENCRYPTION in capabilities.native_features
        assert Feature.DATA_DEDUPLICATION in capabilities.native_features
    
    def test_get_tool_capabilities_borg(self):
        """Test getting Borg capabilities"""
        manager = ToolManager()
        
        capabilities = manager.get_tool_capabilities('borg')
        
        assert capabilities.tool_name == 'borg'
        assert capabilities.version is not None
        assert len(capabilities.native_features) > 0
        assert Feature.INCREMENTAL_BACKUP in capabilities.native_features
        assert Feature.ENCRYPTION in capabilities.native_features
    
    def test_get_tool_capabilities_duplicity(self):
        """Test getting Duplicity capabilities"""
        manager = ToolManager()
        
        capabilities = manager.get_tool_capabilities('duplicity')
        
        assert capabilities.tool_name == 'duplicity'
        assert capabilities.version is not None
        assert len(capabilities.native_features) > 0
        assert Feature.INCREMENTAL_BACKUP in capabilities.native_features
    
    def test_get_tool_capabilities_unsupported(self):
        """Test getting capabilities for unsupported tool"""
        manager = ToolManager()
        
        with pytest.raises(ValueError, match="Unsupported tool type"):
            manager.get_tool_capabilities('unsupported_tool')
    
    def test_capabilities_caching(self):
        """Test that capabilities are cached"""
        manager = ToolManager()
        
        # First call should detect and cache
        cap1 = manager.get_tool_capabilities('restic')
        
        # Second call should return cached version
        cap2 = manager.get_tool_capabilities('restic')
        
        assert cap1 is cap2  # Same object reference
    
    def test_configure_tool_for_job(self):
        """Test tool configuration for a job"""
        manager = ToolManager()
        
        job_config = BackupJobConfig(
            job_id="test-job",
            repository_id="test-repo",
            target_names=["test-target"],
            priority=5
        )
        
        job = BackupJob(
            config=job_config,
            source_paths=["/test/path"],
            execution_context=ExecutionContext(start_time=time.time())
        )
        
        config = manager.configure_tool_for_job('restic', job)
        
        assert config.tool_type == 'restic'
        assert config.parallel_operations >= 1
        assert config.encryption_enabled is True
        assert config.integrity_check_enabled is True
        assert isinstance(config.tool_specific_options, dict)
    
    def test_configure_tool_high_priority_job(self):
        """Test configuration for high priority job"""
        manager = ToolManager()
        
        job_config = BackupJobConfig(
            job_id="high-priority-job",
            repository_id="test-repo",
            target_names=["test-target"],
            priority=9  # High priority
        )
        
        job = BackupJob(
            config=job_config,
            source_paths=["/test/path"],
            execution_context=ExecutionContext(start_time=time.time())
        )
        
        config = manager.configure_tool_for_job('restic', job)
        
        # High priority should get more parallel operations
        assert config.parallel_operations > 1
        # High priority should get lower compression
        assert config.compression_level is not None
        assert config.compression_level <= 3
    
    def test_get_supported_tools(self):
        """Test getting list of supported tools"""
        manager = ToolManager()
        
        tools = manager.get_supported_tools()
        
        assert len(tools) > 0
        assert all(isinstance(tool, ToolInfo) for tool in tools)
        
        tool_names = [tool.tool_name for tool in tools]
        assert 'restic' in tool_names
        assert 'borg' in tool_names
        assert 'duplicity' in tool_names
    
    def test_validate_job_compatibility(self):
        """Test job compatibility validation"""
        manager = ToolManager()
        
        job_config = BackupJobConfig(
            job_id="test-job",
            repository_id="test-repo",
            target_names=["test-target"]
        )
        
        job = BackupJob(
            config=job_config,
            source_paths=["/test/path"],
            exclude_patterns=["*.tmp"],
            execution_context=ExecutionContext(start_time=time.time())
        )
        
        result = manager.validate_job_compatibility('restic', job)
        
        assert 'is_compatible' in result
        assert 'warnings' in result
        assert 'missing_features' in result
        assert 'recommendations' in result
        assert isinstance(result['is_compatible'], bool)
    
    def test_validate_job_with_encryption(self):
        """Test validation for job requiring encryption"""
        manager = ToolManager()
        
        job_config = BackupJobConfig(
            job_id="encrypted-job",
            repository_id="test-repo",
            target_names=["test-target"]
        )
        
        job = BackupJob(
            config=job_config,
            source_paths=["/test/path"],
            tool_configuration=ToolConfiguration(
                tool_type='restic',
                encryption_enabled=True
            ),
            execution_context=ExecutionContext(start_time=time.time())
        )
        
        result = manager.validate_job_compatibility('restic', job)
        
        # Restic supports encryption, so should be compatible
        assert result['is_compatible'] is True
        assert Feature.ENCRYPTION not in result['missing_features']


class TestToolCapabilities:
    """Test suite for ToolCapabilities"""
    
    def test_all_features_property(self):
        """Test all_features property combines native and wrapper features"""
        capabilities = ToolCapabilities(
            tool_name="test",
            version="1.0",
            native_features={Feature.ENCRYPTION, Feature.COMPRESSION},
            wrapper_features={Feature.PARALLEL_PROCESSING}
        )
        
        all_features = capabilities.all_features
        
        assert len(all_features) == 3
        assert Feature.ENCRYPTION in all_features
        assert Feature.COMPRESSION in all_features
        assert Feature.PARALLEL_PROCESSING in all_features
    
    def test_has_feature(self):
        """Test has_feature method"""
        capabilities = ToolCapabilities(
            tool_name="test",
            version="1.0",
            native_features={Feature.ENCRYPTION},
            wrapper_features={Feature.PARALLEL_PROCESSING}
        )
        
        assert capabilities.has_feature(Feature.ENCRYPTION) is True
        assert capabilities.has_feature(Feature.PARALLEL_PROCESSING) is True
        assert capabilities.has_feature(Feature.DRY_RUN) is False
    
    def test_is_native_feature(self):
        """Test is_native_feature method"""
        capabilities = ToolCapabilities(
            tool_name="test",
            version="1.0",
            native_features={Feature.ENCRYPTION},
            wrapper_features={Feature.PARALLEL_PROCESSING}
        )
        
        assert capabilities.is_native_feature(Feature.ENCRYPTION) is True
        assert capabilities.is_native_feature(Feature.PARALLEL_PROCESSING) is False
    
    def test_is_wrapper_feature(self):
        """Test is_wrapper_feature method"""
        capabilities = ToolCapabilities(
            tool_name="test",
            version="1.0",
            native_features={Feature.ENCRYPTION},
            wrapper_features={Feature.PARALLEL_PROCESSING}
        )
        
        assert capabilities.is_wrapper_feature(Feature.PARALLEL_PROCESSING) is True
        assert capabilities.is_wrapper_feature(Feature.ENCRYPTION) is False


class TestPerformanceProfile:
    """Test suite for PerformanceProfile"""
    
    def test_default_values(self):
        """Test PerformanceProfile default values"""
        profile = PerformanceProfile()
        
        assert profile.cpu_usage == "medium"
        assert profile.memory_usage == "medium"
        assert profile.parallel_efficiency == 0.7
        assert profile.compression_overhead == "medium"
        assert profile.supports_resume is False
    
    def test_custom_values(self):
        """Test PerformanceProfile with custom values"""
        profile = PerformanceProfile(
            typical_throughput_mbps=150.0,
            cpu_usage="high",
            memory_usage="low",
            parallel_efficiency=0.9,
            supports_resume=True
        )
        
        assert profile.typical_throughput_mbps == 150.0
        assert profile.cpu_usage == "high"
        assert profile.memory_usage == "low"
        assert profile.parallel_efficiency == 0.9
        assert profile.supports_resume is True


class TestLimitation:
    """Test suite for Limitation"""
    
    def test_limitation_creation(self):
        """Test creating a Limitation"""
        limitation = Limitation(
            feature="test_feature",
            description="Test limitation",
            workaround="Use alternative approach",
            severity="high"
        )
        
        assert limitation.feature == "test_feature"
        assert limitation.description == "Test limitation"
        assert limitation.workaround == "Use alternative approach"
        assert limitation.severity == "high"
    
    def test_limitation_default_severity(self):
        """Test Limitation default severity"""
        limitation = Limitation(
            feature="test_feature",
            description="Test limitation"
        )
        
        assert limitation.severity == "medium"


class TestToolInfo:
    """Test suite for ToolInfo"""
    
    def test_tool_info_creation(self):
        """Test creating ToolInfo"""
        info = ToolInfo(
            tool_name="restic",
            version="0.16.0",
            is_available=True,
            feature_count=20,
            native_feature_count=18,
            wrapper_feature_count=2
        )
        
        assert info.tool_name == "restic"
        assert info.version == "0.16.0"
        assert info.is_available is True
        assert info.feature_count == 20
        assert info.native_feature_count == 18
        assert info.wrapper_feature_count == 2


class TestFeatureEnum:
    """Test suite for Feature enum"""
    
    def test_feature_values(self):
        """Test Feature enum values"""
        assert Feature.INCREMENTAL_BACKUP.value == "incremental_backup"
        assert Feature.ENCRYPTION.value == "encryption"
        assert Feature.PARALLEL_PROCESSING.value == "parallel_processing"
        assert Feature.DATA_DEDUPLICATION.value == "data_deduplication"
    
    def test_feature_membership(self):
        """Test Feature enum membership"""
        features = {
            Feature.ENCRYPTION,
            Feature.COMPRESSION,
            Feature.PARALLEL_PROCESSING
        }
        
        assert Feature.ENCRYPTION in features
        assert Feature.COMPRESSION in features
        assert Feature.DRY_RUN not in features


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
