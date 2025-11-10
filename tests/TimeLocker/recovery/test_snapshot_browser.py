"""
Tests for SnapshotBrowser functionality
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.snapshot_browser import (
    SnapshotBrowser,
    PaginationOptions,
    SearchCriteria,
    FileMetadata
)
from TimeLocker.interfaces.recovery_models import (
    FileType,
    SizeRange,
    DateRange
)
from TimeLocker.recovery_errors import SnapshotNotFoundError, RecoveryError
from .mock_recovery_repository import MockRecoveryRepository


class TestSnapshotBrowser:
    """Test cases for SnapshotBrowser"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockRecoveryRepository()
        self.browser = SnapshotBrowser(self.repository)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_list_snapshot_contents_root(self):
        """Test listing snapshot contents at root"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            # Mock return value
            mock_list.return_value = [
                Mock(path="/file1.txt", name="file1.txt", type=FileType.FILE),
                Mock(path="/dir1", name="dir1", type=FileType.DIRECTORY)
            ]
            
            listing = self.browser.list_snapshot_contents(
                snapshot_id="abc123",
                path="/"
            )
            
            assert listing is not None
            assert listing.path == "/"
            assert len(listing.entries) == 2
            assert listing.total_entries == 2

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_list_snapshot_contents_with_pagination(self):
        """Test listing snapshot contents with pagination"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            # Create 50 mock entries
            mock_entries = [
                Mock(path=f"/file{i}.txt", name=f"file{i}.txt", type=FileType.FILE)
                for i in range(50)
            ]
            mock_list.return_value = mock_entries
            
            # Request first page with 10 items per page
            pagination = PaginationOptions(page=1, page_size=10)
            listing = self.browser.list_snapshot_contents(
                snapshot_id="abc123",
                path="/",
                pagination=pagination
            )
            
            assert len(listing.entries) == 10
            assert listing.total_entries == 50
            assert listing.pagination_info is not None
            assert listing.pagination_info.current_page == 1
            assert listing.pagination_info.total_pages == 5
            assert listing.pagination_info.has_next is True
            assert listing.pagination_info.has_previous is False

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_list_snapshot_contents_snapshot_not_found(self):
        """Test listing contents of non-existent snapshot"""
        with pytest.raises(SnapshotNotFoundError):
            self.browser.list_snapshot_contents(
                snapshot_id="nonexistent",
                path="/"
            )

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_list_snapshot_contents_caching(self):
        """Test that snapshot listings are cached"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_list.return_value = [
                Mock(path="/file1.txt", name="file1.txt", type=FileType.FILE)
            ]
            
            # First call
            listing1 = self.browser.list_snapshot_contents("abc123", "/")
            
            # Second call - should use cache
            listing2 = self.browser.list_snapshot_contents("abc123", "/")
            
            # Should only call _list_snapshot_path once
            assert mock_list.call_count == 1
            assert listing1.entries == listing2.entries

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_search_snapshot_files_by_name_pattern(self):
        """Test searching files by name pattern"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            # Mock needs to handle the recursive parameter
            def mock_list_side_effect(snapshot_id, path, recursive=False):
                # Create proper mock objects with spec
                mock1 = Mock(spec=['path', 'name', 'type', 'size', 'modification_time'])
                mock1.path = "/file1.txt"
                mock1.name = "file1.txt"
                mock1.type = FileType.FILE
                mock1.size = 100
                mock1.modification_time = datetime.now()
                
                mock2 = Mock(spec=['path', 'name', 'type', 'size', 'modification_time'])
                mock2.path = "/file2.pdf"
                mock2.name = "file2.pdf"
                mock2.type = FileType.FILE
                mock2.size = 200
                mock2.modification_time = datetime.now()
                
                mock3 = Mock(spec=['path', 'name', 'type', 'size', 'modification_time'])
                mock3.path = "/file3.txt"
                mock3.name = "file3.txt"
                mock3.type = FileType.FILE
                mock3.size = 150
                mock3.modification_time = datetime.now()
                
                return [mock1, mock2, mock3]
            mock_list.side_effect = mock_list_side_effect
            
            criteria = SearchCriteria(name_pattern="*.txt")
            results = self.browser.search_snapshot_files("abc123", criteria)
            
            assert len(results) == 2
            assert all(entry.name.endswith('.txt') for entry in results)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_search_snapshot_files_by_file_type(self):
        """Test searching files by file type"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_list.return_value = [
                Mock(path="/file1.txt", name="file1.txt", type=FileType.FILE, size=100, modification_time=datetime.now()),
                Mock(path="/dir1", name="dir1", type=FileType.DIRECTORY, size=0, modification_time=datetime.now()),
                Mock(path="/link1", name="link1", type=FileType.SYMLINK, size=0, modification_time=datetime.now())
            ]
            
            criteria = SearchCriteria(file_types=[FileType.FILE])
            results = self.browser.search_snapshot_files("abc123", criteria)
            
            assert len(results) == 1
            assert results[0].type == FileType.FILE

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_search_snapshot_files_by_size_range(self):
        """Test searching files by size range"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_list.return_value = [
                Mock(path="/small.txt", name="small.txt", type=FileType.FILE, size=50, modification_time=datetime.now()),
                Mock(path="/medium.txt", name="medium.txt", type=FileType.FILE, size=150, modification_time=datetime.now()),
                Mock(path="/large.txt", name="large.txt", type=FileType.FILE, size=250, modification_time=datetime.now())
            ]
            
            size_range = SizeRange(min_size=100, max_size=200)
            criteria = SearchCriteria(size_range=size_range)
            results = self.browser.search_snapshot_files("abc123", criteria)
            
            assert len(results) == 1
            assert results[0].size == 150

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_search_snapshot_files_by_date_range(self):
        """Test searching files by modification date range"""
        now = datetime.now()
        old_date = now - timedelta(days=10)
        recent_date = now - timedelta(days=2)
        
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_list.return_value = [
                Mock(path="/old.txt", name="old.txt", type=FileType.FILE, size=100, modification_time=old_date),
                Mock(path="/recent.txt", name="recent.txt", type=FileType.FILE, size=100, modification_time=recent_date),
                Mock(path="/new.txt", name="new.txt", type=FileType.FILE, size=100, modification_time=now)
            ]
            
            date_range = DateRange(start_date=now - timedelta(days=5))
            criteria = SearchCriteria(date_range=date_range)
            results = self.browser.search_snapshot_files("abc123", criteria)
            
            assert len(results) == 2
            assert all(entry.modification_time >= date_range.start_date for entry in results)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_compare_snapshots_two_snapshots(self):
        """Test comparing two snapshots"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            # First snapshot has files A and B
            # Second snapshot has files B (modified) and C
            def side_effect(snapshot_id, path, recursive=False):
                if snapshot_id == "abc123":
                    return [
                        Mock(path="/fileA.txt", name="fileA.txt", type=FileType.FILE, size=100, 
                             modification_time=datetime(2024, 1, 1), checksum="hash1"),
                        Mock(path="/fileB.txt", name="fileB.txt", type=FileType.FILE, size=200, 
                             modification_time=datetime(2024, 1, 1), checksum="hash2")
                    ]
                else:  # def456
                    return [
                        Mock(path="/fileB.txt", name="fileB.txt", type=FileType.FILE, size=250, 
                             modification_time=datetime(2024, 1, 2), checksum="hash2_modified"),
                        Mock(path="/fileC.txt", name="fileC.txt", type=FileType.FILE, size=150, 
                             modification_time=datetime(2024, 1, 2), checksum="hash3")
                    ]
            
            mock_list.side_effect = side_effect
            
            comparison = self.browser.compare_snapshots(
                snapshot_ids=["abc123", "def456"],
                path="/"
            )
            
            assert comparison is not None
            assert len(comparison.added_files) == 1  # fileC
            assert len(comparison.removed_files) == 1  # fileA
            assert len(comparison.modified_files) == 1  # fileB
            assert comparison.added_files[0].path == "/fileC.txt"
            assert comparison.removed_files[0].path == "/fileA.txt"

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_compare_snapshots_insufficient_snapshots(self):
        """Test comparing with fewer than 2 snapshots"""
        with pytest.raises(ValueError):
            self.browser.compare_snapshots(
                snapshot_ids=["abc123"],
                path="/"
            )

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_get_file_metadata(self):
        """Test retrieving file metadata"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_entry = Mock(
                path="/test.txt",
                name="test.txt",
                type=FileType.FILE,
                size=100,
                modification_time=datetime.now(),
                permissions="rw-r--r--",
                checksum="abc123"
            )
            mock_list.return_value = [mock_entry]
            
            metadata = self.browser.get_file_metadata("abc123", "/test.txt")
            
            assert metadata is not None
            assert isinstance(metadata, FileMetadata)
            assert metadata.file_entry.path == "/test.txt"

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_get_file_metadata_file_not_found(self):
        """Test retrieving metadata for non-existent file"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_list.return_value = []
            
            with pytest.raises(RecoveryError):
                self.browser.get_file_metadata("abc123", "/nonexistent.txt")

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_get_file_metadata_caching(self):
        """Test that file metadata is cached"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_entry = Mock(
                path="/test.txt",
                name="test.txt",
                type=FileType.FILE,
                size=100,
                modification_time=datetime.now(),
                permissions="rw-r--r--",
                checksum="abc123"
            )
            mock_list.return_value = [mock_entry]
            
            # First call
            metadata1 = self.browser.get_file_metadata("abc123", "/test.txt")
            
            # Second call - should use cache
            metadata2 = self.browser.get_file_metadata("abc123", "/test.txt")
            
            # Should only call _list_snapshot_path once
            assert mock_list.call_count == 1
            assert metadata1.file_entry.path == metadata2.file_entry.path

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_clear_cache(self):
        """Test clearing the browser cache"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_list.return_value = [
                Mock(path="/file1.txt", name="file1.txt", type=FileType.FILE)
            ]
            
            # Populate cache
            self.browser.list_snapshot_contents("abc123", "/")
            
            # Clear cache
            self.browser.clear_cache()
            
            # Next call should hit the backend again
            self.browser.list_snapshot_contents("abc123", "/")
            
            assert mock_list.call_count == 2

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_pagination_options_validation(self):
        """Test pagination options validation"""
        # Valid options
        options = PaginationOptions(page=1, page_size=10)
        assert options.page == 1
        assert options.page_size == 10
        
        # Invalid page number
        with pytest.raises(ValueError):
            PaginationOptions(page=0, page_size=10)
        
        # Invalid page size
        with pytest.raises(ValueError):
            PaginationOptions(page=1, page_size=0)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_search_case_sensitivity(self):
        """Test case-sensitive and case-insensitive search"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            # Mock needs to handle the recursive parameter
            def mock_list_side_effect(snapshot_id, path, recursive=False):
                mock1 = Mock(spec=['path', 'name', 'type', 'size', 'modification_time'])
                mock1.path = "/File1.TXT"
                mock1.name = "File1.TXT"
                mock1.type = FileType.FILE
                mock1.size = 100
                mock1.modification_time = datetime.now()
                
                mock2 = Mock(spec=['path', 'name', 'type', 'size', 'modification_time'])
                mock2.path = "/file2.txt"
                mock2.name = "file2.txt"
                mock2.type = FileType.FILE
                mock2.size = 100
                mock2.modification_time = datetime.now()
                
                return [mock1, mock2]
            mock_list.side_effect = mock_list_side_effect
            
            # Case-insensitive search (default)
            criteria_insensitive = SearchCriteria(name_pattern="*.txt", case_sensitive=False)
            results_insensitive = self.browser.search_snapshot_files("abc123", criteria_insensitive)
            assert len(results_insensitive) == 2
            
            # Case-sensitive search
            criteria_sensitive = SearchCriteria(name_pattern="*.txt", case_sensitive=True)
            results_sensitive = self.browser.search_snapshot_files("abc123", criteria_sensitive)
            assert len(results_sensitive) == 1
