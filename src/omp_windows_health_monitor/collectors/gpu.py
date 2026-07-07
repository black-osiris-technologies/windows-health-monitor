from __future__ import annotations

import shutil
import subprocess


def parse_nvidia_smi_csv(output: str) -> dict[str, int] | None:
    line = output.strip().splitlines()[0] if output.strip() else ""
    if not line:
        return None

    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 3:
        return None

    try:
        return {
            "gpu_temp_c": int(parts[0]),
            "gpu_util_percent": int(parts[1]),
            "gpu_memory_used_mb": int(parts[2]),
        }
    except ValueError:
        return None


def collect_nvidia_gpu() -> dict[str, int | None]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return {
            "gpu_temp_c": None,
            "gpu_util_percent": None,
            "gpu_memory_used_mb": None,
        }

    result = subprocess.run(
        [
            executable,
            "--query-gpu=temperature.gpu,utilization.gpu,memory.used",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    parsed = parse_nvidia_smi_csv(result.stdout) if result.returncode == 0 else None
    if parsed is None:
        return {
            "gpu_temp_c": None,
            "gpu_util_percent": None,
            "gpu_memory_used_mb": None,
        }
    return parsed
