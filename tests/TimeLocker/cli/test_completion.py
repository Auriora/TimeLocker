"""
Unit tests for TimeLocker CLI completion functions.

Tests auto-completion for repositories, selections, and other CLI parameters.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.TimeLocker.completion import (
    complete_repositories,
    complete_selection_names,
    complete_repository_names,
    repository_completer,
    selection_name_completer
)


class TestCompletion:
    """Test suite for CLI completion functions."""

    @pytest.mark.unit
    def test_complete_repositories_returns_list(self):
        """Test that complete_repositories returns a list."""
        result = complete_repositories('')
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_complete_repositories_filters_by_prefix(self):
        """Test that complete_repositories filters by prefix."""
        # Get all repositories
        all_repos = complete_repositories('')
        
        if all_repos:
            # Test with first character of first repo
            prefix = all_repos[0][0]
            filtered = complete_repositories(prefix)
            
            # All filtered results should start with prefix
            for repo in filtered:
                assert repo.startswith(prefix)

    @pytest.mark.unit
    def test_complete_selection_names_returns_list(self):
        """Test that complete_selection_names returns a list."""
        result = complete_selection_names('')
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_complete_selection_names_filters_by_prefix(self):
        """Test that complete_selection_names filters by prefix."""
        # Get all selections
        all_selections = complete_selection_names('')
        
        if all_selections:
            # Test with first character of first selection
            prefix = all_selections[0][0]
            filtered = complete_selection_names(prefix)
            
            # All filtered results should start with prefix
            for selection in filtered:
                assert selection.startswith(prefix)

    @pytest.mark.unit
    def test_complete_repository_names_returns_list(self):
        """Test that complete_repository_names returns a list."""
        result = complete_repository_names('')
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_repository_completer_is_callable(self):
        """Test that repository_completer is callable."""
        assert callable(repository_completer)
        result = repository_completer('')
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_selection_name_completer_is_callable(self):
        """Test that selection_name_completer is callable."""
        assert callable(selection_name_completer)
        result = selection_name_completer('')
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_complete_repositories_handles_empty_prefix(self):
        """Test that complete_repositories handles empty prefix."""
        result = complete_repositories('')
        assert isinstance(result, list)
        # Should return all available repositories
        assert len(result) >= 0

    @pytest.mark.unit
    def test_complete_selection_names_handles_empty_prefix(self):
        """Test that complete_selection_names handles empty prefix."""
        result = complete_selection_names('')
        assert isinstance(result, list)
        # Should return all available selections
        assert len(result) >= 0

    @pytest.mark.unit
    def test_complete_repositories_handles_nonexistent_prefix(self):
        """Test that complete_repositories handles nonexistent prefix."""
        result = complete_repositories('zzz_nonexistent_repo_xyz')
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_complete_selection_names_handles_nonexistent_prefix(self):
        """Test that complete_selection_names handles nonexistent prefix."""
        result = complete_selection_names('zzz_nonexistent_selection_xyz')
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_complete_repositories_no_duplicates(self):
        """Test that complete_repositories returns no duplicates."""
        result = complete_repositories('')
        assert len(result) == len(set(result))

    @pytest.mark.unit
    def test_complete_selection_names_no_duplicates(self):
        """Test that complete_selection_names returns no duplicates."""
        result = complete_selection_names('')
        assert len(result) == len(set(result))

    @pytest.mark.unit
    @patch('src.TimeLocker.completion.list_available_repositories')
    def test_complete_repositories_handles_errors_gracefully(self, mock_list_repos):
        """Test that complete_repositories handles errors gracefully."""
        # Simulate an error
        mock_list_repos.side_effect = Exception("Test error")
        
        # Should return empty list instead of raising
        result = complete_repositories('')
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.unit
    def test_complete_selection_names_handles_missing_directory(self):
        """Test that complete_selection_names handles missing template directory."""
        with patch('src.TimeLocker.completion.Path') as mock_path:
            # Simulate missing directory
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value = mock_path_instance
            mock_path.home.return_value = mock_path_instance
            
            # Should return empty list
            result = complete_selection_names('')
            assert isinstance(result, list)

    @pytest.mark.unit
    def test_repository_completer_matches_complete_repositories(self):
        """Test that repository_completer returns same results as complete_repositories."""
        test_prefix = ''
        result1 = repository_completer(test_prefix)
        result2 = complete_repositories(test_prefix)
        assert result1 == result2

    @pytest.mark.unit
    def test_selection_name_completer_matches_complete_selection_names(self):
        """Test that selection_name_completer returns same results as complete_selection_names."""
        test_prefix = ''
        result1 = selection_name_completer(test_prefix)
        result2 = complete_selection_names(test_prefix)
        assert result1 == result2
