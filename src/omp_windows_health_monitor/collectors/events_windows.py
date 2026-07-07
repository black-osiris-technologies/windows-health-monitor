from __future__ import annotations

import subprocess


DEFAULT_EVENT_PATTERN = "nvlddmkm|Display|Kernel-Power|Kernel-Processor-Power|disk|Ntfs|USB|stor|WHEA"


def collect_recent_system_events(seconds: int, pattern: str = DEFAULT_EVENT_PATTERN) -> list[str]:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            f"$start=(Get-Date).AddSeconds(-{seconds}); "
            "Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$start} "
            "-ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.ProviderName -match '{pattern}' }} | "
            "ForEach-Object { "
            "\"[{0}] {1} {2} {3}: {4}\" -f "
            "$_.TimeCreated,$_.ProviderName,$_.Id,$_.LevelDisplayName,"
            "($_.Message -replace '\\s+', ' ') }"
        ),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]
