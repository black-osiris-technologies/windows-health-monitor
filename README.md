# Windows Health Monitor

> Lightweight Windows diagnostics for the moments when your machine slows down, freezes, or throttles without an obvious cause.

[![CI](https://github.com/black-osiris-technologies/windows-health-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/black-osiris-technologies/windows-health-monitor/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/black-osiris-technologies/windows-health-monitor)](https://github.com/black-osiris-technologies/windows-health-monitor/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows)](README.md)

Windows Health Monitor records compact, time-aligned system metrics and Windows events so you can investigate intermittent CPU, memory, disk, GPU, and operating-system problems after they happen. It runs locally, stores data in human-readable files, and has no required cloud service.

## What It Captures

- CPU and memory utilization.
- Disk activity and storage signals available through Windows.
- NVIDIA GPU temperature, utilization, and memory through `nvidia-smi` when installed.
- Relevant Windows System event log entries with a durable record cursor across restarts.
- BugCheck, Kernel-Power, display, Plug and Play, storage, USB, and WHEA evidence after reboot.
- A crash-artifact inventory for `MEMORY.DMP`, minidumps, and live-kernel reports.
- Optional threshold-based email alerts with daily per-metric deduplication.
- Hourly CSV and event-log rotation with configurable retention.
- A heartbeat file and internal error log so a stopped collector is detectable.

## Quick Start

Requirements: Windows 10/11 or Windows Server and Python 3.11 or newer.

```powershell
git clone https://github.com/black-osiris-technologies/windows-health-monitor.git
cd windows-health-monitor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .

windows-health-monitor once
windows-health-monitor monitor --interval 60 --gpu-interval 300 --output-dir .\monitor-logs --retention-days 30
```

Stop continuous monitoring with `Ctrl+C`.

## Commands

| Command | Purpose |
| --- | --- |
| `once` | Collect one sample and print JSON to standard output. |
| `monitor` | Collect continuously and rotate hourly metrics and event files. |
| `test-email` | Validate SMTP configuration by sending a test alert. |

Use `windows-health-monitor --help` or `windows-health-monitor <command> --help` for all options.

## Output

The monitor writes hourly files below the selected output directory:

```text
metrics-YYYYMMDD-HH.csv
events-YYYYMMDD-HH.log
email-alert-state.json
event-cursor.json
crash-artifacts.json
monitor-errors.log
status.json
```

The durable event cursor prevents a restart from creating a blind spot: on first start the monitor
captures a configurable lookback window, then resumes from the latest Windows System event record.
For an installed task, `status.json` is stored in the installation root while the remaining files
are stored below its `logs` directory.

## Automatic Background Monitoring

An elevated installer creates an isolated virtual environment under
`%ProgramData%\WindowsHealthMonitor` and registers a hidden Scheduled Task running as `SYSTEM` at
Windows startup. The default deployment samples general metrics once per minute and NVIDIA data
once every five minutes. Less frequent GPU polling reduces wakeups on Optimus laptops.
Startup is delayed by two minutes so Windows Error Reporting can finish writing crash evidence and
to keep disk activity away from the interactive boot path.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\install-monitor-task.ps1

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\show-monitor-status.ps1
```

The task restarts automatically after an unexpected process failure and runs whether or not a user
is signed in. Runtime data is restricted to `SYSTEM`, local administrators, and the account that
installed it.

Rerunning the installer performs an in-place upgrade: it stages the new package, stops the existing
task, replaces the package, and verifies the new task is running. Collected evidence is preserved.

To preserve a full `MEMORY.DMP` before a later crash overwrites it, opt in to dump archiving:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\install-monitor-task.ps1 `
  -ArchiveCrashDumps -CrashDumpRetention 2
```

Full dumps can be several gigabytes. Archiving runs in a background worker at below-normal task
priority and never deletes the Windows-owned source dump. Use `-CrashDumpArchiveDir` to place the
archives on a different local disk.

To unregister the task while keeping collected evidence:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\uninstall-monitor-task.ps1
```

Logs can contain machine names, process information, and Windows event messages. Review and redact them before sharing.

See [Unattended Windows Monitoring](docs/operations.md) for configuration, status interpretation,
runtime layout, overhead, upgrades, troubleshooting, and removal. See
[Investigating a Windows Crash](docs/crash-investigation.md) for the post-reboot evidence workflow.

## Email Alerts

Email is optional. Configure it in the current PowerShell session or through your preferred local secret manager:

```powershell
$env:WHM_EMAIL_TO="you@example.com"
$env:WHM_SMTP_HOST="smtp.example.com"
$env:WHM_SMTP_PORT="587"
$env:WHM_SMTP_USER="smtp-user"
$env:WHM_SMTP_PASSWORD="smtp-password-or-app-password"
$env:WHM_EMAIL_FROM="you@example.com"
$env:WHM_SMTP_TLS="true"

windows-health-monitor test-email
windows-health-monitor monitor --email-thresholds 70,80,90
```

The monitor evaluates CPU, memory, GPU utilization, and GPU memory utilization. It sends at most one email per metric per day. Legacy `OMP_HEALTH_*` variables remain supported during the pre-1.0 transition, but new configurations should use `WHM_*`.

Never commit SMTP credentials or personal email addresses.

## Privacy and Limitations

- All monitoring and storage are local unless email alerts are enabled.
- NVIDIA metrics require `nvidia-smi`; other GPU vendors are not yet supported.
- This is a diagnostic aid, not an antivirus, endpoint-management agent, or replacement for Windows Performance Recorder.
- Sampling can miss events shorter than the configured interval.
- Event-log access depends on the current Windows account permissions.
- Automatic dump archiving is disabled unless explicitly selected because of its storage cost.
- Any monitor has non-zero overhead; longer metric and GPU intervals reduce it.

## Project Status

The project is under active pre-1.0 development. Core sampling, logging, retention, NVIDIA metrics, Windows events, and email alerts are implemented. Interfaces and file schemas may evolve before v1.0.

See [CHANGELOG.md](CHANGELOG.md) and the [issue tracker](https://github.com/black-osiris-technologies/windows-health-monitor/issues) for current work.

## Development

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

Read [CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md) before contributing.

## License

Released under the [MIT License](LICENSE).
