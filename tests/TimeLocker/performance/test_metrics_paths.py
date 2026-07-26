"""Performance metrics path and startup safety tests."""

from pathlib import Path

import pytest

from TimeLocker.performance.metrics import PerformanceMetrics


@pytest.mark.unit
def test_default_metrics_path_uses_xdg_cache_not_working_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache_root = tmp_path / "cache"
    working_root = tmp_path / "working"
    working_root.mkdir()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_root))
    monkeypatch.chdir(working_root)

    metrics = PerformanceMetrics()

    assert metrics.metrics_file == (
        cache_root / "timelocker" / "performance_metrics.json"
    )
    assert metrics.metrics_file.parent != working_root


@pytest.mark.unit
def test_unreadable_metrics_parent_does_not_break_initialization(
    tmp_path: Path,
) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir(mode=0o700)
    metrics_path = blocked / "performance_metrics.json"
    blocked.chmod(0o000)
    try:
        metrics = PerformanceMetrics(metrics_path)
    finally:
        blocked.chmod(0o700)

    assert metrics.metrics_file == metrics_path
