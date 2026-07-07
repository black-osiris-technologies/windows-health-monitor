from omp_windows_health_monitor.cli import build_parser


def test_once_command_parses() -> None:
    args = build_parser().parse_args(["once"])
    assert args.command == "once"


def test_monitor_defaults_parse() -> None:
    args = build_parser().parse_args(["monitor"])
    assert args.command == "monitor"
    assert args.interval == 10
    assert args.retention_days == 3
