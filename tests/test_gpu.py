from omp_windows_health_monitor.collectors.gpu import parse_nvidia_smi_csv


def test_parse_nvidia_smi_csv() -> None:
    assert parse_nvidia_smi_csv("40, 1, 123\n") == {
        "gpu_temp_c": 40,
        "gpu_util_percent": 1,
        "gpu_memory_used_mb": 123,
    }


def test_parse_nvidia_smi_csv_rejects_invalid_output() -> None:
    assert parse_nvidia_smi_csv("") is None
    assert parse_nvidia_smi_csv("not,a,number") is None
