from __future__ import annotations

import json
from subprocess import CompletedProcess

from windows_health_monitor.collectors import events_windows


def test_collect_system_event_batch_tracks_cursor(monkeypatch) -> None:
    payload = {
        "last_record_id": 44,
        "events": [
            {
                "record_id": 43,
                "timestamp": "2026-08-28T15:26:42+03:00",
                "provider": "Microsoft-Windows-WER-SystemErrorReporting",
                "event_id": 1001,
                "level": "Error",
                "message": "The computer rebooted from a bugcheck.",
            }
        ],
    }

    captured = {}

    def fake_run(*args, **kwargs):
        captured["command"] = args[0]
        return CompletedProcess(args[0], 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(events_windows.subprocess, "run", fake_run)

    batch = events_windows.collect_system_event_batch(last_record_id=42)

    assert batch.last_record_id == 44
    assert len(batch.events) == 1
    assert "RecordId=43" in batch.events[0].format()
    assert batch.events[0].event_id == 1001
    script = captured["command"][-1]
    assert "Import-Module $diagnosticsModule -ErrorAction Stop" in script
    assert "-FilterXPath $xpath -Oldest -MaxEvents 1000" in script
    assert "Where-Object RecordId" not in script


def test_collect_system_event_batch_uses_time_filter_without_cursor(monkeypatch) -> None:
    captured = {}
    payload = {"last_record_id": 12, "events": []}

    def fake_run(*args, **kwargs):
        captured["command"] = args[0]
        return CompletedProcess(args[0], 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(events_windows.subprocess, "run", fake_run)

    events_windows.collect_system_event_batch(startup_lookback_seconds=300)

    script = captured["command"][-1]
    assert "AddSeconds(-300)" in script
    assert "-FilterHashtable @{LogName='System'; StartTime=$start}" in script


def test_collect_recent_system_events_is_resilient(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return CompletedProcess(args[0], 1, stdout="", stderr="access denied")

    monkeypatch.setattr(events_windows.subprocess, "run", fake_run)

    assert events_windows.collect_recent_system_events(60) == []
