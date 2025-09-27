from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Sequence


def _snapshot_timestamp(s) -> datetime:
    """Best-effort accessor to a snapshot's datetime.
    Supports objects having .timestamp or .time attributes.
    """
    ts = getattr(s, "timestamp", None)
    if ts is None:
        ts = getattr(s, "time", None)
    if ts is None:
        raise AttributeError("Snapshot object lacks 'timestamp'/'time' attribute")
    return ts


def select_snapshots_to_remove(
    snapshots: Sequence[object],
    keep_last: int = 0,
    keep_daily: int = 0,
    keep_weekly: int = 0,
    keep_monthly: int = 0,
    keep_yearly: int = 0,
) -> List[object]:
    """
    Determine which snapshots to remove based on extended retention buckets.

    Selection order (newest-first within each bucket):
      1) keep_last           - keep N most-recent snapshots
      2) keep_daily          - keep up to N distinct calendar days
      3) keep_weekly         - keep up to N distinct ISO weeks
      4) keep_monthly        - keep up to N distinct months (YYYY-MM)
      5) keep_yearly         - keep up to N distinct years (YYYY)

    Args:
      snapshots: sequence of snapshot-like objects with .id and .timestamp/.time

    Returns:
      List of snapshots selected for removal, ordered from newest to oldest.
    """
    if not snapshots:
        return []

    snapshots_sorted = sorted(snapshots, key=_snapshot_timestamp, reverse=True)
    kept_ids: set[str] = set()

    # 1) Keep last N most recent
    if keep_last and keep_last > 0:
        for s in snapshots_sorted[:keep_last]:
            kept_ids.add(s.id)

    # 2) Keep up to keep_daily distinct calendar days
    if keep_daily and keep_daily > 0:
        seen_days = set()
        for s in snapshots_sorted:
            if s.id in kept_ids:
                continue
            day_key = _snapshot_timestamp(s).date()
            if len(seen_days) < keep_daily and day_key not in seen_days:
                kept_ids.add(s.id)
                seen_days.add(day_key)

    # 3) Keep up to keep_weekly distinct ISO weeks
    if keep_weekly and keep_weekly > 0:
        seen_weeks = set()
        for s in snapshots_sorted:
            if s.id in kept_ids:
                continue
            iso = _snapshot_timestamp(s).isocalendar()  # (year, week, weekday)
            week_key = (iso[0], iso[1])
            if len(seen_weeks) < keep_weekly and week_key not in seen_weeks:
                kept_ids.add(s.id)
                seen_weeks.add(week_key)

    # 4) Keep up to keep_monthly distinct months (YYYY-MM)
    if keep_monthly and keep_monthly > 0:
        seen_months = set()
        for s in snapshots_sorted:
            if s.id in kept_ids:
                continue
            ts = _snapshot_timestamp(s)
            month_key = (ts.year, ts.month)
            if len(seen_months) < keep_monthly and month_key not in seen_months:
                kept_ids.add(s.id)
                seen_months.add(month_key)

    # 5) Keep up to keep_yearly distinct years (YYYY)
    if keep_yearly and keep_yearly > 0:
        seen_years = set()
        for s in snapshots_sorted:
            if s.id in kept_ids:
                continue
            year_key = _snapshot_timestamp(s).year
            if len(seen_years) < keep_yearly and year_key not in seen_years:
                kept_ids.add(s.id)
                seen_years.add(year_key)

    # Everything else is a removal candidate (maintain newest->oldest order)
    return [s for s in snapshots_sorted if s.id not in kept_ids]

