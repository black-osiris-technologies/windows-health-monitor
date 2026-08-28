from __future__ import annotations

import os
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import __version__
from .alerts import AlertConfig, AlertState, send_alerts_for_sample
from .collectors.events_windows import collect_system_event_batch
from .collectors.gpu import collect_nvidia_gpu
from .collectors.system import (
    collect_cpu_percent,
    collect_disk_io_mbps,
    collect_memory,
)
from .crash_artifacts import (
    archive_memory_dump,
    discover_crash_artifacts,
    write_crash_inventory,
)
from .logging import append_events, append_metric, cleanup_old_logs, hourly_log_paths
from .state import append_runtime_error, read_json, write_json_atomic


def collect_sample(include_gpu: bool = True) -> dict[str, object]:
    sample: dict[str, object] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_percent": collect_cpu_percent(),
        "gpu_sampled": include_gpu,
    }
    sample.update(collect_memory())
    sample.update(collect_disk_io_mbps())
    if include_gpu:
        sample.update(collect_nvidia_gpu())
    return sample


def run_monitor(
    output_dir: Path,
    interval_seconds: int,
    retention_days: int,
    alert_config: AlertConfig | None = None,
    gpu_interval_seconds: int | None = None,
    startup_lookback_seconds: int = 24 * 60 * 60,
    status_file: Path | None = None,
    crash_dump_archive_dir: Path | None = None,
    crash_dump_retention: int = 2,
) -> None:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    if gpu_interval_seconds is not None and gpu_interval_seconds < interval_seconds:
        raise ValueError("gpu_interval_seconds must be at least interval_seconds")
    if startup_lookback_seconds <= 0:
        raise ValueError("startup_lookback_seconds must be positive")
    if crash_dump_retention <= 0:
        raise ValueError("crash_dump_retention must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)
    effective_gpu_interval = gpu_interval_seconds or interval_seconds
    status_path = status_file or output_dir / "status.json"
    error_path = output_dir / "monitor-errors.log"
    event_state_path = output_dir / "event-cursor.json"
    crash_inventory_path = output_dir / "crash-artifacts.json"
    windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    started_at = datetime.now().astimezone().isoformat()
    event_state = read_json(event_state_path, {"last_record_id": 0})
    last_record_id = int(event_state.get("last_record_id", 0))
    alert_state = AlertState.load(alert_config.state_file) if alert_config else None

    write_crash_inventory(crash_inventory_path, discover_crash_artifacts(windows_dir))
    archive_executor: ThreadPoolExecutor | None = None
    archive_future: Future[Path | None] | None = None
    archive_result: str | None = None
    if crash_dump_archive_dir is not None:
        archive_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="crash-archive")
        archive_future = archive_executor.submit(
            archive_memory_dump,
            windows_dir / "MEMORY.DMP",
            crash_dump_archive_dir,
            crash_dump_retention,
        )

    next_gpu_sample = 0.0
    last_error: str | None = None
    while True:
        iteration_started = time.monotonic()
        try:
            paths = hourly_log_paths(output_dir)
            include_gpu = iteration_started >= next_gpu_sample
            sample = collect_sample(include_gpu=include_gpu)
            if include_gpu:
                next_gpu_sample = iteration_started + effective_gpu_interval
            append_metric(paths.metrics, sample)

            batch = collect_system_event_batch(
                last_record_id=last_record_id,
                startup_lookback_seconds=startup_lookback_seconds,
            )
            append_events(paths.events, [event.format() for event in batch.events])
            last_record_id = batch.last_record_id
            write_json_atomic(event_state_path, {"last_record_id": last_record_id})

            if alert_config and alert_state:
                send_alerts_for_sample(sample, alert_config, alert_state)
            cleanup_old_logs(output_dir, retention_days)

            if archive_future is not None and archive_future.done():
                try:
                    archived = archive_future.result()
                    archive_result = str(archived) if archived else "no-memory-dump"
                except Exception as archive_error:
                    append_runtime_error(error_path, archive_error)
                    archive_result = f"failed: {type(archive_error).__name__}"
                finally:
                    archive_future = None
                    if archive_executor is not None:
                        archive_executor.shutdown(wait=False)
                        archive_executor = None
            last_error = None
        except Exception as error:  # The background monitor must survive collector failures.
            append_runtime_error(error_path, error)
            last_error = f"{type(error).__name__}: {error}"

        write_json_atomic(
            status_path,
            {
                "version": __version__,
                "pid": os.getpid(),
                "started_at": started_at,
                "last_iteration_at": datetime.now().astimezone().isoformat(),
                "last_event_record_id": last_record_id,
                "last_error": last_error,
                "crash_archive_status": (
                    "running" if archive_future is not None else archive_result or "disabled"
                ),
            },
        )
        elapsed = time.monotonic() - iteration_started
        time.sleep(max(0.0, interval_seconds - elapsed))
