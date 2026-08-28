from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .alerts import Alert, build_alert_config, build_alert_message, send_email
from .monitor import collect_sample, run_monitor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="windows-health-monitor",
        description="Lightweight Windows health monitor.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("once", help="Collect one sample and print it as JSON.")

    monitor = subparsers.add_parser("monitor", help="Continuously write hourly logs.")
    monitor.add_argument("--interval", type=int, default=10, help="Sampling interval in seconds.")
    monitor.add_argument(
        "--gpu-interval",
        type=int,
        default=None,
        help="GPU sampling interval in seconds. Defaults to the main sampling interval.",
    )
    monitor.add_argument("--output-dir", type=Path, default=Path("monitor-logs"))
    monitor.add_argument("--retention-days", type=int, default=3)
    monitor.add_argument(
        "--startup-lookback-hours",
        type=int,
        default=24,
        help="System event history captured when no durable event cursor exists.",
    )
    monitor.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help="Heartbeat/status JSON path. Defaults to <output-dir>/status.json.",
    )
    monitor.add_argument(
        "--crash-dump-archive-dir",
        type=Path,
        default=None,
        help="Optional directory that preserves MEMORY.DMP across later crashes.",
    )
    monitor.add_argument(
        "--crash-dump-retention",
        type=int,
        default=2,
        help="Number of archived MEMORY.DMP files to retain when archiving is enabled.",
    )
    monitor.add_argument("--email-to", default=None, help="Alert recipient email address.")
    monitor.add_argument(
        "--email-thresholds",
        default="70,80,90",
        help="Comma-separated percent thresholds for CPU, memory, and GPU alerts.",
    )
    monitor.add_argument(
        "--email-state-file",
        type=Path,
        default=None,
        help="Path for daily email dedupe state. Defaults to <output-dir>/email-alert-state.json.",
    )

    test_email = subparsers.add_parser("test-email", help="Send one test alert email.")
    test_email.add_argument("--email-to", default=None, help="Alert recipient email address.")
    test_email.add_argument("--email-thresholds", default="70,80,90")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "once":
        print(json.dumps(collect_sample(), indent=2))
        return 0

    if args.command == "monitor":
        state_file = args.email_state_file or args.output_dir / "email-alert-state.json"
        alert_config = build_alert_config(args.email_to, args.email_thresholds, state_file)
        run_monitor(
            args.output_dir,
            args.interval,
            args.retention_days,
            alert_config,
            gpu_interval_seconds=args.gpu_interval,
            startup_lookback_seconds=args.startup_lookback_hours * 60 * 60,
            status_file=args.status_file,
            crash_dump_archive_dir=args.crash_dump_archive_dir,
            crash_dump_retention=args.crash_dump_retention,
        )
        return 0

    if args.command == "test-email":
        state_file = Path("monitor-logs") / "email-alert-state.json"
        alert_config = build_alert_config(args.email_to, args.email_thresholds, state_file)
        if alert_config is None:
            parser.error(
                "email is not configured; set --email-to or WHM_EMAIL_TO plus "
                "WHM_SMTP_HOST and WHM_EMAIL_FROM/WHM_SMTP_USER"
            )
        alert = Alert(metric="test", label="Test alert", value=100.0, threshold=100)
        message = build_alert_message(alert, alert_config.email_to, datetime.now())
        send_email(alert_config.smtp, message)
        print(f"Sent test email to {alert_config.email_to}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
