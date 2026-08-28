# Unattended Windows Monitoring

This guide covers installation, upgrades, verification, recovery, and removal of the background
monitor. It complements the foreground commands in the [README](../README.md).

## Requirements

- Windows 10, Windows 11, or Windows Server.
- Python 3.11 or newer.
- An elevated Windows PowerShell session for installation and removal.
- Enough local storage for retained logs and, when enabled, crash-dump archives.

The installer does not download packages. It creates an isolated virtual environment and copies
the monitor package from the current checkout into `%ProgramData%\WindowsHealthMonitor`.

## Install

Open Windows PowerShell as Administrator in the repository root and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\install-monitor-task.ps1
```

The default installation registers a Scheduled Task named `Windows Health Monitor` with these
operational settings:

| Setting | Default |
| --- | --- |
| Account | `SYSTEM`, highest available privileges |
| Trigger | Windows startup, delayed two minutes |
| General sample interval | 60 seconds |
| NVIDIA sample interval | 300 seconds |
| Log retention | 30 days |
| First-start event lookback | 72 hours |
| Process | `pythonw.exe`, with no interactive console |
| Task priority | Below normal |

The task runs in session 0 even when nobody is signed in. Collectors may start short-lived
`powershell.exe` and `nvidia-smi.exe` child processes, but they remain in the non-interactive task
session and should not flash windows on the desktop.

### Installation options

| Parameter | Purpose |
| --- | --- |
| `-TaskName` | Override the Scheduled Task name. |
| `-InstallDir` | Override the protected runtime directory. |
| `-PythonExe` | Select a specific Python 3.11+ executable. |
| `-IntervalSeconds` | Set the main interval; minimum 10 seconds. |
| `-GpuIntervalSeconds` | Set NVIDIA polling; must be at least the main interval. |
| `-RetentionDays` | Retain hourly metric and event logs for this many days. |
| `-StartupLookbackHours` | Set the initial System event-log lookback. |
| `-StartupDelayMinutes` | Delay collection after Windows starts. |
| `-ArchiveCrashDumps` | Opt in to preserving copies of `MEMORY.DMP`. |
| `-CrashDumpArchiveDir` | Place dump copies in another local directory. |
| `-CrashDumpRetention` | Bound the number of archived full dumps. |

Full memory dumps can consume several gigabytes each. Dump archiving is therefore disabled by
default and must be selected explicitly:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\install-monitor-task.ps1 `
  -ArchiveCrashDumps -CrashDumpRetention 2
```

The archive operation is asynchronous, copies in large blocks, and never removes the
Windows-owned source dump.

## Upgrade

Update the checkout, then rerun the same elevated installer with the desired options. The
installer stages the new package before touching the running copy, stops the existing task,
replaces the package, registers the requested configuration, and verifies that the new task is
running. Collected logs, cursor state, status file, and crash archives remain in place.

Always repeat optional settings such as `-ArchiveCrashDumps` during an upgrade. The installer
uses the parameters supplied for that invocation as the complete task configuration.

## Verify Health

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\show-monitor-status.ps1
```

Healthy evidence consists of:

- `TaskState` equal to `Running`;
- `LastIterationAt` advancing at approximately the configured interval;
- a small `HeartbeatAgeSeconds` value;
- `LastError` empty;
- `MonitorVersion` matching the installed release.

Task Scheduler can report `0x00041301` while a continuous task is currently running. Interpret
`LastTaskResult` together with task state, heartbeat age, and the runtime error log rather than as
a standalone health signal.

After a restart, allow for the configured startup delay plus one collection interval, then run the
status script twice. `MonitorStartedAt` should reflect the new boot and `LastIterationAt` should
advance between checks.

## Runtime Data

The default layout is:

```text
%ProgramData%\WindowsHealthMonitor\
|-- status.json
|-- logs\
|   |-- metrics-YYYYMMDD-HH.csv
|   |-- events-YYYYMMDD-HH.log
|   |-- event-cursor.json
|   |-- crash-artifacts.json
|   |-- monitor-errors.log
|   `-- email-alert-state.json        # only when email alerts are configured
|-- crash-dumps\                      # only when dump archiving is enabled
`-- venv\
```

Hourly metric and event files follow `-RetentionDays`. The event cursor, status, error log, and
latest crash inventory are operational state and are not deleted by normal rotation. Dump archive
retention is controlled separately by `-CrashDumpRetention`.

The install directory is restricted to `SYSTEM`, local administrators, and the account that ran
the installer. Logs and dumps can contain hostnames, process details, memory contents, event
messages, file paths, and other sensitive data. Review and redact evidence before sharing it.

## Performance Characteristics

The default schedule favors low impact over high-frequency telemetry. CPU measurement samples for
250 milliseconds, disk metrics use a bounded PowerShell/CIM query, System event collection reads
at most 1,000 new records per pass, and NVIDIA collection runs once every five minutes. Hourly
files are append-only and cleanup is limited to recognized monitor log names.

Any monitor has non-zero cost. Increase `-IntervalSeconds` and `-GpuIntervalSeconds` if a system is
especially sensitive to wakeups. Decrease them only when the extra diagnostic resolution is worth
the additional process starts and sampling work.

## Troubleshooting

If the task is not running:

1. Run the status script from an elevated Windows PowerShell session.
2. Inspect `monitor-errors.log` for the most recent collector exception.
3. Confirm the configured Python executable still exists.
4. Rerun the installer to repair the virtual environment, task definition, and package copy.

A missing or stale `status.json` means the monitor has not completed an iteration. It does not by
itself identify which collector failed; use Task Scheduler history and `monitor-errors.log`.
Missing NVIDIA fields normally mean `nvidia-smi` is unavailable or the NVIDIA GPU was asleep.

## Uninstall

To stop and unregister the task while preserving all collected evidence:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\uninstall-monitor-task.ps1
```

Add `-RemoveData` only when the runtime, logs, cursor, and crash archives are no longer needed. That
option permanently removes the selected installation directory beneath `%ProgramData%`.
