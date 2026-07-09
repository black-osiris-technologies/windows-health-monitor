from __future__ import annotations

from datetime import datetime

from omp_windows_health_monitor.alerts import (
    AlertState,
    collect_alerts,
    parse_thresholds,
    send_alerts_for_sample,
)


def test_parse_thresholds_sorts_and_deduplicates() -> None:
    assert parse_thresholds("90,70,80,80") == (70, 80, 90)


def test_collect_alerts_uses_highest_crossed_threshold() -> None:
    alerts = collect_alerts({"cpu_percent": 87.5}, (70, 80, 90))

    assert len(alerts) == 1
    assert alerts[0].metric == "cpu_percent"
    assert alerts[0].threshold == 80


def test_send_alerts_only_once_per_metric_per_day(tmp_path, monkeypatch) -> None:
    sent = []

    def fake_send_email(_config, message):
        sent.append(message)

    monkeypatch.setattr("omp_windows_health_monitor.alerts.send_email", fake_send_email)

    config = type(
        "Config",
        (),
        {
            "email_to": "person@example.com",
            "thresholds": (70, 80, 90),
            "state_file": tmp_path / "state.json",
            "smtp": object(),
        },
    )()
    state = AlertState.load(config.state_file)
    now = datetime(2026, 7, 9, 10, 0)

    first = send_alerts_for_sample({"cpu_percent": 91.0}, config, state, now)
    second = send_alerts_for_sample({"cpu_percent": 95.0}, config, state, now)

    assert len(first) == 1
    assert second == []
    assert len(sent) == 1

