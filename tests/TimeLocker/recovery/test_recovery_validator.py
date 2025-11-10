"""
Tests for RecoveryValidator functionality
"""

import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.recovery_validator import RecoveryValidator
from TimeLocker.interfaces.recovery_models import (
    ValidationResult,
    ValidationFailure,
    FailureType,
    SelectionCriteria,
    FileEntry,
    FileType
)
from TimeLocker.recovery_errors import ValidationError
from .mock_recovery_repository import MockRecoveryRepository


class TestRecoveryValidator:
    """Test cases for RecoveryValidator"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockRecoveryRepository()
        self.validator = RecoveryValidator(self.repository)
        
        # Create temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_pre_recovery_success(self):
        """Test successful pre-recovery validation"""
        target_path = str(self.temp_dir / "restore_target")
        
        result = self.validator.validate_pre_recovery(
            snapshot_id="abc123",
            target_path=target_path
        )
        
        assert result is not None
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_pre_recovery_snapshot_not_found(self):
        """Test pre-recovery validation with non-existent snapshot"""
        target_path = str(self.temp_dir / "restore_target")
        
        result = self.validator.validate_pre_recovery(
            snapshot_id="nonexistent",
            target_path=target_path
        )
        
        assert result.is_valid is False
        assert len(result.failed_validations) > 0

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_pre_recovery_invalid_target_path(self):
        """Test pre-recovery validation with invalid target path"""
        # Create a file instead of directory
        invalid_target = self.temp_dir / "file.txt"
        invalid_target.write_text("test")
        
        result = self.validator.validate_pre_recovery(
            snapshot_id="abc123",
            target_path=str(invalid_target)
        )
        
        assert result.is_valid is False
        assert any(
            failure.failure_type == FailureType.PERMISSION_ERROR
            for failure in result.failed_validations
        )

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_pre_recovery_non_writable_target(self):
        """Test pre-recovery validation with non-writable target"""
        # Create a directory and make it read-only
        readonly_dir = self.temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        
        try:
            result = self.validator.validate_pre_recovery(
                snapshot_id="abc123",
                target_path=str(readonly_dir)
            )
            
            # Should fail due to permission error
            assert result.is_valid is False
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_pre_recovery_with_selection_criteria(self):
        """Test pre-recovery validation with selection criteria"""
        target_path = str(self.temp_dir / "restore_target")
        selection_criteria = SelectionCriteria(
            include_patterns=["*.txt"],
            exclude_patterns=["temp/*"]
        )
        
        result = self.validator.validate_pre_recovery(
            snapshot_id="abc123",
            target_path=target_path,
            selection_criteria=selection_criteria
        )
        
        assert result is not None
        assert isinstance(result, ValidationResult)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_during_recovery(self):
        """Test during-recovery validation"""
        operation_id = "test-operation-123"
        
        result = self.validator.validate_during_recovery(operation_id)
        
        assert result is not None
        assert isinstance(result, ValidationResult)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_during_recovery_concurrent_calls(self):
        """Test that concurrent validation calls are handled"""
        operation_id = "test-operation-123"
        
        # First call
        result1 = self.validator.validate_during_recovery(operation_id)
        
        # Second call - should handle gracefully
        result2 = self.validator.validate_during_recovery(operation_id)
        
        assert result1 is not None
        assert result2 is not None

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_post_recovery(self):
        """Test post-recovery validation"""
        operation_id = "test-operation-123"
        
        result = self.validator.validate_post_recovery(operation_id)
        
        assert result is not None
        assert isinstance(result, ValidationResult)

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_verify_file_integrity_success(self):
        """Test successful file integrity verification"""
        # Create a test file
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("test content")
        
        # Compute expected checksum
        import hashlib
        with open(test_file, 'rb') as f:
            expected_checksum = hashlib.sha256(f.read()).hexdigest()
        
        # Verify integrity
        result = self.validator.verify_file_integrity(
            str(test_file),
            expected_checksum
        )
        
        assert result is True

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_verify_file_integrity_checksum_mismatch(self):
        """Test file integrity verification with checksum mismatch"""
        # Create a test file
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("test content")
        
        # Use wrong checksum
        wrong_checksum = "0" * 64
        
        # Verify integrity
        result = self.validator.verify_file_integrity(
            str(test_file),
            wrong_checksum
        )
        
        assert result is False

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_verify_file_integrity_file_not_found(self):
        """Test file integrity verification with non-existent file"""
        nonexistent_file = str(self.temp_dir / "nonexistent.txt")
        
        result = self.validator.verify_file_integrity(
            nonexistent_file,
            "abc123"
        )
        
        assert result is False

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_verify_file_integrity_directory(self):
        """Test file integrity verification with directory"""
        # Create a directory
        test_dir = self.temp_dir / "testdir"
        test_dir.mkdir()
        
        # Directories don't have checksums - should return True
        result = self.validator.verify_file_integrity(
            str(test_dir),
            "abc123"
        )
        
        assert result is True

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_restored_files_all_valid(self):
        """Test validating restored files when all are valid"""
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
        
        # Create file entries
        file_list = [
            FileEntry(
                path="file1.txt",
                name="file1.txt",
                type=FileType.FILE,
                size=8,
                modification_time=datetime.now(),
                permissions="rw-r--r--",
                checksum=checksum1
            ),
            FileEntry(
                path="file2.txt",
                name="file2.txt",
                type=FileType.FILE,
                size=8,
                modification_time=datetime.now(),
                permissions="rw-r--r--",
                checksum=checksum2
            )
        ]
        
        result = self.validator.validate_restored_files(
            snapshot_id="abc123",
            target_path=str(self.temp_dir),
            file_list=file_list
        )
        
        assert result.is_valid is True
        assert result.validated_files == 2
        assert len(result.failed_validations) == 0

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_restored_files_missing_file(self):
        """Test validating restored files when some are missing"""
        file_list = [
            FileEntry(
                path="missing.txt",
                name="missing.txt",
                type=FileType.FILE,
                size=100,
                modification_time=datetime.now(),
                permissions="rw-r--r--",
                checksum="abc123"
            )
        ]
        
        result = self.validator.validate_restored_files(
            snapshot_id="abc123",
            target_path=str(self.temp_dir),
            file_list=file_list
        )
        
        assert result.is_valid is False
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0].failure_type == FailureType.FILE_MISSING

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_validate_restored_files_checksum_mismatch(self):
        """Test validating restored files with checksum mismatch"""
        # Create a test file
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("actual content")
        
        # Create file entry with wrong checksum
        file_list = [
            FileEntry(
                path="test.txt",
                name="test.txt",
                type=FileType.FILE,
                size=14,
                modification_time=datetime.now(),
                permissions="rw-r--r--",
                checksum="0" * 64  # Wrong checksum
            )
        ]
        
        result = self.validator.validate_restored_files(
            snapshot_id="abc123",
            target_path=str(self.temp_dir),
            file_list=file_list
        )
        
        assert result.is_valid is False
        assert len(result.failed_validations) == 1
        assert result.failed_validations[0].failure_type == FailureType.CHECKSUM_MISMATCH

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_clear_validation_cache_specific_operation(self):
        """Test clearing validation cache for specific operation"""
        operation_id = "test-operation-123"
        
        # Perform validation to populate cache
        self.validator.validate_during_recovery(operation_id)
        
        # Clear cache for this operation
        self.validator.clear_validation_cache(operation_id)
        
        # Should succeed without error
        assert True

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_clear_validation_cache_all(self):
        """Test clearing entire validation cache"""
        # Perform multiple validations
        self.validator.validate_during_recovery("op1")
        self.validator.validate_during_recovery("op2")
        
        # Clear entire cache
        self.validator.clear_validation_cache()
        
        # Should succeed without error
        assert True

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_detect_corruption_file_not_found(self):
        """Test corruption detection for non-existent file"""
        result = self.validator.detect_corruption(
            file_path=str(self.temp_dir / "nonexistent.txt"),
            expected_size=100
        )
        
        assert result["corrupted"] is True
        assert "does not exist" in result["issues"][0]
        assert result["severity"] == "critical"

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_detect_corruption_size_mismatch(self):
        """Test corruption detection with size mismatch"""
        # Create a test file
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("short")
        
        result = self.validator.detect_corruption(
            file_path=str(test_file),
            expected_size=1000
        )
        
        assert result["corrupted"] is True
        assert any("Size mismatch" in issue for issue in result["issues"])
        assert result["severity"] == "high"

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_detect_corruption_checksum_mismatch(self):
        """Test corruption detection with checksum mismatch"""
        # Create a test file
        test_file = self.temp_dir / "test.txt"
        content = "test content"
        test_file.write_text(content)
        
        result = self.validator.detect_corruption(
            file_path=str(test_file),
            expected_size=len(content),
            expected_checksum="0" * 64
        )
        
        assert result["corrupted"] is True
        assert any("Checksum mismatch" in issue for issue in result["issues"])
        assert result["severity"] == "critical"

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_detect_corruption_zero_byte_file(self):
        """Test corruption detection for zero-byte file"""
        # Create an empty file
        test_file = self.temp_dir / "empty.txt"
        test_file.touch()
        
        result = self.validator.detect_corruption(
            file_path=str(test_file),
            expected_size=100
        )
        
        assert result["corrupted"] is True
        assert any("empty" in issue.lower() for issue in result["issues"])
        assert result["severity"] == "critical"

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_detect_corruption_no_issues(self):
        """Test corruption detection when file is valid"""
        # Create a test file
        test_file = self.temp_dir / "test.txt"
        content = "test content"
        test_file.write_text(content)
        
        # Compute correct checksum
        import hashlib
        with open(test_file, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        result = self.validator.detect_corruption(
            file_path=str(test_file),
            expected_size=len(content),
            expected_checksum=checksum
        )
        
        assert result["corrupted"] is False
        assert len(result["issues"]) == 0

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_generate_verification_report(self):
        """Test generating verification report"""
        # Create a validation result with some failures
        result = ValidationResult(
            is_valid=False,
            validated_files=10,
            validation_time=datetime.now()
        )
        result.add_failure(ValidationFailure(
            file_path="/test/file1.txt",
            expected_checksum="abc123",
            actual_checksum="def456",
            failure_type=FailureType.CHECKSUM_MISMATCH,
            error_message="Checksum mismatch detected"
        ))
        
        report = self.validator.generate_verification_report(result)
        
        assert report is not None
        assert "RECOVERY VALIDATION REPORT" in report
        assert "FAILED" in report
        assert "file1.txt" in report
        assert "Checksum mismatch" in report

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_generate_verification_report_to_file(self):
        """Test generating verification report to file"""
        result = ValidationResult(
            is_valid=True,
            validated_files=5,
            validation_time=datetime.now()
        )
        
        output_path = str(self.temp_dir / "report.txt")
        report = self.validator.generate_verification_report(result, output_path)
        
        assert Path(output_path).exists()
        assert "RECOVERY VALIDATION REPORT" in report

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_batch_verify_files_all_valid(self):
        """Test batch file verification when all files are valid"""
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
        assert len(result.failed_validations) == 0

    @pytest.mark.recovery
    @pytest.mark.unit
    def test_batch_verify_files_some_invalid(self):
        """Test batch file verification with some invalid files"""
        # Create one valid file
        file1 = self.temp_dir / "file1.txt"
        file1.write_text("content1")
        
        import hashlib
        with open(file1, 'rb') as f:
            checksum1 = hashlib.sha256(f.read()).hexdigest()
        
        file_checksums = {
            "file1.txt": checksum1,
            "missing.txt": "abc123"  # This file doesn't exist
        }
        
        result = self.validator.batch_verify_files(
            file_checksums,
            base_path=str(self.temp_dir)
        )
        
        assert result.is_valid is False
        assert result.validated_files == 1
        assert len(result.failed_validations) == 1
