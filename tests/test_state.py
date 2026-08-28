from __future__ import annotations

from windows_health_monitor.state import append_runtime_error, read_json, write_json_atomic


def test_json_state_round_trip_and_invalid_fallback(tmp_path) -> None:
    path = tmp_path / "state.json"
    write_json_atomic(path, {"last_record_id": 42})
    assert read_json(path) == {"last_record_id": 42}

    path.write_text("not-json", encoding="utf-8")
    assert read_json(path, {"last_record_id": 0}) == {"last_record_id": 0}


def test_append_runtime_error(tmp_path) -> None:
    path = tmp_path / "errors.log"
    try:
        raise RuntimeError("collector failed")
    except RuntimeError as error:
        append_runtime_error(path, error)

    assert "RuntimeError: collector failed" in path.read_text(encoding="utf-8")
