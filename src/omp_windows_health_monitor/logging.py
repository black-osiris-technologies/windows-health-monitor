from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

METRIC_FIELDS = [
    "timestamp",
    "cpu_percent",
    "available_mb",
    "disk_read_mbps",
    "disk_write_mbps",
    "gpu_temp_c",
    "gpu_util_percent",
    "gpu_memory_used_mb",
]


@dataclass(frozen=True)
class LogPaths:
    metrics: Path
    events: Path


def hourly_log_paths(output_dir: Path, now: datetime | None = None) -> LogPaths:
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H")
    return LogPaths(
        metrics=output_dir / f"metrics-{timestamp}.csv",
        events=output_dir / f"events-{timestamp}.log",
    )


def ensure_metric_header(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=METRIC_FIELDS)
        writer.writeheader()


def append_metric(path: Path, sample: dict[str, object]) -> None:
    ensure_metric_header(path)
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=METRIC_FIELDS, extrasaction="ignore")
        writer.writerow(sample)


def append_events(path: Path, events: list[str]) -> None:
    if not events:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for event in events:
            file.write(event)
            file.write("\n")


def cleanup_old_logs(output_dir: Path, retention_days: int, now: datetime | None = None) -> None:
    if retention_days <= 0 or not output_dir.exists():
        return
    cutoff = (now or datetime.now()) - timedelta(days=retention_days)
    for path in output_dir.iterdir():
        if not path.is_file() or not path.name.startswith(("metrics-", "events-")):
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if modified < cutoff:
            path.unlink()
