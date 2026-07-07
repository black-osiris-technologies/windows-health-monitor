from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from .collectors.events_windows import collect_recent_system_events
from .collectors.gpu import collect_nvidia_gpu
from .collectors.system import (
    collect_available_memory_mb,
    collect_cpu_percent,
    collect_disk_io_mbps,
)
from .logging import append_events, append_metric, cleanup_old_logs, hourly_log_paths


def collect_sample() -> dict[str, object]:
    sample: dict[str, object] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_percent": collect_cpu_percent(),
        "available_mb": collect_available_memory_mb(),
    }
    sample.update(collect_disk_io_mbps())
    sample.update(collect_nvidia_gpu())
    return sample


def run_monitor(output_dir: Path, interval_seconds: int, retention_days: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    while True:
        paths = hourly_log_paths(output_dir)
        sample = collect_sample()
        append_metric(paths.metrics, sample)
        append_events(paths.events, collect_recent_system_events(interval_seconds))
        cleanup_old_logs(output_dir, retention_days)
        time.sleep(interval_seconds)
