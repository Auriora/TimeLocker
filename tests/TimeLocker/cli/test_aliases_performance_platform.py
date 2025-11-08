"""
Tests for CLI aliases, performance monitoring, and platform compatibility.

This test module covers:
- Command alias resolution and shortcuts (Task 8.1)
- Performance monitoring and optimization (Task 8.2)
- Cross-platform compatibility (Task 8.3)
"""

import pytest
import time
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.cli_modules.helpers.aliases import (
    CommandAliasResolver,
    resolve_command_alias,
    is_command_ambiguous,
    suggest_similar_commands,
    get_all_shortcuts,
)
from TimeLocker.cli_modules.helpers.performance import (
    PerformanceMetrics,
    PerformanceMonitor,
    ProgressIndicator,
    CancellationHandler,
    get_performance_monitor,
    track_command_performance,
)
from TimeLocker.cli_modules.helpers.platform_compat import (
    Platform,
    PlatformInfo,
    PathHandler,
    CredentialHandler,
    ErrorMessageFormatter,
    PlatformCapabilities,
    get_platform_name,
    normalize_path,
    format_error_message,
    check_platform_compatibility,
)


class TestCommandAliasResolver:
    """Test command alias resolution and shortcuts."""
    
    def test_resolve_known_shortcuts(self):
        """Test resolving known command shortcuts."""
        resolver = CommandAliasResolver()
        
        assert resolver.resolve_alias("repo") == "repos"
        assert resolver.resolve_alias("sel") == "selections"
        assert resolver.resolve_alias("pol") == "policies"
        # Note: "backup" is a valid command, so it returns itself
        # The shortcut "backup" -> "backup run" is for convenience but backup is valid
        assert resolver.resolve_alias("repository") == "repos"
        assert resolver.resolve_alias("selection") == "selections"
    
    def test_resolve_valid_commands(self):
        """Test that valid commands are returned unchanged."""
        resolver = CommandAliasResolver()
        
        assert resolver.resolve_alias("repos") == "repos"
        assert resolver.resolve_alias("selections") == "selections"
        assert resolver.resolve_alias("backup") == "backup"  # Valid command returns itself
    
    def test_resolve_unambiguous_prefix(self):
        """Test unambiguous prefix matching."""
        resolver = CommandAliasResolver()
        
        # "repo" should match "repos" unambiguously
        assert resolver.resolve_alias("repo") == "repos"
        
        # "snap" should match "snapshots"
        assert resolver.resolve_alias("snap") == "snapshots"
    
    def test_ambiguous_prefix_detection(self):
        """Test detection of ambiguous prefixes."""
        resolver = CommandAliasResolver()
        
        # "re" is ambiguous (repos, restore, reports)
        is_ambig, matches = resolver.is_ambiguous("re")
        assert is_ambig is True
        assert len(matches) > 1
        assert "repos" in matches or "restore" in matches
    
    def test_suggest_similar_commands(self):
        """Test command suggestion for typos."""
        resolver = CommandAliasResolver()
        
        suggestions = resolver.suggest_command("repoz")
        assert "repos" in suggestions or "reports" in suggestions
        
        suggestions = resolver.suggest_command("selectons")
        assert "selections" in suggestions
    
    def test_get_shortcut_help(self):
        """Test getting all shortcuts."""
        resolver = CommandAliasResolver()
        shortcuts = resolver.get_shortcut_help()
        
        assert isinstance(shortcuts, dict)
        assert "repo" in shortcuts
        assert shortcuts["repo"] == "repos"
    
    def test_expand_command_path(self):
        """Test expanding command paths with aliases."""
        resolver = CommandAliasResolver()
        
        assert resolver.expand_command_path("repo list") == "repos list"
        assert resolver.expand_command_path("sel create mysel") == "selections create mysel"
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        assert resolve_command_alias("repo") == "repos"
        
        is_ambig, matches = is_command_ambiguous("re")
        assert isinstance(is_ambig, bool)
        assert isinstance(matches, list)
        
        suggestions = suggest_similar_commands("repoz")
        assert isinstance(suggestions, list)
        
        shortcuts = get_all_shortcuts()
        assert isinstance(shortcuts, dict)


class TestPerformanceMonitoring:
    """Test performance monitoring and optimization."""
    
    def test_performance_metrics_creation(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(command_name="test_command")
        
        assert metrics.command_name == "test_command"
        assert metrics.start_time > 0
        assert metrics.end_time is None
        assert metrics.duration_ms is None
    
    def test_performance_metrics_completion(self):
        """Test completing performance metrics."""
        metrics = PerformanceMetrics(command_name="test_command")
        time.sleep(0.1)  # Simulate work
        metrics.complete()
        
        assert metrics.end_time is not None
        assert metrics.duration_ms is not None
        assert metrics.duration_ms >= 100  # At least 100ms
    
    def test_performance_threshold_detection(self):
        """Test detection of slow operations."""
        metrics = PerformanceMetrics(command_name="test_command")
        
        # Simulate fast operation
        metrics.duration_ms = 100
        assert not metrics.is_slow(is_complex=False)
        
        # Simulate slow simple operation
        metrics.duration_ms = 300
        assert metrics.is_slow(is_complex=False)
        
        # Same duration is OK for complex operation
        assert not metrics.is_slow(is_complex=True)
    
    def test_performance_warning_generation(self):
        """Test generation of performance warnings."""
        metrics = PerformanceMetrics(command_name="test_command")
        metrics.duration_ms = 300
        
        warning = metrics.get_performance_warning(is_complex=False)
        assert warning is not None
        assert "test_command" in warning
        assert "300" in warning
    
    def test_performance_monitor_tracking(self):
        """Test performance monitor command tracking."""
        monitor = PerformanceMonitor()
        
        with monitor.track_command("test_command") as metrics:
            time.sleep(0.05)  # Simulate work
            assert metrics.command_name == "test_command"
        
        # Check metrics were recorded
        recorded_metrics = monitor.get_metrics("test_command")
        assert recorded_metrics is not None
        assert recorded_metrics.duration_ms is not None
    
    def test_performance_monitor_multiple_commands(self):
        """Test tracking multiple commands."""
        monitor = PerformanceMonitor()
        
        with monitor.track_command("command1"):
            pass
        
        with monitor.track_command("command2"):
            pass
        
        all_metrics = monitor.get_all_metrics()
        assert len(all_metrics) == 2
        assert "command1" in all_metrics
        assert "command2" in all_metrics
    
    def test_progress_indicator_context(self):
        """Test progress indicator context manager."""
        indicator = ProgressIndicator()
        
        with indicator.show_progress("Test operation", total=10) as update:
            for i in range(10):
                update(advance=1)
        
        assert not indicator.is_active()
    
    def test_cancellation_handler_registration(self):
        """Test registering cleanup callbacks."""
        handler = CancellationHandler()
        
        cleanup_called = []
        handler.register_cleanup(lambda: cleanup_called.append(True))
        
        assert len(handler._cleanup_callbacks) == 1
    
    def test_cancellation_handler_context(self):
        """Test cancellation handler context manager."""
        handler = CancellationHandler()
        
        with handler.handle_cancellation():
            assert not handler.is_cancelled()
        
        assert not handler.is_cancelled()
    
    def test_global_performance_monitor(self):
        """Test global performance monitor instance."""
        monitor = get_performance_monitor()
        assert isinstance(monitor, PerformanceMonitor)
    
    def test_track_command_performance_convenience(self):
        """Test convenience function for tracking performance."""
        with track_command_performance("test_command") as metrics:
            assert metrics.command_name == "test_command"


class TestPlatformCompatibility:
    """Test cross-platform compatibility utilities."""
    
    def test_platform_detection(self):
        """Test platform detection."""
        detected_platform = PlatformInfo.get_platform()
        assert isinstance(detected_platform, Platform)
        assert detected_platform != Platform.UNKNOWN
    
    def test_platform_name(self):
        """Test getting platform name."""
        name = PlatformInfo.get_platform_name()
        assert name in ["Windows", "macOS", "Linux"]
    
    def test_platform_checks(self):
        """Test platform check functions."""
        # At least one should be true
        assert (
            PlatformInfo.is_windows() or
            PlatformInfo.is_macos() or
            PlatformInfo.is_linux()
        )
    
    def test_system_info(self):
        """Test getting system information."""
        info = PlatformInfo.get_system_info()
        
        assert "platform" in info
        assert "system" in info
        assert "python_version" in info
    
    def test_path_normalization(self):
        """Test path normalization."""
        path = "~/test/path"
        normalized = PathHandler.normalize_path(path)
        
        assert isinstance(normalized, Path)
        assert normalized.is_absolute()
    
    def test_platform_path_conversion(self):
        """Test platform-specific path conversion."""
        path = "/test/path"
        platform_path = PathHandler.to_platform_path(path)
        
        assert isinstance(platform_path, str)
        # On Windows, should have backslashes; on Unix, forward slashes
        if PlatformInfo.is_windows():
            assert "\\" in platform_path or ":" in platform_path
        else:
            assert "/" in platform_path
    
    def test_config_directory_detection(self):
        """Test platform-appropriate config directory."""
        config_dir = PathHandler.get_config_dir()
        
        assert isinstance(config_dir, Path)
        assert "TimeLocker" in str(config_dir) or "timelocker" in str(config_dir)
    
    def test_cache_directory_detection(self):
        """Test platform-appropriate cache directory."""
        cache_dir = PathHandler.get_cache_dir()
        
        assert isinstance(cache_dir, Path)
        assert "TimeLocker" in str(cache_dir) or "timelocker" in str(cache_dir)
    
    def test_data_directory_detection(self):
        """Test platform-appropriate data directory."""
        data_dir = PathHandler.get_data_dir()
        
        assert isinstance(data_dir, Path)
        assert "TimeLocker" in str(data_dir) or "timelocker" in str(data_dir)
    
    def test_absolute_path_check(self):
        """Test absolute path checking."""
        assert PathHandler.is_absolute_path("/absolute/path")
        assert not PathHandler.is_absolute_path("relative/path")
    
    def test_path_joining(self):
        """Test platform-appropriate path joining."""
        joined = PathHandler.join_paths("part1", "part2", "part3")
        
        assert "part1" in joined
        assert "part2" in joined
        assert "part3" in joined
    
    def test_credential_backend_detection(self):
        """Test credential backend detection."""
        backend = CredentialHandler.get_credential_backend()
        
        assert isinstance(backend, str)
        assert len(backend) > 0
    
    def test_credential_storage_info(self):
        """Test getting credential storage information."""
        info = CredentialHandler.get_credential_storage_info()
        
        assert "backend" in info
        assert "available" in info
        assert "platform" in info
    
    def test_error_message_formatting(self):
        """Test platform-appropriate error message formatting."""
        path_error = ErrorMessageFormatter.format_path_error("/test/path", "Path not found")
        assert "Path not found" in path_error
        assert "/test/path" in path_error or "\\test\\path" in path_error
        
        perm_error = ErrorMessageFormatter.format_permission_error("/test/path", "read file")
        assert "Permission denied" in perm_error
        assert "read file" in perm_error
        
        cmd_error = ErrorMessageFormatter.format_command_not_found("testcmd")
        assert "testcmd" in cmd_error
        assert "not found" in cmd_error.lower() or "not recognized" in cmd_error.lower()
    
    def test_platform_capabilities(self):
        """Test platform capability detection."""
        capabilities = PlatformCapabilities.get_capabilities()
        
        assert isinstance(capabilities, dict)
        assert "credential_storage" in capabilities
        assert "symbolic_links" in capabilities
        assert "case_sensitive_fs" in capabilities
    
    def test_capability_report(self):
        """Test capability report generation."""
        report = PlatformCapabilities.get_capability_report()
        
        assert isinstance(report, str)
        assert "Platform:" in report
        assert "Capabilities:" in report
    
    def test_platform_limitations(self):
        """Test platform limitation detection."""
        limitations = PlatformCapabilities.check_platform_limitations()
        
        assert isinstance(limitations, list)
        # May or may not have limitations depending on platform
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        assert isinstance(get_platform_name(), str)
        
        path = normalize_path("~/test")
        assert isinstance(path, Path)
        
        error_msg = format_error_message("path", path="/test", error="Not found")
        assert isinstance(error_msg, str)
        
        capabilities = PlatformCapabilities.get_capabilities()
        assert isinstance(capabilities, dict)
        
        is_compat, warnings = check_platform_compatibility()
        assert isinstance(is_compat, bool)
        assert isinstance(warnings, list)


class TestIntegration:
    """Integration tests for aliases, performance, and platform features."""
    
    def test_alias_with_performance_tracking(self):
        """Test using aliases with performance tracking."""
        monitor = PerformanceMonitor()
        resolver = CommandAliasResolver()
        
        # Resolve alias
        command = resolver.resolve_alias("repo")
        
        # Track performance
        with monitor.track_command(command) as metrics:
            time.sleep(0.01)
        
        assert metrics.duration_ms is not None
        assert monitor.get_metrics(command) is not None
    
    def test_platform_aware_error_formatting(self):
        """Test platform-aware error message formatting."""
        # Get platform-specific path
        test_path = PathHandler.normalize_path("~/test")
        
        # Format error for current platform
        error = ErrorMessageFormatter.format_path_error(str(test_path), "Test error")
        
        assert "Test error" in error
        assert str(test_path) in error or PathHandler.to_platform_path(str(test_path)) in error
    
    def test_performance_with_platform_capabilities(self):
        """Test performance monitoring with platform capability checks."""
        monitor = PerformanceMonitor()
        capabilities = PlatformCapabilities.get_capabilities()
        
        with monitor.track_command("capability_check") as metrics:
            # Simulate checking capabilities
            _ = capabilities["credential_storage"]
        
        assert metrics.duration_ms is not None
        # Should be fast
        assert metrics.duration_ms < 1000
