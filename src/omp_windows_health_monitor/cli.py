from __future__ import annotations

import argparse
import json
from pathlib import Path

from .monitor import collect_sample, run_monitor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omp-windows-health-monitor",
        description="Lightweight Windows health monitor.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("once", help="Collect one sample and print it as JSON.")

    monitor = subparsers.add_parser("monitor", help="Continuously write hourly logs.")
    monitor.add_argument("--interval", type=int, default=10, help="Sampling interval in seconds.")
    monitor.add_argument("--output-dir", type=Path, default=Path("monitor-logs"))
    monitor.add_argument("--retention-days", type=int, default=3)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "once":
        print(json.dumps(collect_sample(), indent=2))
        return 0

    if args.command == "monitor":
        run_monitor(args.output_dir, args.interval, args.retention_days)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
