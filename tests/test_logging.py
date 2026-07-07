from __future__ import annotations

import os
from datetime import datetime, timedelta

from omp_windows_health_monitor.logging import cleanup_old_logs, hourly_log_paths


def test_hourly_log_paths(tmp_path) -> None:
    paths = hourly_log_paths(tmp_path, datetime(2026, 7, 8, 13, 5))

    assert paths.metrics.name == "metrics-20260708-13.csv"
    assert paths.events.name == "events-20260708-13.log"


def test_cleanup_old_logs(tmp_path) -> None:
    old_log = tmp_path / "metrics-old.csv"
    keep_log = tmp_path / "metrics-new.csv"
    ignored = tmp_path / "notes.txt"
    old_log.write_text("old", encoding="utf-8")
    keep_log.write_text("new", encoding="utf-8")
    ignored.write_text("ignored", encoding="utf-8")

    now = datetime(2026, 7, 8, 12, 0)
    old_time = (now - timedelta(days=5)).timestamp()
    new_time = (now - timedelta(hours=1)).timestamp()
    os.utime(old_log, (old_time, old_time))
    os.utime(keep_log, (new_time, new_time))
    os.utime(ignored, (old_time, old_time))

    cleanup_old_logs(tmp_path, retention_days=3, now=now)

    assert not old_log.exists()
    assert keep_log.exists()
    assert ignored.exists()
