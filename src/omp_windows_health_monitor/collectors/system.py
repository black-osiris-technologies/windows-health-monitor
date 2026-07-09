from __future__ import annotations

import ctypes
import ctypes.wintypes
import subprocess
import time
from dataclasses import dataclass


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


@dataclass(frozen=True)
class CpuTimes:
    idle: int
    kernel: int
    user: int


def _filetime_to_int(filetime: ctypes.wintypes.FILETIME) -> int:
    return (filetime.dwHighDateTime << 32) + filetime.dwLowDateTime


def _get_cpu_times() -> CpuTimes:
    idle = ctypes.wintypes.FILETIME()
    kernel = ctypes.wintypes.FILETIME()
    user = ctypes.wintypes.FILETIME()
    ok = ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle),
        ctypes.byref(kernel),
        ctypes.byref(user),
    )
    if not ok:
        raise OSError("GetSystemTimes failed")
    return CpuTimes(
        idle=_filetime_to_int(idle),
        kernel=_filetime_to_int(kernel),
        user=_filetime_to_int(user),
    )


def collect_cpu_percent(sample_seconds: float = 0.25) -> float:
    first = _get_cpu_times()
    time.sleep(sample_seconds)
    second = _get_cpu_times()

    idle_delta = second.idle - first.idle
    total_delta = (second.kernel - first.kernel) + (second.user - first.user)
    if total_delta <= 0:
        return 0.0
    return round((1.0 - idle_delta / total_delta) * 100.0, 2)


def collect_memory() -> dict[str, int | float]:
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    if not ok:
        raise OSError("GlobalMemoryStatusEx failed")
    total_mb = round(status.ullTotalPhys / 1024 / 1024)
    available_mb = round(status.ullAvailPhys / 1024 / 1024)
    used_percent = 0.0
    if total_mb > 0:
        used_percent = round((1.0 - available_mb / total_mb) * 100.0, 2)
    return {
        "available_mb": available_mb,
        "total_memory_mb": total_mb,
        "memory_used_percent": used_percent,
    }


def collect_available_memory_mb() -> int:
    return int(collect_memory()["available_mb"])


def collect_disk_io_mbps() -> dict[str, float | None]:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "$d=Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk | "
            "Where-Object { $_.Name -ne '_Total' }; "
            "($d | Measure-Object DiskReadBytesPersec -Sum).Sum; "
            "($d | Measure-Object DiskWriteBytesPersec -Sum).Sum"
        ),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    if result.returncode != 0:
        return {"disk_read_mbps": None, "disk_write_mbps": None}

    values = [float(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    if len(values) < 2:
        return {"disk_read_mbps": None, "disk_write_mbps": None}

    return {
        "disk_read_mbps": round(values[0] / 1024 / 1024, 2),
        "disk_write_mbps": round(values[1] / 1024 / 1024, 2),
    }

