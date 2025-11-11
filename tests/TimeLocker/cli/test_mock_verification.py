"""Quick test to verify mock factory works correctly."""

import pytest
from tests.TimeLocker.cli.test_utils import create_mock_cli_service_manager


def test_mock_has_list_repositories():
    """Verify mock has list_repositories method."""
    mock = create_mock_cli_service_manager()
    
    # Should have the method
    assert hasattr(mock, 'list_repositories')
    assert callable(mock.list_repositories)
    
    # Should return empty list by default
    result = mock.list_repositories()
    assert result == []
    
    print("✓ Mock has list_repositories method")
    print(f"✓ Mock attributes: {dir(mock)}")


def test_mock_has_all_required_methods():
    """Verify mock has all required methods."""
    mock = create_mock_cli_service_manager()
    
    required_methods = [
        'list_repositories',
        'get_repository',
        'add_repository',
        'remove_repository',
        'update_repository',
        'initialize_repository',
        'check_repository',
        'get_repository_stats',
        'list_snapshots',
        'get_snapshot',
        'find_snapshots',
    ]
    
    for method_name in required_methods:
        assert hasattr(mock, method_name), f"Mock missing method: {method_name}"
        assert callable(getattr(mock, method_name)), f"Mock method not callable: {method_name}"
    
    print(f"✓ Mock has all {len(required_methods)} required methods")


if __name__ == "__main__":
    test_mock_has_list_repositories()
    test_mock_has_all_required_methods()
    print("\n✅ All mock verification tests passed!")
