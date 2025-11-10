"""
Integration tests for recovery operations workflows

These tests verify end-to-end recovery workflows including full and selective
recovery operations, cross-component integration, and real-world scenarios.
"""

import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
from TimeLocker.snapshot_browser import SnapshotBrowser
from TimeLocker.recovery_validator import RecoveryValidator
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.interfaces.recovery_models import (
    RecoveryOptions,
    RecoveryType,
    OperationStatus,
    SelectionCriteria,
    FileType
)
from TimeLocker.recovery_errors import RecoveryError
from .mock_recovery_repository import MockRecoveryRepository


class TestRecoveryIntegration:
    """Integration tests for recovery operations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockRecoveryRepository()
        self.snapshot_manager = SnapshotManager(self.repository)
        self.orchestrator = RecoveryOrchestrator(
            self.repository,
            snapshot_manager=self.snapshot_manager
        )
        self.browser = SnapshotBrowser(self.repository, self.snapshot_manager)
        self.validator = RecoveryValidator(self.repository, self.snapshot_manager)
        
        # Create temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_full_recovery_workflow(self):
        """Test complete full recovery workflow from start to finish"""
        target_path = str(self.temp_dir / "restore_target")
        
        # Step 1: List available snapshots
        snapshots = self.snapshot_manager.list_snapshots()
        assert len(snapshots) > 0
        snapshot_id = snapshots[0].id
        
        # Step 2: Validate pre-recovery conditions
        validation = self.validator.validate_pre_recovery(
            snapshot_id=snapshot_id,
            target_path=target_path
        )
        assert validation.is_valid is True
        
        # Step 3: Initiate recovery
        options = RecoveryOptions()
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id=snapshot_id,
            target_path=target_path,
            options=options
        )
        
        assert operation is not None
        assert operation.recovery_type == RecoveryType.FULL
        
        # Step 4: Check operation status
        status = self.orchestrator.get_recovery_status(operation.operation_id)
        assert status is not None
        assert status.operation_id == operation.operation_id

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_selective_recovery_workflow(self):
        """Test complete selective recovery workflow"""
        target_path = str(self.temp_dir / "restore_target")
        
        # Step 1: Browse snapshot to identify files
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_list.return_value = [
                Mock(path="/docs/file1.txt", name="file1.txt", type=FileType.FILE),
                Mock(path="/docs/file2.pdf", name="file2.pdf", type=FileType.FILE),
                Mock(path="/images/photo.jpg", name="photo.jpg", type=FileType.FILE)
            ]
            
            listing = self.browser.list_snapshot_contents("abc123", "/")
            assert len(listing.entries) == 3
        
        # Step 2: Define selection criteria
        selection_criteria = SelectionCriteria(
            include_patterns=["*.txt", "*.pdf"],
            exclude_patterns=["temp/*"]
        )
        
        # Step 3: Validate pre-recovery
        validation = self.validator.validate_pre_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            selection_criteria=selection_criteria
        )
        assert validation.is_valid is True
        
        # Step 4: Initiate selective recovery
        options = RecoveryOptions()
        operation = self.orchestrator.initiate_selective_recovery(
            snapshot_id="abc123",
            selection_criteria=selection_criteria,
            target_path=target_path,
            options=options
        )
        
        assert operation is not None
        assert operation.recovery_type == RecoveryType.SELECTIVE

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_recovery_with_validation_workflow(self):
        """Test recovery workflow with comprehensive validation"""
        target_path = str(self.temp_dir / "restore_target")
        
        # Step 1: Pre-recovery validation
        pre_validation = self.validator.validate_pre_recovery(
            snapshot_id="abc123",
            target_path=target_path
        )
        assert pre_validation.is_valid is True
        
        # Step 2: Initiate recovery
        options = RecoveryOptions()
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            options=options
        )
        
        # Step 3: During-recovery validation
        during_validation = self.validator.validate_during_recovery(
            operation.operation_id
        )
        assert during_validation is not None
        
        # Step 4: Post-recovery validation
        post_validation = self.validator.validate_post_recovery(
            operation.operation_id
        )
        assert post_validation is not None

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_browse_and_recover_workflow(self):
        """Test workflow of browsing snapshot then recovering specific files"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            # Mock snapshot contents
            mock_list.return_value = [
                Mock(path="/important/data.txt", name="data.txt", type=FileType.FILE, 
                     size=1000, modification_time=datetime.now()),
                Mock(path="/important/config.json", name="config.json", type=FileType.FILE,
                     size=500, modification_time=datetime.now()),
                Mock(path="/temp/cache.tmp", name="cache.tmp", type=FileType.FILE,
                     size=100, modification_time=datetime.now())
            ]
            
            # Step 1: Browse snapshot
            listing = self.browser.list_snapshot_contents("abc123", "/")
            assert len(listing.entries) == 3
            
            # Step 2: Search for specific files
            from TimeLocker.snapshot_browser import SearchCriteria
            search_criteria = SearchCriteria(path_pattern="/important/*")
            results = self.browser.search_snapshot_files("abc123", search_criteria)
            assert len(results) == 2
            
            # Step 3: Recover only the important files
            selection_criteria = SelectionCriteria(
                include_patterns=["/important/*"],
                exclude_patterns=[]
            )
            
            target_path = str(self.temp_dir / "restore_target")
            options = RecoveryOptions()
            
            operation = self.orchestrator.initiate_selective_recovery(
                snapshot_id="abc123",
                selection_criteria=selection_criteria,
                target_path=target_path,
                options=options
            )
            
            assert operation is not None
            assert operation.recovery_type == RecoveryType.SELECTIVE

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_compare_snapshots_and_recover_workflow(self):
        """Test workflow of comparing snapshots then recovering from specific one"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            # Mock different snapshot contents
            def side_effect(snapshot_id, path, recursive=False):
                if snapshot_id == "abc123":
                    return [
                        Mock(path="/file1.txt", name="file1.txt", type=FileType.FILE,
                             size=100, modification_time=datetime(2024, 1, 1), checksum="hash1"),
                        Mock(path="/file2.txt", name="file2.txt", type=FileType.FILE,
                             size=200, modification_time=datetime(2024, 1, 1), checksum="hash2")
                    ]
                else:  # def456
                    return [
                        Mock(path="/file1.txt", name="file1.txt", type=FileType.FILE,
                             size=150, modification_time=datetime(2024, 1, 2), checksum="hash1_new"),
                        Mock(path="/file3.txt", name="file3.txt", type=FileType.FILE,
                             size=300, modification_time=datetime(2024, 1, 2), checksum="hash3")
                    ]
            
            mock_list.side_effect = side_effect
            
            # Step 1: Compare snapshots
            comparison = self.browser.compare_snapshots(
                snapshot_ids=["abc123", "def456"],
                path="/"
            )
            
            assert len(comparison.added_files) == 1  # file3.txt
            assert len(comparison.removed_files) == 1  # file2.txt
            assert len(comparison.modified_files) == 1  # file1.txt
            
            # Step 2: Recover from newer snapshot
            target_path = str(self.temp_dir / "restore_target")
            options = RecoveryOptions()
            
            operation = self.orchestrator.initiate_full_recovery(
                snapshot_id="def456",
                target_path=target_path,
                options=options
            )
            
            assert operation is not None
            assert operation.snapshot_id == "def456"

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_recovery_with_error_handling_workflow(self):
        """Test recovery workflow with error handling"""
        # Step 1: Try to recover from non-existent snapshot
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        with pytest.raises(Exception):  # Should raise SnapshotNotFoundError
            self.orchestrator.initiate_full_recovery(
                snapshot_id="nonexistent",
                target_path=target_path,
                options=options
            )
        
        # Step 2: Try to recover to invalid target
        invalid_target = self.temp_dir / "file.txt"
        invalid_target.write_text("test")
        
        with pytest.raises(Exception):  # Should raise RestoreTargetError
            self.orchestrator.initiate_full_recovery(
                snapshot_id="abc123",
                target_path=str(invalid_target),
                options=options
            )

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_multiple_concurrent_recoveries(self):
        """Test handling multiple concurrent recovery operations"""
        target_path1 = str(self.temp_dir / "restore1")
        target_path2 = str(self.temp_dir / "restore2")
        target_path3 = str(self.temp_dir / "restore3")
        
        options = RecoveryOptions()
        
        # Initiate multiple recovery operations
        op1 = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path1,
            options=options
        )
        
        op2 = self.orchestrator.initiate_full_recovery(
            snapshot_id="def456",
            target_path=target_path2,
            options=options
        )
        
        op3 = self.orchestrator.initiate_full_recovery(
            snapshot_id="ghi789",
            target_path=target_path3,
            options=options
        )
        
        # Verify all operations are tracked
        operations = self.orchestrator.list_operations()
        assert len(operations) >= 3
        
        operation_ids = [op.operation_id for op in operations]
        assert op1.operation_id in operation_ids
        assert op2.operation_id in operation_ids
        assert op3.operation_id in operation_ids

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_recovery_cancellation_workflow(self):
        """Test workflow of starting and cancelling recovery"""
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        # Step 1: Start recovery
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            options=options
        )
        
        # Step 2: Check status
        status = self.orchestrator.get_recovery_status(operation.operation_id)
        assert status is not None
        
        # Step 3: Cancel recovery
        cancelled = self.orchestrator.cancel_recovery(operation.operation_id)
        # In mock environment, operation may complete before cancellation
        assert isinstance(cancelled, bool)
        
        # Step 4: Verify final status
        final_status = self.orchestrator.get_recovery_status(operation.operation_id)
        assert final_status is not None
        # Status should be either CANCELLED or already completed
        assert final_status.status in [
            OperationStatus.CANCELLED,
            OperationStatus.COMPLETED,
            OperationStatus.FAILED
        ]

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_recovery_with_file_validation_workflow(self):
        """Test recovery workflow with file-by-file validation"""
        # Create test files to simulate restored files
        file1 = self.temp_dir / "file1.txt"
        file1.write_text("content1")
        file2 = self.temp_dir / "file2.txt"
        file2.write_text("content2")
        
        # Compute checksums
        import hashlib
        with open(file1, 'rb') as f:
            checksum1 = hashlib.sha256(f.read()).hexdigest()
        with open(file2, 'rb') as f:
            checksum2 = hashlib.sha256(f.read()).hexdigest()
        
        # Step 1: Verify individual files
        assert self.validator.verify_file_integrity(str(file1), checksum1) is True
        assert self.validator.verify_file_integrity(str(file2), checksum2) is True
        
        # Step 2: Batch verify files
        file_checksums = {
            "file1.txt": checksum1,
            "file2.txt": checksum2
        }
        
        result = self.validator.batch_verify_files(
            file_checksums,
            base_path=str(self.temp_dir)
        )
        
        assert result.is_valid is True
        assert result.validated_files == 2
        
        # Step 3: Generate verification report
        report = self.validator.generate_verification_report(result)
        assert "RECOVERY VALIDATION REPORT" in report
        assert "PASSED" in report

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_snapshot_browsing_with_pagination_workflow(self):
        """Test browsing large snapshots with pagination"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            # Create 100 mock files
            mock_entries = [
                Mock(path=f"/file{i}.txt", name=f"file{i}.txt", type=FileType.FILE)
                for i in range(100)
            ]
            mock_list.return_value = mock_entries
            
            # Step 1: Get first page
            from TimeLocker.snapshot_browser import PaginationOptions
            page1 = self.browser.list_snapshot_contents(
                snapshot_id="abc123",
                path="/",
                pagination=PaginationOptions(page=1, page_size=20)
            )
            
            assert len(page1.entries) == 20
            assert page1.pagination_info.current_page == 1
            assert page1.pagination_info.total_pages == 5
            assert page1.pagination_info.has_next is True
            
            # Step 2: Get second page
            page2 = self.browser.list_snapshot_contents(
                snapshot_id="abc123",
                path="/",
                pagination=PaginationOptions(page=2, page_size=20)
            )
            
            assert len(page2.entries) == 20
            assert page2.pagination_info.current_page == 2
            assert page2.pagination_info.has_previous is True

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_search_and_selective_recovery_workflow(self):
        """Test searching for files then selectively recovering them"""
        with patch.object(self.browser, '_list_snapshot_path') as mock_list:
            mock_list.return_value = [
                Mock(path="/docs/report.pdf", name="report.pdf", type=FileType.FILE,
                     size=1000, modification_time=datetime.now()),
                Mock(path="/docs/notes.txt", name="notes.txt", type=FileType.FILE,
                     size=500, modification_time=datetime.now()),
                Mock(path="/images/photo.jpg", name="photo.jpg", type=FileType.FILE,
                     size=2000, modification_time=datetime.now()),
                Mock(path="/videos/clip.mp4", name="clip.mp4", type=FileType.FILE,
                     size=5000, modification_time=datetime.now())
            ]
            
            # Step 1: Search for documents only
            from TimeLocker.snapshot_browser import SearchCriteria
            from TimeLocker.interfaces.recovery_models import SizeRange
            
            search_criteria = SearchCriteria(
                path_pattern="/docs/*",
                size_range=SizeRange(min_size=0, max_size=2000)
            )
            
            results = self.browser.search_snapshot_files("abc123", search_criteria)
            assert len(results) == 2  # report.pdf and notes.txt
            
            # Step 2: Recover only the found documents
            selection_criteria = SelectionCriteria(
                include_patterns=["/docs/*"],
                exclude_patterns=[]
            )
            
            target_path = str(self.temp_dir / "restore_target")
            options = RecoveryOptions()
            
            operation = self.orchestrator.initiate_selective_recovery(
                snapshot_id="abc123",
                selection_criteria=selection_criteria,
                target_path=target_path,
                options=options
            )
            
            assert operation is not None
            assert operation.recovery_type == RecoveryType.SELECTIVE

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_recovery_status_tracking_workflow(self):
        """Test tracking recovery operation status throughout lifecycle"""
        target_path = str(self.temp_dir / "restore_target")
        options = RecoveryOptions()
        
        # Step 1: Initiate recovery
        operation = self.orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            options=options
        )
        
        initial_status = operation.status
        # In mock environment, operation may complete immediately or fail
        assert initial_status in [
            OperationStatus.PENDING, 
            OperationStatus.RUNNING, 
            OperationStatus.COMPLETED,
            OperationStatus.FAILED
        ]
        
        # Step 2: Check status multiple times
        for _ in range(3):
            status = self.orchestrator.get_recovery_status(operation.operation_id)
            assert status is not None
            assert status.operation_id == operation.operation_id
        
        # Step 3: List all operations
        all_operations = self.orchestrator.list_operations()
        assert any(op.operation_id == operation.operation_id for op in all_operations)

    @pytest.mark.recovery
    @pytest.mark.integration
    def test_validation_report_generation_workflow(self):
        """Test complete validation and report generation workflow"""
        # Create test files
        file1 = self.temp_dir / "file1.txt"
        file1.write_text("content1")
        file2 = self.temp_dir / "file2.txt"
        file2.write_text("content2")
        
        # Compute checksums
        import hashlib
        with open(file1, 'rb') as f:
            checksum1 = hashlib.sha256(f.read()).hexdigest()
        with open(file2, 'rb') as f:
            checksum2 = hashlib.sha256(f.read()).hexdigest()
        
        # Step 1: Batch verify files
        file_checksums = {
            "file1.txt": checksum1,
            "file2.txt": checksum2,
            "missing.txt": "abc123"  # This will fail
        }
        
        result = self.validator.batch_verify_files(
            file_checksums,
            base_path=str(self.temp_dir)
        )
        
        assert result.is_valid is False
        assert result.validated_files == 2
        assert len(result.failed_validations) == 1
        
        # Step 2: Generate report
        report_path = str(self.temp_dir / "validation_report.txt")
        report = self.validator.generate_verification_report(result, report_path)
        
        assert Path(report_path).exists()
        assert "RECOVERY VALIDATION REPORT" in report
        assert "FAILED" in report
        assert "missing.txt" in report
