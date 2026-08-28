from windows_health_monitor.cli import build_parser


def test_once_command_parses() -> None:
    args = build_parser().parse_args(["once"])
    assert args.command == "once"


def test_monitor_defaults_parse() -> None:
    args = build_parser().parse_args(["monitor"])
    assert args.command == "monitor"
    assert args.interval == 10
    assert args.gpu_interval is None
    assert args.retention_days == 3
    assert args.startup_lookback_hours == 24
    assert args.crash_dump_archive_dir is None
    assert args.crash_dump_retention == 2
    assert args.email_thresholds == "70,80,90"


def test_test_email_command_parses() -> None:
    args = build_parser().parse_args(["test-email", "--email-to", "person@example.com"])
    assert args.command == "test-email"
    assert args.email_to == "person@example.com"
