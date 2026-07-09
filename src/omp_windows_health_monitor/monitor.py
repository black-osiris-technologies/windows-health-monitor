from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from .alerts import AlertConfig, AlertState, send_alerts_for_sample
from .collectors.events_windows import collect_recent_system_events
from .collectors.gpu import collect_nvidia_gpu
from .collectors.system import (
    collect_cpu_percent,
    collect_disk_io_mbps,
    collect_memory,
)
from .logging import append_events, append_metric, cleanup_old_logs, hourly_log_paths


def collect_sample() -> dict[str, object]:
    sample: dict[str, object] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_percent": collect_cpu_percent(),
    }
    sample.update(collect_memory())
    sample.update(collect_disk_io_mbps())
    sample.update(collect_nvidia_gpu())
    return sample


def run_monitor(
    output_dir: Path,
    interval_seconds: int,
    retention_days: int,
    alert_config: AlertConfig | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    alert_state = AlertState.load(alert_config.state_file) if alert_config else None
    while True:
        paths = hourly_log_paths(output_dir)
        sample = collect_sample()
        append_metric(paths.metrics, sample)
        append_events(paths.events, collect_recent_system_events(interval_seconds))
        if alert_config and alert_state:
            send_alerts_for_sample(sample, alert_config, alert_state)
        cleanup_old_logs(output_dir, retention_days)
        time.sleep(interval_seconds)
