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

"""
Tests for Plugin Wrapper System

This module tests the plugin wrapper base class and wrapper functionality.
"""

import pytest
from pathlib import Path
from typing import Set, Dict, List, Any

from TimeLocker.services.plugin_wrapper import (
    PluginWrapper,
    BackupConfig,
    PluginWrapperError,
    CapabilityNotSupportedError
)
from TimeLocker.services.tool_manager import Feature
from TimeLocker.interfaces.data_models import (
    BackupResult,
    BackupStatus,
    ToolConfiguration
)


class MockPluginWrapper(PluginWrapper):
    """Mock plugin wrapper for testing"""
    
    def __init__(self):
        super().__init__("mock_tool")
        self._native_caps = {
            Feature.FULL_BACKUP,
            Feature.ENCRYPTION,
            Feature.COMPRESSION
        }
        self._wrapper_caps = {
            Feature.REGEX_PATTERNS,
            Feature.PARALLEL_PROCESSING
        }
    
    def get_native_capabilities(self) -> Set[Feature]:
        return self._native_caps
    
    def get_wrapper_capabilities(self) -> Set[Feature]:
        return self._wrapper_caps
    
    def execute_backup(self, config: BackupConfig) -> BackupResult:
        return self._create_backup_result(
            status=BackupStatus.COMPLETED,
            snapshot_id="test_snapshot",
            files_processed=100,
            bytes_processed=1024000
        )
    
    def validate_configuration(self, config: BackupConfig) -> Dict[str, Any]:
        errors = []
        warnings = []
        
        if not config.source_paths:
            errors.append("Source paths required")
        if not config.repository_uri:
            errors.append("Repository URI required")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def translate_selection_rules(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Dict[str, List[str]]:
        return {
            'include': include_patterns,
            'exclude': exclude_patterns,
            'unsupported': []
        }


class TestPluginWrapper:
    """Test suite for PluginWrapper base class"""
    
    def test_initialization(self):
        """Test wrapper initialization"""
        wrapper = MockPluginWrapper()
        assert wrapper.tool_name == "mock_tool"
    
    def test_get_all_capabilities(self):
        """Test getting all capabilities"""
        wrapper = MockPluginWrapper()
        all_caps = wrapper.get_all_capabilities()
        
        assert Feature.FULL_BACKUP in all_caps
        assert Feature.ENCRYPTION in all_caps
        assert Feature.REGEX_PATTERNS in all_caps
        assert len(all_caps) == 5
    
    def test_has_capability(self):
        """Test capability checking"""
        wrapper = MockPluginWrapper()
        
        # Native capability
        assert wrapper.has_capability(Feature.ENCRYPTION)
        
        # Wrapper capability
        assert wrapper.has_capability(Feature.REGEX_PATTERNS)
        
        # Missing capability
        assert not wrapper.has_capability(Feature.SNAPSHOT_TAGGING)
    
    def test_is_native_capability(self):
        """Test native capability checking"""
        wrapper = MockPluginWrapper()
        
        assert wrapper.is_native_capability(Feature.ENCRYPTION)
        assert not wrapper.is_native_capability(Feature.REGEX_PATTERNS)
        assert not wrapper.is_native_capability(Feature.SNAPSHOT_TAGGING)
    
    def test_is_wrapper_capability(self):
        """Test wrapper capability checking"""
        wrapper = MockPluginWrapper()
        
        assert wrapper.is_wrapper_capability(Feature.REGEX_PATTERNS)
        assert not wrapper.is_wrapper_capability(Feature.ENCRYPTION)
        assert not wrapper.is_wrapper_capability(Feature.SNAPSHOT_TAGGING)
    
    def test_get_capability_info(self):
        """Test getting capability information"""
        wrapper = MockPluginWrapper()
        info = wrapper.get_capability_info()
        
        assert info['tool_name'] == "mock_tool"
        assert info['native_count'] == 3
        assert info['wrapper_count'] == 2
        assert info['total_features'] == 5
        assert len(info['native_features']) == 3
        assert len(info['wrapper_features']) == 2
    
    def test_check_required_capabilities_all_supported(self):
        """Test checking required capabilities when all are supported"""
        wrapper = MockPluginWrapper()
        
        required = {
            Feature.FULL_BACKUP,
            Feature.ENCRYPTION,
            Feature.REGEX_PATTERNS
        }
        
        result = wrapper.check_required_capabilities(required)
        
        assert result['all_supported'] is True
        assert len(result['missing_features']) == 0
        assert Feature.FULL_BACKUP in result['native_features']
        assert Feature.REGEX_PATTERNS in result['wrapper_features']
    
    def test_check_required_capabilities_missing(self):
        """Test checking required capabilities with missing features"""
        wrapper = MockPluginWrapper()
        
        required = {
            Feature.FULL_BACKUP,
            Feature.SNAPSHOT_TAGGING,  # Not supported
            Feature.DATA_DEDUPLICATION  # Not supported
        }
        
        result = wrapper.check_required_capabilities(required)
        
        assert result['all_supported'] is False
        assert len(result['missing_features']) == 2
        assert Feature.SNAPSHOT_TAGGING in result['missing_features']
        assert Feature.DATA_DEDUPLICATION in result['missing_features']


class TestBackupConfig:
    """Test suite for BackupConfig"""
    
    def test_basic_config(self):
        """Test basic configuration creation"""
        config = BackupConfig(
            source_paths=[Path("/tmp/test")],
            repository_uri="/tmp/repo"
        )
        
        assert len(config.source_paths) == 1
        assert config.repository_uri == "/tmp/repo"
        assert config.dry_run is False
        assert len(config.tags) == 0
    
    def test_config_with_patterns(self):
        """Test configuration with patterns"""
        config = BackupConfig(
            source_paths=[Path("/tmp/test")],
            repository_uri="/tmp/repo",
            include_patterns=["*.py"],
            exclude_patterns=["*.pyc", "__pycache__"]
        )
        
        assert len(config.include_patterns) == 1
        assert len(config.exclude_patterns) == 2
    
    def test_config_with_tool_configuration(self):
        """Test configuration with tool settings"""
        tool_config = ToolConfiguration(
            tool_type="restic",
            parallel_operations=4,
            compression_level=6
        )
        
        config = BackupConfig(
            source_paths=[Path("/tmp/test")],
            repository_uri="/tmp/repo",
            tool_configuration=tool_config
        )
        
        assert config.tool_configuration is not None
        assert config.tool_configuration.parallel_operations == 4
        assert config.tool_configuration.compression_level == 6


class TestMockPluginWrapper:
    """Test suite for mock wrapper implementation"""
    
    def test_execute_backup(self):
        """Test backup execution"""
        wrapper = MockPluginWrapper()
        
        config = BackupConfig(
            source_paths=[Path("/tmp/test")],
            repository_uri="/tmp/repo"
        )
        
        result = wrapper.execute_backup(config)
        
        assert result.status == BackupStatus.COMPLETED
        assert result.snapshot_id == "test_snapshot"
        assert result.files_processed == 100
        assert result.bytes_processed == 1024000
    
    def test_validate_valid_configuration(self):
        """Test validation of valid configuration"""
        wrapper = MockPluginWrapper()
        
        config = BackupConfig(
            source_paths=[Path("/tmp/test")],
            repository_uri="/tmp/repo"
        )
        
        validation = wrapper.validate_configuration(config)
        
        assert validation['is_valid'] is True
        assert len(validation['errors']) == 0
    
    def test_validate_invalid_configuration(self):
        """Test validation of invalid configuration"""
        wrapper = MockPluginWrapper()
        
        config = BackupConfig(
            source_paths=[],
            repository_uri=""
        )
        
        validation = wrapper.validate_configuration(config)
        
        assert validation['is_valid'] is False
        assert len(validation['errors']) == 2
        assert "Source paths required" in validation['errors']
        assert "Repository URI required" in validation['errors']
    
    def test_translate_selection_rules(self):
        """Test pattern translation"""
        wrapper = MockPluginWrapper()
        
        include = ["*.py", "*.txt"]
        exclude = ["*.pyc", "__pycache__"]
        
        result = wrapper.translate_selection_rules(include, exclude)
        
        assert result['include'] == include
        assert result['exclude'] == exclude
        assert len(result['unsupported']) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
