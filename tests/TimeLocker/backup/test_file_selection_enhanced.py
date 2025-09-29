"""
Tests for enhanced file selection functionality
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from TimeLocker.file_selections import FileSelection, SelectionType, PatternGroup


class TestEnhancedFileSelection:
    """Test cases for enhanced file selection functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_dir = self.temp_dir / "test_files"
        self.test_dir.mkdir(parents=True)

        # Create test files with various extensions and patterns
        test_files = [
                "document.pdf",
                "spreadsheet.xlsx",
                "presentation.pptx",
                "source_code.py",
                "web_page.html",
                "style.css",
                "temp_file.tmp",
                "backup_file.bak",
                "log_file.log",
                "cache_file.cache",
                "image.jpg",
                "video.mp4",
                "audio.mp3"
        ]

        for filename in test_files:
            (self.test_dir / filename).write_text(f"Content of {filename}")

        # Create subdirectories
        (self.test_dir / "subdir1").mkdir()
        (self.test_dir / "subdir1" / "nested.txt").write_text("Nested content")
        (self.test_dir / "subdir1" / "temp.tmp").write_text("Temp in subdir")

        (self.test_dir / "subdir2").mkdir()
        (self.test_dir / "subdir2" / "another.py").write_text("Python in subdir")

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_pattern_group_common_groups(self):
        """Test predefined common pattern groups"""
        # Test office documents group
        office_group = PatternGroup.get_common_group("office_documents")
        assert "*.pdf" in office_group.patterns
        assert "*.docx" in office_group.patterns
        assert "*.xlsx" in office_group.patterns
        assert "*.pptx" in office_group.patterns

        # Test temporary files group
        temp_group = PatternGroup.get_common_group("temporary_files")
        assert "*.tmp" in temp_group.patterns
        assert "*.bak" in temp_group.patterns
        assert "*.cache" in temp_group.patterns

        # Test source code group
        source_group = PatternGroup.get_common_group("source_code")
        assert "*.py" in source_group.patterns
        assert "*.html" in source_group.patterns
        assert "*.css" in source_group.patterns

        # Test media files group
        media_group = PatternGroup.get_common_group("media_files")
        assert "*.jpg" in media_group.patterns
        assert "*.mp4" in media_group.patterns
        assert "*.mp3" in media_group.patterns

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_pattern_group_invalid_group(self):
        """Test error handling for invalid pattern group"""
        with pytest.raises(KeyError, match="Pattern group 'invalid_group' not found"):
            PatternGroup.get_common_group("invalid_group")

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_pattern_groups(self):
        """Test adding and removing pattern groups"""
        selection = FileSelection()

        # Add office documents as include
        selection.add_pattern_group("office_documents", SelectionType.INCLUDE)
        assert "*.pdf" in selection.include_patterns
        assert "*.docx" in selection.include_patterns

        # Add temporary files as exclude
        selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)
        assert "*.tmp" in selection.exclude_patterns
        assert "*.bak" in selection.exclude_patterns

        # Remove office documents
        selection.remove_pattern_group("office_documents", SelectionType.INCLUDE)
        assert "*.pdf" not in selection.include_patterns
        assert "*.docx" not in selection.include_patterns

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_custom_pattern_group(self):
        """Test adding custom pattern groups"""
        selection = FileSelection()

        # Create custom pattern group
        custom_group = PatternGroup("custom_docs", ["*.txt", "*.md", "*.rst"])
        selection.add_pattern_group(custom_group, SelectionType.INCLUDE)

        assert "*.txt" in selection.include_patterns
        assert "*.md" in selection.include_patterns
        assert "*.rst" in selection.include_patterns

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_matches_pattern_functionality(self):
        """Test pattern matching functionality"""
        selection = FileSelection()

        patterns = {"*.txt", "*.py", "temp*"}

        # Test exact matches
        assert selection.matches_pattern("file.txt", patterns)
        assert selection.matches_pattern("script.py", patterns)
        assert selection.matches_pattern("tempfile", patterns)

        # Test path-based matches
        assert selection.matches_pattern("/path/to/file.txt", patterns)
        assert selection.matches_pattern("/path/to/script.py", patterns)

        # Test non-matches
        assert not selection.matches_pattern("file.pdf", patterns)
        assert not selection.matches_pattern("document.docx", patterns)

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_should_include_file_logic(self):
        """Test comprehensive file inclusion logic"""
        selection = FileSelection()
        selection.add_path(self.test_dir, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)
        selection.add_pattern("*.bak", SelectionType.EXCLUDE)
        selection.add_path(self.test_dir / "subdir1", SelectionType.EXCLUDE)

        # Files that should be included
        assert selection.should_include_file(self.test_dir / "document.pdf")
        assert selection.should_include_file(self.test_dir / "source_code.py")
        assert selection.should_include_file(self.test_dir / "subdir2" / "another.py")

        # Files that should be excluded by pattern
        assert not selection.should_include_file(self.test_dir / "temp_file.tmp")
        assert not selection.should_include_file(self.test_dir / "backup_file.bak")

        # Files that should be excluded by path
        assert not selection.should_include_file(self.test_dir / "subdir1" / "nested.txt")
        assert not selection.should_include_file(self.test_dir / "subdir1" / "temp.tmp")

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_get_effective_paths(self):
        """Test effective path resolution"""
        selection = FileSelection()
        selection.add_path(self.test_dir, SelectionType.INCLUDE)
        selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)

        effective_paths = selection.get_effective_paths()

        # Check included files
        included_names = [p.name for p in effective_paths["included"]]
        assert "document.pdf" in included_names
        assert "source_code.py" in included_names
        assert "nested.txt" in included_names
        assert "another.py" in included_names

        # Check excluded files (by pattern)
        assert "temp_file.tmp" not in included_names
        assert "backup_file.bak" not in included_names
        assert "cache_file.cache" not in included_names

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_estimate_backup_size(self):
        """Test backup size estimation"""
        selection = FileSelection()
        selection.add_path(self.test_dir, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)

        stats = selection.estimate_backup_size()

        # Should have positive values
        assert stats["total_size"] > 0
        assert stats["file_count"] > 0
        assert stats["directory_count"] >= 2  # At least subdir1 and subdir2

        # Verify that excluded files don't contribute to size
        selection_all = FileSelection()
        selection_all.add_path(self.test_dir, SelectionType.INCLUDE)
        stats_all = selection_all.estimate_backup_size()

        # Stats with exclusions should be smaller
        assert stats["total_size"] <= stats_all["total_size"]
        assert stats["file_count"] <= stats_all["file_count"]

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_complex_selection_scenario(self):
        """Test complex file selection scenario"""
        selection = FileSelection()

        # Include the test directory
        selection.add_path(self.test_dir, SelectionType.INCLUDE)

        # Include office documents specifically
        selection.add_pattern_group("office_documents", SelectionType.INCLUDE)

        # Exclude temporary files
        selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)

        # Exclude specific subdirectory
        selection.add_path(self.test_dir / "subdir1", SelectionType.EXCLUDE)

        # Test specific files
        assert selection.should_include_file(self.test_dir / "document.pdf")  # Office doc
        assert selection.should_include_file(self.test_dir / "source_code.py")  # Regular file
        assert not selection.should_include_file(self.test_dir / "temp_file.tmp")  # Temp file
        assert not selection.should_include_file(self.test_dir / "subdir1" / "nested.txt")  # Excluded dir

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_edge_cases(self):
        """Test edge cases in file selection"""
        selection = FileSelection()

        # Test with non-existent paths
        non_existent = Path("/non/existent/path")
        selection.add_path(non_existent, SelectionType.INCLUDE)

        # Should not crash when getting effective paths
        effective_paths = selection.get_effective_paths()
        assert len(effective_paths["included"]) == 0

        # Should not crash when estimating size
        stats = selection.estimate_backup_size()
        assert stats["total_size"] == 0
        assert stats["file_count"] == 0

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_properties(self):
        """Test file selection property accessors"""
        selection = FileSelection()

        # Add some paths and patterns
        selection.add_path(self.test_dir, SelectionType.INCLUDE)
        selection.add_path(self.test_dir / "subdir1", SelectionType.EXCLUDE)
        selection.add_pattern("*.txt", SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)

        # Test properties return copies
        includes = selection.includes
        excludes = selection.excludes
        include_patterns = selection.include_patterns
        exclude_patterns = selection.exclude_patterns

        # Verify content
        assert self.test_dir in includes
        assert self.test_dir / "subdir1" in excludes
        assert "*.txt" in include_patterns
        assert "*.tmp" in exclude_patterns

        # Verify they are copies (modifying shouldn't affect original)
        includes.add(Path("/new/path"))
        assert Path("/new/path") not in selection.includes

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_repr(self):
        """Test string representation of file selection"""
        selection = FileSelection()
        selection.add_path(self.test_dir, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)

        repr_str = repr(selection)
        assert "FileSelection" in repr_str
        # Check for path in a platform-independent way - the path should be present
        # either as forward slashes (Unix/repr) or backslashes (Windows/str)
        test_dir_str = str(self.test_dir)
        test_dir_posix = self.test_dir.as_posix()
        assert test_dir_str in repr_str or test_dir_posix in repr_str
        assert "*.tmp" in repr_str
