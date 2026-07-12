from __future__ import annotations

import json
import os
import smtplib
import socket
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

PERCENT_METRICS = {
    "cpu_percent": "CPU usage",
    "memory_used_percent": "Memory usage",
    "gpu_util_percent": "GPU usage",
    "gpu_memory_used_percent": "GPU memory usage",
}


def _env(name: str) -> str | None:
    """Read the current variable name, then the pre-rename compatibility alias."""
    return os.getenv(f"WHM_{name}") or os.getenv(f"OMP_HEALTH_{name}")


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    sender: str
    use_tls: bool = True


@dataclass(frozen=True)
class AlertConfig:
    email_to: str
    thresholds: tuple[int, ...]
    state_file: Path
    smtp: SmtpConfig


@dataclass(frozen=True)
class Alert:
    metric: str
    label: str
    value: float
    threshold: int


class AlertState:
    def __init__(self, path: Path, sent_by_metric: dict[str, str] | None = None) -> None:
        self.path = path
        self.sent_by_metric = sent_by_metric or {}

    @classmethod
    def load(cls, path: Path) -> AlertState:
        if not path.exists():
            return cls(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(path)
        sent_by_metric = data.get("sent_by_metric", {})
        if not isinstance(sent_by_metric, dict):
            return cls(path)
        return cls(path, {str(key): str(value) for key, value in sent_by_metric.items()})

    def already_sent_today(self, metric: str, now: datetime) -> bool:
        return self.sent_by_metric.get(metric) == now.date().isoformat()

    def mark_sent(self, metric: str, now: datetime) -> None:
        self.sent_by_metric[metric] = now.date().isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"sent_by_metric": self.sent_by_metric}, indent=2),
            encoding="utf-8",
        )


def parse_thresholds(value: str) -> tuple[int, ...]:
    thresholds = tuple(sorted({int(part.strip()) for part in value.split(",") if part.strip()}))
    if not thresholds:
        raise ValueError("at least one threshold is required")
    for threshold in thresholds:
        if threshold < 0 or threshold > 100:
            raise ValueError("thresholds must be between 0 and 100")
    return thresholds


def smtp_config_from_env() -> SmtpConfig | None:
    host = _env("SMTP_HOST")
    sender = _env("EMAIL_FROM") or _env("SMTP_USER")
    if not host or not sender:
        return None
    return SmtpConfig(
        host=host,
        port=int(_env("SMTP_PORT") or "587"),
        username=_env("SMTP_USER"),
        password=_env("SMTP_PASSWORD"),
        sender=sender,
        use_tls=(_env("SMTP_TLS") or "true").lower() != "false",
    )


def build_alert_config(
    email_to: str | None,
    thresholds: str,
    state_file: Path,
) -> AlertConfig | None:
    recipient = email_to or _env("EMAIL_TO")
    smtp = smtp_config_from_env()
    if not recipient or smtp is None:
        return None
    return AlertConfig(
        email_to=recipient,
        thresholds=parse_thresholds(thresholds),
        state_file=state_file,
        smtp=smtp,
    )


def collect_alerts(sample: dict[str, object], thresholds: tuple[int, ...]) -> list[Alert]:
    alerts: list[Alert] = []
    for metric, label in PERCENT_METRICS.items():
        raw_value = sample.get(metric)
        if raw_value is None:
            continue
        value = float(raw_value)
        crossed = [threshold for threshold in thresholds if value >= threshold]
        if crossed:
            alerts.append(Alert(metric=metric, label=label, value=value, threshold=max(crossed)))
    return alerts


def send_alerts_for_sample(
    sample: dict[str, object],
    config: AlertConfig,
    state: AlertState,
    now: datetime | None = None,
) -> list[Alert]:
    now = now or datetime.now()
    sent: list[Alert] = []
    for alert in collect_alerts(sample, config.thresholds):
        if state.already_sent_today(alert.metric, now):
            continue
        send_email(config.smtp, build_alert_message(alert, config.email_to, now))
        state.mark_sent(alert.metric, now)
        sent.append(alert)
    return sent


def build_alert_message(alert: Alert, recipient: str, now: datetime) -> EmailMessage:
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = f"[windows-health] {alert.label} over {alert.threshold}%"
    message.set_content(
        "\n".join(
            [
                f"{alert.label} reached {alert.value}%.",
                f"Threshold: {alert.threshold}%.",
                f"Host: {socket.gethostname()}",
                f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            ]
        )
    )
    return message


def send_email(config: SmtpConfig, message: EmailMessage) -> None:
    message["From"] = config.sender
    with smtplib.SMTP(config.host, config.port, timeout=30) as smtp:
        if config.use_tls:
            smtp.starttls()
        if config.username and config.password:
            smtp.login(config.username, config.password)
        smtp.send_message(message)
