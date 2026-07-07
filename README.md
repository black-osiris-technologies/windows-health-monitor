# omp-windows-health-monitor

Lightweight Windows health monitor for diagnosing freezes, throttling, disk activity, GPU issues, and system events.

## Status

Early local version. Windows-only.

## Features

- Capture one system health sample.
- Monitor continuously with hourly CSV log rotation.
- Retain logs for a configurable number of days.
- Read NVIDIA GPU temperature/utilization through `nvidia-smi` when available.
- Capture relevant Windows System event log entries.
- Keep legacy PowerShell scripts under `scripts/windows` as reference/fallback.

## Usage

Run from the repository root:

```powershell
python -m omp_windows_health_monitor once
python -m omp_windows_health_monitor monitor --interval 10 --output-dir .\monitor-logs --retention-days 3
```

After packaging, the intended command is:

```powershell
omp-windows-health-monitor once
omp-windows-health-monitor monitor
```

## Log Files

The monitor writes hourly files:

```text
metrics-YYYYMMDD-HH.csv
events-YYYYMMDD-HH.log
```

## Development

```powershell
python -m pytest
python -m ruff check .
```

## License

MIT
