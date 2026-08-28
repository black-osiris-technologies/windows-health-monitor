from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_EVENT_PATTERN = (
    "nvlddmkm|Display|dxgkrnl|Kernel-Power|Kernel-Processor-Power|"
    "Kernel-PnP|UserPnp|WER-SystemErrorReporting|disk|Ntfs|USB|stor|WHEA"
)
EVENT_BATCH_LIMIT = 1000


def _powershell_executable() -> str:
    windows_dir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    return str(windows_dir / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")


@dataclass(frozen=True)
class WindowsEvent:
    record_id: int
    timestamp: str
    provider: str
    event_id: int
    level: str
    message: str

    def format(self) -> str:
        return (
            f"[{self.timestamp}] [RecordId={self.record_id}] "
            f"{self.provider} {self.event_id} {self.level}: {self.message}"
        )


@dataclass(frozen=True)
class WindowsEventBatch:
    last_record_id: int
    events: list[WindowsEvent]


def _as_list(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def collect_system_event_batch(
    last_record_id: int = 0,
    startup_lookback_seconds: int = 24 * 60 * 60,
    pattern: str = DEFAULT_EVENT_PATTERN,
) -> WindowsEventBatch:
    if last_record_id < 0:
        raise ValueError("last_record_id must be non-negative")
    if startup_lookback_seconds <= 0:
        raise ValueError("startup_lookback_seconds must be positive")

    escaped_pattern = pattern.replace("'", "''")
    script = (
        "$diagnosticsModule=Join-Path $PSHOME "
        "'Modules\\Microsoft.PowerShell.Diagnostics\\Microsoft.PowerShell.Diagnostics.psd1'; "
        "Import-Module $diagnosticsModule -ErrorAction Stop; "
        f"$last={last_record_id}; "
        "$latest=Get-WinEvent -LogName 'System' -MaxEvents 1 -ErrorAction SilentlyContinue; "
        "$latestRecord=if($null -eq $latest){$last}else{[int64]$latest.RecordId}; "
        "if($last -gt 0 -and $latestRecord -ge $last){ "
        "$xpath=\"*[System[EventRecordID > $last]]\"; "
        "$raw=@(Get-WinEvent -LogName 'System' -FilterXPath $xpath -Oldest "
        f"-MaxEvents {EVENT_BATCH_LIMIT} -ErrorAction SilentlyContinue) "
        "} else { "
        f"$start=(Get-Date).AddSeconds(-{startup_lookback_seconds}); "
        "$raw=@(Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$start} "
        f"-MaxEvents {EVENT_BATCH_LIMIT} -ErrorAction SilentlyContinue) }}; "
        "$maxRecord=if($latestRecord -lt $last){$latestRecord}else{$last}; "
        "if($raw.Count -gt 0){ "
        "$maxRecord=($raw | Measure-Object RecordId -Maximum).Maximum }; "
        f"$matched=@($raw | Where-Object ProviderName -match '{escaped_pattern}' | "
        "Sort-Object RecordId | ForEach-Object { [pscustomobject]@{ "
        "record_id=[int64]$_.RecordId; timestamp=$_.TimeCreated.ToString('o'); "
        "provider=[string]$_.ProviderName; event_id=[int]$_.Id; "
        "level=[string]$_.LevelDisplayName; "
        "message=[string](($_.Message -replace '\\s+',' ').Trim()) } }); "
        "[pscustomobject]@{ last_record_id=[int64]$maxRecord; events=$matched } | "
        "ConvertTo-Json -Depth 5 -Compress"
    )
    result = subprocess.run(
        [_powershell_executable(), "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        detail = result.stderr.strip() or "PowerShell returned no event data"
        raise RuntimeError(f"Windows event collection failed: {detail}")

    payload = json.loads(result.stdout)
    events = [
        WindowsEvent(
            record_id=int(item.get("record_id", 0)),
            timestamp=str(item.get("timestamp", "")),
            provider=str(item.get("provider", "")),
            event_id=int(item.get("event_id", 0)),
            level=str(item.get("level", "")),
            message=str(item.get("message", "")),
        )
        for item in _as_list(payload.get("events"))
    ]
    return WindowsEventBatch(
        last_record_id=int(payload.get("last_record_id", last_record_id)),
        events=events,
    )


def collect_recent_system_events(
    seconds: int,
    pattern: str = DEFAULT_EVENT_PATTERN,
) -> list[str]:
    try:
        batch = collect_system_event_batch(
            startup_lookback_seconds=seconds,
            pattern=pattern,
        )
    except (RuntimeError, ValueError, json.JSONDecodeError):
        return []
    return [event.format() for event in batch.events]
