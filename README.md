# omp-windows-health-monitor

Lightweight Windows health monitor for diagnosing freezes, throttling, disk activity, GPU issues, and system events.

## Status

Early development. Windows-only.

## Features

- Capture one system health sample.
- Monitor continuously with hourly CSV log rotation.
- Retain logs for a configurable number of days.
- Read NVIDIA GPU temperature/utilization through `nvidia-smi` when available.
- Send optional email alerts when percentage metrics cross configured thresholds.
- Capture relevant Windows System event log entries.
- Keep legacy PowerShell scripts under `scripts/windows` as reference/fallback.

## Usage

Run from the repository root:

```powershell
python -m omp_windows_health_monitor once
python -m omp_windows_health_monitor monitor --interval 10 --output-dir .\monitor-logs --retention-days 3
```

After installing the package, the command is:

```powershell
omp-windows-health-monitor once
omp-windows-health-monitor monitor
```

## Email Alerts

Email alerts are optional and configured locally through CLI flags and environment variables. Do not commit personal email addresses or SMTP credentials.

The monitor checks percentage metrics:

- CPU usage
- memory usage
- GPU usage, when `nvidia-smi` is available
- GPU memory usage, when `nvidia-smi` is available

Default thresholds are `70,80,90`. To avoid spam, the monitor sends at most one email per metric per day. If CPU crosses 70% and later 90% on the same day, only the first CPU alert is sent.

```powershell
$env:OMP_HEALTH_EMAIL_TO="you@example.com"
$env:OMP_HEALTH_SMTP_HOST="smtp.example.com"
$env:OMP_HEALTH_SMTP_PORT="587"
$env:OMP_HEALTH_SMTP_USER="smtp-user"
$env:OMP_HEALTH_SMTP_PASSWORD="smtp-password-or-app-password"
$env:OMP_HEALTH_EMAIL_FROM="you@example.com"

omp-windows-health-monitor test-email
omp-windows-health-monitor monitor --email-thresholds 70,80,90
```

## Log Files

The monitor writes hourly files:

```text
metrics-YYYYMMDD-HH.csv
events-YYYYMMDD-HH.log
```

## Development

```powershell
python -m pip install -e .
python -m pytest
python -m ruff check .
```

## License

MIT
