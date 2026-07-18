"""Tests for repository-wide pytest environment precedence."""

import os

from tests.conftest import _load_project_env


def test_explicit_environment_wins_over_test_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "MINIO_ENDPOINT_URL=https://tracked-config.invalid\n"
        "MINIO_ACCESS_KEY=tracked-access\n"
    )
    monkeypatch.setenv("MINIO_ENDPOINT_URL", "http://127.0.0.1:19000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "ci-access")

    _load_project_env(tmp_path)

    assert os.environ["MINIO_ENDPOINT_URL"] == "http://127.0.0.1:19000"
    assert os.environ["MINIO_ACCESS_KEY"] == "ci-access"
