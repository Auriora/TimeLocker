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
Tests for Wrapper Registry System

This module tests the wrapper registry functionality.
"""

import pytest
from typing import Set, Dict, List, Any
from pathlib import Path

from TimeLocker.services.wrapper_registry import (
    WrapperRegistry,
    get_wrapper_registry,
    initialize_wrappers
)
from TimeLocker.services.plugin_wrapper import (
    PluginWrapper,
    BackupConfig,
    PluginWrapperError
)
from TimeLocker.services.tool_manager import Feature
from TimeLocker.interfaces.data_models import BackupResult, BackupStatus


class TestWrapperOne(PluginWrapper):
    """Test wrapper implementation 1"""
    
    def __init__(self):
        super().__init__("test_tool_1")
    
    def get_native_capabilities(self) -> Set[Feature]:
        return {Feature.FULL_BACKUP, Feature.ENCRYPTION}
    
    def get_wrapper_capabilities(self) -> Set[Feature]:
        return {Feature.REGEX_PATTERNS}
    
    def execute_backup(self, config: BackupConfig) -> BackupResult:
        return self._create_backup_result(BackupStatus.COMPLETED)
    
    def validate_configuration(self, config: BackupConfig) -> Dict[str, Any]:
        return {'is_valid': True, 'errors': [], 'warnings': []}
    
    def translate_selection_rules(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Dict[str, List[str]]:
        return {'include': include_patterns, 'exclude': exclude_patterns, 'unsupported': []}


class TestWrapperTwo(PluginWrapper):
    """Test wrapper implementation 2"""
    
    def __init__(self):
        super().__init__("test_tool_2")
    
    def get_native_capabilities(self) -> Set[Feature]:
        return {Feature.FULL_BACKUP, Feature.COMPRESSION, Feature.PARALLEL_PROCESSING}
    
    def get_wrapper_capabilities(self) -> Set[Feature]:
        return {Feature.ENCRYPTION}
    
    def execute_backup(self, config: BackupConfig) -> BackupResult:
        return self._create_backup_result(BackupStatus.COMPLETED)
    
    def validate_configuration(self, config: BackupConfig) -> Dict[str, Any]:
        return {'is_valid': True, 'errors': [], 'warnings': []}
    
    def translate_selection_rules(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Dict[str, List[str]]:
        return {'include': include_patterns, 'exclude': exclude_patterns, 'unsupported': []}


@pytest.fixture
def clean_registry():
    """Provide a clean registry for each test"""
    registry = WrapperRegistry()
    registry.clear()
    yield registry
    registry.clear()


class TestWrapperRegistry:
    """Test suite for WrapperRegistry"""
    
    def test_singleton_pattern(self):
        """Test that registry follows singleton pattern"""
        registry1 = WrapperRegistry()
        registry2 = WrapperRegistry()
        assert registry1 is registry2
    
    def test_register_wrapper(self, clean_registry):
        """Test wrapper registration"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        
        assert clean_registry.is_tool_supported('test1')
        assert 'test1' in clean_registry.get_supported_tools()
    
    def test_register_multiple_wrappers(self, clean_registry):
        """Test registering multiple wrappers"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        clean_registry.register_wrapper('test2', TestWrapperTwo)
        
        supported = clean_registry.get_supported_tools()
        assert len(supported) == 2
        assert 'test1' in supported
        assert 'test2' in supported
    
    def test_register_invalid_wrapper(self, clean_registry):
        """Test registering invalid wrapper class"""
        class NotAWrapper:
            pass
        
        with pytest.raises(PluginWrapperError):
            clean_registry.register_wrapper('invalid', NotAWrapper)
    
    def test_get_wrapper(self, clean_registry):
        """Test getting wrapper instance"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        
        wrapper = clean_registry.get_wrapper('test1')
        assert isinstance(wrapper, TestWrapperOne)
        assert wrapper.tool_name == "test_tool_1"
    
    def test_get_wrapper_case_insensitive(self, clean_registry):
        """Test getting wrapper with different case"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        
        wrapper1 = clean_registry.get_wrapper('test1')
        wrapper2 = clean_registry.get_wrapper('TEST1')
        wrapper3 = clean_registry.get_wrapper('Test1')
        
        assert wrapper1 is wrapper2
        assert wrapper2 is wrapper3
    
    def test_get_wrapper_not_registered(self, clean_registry):
        """Test getting unregistered wrapper"""
        with pytest.raises(PluginWrapperError) as exc_info:
            clean_registry.get_wrapper('nonexistent')
        
        assert "No wrapper registered" in str(exc_info.value)
    
    def test_get_wrapper_caching(self, clean_registry):
        """Test that wrapper instances are cached"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        
        wrapper1 = clean_registry.get_wrapper('test1')
        wrapper2 = clean_registry.get_wrapper('test1')
        
        assert wrapper1 is wrapper2
    
    def test_is_tool_supported(self, clean_registry):
        """Test checking tool support"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        
        assert clean_registry.is_tool_supported('test1')
        assert clean_registry.is_tool_supported('TEST1')
        assert not clean_registry.is_tool_supported('test2')
    
    def test_get_wrapper_info(self, clean_registry):
        """Test getting wrapper information"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        
        info = clean_registry.get_wrapper_info('test1')
        
        assert info['tool_name'] == "test_tool_1"
        assert info['native_count'] == 2
        assert info['wrapper_count'] == 1
        assert info['total_features'] == 3
    
    def test_get_all_wrapper_info(self, clean_registry):
        """Test getting all wrapper information"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        clean_registry.register_wrapper('test2', TestWrapperTwo)
        
        all_info = clean_registry.get_all_wrapper_info()
        
        assert len(all_info) == 2
        assert 'test1' in all_info
        assert 'test2' in all_info
    
    def test_find_wrappers_with_capability(self, clean_registry):
        """Test finding wrappers by capability"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        clean_registry.register_wrapper('test2', TestWrapperTwo)
        
        # Both support FULL_BACKUP
        full_backup_tools = clean_registry.find_wrappers_with_capability(
            Feature.FULL_BACKUP
        )
        assert len(full_backup_tools) == 2
        
        # Only test1 supports REGEX_PATTERNS
        regex_tools = clean_registry.find_wrappers_with_capability(
            Feature.REGEX_PATTERNS
        )
        assert len(regex_tools) == 1
        assert 'test1' in regex_tools
        
        # Only test2 supports PARALLEL_PROCESSING
        parallel_tools = clean_registry.find_wrappers_with_capability(
            Feature.PARALLEL_PROCESSING
        )
        assert len(parallel_tools) == 1
        assert 'test2' in parallel_tools
    
    def test_find_wrappers_with_native_capability(self, clean_registry):
        """Test finding wrappers with native capability"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        clean_registry.register_wrapper('test2', TestWrapperTwo)
        
        # Both have native FULL_BACKUP
        native_full_backup = clean_registry.find_wrappers_with_native_capability(
            Feature.FULL_BACKUP
        )
        assert len(native_full_backup) == 2
        
        # Only test1 has native ENCRYPTION
        native_encryption = clean_registry.find_wrappers_with_native_capability(
            Feature.ENCRYPTION
        )
        assert len(native_encryption) == 1
        assert 'test1' in native_encryption
        
        # No native REGEX_PATTERNS (test1 has it as wrapper)
        native_regex = clean_registry.find_wrappers_with_native_capability(
            Feature.REGEX_PATTERNS
        )
        assert len(native_regex) == 0
    
    def test_compare_wrappers(self, clean_registry):
        """Test comparing wrapper capabilities"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        clean_registry.register_wrapper('test2', TestWrapperTwo)
        
        comparison = clean_registry.compare_wrappers(['test1', 'test2'])
        
        assert comparison['tools'] == ['test1', 'test2']
        assert len(comparison['capabilities']) > 0
        
        # Check FULL_BACKUP (both support it natively)
        full_backup_key = Feature.FULL_BACKUP.value
        assert full_backup_key in comparison['capabilities']
        assert comparison['capabilities'][full_backup_key]['test1']['native'] is True
        assert comparison['capabilities'][full_backup_key]['test2']['native'] is True
        
        # Check ENCRYPTION (test1 native, test2 wrapper)
        encryption_key = Feature.ENCRYPTION.value
        assert encryption_key in comparison['capabilities']
        assert comparison['capabilities'][encryption_key]['test1']['native'] is True
        assert comparison['capabilities'][encryption_key]['test2']['wrapper'] is True
    
    def test_unregister_wrapper(self, clean_registry):
        """Test unregistering wrapper"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        assert clean_registry.is_tool_supported('test1')
        
        result = clean_registry.unregister_wrapper('test1')
        assert result is True
        assert not clean_registry.is_tool_supported('test1')
        
        # Unregistering again should return False
        result = clean_registry.unregister_wrapper('test1')
        assert result is False
    
    def test_clear(self, clean_registry):
        """Test clearing all wrappers"""
        clean_registry.register_wrapper('test1', TestWrapperOne)
        clean_registry.register_wrapper('test2', TestWrapperTwo)
        
        assert len(clean_registry.get_supported_tools()) == 2
        
        clean_registry.clear()
        
        assert len(clean_registry.get_supported_tools()) == 0


class TestGlobalRegistry:
    """Test suite for global registry functions"""
    
    def test_get_wrapper_registry(self):
        """Test getting global registry"""
        registry1 = get_wrapper_registry()
        registry2 = get_wrapper_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, WrapperRegistry)
    
    def test_initialize_wrappers(self):
        """Test wrapper initialization"""
        # This will attempt to register real wrappers
        initialize_wrappers()
        
        registry = get_wrapper_registry()
        supported = registry.get_supported_tools()
        
        # Should have at least Restic wrapper
        assert 'restic' in supported


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
