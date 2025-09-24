import pytest
from datetime import datetime, timedelta

from src.TimeLocker.retention import select_snapshots_to_remove


class Snap:
    def __init__(self, sid: str, ts: datetime):
        self.id = sid
        self.timestamp = ts


def ids(items):
    return [s.id for s in items]


@pytest.mark.unit
def test_empty_returns_empty():
    assert select_snapshots_to_remove([], 0, 0, 0, 0, 0) == []


@pytest.mark.unit
def test_keep_last_two_removes_others():
    base = datetime(2025, 1, 1, 12, 0, 0)
    snaps = [Snap(f"s{i}", base + timedelta(hours=i)) for i in range(5)]
    to_remove = select_snapshots_to_remove(snaps, keep_last=2)
    # Expect 3 removals (oldest three)
    assert len(to_remove) == 3
    assert ids(to_remove) == ["s2", "s1", "s0"]


@pytest.mark.unit
def test_keep_daily_distinct_days():
    # Three days, multiple snapshots per day
    day0 = datetime(2025, 1, 3, 10, 0)
    snaps = [
        Snap("d0a", day0 + timedelta(hours=1)),
        Snap("d0b", day0 + timedelta(hours=2)),
        Snap("d1a", day0 - timedelta(days=1) + timedelta(hours=1)),
        Snap("d1b", day0 - timedelta(days=1) + timedelta(hours=2)),
        Snap("d2a", day0 - timedelta(days=2) + timedelta(hours=1)),
    ]
    to_remove = select_snapshots_to_remove(snaps, keep_daily=2)
    kept = {s.id for s in snaps} - set(ids(to_remove))
    # Should keep exactly 2 distinct days, 1 snapshot per day
    # Newest-first, so days d0 and d1 are preferred
    assert len(kept) == 2
    assert kept.issubset({"d0a", "d0b", "d1a", "d1b"})


@pytest.mark.unit
def test_keep_weekly_distinct_weeks():
    # Create snapshots over three distinct ISO weeks
    monday = datetime(2025, 1, 6, 12, 0)  # ISO week 2 of 2025
    snaps = [
        Snap("w0", monday + timedelta(days=0)),
        Snap("w1", monday - timedelta(days=7)),
        Snap("w2", monday - timedelta(days=14)),
    ]
    to_remove = select_snapshots_to_remove(snaps, keep_weekly=1)
    kept = {s.id for s in snaps} - set(ids(to_remove))
    assert len(kept) == 1
    # Newest week kept
    assert kept == {"w0"}


@pytest.mark.unit
def test_keep_monthly_distinct_months():
    snaps = [
        Snap("m0", datetime(2025, 3, 15, 12, 0)),
        Snap("m1", datetime(2025, 2, 15, 12, 0)),
        Snap("m2", datetime(2025, 1, 15, 12, 0)),
    ]
    to_remove = select_snapshots_to_remove(snaps, keep_monthly=2)
    kept = {s.id for s in snaps} - set(ids(to_remove))
    assert kept == {"m0", "m1"}


@pytest.mark.unit
def test_keep_yearly_distinct_years():
    snaps = [
        Snap("y0", datetime(2025, 1, 1, 0, 0)),
        Snap("y1", datetime(2024, 12, 31, 23, 0)),
        Snap("y2", datetime(2023, 6, 1, 0, 0)),
    ]
    to_remove = select_snapshots_to_remove(snaps, keep_yearly=1)
    kept = {s.id for s in snaps} - set(ids(to_remove))
    assert kept == {"y0"}


@pytest.mark.unit
def test_combined_order_precedence():
    # 5 days, one per day; keep_last=2 keeps two newest, then keep_daily=2 keeps next two
    base = datetime(2025, 1, 5, 12, 0)
    snaps = [Snap(f"d{i}", base - timedelta(days=i)) for i in range(5)]  # d0 newest ... d4 oldest
    to_remove = select_snapshots_to_remove(snaps, keep_last=2, keep_daily=2)
    kept = {s.id for s in snaps} - set(ids(to_remove))
    assert kept == {"d0", "d1", "d2", "d3"}

