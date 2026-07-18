"""Regression tests for normal-versus-live MinIO test ownership."""

from pathlib import Path

import pytest

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


def test_workflow_provisions_and_runs_live_minio_profile():
    repo_root = Path(__file__).resolve().parents[3]
    workflow = (repo_root / ".github/workflows/test-suite.yml").read_text()

    assert "minio-test:" in workflow
    assert "quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z" in workflow
    assert "MINIO_ACCESS_KEY: timelocker-ci" in workflow
    assert "MINIO_SECRET_KEY: timelocker-ci-secret" in workflow
    assert "$MINIO_ENDPOINT_URL/minio/health/live" in workflow
    assert "MinIO profile dependency error: service did not become ready" in workflow
    assert "python -m pytest -m minio --no-cov" in workflow


def test_live_minio_preflight_failure_is_actionable(monkeypatch):
    def _raise_unavailable(*_args, **_kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(test_s3_minio, "ensure_minio_reachable", _raise_unavailable)
    settings = {
        "MINIO_ENDPOINT_URL": "http://127.0.0.1:9000",
        "MINIO_ACCESS_KEY": "test-access",
        "MINIO_SECRET_KEY": "test-secret",
        "MINIO_REGION": "us-east-1",
        "MINIO_VERIFY_SSL": "false",
    }

    with pytest.raises(
        pytest.fail.Exception,
        match="MinIO profile dependency error: service is unavailable",
    ):
        test_s3_minio.minio_available.__wrapped__(settings)


def test_minio_repository_uri_preserves_explicit_endpoint_scheme(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT_URL", "http://127.0.0.1:19000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "test-access")
    monkeypatch.setenv("MINIO_SECRET_KEY", "test-secret")

    settings, missing = test_s3_minio.load_minio_settings(require_credentials=True)

    assert not missing
    assert settings["MINIO_URI_PREFIX"] == "s3:http://127.0.0.1:19000"
