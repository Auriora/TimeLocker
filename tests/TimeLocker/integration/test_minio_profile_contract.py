"""Regression tests for normal-versus-live MinIO test ownership."""

from pathlib import Path

from tests.TimeLocker.integration import test_minio_connection, test_s3_minio


LIVE_TESTS = {
    "test_s3_repository_init_and_check",
    "test_s3_backup_and_restore",
    "test_s3_multiple_backups",
    "test_s3_repository_stats",
}


def _marker_names(test_function) -> set[str]:
    return {marker.name for marker in getattr(test_function, "pytestmark", [])}


def test_only_live_service_tests_use_minio_marker():
    collected_tests = {
        name: value
        for name, value in vars(test_s3_minio).items()
        if name.startswith("test_") and callable(value)
    }

    assert LIVE_TESTS <= collected_tests.keys()
    for name, test_function in collected_tests.items():
        marker_names = _marker_names(test_function)
        assert ("minio" in marker_names) is (name in LIVE_TESTS)
        assert ("network" in marker_names) is (name in LIVE_TESTS)


def test_mocked_minio_contracts_remain_in_normal_profile():
    mocked_tests = [
        value
        for name, value in vars(test_minio_connection).items()
        if name.startswith("test_") and callable(value)
    ]

    assert mocked_tests
    assert all("minio" not in _marker_names(test) for test in mocked_tests)


def test_normal_ci_explicitly_excludes_live_minio_profile():
    repo_root = Path(__file__).resolve().parents[3]
    workflow = (repo_root / ".github/workflows/test-suite.yml").read_text()

    assert (
        'python -m pytest -m "not performance and not stress and not minio"' in workflow
    )
